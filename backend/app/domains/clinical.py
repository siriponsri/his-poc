"""Manual/synthetic clinical workflows. No diagnosis, dosing or compatibility inference."""
from __future__ import annotations
import base64, hashlib, json, os
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal
from fastapi import APIRouter, Depends, HTTPException, Header, Response
from pydantic import BaseModel, ConfigDict, Field, ValidationError, create_model
from sqlalchemy import select, func, and_, text
from sqlalchemy.orm import Session
from ..db import get_db
from ..auth import current_actor, require, require_domain, scoped_patient, scoped_encounter, revalidate_actor
from ..common import audit, serialize, check_version, begin_operation, finish_operation, uid, utcnow
from .. import models_clinical as m
from ..models import Encounter, Patient, PatientIdentifier, User, ClinicalOrder, DocumentVersion, Document

router=APIRouter(prefix='/clinical',tags=['clinical'])

def field(name,label,type='text',required=True,source=None):
    v={'name':name,'label':label,'type':type,'required':required}
    if source:v['source']=source
    return v
P=field('patient_id','ผู้ป่วย',source='patients'); E=field('encounter_id','Encounter',source='encounters')
def action(name,label,from_,fields=()):return {'name':name,'label':label,'from':from_.split('|'),'fields':list(fields)}
F=field; A=action
SPECS={
'D02':{'model':m.Appointment,'name_th':'นัดหมายและคิว','initial':'requested','fields':[P,F('slot_id','ช่วงบริการ',source='slots'),F('reason','เหตุผลการนัด','textarea')], 'actions':[A('booked','ยืนยันจอง','requested'),A('reschedule','เลื่อนนัด','booked',[F('slot_id','ช่วงบริการใหม่',source='slots')]),A('checked_in','เช็กอินและเปิด Encounter','booked'),A('called','เรียกคิว','checked_in'),A('completed','เสร็จบริการ','called'),A('cancelled','ยกเลิก','requested|booked')]},
'D04':{'model':m.EmergencyEpisode,'name_th':'ห้องฉุกเฉิน','initial':'arrived','fields':[P,E,F('presenting_complaint','อาการที่แจ้ง','textarea')],'actions':[A('assessed','บันทึกการประเมินโดยคน','arrived',[F('triage_level','ระดับที่ผู้ประเมินเลือก'),F('assessment','ผลประเมิน','textarea')]),A('in_care','รับดูแล','assessed'),A('discharged','จำหน่าย','in_care',[F('disposition_reason','เหตุผล','textarea')]),A('admission_requested','ขอรับผู้ป่วยใน','in_care',[F('disposition_reason','เหตุผล','textarea')]),A('referral_requested','ขอส่งต่อ','in_care',[F('disposition_reason','เหตุผล','textarea')])]},
'D05':{'model':m.Admission,'name_th':'ผู้ป่วยในและเตียง','initial':'requested','fields':[P,E,F('admission_reason','เหตุผลการรับไว้','textarea')],'actions':[A('admitted','จัดเตียง/ยืนยันย้าย','requested|transfer_requested',[F('bed_id','เตียง',source='beds')]),A('transfer_requested','ขอย้ายเตียง','admitted'),A('discharge_ready','พร้อมจำหน่าย','admitted',[F('discharge_summary','สรุปจำหน่าย','textarea')]),A('discharged','จำหน่ายและคืนเตียง','discharge_ready')]},
'D06':{'model':m.Handover,'name_th':'พยาบาลและส่งเวร','initial':'draft','fields':[P,E,F('summary','สรุปส่งเวร','textarea'),F('pending_tasks','งานที่ต้องติดตาม','textarea'),F('task_ids','Task IDs คั่นด้วยจุลภาค'),F('receiving_staff_id','ผู้รับเวร',source='staff')],'actions':[A('signed','ลงนามส่งเวร','draft'),A('acknowledged','รับทราบเวร','signed'),A('amended','เพิ่มฉบับแก้ไข','acknowledged',[F('summary','สรุปฉบับแก้','textarea'),F('reason','เหตุผล','textarea')])]},
'D08':{'model':m.MedicationOrder,'name_th':'เภสัชกรรม','initial':'received','fields':[P,E,F('order_id','คำสั่งยา',source='orders'),F('item_id','รหัสรายการยา',source='items'),F('medication_name','ชื่อยาสังเคราะห์'),F('prescribed_dose','ขนาดยาที่ผู้สั่งระบุ'),F('route','วิธีให้ยา'),F('quantity','จำนวน','number'),F('unit','หน่วย')],'actions':[A('reviewed','เภสัชกรตรวจคำสั่ง','received'),A('prepared','จัดยา','reviewed'),A('dispensed','ยืนยันจ่าย','prepared',[F('lot_id','Lot',source='lots'),F('location_id','คลัง',source='stock-locations'),F('quantity','จำนวนที่จ่าย','number'),F('unit_price','ราคาต่อหน่วย','number')]),A('rejected','ปฏิเสธคำสั่ง','received',[F('reason','เหตุผล','textarea')]),A('return_recorded','บันทึกคืนเพื่อกักกัน','dispensed|return_recorded',[F('quantity','จำนวนคืน','number'),F('reason','เหตุผล','textarea')])]},
'D09':{'model':m.Administration,'name_th':'การให้ยา','initial':'scheduled','fields':[P,E,F('medication_id','รายการยาที่ตรวจแล้ว',source='medications'),F('scheduled_at','เวลาที่กำหนด','datetime-local'),F('dose','ขนาดยาตามคำสั่ง'),F('route','วิธีให้')],'actions':[A('verified','ยืนยันผู้ป่วยและคำสั่ง','scheduled'),A('administered','บันทึกให้ยา','verified',[F('actual_at','เวลาที่ให้','datetime-local')]),A('held','งดยาชั่วคราว','verified',[F('reason','เหตุผล','textarea')]),A('not_given','ไม่ได้ให้ยา','verified',[F('reason','เหตุผล','textarea')]),A('corrected','แก้เหตุการณ์เป็นฉบับใหม่','administered',[F('reason','เหตุผล','textarea'),F('actual_at','เวลาที่ถูกต้อง','datetime-local')])]},
'D10':{'model':m.LabRequest,'name_th':'ห้องปฏิบัติการ','initial':'ordered','fields':[P,E,F('order_id','คำสั่งตรวจ',source='orders'),F('analyte','รายการตรวจ'),F('specimen_type','สิ่งส่งตรวจ')],'actions':[A('collected','เก็บสิ่งส่งตรวจ','ordered'),A('received','รับสิ่งส่งตรวจ','collected'),A('preliminary','ลงผลสังเคราะห์','received',[F('result_value','ผล'),F('unit','หน่วย'),F('reference_range','ช่วงอ้างอิงที่คนระบุ')]),A('verified','ตรวจรับรองโดยคน','preliminary'),A('released','เผยแพร่ผล','verified'),A('publish_portal','อนุญาตเผยแพร่แก่เจ้าของข้อมูล','released|corrected'),A('acknowledge','แพทย์รับทราบผล','released|corrected'),A('corrected','แก้ผลโดยเก็บฉบับเดิม','released|corrected',[F('result_value','ผลฉบับแก้'),F('unit','หน่วย'),F('reference_range','ช่วงอ้างอิง'),F('reason','เหตุผล','textarea')])]},
'D11':{'model':m.ImagingStudy,'name_th':'รังสีและภาพ','initial':'ordered','fields':[P,E,F('order_id','คำสั่งภาพ',source='orders'),F('modality','Modality'),F('body_site','ตำแหน่ง'),F('asset_id','อุปกรณ์ที่ใช้','text',False,source='assets')],'actions':[A('scheduled','จัดนัด','ordered'),A('acquired','รับไฟล์ภาพหรือข้อความ','scheduled',[F('file_base64','ไฟล์ PNG/JPEG/TXT แบบ Base64','textarea'),F('file_mime','ชนิดไฟล์ image/png, image/jpeg หรือ text/plain')]),A('report_draft','ร่างรายงานโดยคน','acquired',[F('report','รายงาน','textarea')]),A('verified','ตรวจรายงาน','report_draft'),A('released','เผยแพร่รายงาน','verified'),A('publish_portal','อนุญาตเผยแพร่แก่ผู้ป่วย','released|amended'),A('amended','เพิ่มรายงานแก้ไข','released|amended',[F('report','รายงานฉบับแก้','textarea'),F('reason','เหตุผล','textarea')])]},
'D12':{'model':m.ProcedureCase,'name_th':'ผ่าตัดและวิสัญญี','initial':'requested','fields':[P,E,F('procedure_name','หัตถการที่บุคลากรเลือก'),F('asset_id','อุปกรณ์','text',False,source='assets'),F('cssd_cycle_id','Cycle เครื่องมือที่ปล่อยแล้ว','text',False)],'actions':[A('scheduled','จองห้อง','requested',[F('room','ห้อง'),F('starts_at','เริ่ม','datetime-local'),F('ends_at','สิ้นสุด','datetime-local')]),A('checklist_verified','ตรวจ Checklist','scheduled',[F('checklist','หลักฐาน Checklist','textarea')]),A('in_progress','เริ่มหัตถการ','checklist_verified'),A('documented','บันทึกหัตถการและวิสัญญี','in_progress',[F('anesthesia_record','บันทึกโดยผู้ปฏิบัติ','textarea')]),A('closed','ปิด Case','documented'),A('cancelled','ยกเลิก','scheduled')]},
'D13':{'model':m.ICURound,'name_th':'ICU และ Observation','initial':'draft','fields':[P,E,F('admission_id','Admission',source='admissions'),F('observation_name','รายการ'),F('observation_value','ค่าที่วัด'),F('unit','หน่วย'),F('observed_at','เวลาที่วัด','datetime-local'),F('round_note','Round note','textarea'),F('asset_id','อุปกรณ์ที่ผูก Episode','text',False,source='assets')],'actions':[A('assign_device','บันทึกผูกอุปกรณ์กับ Episode','draft|recorded|reviewed',[F('asset_id','อุปกรณ์ที่ใช้งานได้',source='assets')]),A('release_device','คืนอุปกรณ์','draft|recorded|reviewed|signed|amended',[F('assignment_id','Device assignment',source='device-assignments'),F('reason','เหตุผลคืน','textarea')]),A('recorded','บันทึกค่า','draft'),A('reviewed','ทบทวน','recorded'),A('signed','ลงนาม','reviewed'),A('amended','เพิ่มฉบับแก้','signed|amended',[F('observation_value','ค่าที่แก้'),F('round_note','บันทึกฉบับแก้','textarea'),F('reason','เหตุผล','textarea')])]},
'D14':{'model':m.PregnancyEpisode,'name_th':'มารดาและทารก','initial':'registered','fields':[P,E,F('gestation_note','ข้อมูลครรภ์ที่คนบันทึก','textarea')],'actions':[A('antenatal_active','เริ่มติดตามครรภ์','registered'),A('delivery_documented','บันทึกคลอดและสร้างตัวตนทารก','antenatal_active',[F('delivery_note','บันทึกคลอด','textarea'),F('child_name','ชื่อสังเคราะห์ทารก'),F('child_identifier','เลขทะเบียนทารกสังเคราะห์')]),A('verified','ตรวจความสัมพันธ์แม่ลูก','delivery_documented'),A('closed','ปิด Episode','verified')]},
'D15':{'model':m.PediatricVisit,'name_th':'กุมารเวชกรรมและการเติบโต','initial':'draft','fields':[P,E,F('measurement_name','รายการวัด'),F('measurement_value','ค่าที่วัด','number'),F('unit','หน่วย'),F('measured_at','เวลาที่วัด','datetime-local'),F('immunization_note','วัคซีนที่บันทึกด้วยคน','textarea',False)],'actions':[A('recorded','บันทึกค่า','draft'),A('reviewed','ทบทวน','recorded'),A('closed','ปิด Visit','reviewed'),A('immunization','บันทึกวัคซีนด้วยคน','draft|recorded|reviewed',[F('item_id','วัคซีนสังเคราะห์',source='items'),F('lot_id','Lot',source='lots'),F('administered_at','เวลาที่ให้ตามบันทึก','datetime-local'),F('quantity','จำนวนตามบันทึก ไม่คำนวณขนาดยา','number'),F('unit','หน่วย')]),A('amended','เพิ่มฉบับแก้','closed|amended',[F('measurement_value','ค่าฉบับแก้','number'),F('reason','เหตุผล','textarea')])]},
'D16':{'model':m.RehabPlan,'name_th':'เวชศาสตร์ฟื้นฟู','initial':'requested','fields':[P,E,F('order_id','คำสั่งส่งฟื้นฟู',source='orders'),F('goals','เป้าหมายที่ผู้รักษากำหนด','textarea'),F('therapist_id','ผู้รับผิดชอบ',source='staff')],'actions':[A('assessed','ประเมินโดยคน','requested',[F('assessment','ผลประเมิน','textarea')]),A('active','เริ่มแผน','assessed|reviewed'),A('schedule','นัด Session','active',[F('slot_id','ช่วงบริการ',source='slots')]),A('session','บันทึก Session ที่นัดไว้','active',[F('session_id','Session ที่นัดไว้',source='therapy-sessions'),F('performed_at','วันเวลาที่ทำ','datetime-local'),F('progress','ความก้าวหน้า','textarea')]),A('reviewed','ทบทวนแผน','active'),A('completed','สิ้นสุดแผน','reviewed'),A('discontinued','ยุติ','active',[F('reason','เหตุผล','textarea')])]},
'D17':{'model':m.DentalProcedure,'name_th':'ทันตกรรมและเฉพาะทาง','initial':'draft','fields':[P,E,F('tooth_code','ตำแหน่งฟัน'),F('finding','ผลตรวจโดยคน','textarea'),F('procedure_name','หัตถการ')],'actions':[A('reviewed','ตรวจแผน','draft'),A('scheduled','จัดนัด','reviewed'),A('performed','บันทึกทำหัตถการและค่าบริการ','scheduled',[F('unit_price','ค่าบริการ','number')]),A('verified','ตรวจบันทึก','performed'),A('closed','ปิด Visit','verified'),A('cancelled','ยกเลิก','scheduled')]},
'D18':{'model':m.BloodRequest,'name_th':'ธนาคารเลือด','initial':'requested','fields':[P,E,F('indication','เหตุผลคำขอ','textarea')],'actions':[A('reviewed','ตรวจคำขอ','requested'),A('reserved','จอง Unit','reviewed',[F('unit_id','Unit สังเคราะห์',source='blood-units')]),A('compatibility_verified','บันทึกการตรวจ Compatibility โดยคน','reserved',[F('verification_evidence','หลักฐานผู้ตรวจ ไม่ใช่ AI','textarea')]),A('released','ปล่อย Unit หลังตรวจซ้ำ','compatibility_verified'),A('administration_recorded','บันทึกให้เลือด','released',[F('administration_note','บันทึกโดยผู้ปฏิบัติ','textarea')]),A('cancelled','ยกเลิกจอง','reserved')]},
'D19':{'model':m.DietOrder,'name_th':'โภชนาการและอาหาร','initial':'ordered','fields':[P,E,F('diet_description','คำสั่งอาหารโดยคน','textarea'),F('allergy_note','ข้อมูลแพ้ที่บันทึก','textarea'),F('meal_period','รอบอาหาร เช่น 2026-11-12-lunch')],'actions':[A('revise','แก้คำสั่งก่อนเตรียม','ordered|reviewed',[F('diet_description','คำสั่งอาหารฉบับใหม่','textarea'),F('allergy_note','ข้อมูลแพ้','textarea')]),A('reviewed','ตรวจคำสั่ง','ordered'),A('prepared','จัดเตรียม','reviewed'),A('delivered','ยืนยันส่ง','prepared'),A('cancelled','ยกเลิก','ordered|reviewed')]},
'D20':{'model':m.Referral,'name_th':'ส่งต่อและติดตาม','initial':'draft','fields':[P,E,F('destination','หน่วยงานปลายทาง'),F('reason','เหตุผลส่งต่อ','textarea'),F('document_revision_id','Document revision ID')],'actions':[A('reviewed','ตรวจเอกสาร','draft'),A('exported','สร้าง Referral packet','reviewed'),A('response_recorded','บันทึกตอบกลับด้วยคน','exported',[F('response_source','แหล่งข้อมูลตอบกลับ'),F('response_note','รายละเอียดตอบกลับ','textarea')]),A('closed','ปิดติดตาม','response_recorded'),A('cancelled','ยกเลิก','draft')]},
'D21':{'model':m.PortalRequest,'name_th':'พอร์ทัลผู้ป่วย','initial':'requested','fields':[{'name':'request_kind','label':'ประเภทคำขอ','type':'select','required':True,'options':[{'value':'appointment','label':'ขอนัดหมาย'},{'value':'correction','label':'ขอแก้ไขข้อมูลเอกสาร'}]},F('slot_id','ช่วงบริการ สำหรับขอนัด','text',False,source='slots'),F('document_revision_id','เอกสารที่ขอแก้','text',False,source='released-documents'),F('reason','เหตุผลคำขอ','textarea')],'actions':[A('reviewed','เจ้าหน้าที่ทบทวน','requested'),A('booked','เจ้าหน้าที่จองนัด','reviewed'),A('completed','ปิดคำขอพร้อมผลพิจารณา','booked|reviewed',[F('response_note','ผลพิจารณา/การดำเนินการ','textarea')]),A('cancelled','ยกเลิกคำขอของตน','requested'),A('declined','ปฏิเสธพร้อมเหตุผล','reviewed',[F('reason','เหตุผล','textarea')])]}
}

class StrictDTO(BaseModel):model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
def input_model(fields,extra=None):
    defs={}
    for f in fields:
        typ=Decimal if f['type']=='number' else datetime if f['type']=='datetime-local' else Literal[tuple(x['value'] for x in f['options'])] if f['type']=='select' and f.get('options') else str
        default=... if f['required'] else None
        if typ is str:
            name=f['name']; limits={'triage_level':40,'medication_name':200,'prescribed_dose':150,'dose':150,'route':80,'unit':40,'analyte':150,'specimen_type':80,'result_value':200,'reference_range':150,'modality':40,'body_site':120,'procedure_name':200,'room':80,'observation_name':100,'observation_value':120,'measurement_name':80,'tooth_code':12,'meal_period':100,'destination':200,'response_source':200,'child_identifier':100,'file_mime':80,'file_base64':1400000}
            limit=64 if name.endswith('_id') else limits.get(name,10000)
            defs[name]=(typ if f['required'] else typ|None,Field(default,min_length=1,max_length=limit))
        elif typ is Decimal:defs[f['name']]=(typ if f['required'] else typ|None,Field(default,max_digits=18,decimal_places=2 if f['name']=='unit_price' else 3))
        else:defs[f['name']]=(typ if f['required'] else typ|None,default)
    defs.update(extra or {})
    return create_model('ClinicalInput',__base__=StrictDTO,**defs)
def validate_fields(fields,data,extra=None):
    try:return input_model(fields,extra).model_validate(data).model_dump(exclude_none=True)
    except ValidationError as e: raise HTTPException(422,detail=json.loads(e.json()))
def domain_schemas():
    return {d:{'create':input_model(s['fields']).model_json_schema(),'actions':{a['name']:input_model(a['fields'],{'action':(Literal[a['name']],...),'version':(int,Field(...,ge=1,strict=True))}).model_json_schema() for a in s['actions']}} for d,s in SPECS.items()}
def spec(domain):
    if domain not in SPECS:raise HTTPException(404,'Unknown clinical domain')
    return SPECS[domain]
def scoped_query(db,actor,model):
    q=select(model).where(model.organization_id==actor.organization_id,model.facility_id==actor.facility_id)
    if actor.patient_scope:q=q.where(model.patient_id==actor.patient_scope)
    if actor.care_patient_ids is not None:q=q.where(model.patient_id.in_(actor.care_patient_ids))
    return q

def record(db,actor,domain,id,lock=False):
    require_domain(actor,domain)
    q=scoped_query(db,actor,spec(domain)['model']).where(spec(domain)['model'].id==id)
    if lock:q=q.with_for_update()
    obj=db.scalar(q)
    if not obj:raise HTTPException(404,'Record not found in active scope')
    scoped_patient(db,actor,obj.patient_id)
    if obj.encounter_id:scoped_encounter(db,actor,obj.encounter_id)
    return obj

def emit(db,actor,domain,obj,act,reason=None):
    db.flush(); out=serialize(obj)
    # Never expose filesystem path; clients use authorized file endpoint.
    if 'file_path' in out:out.pop('file_path')
    out.pop('packet',None)
    db.add(m.ClinicalEvent(organization_id=actor.organization_id,domain=domain,record_id=obj.id,version=obj.version,action=act,actor_id=actor.user_id,snapshot=out,reason=reason))
    audit(db,actor,domain,obj.id,act,{'version':obj.version})
    return out

def valid_datetime(v):
    if v.tzinfo is None:raise HTTPException(422,'Timestamp must include UTC offset')
    return v

def related(db,actor,model,id,patient_id=None,encounter_id=None,lock=False):
    obj=db.get(model,id,with_for_update=lock)
    if not obj or getattr(obj,'organization_id',actor.organization_id)!=actor.organization_id or getattr(obj,'facility_id',actor.facility_id)!=actor.facility_id:raise HTTPException(404,'Linked record outside active scope')
    if model is User:
        from ..models import Membership
        if obj.status!='active' or not db.scalar(select(Membership.id).where(Membership.user_id==obj.id,Membership.facility_id==actor.facility_id,Membership.active.is_(True))):raise HTTPException(404,'User is not active in this facility')
    if patient_id and getattr(obj,'patient_id',patient_id)!=patient_id:raise HTTPException(409,'Linked patient mismatch')
    if encounter_id and getattr(obj,'encounter_id',encounter_id)!=encounter_id:raise HTTPException(409,'Linked encounter mismatch')
    return obj

def reserve_slot(db,actor,slot_id,exclude=None):
    slot=related(db,actor,m.ServiceSlot,slot_id,lock=True)
    q=select(func.count()).select_from(m.Appointment).where(m.Appointment.slot_id==slot_id,m.Appointment.status.in_(['booked','checked_in','called']))
    if exclude:q=q.where(m.Appointment.id!=exclude)
    if db.scalar(q)>=slot.capacity:raise HTTPException(409,'Service slot full')
    return slot

@router.get('/catalog')
def catalog(actor=Depends(current_actor)):
    return {'items':[{'id':k,'api_path':f'/clinical/{k}/records',**{a:b for a,b in v.items() if a!='model'}} for k,v in SPECS.items() if f'{k}.read' in actor.permissions]}

@router.get('/catalog/{kind}')
def resources(kind:str,db:Session=Depends(get_db,scope="function"),actor=Depends(current_actor)):
    extra_permissions={'items':['D08','D15'],'lots':['D08','D15'],'assets':['D11','D12','D13'],'cssd-cycles':['D12'],'therapy-sessions':['D16'],'released-documents':['D21'],'device-assignments':['D13']}
    if kind in extra_permissions:
        if not any(f'{d}.read' in actor.permissions for d in extra_permissions[kind]):raise HTTPException(403,'Catalog permission denied')
        if kind=='device-assignments':
            return {'items':[serialize(x) for x in db.scalars(scoped_query(db,actor,m.DeviceAssignment).where(m.DeviceAssignment.ended_at.is_(None)))]}
        if kind=='released-documents':
            query=select(Document).where(Document.organization_id==actor.organization_id,Document.facility_id==actor.facility_id,Document.published.is_(True))
            if actor.patient_scope:query=query.where(Document.patient_id==actor.patient_scope)
            if actor.care_patient_ids is not None:query=query.where(Document.patient_id.in_(actor.care_patient_ids))
            return {'items':[{'id':d.current_version_id,'document_id':d.id,'label':d.title,'patient_id':d.patient_id} for d in db.scalars(query)]}
        if kind=='therapy-sessions':
            plans=list(db.scalars(scoped_query(db,actor,m.RehabPlan)))
            ids=[x.id for x in plans]
            return {'items':[{'id':x.id,'plan_id':x.plan_id,'patient_id':next(p.patient_id for p in plans if p.id==x.plan_id),'encounter_id':next(p.encounter_id for p in plans if p.id==x.plan_id),'label':x.scheduled_at.isoformat(),'appointment_id':x.appointment_id} for x in db.scalars(select(m.TherapySession).where(m.TherapySession.plan_id.in_(ids))) if not db.scalar(select(m.TherapyProgress.id).where(m.TherapyProgress.session_id==x.id))]}
        from ..models_erp import InventoryItem,InventoryLot,EquipmentAsset,CSSDCycle
        cls={'items':InventoryItem,'lots':InventoryLot,'assets':EquipmentAsset,'cssd-cycles':CSSDCycle}[kind]
        query=select(cls).where(cls.organization_id==actor.organization_id,cls.facility_id==actor.facility_id)
        if kind=='cssd-cycles':query=query.where(cls.status=='released')
        allowed={'items':['id','name','unit','status'],'lots':['id','item_id','lot_number','expiry_date','status'],'assets':['id','name','status','location_id'],'cssd-cycles':['id','cycle_code','asset_id','status']}
        return {'items':[{k:v for k,v in serialize(x).items() if k in allowed[kind]} for x in db.scalars(query)]}
    models={'slots':m.ServiceSlot,'beds':m.Bed,'blood-units':m.BloodUnit,'medications':m.MedicationOrder,'admissions':m.Admission,'staff':User}
    if kind not in models:raise HTTPException(404,'Unknown catalog')
    allowed={'slots':['D02','D16','D21'],'beds':['D05'],'blood-units':['D18'],'medications':['D08','D09'],'admissions':['D05','D13'],'staff':['D06','D16']}
    if not any(f'{d}.read' in actor.permissions for d in allowed[kind]):raise HTTPException(403,'Catalog permission denied')
    cls=models[kind];q=select(cls).where(cls.organization_id==actor.organization_id)
    if hasattr(cls,'facility_id'):q=q.where(cls.facility_id==actor.facility_id)
    if kind=='staff':
        from ..models import Membership
        q=q.join(Membership,Membership.user_id==User.id).where(Membership.facility_id==actor.facility_id,Membership.active.is_(True),User.status=='active').distinct()
    if actor.patient_scope and hasattr(cls,'patient_id'):q=q.where(cls.patient_id==actor.patient_scope)
    if actor.care_patient_ids is not None and hasattr(cls,'patient_id'):q=q.where(cls.patient_id.in_(actor.care_patient_ids))
    items=[]
    for o in db.scalars(q):
        if kind=='staff':items.append({'id':o.id,'label':o.display_name})
        else:items.append(serialize(o))
    return {'items':items}

@router.get('/{domain}/records')
def list_records(domain:str,q:str='',patient_id:str|None=None,encounter_id:str|None=None,db:Session=Depends(get_db,scope="function"),actor=Depends(current_actor)):
    require_domain(actor,domain);s=spec(domain); query=scoped_query(db,actor,s['model'])
    if patient_id:scoped_patient(db,actor,patient_id);query=query.where(s['model'].patient_id==patient_id)
    if encounter_id:scoped_encounter(db,actor,encounter_id);query=query.where(s['model'].encounter_id==encounter_id)
    items=[{k:v for k,v in serialize(o).items() if k not in ('file_path','packet')} for o in db.scalars(query.order_by(s['model'].created_at.desc()).limit(500))]
    if q:items=[x for x in items if q.casefold() in json.dumps(x,ensure_ascii=False).casefold()]
    return {'items':items}

@router.get('/{domain}/records/{id}')
def detail(domain:str,id:str,db:Session=Depends(get_db,scope="function"),actor=Depends(current_actor)):
    obj=record(db,actor,domain,id);out=serialize(obj);out.pop('file_path',None);out.pop('packet',None)
    out['history']=[serialize(x) for x in db.scalars(select(m.ClinicalEvent).where(m.ClinicalEvent.record_id==id,m.ClinicalEvent.organization_id==actor.organization_id).order_by(m.ClinicalEvent.created_at))]
    if domain=='D16':out['sessions']=[{**serialize(x),'recording':serialize(p) if (p:=db.scalar(select(m.TherapyProgress).where(m.TherapyProgress.session_id==x.id))) else None} for x in db.scalars(select(m.TherapySession).where(m.TherapySession.plan_id==id))]
    if domain=='D13':out['device_assignments']=[serialize(x) for x in db.scalars(select(m.DeviceAssignment).where(m.DeviceAssignment.admission_id==obj.admission_id,m.DeviceAssignment.patient_id==obj.patient_id))]
    if domain=='D15':out['immunizations']=[serialize(x) for x in db.scalars(select(m.ImmunizationRecord).where(m.ImmunizationRecord.visit_id==id))]
    if domain=='D06':out['task_links']=[serialize(x) for x in db.scalars(select(m.HandoverTask).where(m.HandoverTask.handover_id==id))]
    if domain=='D05':out['bed_history']=[serialize(x) for x in db.scalars(select(m.BedAssignment).where(m.BedAssignment.admission_id==id))]
    return out

@router.post('/{domain}/records',status_code=201)
def create(domain:str,data:dict,db:Session=Depends(get_db,scope="function"),actor=Depends(current_actor),idempotency_key:str=Header(alias='Idempotency-Key')):
    revalidate_actor(db,actor);require_domain(actor,domain,write=True);s=spec(domain)
    vals=validate_fields(s['fields'],data)
    replay=begin_operation(db,actor,idempotency_key,f'{domain}.create',data)
    if replay is not None:
        scoped_patient(db,actor,replay['patient_id'])
        if replay.get('encounter_id'):scoped_encounter(db,actor,replay['encounter_id'])
        return replay
    if domain=='D21':
        if not actor.patient_scope:raise HTTPException(403,'Portal subject linkage required')
        vals['patient_id']=actor.patient_scope
    patient=scoped_patient(db,actor,vals['patient_id'])
    if vals.get('encounter_id'):
        enc=scoped_encounter(db,actor,vals['encounter_id'])
        if enc.patient_id!=patient.id:raise HTTPException(409,'Encounter does not belong to patient')
        if enc.status in ('closed','discharged','cancelled'):raise HTTPException(409,'Encounter is closed')
    for k,v in vals.items():
        if isinstance(v,datetime):valid_datetime(v)
    if domain=='D02':related(db,actor,m.ServiceSlot,vals['slot_id'])
    if domain=='D21':
        if vals['request_kind']=='appointment':
            if not vals.get('slot_id') or vals.get('document_revision_id'):raise HTTPException(422,'Appointment requires slot and no correction document')
            related(db,actor,m.ServiceSlot,vals['slot_id'])
        else:
            if vals.get('slot_id') or not vals.get('document_revision_id'):raise HTTPException(422,'Correction requires document revision and no slot')
            rev=db.get(DocumentVersion,vals['document_revision_id'])
            if not rev:raise HTTPException(404,'Released document not found')
            doc=related(db,actor,Document,rev.document_id,patient.id)
            if not doc.published or doc.current_version_id!=rev.id:raise HTTPException(404,'Released document not found')
            vals['encounter_id']=doc.encounter_id
    if domain in ('D08','D10','D11','D16'):
        order=related(db,actor,ClinicalOrder,vals['order_id'],patient.id,vals['encounter_id'])
        if order.status not in ('signed','acknowledged','in_progress'):raise HTTPException(409,'Signed order required')
        if order.kind!={'D08':'medication','D10':'lab','D11':'imaging','D16':'rehab'}[domain]:raise HTTPException(409,'Wrong order kind')
        vals['order_version']=order.version
        if domain=='D08':
            from ..models_erp import InventoryItem
            item=related(db,actor,InventoryItem,vals['item_id'])
            if item.status!='active' or order.code!=item.id or vals['medication_name']!=order.label or order.label!=item.name or vals['quantity']>order.quantity or vals['unit']!=order.unit or item.unit!=vals['unit']:raise HTTPException(409,'Medication quantity/unit differs from signed order or item')
    if domain=='D08' and vals['quantity']<=0:raise HTTPException(422,'Quantity must be positive')
    if domain=='D09':
        medication=related(db,actor,m.MedicationOrder,vals['medication_id'],patient.id,vals['encounter_id'])
        if medication.status not in ('reviewed','prepared','dispensed'):raise HTTPException(409,'Reviewed medication required')
        if medication.prescribed_dose!=vals['dose'] or medication.route!=vals['route']:raise HTTPException(409,'Manual dose/route must match reviewed order')
    if domain=='D13':related(db,actor,m.Admission,vals['admission_id'],patient.id,vals['encounter_id'])
    if domain in ('D06','D16'):related(db,actor,User,vals['receiving_staff_id' if domain=='D06' else 'therapist_id'])
    if domain=='D15' and vals['measurement_value']<0:raise HTTPException(422,'Measurement must not be negative')
    if domain in ('D11','D12','D13'):
        if vals.get('asset_id'):
            from ..models_erp import EquipmentAsset
            asset=related(db,actor,EquipmentAsset,vals['asset_id'])
            if asset.status!='in_service':raise HTTPException(409,'Equipment is not in service')
        if vals.get('cssd_cycle_id'):
            from ..models_erp import CSSDCycle
            cycle=related(db,actor,CSSDCycle,vals['cssd_cycle_id'])
            if cycle.status!='released':raise HTTPException(409,'Instrument cycle is not human-released')
    if domain=='D20':validate_document(db,actor,vals['document_revision_id'],patient.id,vals['encounter_id'])
    task_ids=vals.pop('task_ids',None)
    obj=s['model'](**vals,organization_id=actor.organization_id,facility_id=actor.facility_id,status=s['initial'],created_by=actor.user_id)
    db.add(obj);db.flush()
    if domain=='D06':
        from ..models import Task
        ids=[x.strip() for x in task_ids.split(',') if x.strip()]
        if not ids or len(ids)!=len(set(ids)):raise HTTPException(422,'Provide distinct shared task IDs')
        for task_id in ids:
            task=related(db,actor,Task,task_id,patient.id,vals['encounter_id'])
            db.add(m.HandoverTask(handover_id=obj.id,task_id=task.id,task_version=task.version))
    if domain=='D21' and obj.request_kind=='correction':
        from ..models import Task
        task=Task(id=uid(),organization_id=actor.organization_id,facility_id=actor.facility_id,patient_id=obj.patient_id,encounter_id=obj.encounter_id,domain='D21',kind='document_correction_request',title='คำขอแก้ข้อมูลจากผู้ป่วย: '+obj.id,status='open')
        db.add(task);db.flush();obj.staff_task_id=task.id
    out=emit(db,actor,domain,obj,'created')
    finish_operation(db,actor,idempotency_key,f'{domain}.create',data,out)
    return out

def validate_document(db,actor,revision_id,patient_id,encounter_id):
    rev=db.get(DocumentVersion,revision_id)
    if not rev:raise HTTPException(404,'Document revision missing')
    doc=related(db,actor,Document,rev.document_id,patient_id,encounter_id)
    return rev

@router.post('/{domain}/records/{id}/actions')
def act(domain:str,id:str,data:dict,db:Session=Depends(get_db,scope="function"),actor=Depends(current_actor),idempotency_key:str=Header(alias='Idempotency-Key')):
    revalidate_actor(db,actor);require_domain(actor,domain,write=True);s=spec(domain)
    name=data.get('action');a=next((x for x in s['actions'] if x['name']==name),None)
    if not a:raise HTTPException(422,'Unknown domain action')
    vals=validate_fields(a['fields'],data,{'action':(Literal[name],...),'version':(int,Field(...,ge=1,strict=True))})
    obj=record(db,actor,domain,id,True)
    replay=begin_operation(db,actor,idempotency_key,f'{domain}.{id}.{name}',data)
    if replay is not None:return replay
    check_version(obj,vals['version'])
    if obj.status not in a['from']:raise HTTPException(409,'Invalid state transition')
    for v in vals.values():
        if isinstance(v,datetime):valid_datetime(v)
    if actor.patient_scope and not(domain=='D21' and name=='cancelled'):raise HTTPException(403,'Patient cannot perform staff action')
    if domain=='D18' and name in ('compatibility_verified','released') and not actor.roles.intersection({'clinician','laboratory'}):raise HTTPException(403,'Explicit human blood verifier role required')
    if domain=='D06' and name in ('signed','acknowledged','amended') and not actor.roles.intersection({'nurse','charge_nurse'}):raise HTTPException(403,'Nursing role required')
    if domain=='D10' and name in ('verified','released','corrected','publish_portal') and not actor.roles.intersection({'laboratory','lab','lab_verifier','lab_technologist'}):raise HTTPException(403,'Laboratory verifier role required')
    if domain=='D11' and name in ('verified','released','amended','publish_portal') and not actor.roles.intersection({'imaging','radiologist'}):raise HTTPException(403,'Imaging reviewer role required')
    if domain=='D08' and name in ('reviewed','dispensed','return_recorded') and 'pharmacist' not in actor.roles:raise HTTPException(403,'Pharmacist role required')
    if domain=='D10' and name=='acknowledge' and 'clinician' not in actor.roles:raise HTTPException(403,'Clinician acknowledgement required')
    run_action(db,actor,domain,obj,name,vals,idempotency_key)
    for k,v in vals.items():
        if name not in ('immunization','session','schedule') and k not in {'action','version','reason','slot_id','quantity'} and hasattr(obj,k):setattr(obj,k,v)
    if name not in ('reschedule','schedule','session','immunization','assign_device','release_device','acknowledge','publish_portal','revise'):obj.status=name
    if name=='revise':obj.status='ordered'
    obj.version+=1
    out=emit(db,actor,domain,obj,name,vals.get('reason'))
    if getattr(obj,'_scheduled_session_id',None):out['scheduled_session_id']=obj._scheduled_session_id
    if getattr(obj,'_device_assignment_id',None):out['device_assignment_id']=obj._device_assignment_id
    finish_operation(db,actor,idempotency_key,f'{domain}.{id}.{name}',data,out)
    return out

def run_action(db,actor,d,o,name,v,key):
    if d in ('D08','D10','D11','D16') and name not in ('return_recorded','acknowledge','publish_portal'):
        order=related(db,actor,ClinicalOrder,o.order_id,o.patient_id,o.encounter_id,lock=True)
        allowed_status=('signed','acknowledged','in_progress','completed') if name in ('corrected','amended') else ('signed','acknowledged','in_progress')
        if order.status not in allowed_status or order.version!=o.order_version:raise HTTPException(409,'Source order cancelled or revised; new authorized request required')
        if name in ('collected','scheduled','reviewed','assessed') and order.status in ('signed','acknowledged'):
            order.status='in_progress';order.version+=1;o.order_version=order.version
            if order.task_id:
                from ..models import Task
                task=db.get(Task,order.task_id);task.status='in_progress';task.version+=1
        if name in ('dispensed','released') or (d=='D16' and name=='completed'):
            order.status='completed';order.version+=1;o.order_version=order.version
            if order.task_id:
                from ..models import Task
                task=db.get(Task,order.task_id);task.status='completed';task.version+=1
    if d in ('D11','D12','D13') and name in ('scheduled','acquired','in_progress','recorded'):
        if o.asset_id:
            from ..models_erp import EquipmentAsset
            asset=related(db,actor,EquipmentAsset,o.asset_id,lock=True)
            if asset.status!='in_service':raise HTTPException(409,'Equipment taken out of service')
        if d=='D12' and o.cssd_cycle_id:
            from ..models_erp import CSSDCycle
            cycle=related(db,actor,CSSDCycle,o.cssd_cycle_id,lock=True)
            if cycle.status!='released':raise HTTPException(409,'Instrument cycle unavailable/quarantined')
    if d=='D02':
        if name=='booked':reserve_slot(db,actor,o.slot_id,o.id)
        if name=='reschedule':reserve_slot(db,actor,v['slot_id'],o.id);o.slot_id=v['slot_id']
        if name=='checked_in':
            enc=Encounter(id=uid(),organization_id=o.organization_id,facility_id=o.facility_id,patient_id=o.patient_id,kind='OPD',status='waiting',version=1)
            db.add(enc);db.flush();o.encounter_id=enc.id;o.ticket_number='Q-'+o.id
    elif d=='D04' and name=='admission_requested':
        adm=m.Admission(id=uid(),organization_id=o.organization_id,facility_id=o.facility_id,patient_id=o.patient_id,encounter_id=o.encounter_id,admission_reason=v['disposition_reason'],status='requested',created_by=actor.user_id)
        db.add(adm);db.flush();o.admission_id=adm.id;emit(db,actor,'D05',adm,'emergency_request')
    elif d=='D04' and name=='referral_requested':
        # Creates an actionable shared task; referral document needs explicit version selection.
        from ..models import Task
        db.add(Task(organization_id=o.organization_id,facility_id=o.facility_id,patient_id=o.patient_id,encounter_id=o.encounter_id,domain='D20',kind='referral',title=v['disposition_reason'],status='open'))
    elif d=='D05':
        if name=='admitted':
            bed=related(db,actor,m.Bed,v['bed_id'],lock=True)
            if not bed.active:raise HTTPException(409,'Bed unavailable')
            if db.scalar(select(m.BedAssignment).where(m.BedAssignment.bed_id==bed.id,m.BedAssignment.ended_at.is_(None))):raise HTTPException(409,'Bed occupied')
            for old in db.scalars(select(m.BedAssignment).where(m.BedAssignment.admission_id==o.id,m.BedAssignment.ended_at.is_(None)).with_for_update()):old.ended_at=utcnow()
            db.flush();db.add(m.BedAssignment(admission_id=o.id,bed_id=bed.id));o.current_bed_id=bed.id
        if name=='discharged':
            if db.scalar(select(m.DeviceAssignment).where(m.DeviceAssignment.admission_id==o.id,m.DeviceAssignment.ended_at.is_(None))):raise HTTPException(409,'Release documented device assignments before discharge')
            for old in db.scalars(select(m.BedAssignment).where(m.BedAssignment.admission_id==o.id,m.BedAssignment.ended_at.is_(None)).with_for_update()):old.ended_at=utcnow()
            o.current_bed_id=None
            enc=scoped_encounter(db,actor,o.encounter_id,lock=True);enc.status='discharged';enc.version+=1
    elif d=='D06':
        if name=='signed':o.signed_by=actor.user_id
        if name=='acknowledged':
            if o.receiving_staff_id!=actor.user_id:raise HTTPException(403,'Only designated receiving staff may acknowledge')
            o.acknowledged_by=actor.user_id
    elif d=='D08':
        if name in ('dispensed','return_recorded'):
            from .erp import get_eligible_lot,post_stock_movement,add_charge
            qty=v['quantity']
            if qty<=0:raise HTTPException(422,'Quantity must be positive')
            if name=='dispensed':
                if qty>o.quantity:raise HTTPException(409,'Dispense exceeds ordered quantity')
                if v['unit_price']<0:raise HTTPException(422,'Price must not be negative')
                lot=get_eligible_lot(db,actor,v['lot_id'],o.item_id)
                movement=post_stock_movement(db,actor,lot.id,v['location_id'],-qty,o.id,key+'-stock');o.dispense_movement_id=movement.id
                add_charge(db,actor,o.encounter_id,o.id,o.medication_name,qty,v['unit_price'],key+'-charge')
                o.dispensed_quantity=qty;o.lot_id=lot.id;o.location_id=v['location_id']
            else:
                if o.returned_quantity+qty>o.dispensed_quantity:raise HTTPException(409,'Return exceeds remaining dispensed quantity')
                db.add(m.MedicationReturn(medication_id=o.id,quantity=qty,reason=v['reason'],reviewer_id=actor.user_id))
                post_stock_movement(db,actor,o.lot_id,o.location_id,qty,o.id,key+'-return',original_id=o.dispense_movement_id,disposition='quarantine')
                o.returned_quantity+=qty
                # Quarantined return is recorded separately and cannot be dispensed until a future disposition workflow.
    elif d=='D10':
        if name=='collected':o.accession='ACC-'+o.id
        if name=='acknowledge':o.acknowledged_by=actor.user_id
        if name=='publish_portal':o.released_to_portal=True
        if name=='corrected':o.released_to_portal=False;o.acknowledged_by=None
    elif d=='D11':
        if name=='acquired':
            mime=v['file_mime']
            if mime not in ('image/png','image/jpeg','text/plain'):raise HTTPException(422,'Only PNG, JPEG or plain text allowed')
            try:b=base64.b64decode(v['file_base64'],validate=True)
            except Exception:raise HTTPException(422,'Invalid base64')
            if not b or len(b)>1024*1024:raise HTTPException(422,'File size must be 1..1048576 bytes')
            if mime=='image/png' and not b.startswith(b'\x89PNG\r\n\x1a\n'):raise HTTPException(422,'PNG signature mismatch')
            if mime=='image/jpeg' and not b.startswith(b'\xff\xd8\xff'):raise HTTPException(422,'JPEG signature mismatch')
            if mime=='text/plain':
                try:b.decode('utf-8')
                except UnicodeError:raise HTTPException(422,'Text must be UTF-8')
            from ..storage import file_store
            stored=file_store().put(b);o.file_path=stored.key;o.file_sha256=stored.sha256;o.file_mime=mime
        if name=='publish_portal':o.released_to_portal=True
        if name=='amended':o.released_to_portal=False
    elif d=='D12':
        if name=='scheduled':
            if v['ends_at']<=v['starts_at']:raise HTTPException(422,'End must follow start')
            db.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:key,0))'),{'key':o.organization_id+':room:'+v['room']})
            overlap=db.scalar(select(m.ProcedureCase).where(m.ProcedureCase.organization_id==o.organization_id,m.ProcedureCase.facility_id==o.facility_id,m.ProcedureCase.room==v['room'],m.ProcedureCase.status.notin_(['requested','closed','cancelled']),m.ProcedureCase.starts_at<v['ends_at'],m.ProcedureCase.ends_at>v['starts_at']))
            if overlap:raise HTTPException(409,'Room reservation overlaps')
        if name=='checklist_verified':o.checklist_verified_by=actor.user_id
    elif d=='D13' and name in ('assign_device','release_device'):
        from ..models_erp import EquipmentAsset
        if name=='assign_device':
            asset=related(db,actor,EquipmentAsset,v['asset_id'],lock=True)
            if asset.status!='in_service':raise HTTPException(409,'Device is unavailable for assignment')
            if db.scalar(select(m.DeviceAssignment).where(m.DeviceAssignment.asset_id==asset.id,m.DeviceAssignment.ended_at.is_(None))):raise HTTPException(409,'Device already assigned to an active episode')
            assignment=m.DeviceAssignment(id=uid(),organization_id=o.organization_id,facility_id=o.facility_id,patient_id=o.patient_id,encounter_id=o.encounter_id,round_id=o.id,admission_id=o.admission_id,asset_id=asset.id,status='assigned',created_by=actor.user_id)
            db.add(assignment);db.flush();o._device_assignment_id=assignment.id
            audit(db,actor,'D13',o.id,'device_assigned',{'assignment_id':assignment.id,'asset_id':asset.id})
        else:
            assignment=related(db,actor,m.DeviceAssignment,v['assignment_id'],o.patient_id,o.encounter_id)
            if assignment.round_id!=o.id:raise HTTPException(409,'Assignment belongs to another round; open its source round')
            related(db,actor,EquipmentAsset,assignment.asset_id,lock=True)
            if assignment.status!='assigned' or assignment.ended_at:raise HTTPException(409,'Device already released')
            assignment.status='released';assignment.version+=1;assignment.ended_at=utcnow();assignment.released_by=actor.user_id;assignment.release_reason=v['reason']
            audit(db,actor,'D13',o.id,'device_released',{'assignment_id':assignment.id})
    elif d=='D14' and name=='delivery_documented':
        child=Patient(id=uid(),organization_id=o.organization_id,facility_id=o.facility_id,display_name=v['child_name'],sex='unknown',status='active',version=1)
        db.add(child);db.flush();db.add(PatientIdentifier(patient_id=child.id,organization_id=o.organization_id,issuer='SYNTHETIC_BIRTH',value=v['child_identifier']));o.child_patient_id=child.id
    elif d=='D15' and name=='immunization':
        from ..models_erp import InventoryItem,InventoryLot
        item=related(db,actor,InventoryItem,v['item_id']);lot=related(db,actor,InventoryLot,v['lot_id'])
        if lot.item_id!=item.id or v['unit']!=item.unit or v['quantity']<=0:raise HTTPException(422,'Immunization item/lot/unit/quantity mismatch')
        db.add(m.ImmunizationRecord(visit_id=o.id,item_id=item.id,lot_id=lot.id,quantity=v['quantity'],unit=v['unit'],administered_at=v['administered_at'],recorded_by=actor.user_id))
    elif d=='D16':
        if name=='schedule':
            slot=reserve_slot(db,actor,v['slot_id'])
            ap=m.Appointment(id=uid(),organization_id=o.organization_id,facility_id=o.facility_id,patient_id=o.patient_id,slot_id=slot.id,reason='Synthetic therapy: '+o.id,status='booked',created_by=actor.user_id)
            db.add(ap);db.flush();emit(db,actor,'D02',ap,'rehab_booked')
            session=m.TherapySession(id=uid(),plan_id=o.id,appointment_id=ap.id,scheduled_at=slot.starts_at,author_id=actor.user_id);db.add(session);o._scheduled_session_id=session.id
        if name=='session':
            session=db.get(m.TherapySession,v['session_id'])
            if not session or session.plan_id!=o.id:raise HTTPException(404,'Session outside this plan')
            if db.scalar(select(m.TherapyProgress).where(m.TherapyProgress.session_id==session.id)):raise HTTPException(409,'Session already recorded')
            db.add(m.TherapyProgress(session_id=session.id,performed_at=v['performed_at'],progress=v['progress'],author_id=actor.user_id))
            appointment=related(db,actor,m.Appointment,session.appointment_id,o.patient_id,lock=True);appointment.status='completed';appointment.version+=1;emit(db,actor,'D02',appointment,'therapy_completed')
        if name=='completed':
            session_ids=list(db.scalars(select(m.TherapySession.id).where(m.TherapySession.plan_id==o.id)))
            if not session_ids or db.scalar(select(func.count()).select_from(m.TherapyProgress).where(m.TherapyProgress.session_id.in_(session_ids)))!=len(session_ids):raise HTTPException(409,'All scheduled sessions require progress before completing plan')
    elif d=='D17' and name=='performed':
        from .erp import add_charge
        if v['unit_price']<0:raise HTTPException(422,'Charge cannot be negative')
        add_charge(db,actor,o.encounter_id,o.id,o.procedure_name,Decimal('1'),v['unit_price'],key+'-charge')
    elif d=='D18':
        if name=='reserved':
            unit=related(db,actor,m.BloodUnit,v['unit_id'],lock=True)
            if unit.eligibility_status!='available' or unit.expiry_at<=utcnow():raise HTTPException(409,'Unit is expired, quarantined, recalled, or unavailable')
            if db.scalar(select(m.BloodRequest).where(m.BloodRequest.unit_id==unit.id,m.BloodRequest.status.in_(['reserved','compatibility_verified','released','administration_recorded']))):raise HTTPException(409,'Unit already reserved')
            o.unit_id=unit.id
        if name=='compatibility_verified':
            unit=related(db,actor,m.BloodUnit,o.unit_id,lock=True)
            if unit.eligibility_status!='available' or unit.expiry_at<=utcnow():raise HTTPException(409,'Unit ineligible')
            patient=scoped_patient(db,actor,o.patient_id,lock=True)
            o.verification_patient_version=patient.version;o.verification_evidence_hash=hashlib.sha256(v['verification_evidence'].encode()).hexdigest()
            o.verification_unit_version=unit.version;o.verification_request_version=o.version+1;o.verified_by=actor.user_id
        if name=='released':
            unit=related(db,actor,m.BloodUnit,o.unit_id,lock=True)
            patient=scoped_patient(db,actor,o.patient_id,lock=True)
            if patient.version!=o.verification_patient_version or hashlib.sha256(o.verification_evidence.encode()).hexdigest()!=o.verification_evidence_hash or unit.eligibility_status!='available' or unit.expiry_at<=utcnow() or unit.version!=o.verification_unit_version or o.version!=o.verification_request_version:raise HTTPException(409,'Eligibility or revision changed; human re-verification required')
            unit.eligibility_status='released';unit.version+=1
    elif d=='D20' and name=='exported':
        require(actor,'documents.export');require(actor,'documents.content')
        rev=validate_document(db,actor,o.document_revision_id,o.patient_id,o.encounter_id)
        o.packet=json.dumps({'kind':'SYNTHETIC_REFERRAL','external_received':False,'patient_id':o.patient_id,'encounter_id':o.encounter_id,'destination':o.destination,'reason':o.reason,'document_revision_id':rev.id,'content_hash':rev.content_hash,'content':rev.content},ensure_ascii=False)
    elif d=='D21' and name=='booked':
        if o.request_kind!='appointment':raise HTTPException(409,'Correction request cannot be booked')
        reserve_slot(db,actor,o.slot_id)
        ap=m.Appointment(id=uid(),organization_id=o.organization_id,facility_id=o.facility_id,patient_id=o.patient_id,slot_id=o.slot_id,reason=o.reason,status='booked',created_by=actor.user_id)
        db.add(ap);db.flush();o.appointment_id=ap.id;emit(db,actor,'D02',ap,'portal_booked')
    elif d=='D21' and name in ('completed','declined','cancelled'):
        if name=='completed' and o.request_kind=='appointment' and o.status!='booked':raise HTTPException(409,'Appointment must be booked first')
        if o.staff_task_id:
            from ..models import Task
            task=db.get(Task,o.staff_task_id);task.status='completed' if name=='completed' else 'cancelled';task.version+=1

@router.get('/D11/records/{id}/file')
def get_file(id:str,db:Session=Depends(get_db,scope="function"),actor=Depends(current_actor)):
    require(actor,'documents.content');require(actor,'documents.export')
    o=record(db,actor,'D11',id)
    if not o.file_path:raise HTTPException(404,'No file')
    from ..storage import file_store
    try:b=file_store().read(o.file_path,o.file_sha256)
    except FileNotFoundError:raise HTTPException(503,'Stored file unavailable')
    except ValueError:raise HTTPException(409,'Stored file checksum mismatch')
    audit(db,actor,'D11',o.id,'file.download',{'sha256':o.file_sha256})
    return Response(b,media_type=o.file_mime,headers={'Content-Disposition':'attachment; filename="imaging-study"','X-Content-Type-Options':'nosniff'})

@router.get('/D20/records/{id}/export')
def get_referral(id:str,db:Session=Depends(get_db,scope="function"),actor=Depends(current_actor)):
    require(actor,'documents.export');require(actor,'documents.content')
    o=record(db,actor,'D20',id)
    if not o.packet:raise HTTPException(409,'Packet not exported')
    return Response(o.packet,media_type='application/json',headers={'Content-Disposition':'attachment; filename="synthetic-referral.json"'})

@router.get('/portal/released-results')
def portal_results(db:Session=Depends(get_db,scope="function"),actor=Depends(current_actor)):
    require_domain(actor,'D21')
    if not actor.patient_scope:raise HTTPException(403,'Portal identity required')
    items=[]
    for cls in (m.LabRequest,m.ImagingStudy):
        for o in db.scalars(scoped_query(db,actor,cls).where(cls.released_to_portal.is_(True))):
            out=serialize(o);out.pop('file_path',None);items.append(out)
    return {'items':items}

def seed_clinical(db):
    """Explicit idempotent synthetic catalog seed; never called by application startup."""
    from datetime import timedelta
    common={'organization_id':'org-demo','facility_id':'facility-demo'}
    entries=[m.ServiceSlot(id='slot-demo',**common,label='Synthetic OPD morning',starts_at=datetime(2027,1,15,8,tzinfo=timezone.utc),capacity=20),
        m.ServiceSlot(id='slot-last',**common,label='Synthetic last-place concurrency slot',starts_at=datetime(2027,1,15,9,tzinfo=timezone.utc),capacity=1),
        m.Bed(id='bed-001',**common,ward='Synthetic ward',label='Bed 001'),m.Bed(id='bed-002',**common,ward='Synthetic ward',label='Bed 002'),
        m.BloodUnit(id='blood-001',**common,identifier='SYNTHETIC-BLOOD-001',expiry_at=datetime(2030,1,1,tzinfo=timezone.utc)),
        m.BloodUnit(id='blood-002',**common,identifier='SYNTHETIC-BLOOD-002',expiry_at=datetime(2030,1,1,tzinfo=timezone.utc))]
    for obj in entries:
        if not db.get(type(obj),obj.id):db.add(obj)
    db.flush()

@router.get('/portal/me')
def portal_me(db:Session=Depends(get_db,scope='function'),actor=Depends(current_actor)):
    require_domain(actor,'D21')
    if not actor.patient_scope:raise HTTPException(403,'Portal subject linkage required')
    p=scoped_patient(db,actor,actor.patient_scope)
    return {'id':p.id,'display_name':p.display_name,'birth_date':p.birth_date.isoformat() if p.birth_date else None,'sex':p.sex}

@router.get('/portal/encounters')
def portal_encounters(db:Session=Depends(get_db,scope='function'),actor=Depends(current_actor)):
    require_domain(actor,'D21')
    if not actor.patient_scope:raise HTTPException(403,'Portal subject linkage required')
    scoped_patient(db,actor,actor.patient_scope)
    rows=db.scalars(select(Encounter).where(Encounter.organization_id==actor.organization_id,Encounter.facility_id==actor.facility_id,Encounter.patient_id==actor.patient_scope,Encounter.published.is_(True)).order_by(Encounter.created_at.desc())).all()
    return {'items':[{'id':x.id,'patient_id':x.patient_id,'kind':x.kind,'status':x.status,'created_at':x.created_at.isoformat()} for x in rows]}
