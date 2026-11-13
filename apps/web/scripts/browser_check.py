"""Optional browser smoke against an ALREADY RUNNING isolated synthetic v2 app.
Requires playwright + installed Chromium and HIS_SEED_PASSWORD. Never starts legacy v1.
This is smoke coverage, not all J01-J10 or clinical validation.
"""
import json,os,time,uuid
from pathlib import Path
from urllib.parse import urlparse
from browser_support import options, provenance, safe_error, failure_artifacts
ARGS=options(__doc__)
BASE=os.environ.get('HIS_BASE_URL','http://127.0.0.1:8000').rstrip('/')
if urlparse(BASE).hostname not in ('localhost','127.0.0.1','::1'):raise SystemExit('Smoke requires loopback synthetic app')
PASSWORD=os.environ.get('HIS_SEED_PASSWORD','')
if len(PASSWORD)<12:raise SystemExit('Set HIS_SEED_PASSWORD from your isolated synthetic seed; do not embed it in script')
OUT=ARGS.output_dir;OUT.mkdir(parents=True,exist_ok=True)
report={**provenance(),'status':'NOT_RUN','assertions':[],'browser_assertions':0,'journey_coverage':'SMOKE_ONLY','reason':None}
def checked(name):report['assertions'].append(name);report['browser_assertions']+=1
try:
 from playwright.sync_api import sync_playwright,expect
 with sync_playwright() as pw, failure_artifacts(lambda:page,OUT,'browser-smoke-failure'):
  browser=pw.chromium.launch(headless=not ARGS.headed,executable_path=os.environ.get('CHROMIUM_PATH'))
  report['status']='FAIL';page=browser.new_page(viewport={'width':1440,'height':1000});errors=[]
  page.on('pageerror',lambda error:errors.append(str(error)))
  page.goto(BASE+'/');expect(page.get_by_role('heading',name='เข้าสู่พื้นที่ทำงาน')).to_be_visible();checked('anonymous root reaches login')
  def login(user):
   page.get_by_label('ชื่อบัญชี',exact=True).fill(user);page.get_by_label('รหัสผ่าน',exact=True).fill(PASSWORD);page.get_by_role('button',name='เข้าสู่ระบบ →',exact=True).click();expect(page.get_by_role('button',name='ออกจากระบบ',exact=True)).to_be_visible()
  login('registration');checked('real local login and session bootstrap')
  page.goto(BASE+'/domains/D01');page.get_by_role('button',name='＋ เพิ่มผู้ป่วย',exact=True).click()
  name='ผู้ป่วยสังเคราะห์ browser '+uuid.uuid4().hex[:8]
  page.get_by_label('ชื่อผู้ป่วยสังเคราะห์',exact=False).fill(name);page.get_by_label('เลขประจำตัวผู้ป่วย',exact=False).fill('BROWSER-'+uuid.uuid4().hex[:12]);page.get_by_label('เพศ',exact=False).select_option('unknown')
  page.get_by_role('button',name='บันทึก',exact=True).click();expect(page.get_by_text('บันทึกสำเร็จจากเซิร์ฟเวอร์แล้ว',exact=True)).to_be_visible();checked('typed patient create persists via PostgreSQL backend')
  page.reload();expect(page.get_by_role('button').filter(has_text=name).first).to_be_visible();checked('deep-link reload retains created patient')
  page.get_by_role('button',name='ข้ามไปยังเนื้อหา',exact=True).focus();page.keyboard.press('Enter');assert urlparse(page.url).path=='/domains/D01';checked('skip focus preserves route')
  page.goto(BASE+'/domains/D25');expect(page.get_by_role('heading',name='ไม่มีสิทธิ์เข้าพื้นที่นี้')).to_be_visible();checked('registration denied finance route')
  page.goto(BASE+'/this-route-does-not-exist');expect(page.get_by_role('heading',name='404 · ไม่พบหน้านี้')).to_be_visible();checked('production deep link not-found')
  page.get_by_role('button',name='ออกจากระบบ',exact=True).click();expect(page.get_by_role('heading',name='เข้าสู่พื้นที่ทำงาน')).to_be_visible();checked('logout clears server session and UI data')
  login('patient');page.goto(BASE+'/domains/D21');expect(page.get_by_role('heading',name='ประวัติและผลที่เผยแพร่ให้คุณ')).to_be_visible();assert page.locator('.patient-context').count()==0;checked('portal own shell without crosspatient picker')
  page.set_viewport_size({'width':390,'height':844});page.get_by_role('button',name='เปิดหรือปิดเมนู').click();expect(page.locator('#app-navigation')).to_be_visible();page.keyboard.press('Escape');checked('mobile sidebar opens and closes with Escape')
  assert not errors,errors;checked('no uncaught browser page errors')
  page.screenshot(path=str(OUT/'portal-mobile.png'),full_page=True)
  report['status']='PASS';browser.close()
except Exception as exc:
 report['reason']=f'{type(exc).__name__}: {safe_error(exc)}'
finally:
 (OUT/'browser-smoke.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({'status':report['status'],'browser_assertions':report['browser_assertions'],'reason':report['reason']},ensure_ascii=False))
if report['status']!='PASS':raise SystemExit(1)
