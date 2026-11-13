"""Actual loaded-state screenshot and subject-binding evidence, no inference/domain mutations."""
from pathlib import Path
import argparse,sys,json,hashlib
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from scripts.dev import load_env
from playwright.sync_api import sync_playwright
p=argparse.ArgumentParser();p.add_argument('--base-url',default='http://127.0.0.1:5173');args=p.parse_args()
out=ROOT/'evidence/triadic-ui/confirmation';out.mkdir(parents=True,exist_ok=True);checks=[];errors=[]
with sync_playwright() as pw:
 browser=pw.chromium.launch();page=browser.new_page(viewport={'width':1440,'height':1000},locale='th-TH');page.set_default_timeout(30000);page.on('pageerror',lambda error:errors.append(str(error)))
 def shot(name):
  page.evaluate('document.fonts.ready');page.screenshot(path=str(out/(name+'.png')),full_page=True)
  bounds=page.evaluate('({width:innerWidth,content:document.documentElement.scrollWidth})');assert bounds['content']<=bounds['width']+1
  checks.append({'screen':name,'no_horizontal_overflow':True})
 page.goto(args.base_url+'/login');page.get_by_label('ชื่อบัญชี',exact=True).wait_for();shot('desktop-login')
 page.get_by_label('ชื่อบัญชี',exact=True).fill('clinician');page.get_by_label('รหัสผ่าน',exact=True).fill(load_env()['HIS_SEED_PASSWORD']);page.get_by_role('button',name='เข้าสู่ระบบ',exact=True).click()
 page.wait_for_url('**/home');page.locator('.task-register tbody tr').first.wait_for();assert not page.locator('.skeleton-list').count();shot('desktop-home-loaded')
 checks.append({'check':'home wait','loaded_task_rows':page.locator('.task-register tbody tr').count(),'skeleton_visible':False})
 page.goto(args.base_url+'/domains/D01');page.locator('.record-list .record-button').first.wait_for();shot('desktop-patients')
 page.goto(args.base_url+'/domains/D22');page.locator('.record-list .record-button').first.wait_for();shot('desktop-documents')
 page.goto(args.base_url+'/domains/D37');page.get_by_role('combobox',name='ผู้ป่วย',exact=True).select_option('patient-001')
 page.get_by_role('combobox',name='การรับบริการ',exact=True).locator('option[value="encounter-001"]').wait_for(state='attached')
 page.get_by_role('combobox',name='การรับบริการ',exact=True).select_option('encounter-001')
 row=page.locator('.proposal-list .record-button').filter(has_text='ผู้ตรวจทดสอบตรวจทานแล้ว').first;row.wait_for();row.click()
 page.locator('.checklist').wait_for();assert page.locator('.checklist .finding').count()==5
 assert 'patient-001' in page.locator('.review-bound-subject').inner_text()
 assert 'encounter-001' in page.locator('.review-bound-subject').inner_text()
 assert page.get_by_role('button',name='อนุมัติรุ่นที่แสดง',exact=True).is_disabled()
 checks.append({'check':'recorded live proposal','global_patient':'patient-001','global_encounter':'encounter-001','five_findings':True,'historic_approval_disabled':True})
 shot('desktop-ai-reviewed')
 page.locator('.ai-run-history>summary').click();assert '11205 ms' in page.locator('.run-list').inner_text();page.locator('.ai-run-history>summary').click()
 checks.append({'check':'prior real model provenance','elapsed_ms':11205,'new_inference':False})
 page.set_viewport_size({'width':1024,'height':900});shot('tablet-ai-reviewed')
 page.set_viewport_size({'width':390,'height':844});shot('mobile-ai-reviewed')
 page.goto(args.base_url+'/home');page.locator('.task-register tbody tr').first.wait_for();shot('mobile-home-loaded')
 page.get_by_role('button',name='เปิดหรือปิดเมนู',exact=True).click()
 assert page.locator('#app-navigation').evaluate('(element)=>element.contains(document.activeElement)')
 assert page.locator('#main-content').get_attribute('inert') is not None
 shot('mobile-navigation')
 page.keyboard.press('Escape');page.wait_for_function("document.querySelector('[aria-controls=app-navigation]')===document.activeElement");assert page.get_by_role('button',name='เปิดหรือปิดเมนู',exact=True).evaluate('(el)=>el===document.activeElement')
 checks.append({'check':'mobile navigation','focus_contained':True,'main_inert':True,'escape_returns_trigger':True})
 browser.close()
assert not errors,errors
report={'observed_at':datetime.now(timezone.utc).isoformat(),'status':'PASS','method':'ActualChromiumUI on explicitcontext; waits for loaded records, zero inference/domain mutations','checks':checks,'page_errors':errors,'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'apps/web/src/App.tsx',ROOT/'apps/web/src/styles.css',ROOT/'apps/web/src/components/core-workspaces.tsx',ROOT/'apps/web/src/components/sidebar.tsx']}}
(out/'execution.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(report,ensure_ascii=False))
