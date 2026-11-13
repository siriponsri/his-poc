"""Readonly browser acceptance for the visual refresh; no inference or domain writes."""
import argparse,json,sys,hashlib
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.dev import load_env
from playwright.sync_api import sync_playwright
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--base-url',default='http://127.0.0.1:8000');p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args()
 env=load_env();out=a.output_dir;out.mkdir(parents=True,exist_ok=True);errors=[];checks=[]
 with sync_playwright() as pw:
  browser=pw.chromium.launch();page=browser.new_page(viewport={'width':1440,'height':1000},locale='th-TH');page.set_default_timeout(20000)
  page.on('pageerror',lambda e:errors.append(str(e)))
  def capture(name):
   page.evaluate('document.fonts.ready');page.screenshot(path=str(out/(name+'.png')),full_page=True)
   size=page.evaluate('({width:innerWidth,content:document.documentElement.scrollWidth})')
   checks.append({'screen':name,'no_horizontal_overflow':size['content']<=size['width']+1,**size})
  page.goto(a.base_url+'/login');page.get_by_label('ชื่อบัญชี',exact=True).wait_for();capture('desktop-login')
  page.get_by_label('ชื่อบัญชี',exact=True).fill('clinician');page.get_by_label('รหัสผ่าน',exact=True).fill(env['HIS_SEED_PASSWORD']);page.get_by_role('button',name='เข้าสู่ระบบ',exact=True).click()
  page.wait_for_url('**/home');page.get_by_role('heading',name='ภาพรวมงาน',exact=True).wait_for();page.get_by_text('งานที่เกี่ยวข้อง',exact=True).wait_for();page.wait_for_timeout(500);capture('desktop-home')
  page.goto(a.base_url+'/domains/D01');page.get_by_role('heading',level=1).wait_for();page.wait_for_timeout(500);capture('desktop-patients')
  page.goto(a.base_url+'/domains/D22');page.get_by_role('heading',level=1).wait_for();page.wait_for_timeout(500);capture('desktop-documents')
  page.goto(a.base_url+'/domains/D37');page.get_by_text('AI จริง · dr-train',exact=True).wait_for();page.wait_for_timeout(500);capture('desktop-ai')
  # Select a visible historical live proposal without submitting another inference.
  proposal=page.locator('.proposal-list .record-button').filter(has_text='ผู้ตรวจทดสอบตรวจทานแล้ว').first
  assert proposal.count(), 'Expected prior synthetic live proposal is unavailable'
  proposal.click();page.locator('.checklist').wait_for()
  assert page.locator('.checklist .finding').count()==5
  checks.append({'screen':'persisted-human-review','five_findings':True,'approval_disabled':page.get_by_role('button',name='อนุมัติรุ่นที่แสดง',exact=True).is_disabled()})
  capture('desktop-ai-reviewed')
  page.locator('.ai-run-history>summary').click()
  assert '11205 ms' in page.locator('.run-list').inner_text()
  checks.append({'screen':'persisted-real-ai-provenance','elapsed_ms':11205,'inference_requested':False})
  page.set_viewport_size({'width':390,'height':844});page.goto(a.base_url+'/home');page.get_by_role('heading',name='ภาพรวมงาน',exact=True).wait_for();page.wait_for_timeout(400);capture('mobile-home')
  page.get_by_role('button',name='เปิดหรือปิดเมนู',exact=True).click();capture('mobile-navigation');page.keyboard.press('Escape')
  checks.append({'screen':'mobile-menu-escape','closed':page.locator('#app-navigation').get_attribute('inert') is not None})
  page.goto(a.base_url+'/domains/D37');page.get_by_text('AI จริง · dr-train',exact=True).wait_for();capture('mobile-ai')
  page.get_by_role('button',name='ออกจากระบบ',exact=True).click();page.wait_for_url('**/login');capture('mobile-login')
  browser.close()
 report={'observed_at':datetime.now(timezone.utc).isoformat(),'status':'PASS' if not errors and all(c.get('no_horizontal_overflow',c.get('closed',c.get('approval_disabled',True))) for c in checks) else 'FAIL','method':'Actual Chromium UI login, readonly navigation and persisted live-AI readback; zero inference/domain mutations','checks':checks,'page_errors':errors}
 (out/'execution.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(report,ensure_ascii=False));return report['status']!='PASS'
if __name__=='__main__':raise SystemExit(main())
