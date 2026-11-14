"""Scoped DR gateway: immutable sources, explicit consent and durable commands."""
from __future__ import annotations

import base64
from copy import deepcopy
from dataclasses import dataclass
from datetime import timedelta
import hashlib
import json
import mimetypes
import os
from pathlib import Path
import re
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, text

from .auth import current_actor, require, require_domain, revalidate_actor, scoped_encounter, scoped_patient
from .common import audit, digest, uid, utcnow
from .db import get_db, SessionLocal
from .dr_client import DRClient, DRRejected, DRUnavailable, DRUnknown, patient_key, resolve_destination, strict_json
from .dr_core import authorize_set, authorize_source, authorize_task, content, fail, scope_for, validate_public_group
from .dr_protocol import Context, Dispatch, Import, ReadReport, SourceInput, canonical
from .models import AuditEvent, Patient, Encounter
from .models_clinical import ImagingStudy
from .models_dr import DRBinding, DRAttempt, DRExchange, DRReportReceipt, DRSourceProvenance, DRSourceSet, DRSourceSetItem, DRCapabilityGrant, DRCapabilityGrantEvent

router=APIRouter(prefix='/integrations/dr',tags=['DR specialist integration'])
browser_router=APIRouter(prefix='/integrations/dr',tags=['bound DR workspace'])
CASE=re.compile(r'^/v1/cases/([0-9a-f]{64})(?:/(comparison|admission|confirm-image|review|annotations|annotation-completeness|screening-report(?:/print)?))?$')
IMAGE=re.compile(r'^/v1/images/([0-9a-f]{64})(?:/(display|analysis-area|mask-overlay))?$')


class Input(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)


class Consent(Input):
    confirmed: bool
    wording_version: str=Field(pattern=r'^carebalance\.dr-transfer\.v[12]$')
    purpose: str=Field(pattern=r'^manual-dr-screening$')


class Selection(Input):
    source_id: str=Field(min_length=1,max_length=64)
    source_version: int=Field(ge=1)
    provenance_id: str=Field(min_length=1,max_length=64)


class SourceSetInput(Input):
    patient_id: str=Field(min_length=1,max_length=64)
    encounter_id: str=Field(min_length=1,max_length=64)
    task_id: str=Field(min_length=1,max_length=64)
    destination_id: str=Field(pattern=r'^[A-Za-z0-9_-]{1,64}$')
    sources: list[Selection]=Field(min_length=1,max_length=8)
    transfer_consent: Consent


class BindingInput(Input):
    transfer_consent: Consent


class ReportRead(Input):
    case_id: str=Field(pattern=r'^[0-9a-f]{64}$')


def lock(db,key):
    key=int.from_bytes(hashlib.sha256(key.encode()).digest()[:8],'big',signed=True)
    db.execute(text('SELECT pg_advisory_xact_lock(:key)'),{'key':key})


def check_key(key):
    if not key or len(key)>120:fail('IDEMPOTENCY_KEY_REQUIRED',400)


def consent_receipt(body,actor,*,reference,manifest_hash=None,destination_id,public_required=False):
    if body.confirmed is not True:fail('DR_EXPLICIT_TRANSFER_CONSENT_REQUIRED',422)
    if public_required and body.wording_version!='carebalance.dr-transfer.v2':fail('DR_PUBLIC_TRANSFER_WORDING_REQUIRED',422)
    return {'reference':reference,'actor_id':actor.user_id,'session_id':actor.session_id,
        'confirmed':True,'wording_version':body.wording_version,'purpose':body.purpose,
        'manifest_sha256':manifest_hash,'destination_id':destination_id,'recorded_at':utcnow().isoformat()}


def set_dto(source_set):
    scope=scope_for(source_set)
    try:
        resolve_destination(source_set.destination_id,scope);availability='provisioned'
    except DRUnavailable:availability='unavailable'
    return {'id':source_set.id,'patient_id':source_set.patient_id,'encounter_id':source_set.encounter_id,
        'task_id':source_set.task_id,'revision':source_set.revision,'source_set_sha256':source_set.manifest_sha256,
        'destination_id':source_set.destination_id,'availability':availability,'scope':scope.model_dump(mode='json'),
        'sources':source_set.manifest,'created_at':source_set.created_at.isoformat()}


def owned(db,actor,id,*,write=False):
    revalidate_actor(db,actor);require_domain(actor,'D11',write)
    binding=db.scalar(select(DRBinding).where(DRBinding.id==id,DRBinding.actor_id==actor.user_id,
        DRBinding.session_id==actor.session_id,DRBinding.organization_id==actor.organization_id,
        DRBinding.facility_id==actor.facility_id).with_for_update().execution_options(populate_existing=True))
    if not binding:fail('DR_BINDING_NOT_FOUND',404)
    if write and binding.state=='quarantined':fail('DR_BINDING_QUARANTINED')
    source_set,task,encounter,caps,auth_hash,blobs=authorize_set(db,actor,binding.source_set_id,write=write)
    if (binding.patient_id,binding.encounter_id,binding.organization_id,binding.facility_id)!=(source_set.patient_id,
            source_set.encounter_id,source_set.organization_id,source_set.facility_id):fail('DR_BINDING_SCOPE_MISMATCH')
    try:destination=resolve_destination(binding.destination_id,scope_for(source_set))
    except DRUnavailable:fail('DR_DESTINATION_UNAVAILABLE',503)
    if destination.fingerprint!=binding.destination_sha256 or destination.workspace_id!=binding.workspace_id:
        fail('DR_DESTINATION_CHANGED',503)
    return binding,source_set,task,encounter,caps,auth_hash,blobs,destination


def binding_dto(binding,source_set,actor,caps,db):
    overview=[]
    snapshots={item.source_id:item.source_snapshot for item in db.scalars(select(DRSourceSetItem).where(DRSourceSetItem.source_set_id==source_set.id)).all()}
    for manifest in source_set.manifest:
        source=db.get(ImagingStudy,manifest['source_id'])
        overview.append({**manifest,'sourcecase_id':manifest['image_sha256'],
            'dataset_provenance':snapshots[manifest['source_id']].get('public_source',{}).get('dataset_provenance'),
            'label':source.modality+' · '+source.body_site})
    return {'schema':'carebalance.dr.browser.v1','id':binding.id,'binding_id':binding.id,
        'workspace_id':binding.workspace_id,'state':binding.state,'capabilities':caps,
        'patient_id':source_set.patient_id,'encounter_id':source_set.encounter_id,'task_id':source_set.task_id,
        'patient_key':patient_key(scope_for(source_set)),'case_ids':[m['image_sha256'] for m in source_set.manifest],
        'sources':overview,'source_set':set_dto(source_set),
        'user':{'id':actor.user_id,'username':actor.username,'display_name':actor.display_name},
        'workspace_url':f'/integrations/dr/{binding.id}/app/','api_prefix':f'/integrations/dr/{binding.id}/api'}


def require_target(method,path,query,body,source_set,caps):
    if '%' in path or '\\' in path or '//' in path or any(p in {'.','..'} for p in path.split('/')):
        fail('DR_TARGET_NOT_ALLOWED',404)
    ids={m['image_sha256'] for m in source_set.manifest}
    if path=='/v1/cases' and method=='GET':suffix='list'
    else:
        match=CASE.fullmatch(path) or IMAGE.fullmatch(path)
        if not match or match[1] not in ids:fail('DR_TARGET_NOT_ALLOWED',404)
        suffix=match[2] or ''
    allowed=({'GET'} if path.startswith('/v1/images/') or suffix in {'','list','comparison','screening-report/print'}
        else {'GET','PUT'} if suffix=='screening-report' else {'POST'} if suffix in {'admission','confirm-image','review'} else {'PUT'})
    if method not in allowed:fail('DR_METHOD_NOT_ALLOWED',405)
    if query and (suffix!='comparison' or set(query)!={'other_image_id'} or query['other_image_id'] not in ids):
        fail('DR_QUERY_NOT_ALLOWED',422)
    if method=='GET':
        if body is not None or 'dr.read' not in caps:fail('DR_READ_REQUIRED',403)
    else:
        if not isinstance(body,dict):fail('DR_BODY_REQUIRED',422)
        required=('dr.grade.confirm' if suffix=='review' and body.get('action')!='CONFIRM_ANNOTATIONS'
            else 'dr.report.prepare' if suffix=='screening-report' else 'dr.prepare')
        if required not in caps:fail('DR_CLINICAL_CAPABILITY_REQUIRED',403)
        if suffix=='screening-report':
            if 'sign' in body and type(body['sign']) is not bool:fail('DR_STRICT_SIGN_BOOLEAN_REQUIRED',422)
            if body.get('sign') is True and 'dr.report.sign' not in caps:fail('DR_VERIFIED_SIGNER_REQUIRED',403)
        if type(body.get('revision')) is not int or body['revision']<0:fail('DR_STRICT_REVISION_REQUIRED',422)
        if suffix=='review' and body.get('action') in {'CORRECT_GRADE','ADJUDICATE_GRADE'}:
            if type(body.get('grade')) is not int or not 0<=body['grade']<=4:fail('DR_STRICT_GRADE_REQUIRED',422)


def is_mutation(operation,payload):
    return operation=='import' or operation=='dispatch' and payload.get('method')!='GET'


@dataclass(frozen=True)
class Reservation:
    binding_id: str
    attempt_id: str
    exchange_id: str
    operation: object
    destination: object
    manifest: tuple


def pending(binding,attempt):
    return JSONResponse(status_code=202,content={'binding_id':binding.id,'attempt_id':attempt.id,
        'outcome':attempt.status,'code':'DR_OUTCOME_UNKNOWN','retry_same_key':True})


def reserve(db,actor,binding,source_set,task,encounter,caps,auth_hash,blobs,destination,operation,key,payload):
    check_key(key);lock(db,'his-dr-workspace:'+source_set.id)
    lock(db,'his-dr-key:'+actor.user_id+':'+actor.session_id+':'+key)
    request_hash=digest({'binding_id':binding.id,'operation':operation,'payload':payload})
    prior=db.scalar(select(DRAttempt).where(DRAttempt.actor_id==actor.user_id,DRAttempt.session_id==actor.session_id,
        DRAttempt.operation_key==key).with_for_update())
    if prior:
        if (prior.binding_id!=binding.id or prior.operation!=operation or prior.request_hash!=request_hash
                or prior.authorization_hash!=auth_hash):fail('DR_IDEMPOTENCY_CONFLICT')
        if prior.status=='succeeded':return deepcopy(prior.response)
        if prior.status=='rejected':
            if prior.response and prior.response.get('receipt') is not None:return deepcopy(prior.response)
            fail(prior.error_code or 'DR_COMMAND_REJECTED',502)
        if prior.status=='quarantined':fail(prior.error_code or 'DR_COMMAND_REJECTED',409)
        if prior.status=='running' and prior.lease_expires_at>utcnow():return pending(binding,prior)
        attempt=prior
    else:
        if is_mutation(operation,payload):
            unresolved=db.scalars(select(DRAttempt).join(DRBinding,DRAttempt.binding_id==DRBinding.id)
                .where(DRBinding.source_set_id==source_set.id,DRAttempt.status.in_(['running','unknown','quarantined']))
                .with_for_update()).all()
            if any(is_mutation(a.operation,a.payload) for a in unresolved):fail('DR_PENDING_RECOVERY_REQUIRED')
        attempt=DRAttempt(id=uid(),binding_id=binding.id,actor_id=actor.user_id,session_id=actor.session_id,
            operation=operation,operation_key=key,request_id=uid(),request_hash=request_hash,
            authorization_hash=auth_hash,payload=payload)
        db.add(attempt)
    exchange_id=uid();attempt.status='running';attempt.lease_id=exchange_id
    attempt.lease_expires_at=utcnow()+timedelta(seconds=55);attempt.error_code=None;attempt.completed_at=None
    context=Context.model_validate_json(canonical({'binding_id':binding.id,'actor_id':actor.user_id,
        'session_id':actor.session_id,'expires_at':(utcnow()+timedelta(seconds=90)).isoformat().replace('+00:00','Z'),
        'capabilities':caps,'scope':scope_for(source_set).model_dump(mode='json')}))
    base={'protocol':'carebalance.dr.v1','request_id':attempt.request_id,'context':context.model_dump(mode='json')}
    if operation=='import':
        message=Import.model_validate_json(canonical({**base,'sources':[{**m,'image_base64':base64.b64encode(blob).decode('ascii')}
            for m,blob in zip(source_set.manifest,blobs)]}))
    elif operation=='dispatch':message=Dispatch.model_validate_json(canonical({**base,**payload}))
    else:message=ReadReport.model_validate_json(canonical({**base,**payload}))
    db.flush();db.add(DRExchange(id=exchange_id,attempt_id=attempt.id,context_snapshot={
        'context':context.model_dump(mode='json'),'authorization_hash':auth_hash,
        'task_version':task.version,'encounter_version':encounter.version},outcome='running'))
    audit(db,actor,'D11',binding.id,'dr.'+operation+'.reserved',{'attempt_id':attempt.id,'exchange_id':exchange_id})
    result=Reservation(binding.id,attempt.id,exchange_id,message,destination,tuple(deepcopy(source_set.manifest)))
    db.commit();db.close()
    return result


def store_exchange(reservation,outcome,receipt,code):
    with SessionLocal.begin() as db:
        exchange=db.get(DRExchange,reservation.exchange_id,with_for_update=True)
        if not exchange or exchange.attempt_id!=reservation.attempt_id or exchange.outcome!='running':fail('DR_EXCHANGE_INCONSISTENT')
        exchange.outcome=outcome;exchange.receipt=receipt;exchange.error_code=code;exchange.completed_at=utcnow()


def quarantine(reservation,code):
    with SessionLocal.begin() as db:
        binding=db.get(DRBinding,reservation.binding_id,with_for_update=True)
        attempt=db.get(DRAttempt,reservation.attempt_id,with_for_update=True)
        exchange=db.get(DRExchange,reservation.exchange_id,with_for_update=True)
        if exchange:exchange.quarantined=True;exchange.quarantine_reason=code
        if attempt and attempt.lease_id==reservation.exchange_id:
            attempt.status='quarantined';attempt.error_code=code;attempt.completed_at=utcnow()
            binding.state='quarantined'
        if binding:db.add(AuditEvent(organization_id=binding.organization_id,facility_id=binding.facility_id,
            actor_id=binding.actor_id,domain='D11',entity_id=binding.id,action='dr.outcome.quarantined',
            details={'attempt_id':reservation.attempt_id,'exchange_id':reservation.exchange_id,'code':code}))


def execute(db,actor,reservation):
    if not isinstance(reservation,Reservation):return reservation
    try:
        receipt=DRClient(reservation.destination,source_manifest=reservation.manifest).exchange(reservation.operation)
        outcome='unknown' if receipt.get('outcome')=='unknown' else 'rejected' if receipt.get('outcome')=='rejected' else 'succeeded'
        code=None if outcome=='succeeded' else 'DR_RECEIVER_'+outcome.upper()
    except DRRejected:receipt=None;outcome='rejected';code='DR_RECEIVER_REJECTED'
    except DRUnknown as exc:
        receipt={'transport_diagnostic':exc.diagnostic} if exc.diagnostic else None
        outcome='unknown';code='DR_OUTCOME_UNKNOWN'
    except Exception:receipt=None;outcome='unknown';code='DR_OUTCOME_UNKNOWN'
    store_exchange(reservation,outcome,receipt,code)
    try:
        is_write=isinstance(reservation.operation,Import) or isinstance(reservation.operation,Dispatch) and reservation.operation.method!='GET'
        binding,source_set,task,encounter,caps,auth_hash,blobs,destination=owned(db,actor,reservation.binding_id,write=is_write)
        attempt=db.get(DRAttempt,reservation.attempt_id,with_for_update=True)
        exchange=db.get(DRExchange,reservation.exchange_id)
        if attempt.lease_id!=reservation.exchange_id or attempt.lease_expires_at<=utcnow():fail('DR_LEASE_EXPIRED_OR_REPLACED')
        snapshot=exchange.context_snapshot
        if (auth_hash!=snapshot['authorization_hash'] or is_write and
                (task.version!=snapshot['task_version'] or encounter.version!=snapshot['encounter_version'])):
            fail('DR_CONTEXT_CHANGED')
        attempt.status=outcome;attempt.error_code=code;attempt.completed_at=utcnow()
        if outcome=='succeeded':
            if isinstance(reservation.operation,Import):binding.state='imported'
            if isinstance(reservation.operation,ReadReport):
                s=receipt['snapshot']
                db.add(DRReportReceipt(binding_id=binding.id,attempt_id=attempt.id,source_set_id=source_set.id,
                    case_id=s['case_id'],case_revision=s['case_revision'],snapshot_sha256=receipt['snapshot_sha256'],receipt=receipt))
            response={'binding_id':binding.id,'attempt_id':attempt.id,'outcome':outcome,'receipt':receipt}
            attempt.response=response
        elif outcome=='unknown':
            if binding.state!='imported':binding.state='unknown'
            response=pending(binding,attempt)
        else:
            response={'binding_id':binding.id,'attempt_id':attempt.id,'outcome':outcome,'receipt':receipt,'code':code}
            attempt.response=response
        audit(db,actor,'D11',binding.id,'dr.'+attempt.operation+'.'+outcome,{'attempt_id':attempt.id,'exchange_id':exchange.id})
        db.commit()
    except HTTPException as exc:
        db.rollback();db.close();quarantine(reservation,exc.detail.get('code','DR_CONTEXT_DENIED') if isinstance(exc.detail,dict) else 'DR_CONTEXT_DENIED')
        raise
    if outcome=='rejected' and receipt is None:fail(code,502)
    return response


@router.get('/sources')
def sources(patient_id:str,encounter_id:str,actor=Depends(current_actor),db=Depends(get_db,scope='function')):
    revalidate_actor(db,actor);require_domain(actor,'D11');require(actor,'documents.content');require(actor,'documents.export')
    scoped_patient(db,actor,patient_id,True);encounter=scoped_encounter(db,actor,encounter_id,True)
    if encounter.patient_id!=patient_id:fail('DR_ENCOUNTER_PATIENT_MISMATCH',404)
    rows=db.scalars(select(DRSourceProvenance).where(DRSourceProvenance.organization_id==actor.organization_id,
        DRSourceProvenance.facility_id==actor.facility_id,DRSourceProvenance.patient_id==patient_id,
        DRSourceProvenance.encounter_id==encounter_id).order_by(DRSourceProvenance.created_at)).all()
    result=[]
    for p in rows:
        try:source,provenance,data,snapshot=authorize_source(db,actor,p.source_id,patient_id,encounter_id,p.source_version,p.id)
        except HTTPException:continue
        result.append({'source_id':source.id,'source_version':source.version,'provenance_id':p.id,
            'laterality':p.laterality,'modality':p.modality,'capture_time':p.capture_time,'image_sha256':p.image_sha256,
            'label':source.modality+' · '+source.body_site,'source_origin':p.source_origin,
            'dataset_provenance':p.dataset_provenance,
            'preview_url':f'/api/v2/integrations/dr/sources/{source.id}/preview?provenance_id={p.id}'})
    return {'items':result}


@router.get('/capability-grants/{id}/history')
def grant_history(id:str,actor=Depends(current_actor),db=Depends(get_db,scope='function')):
    revalidate_actor(db,actor)
    admin='identity.admin' in actor.permissions
    if not admin:require_domain(actor,'D11')
    query=select(DRCapabilityGrant).where(DRCapabilityGrant.id==id,
        DRCapabilityGrant.organization_id==actor.organization_id,DRCapabilityGrant.facility_id==actor.facility_id)
    if not admin:query=query.where(DRCapabilityGrant.user_id==actor.user_id)
    grant=db.scalar(query)
    if not grant:fail('DR_GRANT_NOT_FOUND',404)
    rows=db.scalars(select(DRCapabilityGrantEvent).where(DRCapabilityGrantEvent.grant_id==grant.id,
        DRCapabilityGrantEvent.organization_id==actor.organization_id,DRCapabilityGrantEvent.facility_id==actor.facility_id)
        .order_by(DRCapabilityGrantEvent.grant_version)).all()
    return {'grant_id':grant.id,'user_id':grant.user_id,'events':[{'id':row.id,'version':row.grant_version,
        'operation':row.operation,'old_snapshot':row.old_snapshot,'new_snapshot':row.new_snapshot,
        'database_principal':row.database_principal,'actor_user_id':None,'created_at':row.created_at.isoformat()} for row in rows]}


@router.get('/sources/{id}/preview',include_in_schema=False)
def preview(id:str,provenance_id:str,actor=Depends(current_actor),db=Depends(get_db,scope='function')):
    revalidate_actor(db,actor);require_domain(actor,'D11');require(actor,'documents.content');require(actor,'documents.export')
    p=db.scalar(select(DRSourceProvenance).where(DRSourceProvenance.id==provenance_id,
        DRSourceProvenance.source_id==id,DRSourceProvenance.organization_id==actor.organization_id,
        DRSourceProvenance.facility_id==actor.facility_id))
    if not p:fail('DR_SOURCE_NOT_FOUND',404)
    scoped_patient(db,actor,p.patient_id);scoped_encounter(db,actor,p.encounter_id)
    source,p,data,snapshot=authorize_source(db,actor,id,p.patient_id,p.encounter_id,p.source_version,p.id)
    return Response(data,media_type=source.file_mime,headers={'X-Content-Type-Options':'nosniff'})


@router.post('/source-sets')
def create_source_set(body:SourceSetInput,idempotency_key:str=Header(default='',alias='Idempotency-Key'),
                      actor=Depends(current_actor),db=Depends(get_db,scope='function')):
    check_key(idempotency_key)
    authorize_task(db,actor,body.patient_id,body.encounter_id,body.task_id,write=True)
    lock(db,'his-dr-key:'+actor.user_id+':'+actor.session_id+':'+idempotency_key)
    request_hash=digest(body.model_dump(mode='json'))
    old=db.scalar(select(DRSourceSet).where(DRSourceSet.actor_id==actor.user_id,
        DRSourceSet.session_id==actor.session_id,DRSourceSet.operation_key==idempotency_key))
    if old:
        if old.request_hash!=request_hash:fail('DR_IDEMPOTENCY_CONFLICT')
        authorize_set(db,actor,old.id,write=True)
        return set_dto(old)
    if len({s.source_id for s in body.sources})!=len(body.sources):fail('DR_DUPLICATE_SOURCE',422)
    reference=uid();consent=consent_receipt(body.transfer_consent,actor,reference=reference,destination_id=body.destination_id)
    manifest=[];selected=[]
    for selection in body.sources:
        source,p,data,snapshot=authorize_source(db,actor,selection.source_id,body.patient_id,body.encounter_id,
            selection.source_version,selection.provenance_id)
        manifest.append({'source_id':source.id,'source_version':source.version,'source_sha256':digest(snapshot),
            'image_sha256':p.image_sha256,'byte_size':len(data),'media_type':source.file_mime,'laterality':p.laterality,
            'modality':p.modality,'source_origin':p.source_origin,'consent_reference':reference,'capture_time':p.capture_time})
        selected.append((source,p,snapshot))
    if len({m['image_sha256'] for m in manifest})!=len(manifest):fail('DR_DUPLICATE_IMAGE',422)
    validate_public_group([p for source,p,snapshot in selected])
    if any(m['source_origin']=='PUBLIC' for m in manifest) and body.transfer_consent.wording_version!='carebalance.dr-transfer.v2':
        fail('DR_PUBLIC_TRANSFER_WORDING_REQUIRED',422)
    consent['manifest_sha256']=digest(manifest)
    row=DRSourceSet(id=uid(),organization_id=actor.organization_id,facility_id=actor.facility_id,
        patient_id=body.patient_id,encounter_id=body.encounter_id,task_id=body.task_id,actor_id=actor.user_id,
        session_id=actor.session_id,operation_key=idempotency_key,request_hash=request_hash,revision=1,
        manifest_sha256=digest(manifest),manifest=manifest,consent_snapshot=consent,destination_id=body.destination_id)
    db.add(row);db.flush()
    for i,(source,p,snapshot) in enumerate(selected):
        db.add(DRSourceSetItem(source_set_id=row.id,position=i,source_id=source.id,source_version=source.version,
            provenance_id=p.id,source_snapshot=snapshot,source_sha256=digest(snapshot)))
    audit(db,actor,'D11',row.id,'dr.source-set.created',{'source_set_sha256':row.manifest_sha256,'consent_reference':reference})
    db.flush()
    return set_dto(row)


@router.get('/source-sets')
def source_sets(patient_id:str,encounter_id:str,actor=Depends(current_actor),db=Depends(get_db,scope='function')):
    revalidate_actor(db,actor);require_domain(actor,'D11');require(actor,'documents.content');require(actor,'documents.export')
    scoped_patient(db,actor,patient_id);encounter=scoped_encounter(db,actor,encounter_id)
    if encounter.patient_id!=patient_id:fail('DR_ENCOUNTER_PATIENT_MISMATCH',404)
    rows=db.scalars(select(DRSourceSet).where(DRSourceSet.organization_id==actor.organization_id,
        DRSourceSet.facility_id==actor.facility_id,DRSourceSet.patient_id==patient_id,
        DRSourceSet.encounter_id==encounter_id).order_by(DRSourceSet.created_at)).all()
    result=[]
    for row in rows:
        try:authorize_set(db,actor,row.id)
        except HTTPException:continue
        result.append(set_dto(row))
    return {'items':result}


@router.get('/source-sets/{id}')
def get_source_set(id:str,actor=Depends(current_actor),db=Depends(get_db,scope='function')):
    source_set=authorize_set(db,actor,id)[0];result=set_dto(source_set)
    rows=db.scalars(select(DRBinding).where(DRBinding.source_set_id==source_set.id,
        DRBinding.actor_id==actor.user_id,DRBinding.session_id==actor.session_id,
        DRBinding.organization_id==actor.organization_id,DRBinding.facility_id==actor.facility_id)
        .order_by(DRBinding.created_at)).all()
    result['bindings']=[]
    for binding in rows:
        unresolved=db.scalars(select(DRAttempt).where(DRAttempt.binding_id==binding.id,
            DRAttempt.status.in_(['running','unknown'])).order_by(DRAttempt.created_at)).all()
        commands=[{'attempt_id':a.id,'operation':a.operation,'status':a.status} for a in unresolved if is_mutation(a.operation,a.payload)]
        result['bindings'].append({'id':binding.id,'state':binding.state,
            'workspace_url':f'/integrations/dr/{binding.id}/app/','pending':commands[0] if commands else None})
    return result


@router.post('/source-sets/{id}/bindings')
def import_binding(id:str,body:BindingInput,idempotency_key:str=Header(default='',alias='Idempotency-Key'),
                   actor=Depends(current_actor),db=Depends(get_db,scope='function')):
    source_set,task,encounter,caps,auth_hash,blobs=authorize_set(db,actor,id,write=True)
    try:destination=resolve_destination(source_set.destination_id,scope_for(source_set))
    except DRUnavailable:fail('DR_DESTINATION_UNAVAILABLE',503)
    check_key(idempotency_key);lock(db,'his-dr-workspace:'+source_set.id)
    binding=db.scalar(select(DRBinding).where(DRBinding.source_set_id==id,DRBinding.actor_id==actor.user_id,
        DRBinding.session_id==actor.session_id).with_for_update())
    if not binding:
        consent=consent_receipt(body.transfer_consent,actor,reference=uid(),manifest_hash=source_set.manifest_sha256,
            destination_id=source_set.destination_id,public_required=any(m['source_origin']=='PUBLIC' for m in source_set.manifest))
        binding=DRBinding(id=uid(),source_set_id=id,organization_id=actor.organization_id,facility_id=actor.facility_id,
            patient_id=source_set.patient_id,encounter_id=source_set.encounter_id,actor_id=actor.user_id,
            session_id=actor.session_id,destination_id=source_set.destination_id,destination_sha256=destination.fingerprint,
            workspace_id=destination.workspace_id,consent_snapshot=consent,state='reserved')
        db.add(binding);db.flush()
    elif (not body.transfer_consent.confirmed or destination.fingerprint!=binding.destination_sha256):
        fail('DR_BINDING_CONSENT_OR_DESTINATION_CHANGED')
    if any(m['source_origin']=='PUBLIC' for m in source_set.manifest) and body.transfer_consent.wording_version!='carebalance.dr-transfer.v2':
        fail('DR_PUBLIC_TRANSFER_WORDING_REQUIRED',422)
    if binding.state=='quarantined':fail('DR_BINDING_QUARANTINED')
    if 'dr.prepare' not in caps:fail('DR_PREPARATION_REQUIRED',403)
    return execute(db,actor,reserve(db,actor,binding,source_set,task,encounter,caps,auth_hash,blobs,destination,
        'import',idempotency_key,body.model_dump(mode='json')))


@router.get('/bindings/{id}')
def get_binding(id:str,actor=Depends(current_actor),db=Depends(get_db,scope='function')):
    binding,source_set,task,encounter,caps,*_=owned(db,actor,id)
    result=binding_dto(binding,source_set,actor,caps,db)
    unresolved=db.scalars(select(DRAttempt).where(DRAttempt.binding_id==binding.id,
        DRAttempt.status.in_(['running','unknown'])).order_by(DRAttempt.created_at)).all()
    pending_commands=[{'attempt_id':a.id,'operation':a.operation,'status':a.status} for a in unresolved if is_mutation(a.operation,a.payload)]
    result['pending']=pending_commands[0] if pending_commands else None
    patient=db.get(Patient,source_set.patient_id);encounter=db.get(Encounter,source_set.encounter_id)
    result['patient']={'id':patient.id,'display_name':patient.display_name}
    result['encounter']={'id':encounter.id,'kind':encounter.kind}
    return result


@router.post('/bindings/{id}/read-report')
def read_report(id:str,body:ReportRead,idempotency_key:str=Header(default='',alias='Idempotency-Key'),
                actor=Depends(current_actor),db=Depends(get_db,scope='function')):
    values=owned(db,actor,id);binding,source_set,task,encounter,caps,auth_hash,blobs,destination=values
    if body.case_id not in {m['image_sha256'] for m in source_set.manifest}:fail('DR_CASE_NOT_FOUND',404)
    return execute(db,actor,reserve(db,actor,binding,source_set,task,encounter,caps,auth_hash,blobs,destination,
        'read_report',idempotency_key,body.model_dump(mode='json')))


@router.post('/bindings/{id}/recover')
def recover(id:str,actor=Depends(current_actor),db=Depends(get_db,scope='function')):
    binding,source_set,task,encounter,caps,*_=owned(db,actor,id,write=True)
    attempts=db.scalars(select(DRAttempt).where(DRAttempt.binding_id==binding.id,
        DRAttempt.status.in_(['running','unknown'])).order_by(DRAttempt.created_at)).all()
    return {'binding_id':binding.id,'commands':[{'attempt_id':a.id,'operation':a.operation,'key':a.operation_key,
        'body':a.payload,'request_id':a.request_id,'lease_expires_at':a.lease_expires_at.isoformat(),
        'retry_allowed':a.status=='unknown' or a.lease_expires_at<=utcnow(),'status':a.status} for a in attempts if is_mutation(a.operation,a.payload)],
        'automatic_replay':False}


def static_file(name):
    """Only an operator-supplied exact build manifest is a static authority."""
    if (not name or '%' in name or '\\' in name or name.startswith('/') or
            any(part in {'','.','..'} for part in name.split('/'))):fail('DR_ASSET_NOT_FOUND',404)
    raw=os.getenv('HIS_DR_WEB_MANIFEST','');manifest_path=Path(raw)
    if not raw or not manifest_path.is_absolute() or manifest_path.is_symlink():fail('DR_FRONTEND_UNAVAILABLE',503)
    try:
        if manifest_path.stat().st_size>131072:raise ValueError('Manifest size')
        manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
        if set(manifest)!={'schema','root','assets'} or manifest['schema']!='carebalance.dr.web.v1':raise ValueError('Manifest schema')
        root=Path(manifest['root'])
        if not root.is_absolute() or root.is_symlink() or not isinstance(manifest['assets'],dict):raise ValueError('Manifest root')
        expected=manifest['assets'].get(name)
        if not isinstance(expected,str) or not re.fullmatch('[0-9a-f]{64}',expected):fail('DR_ASSET_NOT_FOUND',404)
        candidate=root/name
        if any(p.is_symlink() for p in [candidate,*candidate.parents]) or not candidate.resolve().is_relative_to(root.resolve()):raise ValueError('Asset path')
        data=candidate.read_bytes()
        if hashlib.sha256(data).hexdigest()!=expected:raise ValueError('Asset checksum')
        return data
    except (OSError,ValueError,KeyError,TypeError,RecursionError):fail('DR_FRONTEND_UNAVAILABLE',503)


@browser_router.get('/{id}/app/',include_in_schema=False)
def workspace(id:str,actor=Depends(current_actor),db=Depends(get_db,scope='function')):
    binding,source_set,*_=owned(db,actor,id)
    if binding.state!='imported':fail('DR_IMPORT_REQUIRED',409)
    data=static_file('index.html').decode('utf-8')
    prefix=f'/integrations/dr/{binding.id}'
    context={'schema':'carebalance.dr.browser.v1','binding_id':binding.id,'workspace_id':binding.workspace_id,
        'api_prefix':prefix+'/api','context_url':'/api/v2/integrations/dr/bindings/'+binding.id,
        'return_url':'/domains/D11?'+urlencode({'patient_id':source_set.patient_id,'encounter_id':source_set.encounter_id,
            'record':source_set.manifest[0]['source_id']})}
    injected='<script type="application/json" id="carebalance-dr-context">'+json.dumps(context,separators=(',',':')).replace('<','\\u003c')+'</script>'
    if '</head>' not in data:fail('DR_FRONTEND_UNAVAILABLE',503)
    data=data.replace('./assets/',prefix+'/assets/assets/').replace('</head>',injected+'</head>',1)
    return HTMLResponse(data)


@browser_router.get('/{id}/assets/{asset_path:path}',include_in_schema=False)
def asset(id:str,asset_path:str,request:Request,actor=Depends(current_actor),db=Depends(get_db,scope='function')):
    owned(db,actor,id)
    if b'%' in request.scope.get('raw_path',b''):fail('DR_ASSET_NOT_FOUND',404)
    data=static_file(asset_path)
    return Response(data,media_type=mimetypes.guess_type(asset_path)[0] or 'application/octet-stream')


@browser_router.api_route('/{id}/api/{clinical_path:path}',methods=['GET','POST','PUT'],include_in_schema=False)
async def clinical_proxy(id:str,clinical_path:str,request:Request,
                         actor=Depends(current_actor),db=Depends(get_db,scope='function')):
    # Stream limit precedes JSON parsing. Never forward browser headers/cookies.
    raw=bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw)>2097152:fail('DR_BROWSER_BODY_TOO_LARGE',413)
    if b'%' in request.scope.get('raw_path',b''):fail('DR_TARGET_NOT_ALLOWED',404)
    body=None
    if request.method!='GET':
        try:
            if request.headers.get('content-type','').split(';')[0]!='application/json':raise ValueError('JSON required')
            body=strict_json(raw)
            if not isinstance(body,dict):raise ValueError('Object required')
        except (ValueError,UnicodeDecodeError,RecursionError):fail('DR_INVALID_BROWSER_BODY',422)
    elif raw:fail('DR_READ_BODY_NOT_ALLOWED',422)
    pairs=list(request.query_params.multi_items())
    if len({k for k,v in pairs})!=len(pairs):fail('DR_DUPLICATE_QUERY',422)
    query=dict(pairs);path='/'+clinical_path
    from starlette.concurrency import run_in_threadpool
    return await run_in_threadpool(proxy_action,id,path,query,body,
        request.headers.get('Idempotency-Key',''),request.method,actor,db)


def proxy_action(id,path,query,body,key,method,actor,db):
    values=owned(db,actor,id,write=method!='GET')
    binding,source_set,task,encounter,caps,auth_hash,blobs,destination=values
    if binding.state!='imported':fail('DR_IMPORT_REQUIRED')
    require_target(method,path,query,body,source_set,caps)
    if body is not None:body['reviewer']=actor.user_id
    payload={'method':method,'path':path,'query':query,'body':body}
    key=key if method!='GET' else uid()
    result=execute(db,actor,reserve(db,actor,binding,source_set,task,encounter,caps,auth_hash,blobs,destination,
        'dispatch',key,payload))
    if isinstance(result,Response):return result
    receipt=result.get('receipt')
    if receipt is None:return JSONResponse(result,status_code=502)
    return clinical_response(receipt,path)


def clinical_response(receipt,path):
    data=base64.b64decode(receipt['body_base64'],validate=True)
    if receipt['content_type']=='text/html' and path.endswith('/screening-report/print'):
        note='<aside role="note" style="border-bottom:1px solid #bbb;padding:10px 0;margin-bottom:16px">Stored report · current review freshness is not assessed in this print view.</aside>'
        html=data.decode('utf-8')
        html=re.sub(r'(<body[^>]*>)',lambda match:match[1]+note,html,count=1,flags=re.I)
        data=html.encode('utf-8')
    return Response(data,status_code=receipt['status_code'],media_type=receipt['content_type'])


@browser_router.get('/{id}/print/{case_id}',include_in_schema=False)
def print_report(id:str,case_id:str,actor=Depends(current_actor),db=Depends(get_db,scope='function')):
    binding,source_set,task,encounter,caps,auth_hash,blobs,destination=owned(db,actor,id)
    path=f'/v1/cases/{case_id}/screening-report/print';require_target('GET',path,{},None,source_set,caps)
    payload={'method':'GET','path':path,'query':{},'body':None}
    result=execute(db,actor,reserve(db,actor,binding,source_set,task,encounter,caps,auth_hash,blobs,destination,'dispatch',uid(),payload))
    if isinstance(result,Response):return result
    receipt=result.get('receipt')
    if receipt is None:return JSONResponse(result,status_code=502)
    return clinical_response(receipt,path)
