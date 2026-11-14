"""Current HIS authorization and immutable authored-source registration for DR."""
from __future__ import annotations

import hashlib
import re

from fastapi import HTTPException
from sqlalchemy import select

from .auth import revalidate_actor, require, require_domain, scoped_encounter, scoped_patient
from .common import audit, authorization_hash, digest, utcnow
from .dr_client import patient_key
from .dr_protocol import WorkspaceScope
from .dr_public_sources import PublicDatasetEvidence
from .models import ClinicalOrder, Patient, Task, User
from .models_clinical import ImagingStudy
from .models_dr import DRCapabilityGrant, DRSourceProvenance, DRSourceSet, DRSourceSetItem
from .storage import file_store

CLOSED={'closed','completed','discharged','cancelled'}


def fail(code,status=409):
    raise HTTPException(status,detail={'code':code})


def scope_for(source_set):
    return WorkspaceScope(organization_id=source_set.organization_id,facility_id=source_set.facility_id,
        patient_id=source_set.patient_id,encounter_id=source_set.encounter_id,task_id=source_set.task_id,
        source_set_id=source_set.id,source_set_revision=source_set.revision,
        source_set_sha256=source_set.manifest_sha256)


def source_snapshot(source, provenance=None):
    names=('id','organization_id','facility_id','patient_id','encounter_id','order_id','order_version',
           'version','status','modality','body_site','file_sha256','file_mime')
    result={'schema':'carebalance.his-dr-source.v1','domain':'D11',**{n:getattr(source,n) for n in names}}
    if provenance is not None and provenance.source_origin=='PUBLIC':
        result.update(schema='carebalance.his-dr-source.v2',public_source={
            'origin':'PUBLIC','provenance_id':provenance.id,'evidence_reference':provenance.evidence_reference,
            'dataset_provenance':provenance.dataset_provenance,'laterality':provenance.laterality,
            'modality':provenance.modality,'capture_time':provenance.capture_time})
    return result


def content(source):
    if not source.file_path or source.file_mime not in {'image/png','image/jpeg'} or not re.fullmatch('[0-9a-f]{64}',source.file_sha256 or ''):
        fail('DR_EXACT_IMAGE_SOURCE_REQUIRED',422)
    try:
        data=file_store().read(source.file_path,source.file_sha256)
    except (OSError,ValueError):fail('DR_SOURCE_BYTES_UNAVAILABLE',409)
    signature=b'\x89PNG\r\n\x1a\n' if source.file_mime=='image/png' else b'\xff\xd8\xff'
    if not 1<=len(data)<=1048576 or not data.startswith(signature):
        fail('DR_EXACT_IMAGE_SOURCE_REQUIRED',422)
    return data


def capabilities(db,actor,*,writable):
    require_domain(actor,'D11')
    require(actor,'documents.content');require(actor,'documents.export')
    caps=['dr.read'];grants=[]
    if writable and 'D11.write' in actor.permissions:
        caps+=['dr.prepare','dr.report.prepare']
        now=utcnow()
        rows=db.scalars(select(DRCapabilityGrant).where(DRCapabilityGrant.organization_id==actor.organization_id,
            DRCapabilityGrant.facility_id==actor.facility_id,DRCapabilityGrant.user_id==actor.user_id,
            DRCapabilityGrant.status=='active',DRCapabilityGrant.verification_status=='verified',
            DRCapabilityGrant.valid_from<=now,DRCapabilityGrant.valid_until>now).order_by(DRCapabilityGrant.id).with_for_update()
            .execution_options(populate_existing=True)).all()
        for row in rows:
            verifier=db.scalar(select(User).where(User.id==row.verifier_id,User.organization_id==actor.organization_id,
                User.status=='active').with_for_update().execution_options(populate_existing=True))
            if (not verifier or verifier.organization_id!=actor.organization_id or verifier.status!='active'
                    or row.verifier_id==actor.user_id or not row.evidence_reference.strip()):
                continue
            caps.append(row.capability)
            grants.append({'id':row.id,'version':row.version,'capability':row.capability,
                'valid_until':row.valid_until.isoformat(),'verification':row.evidence_reference,'verifier_id':row.verifier_id})
    caps=sorted(set(caps))
    return caps,digest({'authorization':authorization_hash(actor),'capabilities':caps,'grants':grants})


def authorize_task(db,actor,patient_id,encounter_id,task_id,*,write):
    revalidate_actor(db,actor);require_domain(actor,'D11',write)
    require(actor,'documents.content');require(actor,'documents.export')
    scoped_patient(db,actor,patient_id,True)
    encounter=scoped_encounter(db,actor,encounter_id,True)
    if encounter.patient_id!=patient_id:fail('DR_ENCOUNTER_PATIENT_MISMATCH',404)
    task=db.scalar(select(Task).where(Task.id==task_id,Task.organization_id==actor.organization_id,
        Task.facility_id==actor.facility_id,Task.patient_id==patient_id,Task.encounter_id==encounter_id)
        .with_for_update().execution_options(populate_existing=True))
    if task is None:fail('DR_REVIEW_TASK_NOT_FOUND',404)
    if task.domain!='D11' or task.kind!='dr_screening_review':fail('DR_REVIEW_TASK_REQUIRED',422)
    writable=task.status in {'open','in_progress'} and encounter.status not in CLOSED
    if write and not writable:fail('DR_REVIEW_TARGET_CLOSED')
    if task.status not in {'open','in_progress','completed'}:fail('DR_REVIEW_TASK_UNAVAILABLE')
    caps,auth_hash=capabilities(db,actor,writable=writable)
    return task,encounter,caps,auth_hash


def authorize_source(db,actor,id,patient_id,encounter_id,version,provenance_id=None):
    source=db.scalar(select(ImagingStudy).where(ImagingStudy.id==id,
        ImagingStudy.organization_id==actor.organization_id,ImagingStudy.facility_id==actor.facility_id,
        ImagingStudy.patient_id==patient_id,ImagingStudy.encounter_id==encounter_id)
        .with_for_update().execution_options(populate_existing=True))
    if source is None:fail('DR_SOURCE_NOT_FOUND',404)
    if source.version!=version or source.status not in {'released','corrected'}:fail('DR_SOURCE_STALE')
    order=db.scalar(select(ClinicalOrder).where(ClinicalOrder.id==source.order_id,
        ClinicalOrder.organization_id==actor.organization_id,ClinicalOrder.facility_id==actor.facility_id,
        ClinicalOrder.patient_id==patient_id,ClinicalOrder.encounter_id==encounter_id)
        .execution_options(populate_existing=True))
    if not order or order.kind!='imaging' or order.version!=source.order_version:fail('DR_SOURCE_ORDER_STALE')
    query=select(DRSourceProvenance).where(DRSourceProvenance.source_id==source.id,
        DRSourceProvenance.source_version==source.version,DRSourceProvenance.organization_id==actor.organization_id,
        DRSourceProvenance.facility_id==actor.facility_id,DRSourceProvenance.patient_id==patient_id,
        DRSourceProvenance.encounter_id==encounter_id)
    if provenance_id:query=query.where(DRSourceProvenance.id==provenance_id)
    provenance=db.scalar(query)
    if not provenance:fail('DR_AUTHORED_SOURCE_REGISTRATION_REQUIRED',422)
    data=content(source)
    if (provenance.source_origin not in {'SYNTHETIC','PUBLIC'} or provenance.image_sha256!=source.file_sha256
            or provenance.byte_size!=len(data)):
        fail('DR_SOURCE_PROVENANCE_STALE')
    if provenance.source_origin=='PUBLIC':
        try:
            evidence=PublicDatasetEvidence.model_validate(provenance.dataset_provenance)
            if provenance.evidence_reference!='public-dataset:'+digest(evidence.model_dump(mode='json')):
                raise ValueError('Public provenance digest mismatch')
            if evidence.upstream_image_sha256 is not None and evidence.upstream_image_sha256!=source.file_sha256:
                raise ValueError('Public image identity mismatch')
        except ValueError:fail('DR_SOURCE_PROVENANCE_STALE')
    elif provenance.dataset_provenance is not None:
        fail('DR_SOURCE_PROVENANCE_STALE')
    return source,provenance,data,source_snapshot(source,provenance)


def authorize_set(db,actor,id,*,write=False):
    revalidate_actor(db,actor);require_domain(actor,'D11',write)
    query=select(DRSourceSet).where(DRSourceSet.id==id,DRSourceSet.organization_id==actor.organization_id,
        DRSourceSet.facility_id==actor.facility_id)
    if actor.patient_scope:query=query.where(DRSourceSet.patient_id==actor.patient_scope)
    if actor.care_patient_ids is not None:query=query.where(DRSourceSet.patient_id.in_(actor.care_patient_ids))
    source_set=db.scalar(query.with_for_update().execution_options(populate_existing=True))
    if not source_set:fail('DR_SOURCE_SET_NOT_FOUND',404)
    task,encounter,caps,auth_hash=authorize_task(db,actor,source_set.patient_id,source_set.encounter_id,source_set.task_id,write=write)
    items=db.scalars(select(DRSourceSetItem).where(DRSourceSetItem.source_set_id==source_set.id).order_by(DRSourceSetItem.position)).all()
    if not 1<=len(items)<=8 or digest(source_set.manifest)!=source_set.manifest_sha256:fail('DR_SOURCE_SET_INVALID')
    if any(m.get('source_origin')=='PUBLIC' for m in source_set.manifest) and source_set.consent_snapshot.get('wording_version')!='carebalance.dr-transfer.v2':
        fail('DR_PUBLIC_TRANSFER_WORDING_REQUIRED')
    blobs=[];provenances=[]
    for position,item in enumerate(items):
        if item.position!=position:fail('DR_SOURCE_SET_INVALID')
        source,provenance,data,snapshot=authorize_source(db,actor,item.source_id,source_set.patient_id,
            source_set.encounter_id,item.source_version,item.provenance_id)
        manifest=source_set.manifest[position]
        if (snapshot!=item.source_snapshot or digest(snapshot)!=item.source_sha256
                or manifest!={'source_id':source.id,'source_version':source.version,'source_sha256':item.source_sha256,
                    'image_sha256':source.file_sha256,'byte_size':len(data),'media_type':source.file_mime,
                    'laterality':provenance.laterality,'modality':provenance.modality,'source_origin':provenance.source_origin,
                    'consent_reference':source_set.consent_snapshot['reference'],'capture_time':provenance.capture_time}):
            fail('DR_SOURCE_SET_STALE')
        blobs.append(data)
        provenances.append(provenance)
    validate_public_group(provenances)
    return source_set,task,encounter,caps,auth_hash,blobs


def validate_public_group(provenances):
    public=[p for p in provenances if p.source_origin=='PUBLIC']
    if not public:return
    if len(public)!=len(provenances):fail('DR_PUBLIC_MIXED_ORIGIN_SET_DENIED',422)
    evidence=[PublicDatasetEvidence.model_validate(p.dataset_provenance) for p in public]
    if len(public)>1 and (any(p.patient_grouping=='isolated_demo_record' for p in evidence)
            or len({p.patient_grouping_reference for p in evidence})!=1):
        fail('DR_PUBLIC_PATIENT_GROUP_EVIDENCE_REQUIRED',422)


def register_authored_source(db,*,source_id,source_version,generated_bytes,laterality,modality,
                             capture_time,evidence_reference,registrar_id):
    """Offline operator-only registration of an authored fixture; never an API.

    The caller supplies bytes generated by its reviewed fixture producer. Merely
    seeing a PNG upload or receiving a browser checkbox is never registration.
    """
    source=db.get(ImagingStudy,source_id)
    registrar=db.get(User,registrar_id)
    if (not source or not registrar or registrar.organization_id!=source.organization_id
            or registrar.status!='active' or source.version!=source_version
            or source.status not in {'released','corrected'} or not isinstance(evidence_reference,str)
            or not evidence_reference.startswith('authored-synthetic:') or len(evidence_reference)>240
            or not isinstance(generated_bytes,bytes) or not 1<=len(generated_bytes)<=1048576 or hashlib.sha256(generated_bytes).hexdigest()!=source.file_sha256
            or source.file_mime!='image/png' or content(source)!=generated_bytes or laterality not in {'L','R'} or modality not in {'CFP','UWF'}):
        fail('DR_AUTHORED_FIXTURE_REGISTRATION_INVALID',422)
    if capture_time is not None:
        from .dr_protocol import utc
        utc(capture_time)
    old=db.scalar(select(DRSourceProvenance).where(DRSourceProvenance.source_id==source_id,
        DRSourceProvenance.source_version==source_version))
    expected=dict(source_id=source_id,source_version=source_version,image_sha256=source.file_sha256,
        byte_size=len(generated_bytes),source_origin='SYNTHETIC',laterality=laterality,modality=modality,
        capture_time=capture_time,evidence_reference=evidence_reference,registrar_id=registrar_id)
    if old:
        if any(getattr(old,k)!=v for k,v in expected.items()):fail('DR_PROVENANCE_IMMUTABLE')
        return old
    row=DRSourceProvenance(organization_id=source.organization_id,facility_id=source.facility_id,
        patient_id=source.patient_id,encounter_id=source.encounter_id,**expected)
    db.add(row);db.flush()
    return row


def register_public_dataset_source(db,*,source_id,source_version,original_bytes,laterality,modality,
                                   capture_time,dataset_provenance,registrar_id):
    """Offline operator registration. Dataset membership never establishes eye/patient identity."""
    try:evidence=PublicDatasetEvidence.model_validate(dataset_provenance)
    except ValueError:fail('DR_PUBLIC_SOURCE_EVIDENCE_REQUIRED',422)
    source=db.get(ImagingStudy,source_id);registrar=db.get(User,registrar_id)
    if (not source or not registrar or registrar.organization_id!=source.organization_id
            or registrar.status!='active' or source.version!=source_version
            or source.status not in {'released','corrected'} or laterality not in {'L','R'} or modality!='CFP'
            or not isinstance(original_bytes,bytes) or content(source)!=original_bytes):
        fail('DR_PUBLIC_SOURCE_REGISTRATION_INVALID',422)
    if evidence.upstream_image_sha256 is not None and evidence.upstream_image_sha256!=source.file_sha256:
        fail('DR_PUBLIC_SOURCE_REGISTRATION_INVALID',422)
    # Serialize operator registrations for this patient. Two simultaneous isolated
    # registrations must not both observe an empty group and create a false pair.
    db.scalar(select(Patient).where(Patient.id==source.patient_id).with_for_update())
    others=db.scalars(select(DRSourceProvenance).where(
        DRSourceProvenance.organization_id==source.organization_id,
        DRSourceProvenance.facility_id==source.facility_id,
        DRSourceProvenance.patient_id==source.patient_id,
        DRSourceProvenance.source_origin=='PUBLIC',DRSourceProvenance.source_id!=source_id)).all()
    if others:
        old_evidence=[PublicDatasetEvidence.model_validate(p.dataset_provenance) for p in others]
        if (evidence.patient_grouping=='isolated_demo_record'
                or any(p.patient_grouping=='isolated_demo_record' or p.patient_grouping_reference!=evidence.patient_grouping_reference for p in old_evidence)):
            fail('DR_PUBLIC_PATIENT_GROUP_EVIDENCE_REQUIRED',422)
    if capture_time is not None:
        from .dr_protocol import utc
        utc(capture_time)
    metadata=evidence.model_dump(mode='json')
    expected=dict(source_id=source_id,source_version=source_version,image_sha256=source.file_sha256,
        byte_size=len(original_bytes),source_origin='PUBLIC',laterality=laterality,modality=modality,
        capture_time=capture_time,evidence_reference='public-dataset:'+digest(metadata),
        dataset_provenance=metadata,registrar_id=registrar_id)
    old=db.scalar(select(DRSourceProvenance).where(DRSourceProvenance.source_id==source_id,
        DRSourceProvenance.source_version==source_version))
    if old:
        if any(getattr(old,k)!=v for k,v in expected.items()):fail('DR_PROVENANCE_IMMUTABLE')
        return old
    row=DRSourceProvenance(organization_id=source.organization_id,facility_id=source.facility_id,
        patient_id=source.patient_id,encounter_id=source.encounter_id,**expected)
    db.add(row);db.flush()
    return row
