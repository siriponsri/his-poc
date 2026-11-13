"""Rendered local PostgreSQL acceptance for domains not visited by J01-J10.

All writes use visible typed forms/actions. Direct forbidden GET navigations use
the authenticated browser cookie to check server enforcement, not just menu hiding.
"""
import json
import os
import uuid
from pathlib import Path
from urllib.parse import urlparse
from browser_support import options, provenance, safe_error, screenshot
DOMAINS=['D09',*[f'D{i:02}' for i in range(12,20)],'D30','D35','D36']
ARGS=options(__doc__,domains=DOMAINS)
from playwright.sync_api import sync_playwright, expect
from browser_driver import UI, BASE, PASSWORD

OUT=ARGS.output_dir
if urlparse(BASE).hostname not in ('localhost','127.0.0.1','::1'):
 raise SystemExit('Requires loopback synthetic development app')
if len(PASSWORD)<12:raise SystemExit('Set HIS_SEED_PASSWORD for the isolated synthetic seed')
CTX={'patient_id':'patient-001','encounter_id':'encounter-001'}
report={**provenance(),'status':'NOT_RUN','domains':{d:{'status':'NOT_RUN'} for d in DOMAINS},
        'requested_domains':ARGS.domains or DOMAINS,
        'method':'Playwright typed forms/actions and observed responses; forbidden GET via browser navigation',
        'full_L2_claim':False}


def persisted(ui,d,row,resource=None):
 ui.select(d,row,resource)
 assert ui.last_detail['id']==row['id'] and ui.last_detail['version']==row['version']
 expect(ui.page.locator('.history li').first).to_be_visible()
 ui.page.reload();ui.select(d,row,resource)
 assert ui.last_detail['version']==row['version'] and ui.last_detail['status']==row['status']
 return ui.last_detail


def D09(ui):
 order=ui.order('medication');ui.login('pharmacist')
 med=ui.create('D08',{**CTX,'order_id':order['id'],'item_id':'item-demo',
  'medication_name':'วัสดุสังเคราะห์สำหรับ POC','prescribed_dose':'Manual synthetic 1 unit',
  'route':'manual','quantity':'2','unit':'unit'})
 med=ui.action('D08',med,'reviewed');ui.login('nurse')
 row=ui.create('D09',{**CTX,'medication_id':med['id'],'scheduled_at':'2026-11-13T10:00',
                    'dose':'Manual synthetic 1 unit','route':'manual'})
 row=ui.action('D09',row,'verified');ui.lose_response=True
 row=ui.action('D09',row,'administered',{'actual_at':'2026-11-13T10:01'})
 row=ui.action('D09',row,'corrected',{'actual_at':'2026-11-13T10:02','reason':'Synthetic manual correction'})
 detail=persisted(ui,'D09',row)
 assert sum(h['action']=='administered' for h in detail['history'])==1
 return row


def D12(ui):
 ui.login('clinician');row=ui.create('D12',{**CTX,'procedure_name':'Synthetic browser OR'})
 room='BROWSER-'+uuid.uuid4().hex
 row=ui.action('D12',row,'scheduled',{'room':room,'starts_at':'2027-01-01T08:00','ends_at':'2027-01-01T09:00'})
 for action,values in [('checklist_verified',{'checklist':'Manual synthetic checklist'}),('in_progress',{}),
   ('documented',{'anesthesia_record':'Manual synthetic record'}),('closed',{})]:
  row=ui.action('D12',row,action,values)
 persisted(ui,'D12',row);expect(ui.page.get_by_role('button',name='เริ่มหัตถการ',exact=True)).to_have_count(0)
 return row


def D13(ui):
 ui.login('clinician');admission=ui.create('D05',{**CTX,'admission_reason':'Synthetic browser ICU'})
 row=ui.create('D13',{**CTX,'admission_id':admission['id'],'observation_name':'Manual synthetic observation',
  'observation_value':'10','unit':'demo','observed_at':'2026-11-13T08:00','round_note':'Manual round'})
 for action in ['recorded','reviewed','signed']:row=ui.action('D13',row,action)
 row=ui.action('D13',row,'amended',{'observation_value':'11','round_note':'Manual amended round','reason':'Synthetic correction'})
 detail=persisted(ui,'D13',row)
 assert any(str(h.get('snapshot',{}).get('observation_value'))=='10' for h in detail['history'])
 return row


def D14(ui):
 ui.login('clinician');row=ui.create('D14',{**CTX,'gestation_note':'Manual synthetic browser pregnancy'})
 row=ui.action('D14',row,'antenatal_active');ui.lose_response=True
 row=ui.action('D14',row,'delivery_documented',{'delivery_note':'Synthetic manual birth','child_name':'Synthetic browser newborn','child_identifier':'BIRTH-'+uuid.uuid4().hex})
 for action in ['verified','closed']:row=ui.action('D14',row,action)
 persisted(ui,'D14',row);assert row['child_patient_id']
 return row


def D15(ui):
 ui.login('clinician');row=ui.create('D15',{**CTX,'measurement_name':'Synthetic weight','measurement_value':'3',
  'unit':'kg','measured_at':'2026-11-13T08:00','immunization_note':'Manual synthetic entry'})
 for action in ['recorded','reviewed','closed']:row=ui.action('D15',row,action)
 row=ui.action('D15',row,'amended',{'measurement_value':'3.1','reason':'Synthetic manual correction'})
 persisted(ui,'D15',row);expect(ui.page.get_by_role('img',name='แนวโน้ม patient-001 / Synthetic weight (kg)',exact=True)).to_be_visible()
 return row


def D16(ui):
 order=ui.order('rehab');row=ui.create('D16',{**CTX,'order_id':order['id'],'goals':'Manual synthetic mobility goal','therapist_id':'user-clinician'})
 row=ui.action('D16',row,'assessed',{'assessment':'Manual assessment'});row=ui.action('D16',row,'active')
 for day in [13,14,15]:
  row=ui.action('D16',row,'schedule',{'slot_id':'slot-demo'})
  row=ui.action('D16',row,'session',{'session_id':row['scheduled_session_id'],'performed_at':f'2026-11-{day}T08:00','progress':f'Manual synthetic session {day-12}'})
 for action in ['reviewed','completed']:row=ui.action('D16',row,action)
 detail=persisted(ui,'D16',row);assert len(detail['sessions'])==3
 return row


def D17(ui):
 ui.login('clinician');row=ui.create('D17',{**CTX,'tooth_code':'SYN-11','finding':'Manual synthetic finding','procedure_name':'Synthetic browser dental procedure'})
 for action in ['reviewed','scheduled']:row=ui.action('D17',row,action)
 ui.lose_response=True;row=ui.action('D17',row,'performed',{'unit_price':'10'})
 for action in ['verified','closed']:row=ui.action('D17',row,action)
 persisted(ui,'D17',row);return row


def D18(ui):
 ui.login('clinician');row=ui.create('D18',{**CTX,'indication':'Manual synthetic blood request'})
 row=ui.action('D18',row,'reviewed');row=ui.action('D18',row,'reserved',{'unit_id':'blood-001'})
 row=ui.action('D18',row,'compatibility_verified',{'verification_evidence':'Synthetic manual verifier evidence; no automated matching'})
 row=ui.action('D18',row,'released');row=ui.action('D18',row,'administration_recorded',{'administration_note':'Manual synthetic event'})
 persisted(ui,'D18',row);return row


def D19(ui):
 ui.login('clinician');row=ui.create('D19',{**CTX,'diet_description':'Manual synthetic diet','allergy_note':'Manual synthetic allergy','meal_period':'BROWSER-'+uuid.uuid4().hex})
 row=ui.action('D19',row,'reviewed');row=ui.action('D19',row,'revise',{'diet_description':'Manual revised diet','allergy_note':'Manual reviewed allergy'})
 for action in ['reviewed','prepared']:row=ui.action('D19',row,action)
 ui.lose_response=True;row=ui.action('D19',row,'delivered');persisted(ui,'D19',row);return row


def D30(ui):
 ui.login('quality');ui.action('D30',{'id':'staff-nurse'},'credential',{'status':'active','reason':'Explicit synthetic browser test setup'},resource='staff');day=uuid.uuid4().int%300+1
 from datetime import datetime,timedelta
 date=(datetime(2030,1,1)+timedelta(days=day)).strftime('%Y-%m-%d')
 row=ui.create('D30',{'staff_id':'staff-nurse','starts_at':date+'T08:00','ends_at':date+'T16:00'})
 for action in ['review','publish']:row=ui.action('D30',row,action)
 ui.login('nurse');row=ui.action('D30',row,'acknowledge');persisted(ui,'D30',row)
 ui.login('quality');next_date=(datetime(2030,1,1)+timedelta(days=day+1)).strftime('%Y-%m-%d')
 row=ui.action('D30',row,'revise',{'starts_at':next_date+'T08:00','ends_at':next_date+'T16:00'})
 for action in ['review','publish']:row=ui.action('D30',row,action)
 ui.login('nurse');path,button=ui.prepare_action('D30',row,'acknowledge')
 quality_context=ui.page.context.browser.new_context();quality=UI(quality_context.new_page());quality.login('quality')
 staff=quality.action('D30',{'id':'staff-nurse'},'credential',{'status':'suspended','reason':'Synthetic browser privilege suspension'},resource='staff')
 assert staff['credential_status']=='suspended'
 try:
  with ui.page.expect_response(lambda r:urlparse(r.url).path=='/api/v2/'+path and r.request.method=='POST') as denied:button.click()
  assert denied.value.status==403;expect(ui.page.get_by_role('alert')).to_be_visible()
  ui.trace.append({'check':'credential_revocation_denies_previously_open_rendered_acknowledgement','http_status':403,'staff_id':staff['id']})
 finally:
  try:
   quality.page.locator('.detail-card').get_by_role('button',name='ตรวจหรือระงับสมรรถนะ',exact=True).click()
   action=quality.resource('D30','staff')['actions'][0]
   quality.fill(action['fields'],{'status':'active','reason':'Synthetic browser explicit reactivation'})
   staff=quality.response_click('erp/staff/'+staff['id']+'/credential',quality.page.locator('form').last.get_by_role('button',name='ยืนยันตรวจหรือระงับสมรรถนะ',exact=True))
   assert staff['credential_status']=='active'
  finally:ui.trace.extend(quality.trace);quality_context.close()
 row=ui.action('D30',row,'acknowledge');persisted(ui,'D30',row);return row


def D35(ui):
 ui.login('system_admin');values={'source_id':str(uuid.uuid4()),'sequence':'1','contract_version':'his-local-event-v1','kind':'test','source_record_id':'Synthetic browser local event'}
 row=ui.create('D35',values);duplicate=ui.create('D35',values);assert row['id']==duplicate['id']
 for action in ['validate','queue','fail','retry','deliver','acknowledge']:row=ui.action('D35',row,action)
 assert len(row['attempts'])==2 and row['external_integration_status']=='NOT_CONNECTED'
 persisted(ui,'D35',row);return row


def D36(ui):
 ui.login('quality');row=ui.create('D36',{'name':'Synthetic browser dataset','encounter_kind':'OPD'})
 for action in ['preview','approve','freeze','export']:row=ui.action('D36',row,action)
 persisted(ui,'D36',row)
 with ui.page.expect_download() as download:
  ui.page.get_by_role('link',name='ดาวน์โหลดชุดข้อมูลที่อนุมัติ',exact=True).click()
 dataset=json.loads(Path(download.value.path()).read_text(encoding='utf-8'));assert dataset['items']
 partitions={}
 for item in dataset['items']:assert partitions.setdefault(item['patient_id'],item['partition'])==item['partition']
 row=ui.action('D36',row,'revoke');persisted(ui,'D36',row);return row


try:
 OUT.mkdir(parents=True,exist_ok=True)
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=not ARGS.headed,executable_path=os.getenv('CHROMIUM_PATH'))
  context=browser.new_context(viewport={'width':1440,'height':1000},timezone_id='Asia/Bangkok')
  ui=UI(context.new_page());ui.page.set_default_timeout(20000)
  for d in ARGS.domains or DOMAINS:
   start=len(ui.trace)
   try:
    row=globals()[d](ui);screenshot(ui.page,OUT,d+'-persisted')
    ui.login('registration');response=ui.page.goto(BASE+'/api/v2/'+ui.resource(d)['path']+'/'+row['id'])
    assert response.status==403, f'{d}: wrong-role direct GET status {response.status}'
    ui.page.goto(BASE+'/domains/'+d)
    expect(ui.page.get_by_role('heading',name='ไม่มีสิทธิ์เข้าพื้นที่นี้')).to_be_visible()
    report['domains'][d]={'status':'PASS','record_id':row['id'],'version':row['version'],
      'final_status':row['status'],'wrong_role_direct_get_status':response.status,
      'reload_persistence':'PASS','history_visible':'PASS','executed_dom_mutations':ui.trace[start:]}
   except Exception as error:
    screenshot(ui.page,OUT,d+'-failure');report['domains'][d]={'status':'FAIL','reason':safe_error(error),'executed_dom_mutations':ui.trace[start:]}
   print(d,report['domains'][d]['status'],flush=True)
  report['status']='PASS' if all(report['domains'][d]['status']=='PASS' for d in report['requested_domains']) else 'FAIL'
  browser.close()
except Exception as error:report['reason']=safe_error(error)
finally:
 (OUT/'browser-domains.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({'status':report['status'],'domains':{d:v['status'] for d,v in report['domains'].items()}}))
if report['status']!='PASS':raise SystemExit(1)
