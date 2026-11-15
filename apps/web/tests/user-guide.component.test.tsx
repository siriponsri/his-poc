import {test,beforeEach,afterEach} from 'node:test'
import assert from 'node:assert/strict'
import {JSDOM} from 'jsdom'
import React,{act} from 'react'
import type {Root} from 'react-dom/client'
import type {GuideChapter,GuideDomain} from '../src/data/user-guide-content'
import type {GuideMedia} from '../src/components/user-guide'

const dom=new JSDOM('<!doctype html><html><body></body></html>',{url:'http://localhost:8000/guide'})
for(const name of ['window','document','Event','CustomEvent','HTMLElement','HTMLInputElement','HTMLSelectElement','Node','location','history'])Object.defineProperty(globalThis,name,{configurable:true,value:(dom.window as any)[name]})
;(globalThis as any).IS_REACT_ACT_ENVIRONMENT=true
;(dom.window.HTMLElement.prototype as any).scrollIntoView=()=>{}
let reduced=false
const motionListeners=new Set<()=>void>()
;(dom.window as any).matchMedia=()=>({get matches(){return reduced},addEventListener(_name:string,listener:()=>void){motionListeners.add(listener)},removeEventListener(_name:string,listener:()=>void){motionListeners.delete(listener)}})
let requests:string[]=[]
globalThis.fetch=async(input)=>{requests.push(String(input));throw Error('A static guide must not call application APIs')}
const {createRoot}=await import('react-dom/client')
const {UserGuide,GuideScreenshot}=await import('../src/components/user-guide')

const chapters:GuideChapter[]=[
 {id:'preparation',title:'Visit preparation',summary:'Read evidence before saving a draft',roles:['clinician','nurse'],prerequisites:['เปิด encounter ที่ได้รับมอบหมาย'],steps:[{title:'Open the record',paragraphs:['เปิด Patient record และตรวจชื่อผู้ป่วย'],screenshot:'patient'},{title:'Review the sources',paragraphs:['ตรวจแหล่งข้อมูลและสิ่งที่ยังขาด'],screenshot:'patient',note:'อย่าบันทึกเมื่อข้อมูลต้นทางเปลี่ยน'}],completion:['อ่านเอกสารฉบับเต็มแล้ว'],troubleshooting:[{problem:'Source changed',action:'เตรียมงานใหม่จากข้อมูลล่าสุด'}],domains:['D03','D22']},
 {id:'administration',title:'Administration',summary:'Manage accounts and access',roles:['system_admin'],prerequisites:['ใช้บัญชีที่ได้รับสิทธิ์'],steps:[{title:'Find an account',paragraphs:['ค้นหาผู้ใช้จากชื่อบัญชี']},{title:'Read memberships',paragraphs:['ตรวจสิทธิ์ที่บันทึกไว้จริง']}],completion:['เลือกบัญชีถูกต้อง'],troubleshooting:[{problem:'Account version changed',action:'อ่านบัญชีที่เลือกใหม่ก่อนส่งคำสั่ง'}],domains:['D34']},
]
const domains:GuideDomain[]=Array.from({length:38},(_,index)=>({id:'D'+String(index+1).padStart(2,'0'),name:'Domain '+(index+1),purpose:index===37?'Backup and operations':'Typed work reference',roles:index===33?['system_admin']:['clinician'],steps:['เปิดรายการที่ได้รับสิทธิ์','ตรวจข้อมูลก่อนบันทึก'],completion:'อ่านผลกลับแล้ว',limits:'Synthetic local workflow only'}))
const media:Record<string,GuideMedia>={patient:{src:'/assets/guide/fictional-patient.jpg',alt:'Fictional patient record with its document list',caption:'ภาพข้อมูลสมมุติ ใช้อธิบายขั้นตอน',width:1280,height:720,tour:[{label:'เลือกเวชระเบียน',description:'เปิดข้อมูลของผู้ป่วยที่ต้องการ',rect:{x:5,y:20,width:25,height:30}},{label:'อ่านหลักฐาน',description:'ตรวจข้อความต้นฉบับก่อนบันทึก',rect:{x:40,y:20,width:50,height:60}}]}}
let root:Root
beforeEach(()=>{document.body.innerHTML='<div id="root"></div>';document.body.style.overflow='';history.replaceState({},'','/guide');reduced=false;requests=[];motionListeners.clear();root=createRoot(document.getElementById('root')!)})
afterEach(async()=>{await act(async()=>root.unmount());assert.deepEqual(requests,[],'Guide interactions must not invoke application APIs')})
async function mount(path='/guide',roles:string[]=[]){history.replaceState({},'',path);await act(async()=>root.render(<UserGuide chapters={chapters} domains={domains} media={media} roles={roles}/>));await act(async()=>window.dispatchEvent(new Event('popstate')))}
function findButton(name:string){const button=[...document.querySelectorAll<HTMLButtonElement>('button')].find(item=>(item.getAttribute('aria-label')||item.textContent||'').trim()===name);assert.ok(button,'Missing button '+name);return button}
async function click(name:string){await act(async()=>findButton(name).click())}
async function search(value:string){const input=document.getElementById('guide-search') as HTMLInputElement;await act(async()=>{Object.getOwnPropertyDescriptor(dom.window.HTMLInputElement.prototype,'value')!.set!.call(input,value);input.dispatchEvent(new dom.window.Event('input',{bubbles:true}))})}
function chapterButton(id:string){const button=document.querySelector<HTMLButtonElement>(`.guide-chapter-navigation button[aria-current="page"]`);assert.ok(button);assert.ok(button.textContent?.includes(id));return button}

test('renders chapter reading and the complete 38-domain directory without application requests',async()=>{
 await mount()
 assert.equal(document.querySelector('h1')?.textContent,'User Guide')
 assert.equal(document.querySelector('.guide-reader h2')?.textContent,'Visit preparation')
 assert.equal(document.querySelectorAll('.guide-domain-navigation li').length,38)
 assert.equal(document.querySelectorAll('.guide-steps>li').length,2)
 assert.match(document.querySelector('.guide-completion')?.textContent||'',/อ่านเอกสารฉบับเต็มแล้ว/)
})

test('search includes paragraph and recovery text rather than only headings',async()=>{
 await mount();await search('ข้อมูลล่าสุด')
 assert.equal(document.querySelectorAll('.guide-chapter-navigation>ol>li').length,1)
 assert.match(document.querySelector('.guide-chapter-navigation')?.textContent||'',/Visit preparation/)
 assert.doesNotMatch(document.querySelector('.guide-chapter-navigation')?.textContent||'',/Administration/)
 await search('D38');assert.equal(document.querySelectorAll('.guide-domain-navigation li').length,1)
 assert.match(document.querySelector('.guide-domain-navigation')?.textContent||'',/Domain 38/)
})

test('search normalizes case and requires every search word',async()=>{
 await mount();await search('VISIT source')
 assert.equal(document.querySelectorAll('.guide-chapter-navigation>ol>li').length,1)
 await search('Visit missingword');assert.match(document.querySelector('.guide-no-results')?.textContent||'',/ยังไม่พบหัวข้อ/)
 await click('ล้างตัวกรอง');assert.equal(document.querySelectorAll('.guide-chapter-navigation>ol>li').length,2)
})

test('selecting a chapter preserves a shareable query and focuses its title',async()=>{
 await mount('/guide?lang=th#old')
 const option=[...document.querySelectorAll<HTMLButtonElement>('.guide-chapter-navigation>ol button')].find(item=>item.textContent?.includes('Administration'))!
 await act(async()=>option.click())
 assert.equal(location.search,'?lang=th&chapter=administration');assert.equal(location.hash,'')
 assert.equal(document.activeElement,document.querySelector('.guide-reader h2'))
 chapterButton('Administration')
})

test('direct domain links open the last domain and can return to a full related workflow',async()=>{
 await mount('/guide?domain=D34')
 assert.equal(document.querySelector('.guide-reader h2')?.textContent,'Domain 34')
 assert.match(document.querySelector('.guide-domain-limits')?.textContent||'',/Synthetic local workflow only/)
 await click('Administration ↗');assert.equal(document.querySelector('.guide-reader h2')?.textContent,'Administration')
 assert.equal(location.search,'?chapter=administration')
 await mount('/guide?domain=D38');assert.equal(document.querySelector('.guide-reader h2')?.textContent,'Domain 38')
})

test('browser location changes select the matching guide without network work',async()=>{
 await mount();await act(async()=>{history.replaceState({},'','/guide?chapter=administration');window.dispatchEvent(new Event('popstate'))})
 assert.equal(document.querySelector('.guide-reader h2')?.textContent,'Administration')
})

test('role filtering is optional and never changes account permissions',async()=>{
 await mount('/guide',['nurse'])
 assert.equal(document.querySelectorAll('.guide-chapter-navigation>ol>li').length,2)
 const checkbox=document.querySelector<HTMLInputElement>('.guide-role-filter input')!
 await act(async()=>checkbox.click())
 assert.equal(document.querySelectorAll('.guide-chapter-navigation>ol>li').length,1)
 assert.match(document.querySelector('.guide-chapter-navigation>ol')?.textContent||'',/Visit preparation/)
 await act(async()=>checkbox.click());assert.equal(document.querySelectorAll('.guide-chapter-navigation>ol>li').length,2)
})

test('a broad audience is compact only when it covers every named core persona',async()=>{
 const all=['registration','clinician','nurse','laboratory','imaging','pharmacist','billing','finance','inventory','quality','system_admin','operations_admin','auditor','patient']
 await act(async()=>root.render(<UserGuide chapters={[{...chapters[0],roles:all}]} domains={domains} media={media}/>))
 assert.equal(document.querySelector('.guide-audience')?.textContent,'เหมาะสำหรับ ทุกบทบาท')
 const sameCountMissingPatient=[...all.filter(role=>role!=='patient'),'nurse']
 await act(async()=>root.render(<UserGuide chapters={[{...chapters[0],roles:sameCountMissingPatient}]} domains={domains} media={media}/>))
 assert.doesNotMatch(document.querySelector('.guide-audience')?.textContent||'',/ทุกบทบาท/)
 assert.match(document.querySelector('.guide-audience')?.textContent||'',/พยาบาล/)
})

test('chapter and domain audiences use human role labels while canonical filtering still works',async()=>{
 await mount('/guide',['nurse'])
 assert.match(document.querySelector('.guide-audience')?.textContent||'',/ทีมดูแลผู้ป่วย · พยาบาล/)
 assert.doesNotMatch(document.querySelector('.guide-audience')?.textContent||'',/clinician|nurse/)
 const checkbox=document.querySelector<HTMLInputElement>('.guide-role-filter input')!
 await act(async()=>checkbox.click());assert.equal(document.querySelectorAll('.guide-chapter-navigation>ol>li').length,1)
 await search('พยาบาล');assert.equal(document.querySelectorAll('.guide-chapter-navigation>ol>li').length,1)
 await search('')
 await mount('/guide?domain=D34');assert.match(document.querySelector('.guide-audience')?.textContent||'',/ผู้ดูแลระบบ/)
})

test('return-to-outline action restores search focus without changing the selected chapter or URL',async()=>{
 await mount()
 const select=document.getElementById('guide-section-select') as HTMLSelectElement
 await act(async()=>{select.value='chapter:administration';select.dispatchEvent(new dom.window.Event('change',{bubbles:true}))})
 assert.equal(document.activeElement,document.querySelector('.guide-reader h2'))
 const before=location.href,input=document.getElementById('guide-search') as HTMLInputElement
 let scrolled=0;input.scrollIntoView=()=>{scrolled++}
 await click('สารบัญและค้นหา ↑')
 assert.equal(document.activeElement,input);assert.equal(scrolled,1)
 assert.equal(location.href,before);assert.equal(document.querySelector('.guide-reader h2')?.textContent,'Administration')
})

test('repeated screenshot references reuse one accessible figure and keep the reading steps',async()=>{
 await mount()
 assert.equal(document.querySelectorAll('.guide-image-open img').length,1)
 assert.equal(document.querySelector('.guide-image-open img')?.getAttribute('alt'),media.patient.alt)
 const link=document.querySelector('.guide-figure-reference') as HTMLAnchorElement
 assert.ok(document.querySelector(link.getAttribute('href')!))
 assert.equal(document.querySelectorAll('.guide-step-heading>a').length,2)
})

test('image reading dialog traps focus, closes with Escape and restores reading focus',async()=>{
 await mount()
 const opener=document.querySelector<HTMLButtonElement>('.guide-image-open')!;opener.focus()
 await act(async()=>opener.click())
 const dialog=document.querySelector<HTMLElement>('[role=dialog]')!;assert.ok(dialog)
 const close=findButton('ปิดภาพประกอบคู่มือ'),original=findButton('ขนาดต้นฉบับ'),surface=document.querySelector<HTMLElement>('.guide-zoom-surface')!
 assert.equal(document.activeElement,close);assert.equal(document.body.style.overflow,'hidden')
 await act(async()=>close.dispatchEvent(new dom.window.KeyboardEvent('keydown',{key:'Tab',bubbles:true,cancelable:true})))
 assert.equal(document.activeElement,surface)
 await act(async()=>surface.dispatchEvent(new dom.window.KeyboardEvent('keydown',{key:'Tab',bubbles:true,cancelable:true})))
 assert.equal(document.activeElement,original)
 await act(async()=>original.dispatchEvent(new dom.window.KeyboardEvent('keydown',{key:'Tab',shiftKey:true,bubbles:true,cancelable:true})))
 assert.equal(document.activeElement,surface)
 await act(async()=>surface.dispatchEvent(new dom.window.KeyboardEvent('keydown',{key:'Tab',shiftKey:true,bubbles:true,cancelable:true})))
 assert.equal(document.activeElement,close)
 await act(async()=>surface.dispatchEvent(new dom.window.KeyboardEvent('keydown',{key:'Escape',bubbles:true,cancelable:true})))
 assert.equal(document.querySelector('[role=dialog]'),null);assert.equal(document.activeElement,opener);assert.equal(document.body.style.overflow,'')
})

test('original-size screenshot view is scoped to its own scroll surface',async()=>{
 await mount();await act(async()=>document.querySelector<HTMLButtonElement>('.guide-image-open')!.click());await click('ขนาดต้นฉบับ')
 assert.ok(document.querySelector('.guide-zoom-surface.original-size'))
 assert.equal((document.querySelector('.guide-zoom-surface img') as HTMLImageElement).style.width,'1280px')
 await click('พอดีหน้าจอ');assert.equal(document.querySelector('.guide-zoom-surface.original-size'),null)
})

test('original-size image can be reached and read through the keyboard scroll region',async()=>{
 await mount();await act(async()=>document.querySelector<HTMLButtonElement>('.guide-image-open')!.click());await click('ขนาดต้นฉบับ')
 const close=findButton('ปิดภาพประกอบคู่มือ'),surface=document.querySelector<HTMLElement>('.guide-zoom-surface')!
 close.focus();await act(async()=>close.dispatchEvent(new dom.window.KeyboardEvent('keydown',{key:'Tab',bubbles:true,cancelable:true})))
 assert.equal(document.activeElement,surface);assert.equal(surface.getAttribute('role'),'region')
 assert.match(surface.getAttribute('aria-label')||'',/ปุ่มลูกศร.*เลื่อน/)
 const arrow=new dom.window.KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true,cancelable:true})
 await act(async()=>surface.dispatchEvent(arrow))
 assert.equal(arrow.defaultPrevented,false,'Native arrow scrolling remains available inside the focused image region')
 assert.equal(document.activeElement,surface)
 await act(async()=>surface.dispatchEvent(new dom.window.KeyboardEvent('keydown',{key:'Tab',shiftKey:true,bubbles:true,cancelable:true})))
 assert.equal(document.activeElement,close)
})

test('walkthrough starts paused and manual next/previous retain a full text equivalent',async()=>{
 await act(async()=>root.render(<GuideScreenshot media={media.patient} stepDurationMs={20}/>))
 assert.equal(findButton('เล่นภาพเคลื่อนไหว').getAttribute('aria-pressed'),'false')
 await act(async()=>{await new Promise(resolve=>setTimeout(resolve,45))})
 assert.match(document.querySelector('.guide-tour-caption')?.textContent||'',/เลือกเวชระเบียน/)
 await click('ขั้นตอนถัดไป');assert.match(document.querySelector('.guide-tour-caption')?.textContent||'',/อ่านหลักฐาน/)
 assert.equal(findButton('ขั้นตอนถัดไป').disabled,true)
 await click('ขั้นตอนก่อนหน้า');assert.match(document.querySelector('.guide-tour-caption')?.textContent||'',/เลือกเวชระเบียน/)
 assert.equal(document.querySelectorAll('.guide-tour-transcript li').length,2)
})

test('explicit animation advances, and pausing prevents further automatic movement',async()=>{
 await act(async()=>root.render(<GuideScreenshot media={media.patient} stepDurationMs={20}/>));await click('เล่นภาพเคลื่อนไหว')
 assert.equal(findButton('หยุดภาพเคลื่อนไหว').getAttribute('aria-pressed'),'true')
 await act(async()=>{await new Promise(resolve=>setTimeout(resolve,35))})
 assert.match(document.querySelector('.guide-tour-caption')?.textContent||'',/อ่านหลักฐาน/)
 await click('หยุดภาพเคลื่อนไหว');await act(async()=>{await new Promise(resolve=>setTimeout(resolve,45))})
 assert.match(document.querySelector('.guide-tour-caption')?.textContent||'',/อ่านหลักฐาน/)
 assert.equal(findButton('เล่นภาพเคลื่อนไหว').getAttribute('aria-pressed'),'false')
})

test('reduced-motion users retain manual steps and cannot start animation',async()=>{
 reduced=true;await act(async()=>root.render(<GuideScreenshot media={media.patient}/>))
 assert.equal(findButton('เล่นภาพเคลื่อนไหว').disabled,true)
 assert.match(document.querySelector('.guide-motion-note')?.textContent||'',/ลดการเคลื่อนไหว/)
 await click('ขั้นตอนถัดไป');assert.match(document.querySelector('.guide-tour-caption')?.textContent||'',/อ่านหลักฐาน/)
})

test('changing motion preference pauses an already playing explanation',async()=>{
 await act(async()=>root.render(<GuideScreenshot media={media.patient}/>));await click('เล่นภาพเคลื่อนไหว')
 await act(async()=>{reduced=true;for(const listener of motionListeners)listener()})
 assert.equal(findButton('เล่นภาพเคลื่อนไหว').disabled,true)
 assert.equal(findButton('เล่นภาพเคลื่อนไหว').getAttribute('aria-pressed'),'false')
})

test('mobile section chooser and chapter next controls select the same content',async()=>{
 await mount()
 const select=document.getElementById('guide-section-select') as HTMLSelectElement
 await act(async()=>{select.value='domain:D38';select.dispatchEvent(new dom.window.Event('change',{bubbles:true}))})
 assert.equal(document.querySelector('.guide-reader h2')?.textContent,'Domain 38')
 await mount('/guide?chapter=preparation');await click('Next chapter →Administration')
 assert.equal(document.querySelector('.guide-reader h2')?.textContent,'Administration')
})

test('empty and unknown guide inputs fail to readable local content, not an app command',async()=>{
 await mount('/guide?chapter=unknown');assert.equal(document.querySelector('.guide-reader h2')?.textContent,'Visit preparation')
 await act(async()=>root.render(<UserGuide chapters={[]} domains={[]} media={{}}/>))
 assert.match(document.querySelector('.guide-reader')?.textContent||'',/คู่มือกำลังจัดเตรียม/)
})
