import {test,beforeEach,afterEach} from 'node:test'
import assert from 'node:assert/strict'
import {JSDOM} from 'jsdom'
import React,{act} from 'react'
import type {Root} from 'react-dom/client'

const dom=new JSDOM('<!doctype html><html><body><div id="root"></div></body></html>',{url:'http://localhost:8000/home'})
for(const key of ['window','document','Event','CustomEvent','HTMLElement','HTMLInputElement','HTMLTextAreaElement','Node','location','history'])Object.defineProperty(globalThis,key,{configurable:true,value:(dom.window as any)[key]})
;(globalThis as any).IS_REACT_ACT_ENVIRONMENT=true
;(dom.window as any).matchMedia=()=>({matches:false,addEventListener(){},removeEventListener(){}})
const {createRoot}=await import('react-dom/client')
const session={user:{id:'refresh-reviewer',username:'synthetic-reviewer',display_name:'ผู้ทดสอบหน้าจอ',organization_id:'synthetic-org',facility_id:'synthetic-facility',roles:['clinician'],permissions:['*'],patient_scope:null},csrf_token:'synthetic-test-only',expires_at:'2099-01-01T00:00:00Z'}
let root:Root,requests:string[],customHandler:((path:string)=>unknown)|null=null
globalThis.fetch=async(url,init)=>{
 const path=String(url).replace('/api/v2/','');requests.push(path)
 assert.equal(init?.body,undefined,'Refresh navigation must not write records')
 const result=path==='auth/me'?session:customHandler?.(path)??(path==='home'?{open_tasks:0,items:[],domain_counts:Array.from({length:6},(_,index)=>({domain:'D0'+(index+1),record_count:10+index,pending_count:6-index,href:'/domains/D0'+(index+1),pending_states_rule:'authored synthetic count'}))}:{items:[]})
 return new Response(JSON.stringify(result))
}
const {default:App}=await import('../src/App')
beforeEach(()=>{document.body.innerHTML='<div id="root"></div>';history.replaceState({},'','/home');requests=[];customHandler=null;root=createRoot(document.getElementById('root')!)})
afterEach(async()=>{await act(async()=>root.unmount())})
async function mount(path='/home'){history.replaceState({},'',path);await act(async()=>root.render(<App/>))}

test('six-workspace workload exposes its omitted sixth row and can collapse again',async()=>{
 await mount()
 const heading=[...document.querySelectorAll('h2')].find(h=>h.textContent==='ปริมาณงานตามพื้นที่')
 assert.ok(heading)
 const section=heading.closest('section')!
 assert.equal(section.querySelectorAll('tbody tr').length,5)
 const toggle=section.querySelector<HTMLButtonElement>('button[aria-expanded]')!
 assert.ok(toggle,'The sixth row must have an accessible Show all control')
 assert.equal(toggle.getAttribute('aria-expanded'),'false')
 await act(async()=>toggle.click())
 assert.equal(toggle.getAttribute('aria-expanded'),'true')
 assert.equal(section.querySelectorAll('tbody tr').length,6)
 assert.match(section.querySelector('tbody')!.textContent!,/D06/)
 await act(async()=>toggle.click())
 assert.equal(toggle.getAttribute('aria-expanded'),'false')
 assert.equal(section.querySelectorAll('tbody tr').length,5)
 assert.doesNotMatch(section.querySelector('tbody')!.textContent!,/D06/)
})

test('D07 arrow keys select and focus the next tab without scrolling or losing the event target',async()=>{
 await mount('/domains/D07')
 const tabs=[...document.querySelectorAll<HTMLButtonElement>('[role=tab]')]
 assert.equal(tabs.length,2)
 assert.equal(tabs[0].getAttribute('aria-selected'),'true')
 tabs[0].focus()
 const right=new dom.window.KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true,cancelable:true})
 await act(async()=>{tabs[0].dispatchEvent(right);await new Promise(resolve=>setTimeout(resolve,20))})
 assert.equal(right.defaultPrevented,true)
 assert.equal(tabs[1].getAttribute('aria-selected'),'true')
 assert.equal(tabs[1].tabIndex,0)
 assert.equal(tabs[0].tabIndex,-1)
 assert.equal(document.activeElement,tabs[1])
 assert.ok(requests.includes('tasks'),'Selected task tab must load its own resource')
 const left=new dom.window.KeyboardEvent('keydown',{key:'ArrowLeft',bubbles:true,cancelable:true})
 await act(async()=>{tabs[1].dispatchEvent(left);await new Promise(resolve=>setTimeout(resolve,20))})
 assert.equal(left.defaultPrevented,true)
 assert.equal(tabs[0].getAttribute('aria-selected'),'true')
 assert.equal(document.activeElement,tabs[0])
 assert.ok(requests.includes('orders'),'Order resource remains reachable by keyboard')
})

test('home IDs are unique and workspace directory accessible name resolves to one heading',async()=>{
 await mount()
 const ids=[...document.querySelectorAll<HTMLElement>('[id]')].map(element=>element.id)
 assert.equal(new Set(ids).size,ids.length,'Duplicate IDs break label/reference targets')
 const directory=document.querySelector<HTMLElement>('.workspace-index[aria-labelledby]')!
 assert.ok(directory)
 const targetId=directory.getAttribute('aria-labelledby')!
 const targets=[...document.querySelectorAll('[id]')].filter(element=>element.id===targetId)
 assert.equal(targets.length,1)
 assert.equal(targets[0].tagName,'H2')
 assert.ok(targets[0].textContent?.trim())
})

test('home task destinations resolve the exact same-patient encounter and task, including history navigation',async()=>{
 customHandler=path=>path==='home'?{open_tasks:2,items:[{id:'task-a',title:'Work A',domain:'D37',patient_id:'p1',encounter_id:'e1',status:'open'},{id:'task-b',title:'Work B',domain:'D37',patient_id:'p1',encounter_id:'e2',status:'in_progress'}]}:
 path==='patients'?{items:[{id:'p1',display_name:'Synthetic patient'}]}:
 path.startsWith('encounters?')?{items:[{id:'e1',patient_id:'p1',kind:'OPD',status:'in_consult'},{id:'e2',patient_id:'p1',kind:'OPD',status:'in_consult'}]}:
 path.startsWith('tasks')?{items:[{id:'task-a',title:'Work A',kind:'document_review',patient_id:'p1',encounter_id:'e1',status:'open'},{id:'task-b',title:'Work B',kind:'document_review',patient_id:'p1',encounter_id:'e2',status:'in_progress'}]}:
 path==='ai/config'?{active_provider:'mock_demo',demo:true,live_routes_enabled:false,supported_task_kinds:['document_review']}:null
 await mount()
 const clickText=async(text:string)=>{const b=[...document.querySelectorAll('button')].find(x=>x.textContent===text);assert.ok(b);await act(async()=>b.click())}
 await clickText('Work A')
 assert.equal(document.querySelectorAll<HTMLSelectElement>('.patient-context select')[1].value,'e1')
 assert.equal(document.querySelector<HTMLSelectElement>('.ai-intake select')!.value,'task-a')
 await clickText('ภาพรวมงาน')
 await clickText('Work B')
 assert.equal(document.querySelectorAll<HTMLSelectElement>('.patient-context select')[1].value,'e2')
 assert.equal(document.querySelector<HTMLSelectElement>('.ai-intake select')!.value,'task-b')
 assert.ok(requests.includes('tasks?encounter_id=e2'))
 await act(async()=>{history.replaceState({},'','/domains/D37?task_id=task-a&patient_id=p1&encounter_id=e1');window.dispatchEvent(new dom.window.PopStateEvent('popstate'))})
 // History navigation re-resolves from URL through the same scoped context inputs.
 assert.equal(document.querySelectorAll<HTMLSelectElement>('.patient-context select')[1].value,'e1')
 assert.equal(document.querySelector<HTMLSelectElement>('.ai-intake select')!.value,'task-a')
})

test('home task search and status filters affect actual loaded records without mutations',async()=>{
 customHandler=path=>path==='home'?{open_tasks:2,items:[{id:'a',title:'Alpha record',domain:'D37',status:'open'},{id:'b',title:'Beta record',domain:'D37',status:'completed'}]}:null
 await mount()
 const query=document.querySelector<HTMLInputElement>('.task-filters input')!
 await act(async()=>{Object.getOwnPropertyDescriptor(dom.window.HTMLInputElement.prototype,'value')!.set!.call(query,'Beta');query.dispatchEvent(new dom.window.Event('input',{bubbles:true}));query.dispatchEvent(new dom.window.Event('change',{bubbles:true}))})
 assert.match(document.querySelector('.task-register')!.textContent!,/Beta record/);assert.doesNotMatch(document.querySelector('.task-register')!.textContent!,/Alpha record/)
 const filter=document.querySelector<HTMLSelectElement>('.task-filters select')!
 await act(async()=>{Object.getOwnPropertyDescriptor(dom.window.HTMLSelectElement.prototype,'value')!.set!.call(filter,'open');filter.dispatchEvent(new dom.window.Event('change',{bubbles:true}))})
 assert.match(document.body.textContent!,/ไม่พบงานตามตัวกรอง/)
})

test('mobile navigation contains keyboard focus and makes the underlying work surface inert',async()=>{
 ;(dom.window as any).matchMedia=()=>({matches:true,addEventListener(){},removeEventListener(){}})
 await mount()
 const trigger=document.querySelector<HTMLButtonElement>('[aria-controls=app-navigation]')!
 await act(async()=>trigger.click())
 const panel=document.querySelector<HTMLElement>('#app-navigation')!
 assert.ok(panel.contains(document.activeElement))
 assert.equal(document.querySelector('main')?.hasAttribute('inert'),true)
 const links=[...panel.querySelectorAll<HTMLElement>('a[href],button:not(:disabled),input:not(:disabled),select:not(:disabled),[tabindex="0"]')]
 links[links.length-1].focus()
 await act(async()=>document.dispatchEvent(new dom.window.KeyboardEvent('keydown',{key:'Tab',bubbles:true,cancelable:true})))
 assert.equal(document.activeElement,links[0])
 await act(async()=>{document.dispatchEvent(new dom.window.KeyboardEvent('keydown',{key:'Escape',bubbles:true,cancelable:true}));await new Promise(resolve=>setTimeout(resolve,20))})
 assert.equal(document.activeElement,trigger);assert.equal(document.querySelector('main')?.hasAttribute('inert'),false)
 ;(dom.window as any).matchMedia=()=>({matches:false,addEventListener(){},removeEventListener(){}})
})
