"""Browser conflict recovery, backend denial, audit and non-seeding restart proof.

Mutations use rendered forms. The only service control is an explicit local
Docker Compose application restart; no database reset, migration or seed.
"""
import json
import os
import subprocess
import time
import urllib.request
import uuid
from browser_support import options, provenance, safe_error, screenshot, ROOT
ARGS=options(__doc__)
from playwright.sync_api import sync_playwright,expect
from browser_driver import UI,BASE,PASSWORD
from urllib.parse import urlparse

if urlparse(BASE).hostname not in ('localhost','127.0.0.1','::1'):
 raise SystemExit('Requires local isolated synthetic application')
if len(PASSWORD)<12:raise SystemExit('Set HIS_SEED_PASSWORD for the isolated synthetic seed')
OUT=ARGS.output_dir;OUT.mkdir(parents=True,exist_ok=True)
report={**provenance(),'status':'NOT_RUN','assertions':[],'method':'Rendered forms, observed responses and explicit non-seeding Docker app restart'}


def checked(message):report['assertions'].append(message)


try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=not ARGS.headed,executable_path=os.getenv('CHROMIUM_PATH'))
  context=browser.new_context(viewport={'width':1440,'height':1000});ui=UI(context.new_page());ui.page.set_default_timeout(20000)
  try:
   ui.login('registration');row=ui.create('D01',{'display_name':'Synthetic conflict '+uuid.uuid4().hex[:8],
          'identifier':'RECOVERY-'+uuid.uuid4().hex,'sex':'unknown'})
   path,stale_button=ui.prepare_action('D01',row,'verified')
   other=UI(context.new_page());other.role='registration';winner=other.action('D01',row,'verified')
   with ui.page.expect_response(lambda r:urlparse(r.url).path=='/api/v2/'+path and r.request.method=='POST') as reply:
    stale_button.click()
   assert reply.value.status==409
   expect(ui.page.get_by_role('alert')).to_contain_text('ข้อมูลหรือสถานะเปลี่ยนแล้ว')
   expect(ui.page.get_by_role('button',name='Retry ด้วยคำสั่งเดิม',exact=True)).to_have_count(0)
   checked('stale rendered action receives real 409 and definitive recovery without retaining unknown-outcome retry')
   ui.page.get_by_role('button',name='โหลดล่าสุด',exact=True).click();ui.select('D01',winner)
   row=ui.action('D01',winner,'active');assert row['version']==winner['version']+1
   checked('reload latest then authorized next action succeeds without reconnect or resetting application')
   ui.select('D01',row);expect(ui.page.locator('.history li').first).to_be_visible()
   checked('server audit history rendered for successful patient mutation')
   report['patient_id']=row['id'];report['patient_version']=row['version']
   cookie=context.cookies();assert any(c.get('httpOnly') for c in cookie if c['name'].startswith('his'))
   stored=ui.page.evaluate('Object.keys(localStorage).concat(Object.keys(sessionStorage))')
   assert not any(any(secret in key.lower() for secret in ['token','password','session','csrf']) for key in stored)
   checked('browser session cookie HttpOnly and no credential keys in frontend storage')
   forbidden=ui.page.goto(BASE+'/api/v2/erp/D25/records');assert forbidden.status==403
   checked('direct finance API read denied to registration browser identity')
   ui.login('auditor')
   with ui.page.expect_response(lambda r:urlparse(r.url).path=='/api/v2/audit' and r.request.method=='GET') as audit_response:
    ui.page.goto(BASE+'/audit')
   audit_rows=audit_response.value.json()['items'];event=next(e for e in audit_rows if e['entity_id']==row['id'] and e['action']=='active')
   report['audit_event_id']=event['id'];assert PASSWORD not in json.dumps(audit_rows)
   search=ui.page.locator('.search-field input');search.fill(row['id'])
   expect(ui.page.locator('.record-button').first).to_be_visible();ui.page.locator('.record-button').first.click()
   expect(ui.page.locator('.detail-card')).to_contain_text(row['id'])
   expect(ui.page.locator('.detail-card')).to_contain_text('active')
   expect(ui.page.get_by_role('alert')).to_have_count(0)
   assert PASSWORD not in ui.page.locator('body').inner_text()
   checked('auditor inspects actual patient entity ID and transition action in rendered audit without credentials')
   screenshot(ui.page,OUT,'auditor-patient-transition')
   ui.login('clinician')
   doc_a=ui.create('D22',{'patient_id':'patient-001','encounter_id':'encounter-001','title':'Synthetic delayed A '+uuid.uuid4().hex[:6],'content':'Synthetic A context'})
   doc_b=ui.create('D22',{'patient_id':'patient-002','encounter_id':'encounter-002','title':'Synthetic current B '+uuid.uuid4().hex[:6],'content':'Synthetic B context'})
   ui.page.goto(BASE+'/domains/D22')
   patient=ui.page.locator('.patient-context').get_by_role('combobox',name='ผู้ป่วย',exact=True)
   patient.select_option('patient-001')
   ui.page.locator('.patient-context').get_by_role('combobox',name='การรับบริการ',exact=True).select_option('encounter-001')
   ui.page.locator('.search-field input').fill(doc_a['id']);held=[]
   def delay_a(route):held.append((route,route.fetch()))
   pattern='**/api/v2/documents/'+doc_a['id'];ui.page.route(pattern,delay_a)
   ui.page.locator('.record-button').filter(has_text=doc_a['id']).click()
   expect(ui.page.locator('.detail-card')).to_contain_text(doc_a['id'])
   deadline=time.monotonic()+10
   while not held and time.monotonic()<deadline:ui.page.wait_for_timeout(25)
   assert held,'Delayed source response was not intercepted before deadline'
   patient.select_option('patient-002')
   ui.page.locator('.patient-context').get_by_role('combobox',name='การรับบริการ',exact=True).select_option('encounter-002')
   with ui.page.expect_response(lambda r:urlparse(r.url).path=='/api/v2/documents/'+doc_a['id'] and r.request.method=='GET') as delayed:
    held[0][0].fulfill(response=held[0][1])
   delayed.value.finished();ui.page.unroute(pattern,delay_a)
   ui.page.evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
   expect(patient).to_have_value('patient-002')
   expect(ui.page.locator('.detail-card')).not_to_contain_text(doc_a['id'])
   expect(ui.page.locator('.record-button').filter(has_text=doc_b['id'])).to_be_visible()
   checked('patient A detail response arriving after B selection cannot repopulate B detail or action context')
   report['context_document_ids']={'A':doc_a['id'],'B':doc_b['id']}
   ui.login('registration')
   ui.page.goto(BASE+'/domains/D01');ui.select('D01',row);before=dict(ui.last_detail)
   screenshot(ui.page,OUT,'before-restart')
   with (OUT/'docker-restart.txt').open('w',encoding='utf-8') as log:
    result=subprocess.run(['docker','compose','restart','app'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
   report['restart_command']=['docker','compose','restart','app'];report['restart_exit_code']=result.returncode
   assert result.returncode==0
   deadline=time.monotonic()+90
   while True:
    try:
     with urllib.request.urlopen(BASE+'/ready',timeout=2) as ready:
      if ready.status==200:break
    except Exception:
     if time.monotonic()>=deadline:raise TimeoutError('Application restart readiness timeout')
     time.sleep(.5)
   ui.page.reload();ui.select('D01',row);after=ui.last_detail
   assert after['id']==before['id'] and after['version']==before['version'] and after['display_name']==before['display_name'] and after['status']=='active'
   checked('same UI-created patient, version, name and active state survive app restart without seeding')
   screenshot(ui.page,OUT,'after-restart');other.page.close()
   ui.login('operations_admin');ui.page.goto(BASE+'/domains/D38')
   backup=ui.response_click('operations/jobs',ui.page.get_by_role('button',name='สร้าง backup',exact=True))
   expect(ui.page.locator('details').filter(has_text=backup['id'])).to_contain_text('completed',timeout=120000)
   choice=ui.page.locator('select[aria-label="เลือก backup เพื่อทดสอบกู้คืน"] option').filter(has_text=backup['id'])
   expect(choice).to_have_count(1);artifact_id=choice.get_attribute('value')
   ui.page.get_by_role('combobox',name='เลือก backup เพื่อทดสอบกู้คืน',exact=True).select_option(artifact_id)
   restore=ui.response_click('operations/jobs',ui.page.get_by_role('button',name='กู้คืนลงฐานทดสอบแยก',exact=True))
   restore_detail=ui.page.locator('details').filter(has_text=restore['id'])
   expect(restore_detail).to_contain_text('restore_verified',timeout=120000)
   with ui.page.expect_response(lambda r:urlparse(r.url).path=='/api/v2/operations/jobs' and r.request.method=='GET') as jobs_response:
    ui.page.get_by_role('button',name='ตรวจล่าสุด',exact=True).click()
   jobs=jobs_response.value.json()['items'];verified=next(j for j in jobs if j['id']==restore['id'])
   assert verified['status']=='restore_verified' and verified['source_backup_id']==artifact_id
   assert verified['result']['isolated_database'].startswith('his_restore_')
   assert set(verified['result']['verified_checks'])=={'table row counts','canonical row hashes','validated foreign keys','file checksums'}
   report['operations']={'ui_created_patient_id':row['id'],'ui_document_ids':[doc_a['id'],doc_b['id']],
    'backup_job_id':backup['id'],'artifact_id':artifact_id,'restore_job_id':restore['id'],'verification':verified['result']}
   checked('UI backup then isolated restore verifies table counts, canonical row hashes, FKs and files after browser-created records')
   restore_detail.locator('summary').click();screenshot(ui.page,OUT,'isolated-restore-verified');report['status']='PASS'
  except Exception as error:
   report['status']='FAIL';report['reason']=safe_error(error);screenshot(ui.page,OUT,'recovery-failure')
  browser.close()
except Exception as error:report['reason']=safe_error(error)
finally:
 (OUT/'browser-recovery.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({'status':report['status'],'assertions':len(report['assertions']),'reason':report.get('reason')}))
if report['status']!='PASS':raise SystemExit(1)
