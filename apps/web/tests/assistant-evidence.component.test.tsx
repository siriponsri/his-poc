import {test,beforeEach,afterEach} from 'node:test'
import assert from 'node:assert/strict'
import {JSDOM} from 'jsdom'
import React,{act} from 'react'
import type {Root} from 'react-dom/client'
import {Client} from '../src/lib/client'
import type {AssistantRun,SourceSnapshot} from '../src/lib/assistant-types'

const dom=new JSDOM('<!doctype html><html><body></body></html>',{url:'http://localhost/home'})
for(const name of ['window','document','Event','CustomEvent','HTMLElement','Node','location','history'])Object.defineProperty(globalThis,name,{configurable:true,value:(dom.window as any)[name]})
;(globalThis as any).IS_REACT_ACT_ENVIRONMENT=true
const {createRoot}=await import('react-dom/client')
const {SourceEvidenceModal,EvidenceCoverage,unicodeSlice}=await import('../src/components/assistant-evidence')
const text='🙂 บทนำ ผลเดิม 7.2\nหมายเหตุใหม่ ผลเดิม 7.2 สิ้นสุด'
const quote='ผลเดิม 7.2',start=Array.from(text.slice(0,text.lastIndexOf(quote))).length,end=start+Array.from(quote).length
const source={ref:'s-doc',kind:'document',label:'Authored note',identity:'doc-a',version:3,revision_id:'doc-rev-3',content_hash:'source-hash',fields:{title:'Authored note'}}
const run={id:'run-a',sources:[source]} as AssistantRun
const snapshot:SourceSnapshot={...source,text,selection:'excerpt',excerpt_start:start,excerpt_end:Array.from(text).length,offset_unit:'unicode_code_points',selected_excerpt:unicodeSlice(text,start,Array.from(text).length),source_freshness:'stale',citations:[{field:null,quote,display:'Authored finding',start,end}]}
let root:Root,requests:{path:string;init?:RequestInit}[],reply:unknown,closed:number,client:Client
beforeEach(()=>{document.body.innerHTML='<button id="origin">Read evidence</button><div id="root"></div>';document.getElementById('origin')!.focus();root=createRoot(document.getElementById('root')!);requests=[];reply=structuredClone(snapshot);closed=0;client=new Client(async(url,init)=>{requests.push({path:String(url),init});const value=await reply;return value instanceof Response?value:new Response(JSON.stringify(value))})})
afterEach(async()=>{await act(async()=>root.unmount());document.body.style.overflow=''})
async function mount(request={source,quote}){await act(async()=>root.render(<SourceEvidenceModal client={client} run={run} request={request} onClose={()=>closed++} navigate={()=>{throw Error('Unexpected navigation')}}/>))}

test('snapshot highlights exact original Unicode code-point offsets, not the first equal passage',async()=>{
 await mount();const mark=document.querySelector('mark');assert.equal(mark?.textContent,quote);assert.equal(mark?.previousSibling?.textContent,unicodeSlice(text,0,start));assert.equal(document.querySelector('.evidence-source-text p')?.textContent,text);assert.match(document.body.textContent!,/บริบทที่ใช้เตรียมร่างเปลี่ยนแล้ว/);assert.equal(requests[0].path,'/api/v2/assistant/runs/run-a/sources/s-doc');assert.equal(requests.some(item=>item.init?.method),false)
})
test('a malformed citation offset never highlights a plausible but different quote',async()=>{
 reply={...snapshot,citations:[{field:null,quote,display:'Authored finding',start:start-1,end:end-1}]};await mount();assert.equal(document.querySelector('mark'),null);assert.match(document.body.textContent!,/ไม่พบข้อความอ้างอิง/)
})
test('metadata-only snapshot renders permitted fields without using cached source body',async()=>{
 reply={...snapshot,text:null,fields:{status:'draft',title:'Metadata note'},citations:[]};await mount({source:{...source,text:'NEVER_SHOW_CACHED_DOCUMENT'},quote});assert.match(document.body.textContent!,/อ้างอิงจากช่องข้อมูล/);assert.match(document.body.textContent!,/Metadata note/);assert.doesNotMatch(document.body.textContent!,/NEVER_SHOW_CACHED_DOCUMENT/);assert.equal(document.querySelector('.evidence-source-text'),null)
})
test('permission denial clears captured evidence instead of falling back to run text',async()=>{
 reply=new Response(JSON.stringify({detail:'FORBIDDEN'}),{status:403});await mount();assert.match(document.querySelector('[role=alert]')!.textContent!,/ไม่มีสิทธิ์/);assert.doesNotMatch(document.body.textContent!,/หมายเหตุใหม่/)
})
test('late old-source response cannot replace evidence for a newly selected source',async()=>{
 let release!:(value:unknown)=>void;reply=new Promise(resolve=>{release=resolve});await mount();const next={...source,ref:'s-other',identity:'doc-b',content_hash:'other-hash'};reply={...snapshot,...next,text:'Second selected source',selected_excerpt:'Second selected source',selection:'whole',citations:[]};await mount({source:next,quote:''});await act(async()=>release(snapshot));assert.match(document.body.textContent!,/Second selected source/);assert.doesNotMatch(document.body.textContent!,/หมายเหตุใหม่/)
})
test('snapshot keyboard region is focusable, Escape closes and unmount restores prior focus/body',async()=>{
 await mount();assert.equal(document.body.style.overflow,'hidden');const region=document.querySelector<HTMLElement>('[role=region]')!;assert.equal(region.tabIndex,0);await act(async()=>document.dispatchEvent(new dom.window.KeyboardEvent('keydown',{key:'Tab',bubbles:true,cancelable:true})));assert.equal(document.activeElement,region);await act(async()=>document.dispatchEvent(new dom.window.KeyboardEvent('keydown',{key:'Escape',bubbles:true,cancelable:true})));assert.equal(closed,1);await act(async()=>root.render(null));assert.equal(document.body.style.overflow,'');assert.equal(document.activeElement?.id,'origin')
})
test('coverage discloses partial and omitted sources without presenting a clinical confidence score',async()=>{
 const value={...run,quality:{selection_version:'excerpt-v2',included_by_kind:{document:1,lab:1},eligible_by_kind:{document:3,lab:1},omitted_by_kind:{document:2},partial_source_count:1,verified_fact_count:2,draft_attribution:'source_references_only_requires_human_review'},omitted_sources:[{kind:'document',label:'Omitted note',reason:'context_budget'}]} as AssistantRun
 await act(async()=>root.render(<EvidenceCoverage run={value}/>));assert.match(document.body.textContent!,/ใช้ 2 จาก 4/);assert.match(document.body.textContent!,/1 แหล่งใช้เฉพาะช่วงข้อความ/);assert.match(document.body.textContent!,/Omitted note/);assert.match(document.body.textContent!,/ตรวจคำอ้างอิงกับต้นฉบับแล้ว 2/);assert.match(document.body.textContent!,/ไม่ได้ยืนยันความถูกต้องทางคลินิก/);assert.doesNotMatch(document.body.textContent!,/confidence|accuracy|\d+%/i);assert.equal(requests.length,0)
})
