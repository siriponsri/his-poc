"""Reproduce project-authored read-only Thai UI record fixtures. No database or network."""
import hashlib,json,random
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SEED=20261112
VERSION='1.0.0'

def build():
 rng=random.Random(SEED)
 cases=[
 ('complete','เอกสารครบ','ตรวจการแสดงเอกสารที่มีผู้จัดทำและเวลาลงนามสังเคราะห์'),
 ('missing_author','ขาดผู้จัดทำ','แสดงช่องข้อมูลผู้จัดทำที่ยังไม่มี'),
 ('missing_signature','ขาดเวลาลงนาม','แสดง signed_at ที่ไม่มี โดยไม่ถือเป็น clinical signing'),
 ('empty','ข้อความว่าง','รับรู้เอกสารว่าง; ไม่สร้างผลทางคลินิกจากข้อความว่าง'),
 ('multiline','ข้อความไทยหลายบรรทัด','ตรวจการตัดบรรทัดภาษาไทยและการรักษาข้อความยาว'),
 ('pending','ข้อเสนอรอตรวจ','แสดงข้อเสนอจำลอง pending แบบอ่านอย่างเดียว'),
 ('edited','แก้ไขแล้วรออนุมัติใหม่','แสดงเหตุที่การแก้ summary ต้องสร้าง version/hash ใหม่'),
 ('rejected','ผู้ตรวจปฏิเสธ','แสดงสถานะ rejected; ไม่ใช่ผลยืนยัน'),
 ('committed','บันทึกผลแล้ว','แสดงผลยืนยันและ audit ใน snapshot; ไม่มีการเขียน backend'),
 ('stale','หลักฐานเปลี่ยน','อธิบาย 409 stale context และการทบทวนฉบับใหม่'),
 ('expired','ข้อเสนอหมดอายุ','อธิบาย expiry โดยไม่เปลี่ยน backend enum'),
 ('forbidden','ไม่มีสิทธิ์เขียน','แสดง 403 เป็นสถานะการตอบกลับ ไม่ใช่คุณสมบัติผู้ป่วย'),
 ('task_closed','งานปิดแล้ว','อธิบาย TASK_NOT_OPEN และการไม่เปิดงานกลับเอง'),
 ('failed','provider ล้มเหลว','แสดง failed แม้ HTTP เป็น 200'),
 ('timeout','provider หมดเวลารอ','แสดง timeout จำลองและไม่สร้าง proposal สำเร็จ'),
 ('abstained','provider งดให้ข้อเสนอ','แสดงเหตุผลการงดให้ข้อเสนอที่อ่านกลับได้'),
 ('replayed','ส่งคำสั่งเดิมซ้ำ','แสดง replay ของผลเดิม ไม่เกิดธุรกรรมใหม่'),
 ('network_error','ไม่ทราบผลจากเครือข่าย','แสดงการเก็บ key/payload สำหรับ retry โดยไม่สมมติว่าสำเร็จหรือล้มเหลวแน่ชัด')]
 records=[]
 for i,(state,label,description) in enumerate(cases,1):
  doc={'text':f'เอกสารสังเคราะห์กรณี {i:02d}\nบันทึกเพื่อทดสอบความครบถ้วนของเอกสารเท่านั้น\nรหัสตัวอย่าง {rng.randrange(10000,99999)} ไม่ได้เชื่อมกับบุคคลจริง','author':'ผู้จัดทำสังเคราะห์','signed_at':'2026-11-12T08:00:00Z'}
  if state=='missing_author':doc.pop('author')
  if state in ['missing_signature','pending','edited']:doc.pop('signed_at')
  if state=='empty':doc['text']=''
  if state=='multiline':doc['text']='\n'.join(f'บรรทัดที่ {j}: ข้อมูลสมมติสำหรับทดสอบการอ่านและแก้ไขข้อความภาษาไทย ไม่มีผลตรวจทางคลินิกจริง' for j in range(1,21))
  records.append({'fixture_id':f'TH-{i:03d}','label':label,'patient_id':f'fixture-p-{i:03d}','encounter_id':f'fixture-e-{i:03d}','document':doc,'expected_state':state,'description':description,'source_id':'SRC-OWN-THAI-SYNTHETIC','asset_id':'ASSET-THAI-RECORDS-001','data_classification':'WHOLLY_SYNTHETIC','contains_real_patient_source_data':False,'api_response_fixture_ref':None})
 return {'schema_version':'1.0','mode':'READ_ONLY_FIXTURE','generator':{'name':'generate_fixtures.py','version':VERSION,'seed':SEED},'records':records}

def main():
 p=ROOT/'data/fixtures/thai_records.json';p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(json.dumps(build(),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({'path':str(p.relative_to(ROOT)),'records':len(build()['records']),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}))
if __name__=='__main__':main()
