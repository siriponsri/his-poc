import {test,beforeEach,afterEach} from 'node:test'
import assert from 'node:assert/strict'
import {JSDOM} from 'jsdom'
import React,{act} from 'react'
import type {Root} from 'react-dom/client'
import {Client} from '../src/lib/client'
import {AIWorkspace} from '../src/components/core-workspaces'
import {ResourceWorkspace} from '../src/components/workspace'
import {patientResource} from '../src/components/core-workspaces'
const dom=new JSDOM('<!doctype html><html><body><div id="root"></div></body></html>',{url:'http://localhost:8080/home'})
for(const key of ['window','document','Event','CustomEvent','HTMLElement','HTMLInputElement','HTMLTextAreaElement','Node','location','history'])Object.defineProperty(globalThis,key,{configurable:true,value:(dom.window as any)[key]})
;(globalThis as any).IS_REACT_ACT_ENVIRONMENT=true
;(dom.window as any).scrollTo=()=>{}
;(dom.window as any).matchMedia=()=>({matches:false,addEventListener(){},removeEventListener(){}})
const {createRoot}=await import('react-dom/client')
let root:Root;let calls:any[];let handler:(path:string,body:any,init:any)=>any
const client=new Client(async(url,init)=>{const path=String(url).replace('/api/v2/','');const body=init?.body?JSON.parse(String(init.body)):undefined;calls.push({path,body,init});const result=await handler(path,body,init);if(result instanceof Response)return result;return new Response(JSON.stringify(result??{}))})
const proposal=(version=1,status='pending')=>({id:'proposal1',version,status,task_id:'task1',patient_id:'p1',encounter_id:'e1',action_hash:String(version).repeat(64),action:{text:'summary '+version},evidence:{document_version_id:'docv1',content_hash:'e'.repeat(64),encounter_version:1}})
let proposals:any[],results:any[]
beforeEach(()=>{document.body.innerHTML='<div id="root"></div>';root=createRoot(document.getElementById('root')!);calls=[];proposals=[proposal()];results=[];handler=(path,body)=>{if(path==='ai/config')return {active_provider:'mock_demo',demo:true,live_routes_enabled:false,supported_task_kinds:['document_review','imaging_review','dr_review']};if(path.startsWith('tasks'))return {items:[{id:'task1',patient_id:'p1',encounter_id:'e1',title:'Review document',status:'open'}]};if(path.startsWith('documents'))return {items:[{id:'doc1',patient_id:'p1',encounter_id:'e1',title:'Synthetic document',version:1}]};if(path.startsWith('proposals')&&!body)return {items:proposals};if(path.startsWith('runs'))return {items:[]};if(path.startsWith('results'))return {items:results};return {items:[]}}})
afterEach(async()=>{await act(async()=>root.unmount())})
async function click(text:string){const button=[...document.querySelectorAll('button')].find(b=>b.textContent?.includes(text));assert.ok(button,'button '+text);assert.equal(button.disabled,false,'enabled '+text);await act(async()=>button.click())}
async function mountAI(){await act(async()=>root.render(<AIWorkspace client={client} context={{patient_id:'p1',encounter_id:'e1'}}/>));await click('summary 1')}
async function fillTextarea(value:string){const input=document.querySelector('textarea')!;await act(async()=>{Object.getOwnPropertyDescriptor(dom.window.HTMLTextAreaElement.prototype,'value')!.set!.call(input,value);input.dispatchEvent(new dom.window.Event('input',{bubbles:true}));input.dispatchEvent(new dom.window.Event('change',{bubbles:true}))})}
test('actual mounted AI: edit response + refresh failure keeps displayed revision and approval binding aligned',async()=>{await mountAI();await fillTextarea('reviewed new text');const base=handler;let edited=false;handler=(path,body,init)=>{if(path==='proposals/proposal1/review'){if(body.decision==='edit'){edited=true;return {...proposal(2),action:{text:'reviewed new text'}}}return {...proposal(2,'approved'),action:{text:'reviewed new text'}}}if(edited&&path==='proposals'&&!body)throw Error('refresh lost');return base(path,body,init)};await click('บันทึกเป็นรุ่นใหม่');assert.match(document.body.textContent!,/ทบทวนรุ่น 2/);assert.equal(document.querySelector('textarea')?.value,'reviewed new text');await click('อนุมัติรุ่นที่แสดง');const approve=calls.find(c=>c.body?.decision==='approve');assert.equal(approve.body.version,2);assert.equal(approve.body.action_hash,'2'.repeat(64))})
test('actual mounted AI: definitive commit409 clears unknown state without reconnect',async()=>{proposals=[proposal(1,'approved')];await mountAI();const base=handler;handler=(path,body,init)=>path.endsWith('/commit')?new Response('{"detail":{"code":"STALE_EVIDENCE_OR_TARGET","outcome":"not_written"}}',{status:409}):base(path,body,init);await click('ยืนยันบันทึกผล');assert.doesNotMatch(document.body.textContent!,/Retry commit เดิม/);assert.match(document.body.textContent!,/เซิร์ฟเวอร์ปฏิเสธคำสั่ง/);assert.equal([...document.querySelectorAll('button')].find(b=>b.textContent==='สร้างข้อเสนอจากเอกสารที่บันทึก')?.disabled,true)})
test('actual mounted AI: lost response matches readback identity and clears pending',async()=>{proposals=[proposal(1,'approved')];await mountAI();const base=handler;handler=(path,body,init)=>{if(path.endsWith('/commit')){results=[{id:'result1',task_id:'task1',patient_id:'p1',encounter_id:'e1',proposal_id:'proposal1',proposal_version:1,action_hash:'1'.repeat(64),operation_key:init.headers['Idempotency-Key']}];throw Error('response lost')}return base(path,body,init)};await click('ยืนยันบันทึกผล');assert.match(document.body.textContent!,/Retry commit เดิม/);await click('โหลดและยืนยันผลล่าสุด');assert.doesNotMatch(document.body.textContent!,/Retry commit เดิม/);assert.match(document.body.textContent!,/ยืนยันผลที่บันทึกแล้ว/);assert.match(document.body.textContent!,/result1/)})
test('actual mounted patient form sends typed fields and displays server-created record',async()=>{let patients:any[]=[];handler=(path,body)=>{if(path==='patients'&&body){const p={id:'new-patient',version:1,status:'draft',...body};patients.push(p);return p}if(path==='patients')return {items:patients};return {items:[]}};await act(async()=>root.render(<ResourceWorkspace resource={patientResource} client={client} context={{patient_id:'',encounter_id:''}}/>));await click('เพิ่มผู้ป่วย');const form=document.querySelector('form')!;const inputs=form.querySelectorAll('input');for(const [index,value] of [[0,'ผู้ป่วยสังเคราะห์'],[1,'SYN-999']] as const){await act(async()=>{Object.getOwnPropertyDescriptor(dom.window.HTMLInputElement.prototype,'value')!.set!.call(inputs[index],value);inputs[index].dispatchEvent(new dom.window.Event('input',{bubbles:true}));inputs[index].dispatchEvent(new dom.window.Event('change',{bubbles:true}))})}await act(async()=>form.dispatchEvent(new dom.window.Event('submit',{bubbles:true,cancelable:true})));assert.equal(calls.find(c=>c.body)?.body.display_name,'ผู้ป่วยสังเคราะห์');assert.match(document.body.textContent!,/new-patient/)})
let appHandler:(path:string,body:any,init:any)=>any=()=>({})
test('exported referral exposes scoped download without embedding its packet in detail JSON',async()=>{
 const row={id:'referral-synthetic',status:'exported',version:3};handler=path=>path==='clinical/D20/records'?{items:[row]}:row
 await act(async()=>root.render(<ResourceWorkspace resource={{id:'D20',label:'ส่งต่อ',path:'clinical/D20/records',fields:[],actions:[]}} client={client} context={{patient_id:'',encounter_id:''}}/>))
 await click('referral-synthetic');assert.equal(document.querySelector<HTMLAnchorElement>('.download-link')?.getAttribute('href'),'/api/v2/clinical/D20/records/referral-synthetic/export')
 assert.equal('packet' in row,false)
})
test('typed message sequence submits JSON integer while money retains Decimal text',async()=>{
 let sent:any
 await act(async()=>root.render(<DataForm client={client} fields={[{name:'sequence',label:'ลำดับข้อความ',type:'integer',required:true,min:1},{name:'amount',label:'ยอดเงิน',type:'number',required:true}]} onSubmit={async data=>{sent=data}}/>))
 const inputs=document.querySelectorAll('input');assert.equal(inputs[0].type,'number');assert.equal(inputs[0].step,'1')
 await inputValue(inputs[0],'2');await inputValue(inputs[1],'9999999999999999.99')
 await act(async()=>document.querySelector('form')!.dispatchEvent(new dom.window.Event('submit',{bubbles:true,cancelable:true})))
 assert.equal(sent.sequence,2);assert.equal(sent.amount,'9999999999999999.99')
})
test('integer form rejects fractional, unsafe and below-minimum sequence without sending',async()=>{
 let writes=0
 await act(async()=>root.render(<DataForm client={client} fields={[{name:'sequence',label:'ลำดับข้อความ',type:'integer',required:true,min:1}]} onSubmit={async()=>{writes++}}/>))
 for(const value of ['1.5','9007199254740992','0']){await inputValue(document.querySelector('input')!,value);await act(async()=>document.querySelector('form')!.dispatchEvent(new dom.window.Event('submit',{bubbles:true,cancelable:true})));assert.match(document.querySelector('[role=alert]')!.textContent!,/จำนวนเต็ม/)}
 assert.equal(writes,0)
})
test('actual audit route inspects authorized list snapshot without nonexistent detail request',async()=>{
 history.replaceState({},'','/audit');const requests:string[]=[]
 appHandler=path=>{requests.push(path);if(path==='auth/me')return {...session,user:{...session.user,roles:['auditor'],permissions:['audit.read']}};if(path==='audit')return {items:[{id:'audit-synthetic-one',entity_id:'patient-synthetic-one',action:'patient.created',actor_id:'synthetic-registration',created_at:'2026-11-13T12:00:00Z'}]};if(path.startsWith('audit/'))return new Response('{"detail":"Not Found"}',{status:404});return {items:[]}}
 await act(async()=>root.render(<App/>));await click('audit-synthetic-one')
 assert.match(document.querySelector('.detail-card')!.textContent!,/patient-synthetic-one/)
 assert.match(document.querySelector('.detail-card')!.textContent!,/patient.created/)
 assert.equal(requests.some(path=>path.startsWith('audit/')),false)
 assert.equal(document.querySelector('.detail-card form'),null)
})
globalThis.fetch=async(url,init)=>{const path=String(url).replace('/api/v2/','');const body=init?.body?JSON.parse(String(init.body)):undefined;const result=await appHandler(path,body,init);return result instanceof Response?result:new Response(JSON.stringify(result??{}))}
const {default:App}=await import('../src/App')
const session={user:{id:'u1',username:'registration',display_name:'เจ้าหน้าที่ทดสอบ',organization_id:'org1',facility_id:'f1',roles:['registration'],permissions:['D01.read','D01.write','D03.read'],patient_scope:null},csrf_token:'csrf1',expires_at:'2099-01-01T00:00:00Z'}
async function inputValue(input:HTMLInputElement,value:string){await act(async()=>{Object.getOwnPropertyDescriptor(dom.window.HTMLInputElement.prototype,'value')!.set!.call(input,value);input.dispatchEvent(new dom.window.Event('input',{bubbles:true}));input.dispatchEvent(new dom.window.Event('change',{bubbles:true}))})}
test('actual mounted app: login backend session, scoped home counters, logout clears prior records',async()=>{history.replaceState({},'','/');const scrollCalls:{path:string;loginVisible:boolean;options:unknown}[]=[];const originalScroll=dom.window.scrollTo;(dom.window as any).scrollTo=(options:unknown)=>scrollCalls.push({path:location.pathname,loginVisible:!!document.querySelector('.login-panel form'),options});let logged=false;appHandler=(path,body)=>{if(path==='auth/me')return logged?session:new Response('{"detail":"UNAUTHENTICATED"}',{status:401});if(path==='auth/login'){assert.equal(body.username,'registration');assert.equal(body.password,'local-password');logged=true;return session}if(path==='auth/logout'){logged=false;return {ok:true}}if(path==='home')return {open_tasks:3,items:[{id:'task-user-one',title:'งานของผู้ใช้เดิม',domain:'D03'}]};if(path==='patients')return {items:[{id:'patient-user-one',display_name:'ชื่อผู้ป่วยเดิม'}]};return {items:[]}};await act(async()=>root.render(<App/>));assert.equal(location.pathname,'/login');const inputs=document.querySelectorAll('input');await inputValue(inputs[0],'registration');await inputValue(inputs[1],'local-password');await act(async()=>document.querySelector('form')!.dispatchEvent(new dom.window.Event('submit',{bubbles:true,cancelable:true})));assert.deepEqual(scrollCalls.at(-1),{path:'/home',loginVisible:false,options:{top:0,left:0,behavior:'instant'}});assert.match(document.querySelector('.sidebar-footer')!.textContent!,/เจ้าหน้าที่ทดสอบ/);assert.match(document.querySelector('.queue-date')!.textContent!,/f1/);assert.match(document.body.textContent!,/งานของผู้ใช้เดิม/);assert.match(document.querySelector('.inline-count')!.textContent!,/1 งานที่เปิดในรายการนี้/);await click('ออกจากระบบ');assert.ok(document.querySelector('.login-panel form'));assert.equal(document.querySelector<HTMLInputElement>('input[autocomplete=username]')?.value,'');assert.equal(document.querySelector<HTMLInputElement>('input[autocomplete=current-password]')?.value,'');assert.doesNotMatch(document.body.textContent!,/งานของผู้ใช้เดิม|ชื่อผู้ป่วยเดิม/);assert.equal(location.pathname,'/login');assert.deepEqual(scrollCalls.at(-1),{path:'/login',loginVisible:true,options:{top:0,left:0,behavior:'instant'}});dom.window.scrollTo=originalScroll})
test('actual mounted app: skip focus retains route and unknown route shows404',async()=>{history.replaceState({},'','/domains/D01');appHandler=path=>path==='auth/me'?session:path==='home'?{open_tasks:0,items:[]}:{items:[]};await act(async()=>root.render(<App/>));await click('ข้ามไปยังเนื้อหา');assert.equal(location.pathname,'/domains/D01');assert.equal(document.activeElement?.className,'page');await act(async()=>{history.pushState({},'','/wrong-url');window.dispatchEvent(new dom.window.PopStateEvent('popstate'))});assert.match(document.body.textContent!,/404 · ไม่พบหน้านี้/)})
test('actual mounted app: unauthorized deep link shows denied and never mutates',async()=>{history.replaceState({},'','/domains/D25');const sent:any[]=[];appHandler=(path,body)=>{sent.push({path,body});return path==='auth/me'?session:{items:[]}};await act(async()=>root.render(<App/>));assert.match(document.body.textContent!,/ไม่มีสิทธิ์เข้าพื้นที่นี้/);assert.equal(sent.some(x=>x.body),false)})
test('fresh login retains the complete scoped clinical destination without trusting an external redirect',async()=>{
 const destination='/domains/D10?patient_id=scope-patient&encounter_id=scope-visit&record=scope-result'
 history.replaceState({},'',destination);let logged=false
 appHandler=path=>{
  if(path==='auth/me')return logged?{...session,user:{...session.user,permissions:['*']}}:new Response('{"detail":"UNAUTHENTICATED"}',{status:401})
  if(path==='auth/login'){logged=true;return {...session,user:{...session.user,permissions:['*']}}}
  if(path==='patients')return {items:[{id:'scope-patient',display_name:'Scoped synthetic patient'}]}
  if(path==='encounters?patient_id=scope-patient')return {items:[{id:'scope-visit',patient_id:'scope-patient',kind:'OPD',status:'in_consult'}]}
  if(path==='clinical/D10/records/scope-result')return {id:'scope-result',patient_id:'scope-patient',encounter_id:'scope-visit',analyte:'ALT',result_value:'42',status:'released',version:6}
  return {items:[]}
 }
 await act(async()=>root.render(<App/>));assert.equal(location.pathname,'/login')
 const inputs=document.querySelectorAll('input');await inputValue(inputs[0],'synthetic');await inputValue(inputs[1],'synthetic-password')
 await act(async()=>document.querySelector('form')!.dispatchEvent(new dom.window.Event('submit',{bubbles:true,cancelable:true})))
 assert.equal(location.pathname+location.search,destination)
 const selectors=document.querySelectorAll<HTMLSelectElement>('.patient-context select')
 assert.equal(selectors[0].value,'scope-patient');assert.equal(selectors[1].value,'scope-visit')
 assert.match(document.querySelector('.detail-header h3')!.textContent!,/ALT/)
})
test('clinical result uses its test name and keeps raw audit details collapsed beside the readable history',async()=>{
 const row={id:'3afe9621-240c-4cb6-87b7-3b1d3fd83ef0',analyte:'ALT',result_value:'42',status:'released',history:[{id:'event-one',action:'lab.released',actor_id:'synthetic-laboratory',created_at:'2026-11-14T00:00:00Z',snapshot:{result_value:'42'}}]}
 handler=path=>path==='clinical/D10/records'?{items:[row]}:row
 history.replaceState({},'','/domains/D10')
 await act(async()=>root.render(<ResourceWorkspace resource={{id:'D10',label:'Laboratory',path:'clinical/D10/records',fields:[],actions:[]}} client={client} context={{patient_id:'',encounter_id:''}}/>))
 assert.equal(document.querySelector('.record-button strong')?.textContent,'ALT');await click('ALT')
 assert.equal(document.querySelector('.detail-header h3')?.textContent,'ALT')
 assert.match(document.querySelector('.history')!.textContent!,/lab.released/)
 assert.doesNotMatch(document.querySelector('.detail-values > .detail-grid')!.textContent!,/snapshot|lab.released/)
 const raw=document.querySelector<HTMLDetailsElement>('.detail-values .technical')!;assert.equal(raw.open,false);assert.match(raw.textContent!,/snapshot/)
})
const {DataForm}=await import('../src/components/forms')
const fullDomains=(await import('../src/data/full-domains.json')).default
for(const domain of fullDomains)test('actual mounted route has functional controls '+domain.id,async()=>{
 history.replaceState({},'','/domains/'+domain.id)
 appHandler=path=>path==='auth/me'?{...session,user:{...session.user,permissions:['*']}}:path==='operations/health'?{database:'ok',postgres_version:'18.6'}:path==='admin/overview'?{scope:{organization_id:session.user.organization_id,facility_id:session.user.facility_id},users:{total:0,active:0,suspended:0,disabled:0},sessions:{active:0,revoked:0,expired:0},security:{recent_denial_count:0,window_hours:24},database:{reachable:true,migration:'0005_assistant_workspaces'},assistant:{configured:false,route:'none',engine_version:'none',profiles_qualified:[],counts:{queued:0,running:0,succeeded:0,failed:0,awaiting_review:0,active_watches:0},live_status:'not_checked'},observed_at:'2026-11-15T00:00:00Z'}:{items:[]}
 await act(async()=>root.render(<App/>))
 if(domain.id==='D34'){
  assert.equal(document.querySelector('#admin-title')?.textContent,'Administration')
  assert.doesNotMatch(document.body.textContent!,/INVALID_ADMIN_OVERVIEW/)
  const add=[...document.querySelectorAll('button')].find(button=>button.textContent==='เพิ่มผู้ใช้');assert.ok(add,'dedicated administration create control');await act(async()=>add.click());assert.ok(document.querySelector('[role=dialog] input[type=password]'),'typed credential form');assert.equal(document.querySelector<HTMLInputElement>('[role=dialog] input[type=password]')?.minLength,12)
 }else{
  assert.match(document.body.textContent!,new RegExp(domain.id));assert.doesNotMatch(document.body.textContent!,/ไม่พบ contract|ไม่มีสิทธิ์เข้าพื้นที่นี้/)
  if(domain.id==='D37'){assert.ok(document.querySelector('select'));assert.ok([...document.querySelectorAll('button')].find(b=>b.textContent?.includes('สร้างข้อเสนอ')))}else if(domain.id==='D38'){assert.ok([...document.querySelectorAll('button')].find(b=>b.textContent==='สร้าง backup'))}else{const add=[...document.querySelectorAll('button')].find(b=>b.textContent?.startsWith('＋ เพิ่ม'));assert.ok(add,'domain create control '+domain.id);await act(async()=>add.click());assert.ok(document.querySelector('form'),'typed form '+domain.id);assert.ok(document.querySelector('form input, form select,form textarea'),'semantic inputs '+domain.id)}
 }
})
test('actual form preserves Decimal strings and serializes local datetime as aware ISO',async()=>{let sent:any;await act(async()=>root.render(<DataForm client={client} fields={[{name:'amount',label:'จำนวนเงิน',type:'number',required:true},{name:'observed_at',label:'เวลา',type:'datetime-local',required:true}]} onSubmit={async data=>{sent=data}}/>));const inputs=document.querySelectorAll('input');await inputValue(inputs[0],'9999999999999999.99');await inputValue(inputs[1],'2026-11-12T10:20');await act(async()=>document.querySelector('form')!.dispatchEvent(new dom.window.Event('submit',{bubbles:true,cancelable:true})));assert.equal(sent.amount,'9999999999999999.99');assert.equal(sent.observed_at,new Date('2026-11-12T10:20').toISOString())})
test('actual record detail ignores delayed result for previous selection',async()=>{let resolveA:(x:any)=>void=()=>{};handler=(path)=>{if(path==='patients')return {items:[{id:'a',display_name:'Patient A'},{id:'b',display_name:'Patient B'}]};if(path==='patients/a')return new Promise(resolve=>{resolveA=resolve});if(path==='patients/b')return {id:'b',display_name:'Patient B detail'};return {items:[]}};await act(async()=>root.render(<ResourceWorkspace resource={patientResource} client={client} context={{patient_id:'',encounter_id:''}}/>));await click('Patient A');await click('Patient B');await act(async()=>resolveA({id:'a',display_name:'Stale Patient A detail'}));assert.match(document.querySelector('.detail-card')!.textContent!,/Patient B detail/);assert.doesNotMatch(document.querySelector('.detail-card')!.textContent!,/Stale Patient A detail/)})
test('actual file form hides encoding and submits only internally derived file bytes/MIME',async()=>{let sent:any;await act(async()=>root.render(<DataForm client={client} fields={[{name:'file_base64',label:'ไฟล์สังเคราะห์',type:'file',required:true},{name:'file_mime',label:'ชนิดไฟล์ภายใน',type:'hidden',required:true}]} onSubmit={async data=>{sent=data}}/>));const file=document.querySelector('input[type=file]')!;const bytes=new TextEncoder().encode('SYNTHETIC FILE');Object.defineProperty(file,'files',{configurable:true,value:[{size:bytes.length,type:'text/plain',arrayBuffer:async()=>bytes.buffer}]});await act(async()=>file.dispatchEvent(new dom.window.Event('change',{bubbles:true})));assert.equal(document.querySelector('textarea'),null);await act(async()=>document.querySelector('form')!.dispatchEvent(new dom.window.Event('submit',{bubbles:true,cancelable:true})));assert.equal(sent.file_base64,Buffer.from(bytes).toString('base64'));assert.equal(sent.file_mime,'text/plain')})
test('actual metadata-only document role has no content editing controls',async()=>{history.replaceState({},'','/domains/D22');appHandler=path=>path==='auth/me'?{...session,user:{...session.user,permissions:['D22.read','D22.write']}}:path==='documents'?{items:[{id:'metadata-doc',title:'Metadata only',version:1,status:'draft',content_access:'metadata_only'}]}:{items:[]};await act(async()=>root.render(<App/>));assert.equal([...document.querySelectorAll('button')].some(b=>b.textContent?.startsWith('＋ เพิ่ม')),false);assert.equal(document.querySelector('textarea'),null)})
