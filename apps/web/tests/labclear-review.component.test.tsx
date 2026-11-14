import {test,beforeEach,afterEach} from 'node:test'
import assert from 'node:assert/strict'
import {JSDOM} from 'jsdom'
import React,{act,useState} from 'react'
import type {Root} from 'react-dom/client'

const dom=new JSDOM('<!doctype html><html><body><div id="root"></div></body></html>',{url:'http://localhost:8000/domains/D10'})
for(const key of ['window','document','Event','CustomEvent','HTMLElement','HTMLInputElement','Node','location','history','localStorage'])Object.defineProperty(globalThis,key,{configurable:true,value:(dom.window as any)[key]})
;(globalThis as any).IS_REACT_ACT_ENVIRONMENT=true
const {createRoot}=await import('react-dom/client')
const {LabClearReviewPanel}=await import('../src/components/labclear-review-panel')
const {LangProvider}=await import('../src/lib/i18n')
const {Client}=await import('../src/lib/client')
const client=new Client((url,init)=>globalThis.fetch(url,init))
const context={patient_id:'p1',encounter_id:'e1'}
const source={id:'lab1',version:3,status:'released',patient_id:'p1',encounter_id:'e1',analyte:'ALT',result_value:' 42 ',unit:'U/L',reference_range:'0–40'}
const task={id:'task1',title:'LabClear review ALT',domain:'D10',kind:'labclear_review',status:'open',...context}
const binding={id:'binding1',connector:'labclear',...context,task_id:'task1',source_id:'lab1',source_version:3,source_sha256:'a'.repeat(64),external_report_id:'external1',state:'draft',created_at:'2026-11-14T10:00:00Z'}
const cells=[{source_index:0,name:'ALT',value:'42',unit:'U/L',reference:'0–40',printed_flag:''}]
const draft={state:'draft',source:{domain:'D10',record_id:'lab1',version:3,sha256:'a'.repeat(64)},fields:cells,review:null}
const success=(receipt:any=draft)=>({binding:{...binding,state:receipt.state},attempt_id:'attempt1',outcome:'succeeded',receipt})
let root:Root,calls:{path:string;body:any;key:string|undefined}[],handler:(path:string,body:any)=>unknown,closed:number
globalThis.fetch=async(url,init)=>{
 const path=String(url).replace('/api/v2/',''),body=init?.body?JSON.parse(String(init.body)):undefined
 calls.push({path,body,key:(init?.headers as any)?.['Idempotency-Key']})
 const result=await handler(path,body)
 return result instanceof Response?result:new Response(JSON.stringify(result))
}
beforeEach(()=>{document.body.innerHTML='<div id="root"></div>';localStorage.setItem('his-display-language','en');calls=[];closed=0;handler=(path)=>path.startsWith('integrations/labclear/bindings?')?{available:true,items:[]}:path.startsWith('tasks?')?{items:[task]}:path==='integrations/labclear/import'?success():path.endsWith('/recover')?{binding,pending:null,retry_allowed:false}:path==='reference/patients'?{items:[{id:'p1',display_name:'Synthetic Patient One'}]}:path==='reference/encounters?patient_id=p1'?{items:[{id:'e1',patient_id:'p1',kind:'OPD'}]}:{items:[]};root=createRoot(document.getElementById('root')!)})
afterEach(async()=>{await act(async()=>root.unmount())})
async function render(nextSource=source,nextContext=context){await act(async()=>root.render(<LangProvider><LabClearReviewPanel client={client} source={nextSource} context={nextContext} onClose={()=>closed++}/></LangProvider>))}
const button=(text:string)=>[...document.querySelectorAll<HTMLButtonElement>('button')].find(element=>element.textContent===text)!
async function click(text:string){const element=button(text);assert.ok(element,text);assert.equal(element.disabled,false,text+' must be enabled');await act(async()=>element.click())}
async function fill(label:string,value:string){const input=document.querySelector<HTMLInputElement>('input[aria-label="'+label+'"]')!;assert.ok(input,label);await act(async()=>{Object.getOwnPropertyDescriptor(dom.window.HTMLInputElement.prototype,'value')!.set!.call(input,value);input.dispatchEvent(new dom.window.Event('input',{bubbles:true}))})}
async function samePerson(){await act(async()=>document.querySelector<HTMLInputElement>('input[type=checkbox]')!.click())}

test('released source is exact, no import or human confirmation occurs on open',async()=>{
 await render()
 assert.equal(document.querySelector('[role=dialog]')!.getAttribute('aria-modal'),'true')
 assert.equal([...document.querySelectorAll('.labclear-source-cells dd')][1].textContent,' 42 ')
 assert.ok(calls.every(call=>call.body===undefined))
 assert.equal(button('Send released values').disabled,false)
 await click('Send released values')
 assert.equal(calls.filter(call=>call.path==='integrations/labclear/import').length,1)
 assert.equal(calls.find(call=>call.path==='integrations/labclear/import')!.body.source_version,3)
 assert.equal(button('Confirm reviewed values').disabled,true)
 assert.equal(calls.some(call=>call.path.endsWith('/confirm')),false)
})

test('explicit task creation precedes source transfer and never reuses the completed order task',async()=>{
 const base=handler
 handler=(path,body)=>path.startsWith('tasks?')?{items:[{...task,id:'order-task',kind:'order',status:'completed'}]}:path==='tasks'?task:base(path,body)
 await render()
 assert.equal(button('Send released values').disabled,true)
 assert.equal(calls.some(call=>call.path==='tasks'),false)
 await click('Create review task')
 const created=calls.find(call=>call.path==='tasks')!
 assert.equal(created.body.kind,'labclear_review');assert.equal(created.body.domain,'D10')
 assert.deepEqual({patient_id:created.body.patient_id,encounter_id:created.body.encounter_id},context)
 await click('Send released values')
 assert.equal(calls.find(call=>call.path==='integrations/labclear/import')!.body.task_id,'task1')
 assert.equal(calls.some(call=>call.path.includes('transition')||call.path.includes('actions')),false)
})

test('202 import preserves one payload and key, blocks dismissal, then retries the original request',async()=>{
 let attempts=0;const base=handler
 handler=(path,body)=>path==='integrations/labclear/import'?(++attempts===1?{binding,receipt:null,outcome:'unknown',retry_same_key:true}:success()):base(path,body)
 await render();await click('Send released values')
 assert.equal(document.querySelector<HTMLButtonElement>('[aria-label="Close LabClear review"]')!.disabled,true)
 await act(async()=>document.dispatchEvent(new dom.window.KeyboardEvent('keydown',{key:'Escape',bubbles:true,cancelable:true})))
 assert.equal(closed,0)
 await click('Retry the same request')
 const imports=calls.filter(call=>call.path==='integrations/labclear/import')
 assert.equal(imports.length,2);assert.equal(imports[0].key,imports[1].key);assert.deepEqual(imports[0].body,imports[1].body)
 assert.equal(document.querySelector<HTMLButtonElement>('[aria-label="Close LabClear review"]')!.disabled,false)
 assert.equal(calls.some(call=>call.path.endsWith('/confirm')),false)
})

test('unknown network outcome retains the original import command',async()=>{
 let attempts=0;const base=handler
 handler=(path,body)=>{if(path==='integrations/labclear/import'&&++attempts===1)throw Error('connection lost');return base(path,body)}
 await render();await click('Send released values');await click('Retry the same request')
 const requests=calls.filter(call=>call.path==='integrations/labclear/import')
 assert.equal(requests[0].key,requests[1].key)
 assert.equal(button('Confirm reviewed values').disabled,true)
})

test('confirmation binds explicit reviewed cells to the source and becomes immutable after readback',async()=>{
 let confirmed:any=null;const base=handler
 handler=(path,body)=>{
  if(path.endsWith('/confirm')){confirmed={...draft,state:'confirmed',fields:body.fields,review:{reviewer_id:'human1',revision:1,sha256:'b'.repeat(64)}};return success(confirmed)}
  if(path.endsWith('/read'))return success(confirmed)
  return base(path,body)
 }
 await render();await click('Send released values');await samePerson();await fill('Value row 1','43')
 assert.equal(document.querySelector<HTMLInputElement>('input[type=checkbox]')!.checked,false)
 assert.equal(button('Confirm reviewed values').disabled,true)
 await samePerson();await click('Confirm reviewed values')
 const submitted=calls.find(call=>call.path.endsWith('/confirm'))!
 assert.equal(submitted.body.source_version,3);assert.equal(submitted.body.source_sha256,'a'.repeat(64))
 assert.equal(submitted.body.same_person_confirmed,true);assert.equal(submitted.body.fields[0].source_index,0);assert.equal(submitted.body.fields[0].value,'43')
 assert.equal(document.querySelector('fieldset')!.disabled,true)
 assert.equal(button('Confirm reviewed values'),undefined)
 await click('Check latest review')
 assert.equal(document.querySelector<HTMLInputElement>('input[aria-label="Value row 1"]')!.value,'43')
 assert.match(document.body.textContent!,/Confirmed review/)
})

test('existing confirmed binding opens through scoped read without creating a task or another report',async()=>{
 const confirmed={...draft,state:'confirmed',review:{reviewer_id:'human1',revision:1,sha256:'b'.repeat(64)}}
 const base=handler;handler=(path,body)=>path.startsWith('integrations/labclear/bindings?')?{available:true,items:[binding]}:path.endsWith('/read')?success(confirmed):base(path,body)
 await render();await click('Open existing review')
 assert.equal(calls.filter(call=>call.path.endsWith('/read')).length,1)
 assert.equal(calls.some(call=>call.path==='tasks'||call.path.endsWith('/import')||call.path.endsWith('/confirm')),false)
 assert.match(document.body.textContent!,/Confirmed review/)
})

test('confirmed historical review reads directly after its task and visit close without write-scoped recovery',async()=>{
 const confirmed={...draft,state:'confirmed',review:{reviewer_id:'human1',revision:1,sha256:'b'.repeat(64)}}
 const saved={...binding,state:'confirmed'},base=handler
 handler=(path,body)=>path.startsWith('integrations/labclear/bindings?')?{available:true,items:[saved]}:path.startsWith('tasks?')?{items:[{...task,status:'completed'}]}:path==='reference/encounters?patient_id=p1'?{items:[{id:'e1',patient_id:'p1',kind:'OPD',status:'closed'}]}:path.endsWith('/read')?success(confirmed):path.endsWith('/recover')?new Response('{"detail":{"code":"CONNECTOR_TARGET_CLOSED"}}',{status:409}):base(path,body)
 await render();await click('Open existing review')
 assert.match(document.body.textContent!,/Confirmed review/)
 assert.equal(document.querySelector<HTMLFieldSetElement>('fieldset')!.disabled,true)
 assert.equal(button('Confirm reviewed values'),undefined)
 assert.equal(document.querySelector('input[type=checkbox]'),null)
 await click('Check latest review')
 assert.equal(calls.filter(call=>call.path.endsWith('/read')).length,2)
 assert.equal(calls.some(call=>call.path.endsWith('/recover')||call.path.endsWith('/import')||call.path.endsWith('/confirm')||call.path==='tasks'),false)
})

test('draft saved by a completed review task is view only and does not require recovery',async()=>{
 const base=handler
 handler=(path,body)=>path.startsWith('integrations/labclear/bindings?')?{available:true,items:[binding]}:path.startsWith('tasks?')?{items:[{...task,status:'completed'}]}:path.endsWith('/read')?success():base(path,body)
 await render();await click('Open existing review')
 assert.match(document.body.textContent!,/Saved review/)
 assert.doesNotMatch(document.body.textContent!,/Confirmed review/)
 assert.equal(document.querySelector<HTMLFieldSetElement>('fieldset')!.disabled,true)
 assert.equal(button('Confirm reviewed values'),undefined)
 assert.equal(calls.some(call=>call.path.endsWith('/recover')||call.path.endsWith('/confirm')),false)
})

test('closed visit keeps an existing draft readable but hides all confirmation controls',async()=>{
 const base=handler
 handler=(path,body)=>path.startsWith('integrations/labclear/bindings?')?{available:true,items:[binding]}:path==='reference/encounters?patient_id=p1'?{items:[{id:'e1',patient_id:'p1',kind:'OPD',status:'closed'}]}:path.endsWith('/read')?success():base(path,body)
 await render();await click('Open existing review')
 assert.match(document.body.textContent!,/Saved review/)
 assert.equal(document.querySelector<HTMLFieldSetElement>('fieldset')!.disabled,true)
 assert.equal(document.querySelector('input[type=checkbox]'),null)
 assert.equal(button('Confirm reviewed values'),undefined)
 assert.equal(calls.some(call=>call.path.endsWith('/recover')||call.path.endsWith('/confirm')),false)
})

test('disabled connector and cross-context source cannot send values',async()=>{
 handler=path=>path.startsWith('integrations/labclear/bindings?')?{available:false,items:[]}:{items:[task]}
 await render();assert.match(document.body.textContent!,/not connected/);assert.equal(button('Send released values'),undefined)
 calls=[];await render({...source,patient_id:'p2'})
 assert.equal(calls.length,0);assert.match(document.querySelector('[role=alert]')!.textContent!,/unavailable/)
 assert.doesNotMatch(document.body.textContent!,/Printed value/)
})

test('foreign tasks and bindings never become actionable',async()=>{
 handler=path=>path.startsWith('integrations/labclear/bindings?')?{available:true,items:[{...binding,patient_id:'foreign'}]}:{items:[{...task,encounter_id:'foreign'},{...task,id:'task2',domain:'D37'},{...task,id:'task3',status:'completed'}]}
 await render()
 assert.equal(button('Open existing review'),undefined)
 assert.ok(button('Create review task'));assert.equal(button('Send released values').disabled,true)
 assert.doesNotMatch(document.body.textContent!,/foreign/)
})

test('a late patient A response cannot populate patient B review',async()=>{
 let resolveA:(value:any)=>void=()=>{}
 handler=path=>path.startsWith('integrations/labclear/bindings?patient_id=p1')?new Promise(resolve=>resolveA=resolve):path.startsWith('integrations/')?{available:false,items:[]}:{items:[]}
 await render()
 await render({...source,id:'lab2',patient_id:'p2',encounter_id:'e2',analyte:'Patient B test'}, {patient_id:'p2',encounter_id:'e2'})
 await act(async()=>resolveA({available:true,items:[binding]}))
 assert.match(document.body.textContent!,/Patient B test/);assert.doesNotMatch(document.body.textContent!,/ALT|Open existing review/)
 assert.equal(button('Send released values'),undefined)
})

test('mismatched mutation receipt cannot expose or enable another source',async()=>{
 const base=handler;handler=(path,body)=>path.endsWith('/import')?{...success(),binding:{...binding,patient_id:'foreign'},receipt:{...draft,fields:[{...cells[0],value:'FOREIGN SECRET'}]}}:base(path,body)
 await render();await click('Send released values')
 assert.doesNotMatch(document.body.textContent!,/FOREIGN SECRET/)
 assert.equal(document.querySelector('fieldset'),null)
 assert.ok(button('Retry the same request'))
})

test('modal contains focus, Escape restores trigger and preserves existing inert state',async()=>{
 function Harness(){const [open,setOpen]=useState(false);return <><button id="trigger" onClick={()=>setOpen(true)}>Review source</button>{open&&<LabClearReviewPanel client={client} source={source} context={context} onClose={()=>setOpen(false)}/>}</>}
 const inert=document.createElement('div');inert.setAttribute('inert','');document.body.append(inert)
 await act(async()=>root.render(<LangProvider><Harness/></LangProvider>))
 const trigger=document.getElementById('trigger')!;trigger.focus();await act(async()=>trigger.click())
 const close=document.querySelector<HTMLButtonElement>('[aria-label="Close LabClear review"]')!
 assert.equal(document.activeElement,close);assert.ok(document.getElementById('root')!.hasAttribute('inert'))
 const buttons=[...document.querySelectorAll<HTMLButtonElement>('[role=dialog] button:not(:disabled)')]
 buttons[buttons.length-1].focus();document.dispatchEvent(new dom.window.KeyboardEvent('keydown',{key:'Tab',bubbles:true,cancelable:true}));assert.equal(document.activeElement,close)
 await act(async()=>document.dispatchEvent(new dom.window.KeyboardEvent('keydown',{key:'Escape',bubbles:true,cancelable:true})))
 assert.equal(document.querySelector('[role=dialog]'),null);assert.equal(document.activeElement,trigger);assert.equal(document.getElementById('root')!.hasAttribute('inert'),false);assert.ok(inert.hasAttribute('inert'))
})

test('scoped reference names are primary and optional lookup denial never grants or blocks transfer',async()=>{
 await render()
 assert.match(document.querySelector('.labclear-review-context')!.textContent!,/Synthetic Patient One.*OPD/)
 assert.doesNotMatch(document.querySelector('.labclear-review-context')!.textContent!,/p1|e1/)
 const base=handler;handler=(path,body)=>path.startsWith('reference/')?new Response('{"detail":{"code":"PERMISSION_DENIED"}}',{status:403}):base(path,body)
 await render({...source,id:'lab2'})
 assert.match(document.querySelector('.labclear-review-context')!.textContent!,/Selected patient.*Current visit/)
 assert.doesNotMatch(document.querySelector('.labclear-review-context')!.textContent!,/Synthetic Patient One/)
 assert.equal(button('Send released values').disabled,false)
})

test('failed initial workspace load has an explicit retry and is not reported as a disabled connector',async()=>{
 let loads=0;const base=handler
 handler=(path,body)=>{if(path.startsWith('integrations/labclear/bindings?')&&++loads===1)throw Error('offline');return base(path,body)}
 await render()
 assert.doesNotMatch(document.body.textContent!,/not connected/)
 await click('Try loading the review workspace again')
 assert.equal(button('Send released values').disabled,false)
 assert.equal(calls.some(call=>call.path==='integrations/labclear/import'),false)
})

test('unknown read is retried as a fresh authorized read without a mutation key lock',async()=>{
 let reads=0;const base=handler
 handler=(path,body)=>path.startsWith('integrations/labclear/bindings?')?{available:true,items:[binding]}:path.endsWith('/read')?(++reads===1?{binding,receipt:null,outcome:'unknown',retry_same_key:false}:success()):base(path,body)
 await render();await click('Open existing review')
 assert.equal(document.querySelector<HTMLButtonElement>('[aria-label="Close LabClear review"]')!.disabled,false)
 assert.equal(button('Retry the same request'),undefined)
 await click('Open existing review')
 assert.equal(calls.filter(call=>call.path.endsWith('/read')).length,2)
 assert.ok(button('Confirm reviewed values'))
 assert.equal(calls.some(call=>call.path.endsWith('/import')||call.path.endsWith('/confirm')),false)
})

test('known gateway rejection permits recovery while a generic service failure keeps the original command',async()=>{
 let code='LABCLEAR_REQUEST_REJECTED';let status=502;const base=handler
 handler=(path,body)=>path.endsWith('/import')?new Response(JSON.stringify({detail:{code}}),{status}):base(path,body)
 await render();await click('Send released values')
 assert.doesNotMatch(document.querySelector('[role=alert]')!.textContent!,/LABCLEAR_REQUEST_REJECTED/)
 assert.equal(button('Retry the same request'),undefined)
 assert.equal(document.querySelector<HTMLButtonElement>('[aria-label="Close LabClear review"]')!.disabled,false)
 code='UPSTREAM_UNKNOWN';status=503
 await click('Send released values')
 assert.doesNotMatch(document.querySelector('[role=alert]')!.textContent!,/UPSTREAM_UNKNOWN/)
 assert.ok(button('Retry the same request'))
 assert.equal(document.querySelector<HTMLButtonElement>('[aria-label="Close LabClear review"]')!.disabled,true)
})

test('existing read cannot replace the selected binding with another same-context review',async()=>{
 const base=handler;handler=(path,body)=>path.startsWith('integrations/labclear/bindings?')?{available:true,items:[binding]}:path.endsWith('/read')?{...success(),binding:{...binding,id:'other-binding'},receipt:{...draft,fields:[{...cells[0],value:'UNEXPECTED VALUES'}]}}:base(path,body)
 await render();await click('Open existing review')
 assert.match(document.querySelector('[role=alert]')!.textContent!,/does not match/)
 assert.doesNotMatch(document.body.textContent!,/UNEXPECTED VALUES/)
 assert.equal(document.querySelector('fieldset'),null)
})

test('page-reopened unknown import restores the original command without automatically resending it',async()=>{
 const body={...context,task_id:'task1',source_id:'lab1',source_version:3}
 const restored={kind:'import',method:'POST',path:'integrations/labclear/import',key:'original-import-key',body,lease_expires_at:null}
 const unknownBinding={...binding,state:'unknown',external_report_id:null};const base=handler
 handler=(path,payload)=>path.startsWith('integrations/labclear/bindings?')?{available:true,items:[unknownBinding]}:path.endsWith('/recover')?{binding:unknownBinding,pending:restored,retry_allowed:true}:base(path,payload)
 await render();await click('Open existing review')
 assert.equal(calls.some(call=>call.path.endsWith('/read')||call.path.endsWith('/import')||call.path.endsWith('/confirm')),false)
 assert.match(document.body.textContent!,/unresolved request was restored/)
 assert.equal(document.querySelector<HTMLButtonElement>('[aria-label="Close LabClear review"]')!.disabled,true)
 await click('Retry the same request')
 const sent=calls.find(call=>call.path.endsWith('/import'))!
 assert.equal(sent.key,restored.key);assert.deepEqual(sent.body,body)
 assert.equal(calls.some(call=>call.path.endsWith('/confirm')),false)
})

test('an active restored lease requires an explicit status check before same-command retry',async()=>{
 const body={...context,task_id:'task1',source_id:'lab1',source_version:3}
 let recoveries=0;const base=handler
 handler=(path,payload)=>path.startsWith('integrations/labclear/bindings?')?{available:true,items:[binding]}:path.endsWith('/recover')?{binding,pending:{kind:'import',method:'POST',path:'integrations/labclear/import',key:'leased-import-key',body,lease_expires_at:'2026-11-14T11:00:00Z'},retry_allowed:++recoveries>1}:base(path,payload)
 await render();await click('Open existing review')
 assert.equal(button('Retry the same request').disabled,true)
 await click('Check pending request')
 assert.equal(button('Retry the same request').disabled,false)
 assert.equal(calls.some(call=>call.path.endsWith('/import')),false)
 await click('Retry the same request')
 assert.equal(calls.find(call=>call.path.endsWith('/import'))!.key,'leased-import-key')
})

test('restored confirmation displays the exact previous reviewed values read-only and resumes only on request',async()=>{
 const reviewed=[{...cells[0],value:'43'}]
 const body={fields:reviewed,same_person_confirmed:true,source_version:3,source_sha256:'a'.repeat(64)}
 const base=handler
 handler=(path,payload)=>path.startsWith('integrations/labclear/bindings?')?{available:true,items:[binding]}:path.endsWith('/recover')?{binding,pending:{kind:'confirm',method:'POST',path:'integrations/labclear/bindings/binding1/confirm',key:'original-confirm-key',body,lease_expires_at:null},retry_allowed:true}:path.endsWith('/confirm')?success({...draft,state:'confirmed',fields:reviewed,review:{reviewer_id:'human1',revision:1,sha256:'b'.repeat(64)}}):base(path,payload)
 await render();await click('Open existing review')
 assert.match(document.body.textContent!,/Pending reviewed values/)
 assert.equal(document.querySelector<HTMLInputElement>('input[aria-label="Value row 1"]')!.value,'43')
 assert.equal(document.querySelector<HTMLFieldSetElement>('fieldset')!.disabled,true)
 assert.equal(calls.some(call=>call.path.endsWith('/confirm')||call.path.endsWith('/import')),false)
 await click('Retry the same request')
 const sent=calls.find(call=>call.path.endsWith('/confirm'))!
 assert.equal(sent.key,'original-confirm-key');assert.deepEqual(sent.body,body)
 assert.match(document.body.textContent!,/Confirmed review/)
})

test('foreign recovered command is never displayed or executed',async()=>{
 const base=handler
 handler=(path,payload)=>path.startsWith('integrations/labclear/bindings?')?{available:true,items:[binding]}:path.endsWith('/recover')?{binding,pending:{kind:'confirm',method:'POST',path:'integrations/labclear/bindings/foreign/confirm',key:'foreign-key',body:{fields:[{...cells[0],value:'FOREIGN SECRET'}],same_person_confirmed:true,source_version:3,source_sha256:'a'.repeat(64)}},retry_allowed:true}:base(path,payload)
 await render();await click('Open existing review')
 assert.match(document.querySelector('[role=alert]')!.textContent!,/does not match/)
 assert.doesNotMatch(document.body.textContent!,/FOREIGN SECRET/)
 assert.equal(button('Retry the same request'),undefined)
 assert.equal(calls.some(call=>call.path.endsWith('/confirm')),false)
})

test('another-tab pending fence reloads its binding then waits for explicit command recovery',async()=>{
 let lists=0,imports=0;const originalBody={...context,task_id:'task1',source_id:'lab1',source_version:3};const base=handler
 handler=(path,payload)=>{
  if(path.startsWith('integrations/labclear/bindings?'))return {available:true,items:++lists===1?[]:[binding]}
  if(path.endsWith('/import')&&++imports===1)return new Response('{"detail":{"code":"CONNECTOR_PENDING_RECOVERY_REQUIRED","binding_id":"binding1"}}',{status:409})
  if(path.endsWith('/recover'))return {binding,pending:{kind:'import',method:'POST',path:'integrations/labclear/import',key:'another-tab-original-key',body:originalBody},retry_allowed:true}
  return base(path,payload)
 }
 await render();await click('Send released values')
 assert.equal(calls.some(call=>call.path.endsWith('/recover')),false)
 assert.ok(button('Recover pending request'))
 await click('Recover pending request')
 assert.equal(calls.filter(call=>call.path.endsWith('/import')).length,1)
 await click('Retry the same request')
 const resumed=calls.filter(call=>call.path.endsWith('/import'))[1]
 assert.equal(resumed.key,'another-tab-original-key');assert.deepEqual(resumed.body,originalBody)
})
