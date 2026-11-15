import {test,beforeEach,afterEach} from 'node:test'
import assert from 'node:assert/strict'
import {JSDOM} from 'jsdom'
import React,{act} from 'react'
import type {Root} from 'react-dom/client'
import {GUIDE_CHAPTERS,GUIDE_DOMAINS} from '../src/data/user-guide-content'

const dom=new JSDOM('<!doctype html><html><body></body></html>',{url:'http://localhost:8000/guide'})
for(const name of ['window','document','Event','CustomEvent','HTMLElement','HTMLInputElement','HTMLTextAreaElement','Node','location','history'])Object.defineProperty(globalThis,name,{configurable:true,value:(dom.window as any)[name]})
;(globalThis as any).IS_REACT_ACT_ENVIRONMENT=true
;(dom.window as any).scrollTo=()=>{}
;(dom.window.HTMLElement.prototype as any).scrollIntoView=()=>{}
;(dom.window as any).matchMedia=()=>({matches:false,addEventListener(){},removeEventListener(){}})
const user={id:'guide-fictional',username:'guide-reader',display_name:'Fictional guide reader',organization_id:'org-test',facility_id:'facility-test',roles:['clinician'],permissions:['D01.read','D03.read','D22.read','D37.read','patient.reference','encounter.reference'],patient_scope:null as string|null}
let authenticated=true,currentUser={...user},requests:string[]=[],root:Root
globalThis.fetch=async(input)=>{
 const path=String(input).replace('/api/v2/','');requests.push(path)
 assert.equal(path,'auth/me','Opening a static guide must not read records or request inference')
 return new Response(JSON.stringify(authenticated?{user:currentUser,csrf_token:'synthetic-guide-csrf',expires_at:'2099-01-01T00:00:00Z'}:{detail:{code:'SESSION_REQUIRED'}}),{status:authenticated?200:401})
}
const {createRoot}=await import('react-dom/client')
const {default:App}=await import('../src/App')
beforeEach(()=>{document.body.innerHTML='<div id="root"></div>';authenticated=true;currentUser={...user};requests=[];root=createRoot(document.getElementById('root')!)})
afterEach(async()=>{await act(async()=>root.unmount())})
async function flush(){await act(async()=>{await new Promise(resolve=>setTimeout(resolve,20))})}
async function until(selector:string){for(let i=0;i<60&&!document.querySelector(selector);i++)await flush();assert.ok(document.querySelector(selector),'Missing '+selector)}
async function mount(path:string){history.replaceState({},'',path);await act(async()=>root.render(<App/>))}

test('unauthenticated guide retains its deep chapter after the ordinary401 without loading any records',async()=>{
 authenticated=false
 const chapter=GUIDE_CHAPTERS.find(item=>item.id==='administration')!
 assert.ok(chapter)
 await mount('/guide?chapter='+chapter.id);await until('#user-guide-title')
 assert.equal(location.pathname,'/guide');assert.equal(new URLSearchParams(location.search).get('chapter'),chapter.id)
 assert.match(document.body.textContent!,new RegExp(chapter.title.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')))
 assert.ok(document.querySelector('.guide-public-shell'));assert.equal(document.querySelector('input[type=password]'),null)
 assert.deepEqual(requests,['auth/me'])
})

test('signed-in clinical guide skips patient and encounter prefetch despite actual reference permissions',async()=>{
 await mount('/guide');await until('#user-guide-title')
 assert.equal(document.querySelector('.guide-public-shell'),null)
 assert.ok([...document.querySelectorAll('button')].some(item=>item.textContent==='User Guide'&&item.getAttribute('aria-current')==='page'))
 assert.deepEqual(requests,['auth/me'])
})

test('login help opens the readable guide without submitting credentials or requiring a session',async()=>{
 authenticated=false;await mount('/login');await until('.login-form-box')
 const help=document.querySelector<HTMLButtonElement>('.guide-login-link');assert.ok(help)
 await act(async()=>help.click());await until('#user-guide-title')
 assert.equal(location.pathname,'/guide');assert.deepEqual(requests,['auth/me'])
})

test('portal reader can read a domain reference without querying the server-linked patient or changing roles',async()=>{
 currentUser={...user,roles:['patient'],permissions:['D21.read','patient.reference','encounter.reference'],patient_scope:'fictional-subject'}
 const domain=GUIDE_DOMAINS.find(item=>item.id==='D38')!;assert.ok(domain)
 await mount('/guide/?domain=D38');await until('#user-guide-title')
 assert.match(document.body.textContent!,/D38/);assert.match(document.body.textContent!,/platform|operator|ผู้ดูแล/i)
 assert.deepEqual(currentUser.roles,['patient']);assert.deepEqual(requests,['auth/me'])
})
