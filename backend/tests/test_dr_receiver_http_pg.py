"""Actual HIS→HTTP→isolated derivative process, with two PostgreSQL stores."""
import os
assert os.getenv('HIS_TEST_DATABASE_URL') and os.environ['HIS_TEST_DATABASE_URL']==os.environ.get('DATABASE_URL'), 'Disposable PostgreSQL wrapper required'

from datetime import timedelta
import base64
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import time

import httpx
import psycopg
from psycopg import sql
import pytest
from sqlalchemy import func,select

from backend.app.common import digest,uid,utcnow
from backend.app.db import SessionLocal,engine
from backend.app.dr_client import patient_key
from backend.app.dr_protocol import WorkspaceScope
from backend.app.models import InferenceRun,Task
from backend.app.models_clinical import ImagingStudy
from backend.app.models_dr import DRCapabilityGrant,DRReportReceipt
from backend.app.seed import seed
from backend.app.storage import file_store
from backend.tests.test_dr_gateway_pg import BASE,fixture_sources,login

ROOT=Path(__file__).resolve().parents[2]
DERIVATIVE=ROOT.parent/'carebalance-dr-screening'
PYTHON=DERIVATIVE/'local-state/carebalance-venv/Scripts/python.exe'


@pytest.mark.parametrize('public_jpeg',[False,True],ids=['synthetic-png','public-jpeg-protocol-fixture'])
def test_actual_bilateral_manual_report_and_other_eye_freshness(tmp_path,monkeypatch,public_jpeg):
    if not PYTHON.is_file():pytest.skip('Independent DR receiver test environment absent; actual HTTP interop NOT_RUN')
    assert engine.url.database=='his_test'
    with SessionLocal.begin() as db:seed(db,os.environ['HIS_SEED_PASSWORD'])
    client=login()
    env={k:v for k,v in os.environ.items() if k in {'PATH','SYSTEMROOT','TEMP','TMP','USERPROFILE','LOCALAPPDATA','APPDATA'}}
    env.update(PYTHONPATH=str(DERIVATIVE),PYTHONDONTWRITEBYTECODE='1',PYTHONIOENCODING='utf-8')
    # The fixture is generated from code in the independent derivative; no real
    # retinal image, existing sample folder, original runtime or model is used.
    extension='jpg' if public_jpeg else 'png'
    generate='from pathlib import Path;from dr_support.images import synthetic_image;from PIL import Image;import io,sys;d=synthetic_image().data;root=Path(sys.argv[1]);ext=sys.argv[2];a=Image.open(io.BytesIO(d)).convert("RGB");a.save(root/("left."+ext));a.paste((1,2,3),(0,0,100,100));a.save(root/("right."+ext))'
    result=subprocess.run([str(PYTHON),'-c',generate,str(tmp_path),extension],cwd=tmp_path,env=env,capture_output=True,text=True,timeout=20)
    assert result.returncode==0,result.stderr
    images=[(tmp_path/('left.'+extension)).read_bytes(),(tmp_path/('right.'+extension)).read_bytes()];original_images=images.copy()
    if public_jpeg:
        # Exercise the actual D11 acquisition endpoint separately from the
        # direct database fixtures used to keep the two-process test focused.
        def post(actor,path,payload,status=200):
            reply=actor.post('/api/v2'+path,json=payload,headers={'Idempotency-Key':uid()})
            assert reply.status_code==status,reply.text
            return reply.json()
        order=post(client,'/orders',{'patient_id':'patient-001','encounter_id':'encounter-001','kind':'imaging',
            'code':'AUTHORED-JPEG-TEST','label':'Authored JPEG protocol fixture','instructions':'No clinical inference',
            'quantity':1,'unit':'image'},201)
        order=post(client,'/orders/'+order['id']+'/transition',{'version':order['version'],'target':'signed'})
        imaging=login('imaging')
        study=post(imaging,'/clinical/D11/records',{'patient_id':'patient-001','encounter_id':'encounter-001',
            'order_id':order['id'],'modality':'CFP','body_site':'Authored protocol fixture'},201)
        path='/clinical/D11/records/'+study['id']+'/actions'
        study=post(imaging,path,{'version':study['version'],'action':'scheduled'})
        post(imaging,path,{'version':study['version'],'action':'acquired','file_mime':'image/jpeg',
            'file_base64':base64.b64encode(b'not a JPEG').decode()},422)
        study=post(imaging,path,{'version':study['version'],'action':'acquired','file_mime':'image/jpeg',
            'file_base64':base64.b64encode(original_images[0]).decode()})
        assert study['file_mime']=='image/jpeg' and study['file_sha256']==hashlib.sha256(original_images[0]).hexdigest()
        downloaded=imaging.get('/api/v2/clinical/D11/records/'+study['id']+'/file')
        assert downloaded.status_code==200 and downloaded.content==original_images[0]
        assert downloaded.headers['content-type']=='image/jpeg'
    body=fixture_sources(2,png_producer=lambda label:images.pop(0),evidence_reference='authored-synthetic:derivative-generator-http-interop-v1',public=public_jpeg)
    response=client.post(BASE+'/source-sets',json=body,headers={'Idempotency-Key':uid()})
    assert response.status_code==200,response.text
    source_set=response.json();scope=source_set['scope'];key='dedicated-actual-http-test-'+uid()
    database='carebalance_dr_test_his_'+uid().replace('-','')[:12]
    dsn=engine.url.render_as_string(hide_password=False).replace('postgresql+psycopg://','postgresql://')
    with psycopg.connect(dsn,autocommit=True) as connection:
        connection.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(database)))
    target=engine.url.set(database=database).render_as_string(hide_password=False).replace('postgresql+psycopg://','postgresql://')
    env.update(CAREBALANCE_DR_ENABLED='true',CAREBALANCE_DR_DATABASE_URL=target,CAREBALANCE_DR_EXPECTED_DATABASE=database,
        CAREBALANCE_DR_KEY=key,CAREBALANCE_DR_SCOPE_JSON=json.dumps(scope))
    prepare=subprocess.run([str(PYTHON),'-m','carebalance_bridge.app','prepare'],cwd=tmp_path,env=env,capture_output=True,text=True,timeout=40)
    assert prepare.returncode==0,prepare.stderr
    with socket.socket() as probe:probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
    origin=f'http://127.0.0.1:{port}';workspace='cb-'+digest(scope)[:32]
    registry=tmp_path/'registry.json';registry.write_text(json.dumps({'version':1,'destinations':[
        {'id':'fixture','origin':origin,'key':key,'scope':scope,'workspace_id':workspace}]}));registry.chmod(0o600)
    monkeypatch.setenv('HIS_DR_ENABLED','true');monkeypatch.setenv('HIS_DR_DESTINATIONS_FILE',str(registry))
    log=(tmp_path/'receiver-private.log').open('w',encoding='utf-8')
    process=subprocess.Popen([str(PYTHON),'-m','uvicorn','carebalance_bridge.app:create_app','--factory',
        '--host','127.0.0.1','--port',str(port),'--workers','1','--no-access-log'],cwd=tmp_path,env=env,stdout=log,stderr=subprocess.STDOUT)
    grant_ids=[]
    try:
        for _ in range(100):
            if process.poll() is not None:raise AssertionError('Receiver stopped: '+(tmp_path/'receiver-private.log').read_text()[-3000:])
            try:
                if httpx.get(origin+'/ready',timeout=1,trust_env=False).status_code==200:break
            except httpx.HTTPError:pass
            time.sleep(.1)
        else:raise AssertionError('Dedicated receiver startup timeout')
        assert httpx.get(origin+'/v1/cases',trust_env=False).status_code==404
        with SessionLocal() as db:before_runs=db.scalar(select(func.count()).select_from(InferenceRun))
        imported=client.post(BASE+f"/source-sets/{source_set['id']}/bindings",json={'transfer_consent':body['transfer_consent']},headers={'Idempotency-Key':uid()})
        assert imported.status_code==200,imported.text
        binding=imported.json()['binding_id'];prefix=f'/integrations/dr/{binding}/api';ids=[m['image_sha256'] for m in source_set['sources']]
        assert len(client.get(prefix+'/v1/cases').json())==2
        def case(id):
            response=client.get(prefix+'/v1/cases/'+id);assert response.status_code==200,response.text
            return response.json()
        def mutate(id,suffix,body,method='POST',key=None):
            response=client.request(method,prefix+'/v1/cases/'+id+'/'+suffix,json=body,headers={'Idempotency-Key':key or uid()})
            assert response.status_code==200,response.text
            return response.json()
        # Default clinician can explicitly assess quality/confirm source, but
        # cannot silently become a retinal grader or a physician signer.
        for index,id in enumerate(ids):
            current=case(id)
            mutate(id,'admission',{'revision':current['revision'],'action':'QUALITY_ACCEPTABLE','reviewer':'spoof','note':'Explicit authored fixture quality review'})
            current=case(id)
            mutate(id,'confirm-image',{'revision':current['revision'],'reviewer':'spoof','patient_key':patient_key(WorkspaceScope(**scope)),
                'visit_key':scope['encounter_id'],'laterality':'LEFT' if index==0 else 'RIGHT','retinal_modality':'CFP','captured_at':None})
        current=case(ids[0]);denied=client.post(prefix+'/v1/cases/'+ids[0]+'/review',json={'revision':current['revision'],'action':'CORRECT_GRADE','grade':1},headers={'Idempotency-Key':uid()})
        assert denied.status_code==403
        now=utcnow()
        with SessionLocal.begin() as db:
            for capability in ['dr.grade.confirm','dr.report.sign']:
                grant=DRCapabilityGrant(organization_id='org-demo',facility_id='facility-demo',user_id='user-clinician',capability=capability,
                    status='active',valid_from=now-timedelta(minutes=1),valid_until=now+timedelta(hours=1),verification_status='verified',
                    evidence_reference='synthetic-validation:declared-http-test-credential-only',verifier_id='user-quality',version=1)
                db.add(grant);db.flush();grant_ids.append(grant.id)
        for id in ids:
            current=case(id);graded=mutate(id,'review',{'revision':current['revision'],'action':'CORRECT_GRADE','grade':1,'reviewer':'fake-physician'})
            assert graded['clinician_review']['reviewer']=='user-clinician'
        current=case(ids[0]);annotated=mutate(ids[0],'annotations',{'revision':current['revision'],'reviewer':'spoof',
            'annotations':[{'shape_id':'authored-rectangle','type':'rectangle','label':'HEMORRHAGE','geometry':{'x':20,'y':30,'width':10,'height':15},'locked':True}]},'PUT')
        assert annotated['human_annotations'][0]['geometry']=={'x':20.0,'y':30.0,'width':10.0,'height':15.0}
        assert annotated['human_annotations'][0]['reviewer']=='user-clinician'
        current=case(ids[0]);sign_key=uid();sign_body={'revision':current['revision'],'reviewer':'fake-signer','sign':True,
            'report':{'hn':patient_key(WorkspaceScope(**scope)),'patient_name':'','left':{'quality':'GRADABLE','grade':1},
                'right':{'quality':'GRADABLE','grade':1},'decision':'NOT_REFER'}}
        signed=mutate(ids[0],'screening-report',sign_body,'PUT',sign_key)
        assert signed['screening_report']['status']=='SIGNED'
        assert signed['screening_report']['signed_by']['name']=='user-clinician'
        assert mutate(ids[0],'screening-report',sign_body,'PUT',sign_key)==signed
        def read():
            response=client.post(BASE+f'/bindings/{binding}/read-report',json={'case_id':ids[0]},headers={'Idempotency-Key':uid()})
            assert response.status_code==200,response.text
            return response.json()['receipt']
        first=read();assert first['review_freshness']['state']=='CURRENT'
        assert first['snapshot']['report_sha256']==digest(first['snapshot']['report'])
        current=case(ids[1]);mutate(ids[1],'review',{'revision':current['revision'],'action':'CORRECT_GRADE','grade':2})
        changed=read();assert changed['review_freshness']['state']=='CHANGED'
        assert changed['review_freshness']['changed_case_ids']==[ids[1]]
        assert changed['snapshot']['report_sha256']==first['snapshot']['report_sha256']
        assert changed['snapshot']['report_state']=='SIGNED'
        printed=client.get(f'/integrations/dr/{binding}/print/'+ids[0]);assert printed.status_code==200
        assert 'current review freshness is not assessed' in printed.text
        for index,id in enumerate(ids):
            response=client.get(prefix+'/v1/images/'+id)
            assert response.status_code==200 and response.content==original_images[index]
        with SessionLocal() as db:
            assert db.get(Task,body['task_id']).status=='open'
            assert db.scalar(select(func.count()).select_from(InferenceRun))==before_runs
            receipts=db.scalars(select(DRReportReceipt).where(DRReportReceipt.binding_id==binding)).all()
            assert len(receipts)==2 and {r.receipt['review_freshness']['state'] for r in receipts}=={'CURRENT','CHANGED'}
            for index,selection in enumerate(body['sources']):
                source=db.get(ImagingStudy,selection['source_id'])
                assert source.version==5 and file_store().read(source.file_path,source.file_sha256)==original_images[index]
    finally:
        process.terminate()
        try:process.wait(timeout=15)
        except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
        log.close()
        with SessionLocal.begin() as db:
            for id in grant_ids:
                grant=db.get(DRCapabilityGrant,id)
                if grant.status=='active':grant.status='revoked';grant.version+=1
