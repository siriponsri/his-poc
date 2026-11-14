"""Server-owned fixed-scope DR destinations and bounded signed transport."""
from __future__ import annotations

import base64
from dataclasses import dataclass, field
from datetime import datetime,timedelta
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import secrets
import re
from urllib.parse import urlsplit

import httpx

from .dr_protocol import (AUDIENCE, ClinicalEnvelope, Dispatch, Import, MAX_BODY_BYTES,
    MAX_RESPONSE_BYTES, ReadReport, ReviewFreshness, ReviewWitness, SourceManifest, WorkspaceScope, canonical, digest, now_seconds, sign_request, utc, validate_context)


class DRUnavailable(ValueError):
    pass


class DRRejected(ValueError):
    pass


class DRUnknown(ValueError):
    def __init__(self,message,diagnostic=None):
        super().__init__(message)
        self.diagnostic=diagnostic


def strict_json(raw):
    def pairs(items):
        result={}
        for key,value in items:
            if key in result:raise ValueError('Duplicate JSON field')
            result[key]=value
        return result
    def invalid_constant(value):raise ValueError('Non-finite JSON number')
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=invalid_constant)


@dataclass(frozen=True)
class Destination:
    id: str
    origin: str
    key: bytes = field(repr=False)
    scope: WorkspaceScope
    workspace_id: str

    def __post_init__(self):
        parsed = urlsplit(self.origin)
        try:
            address = ipaddress.ip_address(parsed.hostname or '')
            port = parsed.port
        except ValueError:
            raise DRUnavailable('Literal loopback destination required') from None
        if (parsed.scheme != 'http' or not address.is_loopback or not port or parsed.username
                or parsed.password or parsed.path or parsed.query or parsed.fragment or len(self.key) < 32
                or self.workspace_id != 'cb-' + digest(self.scope)[:32]):
            raise DRUnavailable('Invalid fixed DR destination')

    @property
    def fingerprint(self):
        return digest({'id':self.id,'origin':self.origin,'key_sha256':hashlib.sha256(self.key).hexdigest(),
                       'scope':self.scope.model_dump(mode='json'),'workspace_id':self.workspace_id})


def destinations() -> dict[str, Destination]:
    if os.getenv('HIS_DR_ENABLED') != 'true':
        raise DRUnavailable('DR bridge disabled')
    raw = os.getenv('HIS_DR_DESTINATIONS_FILE', '')
    path = Path(raw)
    if not raw or not path.is_absolute() or path.is_symlink() or any(p.is_symlink() for p in path.parents):
        raise DRUnavailable('Private absolute destination registry required')
    try:
        if path.stat().st_size > 65536 or os.name!='nt' and path.stat().st_mode & 0o077:
            raise DRUnavailable('Destination registry exceeds limit')
        value = strict_json(path.read_text(encoding='utf-8'))
        if set(value) != {'version','destinations'} or type(value['version']) is not int or value['version'] != 1:
            raise ValueError('Registry version')
        if not isinstance(value['destinations'], list) or len(value['destinations']) > 32:
            raise ValueError('Registry destinations')
        result = {}
        for entry in value['destinations']:
            if set(entry) != {'id','origin','key','scope','workspace_id'} or not all(isinstance(entry[k],str) for k in ('id','origin','key','workspace_id')):
                raise ValueError('Destination fields')
            scope = WorkspaceScope.model_validate_json(canonical(entry['scope']))
            if entry['id'] in result or not re.fullmatch('[A-Za-z0-9_-]{1,64}',entry['id']):
                raise ValueError('Destination identity')
            result[entry['id']] = Destination(entry['id'],entry['origin'],entry['key'].encode(),scope,entry['workspace_id'])
        return result
    except (OSError, ValueError, TypeError, KeyError, RecursionError):
        raise DRUnavailable('DR destination registry unavailable') from None


def resolve_destination(id: str, scope: WorkspaceScope) -> Destination:
    destination = destinations().get(id)
    if destination is None or destination.scope != scope:
        raise DRUnavailable('Exact source-set destination is not provisioned')
    return destination


class DRClient:
    def __init__(self, destination: Destination, transport=None,source_manifest=None):
        self.destination = destination
        self.transport = transport
        self.source_manifest=tuple(source_manifest) if source_manifest is not None else None
        if self.source_manifest is not None:
            parsed=[SourceManifest.model_validate_json(canonical(m)).model_dump(mode='json') for m in self.source_manifest]
            if not 1<=len(parsed)<=8 or digest(parsed)!=destination.scope.source_set_sha256:
                raise DRUnavailable('Frozen source manifest mismatch')

    def exchange(self, operation: Import | Dispatch | ReadReport) -> dict:
        try:validate_context(operation.context,self.destination.scope,now_seconds())
        except ValueError:raise DRRejected('Expired or mismatched DR context') from None
        if operation.context.scope != self.destination.scope:
            raise DRRejected('Destination scope mismatch')
        path = '/api/connector/dr/' + ('import' if isinstance(operation,Import) else 'dispatch' if isinstance(operation,Dispatch) else 'read-report')
        raw = canonical(operation)
        if len(raw)>MAX_BODY_BYTES:
            raise DRRejected('DR request exceeds limit')
        timestamp = now_seconds(); nonce = secrets.token_urlsafe(32)
        headers = {'Content-Type':'application/json','X-CareBalance-Timestamp':str(timestamp),
            'X-CareBalance-Nonce':nonce,'X-CareBalance-Audience':AUDIENCE,
            'X-CareBalance-Signature':sign_request(self.destination.key,method='POST',path=path,
                timestamp=timestamp,nonce=nonce,audience=AUDIENCE,body=raw)}
        try:
            with httpx.Client(transport=self.transport,trust_env=False,follow_redirects=False,
                              timeout=httpx.Timeout(40,connect=5)) as client:
                with client.stream('POST',self.destination.origin+path,content=raw,headers=headers) as response:
                    data = bytearray()
                    for chunk in response.iter_bytes():
                        data.extend(chunk)
                        if len(data)>MAX_RESPONSE_BYTES*2:
                            raise DRUnknown('DR response exceeds limit')
                    if response.status_code in {400,401,403,404,405,409,413,415,422}:
                        raise DRRejected('DR request rejected')
                    if response.status_code not in {200,202} or response.headers.get('set-cookie'):
                        raise DRUnknown('DR response outcome unknown')
                    if response.headers.get('content-type','').split(';')[0] != 'application/json':
                        raise DRUnknown('DR response representation invalid')
                    value = strict_json(data)
        except (DRRejected,DRUnknown):
            raise
        except (httpx.HTTPError, ValueError, UnicodeDecodeError, RecursionError, TypeError):
            raise DRUnknown('DR response outcome unknown') from None
        try:
            if isinstance(operation,ReadReport):
                return self.validate_report(value,operation)
            envelope = ClinicalEnvelope.model_validate_json(canonical(value))
            if (envelope.request_id!=operation.request_id or envelope.binding_id!=operation.context.binding_id
                    or envelope.workspace_id!=self.destination.workspace_id):
                raise ValueError('Envelope identity')
            decoded = base64.b64decode(envelope.body_base64,validate=True)
            if len(decoded)>MAX_RESPONSE_BYTES or hashlib.sha256(decoded).hexdigest()!=envelope.response_sha256:
                raise ValueError('Envelope checksum')
            if envelope.content_type not in {'application/json','image/png','image/jpeg','text/html'}:
                raise ValueError('Envelope representation')
            if isinstance(operation,Dispatch):self.validate_dispatch(envelope,decoded,operation)
            if isinstance(operation,Import) and envelope.outcome=='succeeded':
                imported = json.loads(decoded)
                if (set(imported)!={'workspace_id','patient_key','source_set','cases','manual_review_only','inference_enabled'}
                        or imported['workspace_id']!=self.destination.workspace_id
                        or imported['source_set']!=operation.context.scope.model_dump(mode='json')
                        or imported['cases']!=[{'case_id':s.image_sha256,'source':s.manifest()} for s in operation.sources]
                        or imported['manual_review_only'] is not True or imported['inference_enabled'] is not False
                        or imported['patient_key']!=patient_key(operation.context.scope)):
                    raise ValueError('Import receipt identity')
            return envelope.model_dump(mode='json')
        except (ValueError,TypeError,KeyError,RecursionError):
            raise DRUnknown('DR receipt invalid',{'status_code':response.status_code,'content_type':response.headers.get('content-type',''),
                'body_length':len(data),'body_sha256':hashlib.sha256(data).hexdigest()}) from None

    def validate_dispatch(self,envelope,decoded,operation):
        path=operation.path
        if envelope.outcome!='succeeded':
            if envelope.content_type!='application/json':raise ValueError('Rejection representation')
            strict_json(decoded)
            return
        image=re.fullmatch(r'/v1/images/([0-9a-f]{64})(?:/(display|analysis-area|mask-overlay))?',path)
        if image:
            if envelope.content_type not in {'image/png','image/jpeg'}:raise ValueError('Image route MIME')
            if (envelope.content_type=='image/png' and not decoded.startswith(b'\x89PNG\r\n\x1a\n')
                    or envelope.content_type=='image/jpeg' and not decoded.startswith(b'\xff\xd8\xff')):
                raise ValueError('Image bytes/MIME')
            originals={m['image_sha256']:m for m in self.source_manifest or ()}
            if image[2] is None and (image[1] not in originals or envelope.content_type!=originals[image[1]]['media_type'] or hashlib.sha256(decoded).hexdigest()!=image[1]):
                raise ValueError('Original image identity')
            return
        if path.endswith('/screening-report/print'):
            if envelope.content_type!='text/html':raise ValueError('Print route MIME')
            if not decoded.lstrip().lower().startswith((b'<!doctype html',b'<html')):raise ValueError('Print representation')
            return
        if envelope.content_type!='application/json':raise ValueError('Clinical JSON route MIME')
        value=strict_json(decoded)
        members={m['image_sha256']:m for m in self.source_manifest or ()}
        if path=='/v1/cases':
            if not members or not isinstance(value,list) or len(value)!=len(members):raise ValueError('Case list membership')
            ids=[]
            for case in value:
                self.validate_case(case,members);ids.append(case['image_id'])
            if len(set(ids))!=len(ids) or set(ids)!=set(members):raise ValueError('Case list identity')
            return
        target=re.fullmatch(r'/v1/cases/([0-9a-f]{64})(?:/(.*))?',path)
        if target is None:raise ValueError('Unknown response target')
        case_id,suffix=target[1],target[2]
        if suffix=='screening-report':
            if (not isinstance(value,dict) or set(value)!={'revision','screening_report'}
                    or type(value['revision']) is not int or value['revision']<0):raise ValueError('Report response')
            report=value['screening_report']
            if report is not None:
                if (not isinstance(report,dict) or not isinstance(report.get('form'),dict)
                        or report['form'].get('hn')!=patient_key(operation.context.scope)
                        or report.get('source_set_sha256')!=operation.context.scope.source_set_sha256):
                    raise ValueError('Report response patient/source identity')
            return
        if suffix=='comparison':
            if not isinstance(value,dict) or type(value.get('eligible')) is not bool:raise ValueError('Comparison response')
            if value['eligible']:
                visits=value.get('visits')
                if (value.get('patient_key')!=patient_key(operation.context.scope) or not isinstance(visits,list)
                        or len(visits)!=2 or case_id not in {v.get('image_id') for v in visits if isinstance(v,dict)}):
                    raise ValueError('Comparison patient/case identity')
                ids=[v.get('image_id') for v in visits if isinstance(v,dict)]
                if not members or len(ids)!=2 or len(set(ids))!=2 or not set(ids)<=set(members):raise ValueError('Comparison member identity')
                other=operation.query.get('other_image_id')
                if other and set(ids)!={case_id,other}:raise ValueError('Comparison target identity')
            return
        self.validate_case(value,members or {case_id:None},expected=case_id)

    def validate_case(self,value,members,expected=None):
        if (not isinstance(value,dict) or not isinstance(value.get('image_id'),str)
                or value['image_id'] not in members or expected is not None and value['image_id']!=expected
                or type(value.get('revision')) is not int or value['revision']<0):
            raise ValueError('Case response identity')
        if value.get('patient_key') not in (None,patient_key(self.destination.scope)):
            raise ValueError('Case response patient')
        visit=value.get('visit_context')
        if visit is not None and (not isinstance(visit,dict) or visit.get('visit_key') not in (None,self.destination.scope.encounter_id)):
            raise ValueError('Case response encounter')
        for name in ('image_sha256','source_sha256'):
            if value.get(name) is not None and value[name]!=value['image_id']:raise ValueError('Case source bytes')
        source=members[value['image_id']]
        if source is not None:
            admission=value.get('admission')
            if value.get('source_origin') not in (None,source['source_origin']):raise ValueError('Case source origin')
            if isinstance(admission,dict):
                if admission.get('source_origin') not in (None,source['source_origin']):raise ValueError('Admission source origin')
                if admission.get('retinal_modality') not in (None,source['modality']):raise ValueError('Admission retinal modality')
        if source is not None and value.get('patient_key') is not None:
            eye='LEFT' if source['laterality']=='L' else 'RIGHT'
            if value.get('laterality')!=eye:raise ValueError('Confirmed case eye identity')

    def validate_report(self,value,operation: ReadReport):
        # Frozen receiver read-report shape; freshness is checked separately from
        # immutable clinical report content, never folded into its report hash.
        if not isinstance(value,dict):raise DRUnknown('DR report receipt invalid')
        required={'protocol','request_id','binding_id','workspace_id','patient_key','snapshot_sha256','reader','snapshot','review_freshness'}
        if set(value)!=required:
            raise DRUnknown('DR report receipt invalid')
        snapshot=value['snapshot']
        if (value['protocol']!=operation.protocol or value['request_id']!=operation.request_id
                or value['binding_id']!=operation.context.binding_id
                or value['workspace_id']!=self.destination.workspace_id
                or value['patient_key']!=patient_key(operation.context.scope)
                or not isinstance(snapshot,dict) or digest(snapshot)!=value['snapshot_sha256']
                or snapshot.get('case_id')!=operation.case_id
                or snapshot.get('source_set')!=operation.context.scope.model_dump(mode='json')
                or snapshot.get('workspace_id')!=self.destination.workspace_id
                or snapshot.get('report_sha256')!=digest(snapshot.get('report'))):
            raise DRUnknown('DR report receipt identity invalid')
        try:
            if set(snapshot)!={'workspace_id','source_set','source_manifest','case_id','case_revision','report','report_sha256','report_state','signer','amendment_provenance'}:
                raise ValueError('Snapshot fields')
            if type(snapshot['case_revision']) is not int or snapshot['case_revision']<0:raise ValueError('Case revision')
            reader={'identity_assurance':'VERIFIED_HIS_SESSION','actor_id':operation.context.actor_id,
                'session_id':operation.context.session_id,'binding_id':operation.context.binding_id,
                'verified_capabilities':list(operation.context.capabilities)}
            if value['reader']!=reader:raise ValueError('Reader identity')
            manifests=[SourceManifest.model_validate_json(canonical(m)) for m in snapshot['source_manifest']]
            if not 1<=len(manifests)<=8 or digest([m.model_dump(mode='json') for m in manifests])!=operation.context.scope.source_set_sha256:
                raise ValueError('Source manifest hash')
            sources={m.image_sha256:m for m in manifests}
            if len(sources)!=len(manifests) or operation.case_id not in sources:raise ValueError('Source membership')
            freshness=ReviewFreshness.model_validate_json(canonical(value['review_freshness']))
            if not -30<=now_seconds()-utc(freshness.checked_at).timestamp()<=90:
                raise ValueError('Freshness assessment timestamp')
            if len(set(freshness.changed_case_ids))!=len(freshness.changed_case_ids) or not set(freshness.changed_case_ids)<=set(sources):
                raise ValueError('Freshness scope')
            report=snapshot['report']
            if report is not None and not isinstance(report,dict):raise ValueError('Report shape')
            if (snapshot['report_state']!=(report or {}).get('status','NOT_STARTED')
                    or snapshot['signer']!=(report or {}).get('signed_by')
                    or snapshot['amendment_provenance']!=(report or {}).get('amended_versions',[])):
                raise ValueError('Report metadata')
            if report:
                form=report.get('form')
                if (not isinstance(form,dict) or form.get('hn')!=patient_key(operation.context.scope)
                        or form.get('patient_name','') not in {'',patient_key(operation.context.scope)}
                        or report.get('source_set_sha256')!=operation.context.scope.source_set_sha256):
                    raise ValueError('Report patient/source identity')
                if report.get('status')=='SIGNED':
                    proof=report.get('carebalance_identity');signer=report.get('signed_by')
                    if (not isinstance(proof,dict) or set(proof)!={'identity_assurance','actor_id','session_id','binding_id','verified_capabilities'}
                            or proof.get('identity_assurance')!='VERIFIED_HIS_SESSION'
                            or any(not isinstance(proof.get(k),str) or not re.fullmatch('[A-Za-z0-9_-]{1,64}',proof[k]) for k in ('actor_id','session_id','binding_id'))
                            or not isinstance(proof.get('verified_capabilities'),list)
                            or any(not isinstance(c,str) for c in proof['verified_capabilities'])
                            or len(set(proof['verified_capabilities']))!=len(proof['verified_capabilities'])
                            or not set(proof['verified_capabilities'])<={'dr.read','dr.prepare','dr.grade.confirm','dr.report.prepare','dr.report.sign'}
                            or not {'dr.read','dr.report.prepare','dr.report.sign'}<=set(proof['verified_capabilities'])
                            or not isinstance(signer,dict) or signer.get('name')!=proof.get('actor_id')
                            or set(signer)!={'name','role','timestamp'} or signer.get('role')!='physician'):
                        raise ValueError('Unverified report signer')
                    signed_at=signer['timestamp']
                    if (not isinstance(signed_at,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|\+00:00)',signed_at)
                            or datetime.fromisoformat(signed_at.replace('Z','+00:00')).utcoffset()!=timedelta(0)):
                        raise ValueError('Signature timestamp')
            witness=None
            if report and report.get('carebalance_review_witness') is not None:
                witness=ReviewWitness.model_validate_json(canonical(report['carebalance_review_witness']))
                witness_hash=report.get('carebalance_review_witness_sha256')
                if (digest(witness)!=witness_hash or witness.source_set_sha256!=operation.context.scope.source_set_sha256
                        or witness.report_form_sha256!=digest(report.get('form'))
                        or {c.case_id for c in witness.cases}!=set(sources)):
                    raise ValueError('Review witness hash/scope')
                for case in witness.cases:
                    source=sources[case.case_id]
                    if case.source_sha256!=source.source_sha256 or case.image_sha256!=source.image_sha256:
                        raise ValueError('Review witness source')
                    if (case.confirm_revision is None or case.grade_review_revision is None
                            or case.grade_review_revision<=case.confirm_revision or case.grade_status not in {'CONFIRMED','UNGRADABLE'}):
                        raise ValueError('Missing positive review milestones')
                    eye='left' if source.laterality=='L' else 'right'
                    findings=report['form'].get(eye) or {}
                    quality='GRADABLE' if case.grade_status=='CONFIRMED' else 'UNGRADABLE'
                    if (not isinstance(findings,dict) or findings.get('grade')!=case.reviewed_grade
                            or findings.get('quality')!=quality or quality=='GRADABLE' and (case.quality!='GRADABLE' or case.reviewed_grade is None)
                            or quality=='UNGRADABLE' and report['form'].get('decision')=='NOT_REFER'):
                        raise ValueError('Report form differs from confirmed reviews')
                present_eyes={'left' if m.laterality=='L' else 'right' for m in manifests}
                for eye in {'left','right'}-present_eyes:
                    findings=report['form'].get(eye) or {}
                    if not isinstance(findings,dict) or any(item not in (None,'',[]) for item in findings.values()):
                        raise ValueError('Report findings outside source set')
                if freshness.witness_sha256!=witness_hash:raise ValueError('Freshness stored witness')
            if freshness.state in {'CURRENT','CHANGED'} and (not report or report.get('status')!='SIGNED' or witness is None):
                raise ValueError('Unproved current review')
            if witness is None and freshness.witness_sha256 is not None:raise ValueError('Missing review witness')
            return value
        except (ValueError,TypeError,KeyError,RecursionError):
            raise DRUnknown('DR report witness/freshness invalid') from None


def patient_key(scope: WorkspaceScope):
    return 'CB0-' + digest({k:getattr(scope,k) for k in ('organization_id','facility_id','patient_id')})[:28].upper()
