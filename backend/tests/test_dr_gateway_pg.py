"""Actual disposable PostgreSQL DR authorization, persistence and BFF tests."""
import os
assert os.getenv('HIS_TEST_DATABASE_URL') and os.environ['HIS_TEST_DATABASE_URL']==os.environ.get('DATABASE_URL'), 'Disposable PostgreSQL wrapper required'

import base64
from copy import deepcopy
from datetime import timedelta
import hashlib
import json
import struct
import time
import zlib
from concurrent.futures import ThreadPoolExecutor
from threading import Event

from fastapi.testclient import TestClient
import httpx
import pytest
from sqlalchemy import func,select,text
from sqlalchemy.exc import DBAPIError

from backend.app import dr_gateway as gateway
from backend.app.common import digest,uid,utcnow
from backend.app.db import SessionLocal,engine
from backend.app.dr_client import DRClient,Destination,patient_key
from backend.app.dr_core import register_authored_source,register_public_dataset_source
from backend.app.dr_protocol import WorkspaceScope,canonical,verify_request
from backend.app.main import app
from backend.app.models import CareAssignment,ClinicalOrder,SessionRecord,Task
from backend.app.models_clinical import ImagingStudy
from backend.app.models_dr import DRBinding,DRAttempt,DRCapabilityGrant,DRCapabilityGrantEvent,DRExchange,DRReportReceipt,DRSourceProvenance,DRSourceSet
from backend.app.seed import seed
from backend.app.storage import file_store

BASE='/api/v2/integrations/dr'
KEY=b'isolated-dr-gateway-synthetic-key-only'


@pytest.fixture(scope='module',autouse=True)
def explicit_seed():
    assert engine.url.database=='his_test'
    with SessionLocal.begin() as db:seed(db,os.environ['HIS_SEED_PASSWORD'])


def login(username='clinician'):
    client=TestClient(app)
    response=client.post('/api/v2/auth/login',json={'username':username,'password':os.environ['HIS_SEED_PASSWORD']})
    assert response.status_code==200,response.text
    client.headers['X-CSRF-Token']=response.json()['csrf_token']
    return client


def png(label):
    def chunk(name,data):return struct.pack('!I',len(data))+name+data+struct.pack('!I',zlib.crc32(name+data)&0xffffffff)
    width,height=64,48
    rows=b''.join(b'\x00'+bytes([x%256,y%256,(x+y)%256])*width for y,x in enumerate(range(height)))
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!IIBBBBB',width,height,8,2,0,0,0))+chunk(b'tEXt',b'fixture\x00'+label.encode())+chunk(b'IDAT',zlib.compress(rows))+chunk(b'IEND',b'')


def public_evidence():
    return {'schema_version':'carebalance.public-retinal-source.v1','dataset_title':'MMRDR',
        'dataset_doi':'10.6084/m9.figshare.29423747.v2','dataset_url':'https://figshare.com/articles/dataset/MMRDR/29423747',
        'license_id':'CC-BY-4.0','license_url':'https://creativecommons.org/licenses/by/4.0/',
        'attribution':'Tang et al. (2025), MMRDR. Isolated protocol test; authored bytes are not dataset samples.',
        'membership_basis':'owner_attestation','membership_reference':'authored-test:public-origin-path-only',
        'original_filename':None,'local_filename':'authored-test.jpg','upstream_image_sha256':None,
        'rename_statement_reference':None,'laterality_evidence_reference':'authored-test:explicit-eye',
        'patient_grouping':'documented_same_patient','patient_grouping_reference':'authored-test:bilateral-fixture'}


def fixture_sources(count=1,registered=True,png_producer=None,evidence_reference='authored-synthetic:stdlib-png-test-v1',public=False):
    with SessionLocal.begin() as db:
        task=Task(id=uid(),organization_id='org-demo',facility_id='facility-demo',patient_id='patient-001',
            encounter_id='encounter-001',domain='D11',kind='dr_screening_review',title='Authored DR fixture review',status='open')
        acquisition=Task(id=uid(),organization_id='org-demo',facility_id='facility-demo',patient_id='patient-001',
            encounter_id='encounter-001',domain='D11',kind='imaging',title='Completed acquisition',status='completed')
        db.add_all([task,acquisition]);db.flush();selected=[]
        for index in range(count):
            order=ClinicalOrder(id=uid(),organization_id='org-demo',facility_id='facility-demo',patient_id='patient-001',
                encounter_id='encounter-001',task_id=acquisition.id,requester_id='user-clinician',kind='imaging',
                code='SYN-RETINA',label='Authored synthetic retina',status='fulfilled',version=4,quantity=1,unit='image')
            db.add(order);db.flush()
            data=(png_producer or png)(uid());stored=file_store().put(data)
            source=ImagingStudy(id=uid(),organization_id='org-demo',facility_id='facility-demo',patient_id='patient-001',
                encounter_id='encounter-001',created_by='user-imaging',status='released',version=5,order_id=order.id,
                order_version=4,modality='synthetic CFP',body_site='synthetic retina',file_sha256=stored.sha256,
                file_path=stored.key,file_mime='image/jpeg' if public else 'image/png')
            db.add(source);db.flush()
            provenance=register_public_dataset_source(db,source_id=source.id,source_version=source.version,original_bytes=data,
                laterality='L' if index==0 else 'R',modality='CFP',capture_time=None,
                dataset_provenance=public_evidence(),registrar_id='user-operations_admin') if public and registered else register_authored_source(db,source_id=source.id,source_version=source.version,generated_bytes=data,
                laterality='L' if index==0 else 'R',modality='CFP',capture_time=None,
                evidence_reference=evidence_reference,registrar_id='user-operations_admin') if registered else None
            selected.append({'source_id':source.id,'source_version':5,'provenance_id':provenance.id if provenance else uid()})
        return {'patient_id':'patient-001','encounter_id':'encounter-001','task_id':task.id,'destination_id':'fixture',
            'sources':selected,'transfer_consent':{'confirmed':True,'wording_version':'carebalance.dr-transfer.v2' if public else 'carebalance.dr-transfer.v1','purpose':'manual-dr-screening'}}


class Receiver:
    def __init__(self):self.calls=[];self.hook=None;self.fail=False
    def __call__(self,request):
        assert engine.pool.checkedout()==0,'HIS held a database connection across receiver HTTP'
        verify_request(KEY,method=request.method,path=request.url.path,timestamp=int(request.headers['X-CareBalance-Timestamp']),
            nonce=request.headers['X-CareBalance-Nonce'],audience=request.headers['X-CareBalance-Audience'],body=request.content,
            signature=request.headers['X-CareBalance-Signature'],now=int(time.time()))
        value=json.loads(request.content);self.calls.append(deepcopy(value));context=value['context'];scope=context['scope']
        workspace='cb-'+digest(scope)[:32]
        if self.hook:self.hook(value)
        if self.fail:raise httpx.ReadTimeout('Synthetic lost response')
        if request.url.path.endswith('/read-report'):
            manifest=self.manifest
            snapshot={'workspace_id':workspace,'source_set':scope,'source_manifest':manifest,'case_id':value['case_id'],
                'case_revision':0,'report':None,'report_sha256':digest(None),'report_state':'NOT_STARTED','signer':None,'amendment_provenance':[]}
            return httpx.Response(200,json={'protocol':value['protocol'],'request_id':value['request_id'],
                'binding_id':context['binding_id'],'workspace_id':workspace,'patient_key':patient_key(WorkspaceScope(**scope)),
                'snapshot_sha256':digest(snapshot),'snapshot':snapshot,
                'reader':{'identity_assurance':'VERIFIED_HIS_SESSION','actor_id':context['actor_id'],'session_id':context['session_id'],
                    'binding_id':context['binding_id'],'verified_capabilities':context['capabilities']},
                'review_freshness':{'state':'UNAVAILABLE','witness_sha256':None,'current_witness_sha256':None,
                    'checked_at':utcnow().isoformat().replace('+00:00','Z'),'changed_case_ids':[]}})
        if request.url.path.endswith('/import'):
            self.manifest=[{k:v for k,v in source.items() if k!='image_base64'} for source in value['sources']]
            result={'workspace_id':workspace,'patient_key':patient_key(WorkspaceScope(**scope)),'source_set':scope,
                'cases':[{'case_id':m['image_sha256'],'source':m} for m in self.manifest],'manual_review_only':True,'inference_enabled':False}
        elif value['path'].startswith('/v1/images/'):
            image=next(source['image_base64'] for source in self.calls[0]['sources'] if source['image_sha256']==value['path'].split('/')[3])
            data=base64.b64decode(image);return self.envelope(value,workspace,data,'image/png')
        elif value['path'].endswith('/print'):
            return self.envelope(value,workspace,b'<!doctype html><html><body><h1>Stored signed report</h1></body></html>','text/html')
        elif value['path'].endswith('/screening-report'):result={'revision':1,'screening_report':None}
        else:result=([{'revision':0,'image_id':m['image_sha256']} for m in self.manifest]
            if value['path']=='/v1/cases' else {'revision':1,'image_id':value['path'].split('/')[3]})
        return self.envelope(value,workspace,canonical(result),'application/json')
    def envelope(self,value,workspace,data,kind):
        return httpx.Response(200,json={'protocol':value['protocol'],'request_id':value['request_id'],
            'binding_id':value['context']['binding_id'],'workspace_id':workspace,'outcome':'succeeded','status_code':200,
            'content_type':kind,'body_base64':base64.b64encode(data).decode(),'response_sha256':hashlib.sha256(data).hexdigest()})


@pytest.fixture()
def prepared(monkeypatch,tmp_path):
    client=login();body=fixture_sources(2)
    created=client.post(BASE+'/source-sets',json=body,headers={'Idempotency-Key':uid()})
    assert created.status_code==200,created.text
    source_set=created.json();scope=source_set['scope'];workspace='cb-'+digest(scope)[:32]
    registry=tmp_path/'destinations.json';registry.write_text(json.dumps({'version':1,'destinations':[
        {'id':'fixture','origin':'http://127.0.0.1:19899','key':KEY.decode(),'scope':scope,'workspace_id':workspace}]}));registry.chmod(0o600)
    monkeypatch.setenv('HIS_DR_ENABLED','true');monkeypatch.setenv('HIS_DR_DESTINATIONS_FILE',str(registry))
    receiver=Receiver();original=gateway.DRClient
    monkeypatch.setattr(gateway,'DRClient',lambda destination,**kwargs:original(destination,httpx.MockTransport(receiver),**kwargs))
    imported=client.post(BASE+f"/source-sets/{source_set['id']}/bindings",json={'transfer_consent':body['transfer_consent']},headers={'Idempotency-Key':uid()})
    assert imported.status_code==200,imported.text
    return client,source_set,imported.json()['binding_id'],receiver,body


def test_registered_source_set_scope_and_explicit_consent(monkeypatch):
    client=login();body=fixture_sources(registered=False)
    response=client.post(BASE+'/source-sets',json=body,headers={'Idempotency-Key':uid()})
    assert response.status_code==422 and response.json()['detail']['code']=='DR_AUTHORED_SOURCE_REGISTRATION_REQUIRED'
    body=fixture_sources();body['transfer_consent']['confirmed']=False
    assert client.post(BASE+'/source-sets',json=body,headers={'Idempotency-Key':uid()}).status_code==422
    body['transfer_consent']['confirmed']=True
    created=client.post(BASE+'/source-sets',json=body,headers={'Idempotency-Key':'same-source-key'})
    assert created.status_code==200,created.text
    replay=client.post(BASE+'/source-sets',json=body,headers={'Idempotency-Key':'same-source-key'})
    assert replay.json()['id']==created.json()['id']
    assert created.json()['availability']=='unavailable'
    assert client.post(BASE+f"/source-sets/{created.json()['id']}/bindings",json={'transfer_consent':body['transfer_consent']},headers={'Idempotency-Key':uid()}).status_code==503


def test_current_binding_defaults_no_signer_and_reads_real_bytes(prepared):
    client,source_set,binding,receiver,body=prepared
    response=client.get(BASE+'/bindings/'+binding);assert response.status_code==200,response.text
    value=response.json();assert value['pending'] is None
    detail=client.get(BASE+'/source-sets/'+source_set['id']).json()
    assert detail['bindings']==[{'id':binding,'state':'imported','workspace_url':f'/integrations/dr/{binding}/app/','pending':None}]
    assert value['capabilities']==['dr.prepare','dr.read','dr.report.prepare']
    assert value['patient']['id']=='patient-001' and value['encounter']['id']=='encounter-001'
    assert value['patient_key'].startswith('CB0-') and len(value['patient_key'])==32
    image=source_set['sources'][0]['image_sha256'];prefix=f'/integrations/dr/{binding}/api'
    assert {c['image_id'] for c in client.get(prefix+'/v1/cases').json()}=={m['image_sha256'] for m in source_set['sources']}
    actual=client.get(prefix+'/v1/images/'+image);assert actual.status_code==200
    assert hashlib.sha256(actual.content).hexdigest()==image
    assert client.get(prefix+'/v1/cases/'+('f'*64)).status_code==404
    assert client.get(prefix+'/v1/workspaces').status_code==404
    assert client.get(prefix+'/v1/cases/'+image+'/comparison?other_image_id='+('e'*64)).status_code==422
    calls=len(receiver.calls)
    sign=client.put(prefix+'/v1/cases/'+image+'/screening-report',json={'sign':True,'report':{}},headers={'Idempotency-Key':uid()})
    assert sign.status_code==403 and len(receiver.calls)==calls
    no_csrf=client.headers.pop('X-CSRF-Token')
    assert client.post(prefix+'/v1/cases/'+image+'/admission',json={},headers={'Idempotency-Key':uid()}).status_code==403
    client.headers['X-CSRF-Token']=no_csrf
    other=login();assert other.get(BASE+'/bindings/'+binding).status_code==404
    assert other.get(BASE+'/source-sets/'+source_set['id']).json()['bindings']==[]
    read=client.post(BASE+f'/bindings/{binding}/read-report',json={'case_id':image},headers={'Idempotency-Key':uid()})
    assert read.status_code==200,read.text
    assert read.json()['receipt']['review_freshness']['state']=='UNAVAILABLE'
    with SessionLocal() as db:
        assert db.get(Task,body['task_id']).status=='open'
        assert db.scalar(select(func.count()).select_from(DRReportReceipt).where(DRReportReceipt.binding_id==binding))==1


def test_unknown_response_requires_same_command_recovery(prepared):
    client,source_set,binding,receiver,body=prepared
    image=source_set['sources'][0]['image_sha256'];path=f'/integrations/dr/{binding}/api/v1/cases/{image}/admission'
    receiver.fail=True;key=uid();payload={'revision':0,'action':'QUALITY_ACCEPTABLE','reviewer':'spoof'}
    result=client.post(path,json=payload,headers={'Idempotency-Key':key});assert result.status_code==202,result.text
    denied=client.post(path,json=payload,headers={'Idempotency-Key':uid()});assert denied.status_code==409
    recovered=client.post(BASE+f'/bindings/{binding}/recover').json()
    assert recovered['automatic_replay'] is False and recovered['commands'][0]['key']==key
    assert recovered['commands'][0]['body']['body']['reviewer']=='user-clinician'
    with SessionLocal.begin() as db:
        attempt=db.scalar(select(DRAttempt).where(DRAttempt.binding_id==binding,DRAttempt.operation_key==key))
        attempt.lease_expires_at=utcnow()-timedelta(seconds=1)
    receiver.fail=False
    retry=client.post(path,json=payload,headers={'Idempotency-Key':key});assert retry.status_code==200,retry.text
    relevant=[c for c in receiver.calls if c.get('path','').endswith('/admission')]
    assert len(relevant)==2 and relevant[0]['request_id']==relevant[1]['request_id']


def test_source_revocation_in_flight_quarantines_actual_receipt(prepared):
    client,source_set,binding,receiver,body=prepared
    source_id=body['sources'][0]['source_id']
    def revoke(value):
        with SessionLocal.begin() as db:
            source=db.get(ImagingStudy,source_id);source.version+=1
    receiver.hook=revoke
    response=client.get(f'/integrations/dr/{binding}/api/v1/cases')
    assert response.status_code==409,response.text
    with SessionLocal() as db:
        assert db.get(DRBinding,binding).state=='quarantined'
        exchange=db.scalar(select(DRExchange).join(DRAttempt).where(DRAttempt.binding_id==binding,DRExchange.quarantined.is_(True)))
        assert exchange.receipt is not None and exchange.outcome=='succeeded'


def test_manifest_assets_and_print_are_authorized_each_request(prepared,tmp_path,monkeypatch):
    client,source_set,binding,receiver,body=prepared
    root=tmp_path/'dist';(root/'assets').mkdir(parents=True)
    (root/'index.html').write_text('<html><head><script src="./assets/test.js"></script></head><body>DR</body></html>')
    (root/'assets/test.js').write_text('/* authored test bundle */')
    manifest=tmp_path/'web.json';manifest.write_text(json.dumps({'schema':'carebalance.dr.web.v1','root':str(root),
        'assets':{p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}}))
    monkeypatch.setenv('HIS_DR_WEB_MANIFEST',str(manifest))
    prefix=f'/integrations/dr/{binding}'
    page=client.get(prefix+'/app/');assert page.status_code==200,page.text
    assert 'id="carebalance-dr-context"' in page.text and prefix+'/assets/assets/test.js' in page.text
    assert 'return_url' in page.text and 'patient_id=patient-001' in page.text and 'encounter_id=encounter-001' in page.text
    assert 'record='+body['sources'][0]['source_id'] in page.text
    assert KEY.decode() not in page.text and '127.0.0.1:19899' not in page.text
    asset=client.get(prefix+'/assets/assets/test.js');assert asset.status_code==200 and 'no-store' in asset.headers['cache-control']
    assert client.get(prefix+'/assets/unknown.js').status_code==404
    assert client.get(prefix+'/app/unknown.js').status_code==404
    image=source_set['sources'][0]['image_sha256']
    printed=client.get(prefix+'/print/'+image);assert printed.status_code==200
    assert 'current review freshness is not assessed' in printed.text
    anonymous=TestClient(app)
    for path in ['/app/','/assets/assets/test.js','/api/v1/cases','/print/'+image]:assert anonymous.get(prefix+path).status_code==401
    with SessionLocal.begin() as db:
        assignment=db.scalar(select(CareAssignment).where(CareAssignment.user_id=='user-clinician',CareAssignment.patient_id=='patient-001'))
        assignment.active=False
    try:
        for path in ['/app/','/assets/assets/test.js','/api/v1/cases','/print/'+image]:assert client.get(prefix+path).status_code==404
    finally:
        with SessionLocal.begin() as db:
            db.scalar(select(CareAssignment).where(CareAssignment.user_id=='user-clinician',CareAssignment.patient_id=='patient-001')).active=True


def test_database_source_and_completed_evidence_immutable(prepared):
    client,source_set,binding,receiver,body=prepared
    for table,id in [('dr_source_sets',source_set['id']),('dr_bindings',binding),('dr_source_provenance',body['sources'][0]['provenance_id'])]:
        with SessionLocal() as db:
            with pytest.raises(DBAPIError):db.execute(text(f'DELETE FROM {table} WHERE id=:id'),{'id':id})
    with SessionLocal() as db:
        with pytest.raises(DBAPIError):db.execute(text('UPDATE dr_source_sets SET manifest_sha256=:sha WHERE id=:id'),{'sha':'a'*64,'id':source_set['id']})


def test_explicit_verified_grants_rechecked_after_external_call(prepared):
    client,source_set,binding,receiver,body=prepared
    now=utcnow();grant_ids=[]
    with SessionLocal.begin() as db:
        for capability in ['dr.grade.confirm','dr.report.sign']:
            grant=DRCapabilityGrant(organization_id='org-demo',facility_id='facility-demo',user_id='user-clinician',
                capability=capability,status='active',valid_from=now-timedelta(minutes=1),valid_until=now+timedelta(hours=1),
                verification_status='verified',evidence_reference='synthetic-validation:explicit-isolated-test-credential',
                verifier_id='user-quality',version=1)
            db.add(grant);db.flush();grant_ids.append(grant.id)
    try:
        caps=client.get(BASE+'/bindings/'+binding).json()['capabilities']
        assert 'dr.grade.confirm' in caps and 'dr.report.sign' in caps
        def revoke(value):
            with SessionLocal.begin() as db:
                grant=db.get(DRCapabilityGrant,grant_ids[1]);grant.status='revoked';grant.version+=1
        receiver.hook=revoke
        image=source_set['sources'][0]['image_sha256']
        response=client.put(f'/integrations/dr/{binding}/api/v1/cases/{image}/screening-report',
            json={'revision':0,'sign':True,'report':{'hn':patient_key(WorkspaceScope(**source_set['scope']))}},
            headers={'Idempotency-Key':uid()})
        assert response.status_code==409,response.text
        with SessionLocal() as db:
            assert db.get(DRBinding,binding).state=='quarantined'
            attempt=db.scalar(select(DRAttempt).where(DRAttempt.binding_id==binding,DRAttempt.operation=='dispatch'))
            assert attempt.status=='quarantined' and attempt.error_code=='DR_CONTEXT_CHANGED'
    finally:
        with SessionLocal.begin() as db:
            for id in grant_ids:
                grant=db.get(DRCapabilityGrant,id)
                if grant.status=='active':grant.status='revoked';grant.version+=1


def test_closed_review_retains_read_but_blocks_preparation(prepared):
    client,source_set,binding,receiver,body=prepared
    with SessionLocal.begin() as db:
        task=db.get(Task,body['task_id']);task.status='completed';task.version+=1
    value=client.get(BASE+'/bindings/'+binding)
    assert value.status_code==200,value.text
    assert value.json()['capabilities']==['dr.read']
    image=source_set['sources'][0]['image_sha256'];prefix=f'/integrations/dr/{binding}/api'
    assert client.get(prefix+'/v1/images/'+image).status_code==200
    response=client.post(prefix+'/v1/cases/'+image+'/admission',json={'revision':0,'action':'QUALITY_ACCEPTABLE'},headers={'Idempotency-Key':uid()})
    assert response.status_code==409 and response.json()['detail']['code']=='DR_REVIEW_TARGET_CLOSED'
    read=client.post(BASE+f'/bindings/{binding}/read-report',json={'case_id':image},headers={'Idempotency-Key':uid()})
    assert read.status_code==200,read.text


def test_foreign_patient_and_stale_registry_cannot_retarget_binding(prepared,tmp_path,monkeypatch):
    client,source_set,binding,receiver,body=prepared
    body=deepcopy(body);body['patient_id']='patient-002'
    assert client.post(BASE+'/source-sets',json=body,headers={'Idempotency-Key':uid()}).status_code==404
    raw=json.loads(open(os.environ['HIS_DR_DESTINATIONS_FILE']).read());raw['destinations'][0]['origin']='http://127.0.0.1:19998'
    changed=tmp_path/'changed.json';changed.write_text(json.dumps(raw));changed.chmod(0o600)
    monkeypatch.setenv('HIS_DR_DESTINATIONS_FILE',str(changed))
    assert client.get(BASE+'/bindings/'+binding).status_code==503
    assert len(receiver.calls)==1


def test_concurrent_same_command_is_sent_once_and_foreign_key_blocked(prepared):
    client,source_set,binding,receiver,body=prepared
    entered,release=Event(),Event();key=uid();image=source_set['sources'][0]['image_sha256']
    path=f'/integrations/dr/{binding}/api/v1/cases/{image}/admission'
    def pause(value):
        if value.get('path','').endswith('/admission'):
            entered.set();assert release.wait(15),'Test release timeout'
    receiver.hook=pause
    payload={'revision':0,'action':'QUALITY_ACCEPTABLE'}
    with ThreadPoolExecutor(max_workers=2) as pool:
        first=pool.submit(client.post,path,json=payload,headers={'Idempotency-Key':key})
        try:
            assert entered.wait(10),'First request did not reach receiver'
            duplicate=client.post(path,json=payload,headers={'Idempotency-Key':key})
            assert duplicate.status_code==202,duplicate.text
            denied=client.post(path,json=payload,headers={'Idempotency-Key':uid()})
            assert denied.status_code==409,denied.text
        finally:release.set()
        result=first.result(timeout=15);assert result.status_code==200,result.text
    assert len([v for v in receiver.calls if v.get('path','').endswith('/admission')])==1
    replay=client.post(path,json=payload,headers={'Idempotency-Key':key})
    assert replay.status_code==200 and replay.json()==result.json()


def test_rejected_clinical_command_replays_original_status_and_body(prepared,monkeypatch):
    client,source_set,binding,receiver,body=prepared
    image=source_set['sources'][0]['image_sha256'];path=f'/integrations/dr/{binding}/api/v1/cases/{image}/admission'
    original=receiver.envelope
    def rejected(value,workspace,data,kind):
        response=original(value,workspace,canonical({'detail':'Synthetic stale clinical revision'}),kind)
        packet=json.loads(response.content);packet['outcome']='rejected';packet['status_code']=409
        return httpx.Response(200,json=packet)
    monkeypatch.setattr(receiver,'envelope',rejected)
    payload={'revision':0,'action':'QUALITY_ACCEPTABLE'};key=uid()
    first=client.post(path,json=payload,headers={'Idempotency-Key':key})
    second=client.post(path,json=payload,headers={'Idempotency-Key':key})
    assert first.status_code==second.status_code==409 and first.content==second.content
    assert len([v for v in receiver.calls if v.get('path','').endswith('/admission')])==1


def test_wrong_original_image_never_becomes_a_successful_his_read(prepared,monkeypatch):
    client,source_set,binding,receiver,body=prepared
    original=receiver.envelope;wrong=png('different-authored-source')
    def corrupt(value,workspace,data,kind):
        return original(value,workspace,wrong,'image/png') if value.get('path','').startswith('/v1/images/') else original(value,workspace,data,kind)
    monkeypatch.setattr(receiver,'envelope',corrupt)
    image=source_set['sources'][0]['image_sha256']
    response=client.get(f'/integrations/dr/{binding}/api/v1/images/{image}')
    assert response.status_code==202 and response.content!=wrong
    with SessionLocal() as db:
        attempt=db.scalar(select(DRAttempt).where(DRAttempt.binding_id==binding,DRAttempt.operation=='dispatch'))
        assert attempt.status=='unknown'
        exchange=db.scalar(select(DRExchange).where(DRExchange.attempt_id==attempt.id))
        assert exchange.outcome=='unknown' and 'transport_diagnostic' in exchange.receipt
        assert 'body_base64' not in exchange.receipt


def test_expired_unreplaced_lease_retains_exchange_and_quarantines(prepared):
    client,source_set,binding,receiver,body=prepared
    def expire(value):
        with SessionLocal.begin() as db:
            attempt=db.scalar(select(DRAttempt).where(DRAttempt.binding_id==binding,DRAttempt.operation=='dispatch',DRAttempt.status=='running'))
            attempt.lease_expires_at=utcnow()-timedelta(seconds=1)
    receiver.hook=expire
    image=source_set['sources'][0]['image_sha256'];path=f'/integrations/dr/{binding}/api/v1/cases/{image}/admission'
    result=client.post(path,json={'revision':0,'action':'QUALITY_ACCEPTABLE'},headers={'Idempotency-Key':uid()})
    assert result.status_code==409 and result.json()['detail']['code']=='DR_LEASE_EXPIRED_OR_REPLACED'
    with SessionLocal() as db:
        attempt=db.scalar(select(DRAttempt).where(DRAttempt.binding_id==binding,DRAttempt.operation=='dispatch'))
        exchange=db.scalar(select(DRExchange).where(DRExchange.attempt_id==attempt.id))
        assert attempt.status=='quarantined' and exchange.outcome=='succeeded' and exchange.receipt is not None and exchange.quarantined
    calls=len(receiver.calls)
    assert client.post(path,json={'revision':0,'action':'QUALITY_ACCEPTABLE'},headers={'Idempotency-Key':uid()}).status_code==409
    assert client.post(BASE+f"/source-sets/{source_set['id']}/bindings",json={'transfer_consent':body['transfer_consent']},headers={'Idempotency-Key':uid()}).status_code==409
    assert len(receiver.calls)==calls


def test_final_grant_rows_lock_until_receipt_commit_and_lifecycle_is_audited(prepared,monkeypatch):
    client,source_set,binding,receiver,body=prepared
    now=utcnow()
    with SessionLocal.begin() as db:
        grant=DRCapabilityGrant(organization_id='org-demo',facility_id='facility-demo',user_id='user-clinician',
            capability='dr.report.sign',status='active',valid_from=now-timedelta(minutes=1),valid_until=now+timedelta(hours=1),
            verification_status='verified',evidence_reference='synthetic-validation:row-lock-and-audit',verifier_id='user-quality',version=1)
        db.add(grant);db.flush();grant_id=grant.id
    after_receiver,final_checked,release_final,revoker_started,revoker_done=Event(),Event(),Event(),Event(),Event()
    original_owned=gateway.owned
    def held_owned(*args,**kwargs):
        result=original_owned(*args,**kwargs)
        if after_receiver.is_set() and not final_checked.is_set():
            final_checked.set();assert release_final.wait(15)
        return result
    receiver.hook=lambda value:after_receiver.set()
    monkeypatch.setattr(gateway,'owned',held_owned)
    def revoke():
        with SessionLocal.begin() as db:
            row=db.get(DRCapabilityGrant,grant_id);row.status='revoked';row.version+=1
            revoker_started.set();db.flush()
        revoker_done.set()
    image=source_set['sources'][0]['image_sha256'];path=f'/integrations/dr/{binding}/api/v1/cases/{image}/admission'
    with ThreadPoolExecutor(max_workers=2) as pool:
        request=pool.submit(client.post,path,json={'revision':0,'action':'QUALITY_ACCEPTABLE'},headers={'Idempotency-Key':uid()})
        try:
            assert final_checked.wait(10)
            revocation=pool.submit(revoke);assert revoker_started.wait(10)
            assert not revoker_done.wait(.25),'Grant revocation committed before final HIS authorization transaction'
        finally:release_final.set()
        result=request.result(timeout=15);assert result.status_code==200,result.text
        revocation.result(timeout=15);assert revoker_done.is_set()
    history=client.get(BASE+f'/capability-grants/{grant_id}/history')
    assert history.status_code==200,history.text
    events=history.json()['events'];assert [e['version'] for e in events]==[1,2]
    assert [e['operation'] for e in events]==['INSERT','UPDATE']
    assert events[0]['old_snapshot'] is None and events[1]['old_snapshot']['status']=='active'
    assert events[1]['new_snapshot']['status']=='revoked' and events[1]['database_principal']=='his_test'
    assert all(e['actor_user_id'] is None for e in events)
    assert login('imaging').get(BASE+f'/capability-grants/{grant_id}/history').status_code==404
    with SessionLocal() as db:
        with pytest.raises(DBAPIError):db.execute(text('UPDATE dr_capability_grant_events SET database_principal=:who WHERE grant_id=:id'),{'who':'forged-human','id':grant_id})


def test_bound_mutation_rejects_boolean_revision_and_duplicate_json(prepared):
    client,source_set,binding,receiver,body=prepared
    image=source_set['sources'][0]['image_sha256'];path=f'/integrations/dr/{binding}/api/v1/cases/{image}/admission'
    calls=len(receiver.calls)
    response=client.post(path,json={'revision':True,'action':'QUALITY_ACCEPTABLE'},headers={'Idempotency-Key':uid()})
    assert response.status_code==422 and response.json()['detail']['code']=='DR_STRICT_REVISION_REQUIRED'
    response=client.post(path,content='{"revision":0,"revision":1,"action":"QUALITY_ACCEPTABLE"}',
        headers={'Content-Type':'application/json','Idempotency-Key':uid()})
    assert response.status_code==422 and len(receiver.calls)==calls
