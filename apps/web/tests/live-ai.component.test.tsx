import {test,beforeEach,afterEach} from 'node:test'
import assert from 'node:assert/strict'
import {JSDOM} from 'jsdom'
import React,{act} from 'react'
import type {Root} from 'react-dom/client'
import {Client} from '../src/lib/client'
import {AIWorkspace} from '../src/components/core-workspaces'

// Component-only HTTP doubles: actual dr-train/browser execution is separate evidence.
const dom=new JSDOM('<!doctype html><html><body><div id="root"></div></body></html>',{url:'http://localhost:8000/domains/D37'})
for(const key of ['window','document','Event','CustomEvent','HTMLElement','HTMLInputElement','HTMLTextAreaElement','HTMLSelectElement','Node','location','history'])Object.defineProperty(globalThis,key,{configurable:true,value:(dom.window as any)[key]})
;(globalThis as any).IS_REACT_ACT_ENVIRONMENT=true
const {createRoot}=await import('react-dom/client')
let root:Root,calls:any[],config:any,proposals:any[],runs:any[],mutate:(path:string,body:any,init:any)=>any
const model='hf.co/scb10x/typhoon2.1-gemma3-12b-gguf:Q4_K_M'
const keys=['chief_complaint','history','assessment','plan','author']
const completeness=()=>({checklist_id:'SYNTHETIC_DOCUMENT_COMPLETENESS_V1',items:keys.map((key,index)=>({key,label:key,status:index===0?'present':'missing',evidence_quote:index===0?'อาการสำคัญ: มาทบทวนเอกสาร':''})),summary:'พบ 1 รายการ ยังไม่พบ 4 รายการ',requires_human_review:true})
const proposal=()=>({id:'live-proposal',version:1,status:'pending',task_id:'task-doc',patient_id:'p1',encounter_id:'e1',demo:false,provider:'dr_train_ollama',action_hash:'a'.repeat(64),action:{text:'AI ตรวจข้อความสังเคราะห์แล้ว',completeness:completeness()},evidence:{document_version_id:'dv1',content_hash:'b'.repeat(64),encounter_version:1}})
const client=new Client(async(url,init)=>{
 const path=String(url).replace('/api/v2/','');const body=init?.body?JSON.parse(String(init.body)):undefined
 calls.push({path,body,init})
 let result:any
 if(body)result=await mutate(path,body,init)
 else if(path==='ai/config')result=config
 else if(path.startsWith('tasks'))result={items:[{id:'task-doc',patient_id:'p1',encounter_id:'e1',title:'งานตรวจเอกสาร',kind:'document_review',status:'open'},{id:'task-dr',patient_id:'p1',encounter_id:'e1',title:'งาน DR ที่ยังไม่เปิดใช้',kind:'dr_review',status:'open'}]}
 else if(path.startsWith('documents'))result={items:[{id:'doc1',patient_id:'p1',encounter_id:'e1',title:'เอกสารสังเคราะห์',version:1}]}
 else if(path.startsWith('proposals'))result={items:proposals}
 else if(path.startsWith('runs'))result={items:runs}
 else result={items:[]}
 return result instanceof Response?result:new Response(JSON.stringify(result??{}))
})
beforeEach(()=>{
 document.body.innerHTML='<div id="root"></div>';root=createRoot(document.getElementById('root')!);calls=[];proposals=[];runs=[]
 config={active_provider:'dr_train_ollama',demo:false,live_routes_enabled:true,model,model_digest:'a'.repeat(64),supported_task_kinds:['document_review']}
 mutate=()=>{throw Error('Unexpected mutation')}
})
afterEach(async()=>{await act(async()=>root.unmount())})
async function mount(){await act(async()=>root.render(<AIWorkspace client={client} context={{patient_id:'p1',encounter_id:'e1'}}/>))}
function button(name:string){const element=[...document.querySelectorAll('button')].find(b=>b.textContent===name);assert.ok(element,'button '+name);return element}
async function click(name:string){const element=button(name);assert.equal(element.disabled,false,'enabled '+name);await act(async()=>element.click())}
async function select(label:string,value:string){const control=[...document.querySelectorAll('label')].find(l=>l.textContent?.startsWith(label))?.querySelector('select');assert.ok(control,'select '+label);await act(async()=>{Object.getOwnPropertyDescriptor(dom.window.HTMLSelectElement.prototype,'value')!.set!.call(control,value);control.dispatchEvent(new dom.window.Event('change',{bubbles:true}))})}
async function selectContext(){await select('งานที่ผูกผู้ป่วย / encounter','task-doc');await select('เอกสารหลักฐาน','doc1')}

test('live provider has accurate model/mode labels and offers only supported document tasks',async()=>{
 proposals=[{...proposal(),id:'historical-mock',demo:true,action:{text:'ข้อเสนอ mock เดิม'}}]
 runs=[{id:'run-live',task_id:'task-doc',outcome:'success',provider:'dr_train_ollama',elapsed_ms:4200,provenance:{model},usage:{input_tokens:111,output_tokens:22},measured_cost:null}]
 await mount();assert.match(document.body.textContent!,/AI จริง · dr-train/);assert.match(document.body.textContent!,new RegExp('typhoon2.1'))
 assert.doesNotMatch(document.body.textContent!,/EXPLICIT MOCK|สถานการณ์ mock/)
 const taskSelect=[...document.querySelectorAll('select')][0];assert.deepEqual([...taskSelect.options].map(o=>o.value),['','task-doc'])
 assert.match(document.body.textContent!,/DEMO mock/);assert.match(document.body.textContent!,/โทเคนเข้า 111 · ออก 22/);assert.match(document.body.textContent!,/ต้นทุน UNKNOWN/)
 assert.equal(calls.some(c=>c.body),false)
})

test('live response renders five typed checks and evidence while human approval remains explicit',async()=>{
 mutate=(path,body)=>{assert.equal(path,'proposals');assert.equal(body.scenario,'success');const value=proposal();proposals=[value];return {run:{outcome:'success',provider:'dr_train_ollama'},proposal:value,demo:false}}
 await mount();await selectContext();await click('สร้างข้อเสนอจากเอกสารที่บันทึก')
 const checklist=document.querySelector('[aria-label="ผลตรวจความครบถ้วนเอกสาร"]')!;assert.ok(checklist);assert.equal(checklist.querySelectorAll('li').length,5)
 assert.match(checklist.textContent!,/อาการสำคัญ.*เหตุผลที่มารับบริการ/);assert.match(checklist.textContent!,/ยังไม่พบในเอกสาร/)
 assert.equal(checklist.querySelector('blockquote')!.textContent,'อาการสำคัญ: มาทบทวนเอกสาร')
 assert.equal(calls.filter(c=>c.body).length,1);assert.equal(button('อนุมัติรุ่นที่แสดง').disabled,false);assert.equal(button('ยืนยันบันทึกผล').disabled,true)
})

test('unknown proposal response and pending replay retain exact request body/key until confirmed',async()=>{
 let attempts=0;mutate=(path)=>{assert.equal(path,'proposals');attempts++;if(attempts===1)throw Error('response lost');if(attempts===2)return {run:{outcome:'running',provider:'dr_train_ollama'},pending:true,proposal:null,demo:false};const value=proposal();proposals=[value];return {run:{outcome:'success',provider:'dr_train_ollama'},proposal:value,demo:false}}
 await mount();await selectContext();await click('สร้างข้อเสนอจากเอกสารที่บันทึก')
 assert.equal(button('สร้างข้อเสนอจากเอกสารที่บันทึก').disabled,true);assert.equal([...document.querySelectorAll('select')].every(s=>s.disabled),true)
 await click('Retry สร้างข้อเสนอเดิม');assert.match(document.body.textContent!,/AI กำลังประมวลผลคำสั่งเดิม/)
 await click('Retry สร้างข้อเสนอเดิม');const writes=calls.filter(c=>c.body)
 assert.equal(writes.length,3);assert.equal(new Set(writes.map(c=>c.init.headers['Idempotency-Key'])).size,1);assert.ok(writes.every(c=>JSON.stringify(c.body)===JSON.stringify(writes[0].body)))
 assert.equal([...document.querySelectorAll('button')].some(b=>b.textContent==='Retry สร้างข้อเสนอเดิม'),false)
 assert.match(document.body.textContent!,/AI ตรวจข้อความสังเคราะห์แล้ว/)
})

test('malformed provider configuration fails closed without silently displaying mock mode',async()=>{
 config={items:[]};await mount();assert.match(document.querySelector('[role=alert]')!.textContent!,/INVALID_AI_CONFIGURATION/)
 assert.equal(button('สร้างข้อเสนอจากเอกสารที่บันทึก').disabled,true);assert.doesNotMatch(document.body.textContent!,/EXPLICIT MOCK|สถานการณ์ mock/);assert.equal(calls.some(c=>c.body),false)
})

test('a failed profile refresh cannot leave stale live configuration enabled',async()=>{
 await mount();await selectContext();assert.equal(button('สร้างข้อเสนอจากเอกสารที่บันทึก').disabled,false)
 config={active_provider:'unsupported',demo:false,live_routes_enabled:true};await click('โหลดและยืนยันผลล่าสุด')
 assert.match(document.querySelector('[role=alert]')!.textContent!,/INVALID_AI_CONFIGURATION/);assert.equal(button('สร้างข้อเสนอจากเอกสารที่บันทึก').disabled,true)
 assert.equal(calls.some(c=>c.body),false)
})

test('a live proposal with a malformed checklist cannot be approved or committed',async()=>{
 proposals=[{...proposal(),action:{text:'Incomplete wire shape',completeness:{...completeness(),items:[null]}}}]
 await mount();const record=[...document.querySelectorAll('button')].find(b=>b.textContent?.includes('Incomplete wire shape'));assert.ok(record);await act(async()=>record.click())
 assert.match(document.querySelector('[role=alert]')!.textContent!,/รายการตรวจของข้อเสนอ AI ไม่ครบ/);assert.equal(button('อนุมัติรุ่นที่แสดง').disabled,true);assert.equal(button('ยืนยันบันทึกผล').disabled,true)
})

test('live result from an old patient context cannot repopulate a newly selected context',async()=>{
 let complete:(value:any)=>void=()=>{};mutate=()=>new Promise(resolve=>{complete=resolve})
 await mount();await selectContext();act(()=>button('สร้างข้อเสนอจากเอกสารที่บันทึก').click())
 await act(async()=>{await new Promise(resolve=>setTimeout(resolve,0));root.render(<AIWorkspace client={client} context={{patient_id:'p2',encounter_id:'e2'}}/>)})
 await act(async()=>complete({run:{outcome:'success',provider:'dr_train_ollama'},proposal:proposal(),demo:false}))
 assert.doesNotMatch(document.body.textContent!,/AI ตรวจข้อความสังเคราะห์แล้ว/);assert.equal(document.querySelector('[aria-label="ผลตรวจความครบถ้วนเอกสาร"]'),null)
})

test('proposal from another subject or missing subject metadata is not exposed under a selected context',async()=>{
 proposals=[{...proposal(),patient_id:'p2',encounter_id:'e2',action:{text:'WRONG SUBJECT'}},{...proposal(),id:'unknown',patient_id:undefined,encounter_id:undefined,action:{text:'UNKNOWN SUBJECT'}}]
 await mount();assert.doesNotMatch(document.body.textContent!,/WRONG SUBJECT|UNKNOWN SUBJECT/)
 assert.equal(document.querySelector('textarea'),null);assert.equal(calls.some(c=>c.body),false)
})

test('unscoped historical proposal can be read but cannot be approved without matching global context',async()=>{
 proposals=[proposal()]
 await act(async()=>root.render(<AIWorkspace client={client} context={{patient_id:'',encounter_id:''}}/>))
 await act(async()=>{const row=document.querySelector<HTMLButtonElement>('.proposal-list .record-button');assert.ok(row);assert.match(row.textContent!,/AI ตรวจข้อความสังเคราะห์แล้ว/);row.click()})
 const approve=button('อนุมัติรุ่นที่แสดง');assert.equal(approve.disabled,true)
 assert.match(document.body.textContent!,/เลือกผู้ป่วยและการรับบริการที่ตรงกับข้อเสนอนี้/)
 assert.match(document.body.textContent!,/ผู้ป่วย: p1/);assert.equal(calls.some(c=>c.body),false)
})

test('changing patient context clears prior proposal and cannot retain actionable previous-subject review',async()=>{
 proposals=[proposal()];await mount();await act(async()=>{const row=document.querySelector<HTMLButtonElement>('.proposal-list .record-button');assert.ok(row);assert.match(row.textContent!,/AI ตรวจข้อความสังเคราะห์แล้ว/);row.click()})
 assert.equal(button('อนุมัติรุ่นที่แสดง').disabled,false)
 await act(async()=>root.render(<AIWorkspace client={client} context={{patient_id:'p2',encounter_id:'e2'}}/>))
 assert.equal(document.querySelector('textarea'),null);assert.doesNotMatch(document.body.textContent!,/AI ตรวจข้อความสังเคราะห์แล้ว/)
 assert.equal(calls.some(c=>c.body),false)
})
