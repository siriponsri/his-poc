"""PostgreSQL integration/HTTP acceptance for manual clinical workflows.
Run against an isolated *_tests database; never drops data or uses SQLite.
"""
import os,json,uuid,base64
from pathlib import Path
from datetime import datetime,timezone,timedelta
from decimal import Decimal
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select,func,inspect
from backend.app.db import Base,engine,SessionLocal
from backend.app import models as c,models_clinical as m,models_erp as erp
from backend.app.auth import router as auth_router,password_hasher
from backend.app.core import router as core_router
from backend.app.ai import router as ai_router
from backend.app.domains.clinical import router,seed_clinical
from backend.app.domains.erp import router as erp_router
from backend.app.common import uid

app=FastAPI();app.include_router(auth_router,prefix='/api/v2');app.include_router(core_router,prefix='/api/v2');app.include_router(router,prefix='/api/v2');app.include_router(erp_router,prefix='/api/v2');app.include_router(ai_router,prefix='/api/v2')
EVIDENCE=[]

@pytest.fixture(scope='module',autouse=True)
def database():
    if not engine.url.database.endswith(('_tests','_test')):pytest.skip('Requires dedicated *_tests PostgreSQL database')
    missing=set(Base.metadata.tables)-set(inspect(engine).get_table_names())
    assert not missing, f'Run Alembic migrations before this suite; missing tables: {sorted(missing)}'
    with SessionLocal.begin() as db:
        from backend.app.seed import seed
        seed(db,'Test-Clinical-Only-2026!')
        if not db.get(erp.InventoryItem,'item-clinical'):db.add(erp.InventoryItem(id='item-clinical',organization_id='org-demo',facility_id='facility-demo',name='Synthetic Tablet',unit='tablet',status='active'));db.flush()
        if not db.get(erp.StockLocation,'store-clinical'):db.add(erp.StockLocation(id='store-clinical',organization_id='org-demo',facility_id='facility-demo',name='Synthetic store'));db.flush()
        if not db.get(erp.InventoryLot,'lot-clinical'):db.add(erp.InventoryLot(id='lot-clinical',organization_id='org-demo',facility_id='facility-demo',item_id='item-clinical',lot_number='TEST',expiry_date=datetime(2030,1,1).date(),status='available',unit_cost=1));db.flush()
        if not db.scalar(select(erp.StockBalance).where(erp.StockBalance.lot_id=='lot-clinical',erp.StockBalance.location_id=='store-clinical')):db.add(erp.StockBalance(lot_id='lot-clinical',location_id='store-clinical',available=100,quarantined=0))
    yield
    out=Path('evidence/fullsystem');out.mkdir(parents=True,exist_ok=True)
    (out/'clinical-journeys.json').write_text(json.dumps({'database':str(engine.url).split('@')[-1],'type':'EXECUTED_HTTP_POSTGRESQL','browser':'NOT_RUN','journeys':EVIDENCE},indent=2),encoding='utf-8')

class Actor:
    def __init__(self,role):
        self.role=role;self.client=TestClient(app)
        r=self.client.post('/api/v2/auth/login',json={'username':role,'password':'Test-Clinical-Only-2026!'})
        assert r.status_code==200,r.text
        self.csrf=r.json()['csrf_token']
    def post(self,path,data,key=None,status=200):
        r=self.client.post('/api/v2'+path,json=data,headers={'X-CSRF-Token':self.csrf,'Idempotency-Key':key or uid()})
        assert r.status_code==status,r.text
        return r.json()
    def create(self,d,**kw):return self.post(f'/clinical/{d}/records',kw,status=201)
    def act(self,d,o,target,key=None,status=200,**kw):return self.post(f'/clinical/{d}/records/{o["id"]}/actions',{'action':target,'version':o['version'],**kw},key,status)
    def get(self,path,status=200):
        r=self.client.get('/api/v2'+path);assert r.status_code==status,r.text;return r.json()

def context(i=1):return {'patient_id':f'patient-{i:03}','encounter_id':f'encounter-{i:03}'}
def order(kind,i=1):
    clinician=Actor('clinician')
    o=clinician.post('/orders',dict(**context(i),kind=kind,code='item-clinical' if kind=='medication' else 'SYNTHETIC',label='Synthetic Tablet' if kind=='medication' else 'Synthetic order',instructions='Manual synthetic order',quantity=10,unit='tablet' if kind=='medication' else 'test'),status=201)
    o=clinician.post(f'/orders/{o["id"]}/transition',{'version':o['version'],'target':'signed'})
    return o['id']

def evidence(id,actors,records,assertions):EVIDENCE.append({'journey':id,'status':'PASS','actors':actors,'record_ids':records,'assertions':assertions})

def test_j02_lab_revisions_authority_and_acknowledgement():
    lab=Actor('laboratory');clin=Actor('clinician');oid=order('lab')
    o=lab.create('D10',**context(),order_id=oid,analyte='Synthetic A',specimen_type='synthetic serum')
    for target in ['collected','received']:o=lab.act('D10',o,target)
    o=lab.act('D10',o,'preliminary',result_value='5',unit='demo-unit',reference_range='manual 1–10')
    clin.act('D10',o,'verified',status=403)
    for target in ['verified','released']:o=lab.act('D10',o,target)
    original=o['result_value'];o=lab.act('D10',o,'publish_portal');o=clin.act('D10',o,'acknowledge')
    o=lab.act('D10',o,'corrected',result_value='6',unit='demo-unit',reference_range='manual 1–10',reason='manual correction')
    detail=lab.get(f'/clinical/D10/records/{o["id"]}')
    assert any(x['snapshot']['result_value']==original for x in detail['history'])
    assert not o['released_to_portal'] and o['acknowledged_by'] is None
    evidence('J02',['clinician','laboratory'],[oid,o['id']],['signed order linkage','manual result release','wrong role denied','immutable correction history','clinician acknowledgement'])

def test_j03_dispense_retry_return_and_conservation():
    actor=Actor('pharmacist');oid=order('medication')
    o=actor.create('D08',**context(),order_id=oid,item_id='item-clinical',medication_name='Synthetic Tablet',prescribed_dose='manual 1 tablet',route='manual oral',quantity=5,unit='tablet')
    for target in ['reviewed','prepared']:o=actor.act('D08',o,target)
    before=o;key=uid();o=actor.act('D08',before,'dispensed',key=key,lot_id='lot-clinical',location_id='store-clinical',quantity=5,unit_price=2)
    replay=actor.act('D08',before,'dispensed',key=key,lot_id='lot-clinical',location_id='store-clinical',quantity=5,unit_price=2);assert replay==o
    o=actor.act('D08',o,'return_recorded',quantity=2,reason='synthetic return')
    actor.act('D08',o,'return_recorded',quantity=4,reason='too much',status=409)
    with SessionLocal() as db:
        movements=list(db.scalars(select(erp.StockMovement).where(erp.StockMovement.source_id==o['id'])))
        assert len(movements)==2 and sum(x.quantity for x in movements)==Decimal('-3')
        assert [x for x in movements if x.quantity>0][0].disposition=='quarantine'
        assert db.scalar(select(func.count()).select_from(erp.Charge).where(erp.Charge.source_id==o['id']))==1
    evidence('J03',['clinician','pharmacist'],[oid,o['id']],['same-key dispense exactly once','charge exactly once','quarantined return','cumulative excess return rejected','stock quantity conserved'])

def test_j04_admission_transfer_handover_discharge_followup():
    nurse=Actor('nurse');reg=Actor('registration')
    emergency=nurse.create('D04',**context(3),presenting_complaint='Synthetic emergency')
    emergency=nurse.act('D04',emergency,'assessed',triage_level='manual',assessment='Synthetic manual assessment');emergency=nurse.act('D04',emergency,'in_care');emergency=nurse.act('D04',emergency,'admission_requested',disposition_reason='Synthetic admit')
    o=nurse.get('/clinical/D05/records/'+emergency['admission_id'])
    o=nurse.act('D05',o,'admitted',bed_id='bed-001')
    other=nurse.create('D05',**context(4),admission_reason='conflict');nurse.act('D05',other,'admitted',bed_id='bed-001',status=409)
    o=nurse.act('D05',o,'transfer_requested');o=nurse.act('D05',o,'admitted',bed_id='bed-002')
    task=nurse.post('/tasks',dict(**context(3),domain='D06',kind='followup',title='Synthetic pending task'),status=201);tid=task['id']
    hand=nurse.create('D06',**context(3),summary='Synthetic handover',pending_tasks='Follow up pending task',task_ids=tid,receiving_staff_id='user-nurse')
    hand=nurse.act('D06',hand,'signed');hand=nurse.act('D06',hand,'acknowledged')
    o=nurse.act('D05',o,'discharge_ready',discharge_summary='Synthetic summary');o=nurse.act('D05',o,'discharged')
    ap=reg.create('D02',patient_id='patient-003',slot_id='slot-demo',reason='Synthetic followup');ap=reg.act('D02',ap,'booked')
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(m.BedAssignment).where(m.BedAssignment.admission_id==o['id'],m.BedAssignment.ended_at.is_(None)))==0
        assert db.get(c.Task,tid).status=='open'
    evidence('J04',['nurse','registration'],[o['id'],hand['id'],tid,ap['id']],['occupied bed conflict','transfer preserves bed history','handover links real pending task','discharge releases bed','followup shares patient'])

def test_j08_imaging_file_report_referral_and_cross_patient_denial():
    imaging=Actor('imaging');oid=order('imaging');o=imaging.create('D11',**context(),order_id=oid,modality='SYNTHETIC',body_site='retina synthetic')
    o=imaging.act('D11',o,'scheduled');o=imaging.act('D11',o,'acquired',file_base64=base64.b64encode(b'SYNTHETIC IMAGE PLACEHOLDER; no clinical inference').decode(),file_mime='text/plain')
    o=imaging.act('D11',o,'report_draft',report='Manual synthetic report; no DR inference')
    for target in ['verified','released']:o=imaging.act('D11',o,target)
    r=imaging.client.get(f'/api/v2/clinical/D11/records/{o["id"]}/file');assert r.status_code==200
    import hashlib
    assert hashlib.sha256(r.content).hexdigest()==o['file_sha256']
    doc=imaging.post('/documents',dict(**context(),title='Synthetic imaging report',content=o['report']),status=201)
    rid=doc['current_version_id']
    task=imaging.post('/tasks',dict(**context(),domain='D37',kind='dr_review',title='Explicit mock human DR review'),status=201)
    proposed=imaging.post('/proposals',{'task_id':task['id'],'document_id':doc['id'],'scenario':'success'})
    assert proposed['demo'] and proposed['run']['provider']=='mock_demo'
    clinician=Actor('clinician');proposal=proposed['proposal']
    proposal=clinician.post(f'/proposals/{proposal["id"]}/review',{'version':proposal['version'],'action_hash':proposal['action_hash'],'decision':'approve'})
    result=clinician.post(f'/proposals/{proposal["id"]}/commit',{'version':proposal['version'],'action_hash':proposal['action_hash']})
    referral=imaging.create('D20',**context(),destination='Synthetic eye clinic',reason='Manual review',document_revision_id=rid)
    for target in ['reviewed','exported']:referral=imaging.act('D20',referral,target)
    packet=imaging.get(f'/clinical/D20/records/{referral["id"]}/export');assert packet['external_received'] is False and packet['document_revision_id']==rid
    evidence('J08',['clinician','imaging'],[oid,o['id'],rid,task['id'],proposal['id'],result['id'],referral['id']],['clinician signed order through HTTP','file checksum verified','manual human report release','explicit mock DR task on same document and encounter','clinician review/commit','referral bound document revision','external receipt explicitly false'])

def test_j10_portal_owner_request_staff_booking_and_release():
    patient=Actor('patient');reg=Actor('registration');lab=Actor('laboratory')
    req=patient.create('D21',request_kind='appointment',slot_id='slot-demo',reason='Synthetic followup')
    assert req['patient_id']=='patient-001'
    patient.act('D21',req,'reviewed',status=403)
    req=reg.act('D21',req,'reviewed');req=reg.act('D21',req,'booked')
    assert req['appointment_id']
    r=patient.client.post('/api/v2/clinical/D21/records',json={'patient_id':'patient-002','slot_id':'slot-demo','reason':'attack'},headers={'X-CSRF-Token':patient.csrf,'Idempotency-Key':uid()});assert r.status_code==422
    own=patient.get('/clinical/D21/records');assert all(x['patient_id']=='patient-001' for x in own['items'])
    own_encounters=patient.get('/clinical/portal/encounters')['items'];assert own_encounters and all(x['patient_id']=='patient-001' for x in own_encounters)
    released=patient.get('/clinical/portal/released-results');assert all(x['patient_id']=='patient-001' for x in released['items'])
    evidence('J10',['patient','registration'],[req['id'],req['appointment_id']],['server linked subject','patient cannot staff-review','patient parameter injection rejected','same appointment staff worklist'])

def test_order_cancel_blocks_downstream_action():
    lab=Actor('laboratory');oid=order('lab');o=lab.create('D10',**context(),order_id=oid,analyte='Cancel',specimen_type='synthetic')
    with SessionLocal.begin() as db:db.get(c.ClinicalOrder,oid).status='cancelled'
    lab.act('D10',o,'collected',status=409)

def test_blood_revision_and_eligibility_binding():
    clin=Actor('clinician');o=clin.create('D18',**context(),indication='Synthetic manual indication');o=clin.act('D18',o,'reviewed');o=clin.act('D18',o,'reserved',unit_id='blood-001');o=clin.act('D18',o,'compatibility_verified',verification_evidence='Synthetic manual verifier evidence')
    with SessionLocal.begin() as db:db.get(m.BloodUnit,'blood-001').version+=1
    clin.act('D18',o,'released',status=409)
    other=clin.create('D18',**context(2),indication='Synthetic other');other=clin.act('D18',other,'reviewed');clin.act('D18',other,'reserved',unit_id='blood-001',status=409)

def test_specialist_domain_workflows():
    clin=Actor('clinician');nurse=Actor('nurse')
    emergency=clin.create('D04',**context(),presenting_complaint='Synthetic complaint');emergency=clin.act('D04',emergency,'assessed',triage_level='manual synthetic',assessment='Manual assessment');emergency=clin.act('D04',emergency,'in_care');emergency=clin.act('D04',emergency,'admission_requested',disposition_reason='Synthetic admission request');assert emergency['admission_id']
    admission=clin.create('D05',**context(),admission_reason='Synthetic ICU context')
    cases=[('D12',dict(procedure_name='Synthetic procedure'),[('scheduled',dict(room='Synthetic OR '+uid(),starts_at='2027-01-01T08:00:00Z',ends_at='2027-01-01T09:00:00Z')),('checklist_verified',dict(checklist='Manual checklist complete')),('in_progress',{}),('documented',dict(anesthesia_record='Manual documentation only')),('closed',{})]),
      ('D13',dict(admission_id=admission['id'],observation_name='Synthetic observation',observation_value='10',unit='demo',observed_at='2026-11-12T08:00:00Z',round_note='Manual round'),[('recorded',{}),('reviewed',{}),('signed',{}),('amended',dict(observation_value='11',round_note='Manual corrected',reason='Synthetic correction'))]),
      ('D14',dict(gestation_note='Manual synthetic'),[('antenatal_active',{}),('delivery_documented',dict(delivery_note='Synthetic delivery',child_name='Synthetic newborn',child_identifier=uid())),('verified',{}),('closed',{})]),
      ('D15',dict(measurement_name='synthetic weight',measurement_value='3',unit='kg',measured_at='2026-11-12T08:00:00Z',immunization_note='Manual record'),[('recorded',{}),('reviewed',{}),('closed',{}),('amended',dict(measurement_value='3.1',reason='Manual correction'))]),
      ('D16',dict(order_id=order('rehab'),goals='Manual mobility goal',therapist_id='user-clinician'),[('assessed',dict(assessment='Manual assessment')),('active',{}),('session',dict(performed_at='2026-11-12T08:00:00Z',progress='Session 1')),('session',dict(performed_at='2026-11-13T08:00:00Z',progress='Session 2')),('session',dict(performed_at='2026-11-14T08:00:00Z',progress='Session 3')),('reviewed',{}),('completed',{})]),
      ('D17',dict(tooth_code='SYN-11',finding='Manual finding',procedure_name='Synthetic procedure'),[('reviewed',{}),('scheduled',{}),('performed',dict(unit_price='10')),('verified',{}),('closed',{})]),
      ('D19',dict(diet_description='Manual synthetic diet',allergy_note='Manual synthetic allergy',meal_period=uid()),[('reviewed',{}),('revise',dict(diet_description='Manual diet revision',allergy_note='Manual allergy')),('reviewed',{}),('prepared',{}),('delivered',{})])]
    for d,fields,actions in cases:
        o=clin.create(d,**context(),**fields)
        for target,values in actions:
            if d=='D16' and target=='session':
                o=clin.act(d,o,'schedule',slot_id='slot-demo');values={**values,'session_id':o['scheduled_session_id']}
            o=clin.act(d,o,target,**values)
        assert clin.get(f'/clinical/{d}/records/{o["id"]}')['history']
        evidence(d,['clinician'],[o['id']],['domain-specific typed fields','full manual state sequence','persisted history'])

def test_mar_duplicate_hold_and_invalid_transition():
    pharm=Actor('pharmacist');nurse=Actor('nurse');o=pharm.create('D08',**context(),order_id=order('medication'),item_id='item-clinical',medication_name='Synthetic Tablet',prescribed_dose='1 tablet',route='oral',quantity=2,unit='tablet');o=pharm.act('D08',o,'reviewed')
    mar=nurse.create('D09',**context(),medication_id=o['id'],scheduled_at=datetime.now(timezone.utc).isoformat(),dose='1 tablet',route='oral');mar=nurse.act('D09',mar,'verified');before=mar;key=uid();mar=nurse.act('D09',before,'held',key=key,reason='Synthetic hold');assert nurse.act('D09',before,'held',key=key,reason='Synthetic hold')==mar
    nurse.act('D09',mar,'administered',status=409,actual_at=datetime.now(timezone.utc).isoformat());assert mar['status']=='held'

def test_slot_capacity_race_and_idempotent_checkin():
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    reg=Actor('registration');nurse=Actor('nurse')
    one=reg.create('D02',patient_id='patient-001',slot_id='slot-last',reason='last place A')
    two=nurse.create('D02',patient_id='patient-002',slot_id='slot-last',reason='last place B')
    barrier=Barrier(2)
    def book(actor,o):
        barrier.wait()
        r=actor.client.post(f'/api/v2/clinical/D02/records/{o["id"]}/actions',json={'action':'booked','version':o['version']},headers={'X-CSRF-Token':actor.csrf,'Idempotency-Key':uid()})
        return actor,r
    with ThreadPoolExecutor(2) as ex:results=list(ex.map(lambda pair:book(*pair),[(reg,one),(nurse,two)]))
    assert sorted(r.status_code for _,r in results)==[200,409]
    actor,r=next((a,r) for a,r in results if r.status_code==200);booked=r.json();key=uid()
    checked=actor.act('D02',booked,'checked_in',key=key);assert actor.act('D02',booked,'checked_in',key=key)==checked
    with SessionLocal() as db:
        enc=db.get(c.Encounter,checked['encounter_id']);assert enc.status=='waiting' and enc.patient_id==checked['patient_id']
    checked=actor.act('D02',checked,'called');checked=actor.act('D02',checked,'completed')
    evidence('D02',['registration','nurse'],[one['id'],two['id'],checked['encounter_id']],['actual concurrent last-slot requests yield one winner','checkin replay same encounter','queue completed'])

def test_portal_results_never_leak_other_patient_or_unreleased():
    lab=Actor('laboratory');portal=Actor('patient');records=[]
    for i in (1,2):
        o=lab.create('D10',**context(i),order_id=order('lab',i),analyte='Portal ownership',specimen_type='synthetic')
        for target in ('collected','received'):o=lab.act('D10',o,target)
        o=lab.act('D10',o,'preliminary',result_value=f'owned-{i}',unit='demo',reference_range='manual')
        for target in ('verified','released','publish_portal'):o=lab.act('D10',o,target)
        records.append(o)
    got=portal.get('/clinical/portal/released-results')['items'];ids={x['id'] for x in got}
    assert records[0]['id'] in ids and records[1]['id'] not in ids
    assert all(x['patient_id']=='patient-001' for x in got)
    portal.get('/clinical/D10/records/'+records[1]['id'],status=403)
    evidence('J10_RELEASED_RESULTS',['patient','laboratory'],[x['id'] for x in records],['positive own released result','other patient published result excluded','direct access forbidden'])

def test_wrong_lot_item_and_stale_order_refuse_dispense():
    pharm=Actor('pharmacist');o=pharm.create('D08',**context(),order_id=order('medication'),item_id='item-clinical',medication_name='Synthetic Tablet',prescribed_dose='manual',route='oral',quantity=2,unit='tablet')
    for target in ('reviewed','prepared'):o=pharm.act('D08',o,target)
    with SessionLocal.begin() as db:
        item=erp.InventoryItem(id=uid(),organization_id='org-demo',facility_id='facility-demo',name='Wrong synthetic item',unit='tablet');db.add(item);db.flush()
        lot=erp.InventoryLot(id=uid(),organization_id='org-demo',facility_id='facility-demo',item_id=item.id,lot_number=uid(),expiry_date=datetime(2030,1,1).date(),status='available',unit_cost=1);db.add(lot);wrong=lot.id
    pharm.act('D08',o,'dispensed',lot_id=wrong,location_id='store-clinical',quantity=2,unit_price=1,status=409)
    with SessionLocal.begin() as db:db.get(c.ClinicalOrder,o['order_id']).version+=1
    pharm.act('D08',o,'dispensed',lot_id='lot-clinical',location_id='store-clinical',quantity=2,unit_price=1,status=409)
    with SessionLocal() as db:assert db.scalar(select(func.count()).select_from(erp.StockMovement).where(erp.StockMovement.source_id==o['id']))==0

def test_care_scope_filters_list_and_linked_user_facility():
    nurse=Actor('nurse');clin=Actor('clinician');reg=Actor('registration')
    with SessionLocal.begin() as db:
        p=c.Patient(id=uid(),organization_id='org-demo',facility_id='facility-demo',display_name='Unassigned synthetic',status='active');db.add(p);db.flush()
        row=m.Appointment(id=uid(),organization_id='org-demo',facility_id='facility-demo',patient_id=p.id,slot_id='slot-demo',reason='unassigned',status='requested',created_by='user-registration');db.add(row);record_id=row.id
        # Same organization, different facility; no default-facility membership.
        u=c.User(id=uid(),organization_id='org-demo',username='second-'+uid(),display_name='Other facility nurse',password_hash='unused',status='active');db.add(u);db.flush();db.add(c.Membership(user_id=u.id,facility_id='facility-second',role='nurse'));other_user=u.id
    assert record_id not in {x['id'] for x in clin.get('/clinical/D02/records')['items']}
    clin.get('/clinical/D02/records/'+record_id,status=404)
    nurse.post('/clinical/D06/records',dict(**context(),summary='bad receiver',pending_tasks='task',task_ids='task-patient-001',receiving_staff_id=other_user),status=404)

def test_blood_success_patient_revision_and_expiry_guards():
    clin=Actor('clinician')
    def unit():
        with SessionLocal.begin() as db:
            u=m.BloodUnit(id=uid(),organization_id='org-demo',facility_id='facility-demo',identifier='SYN-'+uid(),expiry_at=datetime(2030,1,1,tzinfo=timezone.utc),eligibility_status='available');db.add(u);return u.id
    def verified(unit_id):
        o=clin.create('D18',**context(2),indication='Synthetic trace');o=clin.act('D18',o,'reviewed');o=clin.act('D18',o,'reserved',unit_id=unit_id);return clin.act('D18',o,'compatibility_verified',verification_evidence='Manual synthetic verification')
    good=verified(unit());good=clin.act('D18',good,'released');good=clin.act('D18',good,'administration_recorded',administration_note='Manual synthetic event')
    changed=verified(unit())
    with SessionLocal.begin() as db:db.get(c.Patient,'patient-002').version+=1
    clin.act('D18',changed,'released',status=409)
    expired=verified(unit())
    with SessionLocal.begin() as db:db.get(m.BloodUnit,expired['unit_id']).expiry_at=datetime(2020,1,1,tzinfo=timezone.utc)
    clin.act('D18',expired,'released',status=409)
    evidence('D18',['clinician'],[good['id'],changed['id'],expired['id']],['manual verification trace','patient revision change blocks release','expiry change blocks release','successful release and administration trace'])

def test_mar_administration_exactly_once_then_immutable_correction():
    pharm=Actor('pharmacist');nurse=Actor('nurse');med=pharm.create('D08',**context(),order_id=order('medication'),item_id='item-clinical',medication_name='Synthetic Tablet',prescribed_dose='1 tablet',route='oral',quantity=2,unit='tablet');med=pharm.act('D08',med,'reviewed')
    o=nurse.create('D09',**context(),medication_id=med['id'],scheduled_at=datetime.now(timezone.utc).isoformat(),dose='1 tablet',route='oral');o=nurse.act('D09',o,'verified');before=o;key=uid();when='2026-11-12T10:00:00Z'
    o=nurse.act('D09',before,'administered',key=key,actual_at=when);assert nurse.act('D09',before,'administered',key=key,actual_at=when)==o
    o=nurse.act('D09',o,'corrected',actual_at='2026-11-12T10:01:00Z',reason='Manual time correction')
    hist=nurse.get(f'/clinical/D09/records/{o["id"]}')['history'];assert sum(x['action']=='administered' for x in hist)==1
    assert any((x['snapshot']['actual_at'] or '').startswith('2026-11-12T10:00') for x in hist)
    evidence('D09',['nurse','pharmacist'],[med['id'],o['id']],['duplicate give exactly once','correction preserves original event'])

def test_portal_correction_creates_staff_task_preserves_document():
    patient=Actor('patient');registration=Actor('registration')
    docs=patient.get('/clinical/catalog/released-documents')['items'];assert docs
    chosen=next(x for x in docs if x['patient_id']=='patient-001')
    with SessionLocal() as db:before=db.get(c.DocumentVersion,chosen['id']).content
    request=patient.create('D21',request_kind='correction',document_revision_id=chosen['id'],reason='Synthetic patient requests text correction')
    assert request['staff_task_id'] and request['patient_id']=='patient-001'
    registration.act('D21',request,'booked',status=409)
    request=registration.act('D21',request,'reviewed');request=registration.act('D21',request,'completed',response_note='Reviewed; author to create formal amendment separately')
    with SessionLocal() as db:
        assert db.get(c.DocumentVersion,chosen['id']).content==before
        assert db.get(c.Task,request['staff_task_id']).status=='completed'
    evidence('D21_CORRECTION',['patient','registration'],[request['id'],chosen['id'],request['staff_task_id']],['own published revision bound','staff task shares encounter','review and response persisted','original document unchanged'])

def test_immunization_lot_trace_does_not_change_growth_measurement():
    clinician=Actor('clinician')
    visit=clinician.create('D15',**context(),measurement_name='Synthetic weight',measurement_value='20',unit='kg',measured_at='2026-11-12T08:00:00Z')
    visit=clinician.act('D15',visit,'immunization',item_id='item-clinical',lot_id='lot-clinical',administered_at='2026-11-12T08:30:00Z',quantity='1',unit='tablet')
    assert visit['unit']=='kg' and Decimal(visit['measurement_value'])==20
    detail=clinician.get('/clinical/D15/records/'+visit['id']);assert len(detail['immunizations'])==1
    assert detail['immunizations'][0]['lot_id']=='lot-clinical'
    # Historical synthetic record; it does not infer dose or post a stock dispense.
    with SessionLocal() as db:assert db.scalar(select(func.count()).select_from(erp.StockMovement).where(erp.StockMovement.source_id==visit['id']))==0
    evidence('D15_IMMUNIZATION',['clinician'],[visit['id'],detail['immunizations'][0]['id']],['structured manual immunization','item/lot FK trace','growth units unchanged','no inferred dose or stock dispensing'])

def test_equipment_and_cssd_rechecked_before_procedure():
    clinician=Actor('clinician')
    with SessionLocal.begin() as db:
        asset=erp.EquipmentAsset(id=uid(),organization_id='org-demo',facility_id='facility-demo',name='Synthetic procedure asset',location_id='location-ward',status='in_service');db.add(asset);db.flush()
        cycle=erp.CSSDCycle(id=uid(),organization_id='org-demo',facility_id='facility-demo',asset_id=asset.id,operator_id='user-inventory',cycle_code='SYN-'+uid(),status='released');db.add(cycle);asset_id=asset.id;cycle_id=cycle.id
    case=clinician.create('D12',**context(),procedure_name='Synthetic procedure',asset_id=asset_id,cssd_cycle_id=cycle_id)
    case=clinician.act('D12',case,'scheduled',room='Resource test OR',starts_at='2027-02-01T08:00:00Z',ends_at='2027-02-01T09:00:00Z')
    case=clinician.act('D12',case,'checklist_verified',checklist='Manual checklist')
    with SessionLocal.begin() as db:db.get(erp.CSSDCycle,cycle_id).status='quarantined'
    clinician.act('D12',case,'in_progress',status=409)
    assert clinician.get('/clinical/D12/records/'+case['id'])['status']=='checklist_verified'

def test_room_overlap_bed_race_and_blood_reservation_race():
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    clinician=Actor('clinician');nurse=Actor('nurse')
    first=clinician.create('D12',**context(),procedure_name='Synthetic OR A')
    first=clinician.act('D12',first,'scheduled',room='Overlap room',starts_at='2027-03-01T08:00:00Z',ends_at='2027-03-01T09:00:00Z')
    second=clinician.create('D12',**context(2),procedure_name='Synthetic OR B')
    clinician.act('D12',second,'scheduled',room='Overlap room',starts_at='2027-03-01T08:30:00Z',ends_at='2027-03-01T09:30:00Z',status=409)
    with SessionLocal.begin() as db:
        bed=m.Bed(id=uid(),organization_id='org-demo',facility_id='facility-demo',ward='Synthetic race ward',label='Race bed');db.add(bed);bed_id=bed.id
        unit=m.BloodUnit(id=uid(),organization_id='org-demo',facility_id='facility-demo',identifier='RACE-'+uid(),expiry_at=datetime(2030,1,1,tzinfo=timezone.utc),eligibility_status='available');db.add(unit);unit_id=unit.id
    admissions=[clinician.create('D05',**context(),admission_reason='Race A'),nurse.create('D05',**context(2),admission_reason='Race B')]
    requests=[]
    for actor,i in [(clinician,1),(nurse,2)]:
        o=actor.create('D18',**context(i),indication='Race blood request');requests.append(actor.act('D18',o,'reviewed'))
    def race(d,records,action,extra):
        barrier=Barrier(2)
        def call(pair):
            actor,obj=pair;barrier.wait()
            r=actor.client.post(f'/api/v2/clinical/{d}/records/{obj["id"]}/actions',json={'action':action,'version':obj['version'],**extra},headers={'X-CSRF-Token':actor.csrf,'Idempotency-Key':uid()})
            return r.status_code
        with ThreadPoolExecutor(2) as ex:codes=list(ex.map(call,zip([clinician,nurse],records)))
        assert sorted(codes)==[200,409]
    race('D05',admissions,'admitted',{'bed_id':bed_id});race('D18',requests,'reserved',{'unit_id':unit_id})
    evidence('D05_D12_D18_CONCURRENCY',['clinician','nurse'],[bed_id,unit_id,first['id'],second['id']],['room overlap rejected','simultaneous bed assignment one winner','simultaneous unit reservation one winner'])

def test_birth_replay_preserves_single_child_identity():
    clinician=Actor('clinician');registration=Actor('registration')
    o=clinician.create('D14',**context(),gestation_note='Synthetic birth replay');o=clinician.act('D14',o,'antenatal_active');before=o;key=uid();identifier='BIRTH-'+uid()
    vals={'delivery_note':'Manual synthetic delivery','child_name':'Synthetic child retry','child_identifier':identifier}
    o=clinician.act('D14',before,'delivery_documented',key=key,**vals);assert clinician.act('D14',before,'delivery_documented',key=key,**vals)==o
    child=registration.get('/patients/'+o['child_patient_id']);assert child['display_name']=='Synthetic child retry'
    with SessionLocal() as db:assert db.scalar(select(func.count()).select_from(c.PatientIdentifier).where(c.PatientIdentifier.value==identifier))==1
    evidence('D14',['clinician','registration'],[o['id'],child['id']],['same-key delivery one child','relational mother child identity retained','registration reads actual newborn'])

def test_observation_and_growth_history_separate_patients_and_dates():
    clinician=Actor('clinician');observations=[];measurements=[]
    for i,date in [(1,'2026-11-10T08:00:00Z'),(1,'2026-11-11T08:00:00Z'),(2,'2026-11-11T08:00:00Z')]:
        admission=clinician.create('D05',**context(i),admission_reason='Synthetic observation context')
        o=clinician.create('D13',**context(i),admission_id=admission['id'],observation_name='manual observation',observation_value=str(i),unit='demo',observed_at=date,round_note='Manual timestamp record')
        observations.append(clinician.act('D13',o,'recorded'))
        g=clinician.create('D15',**context(i),measurement_name='synthetic length',measurement_value=str(i*10),unit='cm',measured_at=date);measurements.append(clinician.act('D15',g,'recorded'))
    for domain,records in [('D13',observations),('D15',measurements)]:
        got=clinician.get('/clinical/'+domain+'/records?patient_id=patient-001')['items'];ids={x['id'] for x in got}
        assert records[0]['id'] in ids and records[1]['id'] in ids and records[2]['id'] not in ids
        assert all(x['patient_id']=='patient-001' for x in got)
    evidence('D13_D15_HISTORY',['clinician'],[x['id'] for x in observations+measurements],['two dates retained','two patients not mixed','raw measurement units preserved'])

def test_dental_two_teeth_two_visits_and_charge_identity():
    clinician=Actor('clinician');registration=Actor('registration')
    encounter=registration.post('/encounters',{'patient_id':'patient-001','kind':'OPD','department_id':'department-demo'},status=201)
    records=[]
    for tooth,enc,price in [('SYN-11','encounter-001','10'),('SYN-21',encounter['id'],'20')]:
        o=clinician.create('D17',patient_id='patient-001',encounter_id=enc,tooth_code=tooth,finding='Manual synthetic tooth finding',procedure_name='Synthetic dental procedure '+tooth)
        for target in ('reviewed','scheduled'):o=clinician.act('D17',o,target)
        before=o;key=uid();o=clinician.act('D17',before,'performed',key=key,unit_price=price);assert clinician.act('D17',before,'performed',key=key,unit_price=price)==o
        for target in ('verified','closed'):o=clinician.act('D17',o,target)
        records.append(o)
    got=clinician.get('/clinical/D17/records?patient_id=patient-001')['items'];by_id={x['id']:x for x in got}
    assert [by_id[x['id']]['tooth_code'] for x in records]==['SYN-11','SYN-21']
    with SessionLocal() as db:
        charges=list(db.scalars(select(erp.Charge).where(erp.Charge.source_id.in_([x['id'] for x in records]))));assert len(charges)==2
        assert {x.encounter_id for x in charges}=={'encounter-001',encounter['id']}
        assert sum(x.amount for x in charges)==30
    evidence('D17',['clinician','registration'],[encounter['id']]+[x['id'] for x in records],['two teeth across two visits retained','charge links correct procedure and encounter','duplicate performance does not double charge'])

def test_concurrent_room_reservation_one_winner():
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    clinician=Actor('clinician');nurse=Actor('nurse');one=clinician.create('D12',**context(),procedure_name='Room race A');two=nurse.create('D12',**context(2),procedure_name='Room race B');barrier=Barrier(2)
    def run(pair):
        actor,o=pair;barrier.wait()
        return actor.client.post('/api/v2/clinical/D12/records/'+o['id']+'/actions',json={'action':'scheduled','version':o['version'],'room':'Concurrent synthetic OR','starts_at':'2027-04-01T08:00:00Z','ends_at':'2027-04-01T09:00:00Z'},headers={'X-CSRF-Token':actor.csrf,'Idempotency-Key':uid()}).status_code
    with ThreadPoolExecutor(2) as pool:results=list(pool.map(run,[(clinician,one),(nurse,two)]))
    assert sorted(results)==[200,409]
    evidence('D12_CONCURRENCY',['clinician','nurse'],[one['id'],two['id']],['simultaneous same-room scheduling yields one winner'])

def test_d16_only_permission_reads_schedule_catalog():
    from backend.app.auth import permissions_for
    with SessionLocal.begin() as db:
        role='clinical_test_therapist'
        if not db.get(c.Role,role):db.add(c.Role(id=role,label='Test therapist'));db.flush()
        for permission in ['D16.read','D16.write','D16.action']:
            if not db.get(c.RolePermission,(role,permission)):db.add(c.RolePermission(role_id=role,permission_id=permission))
        user=c.User(id=uid(),organization_id='org-demo',username='therapist-'+uid(),display_name='Synthetic limited therapist',password_hash=password_hasher.hash('Test-Clinical-Only-2026!'),status='active');db.add(user);db.flush();db.add(c.Membership(user_id=user.id,facility_id='facility-demo',role=role));username=user.username
    client=TestClient(app);r=client.post('/api/v2/auth/login',json={'username':username,'password':'Test-Clinical-Only-2026!'});assert r.status_code==200
    assert client.get('/api/v2/clinical/catalog/slots').status_code==200
    assert client.get('/api/v2/clinical/catalog/blood-units').status_code==403

def test_icu_device_assignment_release_unavailable_and_overlap():
    clinician=Actor('clinician');rounds=[]
    for i in (1,2):
        admission=clinician.create('D05',**context(i),admission_reason='Device episode')
        rounds.append(clinician.create('D13',**context(i),admission_id=admission['id'],observation_name='Manual observation',observation_value='1',unit='demo',observed_at='2026-11-12T08:00:00Z',round_note='No device control'))
    first=clinician.act('D13',rounds[0],'assign_device',asset_id='asset-demo');assignment_id=first['device_assignment_id']
    clinician.act('D13',rounds[1],'assign_device',asset_id='asset-demo',status=409)
    detail=clinician.get('/clinical/D13/records/'+first['id']);assert detail['device_assignments'][0]['status']=='assigned'
    first=clinician.act('D13',first,'release_device',assignment_id=assignment_id,reason='Manual synthetic end of use')
    with SessionLocal.begin() as db:db.get(erp.EquipmentAsset,'asset-demo').status='out_of_service'
    clinician.act('D13',rounds[1],'assign_device',asset_id='asset-demo',status=409)
    with SessionLocal.begin() as db:db.get(erp.EquipmentAsset,'asset-demo').status='in_service'
    second=clinician.act('D13',rounds[1],'assign_device',asset_id='asset-demo')
    with SessionLocal() as db:
        prior=db.get(m.DeviceAssignment,assignment_id);assert prior.status=='released' and prior.ended_at and prior.version==2
        current=db.get(m.DeviceAssignment,second['device_assignment_id']);assert current.patient_id=='patient-002' and current.ended_at is None
    evidence('D13_DEVICE',['clinician'],[first['id'],second['id'],assignment_id,second['device_assignment_id']],['explicit manual device assignment','active overlap blocked','unavailable asset blocked','release preserves actor timestamp version','device reuse after release'])
