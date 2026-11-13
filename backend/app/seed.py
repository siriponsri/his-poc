"""Explicit deterministic synthetic seed. Existing rows are never overwritten."""
import os
from datetime import date
from sqlalchemy import select
from .db import SessionLocal
from . import model_registry
from .models import *
from .auth import password_hasher,ROLE_DOMAINS,ALIASES,permissions_for
from .common import text_hash

def seed(db,password):
    if db.get(SeedRun,'synthetic-v3.0'):return
    if len(password)<12:raise ValueError('HIS_SEED_PASSWORD must contain at least 12 characters')
    def add(cls,id,**values):
        old=db.get(cls,id)
        if not old:old=cls(id=id,**values);db.add(old);db.flush()
        return old
    add(Organization,'org-demo',name='โรงพยาบาลสังเคราะห์ HIS POC')
    add(Organization,'org-other',name='องค์กรแยกสำหรับ negative tests')
    add(Facility,'facility-demo',organization_id='org-demo',name='หน่วยบริการสังเคราะห์')
    add(Facility,'facility-other',organization_id='org-other',name='หน่วยบริการอีกองค์กร')
    add(Facility,'facility-second',organization_id='org-demo',name='สาขาสอง จำกัดขอบเขต')
    add(Department,'department-demo',organization_id='org-demo',facility_id='facility-demo',name='แผนกทั่วไปสังเคราะห์')
    add(Location,'location-ward',organization_id='org-demo',facility_id='facility-demo',name='หอผู้ป่วยสังเคราะห์',kind='ward')
    add(Location,'location-store',organization_id='org-demo',facility_id='facility-demo',name='คลังสังเคราะห์',kind='store')
    for role in set(ROLE_DOMAINS)|set(ALIASES)|{'refund_approver','accountant','purchase_approver'}:
        add(Role,role,label=role)
        for permission in permissions_for({role}):
            if not db.get(Permission,permission):db.add(Permission(id=permission));db.flush()
            if not db.get(RolePermission,(role,permission)):db.add(RolePermission(role_id=role,permission_id=permission))
    db.flush()
    for role in ROLE_DOMAINS:
        u=add(User,'user-'+role,organization_id='org-demo',username=role,display_name='DEMO '+role,password_hash=password_hasher.hash(password))
        add(Membership,'membership-'+role,user_id=u.id,facility_id='facility-demo',role=role)
    extras={'finance_reviewer':['finance','refund_approver','accountant'],'procurement_approver':['inventory','purchase_approver'],'support_reviewer':['quality','cssd_release_reviewer'],'patient2':['patient']}
    for name,roles in extras.items():
        u=add(User,'user-'+name,organization_id='org-demo',username=name,display_name='DEMO '+name,password_hash=password_hasher.hash(password))
        for r in roles:add(Membership,'membership-'+name+'-'+r,user_id=u.id,facility_id='facility-demo',role=r)
    add(User,'user-other',organization_id='org-other',username='other_registration',display_name='OTHER SCOPE',password_hash=password_hasher.hash(password))
    add(Membership,'membership-other',user_id='user-other',facility_id='facility-other',role='registration')
    for n in range(1,5):
        pid=f'patient-{n:03}';eid=f'encounter-{n:03}'
        add(Patient,pid,organization_id='org-demo',facility_id='facility-demo',display_name=f'ผู้ป่วยสังเคราะห์ {n:03}',birth_date=date(1980+n,1,1),sex='unknown',status='active')
        add(PatientIdentifier,'identifier-'+pid,patient_id=pid,organization_id='org-demo',issuer='SYNTHETIC',value=f'SYN-{n:03}')
        add(Encounter,eid,organization_id='org-demo',facility_id='facility-demo',patient_id=pid,department_id='department-demo',status='in_consult',published=n<=2)
        add(Task,'task-'+pid,organization_id='org-demo',facility_id='facility-demo',patient_id=pid,encounter_id=eid,domain='D37',kind='document_review',title=f'ตรวจเอกสารสังเคราะห์ {n:03}')
        did='document-'+pid;vid='revision-'+pid
        add(Document,did,organization_id='org-demo',facility_id='facility-demo',patient_id=pid,encounter_id=eid,title='บันทึกสังเคราะห์',version=1,current_version_id=vid,published=n<=2)
        content=f'DEMO ข้อมูลแต่งขึ้นเพื่อทดสอบผู้ป่วย {n:03} ไม่มีคำแนะนำทางคลินิก'
        add(DocumentVersion,vid,document_id=did,version=1,content=content,content_hash=text_hash(content),created_by='user-clinician')
    for user_id in ['user-clinician','user-nurse']:
        for n in range(1,5):
            pid=f'patient-{n:03}'
            if not db.get(CareAssignment,(user_id,pid)):db.add(CareAssignment(user_id=user_id,patient_id=pid))
    for username,pid in [('patient','patient-001'),('patient2','patient-002')]:
        if not db.get(UserPatientScope,('user-'+username,pid)):db.add(UserPatientScope(user_id='user-'+username,patient_id=pid))
    add(Patient,'patient-other',organization_id='org-other',facility_id='facility-other',display_name='ต่างองค์กร',status='active')
    add(Encounter,'encounter-other',organization_id='org-other',facility_id='facility-other',patient_id='patient-other',status='in_consult')
    add(Patient,'patient-second',organization_id='org-demo',facility_id='facility-second',display_name='ต่างสาขา',status='active')
    add(Encounter,'encounter-second',organization_id='org-demo',facility_id='facility-second',patient_id='patient-second',status='in_consult')
    from .domains.clinical import seed_clinical
    seed_clinical(db)
    from .domains.erp import seed_erp
    seed_erp(db)
    db.add(SeedRun(version='synthetic-v3.0'))
    db.flush()
if __name__=='__main__':
    password=os.environ.get('HIS_SEED_PASSWORD','')
    with SessionLocal.begin() as db:seed(db,password)
    print('Synthetic seed completed; existing records unchanged. Password not printed.')
