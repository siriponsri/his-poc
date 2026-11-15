import {useEffect,useId,useMemo,useRef,useState,type KeyboardEvent} from 'react'
import type {GuideChapter,GuideDomain} from '../data/user-guide-content'

export type GuideMedia={
  src:string
  alt:string
  caption:string
  width:number
  height:number
  tour?:{label:string;description:string;rect:{x:number;y:number;width:number;height:number}}[]
}
type Selection={kind:'chapter'|'domain';id:string}
type Props={chapters:GuideChapter[];domains:GuideDomain[];media:Record<string,GuideMedia>;roles?:string[]}
const normalize=(value:string)=>value.normalize('NFKC').toLocaleLowerCase('th').replaceAll('_',' ')
const matches=(text:string,query:string)=>normalize(query).trim().split(/\s+/).filter(Boolean).every(word=>normalize(text).includes(word))
const relatedToRole=(roles:string[],viewer:string[])=>roles.length===0||roles.some(role=>['all','everyone','ทุกบทบาท'].includes(normalize(role))||viewer.some(value=>normalize(value)===normalize(role)))
const selectionKey=(selection:Selection)=>selection.kind+':'+selection.id
const roleName=(role:string)=>role.replaceAll('_',' ')

function initialSelection(chapters:GuideChapter[],domains:GuideDomain[]):Selection{
  const params=typeof window==='undefined'?new URLSearchParams():new URLSearchParams(window.location.search)
  const domain=params.get('domain'),chapter=params.get('chapter')
  if(domain&&domains.some(item=>item.id===domain))return {kind:'domain',id:domain}
  if(chapter&&chapters.some(item=>item.id===chapter))return {kind:'chapter',id:chapter}
  return {kind:'chapter',id:chapters[0]?.id||''}
}

function useReducedMotion(){
  const [reduced,setReduced]=useState(()=>typeof window!=='undefined'&&Boolean(window.matchMedia?.('(prefers-reduced-motion: reduce)').matches))
  useEffect(()=>{
    const query=window.matchMedia?.('(prefers-reduced-motion: reduce)')
    if(!query)return
    const changed=()=>setReduced(query.matches)
    changed();query.addEventListener?.('change',changed)
    return ()=>query.removeEventListener?.('change',changed)
  },[])
  return reduced
}

function GuideImageZoom({media,onClose}:{media:GuideMedia;onClose:()=>void}){
  const id=useId(),close=useRef<HTMLButtonElement>(null),dialog=useRef<HTMLDivElement>(null)
  const [original,setOriginal]=useState(false)
  useEffect(()=>{
    const previous=document.activeElement as HTMLElement|null
    const overflow=document.body.style.overflow
    document.body.style.overflow='hidden'
    close.current?.focus()
    return ()=>{document.body.style.overflow=overflow;if(previous?.isConnected)previous.focus()}
  },[])
  function keyDown(event:KeyboardEvent){
    if(event.key==='Escape'){event.preventDefault();event.stopPropagation();onClose();return}
    if(event.key!=='Tab')return
    const controls=dialog.current?.querySelectorAll<HTMLButtonElement>('button:not(:disabled)')
    if(!controls?.length)return
    const first=controls[0],last=controls[controls.length-1]
    if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus()}
    else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus()}
  }
  return <div className="guide-zoom-backdrop" onClick={event=>{if(event.target===event.currentTarget)onClose()}}>
    <div className="guide-zoom" ref={dialog} role="dialog" aria-modal="true" aria-labelledby={id} onKeyDown={keyDown}>
      <header><h2 id={id}>ภาพประกอบคู่มือ</h2><div><button type="button" aria-pressed={original} onClick={()=>setOriginal(value=>!value)}>{original?'พอดีหน้าจอ':'ขนาดต้นฉบับ'}</button><button type="button" ref={close} onClick={onClose} aria-label="ปิดภาพประกอบคู่มือ">ปิด <span aria-hidden="true">×</span></button></div></header>
      <div className={'guide-zoom-surface'+(original?' original-size':'')}><img src={media.src} alt={media.alt} width={media.width} height={media.height} style={original?{width:media.width}:undefined}/></div>
      <p>{media.caption}</p>
    </div>
  </div>
}

/** A paused-by-default explanation over a static screenshot. It issues no app command. */
export function GuideScreenshot({media,stepDurationMs=4500}:{media:GuideMedia;stepDurationMs?:number}){
  const steps=media.tour||[],reduced=useReducedMotion()
  const [index,setIndex]=useState(0),[playing,setPlaying]=useState(false),[zoom,setZoom]=useState(false)
  const id=useId(),step=steps[index]
  useEffect(()=>{setIndex(0);setPlaying(false)},[media.src])
  useEffect(()=>{if(reduced)setPlaying(false)},[reduced])
  useEffect(()=>{
    if(!playing||reduced||steps.length<2)return
    const timer=window.setTimeout(()=>{
      if(index>=steps.length-1)setPlaying(false)
      else setIndex(value=>value+1)
    },stepDurationMs)
    return ()=>window.clearTimeout(timer)
  },[playing,reduced,index,steps.length,stepDurationMs])
  const move=(next:number)=>{setPlaying(false);setIndex(Math.min(steps.length-1,Math.max(0,next)))}
  const bounded=(value:number)=>Number.isFinite(value)?Math.max(0,Math.min(100,value)):0
  return <figure className={'guide-figure'+(playing?' is-playing':'')}>
    <button type="button" className="guide-image-open" onClick={()=>{setPlaying(false);setZoom(true)}} aria-label={'ขยายภาพ: '+media.alt}>
      <img src={media.src} alt={media.alt} width={media.width} height={media.height} loading="lazy" decoding="async"/>
      {step&&<span className="guide-spotlight" aria-hidden="true" style={{left:bounded(step.rect.x)+'%',top:bounded(step.rect.y)+'%',width:bounded(step.rect.width)+'%',height:bounded(step.rect.height)+'%'}}><span className="guide-pointer"/></span>}
      <span className="guide-image-expand" aria-hidden="true">ขยายภาพ ↗</span>
    </button>
    <figcaption>{media.caption}</figcaption>
    {step&&<div className="guide-tour" aria-label="ภาพอธิบายขั้นตอน">
      <div className="guide-tour-heading"><span>ภาพอธิบายขั้นตอน</span><span>{index+1} / {steps.length}</span></div>
      <div className="guide-tour-caption" id={id} aria-live={playing?'off':'polite'} aria-atomic="true"><strong>{step.label}</strong><p>{step.description}</p></div>
      <div className="guide-tour-controls">
        <button type="button" onClick={()=>move(index-1)} disabled={index===0} aria-label="ขั้นตอนก่อนหน้า">← ก่อนหน้า</button>
        {steps.length>1&&<button type="button" className="guide-tour-play" aria-pressed={playing} disabled={reduced} aria-describedby={id} onClick={()=>{if(!playing&&index===steps.length-1)setIndex(0);setPlaying(value=>!value)}}>{playing?'หยุดภาพเคลื่อนไหว':'เล่นภาพเคลื่อนไหว'}</button>}
        <button type="button" onClick={()=>move(index+1)} disabled={index===steps.length-1} aria-label="ขั้นตอนถัดไป">ถัดไป →</button>
      </div>
      {reduced&&<p className="guide-motion-note">เปิดโหมดลดการเคลื่อนไหวอยู่ เลือกอ่านด้วยปุ่มก่อนหน้าและถัดไปได้</p>}
      <details className="guide-tour-transcript"><summary>อ่านคำอธิบายทุกขั้นตอน</summary><ol>{steps.map((item,number)=><li key={number}><strong>{item.label}</strong><p>{item.description}</p></li>)}</ol></details>
    </div>}
    {zoom&&<GuideImageZoom media={media} onClose={()=>setZoom(false)}/>}
  </figure>
}

export function UserGuide({chapters,domains,media,roles=[]}:Props){
  const [selection,setSelection]=useState<Selection>(()=>initialSelection(chapters,domains))
  const [query,setQuery]=useState(''),[myRoles,setMyRoles]=useState(false)
  const title=useRef<HTMLHeadingElement>(null),navigated=useRef(false)
  const chapter=selection.kind==='chapter'?chapters.find(item=>item.id===selection.id):undefined
  const domain=selection.kind==='domain'?domains.find(item=>item.id===selection.id):undefined
  const filteredChapters=useMemo(()=>chapters.filter(item=>(!myRoles||relatedToRole(item.roles,roles))&&matches([item.title,item.summary,...item.roles,...item.prerequisites,...item.steps.flatMap(step=>[step.title,...step.paragraphs,step.note||'']),...item.completion,...item.troubleshooting.flatMap(problem=>[problem.problem,problem.action]),...item.domains].join(' '),query)),[chapters,myRoles,query,roles])
  const filteredDomains=useMemo(()=>domains.filter(item=>(!myRoles||relatedToRole(item.roles,roles))&&matches([item.id,item.name,item.purpose,...item.roles,...item.steps,item.completion,item.limits].join(' '),query)),[domains,myRoles,query,roles])
  useEffect(()=>{
    const readLocation=()=>setSelection(initialSelection(chapters,domains))
    window.addEventListener('popstate',readLocation)
    return ()=>window.removeEventListener('popstate',readLocation)
  },[chapters,domains])
  useEffect(()=>{
    if(!navigated.current)return
    title.current?.focus({preventScroll:true});title.current?.scrollIntoView?.({block:'start',behavior:'auto'})
    navigated.current=false
  },[selection])
  function select(next:Selection){
    navigated.current=true;setSelection(next)
    const url=new URL(window.location.href)
    url.searchParams.delete('chapter');url.searchParams.delete('domain');url.hash=''
    url.searchParams.set(next.kind,next.id)
    window.history.replaceState(window.history.state,'',url.pathname+url.search+url.hash)
  }
  const selectKey=(key:string)=>{const [kind,id]=key.split(':');if(kind==='chapter'||kind==='domain')select({kind,id})}
  const currentIndex=chapter?chapters.findIndex(item=>item.id===chapter.id):-1
  const resultCount=filteredChapters.length+filteredDomains.length
  const figureIds=new Set<string>()
  return <section className="user-guide" aria-labelledby="user-guide-title">
    <header className="guide-page-header"><p className="guide-eyebrow">CareBalance / Learning center</p><h1 id="user-guide-title">User Guide</h1><p>เรียนรู้ตามงานที่ต้องทำ ตั้งแต่เปิดเวชระเบียนจนถึงทบทวนและส่งต่องาน</p><span>{chapters.length} หัวข้อการใช้งาน · {domains.length} ส่วนงานอ้างอิง</span></header>
    <div className="guide-layout">
      <aside className="guide-outline" aria-label="สารบัญคู่มือ">
        <div className="guide-search"><label htmlFor="guide-search">ค้นหาในคู่มือ</label><input id="guide-search" type="search" value={query} placeholder="ชื่อเมนู ขั้นตอน หรือ D01–D38" onChange={event=>setQuery(event.target.value)}/></div>
        {roles.length>0&&<label className="guide-role-filter"><input type="checkbox" checked={myRoles} onChange={event=>setMyRoles(event.target.checked)}/>หัวข้อที่เกี่ยวข้องกับบทบาทของฉัน</label>}
        <p className="guide-result-count" role="status">{query.trim()||myRoles?`${resultCount} หัวข้อที่ตรงกัน`:'เลือกหัวข้อจากสารบัญ'}</p>
        <div className="guide-mobile-navigation"><label htmlFor="guide-section-select">เลือกหัวข้อ</label><select id="guide-section-select" value={selectionKey(selection)} onChange={event=>selectKey(event.target.value)}>
          {!filteredChapters.some(item=>selection.kind==='chapter'&&item.id===selection.id)&&!filteredDomains.some(item=>selection.kind==='domain'&&item.id===selection.id)&&<option value={selectionKey(selection)}>{chapter?.title||domain?.name||'หัวข้อปัจจุบัน'}</option>}
          {filteredChapters.length>0&&<optgroup label="Usage chapters">{filteredChapters.map(item=><option key={item.id} value={'chapter:'+item.id}>{item.title}</option>)}</optgroup>}
          {filteredDomains.length>0&&<optgroup label="Domain reference">{filteredDomains.map(item=><option key={item.id} value={'domain:'+item.id}>{item.id} · {item.name}</option>)}</optgroup>}
        </select></div>
        {resultCount===0?<div className="guide-no-results"><strong>ยังไม่พบหัวข้อที่ตรงกัน</strong><p>ลองใช้ชื่อเมนูหรือรหัสส่วนงาน เช่น Documents หรือ D22</p><button type="button" onClick={()=>{setQuery('');setMyRoles(false)}}>ล้างตัวกรอง</button></div>:<nav className={'guide-chapter-navigation'+(query.trim()?' has-search':'')} aria-label="หัวข้อการใช้งาน">
          <p>Usage chapters</p><ol>{filteredChapters.map(item=><li key={item.id}><button type="button" aria-current={selection.kind==='chapter'&&selection.id===item.id?'page':undefined} onClick={()=>select({kind:'chapter',id:item.id})}><span>{String(chapters.indexOf(item)+1).padStart(2,'0')}</span>{item.title}</button></li>)}</ol>
          <details className="guide-domain-navigation" open={Boolean(query.trim())||selection.kind==='domain'}><summary>Domain reference <span>{filteredDomains.length}</span></summary><ul>{filteredDomains.map(item=><li key={item.id}><button type="button" aria-current={selection.kind==='domain'&&selection.id===item.id?'page':undefined} onClick={()=>select({kind:'domain',id:item.id})}><span>{item.id}</span>{item.name}</button></li>)}</ul></details>
        </nav>}
      </aside>
      <article className="guide-reader" aria-label="เนื้อหาคู่มือ">
        {chapter?<>
          <header className="guide-chapter-header"><p className="guide-eyebrow">Usage chapter {String(currentIndex+1).padStart(2,'0')}</p><h2 ref={title} tabIndex={-1}>{chapter.title}</h2><p className="guide-summary">{chapter.summary}</p><p className="guide-audience"><span>เหมาะสำหรับ</span> {chapter.roles.map(roleName).join(' · ')||'ทุกบทบาท'}</p></header>
          {chapter.prerequisites.length>0&&<section className="guide-before" aria-labelledby="guide-before-title"><h3 id="guide-before-title">Before you start</h3><ul>{chapter.prerequisites.map((item,index)=><li key={index}>{item}</li>)}</ul></section>}
          <ol className="guide-steps">{chapter.steps.map((step,index)=>{
            const image=step.screenshot?media[step.screenshot]:undefined,duplicate=Boolean(step.screenshot&&figureIds.has(step.screenshot))
            if(step.screenshot)figureIds.add(step.screenshot)
            return <li key={chapter.id+index} id={`guide-${chapter.id}-step-${index+1}`}><div className="guide-step-heading"><span aria-hidden="true">{String(index+1).padStart(2,'0')}</span><h3>{step.title}</h3><a href={`#guide-${chapter.id}-step-${index+1}`} aria-label={'ลิงก์ไปขั้นตอน '+(index+1)}>#</a></div><div className="guide-step-body">{step.paragraphs.map((paragraph,number)=><p key={number}>{paragraph}</p>)}{step.note&&<p className="guide-step-note"><strong>ข้อควรตรวจ</strong> {step.note}</p>}{image&&(duplicate?<a className="guide-figure-reference" href={`#guide-media-${chapter.id}-${step.screenshot}`}>ดูภาพประกอบ {step.screenshot} ↑</a>:<div id={`guide-media-${chapter.id}-${step.screenshot}`}><GuideScreenshot key={chapter.id+step.screenshot} media={image}/></div>)}</div></li>
          })}</ol>
          {chapter.completion.length>0&&<section className="guide-completion" aria-labelledby="guide-completion-title"><h3 id="guide-completion-title">Check your work</h3><ul>{chapter.completion.map((item,index)=><li key={index}>{item}</li>)}</ul></section>}
          {chapter.troubleshooting.length>0&&<section className="guide-problems" aria-labelledby="guide-problems-title"><h3 id="guide-problems-title">When something needs attention</h3>{chapter.troubleshooting.map((item,index)=><details key={index}><summary>{item.problem}</summary><p>{item.action}</p></details>)}</section>}
          {chapter.domains.length>0&&<div className="guide-related"><h3>Related domains</h3><div>{chapter.domains.map(id=>{const item=domains.find(value=>value.id===id);return item?<button type="button" key={id} onClick={()=>select({kind:'domain',id})}>{id} · {item.name} <span aria-hidden="true">↗</span></button>:null})}</div></div>}
          <footer className="guide-next-chapter">{currentIndex>0?<button type="button" onClick={()=>select({kind:'chapter',id:chapters[currentIndex-1].id})}><span>← Previous chapter</span>{chapters[currentIndex-1].title}</button>:<span/>}{currentIndex<chapters.length-1&&<button type="button" onClick={()=>select({kind:'chapter',id:chapters[currentIndex+1].id})}><span>Next chapter →</span>{chapters[currentIndex+1].title}</button>}</footer>
        </>:domain?<>
          <header className="guide-chapter-header"><p className="guide-eyebrow">Domain reference / {domain.id}</p><h2 ref={title} tabIndex={-1}>{domain.name}</h2><p className="guide-summary">{domain.purpose}</p><p className="guide-audience"><span>บทบาทที่เกี่ยวข้อง</span> {domain.roles.map(roleName).join(' · ')||'ตามสิทธิ์ที่ได้รับมอบหมาย'}</p></header>
          <section className="guide-domain-steps"><h3>Working sequence</h3><ol>{domain.steps.map((step,index)=><li key={index}>{step}</li>)}</ol></section>
          <section className="guide-completion"><h3>Check your work</h3><p>{domain.completion}</p></section>
          <section className="guide-domain-limits"><h3>Scope and limitations</h3><p>{domain.limits}</p></section>
          {chapters.some(item=>item.domains.includes(domain.id))&&<div className="guide-related"><h3>Read the full workflow</h3><div>{chapters.filter(item=>item.domains.includes(domain.id)).map(item=><button type="button" key={item.id} onClick={()=>select({kind:'chapter',id:item.id})}>{item.title} <span aria-hidden="true">↗</span></button>)}</div></div>}
        </>:<div className="guide-empty"><h2 ref={title} tabIndex={-1}>คู่มือกำลังจัดเตรียม</h2><p>ยังไม่มีเนื้อหาสำหรับหัวข้อนี้</p></div>}
      </article>
    </div>
  </section>
}
