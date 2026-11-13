"""Additional canonical clinical assertions on disposable PostgreSQL only."""
import base64,hashlib,json,os,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select,func
from backend.app.main import app
from backend.app.db import engine,SessionLocal
from backend.app import models as c,models_clinical as m
from backend.app.auth import password_hasher
from backend.app.common import uid

PASSWORD='SyntheticAdditionalClinicalOnly-2026!'
RECORDS=[]

@pytest.fixture(scope='module',autouse=True)
def disposable_database():
 assert engine.dialect.name=='postgresql'
 assert engine.url.database.endswith(('_test','_tests'))
 assert os.environ.get('HIS_TEST_DATABASE_URL')==os.environ.get('DATABASE_URL')
 subprocess.run([sys.executable,'-m','alembic','-c','backend/alembic.ini','upgrade','head'],check=True)
 from backend.app.seed import seed
 with SessionLocal.begin() as db:seed(db,PASSWORD)
 yield
 output=Path('evidence/fullsystem/windows-20261113/clinical-additional-records.json')
 output.parent.mkdir(parents=True,exist_ok=True)
 output.write_text(json.dumps({'observed_at':datetime.now(timezone.utc).isoformat(),'method':'EXECUTED_HTTP_POSTGRESQL_SYNTHETIC','browser':'NOT_RUN','records':RECORDS},indent=2)+'\n',encoding='utf-8')

class Actor:
 def __init__(self,username):
  self.client=TestClient(app)
  response=self.client.post('/api/v2/auth/login',json={'username':username,'password':PASSWORD})
  assert response.status_code==200,response.text
  self.csrf=response.json()['csrf_token']
 def post(self,path,data,key=None,status=200):
  response=self.client.post('/api/v2'+path,json=data,headers={'X-CSRF-Token':self.csrf,'Idempotency-Key':key or uid()})
  assert response.status_code==status,response.text
  return response.json()
 def create(self,domain,**fields):return self.post('/clinical/'+domain+'/records',fields,status=201)
 def act(self,domain,row,action,key=None,status=200,**fields):
  return self.post(f'/clinical/{domain}/records/{row["id"]}/actions',{'version':row['version'],'action':action,**fields},key,status)

def context(number=1):return {'patient_id':f'patient-{number:03}','encounter_id':f'encounter-{number:03}'}

def synthetic_actor(role,patient=1):
 username='acceptance-'+uid();identifier=uid()
 with SessionLocal.begin() as db:
  db.add(c.User(id=identifier,organization_id='org-demo',username=username,display_name='Synthetic acceptance '+role,password_hash=password_hasher.hash(PASSWORD),status='active'));db.flush()
  db.add(c.Membership(user_id=identifier,facility_id='facility-demo',role=role))
  db.add(c.CareAssignment(user_id=identifier,patient_id=f'patient-{patient:03}'))
 return Actor(username),identifier

def events(db,identifier):
 return db.scalar(select(func.count()).select_from(m.ClinicalEvent).where(m.ClinicalEvent.record_id==identifier))

def test_d04_lost_response_admission_request_replay_creates_exactly_one_admission():
 nurse=Actor('nurse')
 row=nurse.create('D04',**context(),presenting_complaint='Synthetic admission replay')
 row=nurse.act('D04',row,'assessed',triage_level='manual',assessment='Manual synthetic assessment')
 row=nurse.act('D04',row,'in_care');before=row;key=uid()
 with SessionLocal() as db:count=db.scalar(select(func.count()).select_from(m.Admission))
 committed=nurse.act('D04',before,'admission_requested',key=key,disposition_reason='Synthetic requested admission')
 # The client discarded the first response; retry preserves the original version/payload/key.
 replay=nurse.act('D04',before,'admission_requested',key=key,disposition_reason='Synthetic requested admission')
 assert replay==committed
 with SessionLocal() as db:
  assert db.scalar(select(func.count()).select_from(m.Admission))==count+1
  admission=db.get(m.Admission,committed['admission_id'])
  assert admission.patient_id=='patient-001' and admission.encounter_id=='encounter-001'
  assert events(db,admission.id)==1
 RECORDS.append({'domain':'D04','emergency_id':committed['id'],'admission_id':admission.id,'assertions':['lost-response same-key replay equal','one Admission','one admission history event']})

def test_d05_transfer_releases_old_bed_and_preserves_assignments():
 nurse=Actor('nurse');admission=nurse.create('D05',**context(2),admission_reason='Synthetic bed transfer')
 admission=nurse.act('D05',admission,'admitted',bed_id='bed-001')
 with SessionLocal() as db:original=db.scalar(select(m.BedAssignment.id).where(m.BedAssignment.admission_id==admission['id']))
 admission=nurse.act('D05',admission,'transfer_requested');admission=nurse.act('D05',admission,'admitted',bed_id='bed-002')
 with SessionLocal() as db:
  assignments=list(db.scalars(select(m.BedAssignment).where(m.BedAssignment.admission_id==admission['id'])))
  assert len(assignments)==2
  old=db.get(m.BedAssignment,original);assert old.bed_id=='bed-001' and old.ended_at is not None
  active=[a for a in assignments if a.ended_at is None];assert len(active)==1 and active[0].bed_id=='bed-002'
  assert db.get(m.Admission,admission['id']).current_bed_id=='bed-002'
 other=nurse.create('D05',**context(3),admission_reason='Synthetic reuse freed bed')
 other=nurse.act('D05',other,'admitted',bed_id='bed-001');assert other['current_bed_id']=='bed-001'
 detail=nurse.client.get('/api/v2/clinical/D05/records/'+admission['id']);assert detail.status_code==200
 assert {a['id'] for a in detail.json()['bed_history']}=={a.id for a in assignments}
 RECORDS.append({'domain':'D05','admission_id':admission['id'],'bed_assignment_ids':[a.id for a in assignments],'other_admission_id':other['id'],'assertions':['original assignment retained with end time','one active new bed','old bed reusable','detail history matches persisted IDs']})

def test_d06_distinct_recipient_only_acknowledges_without_losing_linked_task():
 sender=Actor('nurse');recipient,recipient_id=synthetic_actor('nurse');wrong,wrong_id=synthetic_actor('nurse')
 task=sender.post('/tasks',{**context(),'domain':'D06','kind':'followup','title':'Synthetic pending handover task'},status=201)
 hand=sender.create('D06',**context(),summary='Synthetic sender to distinct receiver',pending_tasks='Follow up same task',task_ids=task['id'],receiving_staff_id=recipient_id)
 hand=sender.act('D06',hand,'signed')
 with SessionLocal() as db:before_events=events(db,hand['id'])
 wrong.act('D06',hand,'acknowledged',status=403)
 with SessionLocal() as db:
  current=db.get(m.Handover,hand['id']);assert current.version==hand['version'] and current.acknowledged_by is None
  assert events(db,hand['id'])==before_events
 hand=recipient.act('D06',hand,'acknowledged')
 assert hand['signed_by']=='user-nurse' and hand['acknowledged_by']==recipient_id
 with SessionLocal() as db:
  link=db.get(m.HandoverTask,(hand['id'],task['id']));assert link is not None and link.task_version==task['version']
  persisted=db.get(c.Task,task['id']);assert persisted.status=='open' and persisted.encounter_id=='encounter-001' and persisted.patient_id=='patient-001'
  assert events(db,hand['id'])==before_events+1
 RECORDS.append({'domain':'D06','handover_id':hand['id'],'task_id':task['id'],'sender_id':'user-nurse','recipient_id':recipient_id,'denied_user_id':wrong_id,'assertions':['same-facility wrong recipient denied without partial history/version','distinct designated recipient acknowledged','same pending task/version retained']})

def test_d19_cancelled_meal_cannot_prepare_or_leave_partial_history():
 nurse=Actor('nurse');row=nurse.create('D19',**context(),diet_description='Manual synthetic diet',allergy_note='Manual synthetic allergy',meal_period=uid())
 row=nurse.act('D19',row,'reviewed');row=nurse.act('D19',row,'cancelled')
 with SessionLocal() as db:before_events=events(db,row['id']);count=db.scalar(select(func.count()).select_from(m.DietOrder))
 nurse.act('D19',row,'prepared',status=409)
 with SessionLocal() as db:
  current=db.get(m.DietOrder,row['id']);assert current.status=='cancelled' and current.version==row['version']
  assert events(db,row['id'])==before_events
  assert db.scalar(select(func.count()).select_from(m.DietOrder))==count
 RECORDS.append({'domain':'D19','diet_order_id':row['id'],'assertions':['cancelled preparation rejected','version/history/record count unchanged']})

def test_d11_actual_file_get_denies_wrong_patient_and_noncontent_roles():
 clinician=Actor('clinician');imaging=Actor('imaging')
 order=clinician.post('/orders',{**context(),'kind':'imaging','code':'SYNTHETIC','label':'Synthetic scoped image','instructions':'Manual synthetic only','quantity':1,'unit':'test'},status=201)
 order=clinician.post('/orders/'+order['id']+'/transition',{'version':order['version'],'target':'signed'})
 row=imaging.create('D11',**context(),order_id=order['id'],modality='SYNTHETIC',body_site='synthetic')
 row=imaging.act('D11',row,'scheduled');payload=b'SYNTHETIC FILE BYTES; scoped acceptance only'
 row=imaging.act('D11',row,'acquired',file_base64=base64.b64encode(payload).decode(),file_mime='text/plain')
 path='/api/v2/clinical/D11/records/'+row['id']+'/file'
 allowed=imaging.client.get(path);assert allowed.status_code==200 and allowed.content==payload
 assert hashlib.sha256(allowed.content).hexdigest()==row['file_sha256']
 allowed_clinician=clinician.client.get(path);assert allowed_clinician.status_code==200 and allowed_clinician.content==payload
 with SessionLocal() as db:
  downloads=list(db.scalars(select(c.AuditEvent).where(c.AuditEvent.entity_id==row['id'],c.AuditEvent.action=='file.download')))
  assert len(downloads)==2
  assert {event.actor_id for event in downloads}=={'user-imaging','user-clinician'}
  assert all(event.details=={'sha256':row['file_sha256']} for event in downloads)
 limited,limited_id=synthetic_actor('clinician',patient=2)
 for username,actor in [('different-care-patient',limited),('auditor',Actor('auditor')),('registration',Actor('registration'))]:
  response=actor.client.get(path)
  assert response.status_code in (403,404),(username,response.status_code)
  assert payload not in response.content and 'content-disposition' not in response.headers
 with SessionLocal() as db:
  assert db.scalar(select(func.count()).select_from(c.AuditEvent).where(c.AuditEvent.entity_id==row['id'],c.AuditEvent.action=='file.download'))==2
 RECORDS.append({'domain':'D11','study_id':row['id'],'file_sha256':row['file_sha256'],'limited_clinician_id':limited_id,'download_audit_ids':[event.id for event in downloads],'assertions':['authorized imaging and clinician bytes/checksum verified','file audit stores hash only','actual file GET denied across patient care scope','auditor and registration raw-file denied without bytes or success audit']})
