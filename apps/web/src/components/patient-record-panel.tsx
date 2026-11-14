import {useEffect,useId,useRef,useState} from 'react'
import {createPortal} from 'react-dom'
import {Client,errorText,hasPermission,rows,type Row,type Session} from '../lib/client'
import {Alert,EmptyState,SkeletonRows,formatMoment,statusLabel} from './workspace'
import {Icon} from './icons'
import {useLang} from '../lib/i18n'
import {patientSummary,visitReferenceText} from '../lib/patient-display'

export type PatientRecordRequest={patient_id:string;encounter_id?:string;document_id?:string;task_id?:string}
type LoadedRecord={binding:string;patient:Row|null;encounters:Row[];documents:Row[];tasks:Row[];errors:string[]}

/** Read-only patient view. All writes remain in the original scoped workspaces. */
export function PatientRecordPanel({client,session,request,onClose,onNavigate}:{client:Client;session:Session;request:PatientRecordRequest;onClose:()=>void;onNavigate:(path:string)=>void}){
 const {lang,t}=useLang();const titleId=useId();const overlay=useRef<HTMLDivElement>(null);const closeButton=useRef<HTMLButtonElement>(null);const closeRef=useRef(onClose);closeRef.current=onClose
 const [loaded,setLoaded]=useState<LoadedRecord|null>(null),[selectedDocument,setSelectedDocument]=useState(''),[selectedTask,setSelectedTask]=useState('')
 const binding=[session.user.id,session.user.facility_id,request.patient_id,request.encounter_id||'',request.document_id||'',request.task_id||''].join('|')
 const data=loaded?.binding===binding?loaded:null
 const canDocuments=hasPermission(session.user,'D22'),canReview=hasPermission(session.user,'D37'),canVisit=hasPermission(session.user,'D03')
 useEffect(()=>{
  const previous=document.activeElement instanceof HTMLElement?document.activeElement:null
  const background=[...document.body.children].filter(element=>element!==overlay.current&&element instanceof HTMLElement) as HTMLElement[]
  const previousInert=background.map(element=>element.hasAttribute('inert'));background.forEach(element=>element.setAttribute('inert',''))
  const overflow=document.body.style.overflow;document.body.style.overflow='hidden';closeButton.current?.focus()
  const key=(event:KeyboardEvent)=>{
   if(event.key==='Escape'){event.preventDefault();event.stopPropagation();closeRef.current();return}
   if(event.key!=='Tab')return
   const controls=[...overlay.current!.querySelectorAll<HTMLElement>('button:not(:disabled),a[href],summary,input:not(:disabled),select:not(:disabled),[tabindex="0"]')].filter(element=>{let current:HTMLElement|null=element;while(current&&current!==overlay.current){const style=window.getComputedStyle(current);if(current.hidden||current.hasAttribute('inert')||style.display==='none'||style.visibility==='hidden')return false;current=current.parentElement}return true})
   const first=controls[0],last=controls[controls.length-1];if(!first)return
   if(event.shiftKey&&(document.activeElement===first||!overlay.current?.contains(document.activeElement))){event.preventDefault();last.focus()}
   else if(!event.shiftKey&&(document.activeElement===last||!overlay.current?.contains(document.activeElement))){event.preventDefault();first.focus()}
  }
  document.addEventListener('keydown',key,true)
  return()=>{document.removeEventListener('keydown',key,true);background.forEach((element,index)=>{if(!previousInert[index])element.removeAttribute('inert')});document.body.style.overflow=overflow;if(previous?.isConnected)previous.focus()}
 },[])
 useEffect(()=>{
  let active=true;setLoaded(null);setSelectedDocument('');setSelectedTask('')
  const errors:string[]=[];const fetchRows=async(path:string,label:string)=>{try{return rows(await client.get(path))}catch(error){errors.push(label+': '+errorText(error));return []}}
  const canPatientReference=session.user.permissions.includes('patient.reference')||session.user.permissions.includes('*')
  const canEncounterReference=session.user.permissions.includes('encounter.reference')||session.user.permissions.includes('*')
  const suffix=request.encounter_id?'?encounter_id='+encodeURIComponent(request.encounter_id):''
  Promise.all([
   hasPermission(session.user,'D01')?fetchRows('patients','Patient information'):canPatientReference?fetchRows('reference/patients','Patient information'):Promise.resolve([]),
   canVisit?fetchRows('encounters?patient_id='+encodeURIComponent(request.patient_id),'Visits'):canEncounterReference?fetchRows('reference/encounters?patient_id='+encodeURIComponent(request.patient_id),'Visits'):Promise.resolve([]),
   canDocuments?fetchRows('documents'+suffix,'Documents'):Promise.resolve([]),
   canReview?fetchRows('tasks'+suffix,'Review tasks'):Promise.resolve([]),
  ]).then(([patients,encounters,documents,tasks])=>{
   if(!active)return
   const matches=(row:Row)=>row.patient_id===request.patient_id&&(!request.encounter_id||row.encounter_id===request.encounter_id)
   setLoaded({binding,patient:patients.find(row=>row.id===request.patient_id)||null,encounters:encounters.filter(row=>row.patient_id===request.patient_id),documents:documents.filter(matches),tasks:tasks.filter(matches),errors})
  })
  return()=>{active=false}
 },[client,binding])
 const selected=data?.documents.find(row=>row.id===(selectedDocument||request.document_id))||(!request.document_id?data?.documents[0]:undefined)
 const reviewTasks=selected?data?.tasks.filter(row=>row.domain==='D37'&&row.kind==='document_review'&&row.patient_id===selected.patient_id&&row.encounter_id===selected.encounter_id)||[]:[]
 const reviewTask=reviewTasks.find(row=>row.id===(selectedTask||request.task_id))||(!request.task_id&&!selectedTask&&reviewTasks.length===1?reviewTasks[0]:undefined)
 const encounter=data?.encounters.find(row=>row.id===(selected?.encounter_id||request.encounter_id))
 function path(domain:string,extra:Record<string,string>={}){return '/domains/'+domain+'?'+new URLSearchParams({patient_id:request.patient_id,...((selected?.encounter_id||request.encounter_id)?{encounter_id:String(selected?.encounter_id||request.encounter_id)}:{}),...extra})}
 return createPortal(<div className="patient-record-overlay" ref={overlay} onMouseDown={event=>{if(event.target===event.currentTarget)onClose()}}>
  <section className="patient-record-dialog" role="dialog" aria-modal="true" aria-labelledby={titleId}>
   <header className="patient-record-dialog-header"><div><span className="patient-record-eyebrow">Patient record</span><h2 id={titleId}>{data?.patient?.display_name?String(data.patient.display_name):request.patient_id}</h2><p title={String(selected?.encounter_id||request.encounter_id||'')}>{patientSummary(data?.patient||{id:request.patient_id},lang).join(' · ')}{(selected?.encounter_id||request.encounter_id)?' · '+visitReferenceText(encounter,lang,selected?.encounter_id||request.encounter_id):''}{encounter?' · '+statusLabel(String(encounter.status),'en'):''}</p></div><button ref={closeButton} className="icon-button patient-record-close" aria-label="Close patient record" onClick={onClose}><span aria-hidden="true">×</span></button></header>
   <div className="patient-record-body">
    {!data?<SkeletonRows count={5} label={t('กำลังโหลดแฟ้มผู้ป่วย','Loading patient record')}/>:<>
     {data.errors.map((error,index)=><Alert key={index} kind="error">{error}</Alert>)}
     <div className="patient-record-section-bar"><h3>Documents <span>{data.documents.length}</span></h3><p>{t('เลือกเอกสารเพื่ออ่านต้นฉบับ ก่อนเปิดพื้นที่ทบทวน','Read the source before opening the review workspace.')}</p></div>
     {!canDocuments?<Alert kind="warning">{t('บัญชีนี้ไม่มีสิทธิ์อ่านเอกสาร','This account is not permitted to view documents.')}</Alert>:data.documents.length?<><label className="patient-record-mobile-document"><span>Document</span><select value={selected?.id||''} onChange={event=>{setSelectedDocument(event.target.value);setSelectedTask('')}}><option value="" disabled>Select a document</option>{data.documents.map(doc=><option key={doc.id} value={doc.id}>{String(doc.title||doc.id)}</option>)}</select></label><div className="patient-record-reading-layout">
      <nav className="patient-record-document-list" aria-label="Patient documents">{data.documents.map(doc=><button className={'patient-record-document '+(selected?.id===doc.id?'selected':'')} key={doc.id} aria-current={selected?.id===doc.id?'true':undefined} onClick={()=>{setSelectedDocument(doc.id);setSelectedTask('')}}><strong>{String(doc.title||doc.id)}</strong><span title={String(doc.encounter_id)}>{visitReferenceText(data.encounters.find(visit=>visit.id===doc.encounter_id),lang,doc.encounter_id)} · {statusLabel(String(doc.status||''),'en')}</span><small>{typeof doc.created_at==='string'?formatMoment(doc.created_at,lang):doc.version!==undefined?'Record v'+String(doc.version):''}</small></button>)}</nav>
      <article className="patient-record-source" aria-label="Selected source document">{selected?<><div className="patient-record-source-heading"><h3>{String(selected.title||selected.id)}</h3><p title={String(selected.encounter_id)}>{visitReferenceText(encounter,lang,selected.encounter_id)}{selected.version!==undefined?' · Record v'+String(selected.version):''}</p></div>{typeof selected.content==='string'?<p className="document-content">{selected.content}</p>:<Alert kind="info">{t('บัญชีนี้อ่านได้เฉพาะข้อมูลเอกสาร ไม่มีสิทธิ์อ่านเนื้อหา','This account can view document metadata; source content is restricted.')}</Alert>}</>:<EmptyState title={t('เอกสารที่เปิดไว้ไม่อยู่ในบริบทนี้','The requested document is unavailable in this context')}>{t('เลือกเอกสารจากรายการที่คุณมีสิทธิ์อ่าน','Choose a document from the list you are permitted to view.')}</EmptyState>}</article>
     </div></>:data.errors.some(error=>error.startsWith('Documents:'))?null:<EmptyState icon="document" title={t('ยังไม่มีเอกสารในบริบทนี้','No documents in this context')}>{t('เปิดพื้นที่เอกสารเพื่อเพิ่มหรือเลือกเอกสารของผู้ป่วย','Open the document workspace to add or choose a patient document.')}</EmptyState>}
     {data.encounters.length>0&&<details className="patient-record-visits"><summary>Visits ({data.encounters.length})</summary><ul>{data.encounters.map(visit=><li key={visit.id}><span title={visit.id}>{visitReferenceText(visit,lang)}</span><span>{statusLabel(String(visit.status||''),'en')}</span>{canVisit&&<button className="text-button" onClick={()=>onNavigate('/domains/D03?'+new URLSearchParams({patient_id:request.patient_id,encounter_id:visit.id,record:visit.id}))}>Open visit</button>}</li>)}</ul></details>}
    </>}
   </div>
   <footer className="patient-record-dialog-footer"><p>{t('เลือกเอกสาร แล้วเปิดงานที่ต้องการ','Choose a document, then open the work you need.')}</p><div className="button-row">{(reviewTasks.length>1||reviewTasks.length>0&&!reviewTask)&&<label className="patient-record-task-choice"><span>Review task</span><select value={reviewTask?.id||''} onChange={event=>setSelectedTask(event.target.value)}><option value="">Select a review task</option>{reviewTasks.map(task=><option key={task.id} value={task.id}>{String(task.title||task.id)} · {statusLabel(String(task.status),'en')}</option>)}</select></label>}{canVisit&&request.encounter_id&&<button className="secondary" disabled={!data} onClick={()=>onNavigate(path('D03',{record:request.encounter_id!}))}>Open visit</button>}{canDocuments&&<button className="secondary" disabled={!data||!!request.document_id&&!selected||data.errors.some(error=>error.startsWith('Documents:'))} onClick={()=>onNavigate(path('D22',selected?{record:selected.id}:{}))}>Open document</button>}{canReview&&selected&&reviewTask&&<button className="primary" onClick={()=>onNavigate(path('D37',{task_id:reviewTask.id,document_id:selected.id}))}>Open review <Icon name="chevron" size={14}/></button>}</div></footer>
  </section>
 </div>,document.body)
}
