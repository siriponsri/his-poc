import {test,beforeEach,afterEach} from 'node:test'
import assert from 'node:assert/strict'
import {JSDOM} from 'jsdom'
import React,{act} from 'react'
import type {Root} from 'react-dom/client'

const dom=new JSDOM('<!doctype html><html><body><div id="root"></div></body></html>',{url:'http://localhost:8000/home'})
for(const key of ['window','document','Event','CustomEvent','HTMLElement','HTMLInputElement','HTMLTextAreaElement','Node','location','history'])Object.defineProperty(globalThis,key,{configurable:true,value:(dom.window as any)[key]})
;(globalThis as any).IS_REACT_ACT_ENVIRONMENT=true
;(dom.window as any).scrollTo=()=>{}
;(dom.window as any).matchMedia=()=>({matches:false,addEventListener(){},removeEventListener(){}})
const {createRoot}=await import('react-dom/client')
const {Client}=await import('../src/lib/client')
const {LangProvider}=await import('../src/lib/i18n')
const {Home}=await import('../src/components/home-workspace')
const {PatientRecordPanel}=await import('../src/components/patient-record-panel')
const {ResourceWorkspace}=await import('../src/components/workspace')
const {patientResource}=await import('../src/components/core-workspaces')

const patient={id:'p1',display_name:'นาง มาลี วัฒนกุล',birth_date:'1980-01-01',sex:'female',status:'active',version:2,identifiers:[{issuer:'CAREBALANCE_DEMO',value:'06901425'}]}
const minimum={id:patient.id,display_name:patient.display_name,status:patient.status}
const visit={id:'e1',patient_id:'p1',kind:'OPD',status:'in_consult',version:1,created_at:'2026-11-14T12:00:00Z'}
const minimumVisit={id:visit.id,patient_id:visit.patient_id,kind:visit.kind,status:visit.status,version:visit.version}
const documentRow={id:'doc1',patient_id:'p1',encounter_id:'e1',title:'บันทึกตรวจติดตาม',status:'draft',content:'Authored fictional source for display tests.'}
const task={id:'task1',patient_id:'p1',encounter_id:'e1',domain:'D37',kind:'document_review',title:'ทบทวนบันทึกตรวจติดตาม',status:'open'}
const referenceSession={user:{id:'display-user',username:'display-user',display_name:'Fictional reviewer',organization_id:'org',facility_id:'facility',roles:['clinician'],permissions:['patient.reference','encounter.reference','D22.read','D37.read'],patient_scope:null},csrf_token:'test-only',expires_at:'2099-01-01T00:00:00Z'}
const fullSession={...referenceSession,user:{...referenceSession.user,permissions:[...referenceSession.user.permissions,'D01.read','D03.read']}}
let root:Root,requests:string[],session=fullSession
globalThis.fetch=async(url,init)=>{
 const path=String(url).replace('/api/v2/','');requests.push(path)
 assert.equal(init?.body,undefined,'Patient display must not mutate a record or invoke AI')
 const result=path==='auth/me'?session:path==='patients'?{items:[patient]}:path==='patients/p1'?patient:path==='reference/patients'?{items:[minimum]}:path==='home'?{tasks:[task],domain_counts:[]}:path.startsWith('documents')?{items:[documentRow]}:path.startsWith('tasks')?{items:[task]}:path.startsWith('encounters')?{items:[visit]}:path.startsWith('reference/encounters')?{items:[minimumVisit]}:{items:[]}
 return new Response(JSON.stringify(result))
}
const client=new Client((url,init)=>globalThis.fetch(url,init))
const {default:App}=await import('../src/App')
beforeEach(()=>{document.body.innerHTML='<div id="root"></div>';history.replaceState({},'','/home');requests=[];session=fullSession;root=createRoot(document.getElementById('root')!)})
afterEach(async()=>{await act(async()=>root.unmount())})

test('authorized patient context and selector show actual HN, completed age and sex without changing option identity',async()=>{
 history.replaceState({},'','/domains/D03?patient_id=p1&encounter_id=e1')
 await act(async()=>root.render(<App/>))
 const facts=document.querySelector('.context-facts')!.textContent!
 assert.match(facts,/HN 06901425/);assert.match(facts,new RegExp(String(new Date().getFullYear()-1980)+' ปี'));assert.match(facts,/หญิง/)
 const option=document.querySelector<HTMLOptionElement>('.patient-context option[value="p1"]')!
 assert.equal(option.value,'p1');assert.match(option.textContent!,/มาลี.*HN 06901425/)
 assert.equal(new URL(location.href).searchParams.get('patient_id'),'p1');assert.equal(new URL(location.href).searchParams.get('encounter_id'),'e1')
 assert.ok(requests.includes('patients'));assert.ok(!requests.includes('reference/patients'))
})
test('full D01 patient panel prefers authorized demographics even when minimum-reference permission is also present',async()=>{
 const paths:string[]=[]
 await act(async()=>root.render(<LangProvider><PatientRecordPanel client={client} session={fullSession} request={{patient_id:'p1',encounter_id:'e1',document_id:'doc1'}} onClose={()=>{}} onNavigate={path=>paths.push(path)}/></LangProvider>))
 const header=document.querySelector('.patient-record-dialog-header')!.textContent!
 assert.match(header,/มาลี/);assert.match(header,/HN 06901425/);assert.match(header,/หญิง/);assert.match(header,new RegExp(String(new Date().getFullYear()-1980)+' ปี'))
 assert.ok(requests.includes('patients'));assert.ok(!requests.includes('reference/patients'))
 assert.ok(requests.includes('encounters?patient_id=p1'));assert.ok(!requests.includes('reference/encounters?patient_id=p1'))
 assert.match(header,/OPD/);assert.doesNotMatch(header,/\be1\b/)
 assert.equal(document.querySelector('.patient-record-source-heading p')!.getAttribute('title'),'e1')
 await act(async()=>[...document.querySelectorAll<HTMLButtonElement>('button')].find(button=>button.textContent==='Open document')!.click())
 const target=new URL(paths[0],'http://localhost');assert.equal(target.searchParams.get('patient_id'),'p1');assert.equal(target.searchParams.get('encounter_id'),'e1');assert.equal(target.searchParams.get('record'),'doc1')
})
test('minimum-reference Home and panel do not request or manufacture HN, age or sex',async()=>{
 await act(async()=>root.render(<LangProvider><Home client={client} session={referenceSession} navigate={()=>{}} onOpenPatient={()=>{}}/></LangProvider>))
 assert.ok(requests.includes('reference/patients'));assert.ok(!requests.includes('patients'))
 assert.match(document.querySelector('.preview-subject')!.textContent!,/มาลี/)
 assert.doesNotMatch(document.querySelector('.preview-subject')!.textContent!,/06901425|หญิง|\d+ ปี/)
 await act(async()=>root.render(<LangProvider><PatientRecordPanel client={client} session={referenceSession} request={{patient_id:'p1',encounter_id:'e1'}} onClose={()=>{}} onNavigate={()=>{}}/></LangProvider>))
 assert.doesNotMatch(document.querySelector('.patient-record-dialog-header')!.textContent!,/06901425|หญิง|\d+ ปี/)
 assert.ok(!requests.some(path=>path==='patients'||path.startsWith('patients/')))
})
test('authorized Home queue and preview use stored identifiers while patient registry retains its real record ID',async()=>{
 await act(async()=>root.render(<LangProvider><Home client={client} session={fullSession} navigate={()=>{}} onOpenPatient={()=>{}}/></LangProvider>))
 assert.ok(requests.includes('patients'));assert.ok(!requests.includes('reference/patients'))
 assert.match(document.querySelector('.task-reference')!.textContent!,/มาลี.*HN 06901425.*หญิง/)
 assert.match(document.querySelector('.preview-subject')!.textContent!,/HN 06901425/)
 await act(async()=>root.render(<LangProvider><ResourceWorkspace client={client} resource={patientResource} context={{patient_id:'',encounter_id:''}}/></LangProvider>))
 const record=document.querySelector<HTMLButtonElement>('.record-button')!
 assert.match(record.textContent!,/มาลี.*HN 06901425.*หญิง/)
 await act(async()=>record.click())
 assert.match(document.querySelector('.record-ref')!.textContent!,/HN 06901425/)
 assert.equal(document.querySelector('.record-ref span')!.getAttribute('title'),'p1')
})
