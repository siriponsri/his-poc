import {test,beforeEach,afterEach} from 'node:test'
import assert from 'node:assert/strict'
import {JSDOM} from 'jsdom'
import React,{act} from 'react'
import type {Root} from 'react-dom/client'
import {Client} from '../src/lib/client'
import {DRReviewPanel} from '../src/components/dr-review-panel'

const dom=new JSDOM('<!doctype html><html><body></body></html>',{url:'http://localhost:8080/domains/D11'})
for(const key of ['window','document','Event','CustomEvent','HTMLElement','HTMLInputElement','HTMLSelectElement','Node','location','history'])Object.defineProperty(globalThis,key,{configurable:true,value:(dom.window as any)[key]})
;(globalThis as any).IS_REACT_ACT_ENVIRONMENT=true
const {createRoot}=await import('react-dom/client')
const context={patient_id:'patient-one',encounter_id:'visit-one'}
const source={id:'image-right',...context,version:3,status:'released',file_sha256:'a'.repeat(64),modality:'CFP'}
const registered=(id='image-right',eye='R')=>({source_id:id,source_version:3,provenance_id:'provenance-'+id,laterality:eye,modality:'CFP',source_origin:'SYNTHETIC',label:'Authored '+eye+' image',preview_url:'/api/v2/integrations/dr/sources/'+id+'/preview?provenance_id=provenance-'+id})
const reviewTask={id:'review-task',...context,domain:'D11',kind:'dr_screening_review',title:'Review these images',status:'open'}
const imageSet={id:'image-set',...context,task_id:'review-task',revision:1,destination_id:'carebalance-dr-his-poc',availability:'provisioned',sources:[{source_id:'image-right',source_version:3,image_sha256:'a'.repeat(64),laterality:'R',modality:'CFP'}]}
const linked={id:'binding-one',state:'imported',workspace_url:'/integrations/dr/binding-one/app/',pending:null}
const transfer={confirmed:true,wording_version:'carebalance.dr-transfer.v2',purpose:'manual-dr-screening'}
let root:Root,calls:any[],closed:number,images:any[],sets:any[],tasks:any[],bindings:any[],handler:(path:string,body:any,init:any)=>any
const client=new Client(async(url,init)=>{const path=String(url).replace('/api/v2/',''),body=init?.body?JSON.parse(String(init.body)):undefined;calls.push({path,body,init});const result=await handler(path,body,init);return result instanceof Response?result:new Response(JSON.stringify(result??{}))})
function base(path:string){
 if(path.startsWith('integrations/dr/sources?'))return {items:images}
 if(path.startsWith('integrations/dr/source-sets?'))return {items:sets}
 if(path==='integrations/dr/source-sets/image-set')return {...imageSet,bindings}
 if(path==='integrations/dr/bindings/binding-one')return {...linked,binding_id:'binding-one',...context,source_set:{id:'image-set'}}
 if(path.startsWith('tasks?'))return {items:tasks}
 if(path==='reference/patients')return {items:[{id:context.patient_id,display_name:'Synthetic patient one'}]}
 if(path.startsWith('reference/encounters?'))return {items:[{id:context.encounter_id,patient_id:context.patient_id,kind:'OPD'}]}
 return {items:[]}
}
beforeEach(()=>{document.body.innerHTML='<div id="background"><button id="opener">Open image review</button></div><div id="root"></div>';document.querySelector<HTMLButtonElement>('#opener')!.focus();root=createRoot(document.querySelector('#root')!);calls=[];closed=0;images=[registered()];sets=[imageSet];tasks=[reviewTask];bindings=[];handler=(path)=>base(path)})
afterEach(async()=>{await act(async()=>root.unmount())})
async function mount(props:Partial<React.ComponentProps<typeof DRReviewPanel>>={}){await act(async()=>root.render(<DRReviewPanel client={client} source={source} context={context} onClose={()=>{closed++}} {...props}/>))}
function button(label:string){const value=[...document.querySelectorAll<HTMLButtonElement>('button')].find(node=>node.textContent===label||node.getAttribute('aria-label')===label);assert.ok(value,'button '+label);return value}
async function click(label:string){const value=button(label);assert.equal(value.disabled,false,'enabled '+label);await act(async()=>value.click())}
async function agree(){const input=document.querySelector<HTMLInputElement>('.labclear-review-confirm-person input');assert.ok(input);await act(async()=>input.click())}
const posts=()=>calls.filter(call=>call.init?.method==='POST')

test('DR launcher refuses mismatched context before reading or sending any source',async()=>{
 await mount({source:{...source,patient_id:'foreign-patient'}})
 assert.match(document.querySelector('[role=alert]')!.textContent!,/ตรงกับภาพ/);assert.equal(calls.length,0)
})
test('unregistered and falsely labelled uploads never become transferable synthetic images',async()=>{
 images=[{...registered(),source_origin:'HOSPITAL'}];sets=[];await mount()
 assert.ok(document.querySelector('[role=alert]'));assert.doesNotMatch(document.body.textContent!,/ยังไม่มีภาพสังเคราะห์ที่ลงทะเบียน/)
 assert.equal(document.querySelector('.dr-review-image'),null);assert.equal(posts().length,0)
})

test('registered public images retain their dataset attribution and require explicit manual transfer consent',async()=>{
 images=[{...registered(),source_origin:'PUBLIC',dataset_provenance:{dataset_title:'MMRDR',dataset_url:'https://figshare.com/articles/dataset/MMRDR/29423747',license_id:'CC-BY-4.0',attribution:'Tang et al. (2025), MMRDR, figshare.'}}];sets=[];await mount()
 assert.match(document.body.textContent!,/MMRDR · Public dataset · CC BY 4.0/)
 assert.match(document.body.textContent!,/Tang et al/)
 assert.equal(document.querySelector<HTMLImageElement>('.dr-review-image img')?.alt,'Right eye public dataset source')
 assert.equal(posts().length,0)
 const consent=document.querySelector('.labclear-review-confirm-person')!
 assert.match(consent.textContent!,/ไม่อนุญาตให้เรียกโมเดล/)
})
test('existing current-session review opens without another import and restores focus on close',async()=>{
 bindings=[linked];await mount()
 assert.equal(document.querySelector<HTMLAnchorElement>('.dr-review-open')?.getAttribute('href'),linked.workspace_url)
 assert.equal(posts().length,0);assert.equal(document.querySelector('#background')?.hasAttribute('inert'),true)
 assert.equal(document.activeElement?.getAttribute('aria-label'),'Close DR review')
 await act(async()=>document.dispatchEvent(new dom.window.KeyboardEvent('keydown',{key:'Escape',bubbles:true})))
 assert.equal(closed,1);await act(async()=>root.render(<></>))
 assert.equal(document.querySelector('#background')?.hasAttribute('inert'),false);assert.equal(document.activeElement?.id,'opener')
})
test('failed source loading remains an error rather than a false empty registry',async()=>{
 handler=path=>path.startsWith('integrations/dr/sources?')?new Response('{"detail":{"code":"PERMISSION_DENIED"}}',{status:403}):base(path)
 await mount();assert.match(document.querySelector('[role=alert]')!.textContent!,/ไม่มีสิทธิ์/);assert.doesNotMatch(document.body.textContent!,/ยังไม่มีภาพสังเคราะห์ที่ลงทะเบียน/);assert.equal(posts().length,0)
})
test('foreign source-set metadata is rejected instead of displaying another context',async()=>{
 sets=[{...imageSet,patient_id:'foreign'}];await mount();assert.ok(document.querySelector('[role=alert]'));assert.equal(document.querySelector('.dr-review-open'),null);assert.equal(posts().length,0)
})
test('read-only account can open its existing review but exposes no source mutation controls',async()=>{
 bindings=[linked];await mount({readOnly:true})
 assert.ok(document.querySelector('.dr-review-open'));assert.equal(document.querySelector('.labclear-review-confirm-person'),null)
 assert.equal([...document.querySelectorAll('button')].some(node=>node.textContent==='สร้างงานทบทวนภาพ'),false);assert.equal(posts().length,0)
})
test('unprovisioned source set is shown honestly and cannot send bytes',async()=>{
 sets=[{...imageSet,availability:'unavailable'}];await mount();await agree()
 assert.equal(button('ส่งภาพและเตรียมเปิดการตรวจ').disabled,true);assert.match(document.body.textContent!,/ผู้ดูแลต้องเปิดพื้นที่ตรวจเฉพาะชุดนี้/)
 assert.equal(posts().length,0)
})
test('source transfer requires explicit agreement and sends exact consent without image bytes or browser identity',async()=>{
 handler=(path,body)=>path==='integrations/dr/source-sets/image-set/bindings'&&body?{binding_id:linked.id,outcome:'succeeded'}:base(path)
 await mount();assert.equal(button('ส่งภาพและเตรียมเปิดการตรวจ').disabled,true)
 await agree();await click('ส่งภาพและเตรียมเปิดการตรวจ')
 const sent=posts();assert.equal(sent.length,1);assert.deepEqual(sent[0].body,{transfer_consent:transfer})
 assert.ok(sent[0].init.headers['Idempotency-Key']);assert.equal(document.querySelector('.dr-review-open')?.getAttribute('href'),linked.workspace_url)
 assert.doesNotMatch(JSON.stringify(sent[0].body),/image_base64|actor_id|session_id|password/)
})
test('definitive receiver rejection does not become a successful launch or indefinite unknown state',async()=>{
 handler=(path,body)=>path.endsWith('/bindings')&&body?{binding_id:linked.id,outcome:'rejected'}:base(path)
 await mount();await agree();await click('ส่งภาพและเตรียมเปิดการตรวจ')
 assert.equal(document.querySelector('.dr-review-open'),null);assert.match(document.querySelector('[role=alert]')!.textContent!,/คำสั่งถูกปฏิเสธ/)
 assert.equal([...document.querySelectorAll('button')].some(node=>node.textContent==='ตรวจด้วยคำสั่งเดิม'),false)
 await click('ปิด');assert.equal(closed,1)
})
test('202 unknown outcome retains the exact key/body and blocks close until same-command confirmation',async()=>{
 let attempts=0;handler=(path,body)=>path.endsWith('/bindings')&&body?(++attempts===1?new Response(JSON.stringify({binding_id:linked.id,outcome:'unknown'}),{status:202}):{binding_id:linked.id,outcome:'succeeded'}):base(path)
 await mount();await agree();await click('ส่งภาพและเตรียมเปิดการตรวจ');assert.equal(button('ปิด').disabled,true);assert.equal(closed,0)
 assert.equal(document.querySelector('.dr-review-open'),null);await click('ตรวจด้วยคำสั่งเดิม')
 const sent=posts();assert.equal(sent.length,2);assert.equal(sent[0].init.headers['Idempotency-Key'],sent[1].init.headers['Idempotency-Key']);assert.deepEqual(sent[0].body,sent[1].body)
 assert.ok(document.querySelector('.dr-review-open'))
})
test('durable UNKNOWN permits explicit safe exit while leaving the original request in server recovery',async()=>{
 handler=(path,body)=>path.endsWith('/bindings')&&body?new Response(JSON.stringify({binding_id:linked.id,outcome:'unknown'}),{status:202}):base(path)
 await mount();await agree();await click('ส่งภาพและเตรียมเปิดการตรวจ')
 assert.equal(button('ปิด').disabled,true);await click('ปิดและเก็บคำสั่งที่รอตรวจ');assert.equal(closed,1)
 assert.equal(posts().length,1);assert.ok(posts()[0].init.headers['Idempotency-Key'])
})
test('an imported workspace with pending clinical mutation stays open for read-only inspection',async()=>{
 bindings=[{...linked,pending:{operation:'dispatch'}}];await mount()
 const link=document.querySelector<HTMLAnchorElement>('.dr-review-open')!;assert.equal(link.getAttribute('href'),linked.workspace_url);assert.equal(link.textContent,'Open review (read only)')
 assert.match(document.body.textContent!,/มีคำสั่งเดิมที่ยังรอตรวจผล/);assert.equal(posts().length,0)
})
test('network loss retains one original command for an explicit safe retry',async()=>{
 let attempts=0;handler=(path,body)=>{if(path.endsWith('/bindings')&&body){if(++attempts===1)throw Error('lost response');return {binding_id:linked.id,outcome:'succeeded'}}return base(path)}
 await mount();await agree();await click('ส่งภาพและเตรียมเปิดการตรวจ');await click('ตรวจด้วยคำสั่งเดิม')
 const sent=posts();assert.equal(sent.length,2);assert.equal(sent[0].init.headers['Idempotency-Key'],sent[1].init.headers['Idempotency-Key']);assert.ok(document.querySelector('.dr-review-open'))
})
test('a late transfer response cannot reopen a workspace after source scope changes',async()=>{
 let settle:(value:any)=>void=()=>{};handler=(path,body)=>path.endsWith('/bindings')&&body?new Promise(resolve=>{settle=resolve}):base(path)
 await mount();await agree();await click('ส่งภาพและเตรียมเปิดการตรวจ')
 await mount({source:{...source,patient_id:'foreign-patient'}})
 await act(async()=>settle({binding_id:linked.id,outcome:'succeeded'}))
 assert.equal(document.querySelector('.dr-review-open'),null);assert.match(document.querySelector('[role=alert]')!.textContent!,/ตรงกับภาพ/)
 assert.equal(calls.some(call=>call.path==='integrations/dr/bindings/binding-one'),false)
 await click('ปิด');assert.equal(closed,1)
})
test('refresh discovers durable pending import and recovery never auto-replays',async()=>{
 bindings=[{...linked,state:'unknown',pending:{operation:'import'}}]
 handler=(path,body)=>path==='integrations/dr/bindings/binding-one/recover'?{binding_id:linked.id,automatic_replay:false,commands:[{operation:'import',key:'original-durable-key',body:{transfer_consent:transfer},retry_allowed:true}]}:path.endsWith('/bindings')&&body?{binding_id:linked.id,outcome:'succeeded'}:base(path)
 await mount();assert.equal(posts().length,0);await click('ตรวจคำสั่งที่รออยู่')
 assert.equal(posts().filter(call=>call.path.endsWith('/bindings')).length,0);await click('ตรวจด้วยคำสั่งเดิม')
 assert.equal(posts().find(call=>call.path.endsWith('/bindings'))!.init.headers['Idempotency-Key'],'original-durable-key');assert.ok(document.querySelector('.dr-review-open'))
})
test('foreign or external workspace URLs and external preview references are never followed',async()=>{
 images=[{...registered(),preview_url:'https://foreign.example/private.png'}];bindings=[{...linked,workspace_url:'https://foreign.example/app'}]
 await mount();assert.equal(document.querySelector('.dr-review-open'),null);assert.equal(document.querySelector('.dr-review-image img'),null)
 assert.ok(document.querySelector('[role=alert]'));assert.equal(posts().length,0)
})
test('new review task and image set are explicit typed steps, without automatic transfer or source-order completion',async()=>{
 sets=[];tasks=[];handler=(path,body)=>path==='tasks'&&body?{...reviewTask,...body}:path==='integrations/dr/source-sets'&&body?{...imageSet,availability:'unavailable'}:base(path)
 await mount();await click('สร้างงานทบทวนภาพ');await agree();await click('จัดชุดภาพสำหรับตรวจ')
 const sent=posts();assert.equal(sent.length,2);assert.equal(sent[0].body.kind,'dr_screening_review');assert.equal(sent[0].body.domain,'D11')
 assert.deepEqual(sent[1].body.sources,[{source_id:'image-right',source_version:3,provenance_id:'provenance-image-right'}]);assert.deepEqual(sent[1].body.transfer_consent,transfer)
 assert.equal(sent[1].body.destination_id,'carebalance-dr-his-poc');assert.equal(sent.some(call=>call.path.endsWith('/bindings')||call.path.includes('clinical/')),false)
})
