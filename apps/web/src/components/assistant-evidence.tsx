import {useEffect,useId,useRef,useState,type ReactNode} from 'react'
import {Client,errorText} from '../lib/client'
import {internalSourceUrl,sourceLabel} from '../lib/assistant-client'
import type {AssistantRun,Source,SourceSnapshot} from '../lib/assistant-types'
import {useLang} from '../lib/i18n'

export type EvidenceRequest={source:Source;quote?:string|null;field?:string|null}
const kindLabels:Record<string,string>={patient:'ทะเบียนผู้ป่วย',encounter:'การรับบริการ',document:'เอกสาร',lab:'ผลตรวจ',task:'งานติดตาม',handover:'บันทึกส่งเวร'}
/** Python snapshot offsets count Unicode code points, whereas JS substring counts UTF-16 units. */
export function unicodeSlice(text:string,start:number,end:number){
  const points=Array.from(text)
  if(!Number.isInteger(start)||!Number.isInteger(end)||start<0||end<start||end>points.length)return null
  return points.slice(start,end).join('')
}
export function quotedPassage(text:string,quote:string|null|undefined,start=0,end=Array.from(text).length):{before:string;quote:string;after:string}|null{
  if(!quote)return null
  const selected=unicodeSlice(text,start,end)
  if(selected===null)return null
  const at=selected.indexOf(quote)
  if(at<0)return null
  const prefix=Array.from(selected.slice(0,at)).length,quoteLength=Array.from(quote).length
  return {before:unicodeSlice(text,0,start+prefix)!,quote:unicodeSlice(text,start+prefix,start+prefix+quoteLength)!,after:unicodeSlice(text,start+prefix+quoteLength,Array.from(text).length)!}
}
const valueText=(value:unknown)=>typeof value==='string'?value:value===null||value===undefined?'ไม่ระบุ':typeof value==='object'?JSON.stringify(value):String(value)

export function EvidenceCoverage({run}:{run:AssistantRun}){
  const quality=run.quality
  if(!quality)return null
  const included=Object.values(quality.included_by_kind).reduce((total,value)=>total+value,0),eligible=Object.values(quality.eligible_by_kind).reduce((total,value)=>total+value,0)
  const kinds=[...new Set([...Object.keys(quality.eligible_by_kind),...Object.keys(quality.included_by_kind)])]
  return <section className="evidence-coverage" aria-label="Evidence coverage"><div><strong>Evidence coverage</strong><span>ใช้ {included} จาก {eligible} แหล่งข้อมูล{quality.partial_source_count>0?` · ${quality.partial_source_count} แหล่งใช้เฉพาะช่วงข้อความ`:''}</span></div><details><summary>ดูข้อมูลที่ใช้และที่ยังไม่รวม</summary><p>ตรวจคำอ้างอิงกับต้นฉบับแล้ว {quality.verified_fact_count} รายการ การอ้างอิงยืนยันตำแหน่งข้อมูล ไม่ได้ยืนยันความถูกต้องทางคลินิกหรือความหมายของร่าง</p><table><thead><tr><th>แหล่งข้อมูล</th><th>ที่ใช้</th><th>ที่เข้าถึงได้</th><th>ที่ยังไม่รวม</th></tr></thead><tbody>{kinds.map(kind=><tr key={kind}><th scope="row">{kindLabels[kind]||kind}</th><td>{quality.included_by_kind[kind]??0}</td><td>{quality.eligible_by_kind[kind]??0}</td><td>{quality.omitted_by_kind[kind]??0}</td></tr>)}</tbody></table>{!!run.omitted_sources?.length&&<ul className="evidence-omissions">{run.omitted_sources.map((source,index)=><li key={index}><strong>{source.label}</strong><span>{source.reason.replaceAll('_',' ')}</span></li>)}</ul>}<p className="evidence-attribution">แหล่งอ้างอิงของร่างระบุเป็นรายแหล่ง ต้องอ่านต้นฉบับและทบทวนข้อความก่อนนำไปใช้</p><small>Selection policy {quality.selection_version}</small></details></section>
}

export function SourceEvidenceModal({client,run,request,onClose,navigate}:{client:Client;run:AssistantRun;request:EvidenceRequest;onClose:()=>void;navigate:(path:string)=>void}){
  const {lang,t}=useLang(),id=useId(),dialog=useRef<HTMLDivElement>(null),close=useRef<HTMLButtonElement>(null)
  const closeAction=useRef(onClose);closeAction.current=onClose
  const binding=[run.id,request.source.ref,request.source.identity||'',request.source.version??'',request.source.content_hash||''].join('|')
  const [response,setResponse]=useState<{binding:string;snapshot:SourceSnapshot|null;error:string}|null>(null)
  const snapshot=response?.binding===binding?response.snapshot:null,error=response?.binding===binding?response.error:''
  useEffect(()=>{
    let active=true;setResponse(null)
    client.get<SourceSnapshot>('assistant/runs/'+encodeURIComponent(run.id)+'/sources/'+encodeURIComponent(request.source.ref)).then(value=>{
      if(!value||value.ref!==request.source.ref||typeof value.fields!=='object'||value.fields===null||Array.isArray(value.fields)||!(value.text===null||typeof value.text==='string')||request.source.identity&&value.identity!==request.source.identity||request.source.content_hash&&value.content_hash!==request.source.content_hash||typeof request.source.version==='number'&&value.version!==request.source.version)throw Error('INVALID_SOURCE_SNAPSHOT')
      if(active)setResponse({binding,snapshot:value,error:''})
    }).catch(reason=>{if(active)setResponse({binding,snapshot:null,error:errorText(reason)})})
    return()=>{active=false}
  },[client,binding])
  useEffect(()=>{
    const previous=document.activeElement as HTMLElement|null,overflow=document.body.style.overflow
    document.body.style.overflow='hidden';close.current?.focus()
    const key=(event:KeyboardEvent)=>{
      if(event.key==='Escape'){event.preventDefault();event.stopPropagation();closeAction.current();return}
      if(event.key!=='Tab')return
      const controls=[...(dialog.current?.querySelectorAll<HTMLElement>('button:not(:disabled),summary,[tabindex="0"]')||[])]
      if(!controls.length)return
      const index=controls.indexOf(document.activeElement as HTMLElement),next=index<0?0:(index+(event.shiftKey?-1:1)+controls.length)%controls.length
      event.preventDefault();controls[next].focus()
    }
    document.addEventListener('keydown',key,true)
    return()=>{document.removeEventListener('keydown',key,true);document.body.style.overflow=overflow;if(previous?.isConnected)previous.focus()}
  },[])
  const text=snapshot?.text??null
  const hasExcerpt=snapshot?.selection==='excerpt'
  const excerpt=hasExcerpt&&text!==null&&snapshot?.offset_unit==='unicode_code_points'&&typeof snapshot.excerpt_start==='number'&&typeof snapshot.excerpt_end==='number'?unicodeSlice(text,snapshot.excerpt_start,snapshot.excerpt_end):null
  const rangeValid=!hasExcerpt||excerpt!==null&&(snapshot?.selected_excerpt===undefined||snapshot.selected_excerpt===excerpt)
  const citation=snapshot?.citations?.find(item=>item.quote===request.quote&&!!request.quote)
  const citedText=text!==null&&citation&&typeof citation.start==='number'&&typeof citation.end==='number'?unicodeSlice(text,citation.start,citation.end):null
  const quote=text!==null&&rangeValid?(citation?citedText===request.quote?{before:unicodeSlice(text,0,citation.start!)!,quote:citedText!,after:unicodeSlice(text,citation.end!,Array.from(text).length)!}:null:quotedPassage(text,request.quote,hasExcerpt?snapshot!.excerpt_start!:0,hasExcerpt?snapshot!.excerpt_end!:Array.from(text).length)):null
  useEffect(()=>{if(snapshot)dialog.current?.querySelector('mark')?.scrollIntoView?.({block:'center',behavior:'auto'})},[snapshot,request.quote,request.field])
  const currentUrl=internalSourceUrl(request.source.url)
  function renderText():ReactNode{return quote?<>{quote.before}<mark>{quote.quote}</mark>{quote.after}</>:text}
  return <div className="evidence-modal-backdrop" onMouseDown={event=>{if(event.target===event.currentTarget)onClose()}}><section ref={dialog} className="evidence-modal" role="dialog" aria-modal="true" aria-labelledby={id}><header><div><p>Source snapshot</p><h2 id={id}>{sourceLabel(request.source,lang)}</h2></div><button ref={close} type="button" className="text-button" aria-label="Close source evidence" onClick={onClose}>×</button></header><div className="evidence-modal-body" tabIndex={0} role="region" aria-label="ข้อมูลต้นฉบับที่ใช้อ้างอิง">
    {error?<p className="care-error" role="alert">{t('อ่านหลักฐานไม่ได้ ข้อมูลที่มีสิทธิ์เข้าถึงอาจเปลี่ยนแล้ว','Source evidence could not be read. Your permitted scope may have changed.')} {error}</p>:!snapshot?<p role="status">{t('กำลังอ่านฉบับที่ใช้อ้างอิง…','Reading the captured source…')}</p>:<>
      <div className="evidence-snapshot-meta"><span>{kindLabels[snapshot.kind]||snapshot.kind}</span><span>{t('ฉบับ','Version')} {snapshot.version??t('ไม่ระบุ','unavailable')}</span><span>{snapshot.source_freshness==='current'?t('ข้อมูลที่ใช้เตรียมร่างยังตรงกับปัจจุบัน','Preparation sources remain current'):snapshot.source_freshness==='stale'?t('ฉบับอ้างอิงเดิม บริบทที่ใช้เตรียมร่างเปลี่ยนแล้ว','Captured snapshot; preparation context has changed'):t('ยังยืนยันบริบทปัจจุบันไม่ได้','Current preparation context is unverified')}</span></div>
      {!snapshot.selection&&<p className="evidence-selection-note">{t('รอบเดิมไม่มีข้อมูลช่วงข้อความที่ส่งให้โมเดล แสดงฉบับอ้างอิงที่บันทึกไว้','This older run has no selection metadata. The captured source is shown.')}</p>}
      {!rangeValid&&<p className="care-error" role="alert">{t('ตำแหน่งช่วงข้อความไม่ตรงกับฉบับที่บันทึก จึงไม่เน้นตำแหน่งที่อ้างอิง','Selection offsets do not match the captured source; no location is highlighted.')}</p>}
      {request.quote&&text!==null&&rangeValid&&!quote&&<p className="evidence-selection-note">{t('ไม่พบข้อความอ้างอิงนี้ในช่วงที่เลือก อ่านต้นฉบับฉบับเต็มก่อนใช้ร่าง','This quotation was not found in the selected passage. Read the full source before using the draft.')}</p>}
      {text!==null?<section className="evidence-source-text"><h3>{t('ต้นฉบับฉบับเต็มที่บันทึกไว้','Complete captured source')}</h3><p>{renderText()}</p></section>:<p className="evidence-selection-note">{t('แหล่งข้อมูลนี้อ้างอิงจากช่องข้อมูลที่แสดงด้านล่าง ไม่มีข้อความเอกสารในฉบับอ้างอิงนี้','Evidence for this source is in the structured fields below. This snapshot has no document text.')}</p>}
      {hasExcerpt&&rangeValid&&<details className="evidence-selected-excerpt"><summary>{t('ช่วงข้อความที่ใช้เตรียมร่าง','Passage selected for preparation')}</summary><blockquote>{excerpt}</blockquote><small>{t('ตำแหน่ง Unicode','Unicode code-point range')} {snapshot.excerpt_start}–{snapshot.excerpt_end}</small></details>}
      <dl className="evidence-source-fields">{Object.entries(snapshot.fields).map(([key,value])=><div key={key}><dt>{key.replaceAll('_',' ')}</dt><dd>{request.field===key?<mark>{valueText(value)}</mark>:valueText(value)}</dd></div>)}</dl>
      <details className="evidence-identifiers"><summary>{t('รายละเอียดการผูกฉบับ','Snapshot identifiers')}</summary><dl><dt>Source</dt><dd>{snapshot.ref} · {snapshot.identity}</dd><dt>Revision</dt><dd>{snapshot.revision_id||'Unavailable'}</dd><dt>Content hash</dt><dd>{snapshot.content_hash||'Unavailable'}</dd></dl></details>
    </>}
  </div><footer><p>{t('กำลังอ่านฉบับที่ใช้เตรียมร่าง การบันทึกจะตรวจฉบับปัจจุบันอีกครั้ง','This is the snapshot used for preparation. Saving rechecks current sources.')}</p>{currentUrl&&<button className="secondary" disabled={!snapshot} onClick={()=>{onClose();navigate(currentUrl)}}>{t('เปิดรายการปัจจุบัน','Open current record')}</button>}</footer></section></div>
}
