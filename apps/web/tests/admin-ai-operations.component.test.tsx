import {test,beforeEach,afterEach} from 'node:test'
import assert from 'node:assert/strict'
import {JSDOM} from 'jsdom'
import React,{act} from 'react'
import type {Root} from 'react-dom/client'
import {Client,type Session} from '../src/lib/client'
import {validAIOperations,type AIOperations} from '../src/lib/team-operations'

const dom=new JSDOM('<!doctype html><html><body></body></html>',{url:'http://localhost/admin'})
for(const name of ['window','document','Event','CustomEvent','HTMLElement','HTMLSelectElement','Node','location','history'])Object.defineProperty(globalThis,name,{configurable:true,value:(dom.window as any)[name]})
;(globalThis as any).IS_REACT_ACT_ENVIRONMENT=true
const {createRoot}=await import('react-dom/client')
const {AdminAIOperations}=await import('../src/components/admin-ai-operations')
const session:Session={user:{id:'admin-a',username:'fictional-admin',display_name:'Authored administrator',organization_id:'org-a',facility_id:'facility-a',roles:['system_admin'],permissions:['D34.read','identity.admin'],patient_scope:null},csrf_token:'test-only',expires_at:'2099-01-01'}
const counts={queued:0,waiting_for_capacity:0,running:0,succeeded:5,failed:1,timeout:0,invalid_output:0,abstained:0,stale_context:0,interrupted:0,awaiting_review:3}
function data(overrides:Partial<AIOperations>={}):AIOperations{return {observed_at:'2026-11-15T00:00:00Z',scope:{organization_id:'org-a',facility_id:'facility-a'},provider:{enabled:true,configured:true,route:'named-private-route',model:'declared-model',model_digest:'declared-digest',engine_version:'declared-version',context_tokens:4096,max_output_tokens:512,declared_qualified_profiles:['visit_preparation'],live_status:'not_checked',selection_version:'excerpt-v2'},worker:{heartbeat_status:'not_observed',heartbeat_at:null,last_started_at:'2026-11-14T00:00:00Z',last_completed_at:'2026-11-14T00:01:00Z',persisted_running:0},counts,profiles:[{profile:'visit_preparation',counts}],items:[{id:'run-a',profile:'visit_preparation',execution_state:'succeeded',review_state:'pending',error:null,created_at:'2026-11-14T00:00:00Z',started_at:'2026-11-14T00:00:00Z',completed_at:'2026-11-14T00:01:00Z',elapsed_ms:60000,queue_age_seconds:null,usage:{prompt_eval_count:null,eval_count:null,prompt_eval_duration:null,eval_duration:null,total_duration:null},coverage:{eligible_sources:4,included_sources:2,omitted_sources:2,partial_sources:1},measured_cost:null,revision_count:1,effect_count:0,evidence_freshness:'not_checked_for_admin'}],active_watches:0,total:1,offset:0,limit:25,...overrides}}
let root:Root,requests:{path:string;init?:RequestInit}[],handler:((path:string)=>unknown|Promise<unknown>)|null,client:Client
beforeEach(()=>{document.body.innerHTML='<div id="root"></div>';root=createRoot(document.getElementById('root')!);requests=[];handler=null;client=new Client(async(url,init)=>{const path=String(url).replace('/api/v2/','');requests.push({path,init});const custom=await handler?.(path);return custom instanceof Response?custom:new Response(JSON.stringify(custom??data()))})})
afterEach(async()=>{await act(async()=>root.unmount())})
async function flush(ms=15){await act(async()=>{await new Promise(resolve=>setTimeout(resolve,ms))})}
async function mount(permitted=true,actor=session){await act(async()=>root.render(<AdminAIOperations client={client} session={actor} permitted={permitted}/>));await flush()}
function button(label:RegExp){const found=[...document.querySelectorAll<HTMLButtonElement>('button')].find(item=>label.test(item.getAttribute('aria-label')||item.textContent||''));assert.ok(found,'Missing button '+label);return found}
async function click(label:RegExp){await act(async()=>button(label).click());await flush()}
async function select(label:string,value:string){const input=document.querySelector<HTMLSelectElement>(`select[aria-label="${label}"]`);assert.ok(input);await act(async()=>{Object.getOwnPropertyDescriptor(dom.window.HTMLSelectElement.prototype,'value')!.set!.call(input,value);input.dispatchEvent(new dom.window.Event('change',{bubbles:true}))});await flush()}

test('metadata monitor keeps current health and heartbeat unknown despite historical success',async()=>{
 await mount();assert.match(document.querySelector('.admin-ai-observation')!.textContent!,/สถานะโมเดลสด: ยังไม่ได้ตรวจ/);assert.match(document.querySelector('.admin-ai-observation')!.textContent!,/Heartbeat: ยังไม่มีข้อมูลยืนยัน/);assert.match(document.body.textContent!,/ไม่ใช่สัญญาณว่า worker กำลังทำงานอยู่/);assert.match(document.body.textContent!,/ตัวเลือกข้อมูลรุ่นปัจจุบันเป็นผลตรวจแยก/);assert.equal(requests.length,1);assert.match(requests[0].path,/^admin\/ai-operations\?/);assert.equal(requests.some(item=>item.init?.method),false)
})
test('unknown monetary and token measurements stay unmeasured and no uncontracted patient bodies render',async()=>{
 const value=data() as any;value.patient_name='NEVER_SHOW_PATIENT';value.sources=[{text:'NEVER_SHOW_SOURCE'}];value.provider.endpoint='NEVER_SHOW_PRIVATE_URL';value.items[0].output='NEVER_SHOW_MODEL_OUTPUT';handler=()=>value;await mount();await click(/Read AI operation run-a/);assert.match(document.querySelector('.admin-ai-detail')!.textContent!,/ต้นทุนที่บันทึกยังไม่วัด/);assert.match(document.querySelector('.admin-ai-detail')!.textContent!,/Input tokensยังไม่วัด/);assert.doesNotMatch(document.body.textContent!,/NEVER_SHOW|confidence|healthy|clinically qualified/i);assert.equal(requests.some(item=>/^assistant\/|^patients|^documents/.test(item.path)),false)
})
test('server profile and state filtering and pagination use bounded query parameters',async()=>{
 handler=path=>data({total:60,offset:Number(new URL(path,'http://test').searchParams.get('offset'))});await mount();await select('AI operations profile','visit_preparation');await select('AI operations state','succeeded');await click(/^ถัดไป$/);const query=new URL(requests.at(-1)!.path,'http://test').searchParams;assert.equal(query.get('profile'),'visit_preparation');assert.equal(query.get('state'),'succeeded');assert.equal(query.get('offset'),'25');assert.equal(query.get('limit'),'25');assert.match(document.querySelector('.admin-ai-counts')!.textContent!,/Needs review3/)
})
test('a late older filter response cannot restore rows after newer scoped failure',async()=>{
 let release!:(value:unknown)=>void;handler=path=>new URL(path,'http://test').searchParams.get('state')==='failed'?new Promise(resolve=>{release=resolve}):new URL(path,'http://test').searchParams.get('state')==='timeout'?new Response(JSON.stringify({detail:'FORBIDDEN'}),{status:403}):undefined;await mount();await select('AI operations state','failed');await select('AI operations state','timeout');await act(async()=>release(data()));assert.equal(document.querySelector('.admin-ai-table'),null);assert.match(document.querySelector('[role=alert]')!.textContent!,/ไม่มีสิทธิ์/)
})
test('current-facility binding rejects a successful response for a different facility',async()=>{
 handler=()=>data({scope:{organization_id:'org-a',facility_id:'other-facility'}});await mount();assert.match(document.querySelector('[role=alert]')!.textContent!,/INVALID_AI_OPERATIONS/);assert.equal(document.querySelector('.admin-ai-counts'),null)
})
test('missing permission prevents reads and scalar projection rejects missing counts or fabricated measurements',async()=>{
 await mount(false);assert.equal(requests.length,0);assert.match(document.body.textContent!,/ไม่มีสิทธิ์/);assert.throws(()=>validAIOperations(data({counts:{}}),session.user),/INVALID_AI_OPERATIONS/);const invalid=data();invalid.items[0].usage.eval_count=true as any;assert.throws(()=>validAIOperations(invalid,session.user),/INVALID_AI_OPERATIONS_ITEM/);invalid.items[0].usage.eval_count=null;invalid.items[0].measured_cost='0 USD';assert.throws(()=>validAIOperations(invalid,session.user),/INVALID_AI_OPERATIONS_ITEM/)
})
