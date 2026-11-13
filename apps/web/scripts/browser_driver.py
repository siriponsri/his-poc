"""DOM-only mutation driver for the authored v2 browser acceptance scenarios.
Uses API responses observed by Playwright only for exact IDs/assertions; no API writes.
"""
import json,os,uuid
from pathlib import Path
from urllib.parse import urlparse
from playwright.sync_api import expect
ROOT=Path(__file__).resolve().parents[3]
CATALOG={d['id']:d for d in json.loads((ROOT/'apps/web/src/data/resource-catalog.json').read_text(encoding='utf-8'))}
BASE=os.environ.get('HIS_BASE_URL','http://127.0.0.1:8000').rstrip('/')
PASSWORD=os.environ.get('HIS_SEED_PASSWORD','')
CORE={
'D01':{'label':'ผู้ป่วย','path':'patients','fields':[('display_name','ชื่อผู้ป่วยสังเคราะห์'),('identifier','เลขประจำตัวผู้ป่วย'),('issuer','หน่วยออกเลข'),('birth_date','วันเกิด'),('sex','เพศ')],'actions':{'verified':'ตรวจยืนยัน','active':'เปิดใช้แฟ้ม','inactive':'ปิดใช้แฟ้ม'}},
'D03':{'label':'การรับบริการ','path':'encounters','fields':[('patient_id','ผู้ป่วย'),('kind','ประเภทการรับบริการ'),('department_id','รหัสแผนก')],'actions':{'in_consult':'เริ่มตรวจ','reviewed':'ทบทวน','completed':'ตรวจเสร็จ','closed':'ปิดการรับบริการ'}},
'D07':{'label':'คำสั่งตรวจและรักษา','path':'orders','fields':[('patient_id','ผู้ป่วย'),('encounter_id','การรับบริการ'),('kind','ประเภทคำสั่ง'),('code','รหัสรายการ'),('label','รายการที่สั่ง'),('instructions','คำสั่งโดยบุคลากร'),('quantity','จำนวน'),('unit','หน่วย')],'actions':{'signed':'ลงนามคำสั่ง','acknowledged':'รับทราบคำสั่ง','in_progress':'เริ่มดำเนินงาน','completed':'ดำเนินงานเสร็จ','cancelled':'ยกเลิกคำสั่ง'}},
'D22':{'label':'เอกสารและฉบับแก้ไข','path':'documents','fields':[('patient_id','ผู้ป่วย'),('encounter_id','การรับบริการ'),('title','ชื่อเอกสาร'),('content','เนื้อหาเอกสาร')],'actions':{'in_review':'ส่งตรวจทาน','attested':'รับรองฉบับที่แสดง','returned':'ส่งคืนแก้ไข','draft':'กลับสู่ร่าง'}},
}
TASK={'label':'งานที่มอบหมาย','path':'tasks','fields':[('patient_id','ผู้ป่วย'),('encounter_id','การรับบริการ'),('domain','รหัส Domain เช่น D07'),('kind','ประเภทงาน'),('title','ชื่องาน')],'actions':{'in_progress':'เริ่มงาน','completed':'ปิดงาน','cancelled':'ยกเลิกงาน'}}
class UI:
 def __init__(self,page):
  self.page=page;self.role=None;self.trace=[]
  page.on('requestfailed',lambda request:self.trace.append({'check':'browser_request_failed','path':urlparse(request.url).path,'method':request.method,'failure':request.failure}))
 def login(self,role):
  if self.role==role:return
  self.page.goto(BASE+'/home')
  expect(self.page.get_by_role('button',name='ออกจากระบบ',exact=True).or_(self.page.get_by_role('heading',name='เข้าสู่พื้นที่ทำงาน'))).to_be_visible()
  if self.page.get_by_role('button',name='ออกจากระบบ',exact=True).count():self.page.get_by_role('button',name='ออกจากระบบ',exact=True).click()
  expect(self.page.get_by_role('heading',name='เข้าสู่พื้นที่ทำงาน')).to_be_visible()
  self.page.get_by_label('ชื่อบัญชี',exact=True).fill(role);self.page.get_by_label('รหัสผ่าน',exact=True).fill(PASSWORD)
  self.page.get_by_role('button',name='เข้าสู่ระบบ →',exact=True).click();expect(self.page.get_by_role('button',name='ออกจากระบบ',exact=True)).to_be_visible();self.role=role
 def resource(self,domain,resource=None):
  if resource=='tasks':return TASK
  if domain in CORE:return CORE[domain]
  choices=CATALOG[domain]['resources'];return next((r for r in choices if r['id'].endswith('-'+str(resource))),choices[0])
 def open(self,domain,resource=None):
  spec=self.resource(domain,resource);self.page.goto(BASE+'/domains/'+domain)
  tab=self.page.get_by_role('tab',name=spec['label'],exact=True)
  if domain=='D07' or (domain not in CORE and len(CATALOG[domain]['resources'])>1):
   expect(tab).to_be_visible()
   if spec.get('detailPath') is False:
    with self.page.expect_response(lambda r:urlparse(r.url).path=='/api/v2/'+spec['path'] and r.request.method=='GET') as listed:tab.click()
    assert listed.value.status==200;body=listed.value.json();self.last_list=body if isinstance(body,list) else body['items']
   else:tab.click()
  expect(self.page.get_by_role('heading',name=spec['label'],exact=True).first).to_be_visible();return spec
 def fill(self,fields,values):
  form=self.page.locator('form').last
  mapping={(f['name'] if isinstance(f,dict) else f[0]):f if isinstance(f,dict) else {'name':f[0],'label':f[1]} for f in fields}
  for name,value in values.items():
   if name not in mapping:raise ValueError('No rendered typed field '+name)
   field=mapping[name]
   if field.get('type')=='hidden':continue
   control=form.get_by_label(field['label'],exact=False).first
   if name=='file_base64':control.set_input_files({'name':'synthetic.txt','mimeType':'text/plain','buffer':b'SYNTHETIC IMAGE FILE; no clinical inference'});continue
   tag=control.evaluate('(element)=>element.tagName.toLowerCase()')
   kind=control.get_attribute('type')
   if kind=='checkbox':control.set_checked(bool(value))
   elif tag=='select':control.select_option([str(v) for v in value.split(',')] if control.get_attribute('multiple') is not None else str(value))
   elif kind=='datetime-local':control.fill(str(value).replace('Z','')[:16])
   else:control.fill(str(value))
 def response_click(self,path,button):
  invalid=button.evaluate("b=>{const f=b.closest('form');return f?[...f.elements].filter(e=>e.willValidate&&!e.checkValidity()).map(e=>e.labels?.[0]?.innerText?.slice(0,100)||e.type):[]}")
  if invalid:raise AssertionError('Rendered form rejects missing or invalid fields on '+path+': '+', '.join(invalid))
  if getattr(self,'lose_response',False):
   self.lose_response=False;captured={}
   def lost(route):
    reply=route.fetch();captured['body']=reply.json();captured['key']=route.request.headers.get('idempotency-key');route.abort()
   pattern='**/api/v2/'+path;self.page.route(pattern,lost);button.click();expect(self.page.get_by_role('button',name='Retry ด้วยคำสั่งเดิม',exact=True)).to_be_visible();self.page.unroute(pattern,lost)
   result=self.response_click(path,self.page.get_by_role('button',name='Retry ด้วยคำสั่งเดิม',exact=True));assert result==captured['body'];assert captured['key'] and self.last_operation_key==captured['key'];self.trace.append({'check':'lost_response_retry_same_result_and_key','operation_key':captured['key']});return result
  try:
   with self.page.expect_response(lambda r:urlparse(r.url).path=='/api/v2/'+path and r.request.method in ('POST','PATCH')) as response:button.click()
  except Exception as error:raise AssertionError('Rendered mutation response missing for '+path+': '+str(error)) from error
  result=response.value
  if result.status not in (200,201,202):raise AssertionError(f'HTTP {result.status} on {path}; inspect authorized server diagnostics')
  self.last_operation_key=result.request.headers.get('idempotency-key');body=result.json();self.trace.append({'actor':self.role,'path':path,'id':body.get('id'),'status':body.get('status')});return body
 def create(self,domain,values,resource=None):
  spec=self.open(domain,resource);self.page.get_by_role('button',name='＋ เพิ่ม'+spec['label'],exact=True).click();self.fill(spec['fields'],values)
  return self.response_click(spec['path'],self.page.locator('form').last.get_by_role('button',name='บันทึก',exact=True))
 def select(self,domain,row,resource=None):
  spec=self.open(domain,resource);search=self.page.locator('.search-field input');search.fill(row['id']);button=self.page.locator('.record-button').filter(has_text=row['id']).first;expect(button).to_be_visible();
  if spec.get('detailPath') is False:
   button.click();self.last_detail=next(item for item in self.last_list if item['id']==row['id']);expect(self.page.locator('.detail-card')).to_contain_text(row['id']);return spec
  try:
   with self.page.expect_response(lambda r:urlparse(r.url).path=='/api/v2/'+spec['path']+'/'+row['id'] and r.request.method=='GET') as response:button.click()
  except Exception as error:raise AssertionError('Rendered detail response missing for '+spec['path']+'/'+row['id']+': '+str(error)) from error
  assert response.value.status==200;self.last_detail=response.value.json();expect(self.page.locator('.detail-card')).to_contain_text(row['id']);return spec
 def action(self,domain,row,name,values=None,resource=None):
  path,button=self.prepare_action(domain,row,name,values,resource)
  return self.response_click(path,button)
 def prepare_action(self,domain,row,name,values=None,resource=None):
  spec=self.select(domain,row,resource);values=values or {}
  if domain in CORE or resource=='tasks':label=spec['actions'][name];path=spec['path']+'/'+row['id']+'/transition';fields=[{'name':'reason','label':'เหตุผล / สรุป'},{'name':'acknowledge_pending','label':'ตรวจรายการงานค้างและยืนยันการปิดด้วยตนเอง','type':'checkbox'}]
  else:
   action=next(a for a in spec['actions'] if a['name']==name);label=action['label'];fields=action.get('fields',[]);path=action.get('path',spec['path']+'/{id}/actions').replace('{id}',row['id'])
  self.page.locator('.detail-card').get_by_role('button',name=label,exact=True).click();self.fill(fields,values)
  return path,self.page.locator('form').last.get_by_role('button',name='ยืนยัน'+label,exact=True)
 def care(self,patient_id):
  self.login('system_admin');self.page.goto(BASE+'/domains/D34');self.page.locator('.search-field input').fill('user-clinician');self.page.locator('.record-button').filter(has_text='user-clinician').first.click();self.page.get_by_role('button',name='มอบหมายผู้ป่วย',exact=True).click();self.fill([('patient_id','รหัสผู้ป่วยในหน่วยบริการ')],{'patient_id':patient_id});self.response_click('admin/users/user-clinician/care-assignments',self.page.get_by_role('button',name='ยืนยันมอบหมายผู้ป่วย',exact=True))
 def order(self,kind,patient='patient-001',encounter='encounter-001'):
  self.login('clinician');o=self.create('D07',{'patient_id':patient,'encounter_id':encounter,'kind':kind,'code':'item-demo' if kind=='medication' else 'SYN-'+uuid.uuid4().hex[:8],'label':'วัสดุสังเคราะห์สำหรับ POC' if kind=='medication' else 'Synthetic '+kind,'instructions':'Manual synthetic instruction','quantity':'10','unit':'unit' if kind=='medication' else 'test'});return self.action('D07',o,'signed')
 def ai(self,patient,encounter,doc,task,edit=True):
  self.login('clinician');self.page.goto(BASE+'/domains/D37');self.page.locator('.patient-context').get_by_role('combobox',name='ผู้ป่วย',exact=True).select_option(patient);self.page.locator('.patient-context').get_by_role('combobox',name='การรับบริการ',exact=True).select_option(encounter)
  self.page.get_by_label('งานที่ผูกผู้ป่วย / encounter').select_option(task['id']);self.page.get_by_label('เอกสารหลักฐาน').select_option(doc['id'])
  proposal=self.response_click('proposals',self.page.get_by_role('button',name='สร้างข้อเสนอจากเอกสารที่บันทึก',exact=True))['proposal']
  if edit:
   self.page.get_by_label('ข้อเสนอที่ตรวจจริง').fill('DEMO reviewed by browser journey');proposal=self.response_click('proposals/'+proposal['id']+'/review',self.page.get_by_role('button',name='บันทึกเป็นรุ่นใหม่',exact=True))
  proposal=self.response_click('proposals/'+proposal['id']+'/review',self.page.get_by_role('button',name='อนุมัติรุ่นที่แสดง',exact=True))
  result=self.response_click('proposals/'+proposal['id']+'/commit',self.page.get_by_role('button',name='ยืนยันบันทึกผล',exact=True));expect(self.page.get_by_text('ยืนยันผลที่บันทึกแล้ว',exact=True)).to_be_visible();self.page.reload();expect(self.page.locator('body')).to_contain_text(result['id']);return result
