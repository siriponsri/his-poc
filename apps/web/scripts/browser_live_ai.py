"""Real dr-train document-completeness acceptance through rendered HIS forms.

Requires an already running isolated synthetic app with explicit live profile.
No API writes outside visible UI actions, no credentials in evidence.
"""
import argparse,hashlib,json,os,uuid
from pathlib import Path
from urllib.parse import urlparse
from browser_support import provenance,safe_error,screenshot
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--base-url',default=os.getenv('HIS_BASE_URL','http://127.0.0.1:8000'))
parser.add_argument('--output-dir',type=Path,default=Path(__file__).resolve().parents[1]/'evidence/fullsystem/live-dr-train')
parser.add_argument('--headed',action='store_true')
parser.add_argument('--resume-report',type=Path,help='Resume human review of a successful inference from a retained failed harness report; never reissue inference')
parser.add_argument('--readback-report',type=Path,help='Inspect a completed PASS run through the UI without issuing inference or domain mutations')
ARGS=parser.parse_args();os.environ['HIS_BASE_URL']=ARGS.base_url.rstrip('/')
if ARGS.resume_report and ARGS.readback_report:parser.error('Choose either resume or completed-run readback')
from playwright.sync_api import sync_playwright,expect
from browser_driver import UI,BASE,PASSWORD

if urlparse(BASE).hostname not in ('localhost','127.0.0.1','::1'):raise SystemExit('Requires loopback synthetic app')
if len(PASSWORD)<12:raise SystemExit('Load the private synthetic seed password locally')
OUT=ARGS.output_dir;OUT.mkdir(parents=True,exist_ok=True)
report={**provenance(),'status':'NOT_RUN','assertions':[],
        'method':'Real Chromium DOM mutations -> HIS backend -> private dr-train Ollama; no API-only writes',
        'clinical_effectiveness':'NOT_RUN'}

def checked(text):report['assertions'].append(text)

def readback_completed(source):
 prior=json.loads(source.read_text(encoding='utf-8'))
 assert prior['status']=='PASS' and prior['result_id'] and prior['inference']['run']['outcome']=='success'
 proof={**provenance(),'status':'NOT_RUN','method':'DOM readback of prior completed live run; UI login only, no inference/domain mutations',
        'source_report':str(source),'source_report_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'assertions':[]}
 try:
  with sync_playwright() as pw:
   browser=pw.chromium.launch(headless=not ARGS.headed);page=browser.new_page(viewport={'width':1440,'height':1100},timezone_id='Asia/Bangkok');page.set_default_timeout(30000)
   domain_writes=[]
   page.on('request',lambda request:domain_writes.append({'method':request.method,'path':urlparse(request.url).path}) if request.method in ('POST','PATCH','DELETE') and urlparse(request.url).path.startswith('/api/v2/') and urlparse(request.url).path not in ('/api/v2/auth/login','/api/v2/auth/logout') else None)
   ui=UI(page);ui.login('clinician');page.goto(BASE+'/domains/D37')
   page.locator('.patient-context').get_by_role('combobox',name='ผู้ป่วย',exact=True).select_option('patient-001')
   page.locator('.patient-context').get_by_role('combobox',name='การรับบริการ',exact=True).select_option('encounter-001')
   with page.expect_response(lambda r:urlparse(r.url).path=='/api/v2/runs' and 'task_id='+prior['task_id'] in urlparse(r.url).query and r.request.method=='GET') as response:
    page.get_by_role('combobox',name='งานที่ผูกผู้ป่วย / encounter').select_option(prior['task_id'])
   body=response.value.json();items=body if isinstance(body,list) else body['items'];assert len(items)==1 and items[0]['id']==prior['inference']['run']['id']
   run=items[0];assert run['provider']=='dr_train_ollama' and run['provenance']['model_digest']==prior['inference']['run']['provenance']['model_digest']
   row=page.locator('.run-row');expect(row).to_have_count(1);expect(row).to_contain_text(run['provenance']['model']);expect(row).to_contain_text('dr_train_ollama')
   expect(row).to_contain_text(str(run['elapsed_ms'])+' ms');expect(row).to_contain_text('โทเคนเข้า '+str(run['usage']['prompt_eval_count'])+' · ออก '+str(run['usage']['eval_count']));expect(row).to_contain_text('ต้นทุน UNKNOWN')
   proof['assertions'].append('Task-scoped run ID from observed GET matches original inference; its own DOM row displays exact provider/model/latency/token counts/unknown cost')
   page.get_by_role('button').filter(has_text=prior['proposal_id']).first.click()
   region=page.get_by_role('region',name='ผลตรวจความครบถ้วนเอกสาร');expect(region).to_be_visible();assert region.locator('li').count()==5
   expect(page.locator('body')).to_contain_text(prior['result_id']);assert page.get_by_label('ข้อเสนอที่ตรวจจริง').is_disabled()
   assert page.get_by_role('button',name='อนุมัติรุ่นที่แสดง',exact=True).is_disabled() and page.get_by_role('button',name='ยืนยันบันทึกผล',exact=True).is_disabled()
   proof['assertions'].append('Committed human-reviewed proposal retains five typed findings and cannot be approved or committed again through the UI')
   assert not domain_writes,domain_writes;proof['observed_domain_mutations']=domain_writes
   proof['run_id']=run['id'];proof['proposal_id']=prior['proposal_id'];proof['result_id']=prior['result_id'];proof['status']='PASS'
   screenshot(page,OUT,'live-readback');browser.close()
 except Exception as error:
  proof['status']='FAIL';proof['reason']=safe_error(error)
  try:screenshot(page,OUT,'live-readback-failure')
  except Exception:pass
 (OUT/'browser-live-ai-readback.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({'status':proof['status'],'assertions':len(proof['assertions']),'reason':proof.get('reason')},ensure_ascii=False))
 return 0 if proof['status']=='PASS' else 1

if ARGS.readback_report:raise SystemExit(readback_completed(ARGS.readback_report))

content='\n'.join(['เอกสารสังเคราะห์เพื่อทดสอบระบบ',
 'อาการสำคัญ: มาทบทวนเอกสารตามนัด',
 'ประวัติ: เป็นข้อมูลสมมติ ไม่ใช่ผู้ป่วยจริง',
 'การประเมิน: ผู้บันทึกระบุว่าต้องทบทวนความครบถ้วนของข้อมูล',
 'ผู้บันทึก: ผู้ทดสอบระบบ A01'])
try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=not ARGS.headed)
  page=browser.new_page(viewport={'width':1440,'height':1100},timezone_id='Asia/Bangkok')
  page.set_default_timeout(30000);ui=UI(page);errors=[]
  page.on('pageerror',lambda error:errors.append(str(error)))
  ui.login('clinician')
  context={'patient_id':'patient-001','encounter_id':'encounter-001'}
  resumed=json.loads(ARGS.resume_report.read_text(encoding='utf-8')) if ARGS.resume_report else None
  if resumed:
   assert resumed['inference']['run']['outcome']=='success' and resumed['inference']['proposal']['evidence']['content']==content
   document={'id':resumed['document_id']};task={'id':resumed['task_id']}
   report['resumed_from']={'source':str(ARGS.resume_report),'sha256':hashlib.sha256(ARGS.resume_report.read_bytes()).hexdigest()}
  else:
   document=ui.create('D22',{**context,'title':'ทดสอบ AI จริง '+uuid.uuid4().hex[:6],'content':content})
   task=ui.create('D07',{**context,'domain':'D37','kind':'document_review','title':'ตรวจความครบถ้วนด้วย AI จริง'},resource='tasks')
  report['document_id']=document['id'];report['task_id']=task['id']
  page.goto(BASE+'/domains/D37')
  page.locator('.patient-context').get_by_role('combobox',name='ผู้ป่วย',exact=True).select_option('patient-001')
  page.locator('.patient-context').get_by_role('combobox',name='การรับบริการ',exact=True).select_option('encounter-001')
  expect(page.get_by_text('AI จริง · dr-train',exact=True)).to_be_visible()
  assert page.get_by_label('สถานการณ์ mock',exact=False).count()==0
  checked('Live profile is explicit; mock simulation selector is absent')
  page.get_by_role('combobox',name='งานที่ผูกผู้ป่วย / encounter').select_option(task['id'])
  page.get_by_role('combobox',name='เอกสารหลักฐาน').select_option(document['id'])
  if resumed:
   created=resumed['inference']
   button=page.get_by_role('button').filter(has_text=created['proposal']['id']).first
   expect(button).to_be_visible();button.click()
  else:
   page.set_default_timeout(210000)
   created=ui.response_click('proposals',page.get_by_role('button',name='สร้างข้อเสนอจากเอกสารที่บันทึก',exact=True))
   page.set_default_timeout(30000)
  report['inference']=created
  assert created['demo'] is False and created['run']['provider']=='dr_train_ollama'
  assert created['run']['outcome']=='success' and created['proposal']
  assert created['run']['provenance']['model_digest']=='ab914ef406c9a78e2a8893eaa3b0ef78049f6c4e2703626433028e838d3a168b'
  assert created['run']['usage']['eval_count']>0
  assert created['run']['measured_cost'] is None
  checked('Real pinned model returned a successful durable inference run with token usage and unknown cost')
  proposal=created['proposal'];checklist=proposal['action']['completeness']
  statuses={item['key']:item['status'] for item in checklist['items']}
  assert statuses=={'chief_complaint':'present','history':'present','assessment':'present','plan':'missing','author':'present'},statuses
  assert all(not item['evidence_quote'] or item['evidence_quote'] in content for item in checklist['items'])
  region=page.get_by_role('region',name='ผลตรวจความครบถ้วนเอกสาร')
  expect(region).to_be_visible();assert region.locator('li').count()==5
  expect(region).to_contain_text('ยังไม่พบในเอกสาร')
  checked('Five typed findings and source quotes render; the authored missing-plan case is identified')
  screenshot(page,OUT,'live-checklist')
  page.get_by_label('ข้อเสนอที่ตรวจจริง').fill('ผู้ตรวจทดสอบตรวจทานแล้ว พบว่าต้นฉบับสังเคราะห์ยังขาดแผนติดตาม ต้องให้ผู้บันทึกตรวจสอบก่อนดำเนินงานต่อ')
  edited=ui.response_click('proposals/'+proposal['id']+'/review',page.get_by_role('button',name='บันทึกเป็นรุ่นใหม่',exact=True))
  assert edited['version']==proposal['version']+1
  assert edited['action_hash']!=proposal['action_hash']
  assert edited['action']['completeness']==checklist
  checked('Human edit creates a new bound version while retaining the original model checklist')
  approved=ui.response_click('proposals/'+proposal['id']+'/review',page.get_by_role('button',name='อนุมัติรุ่นที่แสดง',exact=True))
  assert approved['status']=='approved' and approved['version']==edited['version']
  result=ui.response_click('proposals/'+proposal['id']+'/commit',page.get_by_role('button',name='ยืนยันบันทึกผล',exact=True))
  assert result['action']['completeness']==checklist and result['proposal_id']==proposal['id']
  expect(page.get_by_text('ยืนยันผลที่บันทึกแล้ว',exact=True)).to_be_visible()
  checked('Authenticated human approval and commit produce the bound result, never autonomous model writes')
  page.reload();expect(page.locator('body')).to_contain_text(result['id'])
  page.get_by_role('combobox',name='งานที่ผูกผู้ป่วย / encounter').select_option(task['id'])
  expect(page.locator('body')).to_contain_text(created['run']['provenance']['model'])
  checked('Reload retains the result and per-run model provenance')
  screenshot(page,OUT,'live-result')
  assert not errors,errors
  checked('No uncaught browser page errors')
  report['proposal_id']=proposal['id'];report['result_id']=result['id'];report['statuses']=statuses
  report['source_content_sha256']=hashlib.sha256(content.encode()).hexdigest()
  report['mutations']=ui.trace;report['status']='PASS'
  browser.close()
except Exception as error:
 report['status']='FAIL';report['reason']=safe_error(error)
 try:screenshot(page,OUT,'live-failure')
 except Exception:pass
finally:
 (OUT/'browser-live-ai.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({'status':report['status'],'assertions':len(report['assertions']),'document_id':report.get('document_id'),'task_id':report.get('task_id'),'result_id':report.get('result_id'),'reason':report.get('reason')},ensure_ascii=False))
if report['status']!='PASS':raise SystemExit(1)
