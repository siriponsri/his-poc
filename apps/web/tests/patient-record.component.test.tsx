import {test,beforeEach,afterEach} from 'node:test'
import assert from 'node:assert/strict'
import {JSDOM} from 'jsdom'
import React,{act,useState} from 'react'
import type {Root} from 'react-dom/client'

const dom=new JSDOM('<!doctype html><html><body><div id="root"></div></body></html>',{url:'http://localhost:8000/home'})
for(const key of ['window','document','Event','CustomEvent','HTMLElement','HTMLInputElement','HTMLTextAreaElement','Node','location','history'])Object.defineProperty(globalThis,key,{configurable:true,value:(dom.window as any)[key]})
;(globalThis as any).IS_REACT_ACT_ENVIRONMENT=true
const {createRoot}=await import('react-dom/client')
const {PatientRecordPanel}=await import('../src/components/patient-record-panel')
const {LangProvider}=await import('../src/lib/i18n')
const {Client}=await import('../src/lib/client')
const client=new Client((url,init)=>globalThis.fetch(url,init))
const session={user:{id:'limited-reviewer',username:'reviewer',display_name:'Synthetic reviewer',organization_id:'org',facility_id:'facility',roles:['clinician'],permissions:['D22.read','D37.read','patient.reference','encounter.reference'],patient_scope:null},csrf_token:'test-only',expires_at:'2099-01-01T00:00:00Z'}
const doc={id:'doc-a',title:'Full reading source',patient_id:'p1',encounter_id:'e1',content:'COMPLETE SOURCE TEXT '.repeat(120),content_access:'allowed',version:2,status:'draft'}
const task={id:'task-a',title:'Review selected record',patient_id:'p1',encounter_id:'e1',domain:'D37',kind:'document_review',status:'open'}
let root:Root,requests:string[],navigations:string[],handler:(path:string)=>unknown
globalThis.fetch=async(url,init)=>{const path=String(url).replace('/api/v2/','');requests.push(path);assert.equal(init?.body,undefined,'Patient record is read-only and cannot call inference');const data=await handler(path);return data instanceof Response?data:new Response(JSON.stringify(data))}
beforeEach(()=>{document.body.innerHTML='<div id="root"></div>';history.replaceState({},'','/home');requests=[];navigations=[];handler=path=>path==='reference/patients'?{items:[{id:'p1',display_name:'Patient One'},{id:'p2',display_name:'Patient Two'}]}:path.startsWith('reference/encounters')?{items:[{id:'e1',patient_id:'p1',kind:'OPD',status:'in_consult'}]}:path.startsWith('documents')?{items:[doc]}:path.startsWith('tasks')?{items:[task]}:{items:[]};root=createRoot(document.getElementById('root')!)})
afterEach(async()=>{await act(async()=>root.unmount())})
const request={patient_id:'p1',encounter_id:'e1',task_id:'task-a',document_id:'doc-a'}
async function render(next=request){await act(async()=>root.render(<LangProvider><PatientRecordPanel client={client} session={session} request={next} onClose={()=>{}} onNavigate={path=>navigations.push(path)}/></LangProvider>))}

test('wide patient record reads complete source with minimum reference permission and exact workspace navigation',async()=>{
 await render()
 const dialog=document.querySelector('[role=dialog]')!
 assert.equal(dialog.getAttribute('aria-modal'),'true')
 assert.match(document.getElementById(dialog.getAttribute('aria-labelledby')!)!.textContent!,/Patient One/)
 assert.equal(dialog.querySelector('.document-content')!.textContent,doc.content)
 assert.ok(requests.includes('reference/patients'));assert.ok(!requests.includes('patients'))
 assert.ok(document.getElementById('root')!.hasAttribute('inert'))
 const review=[...dialog.querySelectorAll<HTMLButtonElement>('button')].find(button=>button.textContent?.includes('Open review'))!
 await act(async()=>review.click())
 const target=new URL(navigations[0],'http://localhost')
 assert.equal(target.pathname,'/domains/D37')
 assert.equal(target.searchParams.get('patient_id'),'p1');assert.equal(target.searchParams.get('encounter_id'),'e1')
 assert.equal(target.searchParams.get('task_id'),'task-a');assert.equal(target.searchParams.get('document_id'),'doc-a')
 assert.ok(requests.every(path=>!path.includes('proposals')))
})

test('patient dialog traps focus, closes with Escape, restores trigger and previous inert state',async()=>{
 function Harness(){const [open,setOpen]=useState(false);return <><button id="patient-opener" onClick={()=>setOpen(true)}>Patient One</button>{open&&<PatientRecordPanel client={client} session={session} request={request} onClose={()=>setOpen(false)} onNavigate={()=>setOpen(false)}/>}</>}
 const preserved=document.createElement('div');preserved.id='already-inert';preserved.setAttribute('inert','');document.body.append(preserved)
 await act(async()=>root.render(<LangProvider><Harness/></LangProvider>))
 const opener=document.getElementById('patient-opener')!;opener.focus();await act(async()=>opener.click())
 const dialog=document.querySelector('[role=dialog]')!
 assert.equal(document.activeElement?.getAttribute('aria-label'),'Close patient record')
 const controls=[...dialog.querySelectorAll<HTMLElement>('button:not(:disabled),select:not(:disabled)')]
 controls[controls.length-1].focus()
 const forward=new dom.window.KeyboardEvent('keydown',{key:'Tab',bubbles:true,cancelable:true});document.dispatchEvent(forward)
 assert.equal(forward.defaultPrevented,true);assert.equal(document.activeElement,controls[0])
 const backward=new dom.window.KeyboardEvent('keydown',{key:'Tab',shiftKey:true,bubbles:true,cancelable:true});document.dispatchEvent(backward)
 assert.equal(document.activeElement,controls[controls.length-1])
 await act(async()=>document.dispatchEvent(new dom.window.KeyboardEvent('keydown',{key:'Escape',bubbles:true,cancelable:true})))
 assert.equal(document.querySelector('[role=dialog]'),null);assert.equal(document.activeElement,opener)
 assert.equal(document.getElementById('root')!.hasAttribute('inert'),false);assert.equal(preserved.hasAttribute('inert'),true)
})

test('a late patient A response cannot replace patient B data or enable patient A actions',async()=>{
 let resolveA:(value:unknown)=>void=()=>{}
 handler=path=>path==='documents?encounter_id=e1'?new Promise(resolve=>{resolveA=resolve}):path==='documents?encounter_id=e2'?{items:[{...doc,id:'doc-b',patient_id:'p2',encounter_id:'e2',content:'ONLY SOURCE B'}]}:path==='reference/patients'?{items:[{id:'p1',display_name:'Patient One'},{id:'p2',display_name:'Patient Two'}]}:{items:[]}
 await render()
 assert.ok(document.querySelector('[role=status]'))
 await render({patient_id:'p2',encounter_id:'e2',document_id:'doc-b',task_id:''})
 assert.match(document.querySelector('[role=dialog]')!.textContent!,/ONLY SOURCE B/)
 await act(async()=>resolveA({items:[doc]}))
 const dialog=document.querySelector('[role=dialog]')!
 assert.match(dialog.textContent!,/ONLY SOURCE B/);assert.doesNotMatch(dialog.textContent!,/COMPLETE SOURCE TEXT|Patient One/)
 assert.equal([...dialog.querySelectorAll('button')].some(button=>button.textContent?.includes('Open review')),false)
})

test('denied document load is an explicit error, not an empty record or actionable source',async()=>{
 handler=path=>path.startsWith('documents')?new Response('{"detail":"DOCUMENTS_DENIED"}',{status:403}):{items:[]}
 await render()
 const dialog=document.querySelector('[role=dialog]')!
 assert.match(dialog.querySelector('[role=alert]')!.textContent!,/Documents:.*ไม่มีสิทธิ์/)
 assert.doesNotMatch(dialog.textContent!,/No documents in this context|ยังไม่มีเอกสารในบริบทนี้/)
 assert.equal([...dialog.querySelectorAll<HTMLButtonElement>('button')].find(button=>button.textContent==='Open document')!.disabled,true)
 assert.equal(dialog.querySelector('.document-content'),null)
})

test('metadata-only and cross-subject documents never leak source text or select an invalid requested document',async()=>{
 handler=path=>path.startsWith('documents')?{items:[{...doc,content:null,content_access:'metadata_only'},{...doc,id:'cross',patient_id:'p2',content:'CROSS PATIENT SECRET'}]}:{items:[]}
 await render()
 assert.match(document.querySelector('[role=dialog]')!.textContent!,/ไม่มีสิทธิ์อ่านเนื้อหา/)
 assert.doesNotMatch(document.querySelector('[role=dialog]')!.textContent!,/CROSS PATIENT SECRET/)
 await render({...request,document_id:'cross'})
 assert.match(document.querySelector('[role=dialog]')!.textContent!,/เอกสารที่เปิดไว้ไม่อยู่ในบริบทนี้/)
 assert.equal(document.querySelector('.document-content'),null)
 assert.equal([...document.querySelectorAll<HTMLButtonElement>('[role=dialog] button')].find(button=>button.textContent==='Open document')!.disabled,true)
})

test('visits disclosure participates in focus containment when the role has no document actions',async()=>{
 const referenceOnly={...session,user:{...session.user,permissions:['patient.reference','encounter.reference']}}
 await act(async()=>root.render(<LangProvider><PatientRecordPanel client={client} session={referenceOnly} request={request} onClose={()=>{}} onNavigate={()=>{}}/></LangProvider>))
 const close=document.querySelector<HTMLButtonElement>('[aria-label="Close patient record"]')!
 const summary=document.querySelector<HTMLElement>('.patient-record-visits summary')!
 assert.ok(summary)
 close.focus();document.dispatchEvent(new dom.window.KeyboardEvent('keydown',{key:'Tab',shiftKey:true,bubbles:true,cancelable:true}))
 assert.equal(document.activeElement,summary)
 document.dispatchEvent(new dom.window.KeyboardEvent('keydown',{key:'Tab',bubbles:true,cancelable:true}))
 assert.equal(document.activeElement,close)
 assert.equal(requests.some(path=>path.startsWith('documents')||path.startsWith('tasks')),false)
})

test('an unavailable requested task stays unselected instead of silently substituting another task',async()=>{
 await render({...request,task_id:'unavailable-task'})
 const dialog=document.querySelector('[role=dialog]')!
 assert.equal(dialog.querySelector<HTMLSelectElement>('.patient-record-task-choice select')!.value,'')
 assert.equal([...dialog.querySelectorAll('button')].some(button=>button.textContent?.includes('Open review')),false)
 const select=dialog.querySelector<HTMLSelectElement>('.patient-record-task-choice select')!
 await act(async()=>{Object.getOwnPropertyDescriptor(dom.window.HTMLSelectElement.prototype,'value')!.set!.call(select,'task-a');select.dispatchEvent(new dom.window.Event('change',{bubbles:true}))})
 assert.ok([...dialog.querySelectorAll('button')].some(button=>button.textContent?.includes('Open review')))
})
