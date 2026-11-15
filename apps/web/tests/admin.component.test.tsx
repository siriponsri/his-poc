import {test,beforeEach,afterEach} from 'node:test'
import assert from 'node:assert/strict'
import {JSDOM} from 'jsdom'
import React,{act} from 'react'
import type {Root} from 'react-dom/client'

const dom=new JSDOM('<!doctype html><html><body></body></html>',{url:'http://localhost:8000/admin'})
for(const name of ['window','document','Event','CustomEvent','HTMLElement','HTMLInputElement','HTMLTextAreaElement','Node','location','history'])Object.defineProperty(globalThis,name,{configurable:true,value:(dom.window as any)[name]})
;(globalThis as any).IS_REACT_ACT_ENVIRONMENT=true
;(dom.window as any).scrollTo=()=>{}
;(dom.window as any).matchMedia=()=>({matches:false,addEventListener(){},removeEventListener(){}})
const {createRoot}=await import('react-dom/client')
const baseUser={id:'admin-test',username:'admin-demo',display_name:'Demo administrator',organization_id:'org-test',facility_id:'facility-test',roles:['system_admin'],permissions:['D34.read','D34.write','identity.admin','patient.reference','encounter.reference'],patient_scope:null}
const initialSession={user:baseUser,csrf_token:'synthetic-csrf-only',expires_at:'2099-01-01T00:00:00Z'}
const account=(id='other-test',version=1)=>({id,version,username:id,display_name:'Fictional account '+id,status:'active',memberships:[{id:'m-'+id,role:id==='admin-test'?'system_admin':'nurse',facility_id:'facility-test',active:true}]})
const overview={scope:{organization_id:'org-test',facility_id:'facility-test'},users:{total:2,active:2,suspended:0,disabled:0},sessions:{active:1,revoked:0,expired:0},security:{recent_denial_count:3,window_hours:24},database:{reachable:true,migration:'0005_assistant_workspaces'},assistant:{configured:true,route:'dr_train_gpu0_v1',engine_version:'0.12.6',profiles_qualified:['visit_preparation','nursing_handover','records_readiness','laboratory_handoff'],counts:{queued:1,running:1,succeeded:6,failed:0,awaiting_review:1,active_watches:0},live_status:'not_checked'},observed_at:'2026-11-15T00:00:00Z'}
type Request={path:string;init:RequestInit|undefined}
let requests:Request[]=[],handler:((path:string,init?:RequestInit)=>unknown|Promise<unknown>)|null=null,session=structuredClone(initialSession),root:Root
globalThis.fetch=async(url,init)=>{
 const path=String(url).replace('/api/v2/','');requests.push({path,init})
 const custom=await handler?.(path,init);if(custom instanceof Response)return custom
 const parsed=new URL(path,'http://test/');let value=custom
 if(value===undefined){
  if(path==='auth/me')value=session
  else if(path==='admin/overview')value=overview
  else if(parsed.pathname==='/admin/users')value={items:[account('admin-test'),account()],total:2,limit:100,offset:0}
  else if(path==='admin/roles')value={items:[{role:'system_admin',permissions:['D34.read','D34.write','identity.admin']},{role:'nurse',permissions:['D06.read']},{role:'clinician',permissions:['D03.read']}]}
  else if(path==='facilities')value={items:[{id:'facility-test',name:'Demonstration hospital'}]}
  else if(path==='admin/sessions')value={items:[{id:'session-test',user_id:'other-test',user:{id:'other-test',username:'other-test',display_name:'Stable session owner'},created_at:'2026-11-15T00:00:00Z',expires_at:'2099-01-01T00:00:00Z',revoked_at:null,token_hash:'NEVER_RENDER_TOKEN',csrf_token:'NEVER_RENDER_CSRF'}]}
  else if(path==='admin/security-events')value={items:[{id:'security-test',event:'permission_denied',actor_id:'other-test',created_at:'2026-11-15T00:00:00Z'}]}
  else if(path==='assistant/config')value={provider:{enabled:false,configured:true,qualified:false,profiles_qualified:[]},profiles:[]}
  else if(path.startsWith('assistant/worklist'))value={items:[],eligible_contexts:[],watches:[],counts:{}}
  else if(path==='home')value={items:[],open_tasks:0,domain_counts:[]}
  else throw Error('Unexpected request '+path)
 }
 return new Response(JSON.stringify(value))
}
const {default:App}=await import('../src/App')
beforeEach(()=>{document.body.innerHTML='<div id="root"></div>';history.replaceState({},'','/admin');requests=[];handler=null;session=structuredClone(initialSession);root=createRoot(document.getElementById('root')!)})
afterEach(async()=>{await act(async()=>root.unmount())})
async function flush(ms=15){await act(async()=>{await new Promise(resolve=>setTimeout(resolve,ms))})}
async function mount(path='/admin'){history.replaceState({},'',path);await act(async()=>root.render(<App/>));await flush()}
function button(label:RegExp){const found=[...document.querySelectorAll<HTMLButtonElement>('button')].find(node=>label.test(node.getAttribute('aria-label')||node.textContent||''));assert.ok(found,'Missing button '+label);return found}
async function click(label:RegExp){await act(async()=>button(label).click());await flush()}
async function fill(label:string,value:string){const input=document.querySelector<HTMLInputElement>(`input[aria-label="${label}"]`)||[...document.querySelectorAll('label')].find(node=>node.querySelector('span')?.textContent===label)?.querySelector('input');assert.ok(input,'Missing input '+label);await act(async()=>{Object.getOwnPropertyDescriptor(dom.window.HTMLInputElement.prototype,'value')!.set!.call(input,value);input.dispatchEvent(new dom.window.Event('input',{bubbles:true}))})}
async function submit(){const form=document.querySelector('.admin-dialog form');assert.ok(form);await act(async()=>form.dispatchEvent(new dom.window.Event('submit',{bubbles:true,cancelable:true})));await flush()}
const posts=()=>requests.filter(item=>item.init?.method==='POST')

test('administrator ordinary home opens the dedicated console without clinical data or inference requests',async()=>{
 await mount('/home');assert.equal(location.pathname,'/admin');assert.equal(document.querySelector('#admin-title')?.textContent,'Administration')
 assert.equal(requests.some(item=>/^patients|^reference\/|^documents|^assistant\//.test(item.path)),false)
 assert.equal(posts().length,0);assert.match(document.body.textContent!,/live model status not checked|ยังไม่ได้ตรวจสถานะโมเดลสด/)
 assert.match(document.body.textContent!,/Demonstration hospital/)
})
test('identity administration requires both D34 and identity permission before any admin query',async()=>{
 session={...initialSession,user:{...baseUser,roles:['auditor'],permissions:['D34.read']}}
 await mount();assert.match(document.body.textContent!,/ไม่มีสิทธิ์จัดการผู้ใช้|cannot manage users/);assert.equal(requests.some(item=>item.path.startsWith('admin/')),false)
})
test('nonadministrator explicit clinical destination is preserved',async()=>{
 session={...initialSession,user:{...baseUser,roles:['clinician'],permissions:['D37.read']}}
 await mount('/admin');assert.equal(location.pathname,'/admin');assert.equal(requests.some(item=>item.path.startsWith('admin/')),false)
})
test('server-side search finds accounts outside the first page and stale responses cannot replace newer results',async()=>{
 let release:((value:unknown)=>void)|undefined
 handler=path=>{const url=new URL(path,'http://test/');if(url.pathname==='/admin/users'&&url.searchParams.get('q')==='first')return new Promise(resolve=>{release=resolve});if(url.pathname==='/admin/users'&&url.searchParams.get('q')==='second')return {items:[account('second-result')],total:1,offset:0,limit:100}}
 await mount();await fill('ค้นหาผู้ใช้','first');await flush(220);assert.ok(release)
 await fill('ค้นหาผู้ใช้','second');await flush(220);assert.match(document.querySelector('.admin-table')!.textContent!,/second-result/)
 await act(async()=>release!({items:[account('first-obsolete')],total:1,offset:0,limit:100}));assert.doesNotMatch(document.querySelector('.admin-table')!.textContent!,/first-obsolete/)
})
test('next page uses a server offset rather than filtering only loaded accounts',async()=>{
 handler=path=>{const url=new URL(path,'http://test/');if(url.pathname==='/admin/users'){const offset=Number(url.searchParams.get('offset')||0);return {items:Array.from({length:offset?1:100},(_,index)=>account(offset?'last-account':'user-'+index)),total:101,offset,limit:100}}}
 await mount();await click(/ถัดไป|^Next$/);assert.ok(requests.some(item=>item.path.includes('offset=100')));assert.match(document.querySelector('.admin-table')!.textContent!,/last-account/)
})
test('session directory never renders token or CSRF fields and viewing roles never grants them',async()=>{
 await mount();await click(/^Sessions/);assert.doesNotMatch(document.body.textContent!,/NEVER_RENDER_TOKEN|NEVER_RENDER_CSRF/)
 await click(/^Roles & access/);assert.match(document.body.textContent!,/Persisted|สิทธิ์ที่บันทึกอยู่จริง/);assert.equal(posts().length,0)
})
test('uncertain mutation preserves the identical body and key and prevents dismissal',async()=>{
 let attempts=0
 handler=(path,init)=>{if(path==='admin/users'&&init?.method==='POST'){attempts++;if(attempts===1)throw Error('Synthetic transport failure');return account('created-account')}}
 await mount();await click(/เพิ่มผู้ใช้|^Add user$/);await fill('Full name','Fictional created account');await fill('Username','created-account');await fill('Initial password','Synthetic-test-password');await submit()
 assert.equal(posts().length,1);assert.equal(button(/Close administration dialog/).disabled,true)
 await click(/ตรวจด้วยคำสั่งเดิม|Retry original request/);assert.equal(posts().length,2);assert.equal(posts()[0].init?.body,posts()[1].init?.body);assert.deepEqual(posts()[0].init?.headers,posts()[1].init?.headers);assert.equal(document.querySelector('[role=dialog]'),null)
})
test('optimistic conflict keeps the original account version until explicit reload',async()=>{
 let updated=false
 handler=(path,init)=>{if(path==='admin/users/other-test/transition'){const body=JSON.parse(String(init?.body));if(!updated){updated=true;assert.equal(body.version,1);return new Response(JSON.stringify({detail:{code:'VERSION_CONFLICT'}}),{status:409})}assert.equal(body.version,2);return {...account('other-test',3),status:'suspended'}}if(path==='admin/users/other-test'&&updated)return account('other-test',2);if(path.startsWith('admin/users?')&&updated)return {items:[account('other-test',2)],total:1}}
 await mount();await click(/^Manage other-test$/);await click(/^Suspend account$/);await submit();assert.ok(document.querySelector('[role=dialog]'));assert.equal(posts().length,1)
 await click(/อ่านบัญชีรุ่นล่าสุด|Read latest account/);await click(/^Suspend account$/);await submit();assert.equal(posts().length,2);assert.equal(document.querySelector('[role=dialog]'),null)
})
test('self account does not expose a suspend action or enable deactivation of its current administrator membership',async()=>{
 await mount();await click(/^Manage admin-test$/);assert.equal([...document.querySelectorAll('button')].some(item=>item.textContent==='Suspend account'),false);await click(/^Manage access$/)
 const checkbox=document.querySelector<HTMLInputElement>('.admin-dialog input[type=checkbox]');assert.ok(checkbox);assert.equal(checkbox.checked,true);assert.equal(checkbox.disabled,true)
})
test('overview failure leaves users usable and does not fabricate healthy counters',async()=>{
 handler=path=>path==='admin/overview'?new Response(JSON.stringify({detail:{code:'SYNTHETIC_UNAVAILABLE'}}),{status:503}):undefined
 await mount();assert.match(document.body.textContent!,/SYNTHETIC_UNAVAILABLE/);assert.ok(button(/^Manage other-test$/));assert.equal(document.querySelector('.admin-stat-strip'),null)
})
test('role tabs support keyboard movement and modal escape restores triggering focus',async()=>{
 await mount();const tab=document.querySelector<HTMLButtonElement>('[data-admin-tab=users]')!;tab.focus();await act(async()=>tab.dispatchEvent(new dom.window.KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true})));assert.equal(document.activeElement?.getAttribute('data-admin-tab'),'roles')
 await click(/^Users/);const trigger=button(/^Manage other-test$/);trigger.focus();await click(/^Manage other-test$/);await act(async()=>document.dispatchEvent(new dom.window.KeyboardEvent('keydown',{key:'Escape',bubbles:true})));assert.equal(document.querySelector('[role=dialog]'),null);assert.equal(document.activeElement,trigger)
})
test('security activity uses actual event names rather than a generic fabricated label',async()=>{
 await mount();await click(/^Security activity/);assert.match(document.querySelector('.admin-table')!.textContent!,/permission denied/)
})
test('session owner and revoke confirmation remain identifiable after a user search hides that account',async()=>{
 handler=path=>path.startsWith('admin/users?')&&path.includes('q=not-found')?{items:[],total:0}:undefined
 await mount();await fill('ค้นหาผู้ใช้','not-found');await flush(220);await click(/^Sessions/);assert.match(document.querySelector('.admin-table')!.textContent!,/Stable session owner · other-test/)
 await click(/^Revoke session session-test$/);assert.match(document.querySelector('[role=dialog]')!.textContent!,/Stable session owner · other-test/)
})
test('disable account remains a reviewed existing transition with its original version',async()=>{
 handler=(path,init)=>{if(path==='admin/users/other-test/transition'){assert.deepEqual(JSON.parse(String(init?.body)),{version:1,target:'disabled'});return {...account(),status:'disabled',version:2}}}
 await mount();await click(/^Manage other-test$/);await click(/^Disable account$/);assert.match(document.querySelector('[role=dialog]')!.textContent!,/disabled/);await submit();assert.equal(posts().length,1)
})
test('successful overview response cannot erase a failed independent user query',async()=>{
 let finish:((value:unknown)=>void)|undefined
 handler=path=>{if(path==='admin/overview')return new Promise(resolve=>{finish=resolve});if(path.startsWith('admin/users?'))return new Response(JSON.stringify({detail:{code:'USER_DIRECTORY_UNAVAILABLE'}}),{status:503})}
 await mount();assert.ok(finish);assert.match(document.body.textContent!,/USER_DIRECTORY_UNAVAILABLE/);await act(async()=>finish!(overview));assert.match(document.body.textContent!,/USER_DIRECTORY_UNAVAILABLE/)
})
