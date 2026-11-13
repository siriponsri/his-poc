"""Authored browser J01-J10 acceptance against a clean isolated seeded v2 app.
NOT_RUN until this file actually launches a browser and all scenario assertions pass.
No direct API writes: every mutation uses rendered React forms/buttons.
"""
import hashlib,json,os,uuid
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse
from browser_support import options, provenance, safe_error, screenshot
ARGS=options(__doc__,journeys=True)
from playwright.sync_api import sync_playwright,expect
from browser_driver import UI,BASE,PASSWORD
OUT=ARGS.output_dir
if urlparse(BASE).hostname not in ('127.0.0.1','localhost','::1'):raise SystemExit('Requires loopback synthetic development app')
if len(PASSWORD)<12:raise SystemExit('Set HIS_SEED_PASSWORD for the explicit synthetic seed')
report={**provenance(),'status':'NOT_RUN','browser_assertions':0,'journeys':{f'J{i:02}':{'status':'NOT_RUN'} for i in range(1,11)},'method':'Playwright DOM forms/actions; response observation for exact IDs, no direct API mutations','full_L3_claim':False}
state={}
report['requested_journeys']=ARGS.journeys or list(report['journeys'])
def ctx(n=1):return {'patient_id':f'patient-{n:03}','encounter_id':f'encounter-{n:03}'}
def J01(ui):
 ui.login('registration');p=ui.create('D01',{'display_name':'ผู้ป่วยสังเคราะห์ browser '+uuid.uuid4().hex[:6],'identifier':'BROWSER-'+uuid.uuid4().hex,'sex':'unknown'})
 for a in ['verified','active']:p=ui.action('D01',p,a)
 appointment=ui.create('D02',{'patient_id':p['id'],'slot_id':'slot-demo','reason':'Synthetic browser J01'})
 for a in ['booked','checked_in','called']:appointment=ui.action('D02',appointment,a)
 e={'id':appointment['encounter_id']};ui.care(p['id']);ui.login('clinician');e=ui.action('D03',e,'in_consult')
 context={'patient_id':p['id'],'encounter_id':e['id']};doc=ui.create('D22',{**context,'title':'Browser J01 document','content':'DEMO browser source evidence'})
 task=ui.create('D07',{**context,'domain':'D37','kind':'document_review','title':'Browser J01 review'},resource='tasks');result=ui.ai(p['id'],e['id'],doc,task)
 assert result['task_id']==task['id'];return {'patient_id':p['id'],'appointment_id':appointment['id'],'encounter_id':e['id'],'document_id':doc['id'],'task_id':task['id'],'result_id':result['id']}
def J02(ui):
 order=ui.order('lab');ui.login('laboratory');lab=ui.create('D10',{**ctx(),'order_id':order['id'],'analyte':'Synthetic browser analyte','specimen_type':'synthetic serum'})
 for a in ['collected','received']:lab=ui.action('D10',lab,a)
 lab=ui.action('D10',lab,'preliminary',{'result_value':'5','unit':'demo-unit','reference_range':'manual 1-10'})
 for a in ['verified','released','publish_portal']:lab=ui.action('D10',lab,a)
 ui.login('clinician');lab=ui.action('D10',lab,'acknowledge');ui.login('laboratory');lab=ui.action('D10',lab,'corrected',{'result_value':'6','unit':'demo-unit','reference_range':'manual 1-10','reason':'Synthetic manual correction'})
 lab=ui.action('D10',lab,'publish_portal');ui.select('D10',lab);assert any(str(h.get('snapshot',{}).get('result_value'))=='5' for h in ui.last_detail['history']);state['published_lab']=lab
 return {'order_id':order['id'],'lab_id':lab['id'],'corrected_value':lab['result_value'],'released_to_portal':lab['released_to_portal']}
def J03(ui):
 order=ui.order('medication');ui.login('pharmacist');dispense=ui.create('D08',{**ctx(),'order_id':order['id'],'item_id':'item-demo','medication_name':'วัสดุสังเคราะห์สำหรับ POC','prescribed_dose':'manual synthetic 1 unit','route':'manual','quantity':'5','unit':'unit'})
 for a in ['reviewed','prepared']:dispense=ui.action('D08',dispense,a)
 ui.lose_response=True;dispense=ui.action('D08',dispense,'dispensed',{'lot_id':'lot-demo','location_id':'stock-main','quantity':'5','unit_price':'2'})
 dispensed_id=dispense['id'];dispense=ui.action('D08',dispense,'return_recorded',{'quantity':'2','reason':'Synthetic return to quarantine'})
 assert dispense['id']==dispensed_id;return {'order_id':order['id'],'dispense_id':dispense['id'],'retry':'lost HTTP response then same-key UI retry verified equal result','return_status':dispense['status']}
def J04(ui):
 ui.login('nurse');visit=ui.create('D03',{'patient_id':'patient-003','kind':'ER','department_id':'department-demo'});context={'patient_id':'patient-003','encounter_id':visit['id']}
 em=ui.create('D04',{**context,'presenting_complaint':'Synthetic emergency'})
 em=ui.action('D04',em,'assessed',{'triage_level':'manual','assessment':'Manual synthetic assessment'});em=ui.action('D04',em,'in_care');em=ui.action('D04',em,'admission_requested',{'disposition_reason':'Synthetic admit'})
 adm={'id':em['admission_id']};adm=ui.action('D05',adm,'admitted',{'bed_id':'bed-001'});adm=ui.action('D05',adm,'transfer_requested');adm=ui.action('D05',adm,'admitted',{'bed_id':'bed-002'})
 task=ui.create('D07',{**context,'domain':'D06','kind':'followup','title':'Browser pending handoff task'},resource='tasks')
 hand=ui.create('D06',{**context,'summary':'Synthetic nursing handover','pending_tasks':'Review pending task','task_ids':task['id'],'receiving_staff_id':'user-nurse'})
 for a in ['signed','acknowledged']:hand=ui.action('D06',hand,a)
 adm=ui.action('D05',adm,'discharge_ready',{'discharge_summary':'Synthetic discharge summary'});adm=ui.action('D05',adm,'discharged')
 ui.login('registration');followup=ui.create('D02',{'patient_id':'patient-003','slot_id':'slot-demo','reason':'Synthetic followup'});followup=ui.action('D02',followup,'booked')
 assert adm['status']=='discharged';return {'encounter_id':visit['id'],'admission_id':adm['id'],'handover_id':hand['id'],'task_id':task['id'],'followup_id':followup['id']}
def J05(ui):
 ui.login('registration');visit=ui.create('D03',{'patient_id':'patient-002','kind':'OPD','department_id':'department-demo'})
 ui.login('billing');price=ui.create('D23',{'name':'Browser price '+uuid.uuid4().hex[:6],'effective_from':'2026-01-01','unit_price':'1000.00'},resource='prices')
 charge=ui.create('D23',{'encounter_id':visit['id'],'source_id':str(uuid.uuid4()),'label':'Synthetic service','quantity':'1','price_version_id':price['id']},resource='charges')
 invoice=ui.create('D23',{'encounter_id':visit['id'],'label':'Browser invoice'})
 for a in ['price','review','invoice']:invoice=ui.action('D23',invoice,a)
 claim=ui.create('D24',{'invoice_id':invoice['id'],'payer_name':'Synthetic payer'})
 for a in ['validate','export','simulate_submit']:claim=ui.action('D24',claim,a)
 claim=ui.action('D24',claim,'remittance',{'approved_amount':'800.00','source_key':str(uuid.uuid4())});assert Decimal(claim['financials']['gross_received'])==0
 claim=ui.action('D24',claim,'reconcile');ui.login('finance');receipt=ui.create('D25',{'invoice_id':invoice['id'],'payer_name':'Synthetic payer','amount':'800.00'})
 for a in ['review','post']:receipt=ui.action('D25',receipt,a)
 receipt=ui.action('D25',receipt,'refund_request',{'amount':'100.00','reason':'Synthetic refund','release_allocation':False});refund=receipt['refunds'][0]['id']
 ui.login('finance_reviewer');receipt=ui.action('D25',receipt,'refund_approve',{'refund_id':refund});ui.login('finance');ui.lose_response=True;receipt=ui.action('D25',receipt,'refund',{'refund_id':refund})
 cost=ui.create('D26',{'encounter_id':visit['id'],'label':'Synthetic materials','amount':'300.00','method_version':'manual-v1'})
 for a in ['review','post']:cost=ui.action('D26',cost,a)
 ui.select('D23',invoice);finance=ui.last_detail['financials']
 expected={'billed':1000,'submitted':1000,'approved':800,'gross_received':800,'refunded':100,'net_received':700,'outstanding':200,'cost':300}
 assert all(Decimal(finance[name])==value for name,value in expected.items()),finance
 return {'encounter_id':visit['id'],'charge_id':charge['id'],'invoice_id':invoice['id'],'claim_id':claim['id'],'receipt_id':receipt['id'],'refund_id':refund,'cost_id':cost['id'],'financials':finance}
def J06(ui):
 ui.login('inventory');purchase=ui.create('D27',{'supplier_id':'supplier-demo','item_id':'item-demo','quantity':'10','unit_price':'20'})
 ui.login('procurement_approver');purchase=ui.action('D27',purchase,'approve');ui.login('inventory');purchase=ui.action('D27',purchase,'record_po')
 ui.lose_response=True;purchase=ui.action('D27',purchase,'receive',{'lot_id':'lot-demo','location_id':'stock-main','quantity':'4','receipt_key':str(uuid.uuid4())});assert purchase['status']=='part_received'
 purchase=ui.action('D27',purchase,'receive',{'lot_id':'lot-demo','location_id':'stock-main','quantity':'6','receipt_key':str(uuid.uuid4())})
 for a in ['verify_invoice','close']:purchase=ui.action('D27',purchase,a)
 move=ui.create('D28',{'lot_id':'lot-demo','location_id':'stock-main','quantity':'-3','source_id':purchase['id']})
 for a in ['validate','post']:move=ui.action('D28',move,a)
 returned=ui.action('D28',move,'reverse',{'quantity':'2','disposition':'quarantine'});return {'purchase_id':purchase['id'],'receipts':[r['id'] for r in purchase['receipts']],'issue_id':move['id'],'return_id':returned['id']}
def J07(ui):
 ui.login('system_admin');ui.page.goto(BASE+'/domains/D34');ui.page.get_by_role('button',name='＋ เพิ่มบัญชีและสิทธิ์',exact=True).click();username='browser_'+uuid.uuid4().hex[:8]
 ui.fill([('username','ชื่อบัญชี'),('display_name','ชื่อแสดง'),('password','รหัสผ่านอย่างน้อย 12 ตัวอักษร'),('role','บทบาท'),('facility_id','รหัสหน่วยบริการ')],{'username':username,'display_name':'Browser scoped user','password':PASSWORD,'role':'registration','facility_id':'facility-demo'})
 user=ui.response_click('admin/users',ui.page.locator('form').get_by_role('button',name='บันทึก',exact=True));ui.page.get_by_role('button',name='ปรับ membership',exact=True).click()
 ui.fill([('role','บทบาท'),('facility_id','รหัสหน่วยบริการ')],{'role':'registration','facility_id':'facility-second'});grant=ui.response_click('admin/users/'+user['id']+'/memberships',ui.page.get_by_role('button',name='ยืนยันปรับ membership',exact=True))
 ui.login(username);ui.page.get_by_label('ขอบเขตหน่วยบริการ',exact=True).select_option(grant['membership']['id']);expect(ui.page.locator('body')).to_contain_text('facility-second')
 ui.page.goto(BASE+'/domains/D25');expect(ui.page.get_by_role('heading',name='ไม่มีสิทธิ์เข้าพื้นที่นี้')).to_be_visible()
 context=ui.page.context.browser.new_context();admin=UI(context.new_page());admin.login('system_admin');admin.page.goto(BASE+'/domains/D34');admin.page.get_by_role('tab',name='เซสชัน',exact=True).click();admin.page.locator('.search-field input').fill(user['id']);admin.page.locator('.record-button').first.click();admin.page.get_by_role('button',name='ถอนเซสชัน',exact=True).click()
 with admin.page.expect_response(lambda r:'/admin/sessions/' in r.url and r.url.endswith('/revoke') and r.request.method=='POST') as response:admin.page.get_by_role('button',name='ยืนยันถอนเซสชัน',exact=True).click()
 assert response.value.status==200;session_id=response.value.json()['id'];ui.page.goto(BASE+'/home');expect(ui.page.get_by_role('heading',name='เข้าสู่พื้นที่ทำงาน')).to_be_visible();ui.role=None;context.close();return {'user_id':user['id'],'session_id':session_id,'membership_id':grant['membership']['id']}
def J08(ui):
 order=ui.order('imaging');ui.login('imaging');study=ui.create('D11',{**ctx(),'order_id':order['id'],'modality':'SYNTHETIC','body_site':'retina synthetic'});study=ui.action('D11',study,'scheduled');study=ui.action('D11',study,'acquired',{'file_base64':'synthetic'})
 study=ui.action('D11',study,'report_draft',{'report':'Manual synthetic report; no live DR prediction'})
 for a in ['verified','released']:study=ui.action('D11',study,a)
 ui.select('D11',study)
 with ui.page.expect_download() as download:ui.page.get_by_role('link',name='ดาวน์โหลดไฟล์สังเคราะห์ที่ตรวจ checksum แล้ว').click()
 assert hashlib.sha256(Path(download.value.path()).read_bytes()).hexdigest()==study['file_sha256']
 doc=ui.create('D22',{**ctx(),'title':'Browser imaging report','content':study['report']});task=ui.create('D07',{**ctx(),'domain':'D37','kind':'dr_review','title':'Explicit mock human DR review'},resource='tasks');result=ui.ai('patient-001','encounter-001',doc,task,edit=False)
 ui.login('imaging');referral=ui.create('D20',{**ctx(),'destination':'Synthetic eye clinic','reason':'Human review complete','document_revision_id':doc['current_version_id']})
 for a in ['reviewed','exported']:referral=ui.action('D20',referral,a)
 ui.select('D20',referral)
 with ui.page.expect_download() as download:ui.page.get_by_role('link',name='ดาวน์โหลดเอกสารส่งต่อ',exact=True).click()
 packet=json.loads(Path(download.value.path()).read_text(encoding='utf-8'));assert packet['external_received'] is False
 return {'study_id':study['id'],'file_sha256':study['file_sha256'],'document_id':doc['id'],'task_id':task['id'],'result_id':result['id'],'referral_id':referral['id']}
def J09(ui):
 ui.login('inventory');asset=ui.create('D29',{'name':'Synthetic browser asset','location_id':'location-store'});asset=ui.action('D29',asset,'activate');asset=ui.action('D29',asset,'schedule',{'maintenance_due':'2026-11-12'});asset=ui.action('D29',asset,'start');asset=ui.action('D29',asset,'record',{'evidence':'Synthetic maintenance evidence'})
 ui.login('quality');asset=ui.action('D29',asset,'verify',{'evidence':'Synthetic independent maintenance review'});ui.login('inventory');asset=ui.action('D29',asset,'release')
 cycle=ui.create('D31',{'kind':'cssd','asset_id':asset['id'],'cycle_code':'SYN-'+uuid.uuid4().hex[:8]});cycle=ui.action('D31',cycle,'clean');cycle=ui.action('D31',cycle,'record_cycle',{'evidence':'Synthetic cycle manual evidence'});ui.login('support_reviewer');cycle=ui.action('D31',cycle,'review_release');ui.login('inventory');cycle=ui.action('D31',cycle,'release')
 linen=ui.create('D31',{'kind':'linen','location_id':'location-ward','quantity':'5'});linen=ui.action('D31',linen,'return_linen',{'returned_quantity':'5'});linen=ui.action('D31',linen,'reconcile')
 work=ui.create('D31',{'kind':'facility','location_id':'location-store','description':'Synthetic repair'});work=ui.action('D31',work,'assign',{'assignee_id':'user-inventory'});work=ui.action('D31',work,'verify',{'evidence':'Manual inspection'});work=ui.action('D31',work,'close')
 ui.login('quality');incident=ui.create('D32',{'description':'Synthetic maintenance incident','asset_id':asset['id']});incident=ui.action('D32',incident,'triage',{'classification':'synthetic maintenance'});incident=ui.action('D32',incident,'investigate');incident=ui.action('D32',incident,'plan',{'owner_id':'user-quality','action_plan':'Record repair followup'});incident=ui.action('D32',incident,'evidence',{'evidence':'Followup complete'});ui.login('support_reviewer')
 for a in ['review','close']:incident=ui.action('D32',incident,a)
 ui.login('quality');report_row=ui.create('D33',{'name':'Browser operational report','period_start':'2020-01-01','period_end':'2035-12-31'})
 for a in ['generate','review','export']:report_row=ui.action('D33',report_row,a)
 assert report_row['summary']['total_encounters']>=4
 ui.login('operations_admin');ui.page.goto(BASE+'/domains/D38');job=ui.response_click('operations/jobs',ui.page.get_by_role('button',name='สร้าง backup',exact=True));expect(ui.page.locator('details').filter(has_text=job['id'])).to_contain_text('completed',timeout=120000)
 # Operator backup/restore has separate native integration suite; browser verifies the job's actual worker result.
 return {'asset_id':asset['id'],'cycle_id':cycle['id'],'linen_id':linen['id'],'facility_id':work['id'],'incident_id':incident['id'],'report_id':report_row['id'],'backup_job_id':job['id']}
def J10(ui):
 if 'published_lab' not in state:J02(ui)
 ui.login('patient');ui.page.goto(BASE+'/domains/D21');expect(ui.page.get_by_role('heading',name='ประวัติและผลที่เผยแพร่ให้คุณ')).to_be_visible();expect(ui.page.locator('body')).to_contain_text(state['published_lab']['id']);assert ui.page.locator('.patient-context').count()==0
 request=ui.create('D21',{'request_kind':'appointment','slot_id':'slot-demo','reason':'Browser own followup'});assert request['patient_id']=='patient-001'
 ui.login('registration');request=ui.action('D21',request,'reviewed');request=ui.action('D21',request,'booked');assert request['appointment_id']
 ui.login('patient2');private_reason='Synthetic other-subject request '+uuid.uuid4().hex
 other=ui.create('D21',{'request_kind':'appointment','slot_id':'slot-demo','reason':private_reason});assert other['patient_id']=='patient-002'
 ui.login('patient')
 with ui.page.expect_response(lambda r:urlparse(r.url).path=='/api/v2/clinical/D21/records/'+other['id'] and r.request.method=='GET') as denied:
  ui.page.goto(BASE+'/domains/D21?record='+other['id'])
 assert denied.value.status==404,('Expected scope-hidden404',denied.value.status);expect(ui.page.get_by_role('alert')).to_be_visible();assert private_reason not in ui.page.locator('body').inner_text(),'Other subject request reason appeared in portal DOM'
 ui.login('patient');ui.select('D21',request);assert ui.last_detail['patient_id']=='patient-001';ui.page.set_viewport_size({'width':390,'height':844});ui.page.get_by_role('button',name='เปิดหรือปิดเมนู').click();ui.page.keyboard.press('Escape');ui.page.screenshot(path=str(OUT/'journey-J10-mobile.png'),full_page=True)
 return {'portal_patient_id':'patient-001','published_result_id':state['published_lab']['id'],'request_id':request['id'],'appointment_id':request['appointment_id'],'other_subject_request_id':other['id'],'other_subject_read_status':denied.value.status,'other_subject_reason_absent':True}
try:
 OUT.mkdir(parents=True,exist_ok=True)
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=not ARGS.headed,executable_path=os.environ.get('CHROMIUM_PATH'));context=browser.new_context(viewport={'width':1440,'height':1000},timezone_id='Asia/Bangkok');ui=UI(context.new_page());ui.page.set_default_timeout(20000)
  for id,scenario in [(j,globals()[j]) for j in (ARGS.journeys or [f'J{i:02}' for i in range(1,11)])]:
   before=len(ui.trace)
   try:
    records=scenario(ui);screenshot(ui.page,OUT,id+'-pass');report['journeys'][id]={'status':'PASS','record_ids':records,'executed_dom_mutations':ui.trace[before:]};report['browser_assertions']+=1;print(id+' PASS',flush=True)
   except Exception as error:
    screenshot(ui.page,OUT,id+'-failure');report['journeys'][id]={'status':'FAIL','reason':safe_error(error),'executed_dom_mutations':ui.trace[before:]};break
  report['status']='PASS' if all(report['journeys'][j]['status']=='PASS' for j in report['requested_journeys']) else 'FAIL';browser.close()
except Exception as error:report['reason']=safe_error(error)
finally:
 report['full_L3_claim']=False;report['scope_note']='Combine executed scenarios with canonical acceptance, negative/concurrency and domain coverage; this script alone does not certify L3';(OUT/'browser-journeys.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({'status':report['status'],'journeys':{k:v['status'] for k,v in report['journeys'].items()},'browser_assertions':report['browser_assertions']}))
if report['status']!='PASS':raise SystemExit(1)
