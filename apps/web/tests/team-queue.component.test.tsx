import {test,beforeEach,afterEach} from 'node:test'
import assert from 'node:assert/strict'
import {JSDOM} from 'jsdom'
import React,{act} from 'react'
import type {Root} from 'react-dom/client'
import {Client,type Session} from '../src/lib/client'
import type {TeamTask} from '../src/lib/team-operations'

const dom=new JSDOM('<!doctype html><html><body></body></html>',{url:'http://localhost/team-queue'})
for(const name of ['window','document','Event','CustomEvent','HTMLElement','HTMLInputElement','HTMLSelectElement','HTMLTextAreaElement','Node','location','history'])Object.defineProperty(globalThis,name,{configurable:true,value:(dom.window as any)[name]})
;(globalThis as any).IS_REACT_ACT_ENVIRONMENT=true
const {createRoot}=await import('react-dom/client')
const {TeamQueue}=await import('../src/components/team-queue')
const session:Session={user:{id:'actor-a',username:'fictional',display_name:'Authored actor',organization_id:'org-a',facility_id:'facility-a',roles:['clinician'],permissions:['D03.read','D03.write'],patient_scope:null},csrf_token:'test-only',expires_at:'2099-01-01'}
const colleague={id:'actor-b',display_name:'Authored colleague',username:'colleague'}
function task(overrides:Partial<TeamTask>={}):TeamTask{return {id:'task-a',version:4,domain:'D03',kind:'visit_followup',title:'Authored follow-up',status:'open',patient_id:'patient-a',encounter_id:'visit-a',patient_label:'Fictional patient',assignee:null,due_at:null,priority:'normal',escalation_level:0,escalation_reason:null,escalated_at:null,overdue:false,capabilities:{claim:true,release:false,assign:true,schedule:true,escalate:false},...overrides}}
let root:Root,requests:{path:string;init?:RequestInit}[],handler:((path:string,init?:RequestInit)=>unknown|Promise<unknown>)|null,record:TeamTask,navigated:string[],opened:unknown[]
const page=(items=[record],overrides={})=>({items,total:items.length,limit:25,offset:0,scope:'authorized_work',observed_at:'2026-11-15T00:00:00Z',counts:{active:41,mine:12,unassigned:9,overdue:3,escalated:1},counts_scope:'authorized_active_work',...overrides})
function makeClient(){return new Client(async(url,init)=>{const path=String(url).replace('/api/v2/','');requests.push({path,init});const custom=await handler?.(path,init);if(custom instanceof Response)return custom;if(custom!==undefined)return new Response(JSON.stringify(custom));if(path.startsWith('team-queue?'))return new Response(JSON.stringify(page()));if(path==='team-queue/tasks/task-a/assignees')return new Response(JSON.stringify({items:[colleague]}));if(path==='team-queue/tasks/task-a')return new Response(JSON.stringify(record));throw Error('Unexpected request '+path)})}
beforeEach(()=>{document.body.innerHTML='<div id="root"></div>';history.replaceState({},'','/team-queue');root=createRoot(document.getElementById('root')!);requests=[];handler=null;record=task();navigated=[];opened=[]})
afterEach(async()=>{await act(async()=>root.unmount())})
async function flush(ms=15){await act(async()=>{await new Promise(resolve=>setTimeout(resolve,ms))})}
async function mount(path='/team-queue'){history.replaceState({},'',path);await act(async()=>root.render(<TeamQueue client={makeClient()} session={session} navigate={value=>navigated.push(value)} onOpenPatient={value=>opened.push(value)}/>));await flush()}
function button(label:RegExp){const found=[...document.querySelectorAll<HTMLButtonElement>('button')].find(item=>label.test(item.getAttribute('aria-label')||item.textContent||''));assert.ok(found,'Missing button '+label);return found}
async function click(label:RegExp){await act(async()=>button(label).click());await flush()}
async function value(label:string,next:string){const input=document.querySelector<HTMLInputElement|HTMLSelectElement|HTMLTextAreaElement>(`[aria-label="${label}"]`);assert.ok(input,'Missing input '+label);const type=input.tagName==='SELECT'?'HTMLSelectElement':input.tagName==='TEXTAREA'?'HTMLTextAreaElement':'HTMLInputElement';await act(async()=>{Object.getOwnPropertyDescriptor((dom.window as any)[type].prototype,'value')!.set!.call(input,next);input.dispatchEvent(new dom.window.Event(type==='HTMLSelectElement'?'change':'input',{bubbles:true}))});await flush()}
async function submit(){const form=document.querySelector('.team-dialog form');assert.ok(form);await act(async()=>form.dispatchEvent(new dom.window.Event('submit',{bubbles:true,cancelable:true})));await flush()}
const posts=()=>requests.filter(item=>item.init?.method==='POST')

test('queue reads server counts and exact deep-linked task without starting inference or a write',async()=>{
 await mount('/team-queue?task_id=task-a');assert.match(document.querySelector('.team-counts')!.textContent!,/41/);assert.match(document.querySelector('.team-task-detail')!.textContent!,/Authored follow-up/);assert.equal(requests.filter(item=>item.path==='team-queue/tasks/task-a').length,1);assert.equal(posts().length,0);assert.equal(requests.some(item=>item.path.startsWith('assistant/')),false);await click(/Open patient record/);assert.deepEqual(opened,[{patient_id:'patient-a',encounter_id:'visit-a',task_id:'task-a'}]);await click(/สถานะงานและประวัติ/);assert.match(navigated[0],/^\/worklist\?record=task-a/)
})
test('deep-linked task waits for the delayed queue page before scrolling and focusing its final heading',async()=>{
 let releasePage!:(value:unknown)=>void
 handler=path=>path.startsWith('team-queue?')?new Promise(resolve=>{releasePage=resolve}):undefined
 record=task({version:7,title:'B1 authored deep-linked task'})
 const prototype=dom.window.HTMLElement.prototype,previous=prototype.scrollIntoView
 const scrolls:{heading:HTMLElement;rowCount:number;options:unknown}[]=[]
 prototype.scrollIntoView=function(options){if(this.matches('.team-task-detail h2'))scrolls.push({heading:this,rowCount:document.querySelectorAll('.team-task-table tbody tr').length,options})}
 try{
  await mount('/team-queue?task_id=task-a')
  const heading=document.querySelector<HTMLElement>('.team-task-detail h2')!
  assert.equal(heading.textContent,'B1 authored deep-linked task')
  assert.equal(document.querySelectorAll('.team-task-table tbody tr').length,0)
  assert.equal(scrolls.length,0,'Do not scroll while the queue still has no final rows')
  assert.notEqual(document.activeElement,heading,'Do not focus the detail before the pending page can move it')
  const items=[record,...Array.from({length:22},(_,index)=>task({id:'page-task-'+index,title:'Other authored task '+index}))]
  await act(async()=>releasePage(page(items)));await flush()
  assert.equal(document.querySelectorAll('.team-task-table tbody tr').length,23)
  assert.equal(scrolls.length,1)
  assert.equal(scrolls[0].heading,heading)
  assert.equal(scrolls[0].rowCount,23,'Scroll after the page rows have entered the DOM')
  assert.deepEqual(scrolls[0].options,{block:'start',behavior:'auto'})
  assert.equal(document.activeElement,heading)
  assert.match(document.querySelector('.team-task-detail header')!.textContent!,/v7/)
  assert.equal(posts().length,0)
 }finally{if(previous)prototype.scrollIntoView=previous;else Reflect.deleteProperty(prototype,'scrollIntoView')}
})
test('delayed queue completion keeps focus inside an open handoff dialog and Escape restores its trigger',async()=>{
 let releasePage!:(value:unknown)=>void
 handler=path=>path.startsWith('team-queue?')?new Promise(resolve=>{releasePage=resolve}):undefined
 const prototype=dom.window.HTMLElement.prototype,previous=prototype.scrollIntoView
 const scrolls:HTMLElement[]=[]
 prototype.scrollIntoView=function(){if(this.matches('.team-task-detail h2'))scrolls.push(this)}
 try{
  await mount('/team-queue?task_id=task-a')
  const trigger=button(/^ส่งต่องาน$/);trigger.focus();await click(/^ส่งต่องาน$/)
  const dialog=document.querySelector<HTMLElement>('[role=dialog]')!
  assert.equal(dialog.contains(document.activeElement),true)
  await act(async()=>releasePage(page([record,...Array.from({length:22},(_,index)=>task({id:'modal-page-task-'+index}))])));await flush()
  assert.equal(document.querySelectorAll('.team-task-table tbody tr').length,23)
  assert.equal(scrolls.length,0,'A completed page must not scroll the background while its dialog is open')
  assert.equal(dialog.contains(document.activeElement),true,'Keep keyboard focus inside the active modal')
  await act(async()=>document.dispatchEvent(new dom.window.KeyboardEvent('keydown',{key:'Escape',bubbles:true,cancelable:true})))
  assert.equal(document.querySelector('[role=dialog]'),null)
  assert.equal(document.activeElement,trigger,'Closing the modal restores its own trigger, not the task heading')
  assert.equal(scrolls.length,0)
 }finally{if(previous)prototype.scrollIntoView=previous;else Reflect.deleteProperty(prototype,'scrollIntoView')}
})
test('unknown deep link never silently falls back to first listed task',async()=>{
 handler=path=>path==='team-queue/tasks/foreign'?new Response(JSON.stringify({detail:'NOT_FOUND'}),{status:404}):undefined;await mount('/team-queue?task_id=foreign');assert.equal(document.querySelector('.team-task-detail h2')!.textContent,'Task responsibility');assert.match(document.querySelector('.team-task-detail')!.textContent!,/ไม่พบข้อมูล/);assert.equal(button(/^Authored follow-up$/).disabled,false);assert.equal(posts().length,0)
})
test('changing a routed task deep link reads that exact task and clearing it restores the unselected queue',async()=>{
 const client=makeClient();handler=path=>path==='team-queue/tasks/task-b'?task({id:'task-b',title:'Second authored task'}):undefined
 await act(async()=>root.render(<TeamQueue client={client} session={session} requestedTaskId="task-a" navigate={()=>{}} onOpenPatient={()=>{}}/>));await flush();assert.equal(document.activeElement?.textContent,'Authored follow-up')
 await act(async()=>root.render(<TeamQueue client={client} session={session} requestedTaskId="task-b" navigate={()=>{}} onOpenPatient={()=>{}}/>));await flush();assert.equal(document.activeElement?.textContent,'Second authored task');assert.equal(requests.some(item=>item.path==='team-queue/tasks/task-b'),true)
 await act(async()=>root.render(<TeamQueue client={client} session={session} requestedTaskId={null} navigate={()=>{}} onOpenPatient={()=>{}}/>));assert.equal(document.querySelector('.team-task-detail h2')!.textContent,'Task responsibility');assert.equal(posts().length,0)
})
test('ownership, search, domain and offset filters are sent to the server and preserve authorized active count scope',async()=>{
 handler=path=>path.startsWith('team-queue?')?page([record],{total:80,offset:Number(new URL(path,'http://test').searchParams.get('offset'))}):undefined;await mount();await click(/^My work$/);assert.equal(new URL(requests.at(-1)!.path,'http://test').searchParams.get('view'),'mine');await value('ส่วนงานในคิว','D03');await value('ค้นหาคิวงาน','outside-page');await flush(210);let request=new URL(requests.at(-1)!.path,'http://test');assert.equal(request.searchParams.get('q'),'outside-page');assert.equal(request.searchParams.get('domain'),'D03');await click(/^ถัดไป$/);await flush(210);request=new URL(requests.at(-1)!.path,'http://test');assert.equal(request.searchParams.get('offset'),'25');assert.match(document.querySelector('.team-count-scope')!.textContent!,/คำค้นและส่วนงาน/);assert.equal(posts().length,0)
})
test('claim sends expected version and confirms only the bound task and its next version',async()=>{
 handler=(path,init)=>init?.method==='POST'?task({version:5,assignee:{...colleague,id:'actor-a'},capabilities:{...record.capabilities,claim:false,release:true}}):undefined;await mount('/team-queue?task_id=task-a');await click(/^รับผิดชอบงานนี้$/);assert.equal(posts()[0].path,'team-queue/tasks/task-a/claim');assert.deepEqual(JSON.parse(String(posts()[0].init?.body)),{version:4});assert.match(document.querySelector('.team-responsibility')!.textContent!,/Authored colleague/);assert.match(document.body.textContent!,/อ่านกลับจากเซิร์ฟเวอร์สำเร็จ/);assert.equal(posts().length,1)
})
test('uncertain claim blocks navigation and retries the identical command key and body',async()=>{
 let attempt=0;handler=(path,init)=>{if(init?.method==='POST'){if(++attempt===1)throw Error('Disconnected after send');return task({version:5,assignee:colleague})}};await mount('/team-queue?task_id=task-a');await click(/^รับผิดชอบงานนี้$/);assert.equal(button(/^My work$/).disabled,true);assert.equal(button(/Open patient record/).disabled,true);assert.match(document.body.textContent!,/ยังยืนยันผลคำสั่งไม่ได้/);await click(/ตรวจผลคำสั่งเดิม/);assert.equal(posts().length,2);assert.equal(posts()[0].init?.body,posts()[1].init?.body);assert.deepEqual(posts()[0].init?.headers,posts()[1].init?.headers);assert.equal(button(/^My work$/).disabled,false)
})
test('foreign or unchanged-version mutation receipts remain uncertain and cannot confirm success',async()=>{
 handler=(path,init)=>init?.method==='POST'?task({id:'other-task',version:5,patient_id:'other-patient'}):undefined;await mount('/team-queue?task_id=task-a');await click(/^รับผิดชอบงานนี้$/);assert.match(document.body.textContent!,/UNCONFIRMED_TEAM_RESPONSE/);assert.doesNotMatch(document.body.textContent!,/อ่านกลับจากเซิร์ฟเวอร์สำเร็จ/);assert.equal(button(/^My work$/).disabled,true)
})
test('stale version requires explicit exact-task reload before another command',async()=>{
 handler=(path,init)=>init?.method==='POST'?new Response(JSON.stringify({detail:'STALE_VERSION'}),{status:409}):undefined;await mount('/team-queue?task_id=task-a');await click(/^รับผิดชอบงานนี้$/);assert.equal(document.querySelector('.team-task-detail header span')!.textContent?.includes('v4'),true);record=task({version:7,assignee:colleague});await click(/อ่านงานนี้ล่าสุด/);assert.match(document.querySelector('.team-task-detail header')!.textContent!,/v7/);assert.match(document.querySelector('.team-responsibility')!.textContent!,/Authored colleague/);assert.equal(posts().length,1)
})
test('reassignment uses scoped eligible colleagues and requires an explicit handoff reason',async()=>{
 handler=(path,init)=>init?.method==='POST'?task({version:5,assignee:colleague}):undefined;await mount('/team-queue?task_id=task-a');await click(/^ส่งต่องาน$/);assert.equal(requests.some(item=>item.path==='team-queue/tasks/task-a/assignees'),true);assert.equal(requests.some(item=>item.path.startsWith('admin/')),false);assert.equal(document.body.style.overflow,'hidden');await value('ผู้รับผิดชอบคนใหม่','actor-b');await submit();assert.equal(posts().length,0);await value('เหตุผลส่งต่องาน','Review next visit with assigned colleague');await submit();assert.deepEqual(JSON.parse(String(posts()[0].init?.body)),{version:4,assignee_id:'actor-b',reason:'Review next visit with assigned colleague'});assert.equal(document.querySelector('[role=dialog]'),null);assert.equal(document.body.style.overflow,'')
})
test('schedule retains nullable due date and an operational priority without inferring triage',async()=>{
 handler=(path,init)=>init?.method==='POST'?task({version:5,priority:'high'}):undefined;await mount('/team-queue?task_id=task-a');await click(/^กำหนดงาน$/);await value('ความสำคัญของงาน','high');await submit();assert.equal(posts()[0].path,'team-queue/tasks/task-a/schedule');assert.deepEqual(JSON.parse(String(posts()[0].init?.body)),{version:4,due_at:null,priority:'high'});assert.match(document.querySelector('.team-responsibility')!.textContent!,/สูง/)
})
test('overdue escalation keeps the same obligation and sends a reviewed reason once',async()=>{
 record=task({overdue:true,due_at:'2026-11-14T00:00:00Z',assignee:colleague,capabilities:{...task().capabilities,claim:false,escalate:true}});handler=(path,init)=>init?.method==='POST'?{...record,version:5,escalation_level:1,escalation_reason:'Waiting for authorized reviewer'}:undefined;await mount('/team-queue?task_id=task-a');await click(/^ยกระดับการติดตาม$/);await value('เหตุผลยกระดับการติดตาม','Waiting for authorized reviewer');await submit();assert.equal(posts()[0].path,'team-queue/tasks/task-a/escalate');assert.deepEqual(JSON.parse(String(posts()[0].init?.body)),{version:4,reason:'Waiting for authorized reviewer'});assert.match(document.querySelector('.team-responsibility')!.textContent!,/Authored colleague/);assert.match(document.querySelector('.team-escalation-reason')!.textContent!,/Waiting for authorized reviewer/);assert.equal(posts().length,1)
})
test('terminal and server-denied capabilities expose no coordination buttons',async()=>{
 record=task({status:'completed',capabilities:{claim:false,release:false,assign:false,schedule:false,escalate:false}});await mount('/team-queue?task_id=task-a');assert.equal(document.querySelector('.team-actions')!.children.length,0);assert.equal(posts().length,0)
})
test('assignment dialog traps focus and Escape restores the triggering button',async()=>{
 await mount('/team-queue?task_id=task-a');button(/^ส่งต่องาน$/).focus();await click(/^ส่งต่องาน$/);const dialog=document.querySelector<HTMLElement>('[role=dialog]')!;assert.equal(dialog.contains(document.activeElement),true);await act(async()=>document.dispatchEvent(new dom.window.KeyboardEvent('keydown',{key:'Escape',bubbles:true,cancelable:true})));assert.equal(document.querySelector('[role=dialog]'),null);assert.equal(document.activeElement,button(/^ส่งต่องาน$/));assert.equal(document.body.style.overflow,'')
})
