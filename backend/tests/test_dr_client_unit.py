"""Strict DR destination, bytes and clinical-witness sender regressions."""
import base64
from copy import deepcopy
from datetime import datetime,timedelta,timezone
import hashlib
import json

import httpx
import pytest

from backend.app.dr_client import Destination,DRClient,DRRejected,DRUnavailable,DRUnknown,patient_key
from backend.app.dr_protocol import Context,Dispatch,ReadReport,WorkspaceScope,canonical,digest,now_seconds,verify_request

KEY=b'bounded-unit-test-only-dedicated-key'


def fixture():
    manifest=[{'source_id':'source1','source_version':1,'source_sha256':'a'*64,'image_sha256':'b'*64,
        'byte_size':200,'media_type':'image/png','laterality':'L','modality':'CFP','source_origin':'SYNTHETIC',
        'consent_reference':'explicit-consent1','capture_time':None}]
    scope=WorkspaceScope(organization_id='org1',facility_id='facility1',patient_id='patient1',encounter_id='visit1',
        task_id='task1',source_set_id='set1',source_set_revision=1,source_set_sha256=digest(manifest))
    context=Context.model_validate_json(canonical({'binding_id':'binding1','actor_id':'actor1','session_id':'session1',
        'expires_at':(datetime.now(timezone.utc)+timedelta(seconds=90)).isoformat().replace('+00:00','Z'),
        'capabilities':['dr.read'],'scope':scope.model_dump(mode='json')}))
    destination=Destination('dest1','http://127.0.0.1:19001',KEY,scope,'cb-'+digest(scope)[:32])
    operation=ReadReport(protocol='carebalance.dr.v1',request_id='request1',context=context,case_id='b'*64)
    return manifest,scope,destination,operation


def receipt(*,signed=False):
    manifest,scope,destination,operation=fixture()
    report=None
    if signed:
        form={'hn':patient_key(scope),'patient_name':'','left':{'quality':'GRADABLE','grade':0},'decision':'NOT_REFER'}
        witness={'source_set_sha256':scope.source_set_sha256,'report_form_sha256':digest(form),'cases':[
            {'case_id':'b'*64,'source_sha256':'a'*64,'image_sha256':'b'*64,'confirm_revision':1,
             'grade_review_revision':2,'grade_status':'CONFIRMED','reviewed_grade':0,'quality':'GRADABLE',
             'annotation_set_sha256':'c'*64,'annotation_review_revision':None,'annotation_confirmation_sha256':None}]}
        report={'form':form,'status':'SIGNED','source_set_sha256':scope.source_set_sha256,
            'carebalance_identity':{'identity_assurance':'VERIFIED_HIS_SESSION','actor_id':'signer1','session_id':'signer-session',
                'binding_id':'signer-binding','verified_capabilities':['dr.read','dr.report.prepare','dr.report.sign']},
            'signed_by':{'name':'signer1','role':'physician','timestamp':'2026-11-14T00:00:00Z'},
            'carebalance_review_witness':witness,'carebalance_review_witness_sha256':digest(witness)}
    snapshot={'workspace_id':destination.workspace_id,'source_set':scope.model_dump(mode='json'),'source_manifest':manifest,
        'case_id':operation.case_id,'case_revision':3,'report':report,'report_sha256':digest(report),
        'report_state':'SIGNED' if signed else 'NOT_STARTED','signer':(report or {}).get('signed_by'),'amendment_provenance':[]}
    witness_hash=(report or {}).get('carebalance_review_witness_sha256')
    value={'protocol':operation.protocol,'request_id':operation.request_id,'binding_id':operation.context.binding_id,
        'workspace_id':destination.workspace_id,'patient_key':patient_key(scope),'snapshot_sha256':digest(snapshot),'snapshot':snapshot,
        'reader':{'identity_assurance':'VERIFIED_HIS_SESSION','actor_id':'actor1','session_id':'session1','binding_id':'binding1','verified_capabilities':['dr.read']},
        'review_freshness':{'state':'CURRENT' if signed else 'UNAVAILABLE','witness_sha256':witness_hash,
            'current_witness_sha256':witness_hash,'checked_at':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),'changed_case_ids':[]}}
    return destination,operation,value


@pytest.mark.parametrize('origin',['http://localhost:19001','http://10.0.0.1:19001','http://127.0.0.1',
    'http://user:password@127.0.0.1:19001','http://127.0.0.1:19001/','http://127.0.0.1:19001?x=1','https://127.0.0.1:19001'])
def test_destination_rejects_unpinned_authority(origin):
    manifest,scope,destination,operation=fixture()
    with pytest.raises(DRUnavailable):Destination('dest1',origin,KEY,scope,destination.workspace_id)


def test_signed_transport_exact_raw_bytes_and_no_cookie_or_proxy(monkeypatch):
    destination,operation,value=receipt()
    seen=[]
    def receiver(request):
        verify_request(KEY,method=request.method,path=request.url.path,timestamp=int(request.headers['X-CareBalance-Timestamp']),
            nonce=request.headers['X-CareBalance-Nonce'],audience=request.headers['X-CareBalance-Audience'],body=request.content,
            signature=request.headers['X-CareBalance-Signature'],now=now_seconds())
        assert request.url.host=='127.0.0.1' and not any(k in request.headers for k in ['cookie','origin','authorization'])
        seen.append(request.content)
        return httpx.Response(200,json=value)
    monkeypatch.setenv('HTTP_PROXY','http://127.0.0.1:9')
    assert DRClient(destination,httpx.MockTransport(receiver)).exchange(operation)==value
    assert seen==[canonical(operation)]


def test_unsigned_unavailable_and_signed_current_are_distinct():
    for signed in [False,True]:
        destination,operation,value=receipt(signed=signed)
        result=DRClient(destination).validate_report(value,operation)
        assert result['review_freshness']['state']==('CURRENT' if signed else 'UNAVAILABLE')


@pytest.mark.parametrize('mutation',[
    lambda v:v.update(request_id='wrong-request'),
    lambda v:v.update(binding_id='wrong-binding'),
    lambda v:v['snapshot'].update(case_id='f'*64),
    lambda v:v['snapshot']['source_manifest'][0].update(source_sha256='d'*64),
    lambda v:v['reader'].update(actor_id='another-actor'),
    lambda v:v['review_freshness'].update(state='CURRENT'),
    lambda v:v['review_freshness'].update(checked_at='2000-01-01T00:00:00Z'),
    lambda v:v.update(extra='unknown-field'),
])
def test_wrong_scope_reader_manifest_and_unproved_current_denied(mutation):
    destination,operation,value=receipt();mutation(value)
    with pytest.raises(DRUnknown):DRClient(destination).validate_report(value,operation)


@pytest.mark.parametrize('mutation',[
    lambda v:v['snapshot']['report']['carebalance_review_witness']['cases'][0].update(source_sha256='d'*64),
    lambda v:v['snapshot']['report']['carebalance_review_witness']['cases'][0].update(image_sha256='d'*64),
    lambda v:v['snapshot']['report']['carebalance_identity'].update(verified_capabilities=['dr.read']),
    lambda v:v['snapshot']['report']['signed_by'].update(name='forged-signer'),
    lambda v:v['review_freshness'].update(state='CHANGED',current_witness_sha256='d'*64,changed_case_ids=['e'*64]),
])
def test_even_selfconsistent_report_hash_cannot_forge_clinical_witness(mutation):
    destination,operation,value=receipt(signed=True);mutation(value)
    report=value['snapshot']['report'];report['carebalance_review_witness_sha256']=digest(report['carebalance_review_witness'])
    value['snapshot']['report_sha256']=digest(report);value['snapshot']['signer']=report['signed_by'];value['snapshot_sha256']=digest(value['snapshot'])
    value['review_freshness']['witness_sha256']=report['carebalance_review_witness_sha256']
    if value['review_freshness']['state']=='CURRENT':value['review_freshness']['current_witness_sha256']=report['carebalance_review_witness_sha256']
    with pytest.raises(DRUnknown):DRClient(destination).validate_report(value,operation)


def test_changed_review_preserves_historical_signed_snapshot():
    destination,operation,value=receipt(signed=True);old_hash=value['snapshot']['report_sha256']
    value['review_freshness'].update(state='CHANGED',current_witness_sha256='d'*64,changed_case_ids=['b'*64])
    result=DRClient(destination).validate_report(value,operation)
    assert result['snapshot']['report_state']=='SIGNED' and result['snapshot']['report_sha256']==old_hash


def test_expired_context_rejected_before_network():
    manifest,scope,destination,operation=fixture()
    value=operation.model_dump(mode='json');value['context']['expires_at']='2000-01-01T00:00:00Z'
    operation=ReadReport.model_validate_json(canonical(value));calls=[]
    with pytest.raises(DRRejected):DRClient(destination,httpx.MockTransport(lambda req:calls.append(req))).exchange(operation)
    assert calls==[]


def test_transport_rejection_stays_definitive_and_duplicate_json_unknown():
    destination,operation,value=receipt()
    with pytest.raises(DRRejected):DRClient(destination,httpx.MockTransport(lambda request:httpx.Response(403,json={'detail':'rejected'}))).exchange(operation)
    with pytest.raises(DRUnknown):DRClient(destination,httpx.MockTransport(lambda request:httpx.Response(200,content=b'{"protocol":"first","protocol":"second"}',headers={'Content-Type':'application/json'}))).exchange(operation)


@pytest.mark.parametrize('mutation',[
    lambda r:r['carebalance_review_witness']['cases'][0].update(confirm_revision=None),
    lambda r:r['carebalance_review_witness']['cases'][0].update(grade_review_revision=None),
    lambda r:r['carebalance_review_witness']['cases'][0].update(grade_review_revision=1),
    lambda r:r['carebalance_review_witness']['cases'][0].update(grade_status='NOT_REVIEWED'),
    lambda r:r['carebalance_review_witness']['cases'][0].update(reviewed_grade=None),
    lambda r:r['carebalance_review_witness']['cases'][0].update(quality='UNGRADABLE'),
    lambda r:r['form']['left'].update(grade=4),
    lambda r:r['form']['left'].update(quality='UNGRADABLE'),
    lambda r:r['form'].update(right={'grade':1,'quality':'GRADABLE'}),
    lambda r:(r['carebalance_identity'].update(actor_id=None),r['signed_by'].update(name=None)),
    lambda r:r['carebalance_identity'].update(session_id=''),
    lambda r:r['carebalance_identity'].update(binding_id=''),
    lambda r:r['carebalance_identity'].update(verified_capabilities=['dr.report.sign']),
    lambda r:r['signed_by'].update(timestamp='2026-11-14T00:00:00'),
])
def test_selfconsistent_current_requires_positive_milestones_form_and_signer(mutation):
    destination,operation,value=receipt(signed=True);report=value['snapshot']['report'];mutation(report)
    witness=report['carebalance_review_witness'];witness['report_form_sha256']=digest(report['form'])
    report['carebalance_review_witness_sha256']=digest(witness)
    value['review_freshness']['witness_sha256']=value['review_freshness']['current_witness_sha256']=digest(witness)
    value['snapshot']['report_sha256']=digest(report);value['snapshot']['signer']=report['signed_by'];value['snapshot_sha256']=digest(value['snapshot'])
    with pytest.raises(DRUnknown):DRClient(destination).validate_report(value,operation)


@pytest.mark.parametrize('suffix,kind,data',[
    ('/v1/images/'+'b'*64,'image/png',b'\x89PNG\r\n\x1a\nwrong-original-bytes'),
    ('/v1/images/'+'b'*64,'application/json',b'{}'),
    ('/v1/cases/'+'b'*64,'text/html',b'<html>wrong route</html>'),
    ('/v1/cases/'+'b'*64,'application/json',canonical({'image_id':'d'*64,'revision':0})),
    ('/v1/cases/'+'b'*64,'application/json',canonical({'image_id':'b'*64,'revision':0,'patient_key':'foreign-patient'})),
    ('/v1/cases/'+'b'*64,'application/json',canonical({'image_id':'b'*64,'revision':0,'visit_context':{'visit_key':'foreign-visit'}})),
    ('/v1/cases','application/json',canonical([{'image_id':'d'*64,'revision':0}])),
    ('/v1/cases/'+'b'*64,'application/json',canonical({'image_id':'b'*64})),
    ('/v1/cases/'+'b'*64,'application/json',canonical({'image_id':'b'*64,'revision':True})),
    ('/v1/cases/'+'b'*64+'/screening-report','application/json',canonical({'revision':1,'screening_report':{'form':{'hn':'foreign-patient'}}})),
])
def test_matching_envelope_cannot_change_requested_resource_identity(suffix,kind,data):
    manifest,scope,destination,read=fixture()
    operation=Dispatch(protocol=read.protocol,request_id=read.request_id,context=read.context,method='GET',path=suffix,query={},body=None)
    envelope={'protocol':operation.protocol,'request_id':operation.request_id,'binding_id':operation.context.binding_id,
        'workspace_id':destination.workspace_id,'outcome':'succeeded','status_code':200,'content_type':kind,
        'body_base64':base64.b64encode(data).decode(),'response_sha256':hashlib.sha256(data).hexdigest()}
    with pytest.raises(DRUnknown):DRClient(destination,httpx.MockTransport(lambda request:httpx.Response(200,json=envelope)),source_manifest=manifest).exchange(operation)


def test_unconfirmed_case_is_valid_without_inventing_patient_identity():
    manifest,scope,destination,read=fixture()
    operation=Dispatch(protocol=read.protocol,request_id=read.request_id,context=read.context,method='GET',path='/v1/cases/'+'b'*64,query={},body=None)
    data=canonical({'image_id':'b'*64,'revision':0,'patient_key':None,'visit_context':None,'laterality':'UNKNOWN'})
    envelope={'protocol':operation.protocol,'request_id':operation.request_id,'binding_id':operation.context.binding_id,
        'workspace_id':destination.workspace_id,'outcome':'succeeded','status_code':200,'content_type':'application/json',
        'body_base64':base64.b64encode(data).decode(),'response_sha256':hashlib.sha256(data).hexdigest()}
    assert DRClient(destination,httpx.MockTransport(lambda request:httpx.Response(200,json=envelope)),source_manifest=manifest).exchange(operation)==envelope


@pytest.mark.parametrize('origin,returned,admission',[
    ('PUBLIC','SYNTHETIC',None),('PUBLIC','HOSPITAL',None),('SYNTHETIC','PUBLIC',None),
    ('PUBLIC','PUBLIC',{'source_origin':'HOSPITAL'}),('SYNTHETIC','SYNTHETIC',{'source_origin':'PUBLIC'}),
    ('PUBLIC','PUBLIC',{'source_origin':'PUBLIC','retinal_modality':'UWF'}),
])
def test_case_and_admission_cannot_relabel_registered_source(origin,returned,admission):
    manifest,scope,destination,read=fixture();manifest[0]['source_origin']=origin
    scope=scope.model_copy(update={'source_set_sha256':digest(manifest)})
    destination=Destination(destination.id,destination.origin,KEY,scope,'cb-'+digest(scope)[:32])
    context=read.context.model_copy(update={'scope':scope})
    case={'image_id':'b'*64,'revision':0,'source_origin':returned,'admission':admission}
    operation=Dispatch(protocol=read.protocol,request_id=read.request_id,context=context,method='GET',path='/v1/cases/'+'b'*64,query={},body=None)
    data=canonical(case)
    envelope={'protocol':operation.protocol,'request_id':operation.request_id,'binding_id':operation.context.binding_id,
        'workspace_id':destination.workspace_id,'outcome':'succeeded','status_code':200,'content_type':'application/json',
        'body_base64':base64.b64encode(data).decode(),'response_sha256':hashlib.sha256(data).hexdigest()}
    with pytest.raises(DRUnknown):DRClient(destination,httpx.MockTransport(lambda request:httpx.Response(200,json=envelope)),source_manifest=manifest).exchange(operation)
