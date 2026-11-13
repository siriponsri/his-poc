import {useEffect,useRef,useState,type ReactNode} from 'react'
import {Client,HttpError,rows,normalizeMutation,errorText,type Row,type PendingOperation} from '../lib/client'
import type {Resource,ActionDef} from '../lib/catalog'
import {useLang,statusNamesEn} from '../lib/i18n'
import {DataForm,type FormValues} from './forms'
import {GrowthTimeline} from './growth'
import {Icon} from './icons'

const statusNames:Record<string,string>={draft:'ร่าง',pending:'รอตรวจทาน',verified:'ตรวจยืนยันแล้ว',active:'ใช้งาน',inactive:'ปิดใช้',open:'เปิดงาน',in_progress:'กำลังดำเนินงาน',completed:'เสร็จสิ้น',cancelled:'ยกเลิก',requested:'รอดำเนินการ',booked:'จองแล้ว',checked_in:'เช็กอินแล้ว',called:'เรียกคิวแล้ว',waiting:'รอรับบริการ',in_consult:'กำลังตรวจ',reviewed:'ทบทวนแล้ว',closed:'ปิดงาน',approved:'อนุมัติ',rejected:'ปฏิเสธ',committed:'บันทึกผลแล้ว',posted:'ลงรายการแล้ว',released:'เผยแพร่แล้ว',attested:'รับรองแล้ว',returned:'ส่งคืน',in_review:'รอตรวจทาน',amended:'ฉบับแก้ไข',failed:'ไม่สำเร็จ',timeout:'หมดเวลารอ',abstained:'งดให้ข้อเสนอ',success:'สำเร็จ',requested_restore:'ขอกู้คืน',restore_verified:'ตรวจผลกู้คืนแล้ว'}
// Tone carries meaning together with the label; unknown states stay neutral rather than guessing.
const tones:Record<string,string>={
 done:'committed active completed released verified attested approved posted success closed restore_verified reviewed delivered exported corrected acknowledged signed',
 wait:'draft requested pending open in_review booked waiting amended returned requested_restore admission_requested',
 progress:'in_progress in_consult checked_in called running administration_recorded',
 stop:'failed rejected cancelled inactive timeout abstained disabled suspended',
}
const toneOf=(state:string)=>Object.keys(tones).find(tone=>tones[tone].split(' ').includes(state))||'neutral'
export const statusLabel=(state:string,lang:string)=>(lang==='en'?statusNamesEn[state]:statusNames[state])||state.replaceAll('_',' ')||'—'
export function Status({value}:{value:unknown}){
 const {lang}=useLang();const state=String(value||'')
 const label=statusLabel(state,lang)
 return <span title={state} className={'status status-'+state+' tone-'+toneOf(state)}><Icon name={toneOf(state)==='done'?'check':toneOf(state)==='stop'?'missing':'clock'} size={13}/>{label}</span>
}

const fieldNames:Record<string,[string,string]>={display_name:['ชื่อ','Name'],title:['ชื่อเรื่อง','Title'],status:['สถานะ','Status'],kind:['ประเภท','Type'],birth_date:['วันเกิด','Date of birth'],sex:['เพศ','Sex'],created_at:['สร้างเมื่อ','Created'],updated_at:['แก้ไขล่าสุด','Updated'],content:['เนื้อหา','Content'],reason:['เหตุผล','Reason'],published:['เผยแพร่ให้ผู้ป่วย','Published to patient'],disposition:['การจำหน่าย','Disposition'],domain:['พื้นที่งาน','Workspace'],username:['ชื่อบัญชี','Username'],roles:['บทบาท','Roles'],permissions:['สิทธิ์','Permissions'],instructions:['คำสั่ง','Instructions'],quantity:['จำนวน','Quantity'],unit:['หน่วย','Unit'],label:['รายการ','Item'],code:['รหัสรายการ','Code'],action:['การดำเนินการ','Action'],content_access:['การเข้าถึงเนื้อหา','Content access'],identifier:['เลขประจำตัว','Identifier'],expires_at:['หมดอายุ','Expires'],version:['รุ่นข้อมูล','Record version'],id:['รหัสรายการ','Record ID']}
const hiddenKeys=['password_hash','csrf_token','file_base64']
const technicalKey=(key:string)=>/^(id|version)$|_ids?$|hash|sha256|_key$|snapshot|^provenance$|^usage$/.test(key)
const isoLike=/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/
export function formatMoment(value:unknown,lang:string){
 const text=String(value);if(!isoLike.test(text))return text
 const date=new Date(text);if(Number.isNaN(date.getTime()))return text
 return date.toLocaleString(lang==='en'?'en-GB':'th-TH',{dateStyle:'medium',timeStyle:'short'})
}
export const shortId=(id:unknown)=>{const text=String(id??'');return /^[0-9a-f]{8}-[0-9a-f]{4}-/.test(text)?text.slice(0,8):text}
function Value({value,lang,name}:{value:unknown;lang:string;name?:string}){
 if(name==='status'&&typeof value==='string')return <>{statusLabel(value,lang)} <code className="raw-state">{value}</code></>
 if(typeof value==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(value)){const date=new Date(value+'T00:00:00');if(!Number.isNaN(date.getTime()))return <time dateTime={value} title={value}>{date.toLocaleDateString(lang==='en'?'en-GB':'th-TH',{dateStyle:'long'})}</time>}
 if(typeof value==='boolean')return <>{value?(lang==='en'?'Yes':'ใช่'):(lang==='en'?'No':'ไม่ใช่')}</>
 if(Array.isArray(value)){
  if(value.every(x=>typeof x!=='object'))return <span className="value-chips">{value.map((x,i)=><span key={i}>{String(x)}</span>)}</span>
  return <>{value.map((x,i)=><div className="nested-value" key={i}>{typeof x==='object'?Object.entries(x||{}).map(([k,v])=><span key={k}><b>{k}: </b>{typeof v==='object'?JSON.stringify(v):String(v)} </span>):String(x)}</div>)}</>
 }
 if(value&&typeof value==='object')return <>{Object.entries(value as object).map(([k,v])=><p className="nested-value" key={k}><b>{k}: </b>{typeof v==='object'?JSON.stringify(v):String(v)}</p>)}</>
 const text=String(value)
 return isoLike.test(text)?<time dateTime={text} title={text}>{formatMoment(text,lang)}</time>:<>{text}</>
}
/** Readable fields first; identifiers, hashes and versions stay available in a collapsed section. */
export function DetailValues({record}:{record:Row}){
 const {lang,t}=useLang()
 const entries=Object.entries(record).filter(([key,value])=>!hiddenKeys.includes(key)&&value!==null&&value!==undefined)
 const main=entries.filter(([key])=>!technicalKey(key));const technical=entries.filter(([key])=>technicalKey(key))
 const term=(key:string)=>fieldNames[key]?.[lang==='en'?1:0]||key.replaceAll('_',' ')
 const list=(items:[string,unknown][],extra='')=><dl className={'detail-grid '+extra}>{items.map(([key,value])=><div key={key} className={typeof value==='object'||String(value).length>90?'wide':''}><dt>{term(key)}</dt><dd><Value value={value} lang={lang} name={key}/></dd></div>)}</dl>
 return <div className="detail-values">{main.length>0&&list(main)}{technical.length>0&&<details className="technical" open={main.length===0}><summary>{t('รายละเอียดทางเทคนิค','Technical details')} <span className="count">{technical.length}</span></summary>{list(technical,'technical-grid')}</details>}</div>
}
export function Alert({kind,children,role}:{kind:'error'|'info'|'success'|'warning';children:ReactNode;role?:'alert'|'status'}){
 return <div className={'alert '+kind} role={role||(kind==='error'?'alert':'status')}><Icon name={kind==='error'||kind==='warning'?'alert':kind==='success'?'check':'info'} size={18}/><div>{children}</div></div>
}
export function EmptyState({icon='inbox',title,children}:{icon?:string;title:string;children?:ReactNode}){
 return <div className="empty"><span className="empty-icon"><Icon name={icon} size={26}/></span><h3>{title}</h3>{children&&<p>{children}</p>}</div>
}
export function SkeletonRows({count=5,label}:{count?:number;label:string}){
 return <div className="skeleton-list" role="status" aria-label={label}>{Array.from({length:count},(_,i)=><div className="skeleton-row" key={i}><span/><span/></div>)}<span className="sr-only">{label}</span></div>
}
function rowMeta(row:Row,lang:string){
 const parts=[row.identifier,row.kind,row.domain,row.analyte,row.modality].filter(v=>typeof v==='string'&&v).map(String)
 if(typeof row.created_at==='string'&&isoLike.test(row.created_at))parts.push(new Date(row.created_at).toLocaleDateString(lang==='en'?'en-GB':'th-TH',{dateStyle:'medium'}))
 return parts
}
const rowTitle=(row:Row)=>String(row.display_name||row.title||row.name||row.label||row.reference||row.id)

export function ResourceWorkspace({resource,client,context,onSelectContext,readOnly=false}:{resource:Resource;client:Client;context:{patient_id:string;encounter_id:string};onSelectContext?:(row:Row)=>void;readOnly?:boolean}){
 const {lang,t}=useLang()
 const detailGeneration=useRef(0);const detailRef=useRef<HTMLElement>(null);const [versions,setVersions]=useState<Row[]>([]);
 const [items,setItems]=useState<Row[]>([]);const [selected,setSelected]=useState<Row|null>(null);const [history,setHistory]=useState<Row[]>([]);const [error,setError]=useState('');const [notice,setNotice]=useState('');const [noticeKind,setNoticeKind]=useState<'success'|'warning'>('success');const [busy,setBusy]=useState(false);const [create,setCreate]=useState(false);const [query,setQuery]=useState('');const [action,setAction]=useState<ActionDef|null>(null);const [pending,setPending]=useState<PendingOperation|null>(null);const [loaded,setLoaded]=useState(false)
 useEffect(()=>{window.dispatchEvent(new CustomEvent('his-pending',{detail:!!pending}));const warn=(event:BeforeUnloadEvent)=>{if(pending){event.preventDefault();event.returnValue=''}};window.addEventListener('beforeunload',warn);return()=>{window.removeEventListener('beforeunload',warn);window.dispatchEvent(new CustomEvent('his-pending',{detail:false}))}},[pending])
 const queryParams=new URLSearchParams();if(resource.patient_context&&context.patient_id)queryParams.set('patient_id',context.patient_id);if(resource.encounter_context&&context.encounter_id)queryParams.set('encounter_id',context.encounter_id)
 const listPath=resource.path+(queryParams.size?'?'+queryParams:'')
 async function refresh(){const generation=++detailGeneration.current;const data=rows(await client.get(listPath));if(generation!==detailGeneration.current)return data;setItems(data);setLoaded(true);if(selected){const latest=data.find(x=>x.id===selected.id);if(latest)setSelected(latest)}return data}
 useEffect(()=>{let active=true;detailGeneration.current++;setItems([]);setSelected(null);setHistory([]);setVersions([]);setLoaded(false);setError('');client.get(listPath).then(data=>{if(active){setItems(rows(data));setLoaded(true);const wanted=new URLSearchParams(location.search).get('record');if(wanted)choose(rows(data).find(r=>r.id===wanted)||{id:wanted})}}).catch(e=>{if(active)setError(errorText(e))});return()=>{active=false}},[client,listPath])
 async function choose(row:Row){if(pending)return;const generation=++detailGeneration.current;setAction(null);setSelected(row);setHistory([]);setVersions([]);setError('');
  // Single-column layouts place the detail below a long list; bring it to the reader.
  if(typeof window.matchMedia==='function'&&window.matchMedia('(max-width:1099px)').matches)setTimeout(()=>detailRef.current?.scrollIntoView?.({block:'start',behavior:'smooth'}),0)
  try{const detail=resource.detailPath===false?row:await client.get(resource.detailPath?.replace('{id}',row.id)||resource.path+'/'+row.id);if(generation!==detailGeneration.current)return;setSelected(detail);if(Array.isArray(detail.history)||Array.isArray(detail.events)){setHistory(rows(detail.history||detail.events))}else{try{const h=await client.get('audit?entity_id='+encodeURIComponent(row.id));if(generation===detailGeneration.current)setHistory(rows(h))}catch(e){if(generation===detailGeneration.current)setError(t('โหลดประวัติ audit ไม่สำเร็จ: ','Could not load the audit history: ')+errorText(e))}}if(resource.path==='documents'){const versions=await client.get('documents/'+row.id+'/versions');if(generation===detailGeneration.current)setVersions(rows(versions))}}catch(e){if(generation===detailGeneration.current)setError(errorText(e))}}
 async function run(op:PendingOperation){if(busy)return;setBusy(true);setError('');setNotice('');setPending(op);try{const data=await client.mutate(op.path,op.body,op.key,op.method);const record=(data.record||data.item||data.user||data) as Row;if(record.id){setItems(old=>normalizeMutation(old,record));setSelected(record)}setPending(null);setCreate(false);setAction(null);setNoticeKind('success');setNotice(t('บันทึกสำเร็จจากเซิร์ฟเวอร์แล้ว','Saved and confirmed by the server'));try{await refresh()}catch(e){setError(t('บันทึกสำเร็จ แต่โหลดรายการล่าสุดไม่สำเร็จ: ','Saved, but the latest list could not be loaded: ')+errorText(e))}}catch(e){setNoticeKind('warning');if(e instanceof HttpError&&e.definitive){setPending(null);setNotice(t('คำสั่งถูกปฏิเสธ ไม่เกิดรายการใหม่ สามารถโหลดข้อมูลล่าสุดและแก้ไขต่อได้','The request was rejected and nothing was written. Load the latest data and continue.'))}else setNotice(t('ยังไม่ทราบผลการบันทึก เก็บคำสั่งและ key เดิมไว้ กด retry เพื่อยืนยันโดยไม่สร้างรายการซ้ำ','The outcome is unknown. The same request and key are kept; retry to confirm without creating a duplicate.'));setError(errorText(e))}finally{setBusy(false)}}
 async function createRecord(values:FormValues){await run({path:resource.path,body:values,key:crypto.randomUUID()})}
 async function applyAction(values:FormValues){if(!selected||!action)return;await run({path:action.path? action.path.replace('{id}',selected.id):`${resource.path}/${selected.id}/actions`,body:{...(!action.omitVersion?{version:selected.version}:{}),...(!action.path?{action:action.name}:{}),...(action.target?{target:action.target}:{}),...values},key:crypto.randomUUID(),method:action.method})}
 const available=selected&&!readOnly?resource.actions.filter(a=>!a.from||a.from.includes(String(selected.status))):[]
 const filtered=items.filter(row=>Object.values(row).some(v=>typeof v!=='object'&&String(v).toLocaleLowerCase().includes(query.toLocaleLowerCase())))
 const loadingLabel=t('กำลังโหลดข้อมูล…','Loading records…')
 return <div className="workspace-stack">
  <section className="section-toolbar">
   <div><h2>{resource.label}</h2>{resource.description&&<p>{resource.description}</p>}</div>
   <div className="button-row">
    <button className="secondary" disabled={busy} onClick={()=>refresh().catch(e=>setError(errorText(e)))}>{t('โหลดล่าสุด','Refresh')}</button>
    {resource.fields.length>0&&!readOnly&&<button className="primary" disabled={busy||!!pending} aria-expanded={create} onClick={()=>{setCreate(!create);setAction(null)}}>{t('＋ เพิ่ม','＋ Add ')}{resource.label}</button>}
   </div>
  </section>
  {error&&<Alert kind="error">{error}</Alert>}
  {notice&&<Alert kind={noticeKind}>{notice}</Alert>}
  {pending&&!busy&&<div className="pending-banner"><Icon name="clock" size={18}/><span>{t('คำสั่งรอยืนยัน','Request awaiting confirmation')} · <code>{pending.key}</code></span><button className="secondary" onClick={()=>run(pending)}>{t('Retry ด้วยคำสั่งเดิม','Retry the same request')}</button></div>}
  {create&&<section className="form-card"><div className="section-heading"><h3>{t('＋ เพิ่ม','＋ Add ')}{resource.label}</h3><button className="text-button" onClick={()=>setCreate(false)}>{t('ปิด','Close')}</button></div><DataForm fields={resource.fields} initial={context} onSubmit={createRecord} busy={busy||!!pending} client={client}/></section>}
  {resource.path==='clinical/D15/records'&&<GrowthTimeline records={items}/>}
  <div className="record-layout">
   <section className="list-card">
    <div className="list-header">
     <label className="search-field"><span>{t('ค้นหาในรายการ','Search this list')}</span><Icon name="search" size={18}/><input value={query} onChange={e=>setQuery(e.target.value)} placeholder={t('รหัส ชื่อ หรือสถานะ…','ID, name or status…')}/></label>
     <span className="count-chip">{filtered.length} {t('รายการ','records')}</span>
    </div>
    {!loaded&&!error?<SkeletonRows label={loadingLabel}/>:filtered.length?<div className="record-list">{filtered.map(row=>{const title=rowTitle(row);return <button className={'record-button '+(selected?.id===row.id?'selected':'')} key={row.id} aria-current={selected?.id===row.id?'true':undefined} onClick={()=>choose(row)} disabled={!!pending}>
     <div><strong>{title}</strong><small className="record-meta">{rowMeta(row,lang).map((part,i)=><span key={i}>{part}</span>)}{title!==row.id&&<span className="record-id" title={row.id}>{row.id}</span>}</small></div>
     <Status value={row.status}/><span className="chevron"><Icon name="chevron" size={18}/></span>
    </button>})}</div>:<EmptyState title={query?t('ไม่พบรายการที่ตรงกับคำค้น','No records match your search'):t('ยังไม่มีรายการที่ตรงเงื่อนไข','No records yet')}>{query?t('ลองคำค้นอื่น หรือล้างช่องค้นหา','Try another term or clear the search'):t('เพิ่มข้อมูลหรือปรับบริบทผู้ป่วยเพื่อเริ่มงาน','Add a record or change the patient context to begin')}</EmptyState>}
   </section>
   <section className="detail-card" ref={detailRef}>{selected?<>
    <div className="detail-header">
     <div><h3>{String(selected.display_name||selected.title||selected.name||selected.id)}</h3><p className="record-ref"><span title={selected.id}>{t('รหัส','ID')} {selected.id}</span>{selected.version!==undefined&&<span>{t('รุ่น','v')} {selected.version}</span>}</p></div>
     <Status value={selected.status}/>
    </div>
    {(onSelectContext||available.length>0)&&<div className="actions-bar">
     {onSelectContext&&<button className="primary" onClick={()=>onSelectContext(selected)}>{t('ใช้รายการนี้เป็นบริบท','Use as working context')}</button>}
     {available.map(a=><button key={a.name} className={'secondary'+(action?.name===a.name?' pressed':'')} aria-pressed={action?.name===a.name} disabled={busy||!!pending} onClick={()=>setAction(a)}>{a.label}</button>)}
    </div>}
    {action&&<div className="action-form"><div className="section-heading"><h3>{action.label}</h3><button className="text-button" onClick={()=>setAction(null)}>{t('ยกเลิก','Cancel')}</button></div><p>{t('รายการ','Record')} {selected.id} · {t('รุ่น','version')} {selected.version}</p><DataForm key={action.name+selected.id+selected.version} fields={action.fields||[]} initial={{...selected,content_hash:selected.content_hash||(selected.current_version as Row|undefined)?.content_hash}} submitLabel={t('ยืนยัน','Confirm ')+action.label} client={client} busy={busy||!!pending} onSubmit={applyAction}/></div>}
    <DetailValues record={selected}/>
    {resource.path==='clinical/D11/records'&&!!selected.file_sha256&&<a className="download-link" href={'/api/v2/clinical/D11/records/'+selected.id+'/file'}>ดาวน์โหลดไฟล์สังเคราะห์ที่ตรวจ checksum แล้ว</a>}
    {resource.path==='clinical/D20/records'&&['exported','response_recorded','closed'].includes(String(selected.status))&&<a className="download-link" href={'/api/v2/clinical/D20/records/'+selected.id+'/export'} download>ดาวน์โหลดเอกสารส่งต่อ</a>}
    {resource.path==='erp/D36/records'&&selected.status==='exported'&&<a className="download-link" href={'/api/v2/erp/datasets/'+selected.id+'/export'} download>ดาวน์โหลดชุดข้อมูลที่อนุมัติ</a>}
    <div className="document-versions">{versions.length>0&&<details><summary>{t('ประวัติเนื้อหาเอกสาร','Document revisions')} ({versions.length} {t('ฉบับ','revisions')})</summary>{versions.map(v=><article key={v.id}><h4>{t('ฉบับ','Revision')} {v.version} · {String(v.created_by)}</h4><p className="document-content">{String(v.content)}</p><small>{formatMoment(v.created_at,lang)} · {String(v.reason||t('ต้นฉบับ','Original'))}</small><p className="hash" title="content hash">{String(v.content_hash)}</p></article>)}</details>}</div>
    <details className="history" open><summary>{t('ประวัติการทำรายการ','Activity history')} ({history.length})</summary>{history.length?<ol>{history.map(h=><li key={h.id}><strong>{String(h.action||h.event)}</strong><span>{String(h.actor_id||h.actor)} · {formatMoment(h.created_at||h.created,lang)}</span></li>)}</ol>:<p className="muted">{t('ยังไม่มีประวัติที่คุณมีสิทธิ์อ่านสำหรับรายการนี้','No history you are permitted to read for this record')}</p>}</details>
   </>:<EmptyState icon="document" title={t('เลือกรายการเพื่อทำงาน','Select a record to work on')}>{t('รายละเอียด รุ่นข้อมูล และคำสั่งตามสถานะจะแสดงที่นี่','Details, record version and the actions allowed in its state appear here')}</EmptyState>}</section>
  </div>
 </div>
}
