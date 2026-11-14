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
 await clickText('Workspace')
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

test('Home preview reads the production top-level document DTO and never invents completed totals',async()=>{
 customHandler=path=>path==='home'?{open_tasks:1,items:[{id:'task-a',title:'Review source',domain:'D37',patient_id:'p1',encounter_id:'e1',status:'open'}]}:path==='documents'?{items:[{id:'doc-a',title:'Source A',patient_id:'p1',encounter_id:'e1',version:3,current_version_id:'v-source',content:'ข้อความต้นฉบับจาก DTO จริง',content_hash:'a'.repeat(64),content_access:'allowed',status:'draft'}]}:path==='patients'?{items:[{id:'p1',display_name:'ชื่อผู้ป่วยจากทะเบียน'}]}:null
 await mount()
 const preview=document.querySelector('.queue-preview')!
 assert.match(preview.textContent!,/ข้อความต้นฉบับจาก DTO จริง/)
 assert.match(preview.textContent!,/ชื่อผู้ป่วยจากทะเบียน/)
 assert.match(preview.textContent!,/Record v3/)
 assert.doesNotMatch(preview.textContent!,/ไม่มีสิทธิ์อ่านเนื้อหา|restricted/)
 assert.doesNotMatch(document.querySelector('.queue-tabs')!.textContent!,/Completed/)
})

test('Home metadata-only document stays readable without implying content access',async()=>{
 customHandler=path=>path==='home'?{open_tasks:0,items:[]}:path==='documents'?{items:[{id:'meta-doc',title:'Metadata only',patient_id:'p1',encounter_id:'e1',version:1,content:null,content_access:'metadata_only',status:'draft'}]}:null
 await mount()
 const preview=document.querySelector('.queue-preview')!
 assert.match(preview.textContent!,/Metadata only/)
 assert.match(preview.textContent!,/ไม่มีสิทธิ์อ่านเนื้อหา/)
 assert.equal(preview.querySelector('.source-excerpt>p')!.textContent!.includes('undefined'),false)
})

test('Home preview follows exact task patient and encounter without cross-visit source leakage',async()=>{
 customHandler=path=>path==='home'?{open_tasks:2,items:[{id:'task-a',title:'Task A',domain:'D37',patient_id:'p1',encounter_id:'e1',status:'open'},{id:'task-b',title:'Task B',domain:'D37',patient_id:'p1',encounter_id:'e2',status:'open'}]}:path==='documents'?{items:[{id:'doc-a',title:'Visit one source',patient_id:'p1',encounter_id:'e1',content:'PRIVATE VISIT ONE',content_access:'allowed',status:'draft'},{id:'doc-c',title:'Other patient source',patient_id:'p2',encounter_id:'e2',content:'PRIVATE OTHER PATIENT',content_access:'allowed',status:'draft'}]}:null
 await mount()
 assert.match(document.querySelector('.queue-preview')!.textContent!,/PRIVATE VISIT ONE/)
 await act(async()=>document.querySelector<HTMLButtonElement>('[aria-label="Preview Task B"]')!.click())
 assert.doesNotMatch(document.querySelector('.queue-preview')!.textContent!,/PRIVATE VISIT ONE|PRIVATE OTHER PATIENT/)
 assert.match(document.querySelector('.queue-preview')!.textContent!,/ยังไม่มีเอกสาร/)
 assert.ok([...document.querySelectorAll('.queue-preview button')].some(button=>button.textContent==='Open task'))
})

test('document patient context filters all-encounter list and rejects a mismatched authorized deep link',async()=>{
 const docA={id:'doc-a',title:'Patient A source',patient_id:'p1',encounter_id:'e1',content:'SOURCE FOR A',content_access:'allowed',status:'draft'}
 const docB={id:'doc-b',title:'Patient B source',patient_id:'p2',encounter_id:'e2',content:'SOURCE FOR B',content_access:'allowed',status:'draft'}
 customHandler=path=>path==='patients'?{items:[{id:'p1',display_name:'Patient A'},{id:'p2',display_name:'Patient B'}]}:path==='documents'?{items:[docA,docB]}:path==='documents/doc-b'?docB:path==='documents/doc-a'?docA:null
 await mount('/domains/D22?patient_id=p1&record=doc-b')
 assert.match(document.querySelector('.record-list')!.textContent!,/Patient A source/)
 assert.doesNotMatch(document.querySelector('.record-list')!.textContent!,/Patient B source/)
 assert.doesNotMatch(document.querySelector('.detail-card')!.textContent!,/SOURCE FOR B/)
 assert.match(document.body.textContent!,/เอกสารนี้ไม่ตรงกับผู้ป่วย/)
})

test('Open document preserves its explicit patient and encounter context through record navigation',async()=>{
 const doc={id:'doc-a',title:'Selected document',patient_id:'p1',encounter_id:'e1',content:'CURRENT CLINICAL SOURCE',content_access:'allowed',status:'draft',version:2,current_version_id:'v1'}
 customHandler=path=>path==='home'?{open_tasks:0,items:[]}:path==='patients'?{items:[{id:'p1',display_name:'Patient One'}]}:path.startsWith('encounters?')?{items:[{id:'e1',patient_id:'p1',kind:'OPD',status:'in_consult'}]}:path.startsWith('documents/')&&path.endsWith('/versions')?{items:[{id:'v1',version:1,content:'CURRENT CLINICAL SOURCE',created_by:'Authorized author',created_at:'2026-11-14T00:00:00Z'}]}:path==='documents/doc-a'?doc:path.startsWith('documents')?{items:[doc]}:null
 await mount()
 await act(async()=>[...document.querySelectorAll<HTMLButtonElement>('.queue-preview button')].find(button=>button.textContent?.includes('Open document'))!.click())
 const selectors=document.querySelectorAll<HTMLSelectElement>('.patient-context select')
 assert.equal(selectors[0].value,'p1');assert.equal(selectors[1].value,'e1')
 assert.match(document.querySelector('.document-reader')!.textContent!,/CURRENT CLINICAL SOURCE/)
 assert.match(document.querySelector('.document-author')!.textContent!,/Authorized author/)
 assert.equal(document.querySelector('.document-metadata')?.hasAttribute('open'),false)
})

test('patient and encounter selectors canonicalize the URL, remove stale record/task IDs and survive reload/history',async()=>{
 const docA={id:'doc-a',title:'Patient A source',patient_id:'p1',encounter_id:'e1',content:'SOURCE A',content_access:'allowed',status:'draft'}
 const docB={id:'doc-b',title:'Patient B source',patient_id:'p2',encounter_id:'e2',content:'SOURCE B',content_access:'allowed',status:'draft'}
 customHandler=path=>path==='patients'?{items:[{id:'p1',display_name:'Patient A'},{id:'p2',display_name:'Patient B'}]}:path==='encounters?patient_id=p1'?{items:[{id:'e1',patient_id:'p1',kind:'OPD',status:'in_consult'}]}:path==='encounters?patient_id=p2'?{items:[{id:'e2',patient_id:'p2',kind:'OPD',status:'in_consult'}]}:path==='documents/doc-a'?docA:path.startsWith('documents')&&!path.includes('/versions')?{items:[docA,docB]}:null
 await mount('/domains/D22?patient_id=p1&encounter_id=e1&record=doc-a&task_id=old-task&document_id=old-document')
 const selectValue=async(input:HTMLSelectElement,value:string)=>act(async()=>{Object.getOwnPropertyDescriptor(dom.window.HTMLSelectElement.prototype,'value')!.set!.call(input,value);input.dispatchEvent(new dom.window.Event('change',{bubbles:true}))})
 await selectValue(document.querySelectorAll<HTMLSelectElement>('.patient-context select')[0],'p2')
 assert.equal(location.search,'?patient_id=p2')
 assert.equal(document.querySelectorAll<HTMLSelectElement>('.patient-context select')[1].value,'')
 assert.doesNotMatch(document.querySelector('.record-list')!.textContent!,/Patient A source/)
 assert.match(document.querySelector('.record-list')!.textContent!,/Patient B source/)
 assert.doesNotMatch(document.body.textContent!,/เอกสารนี้ไม่ตรงกับผู้ป่วย/)
 await selectValue(document.querySelectorAll<HTMLSelectElement>('.patient-context select')[1],'e2')
 assert.equal(location.search,'?patient_id=p2&encounter_id=e2')
 const canonical=location.pathname+location.search
 await act(async()=>root.unmount());root=createRoot(document.getElementById('root')!);await mount(canonical)
 assert.equal(document.querySelectorAll<HTMLSelectElement>('.patient-context select')[0].value,'p2')
 assert.equal(document.querySelectorAll<HTMLSelectElement>('.patient-context select')[1].value,'e2')
 await act(async()=>{history.replaceState({},'','/domains/D22?patient_id=p1&encounter_id=e1&record=doc-a');window.dispatchEvent(new dom.window.PopStateEvent('popstate'))})
 assert.equal(document.querySelectorAll<HTMLSelectElement>('.patient-context select')[0].value,'p1')
 assert.equal(document.querySelectorAll<HTMLSelectElement>('.patient-context select')[1].value,'e1')
 assert.match(document.querySelector('.document-reader')!.textContent!,/SOURCE A/)
})

test('patient and visit record context actions use canonical reloadable URLs',async()=>{
 const patient={id:'p1',display_name:'Selected patient',status:'active',version:1}
 const encounter={id:'e1',patient_id:'p1',kind:'OPD',status:'in_consult',version:1}
 customHandler=path=>path==='patients'?{items:[patient]}:path==='patients/p1'?patient:path.startsWith('encounters?')?{items:[encounter]}:path==='encounters/e1'?encounter:null
 await mount('/domains/D01')
 await act(async()=>document.querySelector<HTMLButtonElement>('.record-list .record-button')!.click())
 await act(async()=>document.querySelector<HTMLButtonElement>('.actions-bar .primary')!.click())
 assert.equal(location.pathname+location.search,'/domains/D03?patient_id=p1')
 await act(async()=>document.querySelector<HTMLButtonElement>('.record-list .record-button')!.click())
 await act(async()=>document.querySelector<HTMLButtonElement>('.actions-bar .primary')!.click())
 assert.equal(location.pathname+location.search,'/domains/D03?patient_id=p1&encounter_id=e1')
 const canonical=location.pathname+location.search
 await act(async()=>root.unmount());root=createRoot(document.getElementById('root')!);await mount(canonical)
 const selectors=document.querySelectorAll<HTMLSelectElement>('.patient-context select')
 assert.equal(selectors[0].value,'p1');assert.equal(selectors[1].value,'e1')
})

test('queue patient entry opens a wide read-only record and close retains queue search and focus',async()=>{
 const doc={id:'doc-b',title:'Beta source',patient_id:'p2',encounter_id:'e2',content:'FULL BETA SOURCE',content_access:'allowed',status:'draft'}
 customHandler=path=>path==='home'?{items:[{id:'a',title:'Alpha task',patient_id:'p1',encounter_id:'e1',domain:'D37',status:'open'},{id:'b',title:'Beta task',patient_id:'p2',encounter_id:'e2',domain:'D37',status:'open'}]}:path==='reference/patients'?{items:[{id:'p1',display_name:'Patient Alpha'},{id:'p2',display_name:'Patient Beta'}]}:path.startsWith('documents')?{items:[doc]}:null
 await mount()
 const input=document.querySelector<HTMLInputElement>('.task-filters input')!
 await act(async()=>{Object.getOwnPropertyDescriptor(dom.window.HTMLInputElement.prototype,'value')!.set!.call(input,'Beta');input.dispatchEvent(new dom.window.Event('input',{bubbles:true}));input.dispatchEvent(new dom.window.Event('change',{bubbles:true}))})
 const trigger=document.querySelector<HTMLButtonElement>('.task-reference .patient-record-link')!
 trigger.focus();await act(async()=>trigger.click())
 assert.ok(document.querySelector('.patient-record-dialog[role=dialog]'))
 assert.match(document.querySelector('[role=dialog]')!.textContent!,/FULL BETA SOURCE/)
 assert.equal(location.pathname+location.search,'/home')
 assert.equal(document.getElementById('root')!.hasAttribute('inert'),true)
 await act(async()=>document.dispatchEvent(new dom.window.KeyboardEvent('keydown',{key:'Escape',bubbles:true,cancelable:true})))
 assert.equal(document.querySelector('[role=dialog]'),null);assert.equal(document.activeElement,trigger)
 assert.equal(input.value,'Beta');assert.doesNotMatch(document.querySelector('.task-register')!.textContent!,/Alpha task/)
 assert.equal(document.getElementById('root')!.hasAttribute('inert'),false)
 assert.equal(requests.some(path=>path.includes('proposals')),false)
})

test('patient identity entry from review retains its exact URL task and document selection',async()=>{
 const doc={id:'doc-a',title:'Selected source',patient_id:'p1',encounter_id:'e1',content:'READING SOURCE',content_access:'allowed',status:'draft'}
 const tasks=[{id:'task-a',title:'Selected task',patient_id:'p1',encounter_id:'e1',domain:'D37',kind:'document_review',status:'open'},{id:'task-b',title:'Other task',patient_id:'p1',encounter_id:'e1',domain:'D37',kind:'document_review',status:'open'}]
 customHandler=path=>path==='patients'||path==='reference/patients'?{items:[{id:'p1',display_name:'Patient One'}]}:path.startsWith('encounters?')||path.startsWith('reference/encounters?')?{items:[{id:'e1',patient_id:'p1',kind:'OPD',status:'in_consult'}]}:path.startsWith('documents')?{items:[doc]}:path.startsWith('tasks')?{items:tasks}:path==='ai/config'?{active_provider:'mock_demo',demo:true,live_routes_enabled:false,supported_task_kinds:['document_review']}:null
 await mount('/domains/D37?patient_id=p1&encounter_id=e1&task_id=task-a&document_id=doc-a')
 await act(async()=>document.querySelector<HTMLButtonElement>('.patient-record-identity-link')!.click())
 const dialog=document.querySelector('[role=dialog]')!
 assert.match(dialog.querySelector('.patient-record-source-heading')!.textContent!,/Selected source/)
 assert.equal(dialog.querySelector<HTMLSelectElement>('.patient-record-task-choice select')!.value,'task-a')
 await act(async()=>[...dialog.querySelectorAll<HTMLButtonElement>('button')].find(button=>button.textContent?.includes('Open review'))!.click())
 assert.equal(document.querySelector('[role=dialog]'),null)
 const query=new URLSearchParams(location.search)
 assert.equal(query.get('task_id'),'task-a');assert.equal(query.get('document_id'),'doc-a')
 assert.equal(document.querySelectorAll<HTMLSelectElement>('.ai-intake select')[1].value,'doc-a')
})

test('explicit navigation resets viewport after rendering while history, patient panel and pending guards preserve scroll',async()=>{
 const doc={id:'doc-a',title:'Patient source',patient_id:'p1',encounter_id:'e1',content:'Source',content_access:'allowed',status:'draft'}
 customHandler=path=>path==='home'?{items:[{id:'task-a',title:'Review task',patient_id:'p1',encounter_id:'e1',domain:'D37',status:'open'}]}:path.startsWith('documents')?{items:[doc]}:null
 const previousScroll=dom.window.scrollTo,previousAlert=dom.window.alert
 const calls:{options:unknown;path:string;heading:string|null}[]=[],focusOptions:unknown[]=[]
 ;(dom.window as any).scrollTo=(options:unknown)=>calls.push({options,path:location.pathname,heading:document.querySelector('.page h1')?.textContent||null})
 ;(dom.window as any).alert=()=>{}
 try{
  await mount()
  const main=document.querySelector<HTMLElement>('.page')!,focus=main.focus.bind(main)
  main.focus=(options?:FocusOptions)=>{focusOptions.push(options);focus(options)}
  const documents=[...document.querySelectorAll<HTMLButtonElement>('.sidebar button')].find(button=>button.textContent==='Documents')!
  await act(async()=>{documents.click();await new Promise(resolve=>setTimeout(resolve,20))})
  assert.deepEqual(calls.at(-1),{options:{top:0,left:0,behavior:'instant'},path:'/domains/D22',heading:'Documents'})
  assert.deepEqual(focusOptions.at(-1),{preventScroll:true})
  const count=calls.length
  await act(async()=>{history.replaceState({},'','/home');window.dispatchEvent(new dom.window.PopStateEvent('popstate'))})
  assert.equal(calls.length,count,'Browser history must retain native scroll restoration')
  await act(async()=>document.querySelector<HTMLButtonElement>('.task-reference .patient-record-link')!.click())
  assert.ok(document.querySelector('[role=dialog]'));assert.equal(calls.length,count)
  await act(async()=>document.dispatchEvent(new dom.window.KeyboardEvent('keydown',{key:'Escape',bubbles:true,cancelable:true})))
  assert.equal(calls.length,count,'Opening and closing a patient record cannot reset the queue scroll')
  await act(async()=>window.dispatchEvent(new dom.window.CustomEvent('his-pending',{detail:true})))
  await act(async()=>[...document.querySelectorAll<HTMLButtonElement>('.sidebar button')].find(button=>button.textContent==='Documents')!.click())
  assert.equal(location.pathname,'/home');assert.equal(calls.length,count,'A blocked navigation cannot reset scroll')
 }finally{dom.window.scrollTo=previousScroll;dom.window.alert=previousAlert}
})

test('session expiry renders Sign in before resetting the viewport to its header',async()=>{
 await mount('/domains/D22')
 const previousScroll=dom.window.scrollTo
 const calls:{path:string;loginVisible:boolean;options:unknown}[]=[]
 ;(dom.window as any).scrollTo=(options:unknown)=>calls.push({path:location.pathname,loginVisible:!!document.querySelector('.login-panel form'),options})
 try{
  await act(async()=>window.dispatchEvent(new dom.window.CustomEvent('his-session-expired')))
  assert.deepEqual(calls.at(-1),{path:'/login',loginVisible:true,options:{top:0,left:0,behavior:'instant'}})
 }finally{dom.window.scrollTo=previousScroll}
})
