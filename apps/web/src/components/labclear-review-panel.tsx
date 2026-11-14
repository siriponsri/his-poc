import {useEffect,useId,useRef,useState} from 'react'
import {createPortal} from 'react-dom'
import {Client,HttpError,rows,type PendingOperation,type Row} from '../lib/client'
import {useLang} from '../lib/i18n'

type Context={patient_id:string;encounter_id:string}
type Cell={source_index:number;name:string;value:string;unit:string;reference:string;printed_flag:string;id?:string;status?:string}
type Binding=Row&{patient_id:string;encounter_id:string;task_id:string;source_id:string;source_version:number;source_sha256:string;state:string}
type Receipt={state:'draft'|'confirmed';source:{record_id:string;version:number;sha256:string};fields:Cell[];review:null|{reviewer_id:string;revision:number;sha256:string}}
type Operation=PendingOperation&{kind:'task'|'import'|'confirm'}
const cellsValid=(value:unknown):value is Cell[]=>Array.isArray(value)&&value.length===1&&value.every((cell,index)=>cell&&cell.source_index===index&&(['name','value','unit','reference','printed_flag'] as const).every(key=>typeof cell[key]==='string'&&cell[key].length<={name:100,value:150,unit:60,reference:150,printed_flag:25}[key])&&!!cell.name.trim())
const scopedTask=(task:Row,context:Context)=>task.domain==='D10'&&task.kind==='labclear_review'&&task.patient_id===context.patient_id&&task.encounter_id===context.encounter_id
const activeTask=(task:Row,context:Context)=>scopedTask(task,context)&&['open','in_progress'].includes(String(task.status))
const sourceMatches=(source:Row,context:Context)=>!!context.patient_id&&!!context.encounter_id&&source.patient_id===context.patient_id&&source.encounter_id===context.encounter_id&&['released','corrected'].includes(String(source.status))&&Number.isInteger(source.version)&&typeof source.analyte==='string'&&typeof source.result_value==='string'

/** Human review of a released laboratory source, never an automatic release. */
export function LabClearReviewPanel({client,source,context,onClose}:{client:Client;source:Row;context:Context;onClose:()=>void}){
 const {t}=useLang(),titleId=useId(),overlay=useRef<HTMLDivElement>(null),closeButton=useRef<HTMLButtonElement>(null)
 const identity=JSON.stringify([context.patient_id,context.encounter_id,source.id,source.version,source.status,source.analyte,source.result_value,source.unit,source.reference_range]),currentIdentity=useRef(identity);currentIdentity.current=identity
 const generation=useRef(0),mounted=useRef(true),closeRef=useRef(onClose);closeRef.current=onClose
 const [loaded,setLoaded]=useState(''),[available,setAvailable]=useState(false),[loadFailed,setLoadFailed]=useState(false),[reload,setReload]=useState(0),[names,setNames]=useState<{identity:string;patient:string;visit:string;visitStatus:string}|null>(null),[tasks,setTasks]=useState<Row[]>([]),[taskStates,setTaskStates]=useState<Row[]>([]),[taskId,setTaskId]=useState(''),[bindings,setBindings]=useState<Binding[]>([]),[binding,setBinding]=useState<Binding|null>(null),[receipt,setReceipt]=useState<Receipt|null>(null),[fields,setFields]=useState<Cell[]>([]),[confirmedPerson,setConfirmedPerson]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState(''),[busy,setBusy]=useState(false),[pending,setPending]=useState<Operation|null>(null)
 const pendingRef=useRef<Operation|null>(pending);pendingRef.current=pending
 const [retryAllowed,setRetryAllowed]=useState(true)
 const [needsRecovery,setNeedsRecovery]=useState(false)
 const matches=sourceMatches(source,context),ready=loaded===identity&&matches
 const named=names?.identity===identity?names:null
 const closedVisit=!!named&&['closed','completed','discharged','cancelled'].includes(named.visitStatus)
 const historical=closedVisit||!!binding&&taskStates.some(task=>task.id===binding.task_id&&task.status==='completed')
 function messageFor(cause:unknown){
  if(cause instanceof HttpError){
   if(cause.message==='CONNECTOR_PENDING_RECOVERY_REQUIRED')return t('มีคำสั่งเดิมที่ต้องตรวจผลก่อนเริ่มใหม่','An earlier request needs to be recovered before starting another.')
   if(cause.status===401)return t('เซสชันหมดอายุ กรุณาเข้าสู่ระบบอีกครั้ง','Your session expired. Sign in again.')
   if(cause.status===403)return t('บัญชีนี้ไม่มีสิทธิ์ทบทวนผลตรวจนี้','This account is not permitted to review this result.')
   if(cause.status===404)return t('ไม่พบการทบทวนในขอบเขตที่คุณเข้าถึงได้','This review is unavailable in your current scope.')
   if(cause.status===409)return t('ต้นฉบับ สถานะงาน หรือสิทธิ์เปลี่ยนแล้ว กรุณาตรวจข้อมูลล่าสุด','The source, task or access changed. Check the latest information.')
   if(cause.status===422)return t('โปรดตรวจรายการ ค่า หน่วย และการยืนยันให้ครบ','Check every test, value, unit and confirmation.')
   if(cause.message==='LABCLEAR_REQUEST_REJECTED')return t('LabClear ไม่รับคำสั่งนี้ กรุณาตรวจข้อมูลก่อนลองใหม่','LabClear rejected this request. Check the source before trying again.')
   if(cause.message==='LABCLEAR_CONNECTOR_UNAVAILABLE')return t('ยังเชื่อมต่อ LabClear ไม่ได้ในขณะนี้','The LabClear connection is currently unavailable.')
   return t('ยังยืนยันผลตอบกลับไม่ได้ กรุณาลองตรวจอีกครั้ง','The response could not be confirmed. Try checking again.')
  }
  return cause instanceof Error?cause.message:t('โหลดการทบทวนไม่สำเร็จ','The review could not be loaded.')
 }
 const bindingMatches=(value:Binding)=>value.patient_id===context.patient_id&&value.encounter_id===context.encounter_id&&value.source_id===source.id&&value.source_version===source.version
 function requestClose(){if(pendingRef.current){setNotice(t('ยังไม่ทราบผลคำสั่ง กรุณาตรวจผลด้วยคำสั่งเดิมก่อนปิด','Confirm the pending request with the same command before closing.'));return}closeRef.current()}
 useEffect(()=>{
  mounted.current=true;const previous=document.activeElement instanceof HTMLElement?document.activeElement:null
  const background=[...document.body.children].filter(element=>element!==overlay.current&&element instanceof HTMLElement) as HTMLElement[]
  const previousInert=background.map(element=>element.hasAttribute('inert'));background.forEach(element=>element.setAttribute('inert',''))
  const overflow=document.body.style.overflow;document.body.style.overflow='hidden';closeButton.current?.focus()
  const key=(event:KeyboardEvent)=>{
   if(event.key==='Escape'){event.preventDefault();event.stopPropagation();requestClose();return}
   if(event.key!=='Tab')return
   const controls=[...overlay.current!.querySelectorAll<HTMLElement>('button:not(:disabled),a[href],summary,input:not(:disabled),select:not(:disabled),[tabindex="0"]')].filter(element=>{let node:HTMLElement|null=element;while(node&&node!==overlay.current){const style=window.getComputedStyle(node);if(node.hidden||node.hasAttribute('inert')||style.display==='none'||style.visibility==='hidden')return false;node=node.parentElement}return true})
   const first=controls[0],last=controls[controls.length-1];if(!first)return
   if(event.shiftKey&&(document.activeElement===first||!overlay.current?.contains(document.activeElement))){event.preventDefault();last.focus()}
   else if(!event.shiftKey&&(document.activeElement===last||!overlay.current?.contains(document.activeElement))){event.preventDefault();first.focus()}
  }
  document.addEventListener('keydown',key,true)
  return()=>{mounted.current=false;generation.current++;document.removeEventListener('keydown',key,true);background.forEach((element,index)=>{if(!previousInert[index])element.removeAttribute('inert')});document.body.style.overflow=overflow;if(previous?.isConnected)previous.focus({preventScroll:true})}
 },[])
 useEffect(()=>{window.dispatchEvent(new CustomEvent('his-pending',{detail:!!pending}));const warn=(event:BeforeUnloadEvent)=>{if(pending){event.preventDefault();event.returnValue=''}};window.addEventListener('beforeunload',warn);return()=>{window.removeEventListener('beforeunload',warn);window.dispatchEvent(new CustomEvent('his-pending',{detail:false}))}},[pending])
 useEffect(()=>{
  const token=++generation.current;setLoaded('');setAvailable(false);setLoadFailed(false);setTasks([]);setTaskStates([]);setTaskId('');setBindings([]);setBinding(null);setReceipt(null);setFields([]);setConfirmedPerson(false);setError('');setNotice('');setPending(null);setRetryAllowed(true);setNeedsRecovery(false);setBusy(false)
  if(!matches)return
  const query=new URLSearchParams(context)
  Promise.all([client.get('integrations/labclear/bindings?'+query),client.get('tasks?'+query)]).then(([linked,taskRows])=>{
   if(!mounted.current||generation.current!==token||currentIdentity.current!==identity)return
   const scoped=rows(taskRows).filter(row=>scopedTask(row,context)),eligible=scoped.filter(row=>activeTask(row,context)),existing=rows(linked).filter(row=>bindingMatches(row as Binding)) as Binding[]
   setAvailable(linked.available===true);setTaskStates(scoped);setTasks(eligible);setTaskId(eligible.length===1?eligible[0].id:'');setBindings(existing);if(existing.length===1)setBinding(existing[0]);setLoaded(identity)
  }).catch(cause=>{if(mounted.current&&generation.current===token&&currentIdentity.current===identity){setError(messageFor(cause));setLoadFailed(true);setLoaded(identity)}})
 },[client,identity,reload])
 useEffect(()=>{
  let active=true;setNames(null)
  if(!matches)return
  Promise.allSettled([client.get('reference/patients'),client.get('reference/encounters?patient_id='+encodeURIComponent(context.patient_id))]).then(([people,visits])=>{
   if(!active||!mounted.current||currentIdentity.current!==identity)return
   const patient=people.status==='fulfilled'?rows(people.value).find(row=>row.id===context.patient_id):undefined
   const visit=visits.status==='fulfilled'?rows(visits.value).find(row=>row.id===context.encounter_id&&row.patient_id===context.patient_id):undefined
   setNames({identity,patient:typeof patient?.display_name==='string'?patient.display_name:'',visit:typeof visit?.kind==='string'?visit.kind:'',visitStatus:typeof visit?.status==='string'?visit.status:''})
  }).catch(()=>{/* Optional minimum reference metadata never grants connector access. */})
  return()=>{active=false}
 },[client,identity])
 function accept(data:any,expectedBinding?:string,expectedTask?:string){
  const next=data?.binding as Binding|undefined,review=data?.receipt as Receipt|undefined
  if(!next||!bindingMatches(next)||typeof next.id!=='string'||!next.id||!/^([0-9a-f]{64})$/.test(next.source_sha256)||(expectedBinding&&next.id!==expectedBinding)||(expectedTask&&next.task_id!==expectedTask)||!review||review.source?.record_id!==source.id||review.source.version!==source.version||review.source.sha256!==next.source_sha256||!cellsValid(review.fields)||!['draft','confirmed'].includes(review.state)||review.state!==next.state)throw new Error(t('ผลตอบกลับไม่ตรงกับต้นฉบับที่เปิดอยู่','The response does not match the selected source.'))
  setBinding(next);setBindings(previous=>previous.some(item=>item.id===next.id)?previous.map(item=>item.id===next.id?next:item):[next,...previous]);setReceipt(review);setFields(review.fields.map(({source_index,name,value,unit,reference,printed_flag})=>({source_index,name,value,unit,reference,printed_flag})));setConfirmedPerson(false)
 }
 async function run(operation:Operation){
  if(busy||!ready)return
  const token=generation.current,captured=identity;setPending(operation);setRetryAllowed(true);setNeedsRecovery(false);setBusy(true);setError('');setNotice('')
  try{
   const data=await client.mutate(operation.path,operation.body,operation.key)
   if(!mounted.current||generation.current!==token||currentIdentity.current!==captured)return
   if(operation.kind==='task'){
    if(!data?.id||!activeTask(data,context))throw new Error(t('งานที่ได้ไม่ตรงกับผู้ป่วยและการรับบริการนี้','The task does not match this patient and visit.'))
    setTasks(previous=>previous.some(item=>item.id===data.id)?previous:[...previous,data]);setTaskId(data.id);setPending(null);setNotice(t('สร้างงานทบทวนแล้ว เลือกส่งค่าต้นฉบับเมื่อพร้อม','Review task created. Send the source values when ready.'));return
   }
   if(data?.retry_same_key===true&&['running','unknown'].includes(data.outcome)&&data.receipt===null){if(data.binding&&bindingMatches(data.binding))setBinding(data.binding);setNotice(t('กำลังตรวจผลคำสั่ง เก็บคำสั่งเดิมไว้เพื่อไม่สร้างรายการซ้ำ','The outcome is pending. Retry the same request to avoid a duplicate.'));return}
   accept(data,operation.kind==='confirm'?binding?.id:undefined,operation.kind==='import'?String(operation.body.task_id):undefined);setPending(null);setNotice(operation.kind==='confirm'?t('ยืนยันการทบทวนแล้ว ผลแล็บต้นฉบับยังคงเดิม','Review confirmed. The original laboratory result is unchanged.'):t('ได้รับค่าต้นฉบับแล้ว โปรดตรวจเทียบก่อนยืนยัน','Source values received. Check them before confirming.'))
  }catch(cause){if(mounted.current&&generation.current===token&&currentIdentity.current===captured){setError(messageFor(cause));const knownGatewayRejection=cause instanceof HttpError&&((cause.status===502&&cause.message==='LABCLEAR_REQUEST_REJECTED')||(cause.status===503&&cause.message==='LABCLEAR_CONNECTOR_UNAVAILABLE'));if(cause instanceof HttpError&&(cause.definitive||knownGatewayRejection)){setPending(null);setNotice(t('คำสั่งถูกปฏิเสธ กรุณาโหลดข้อมูลรุ่นล่าสุดก่อนลองใหม่','The request was rejected. Load the latest source before trying again.'));if(cause.message==='CONNECTOR_PENDING_RECOVERY_REQUIRED'){
    setNeedsRecovery(true);setNotice(t('มีคำสั่งเดิมที่ยังไม่ทราบผล กรุณากู้คืนคำสั่งนั้นก่อนเริ่มใหม่','Another request is unresolved. Recover that original command before starting again.'))
    try{const linked=await client.get('integrations/labclear/bindings?'+new URLSearchParams(context));if(mounted.current&&generation.current===token&&currentIdentity.current===captured){const existing=rows(linked).filter(row=>bindingMatches(row as Binding)&&(operation.kind!=='import'||row.task_id===operation.body.task_id)) as Binding[];setBindings(existing);setBinding(existing.find(item=>item.id===binding?.id)||(existing.length===1?existing[0]:null))}}catch(loadError){if(mounted.current&&generation.current===token&&currentIdentity.current===captured)setError(messageFor(loadError))}
   }}else setNotice(t('ยังไม่ทราบผลคำสั่ง กรุณาใช้ Retry ด้วยคำสั่งเดิม','The outcome is unknown. Retry using the same request.'))}}
  finally{if(mounted.current&&generation.current===token&&currentIdentity.current===captured)setBusy(false)}
 }
 async function readReview(afterRecovery=false){
  if(!binding||busy||pending&&!afterRecovery||!ready)return
  const token=generation.current,captured=identity;setBusy(true);setError('');setReceipt(null);setFields([])
  try{const data=await client.mutate('integrations/labclear/bindings/'+encodeURIComponent(binding.id)+'/read',{});if(mounted.current&&generation.current===token&&currentIdentity.current===captured){if(data?.receipt)accept(data,binding.id);else setNotice(t('ยังไม่พบผลที่ยืนยันได้ ลองตรวจผลอีกครั้ง','No confirmed response is available yet. Check again.'))}}
  catch(cause){if(mounted.current&&generation.current===token&&currentIdentity.current===captured)setError(messageFor(cause))}
  finally{if(mounted.current&&generation.current===token&&currentIdentity.current===captured)setBusy(false)}
 }
 async function recoverReview(){
  if(!binding||busy||!ready)return
  const token=generation.current,captured=identity;setBusy(true);setError('')
  let readAfterRecovery=false
  try{
   const data=await client.mutate('integrations/labclear/bindings/'+encodeURIComponent(binding.id)+'/recover',{})
   if(!mounted.current||generation.current!==token||currentIdentity.current!==captured)return
   if(!data?.binding||!bindingMatches(data.binding)||data.binding.id!==binding.id||!/^([0-9a-f]{64})$/.test(data.binding.source_sha256)||typeof data.retry_allowed!=='boolean')throw Error(t('ไม่สามารถยืนยันคำสั่งเดิมได้','The original request could not be verified.'))
   if(data.pending===null){setPending(null);setRetryAllowed(true);setNeedsRecovery(false);setNotice('');readAfterRecovery=true}
   else{
    const operation=data.pending,body=operation?.body,kind=operation?.kind
    const path=kind==='import'?'integrations/labclear/import':kind==='confirm'?'integrations/labclear/bindings/'+encodeURIComponent(binding.id)+'/confirm':''
    const validBody=kind==='import'?body?.patient_id===context.patient_id&&body.encounter_id===context.encounter_id&&body.task_id===data.binding.task_id&&body.source_id===source.id&&body.source_version===source.version:body?.source_version===source.version&&body.source_sha256===data.binding.source_sha256&&body.same_person_confirmed===true&&cellsValid(body.fields)
    if(!path||operation.path!==path||operation.method!=='POST'||typeof operation.key!=='string'||!operation.key||operation.key.length>120||!validBody)throw Error(t('คำสั่งที่กู้คืนไม่ตรงกับต้นฉบับนี้','The recovered request does not match this source.'))
    setBinding(data.binding);setPending({kind,path,body,key:operation.key,method:'POST'});setRetryAllowed(data.retry_allowed);setNeedsRecovery(false);setReceipt(null);setFields(kind==='confirm'?body.fields.map((cell:Cell)=>({...cell})):[]);setConfirmedPerson(false)
    setNotice(t('พบคำสั่งเดิมที่ยังไม่ทราบผล ตรวจต้นฉบับแล้วเลือกทำคำสั่งเดิมต่อเมื่อพร้อม','An unresolved request was restored. Check the source, then explicitly resume the same command when ready.'))
   }
  }catch(cause){if(mounted.current&&generation.current===token&&currentIdentity.current===captured)setError(messageFor(cause))}
  finally{if(mounted.current&&generation.current===token&&currentIdentity.current===captured)setBusy(false)}
  if(readAfterRecovery&&mounted.current&&generation.current===token&&currentIdentity.current===captured)await readReview(true)
 }
 function openReview(){
  if(binding&&typeof binding.external_report_id==='string'&&binding.external_report_id&&(binding.state==='confirmed'||historical))void readReview()
  else void recoverReview()
 }
 const canRead=ready&&available&&!busy&&!pending&&!needsRecovery,canWork=canRead&&!closedVisit
 const isConfirmed=receipt?.state==='confirmed',readOnly=isConfirmed||historical,locked=!!pending||busy||readOnly
 const createTask=()=>run({kind:'task',path:'tasks',key:crypto.randomUUID(),body:{...context,domain:'D10',kind:'labclear_review',title:'LabClear review · '+String(source.analyte)}})
 const sendValues=()=>taskId&&run({kind:'import',path:'integrations/labclear/import',key:crypto.randomUUID(),body:{...context,task_id:taskId,source_id:source.id,source_version:source.version}})
 const confirmReview=()=>binding&&confirmedPerson&&run({kind:'confirm',path:'integrations/labclear/bindings/'+encodeURIComponent(binding.id)+'/confirm',key:crypto.randomUUID(),body:{fields:fields.map(cell=>({...cell})),same_person_confirmed:true,source_version:binding.source_version,source_sha256:binding.source_sha256}})
 return createPortal(<div className="labclear-review-overlay" ref={overlay} onMouseDown={event=>{if(event.target===event.currentTarget)requestClose()}}><section className="labclear-review-dialog" role="dialog" aria-modal="true" aria-labelledby={titleId}>
  <header className="labclear-review-header"><div><span className="labclear-review-eyebrow">CareBalance / LabClear</span><h2 id={titleId}>Lab result review</h2><p>{t('ตรวจค่าที่เผยแพร่แล้ว แล้วแยกยืนยันการทบทวน','Check the released source, then confirm this review separately.')}</p></div><button ref={closeButton} className="icon-button" aria-label="Close LabClear review" disabled={!!pending} onClick={requestClose}>×</button></header>
  <div className="labclear-review-body">
   {!matches?<p role="alert">{t('ต้นฉบับนี้ไม่ตรงกับผู้ป่วยและการรับบริการที่เลือก หรือยังไม่เผยแพร่','This source is unavailable for the selected patient and visit, or has not been released.')}</p>:<>
    <div className="labclear-review-context"><strong>{named?.patient||t('ผู้ป่วยที่เลือก','Selected patient')}</strong><span>{named?.visit||t('การรับบริการปัจจุบัน','Current visit')}</span><span>{String(source.analyte)}</span><span>Source v{source.version}</span></div>
    <section aria-labelledby={titleId+'-source'}><h3 id={titleId+'-source'}>Released source</h3><dl className="labclear-source-cells"><div><dt>Test</dt><dd>{String(source.analyte)}</dd></div><div><dt>Printed value</dt><dd>{String(source.result_value)}</dd></div><div><dt>Unit</dt><dd>{source.unit===null||source.unit===undefined?'—':String(source.unit)}</dd></div><div><dt>Printed reference</dt><dd>{source.reference_range===null||source.reference_range===undefined?'—':String(source.reference_range)}</dd></div></dl><details className="labclear-review-technical"><summary>Source details</summary><dl><dt>Patient reference</dt><dd>{context.patient_id}</dd><dt>Visit reference</dt><dd>{context.encounter_id}</dd><dt>Source reference</dt><dd>{source.id}</dd></dl></details></section>
    {error&&<p className="labclear-review-error" role="alert">{error}</p>}{notice&&<p className="labclear-review-notice" role="status">{notice}</p>}
    {needsRecovery&&<button className="secondary" disabled={busy||!binding} onClick={recoverReview}>{t('กู้คืนคำสั่งที่รออยู่','Recover pending request')}</button>}
    {pending&&<details className="labclear-review-technical"><summary>Pending request details</summary><dl><dt>Operation</dt><dd>{pending.kind==='task'?'Create review task':pending.kind==='import'?'Transfer released source':'Confirm reviewed values'}</dd><dt>Request reference</dt><dd>{pending.key}</dd><dt>Source revision</dt><dd>{source.version}</dd></dl></details>}
    {!ready?<p role="status">{t('กำลังโหลดงานทบทวน…','Loading review tasks…')}</p>:loadFailed?<button className="secondary" onClick={()=>setReload(value=>value+1)}>{t('ลองโหลดพื้นที่ทบทวนอีกครั้ง','Try loading the review workspace again')}</button>:!available?<p>{t('ยังไม่ได้เชื่อม LabClear สำหรับระบบนี้','LabClear is not connected for this workspace yet.')}</p>:<>
     {!receipt&&<section className="labclear-review-start"><h3>Review workspace</h3>{bindings.length>0?<div className="labclear-review-start-actions">{bindings.length>1&&<label>Existing review<select aria-label="Existing LabClear review" disabled={!canRead} value={binding?.id||''} onChange={event=>{setBinding(bindings.find(item=>item.id===event.target.value)||null);setReceipt(null);setError('')}}><option value="">Select a review</option>{bindings.map((item,index)=><option key={item.id} value={item.id}>Review {index+1} · {String(item.created_at||'')}</option>)}</select></label>}<button className="primary" disabled={!canRead||!binding} onClick={openReview}>{t('เปิดการทบทวนเดิม','Open existing review')}</button></div>:<><p>{t('ใช้งานทบทวนแยกจากงานตรวจแล็บเดิม','Use a separate review task for these released values.')}</p>{tasks.length>0?<label>Review task<select aria-label="LabClear review task" value={taskId} disabled={!canWork} onChange={event=>setTaskId(event.target.value)}><option value="">Select a review task</option>{tasks.map(task=><option key={task.id} value={task.id}>{String(task.title||'LabClear review')}</option>)}</select></label>:<button className="secondary" disabled={!canWork} onClick={createTask}>{t('สร้างงานทบทวน','Create review task')}</button>}<button className="primary" disabled={!canWork||!taskId} onClick={sendValues}>{t('ส่งค่าต้นฉบับที่เผยแพร่แล้ว','Send released values')}</button></>}</section>}
     {(receipt||pending?.kind==='confirm')&&<section aria-labelledby={titleId+'-review'}><div className="labclear-review-section-heading"><h3 id={titleId+'-review'}>{isConfirmed?'Confirmed review':historical?'Saved review':pending?.kind==='confirm'?'Pending reviewed values':'Review values'}</h3><button className="text-button" disabled={busy||!!pending} onClick={openReview}>{t('ตรวจผลล่าสุด','Check latest review')}</button></div><p>{isConfirmed?t('การทบทวนนี้ยืนยันแล้ว แสดงค่าฉบับที่บันทึกไว้','This review is confirmed. These are the saved reviewed values.'):historical?t('การรับบริการหรืองานทบทวนนี้ปิดแล้ว แสดงค่าที่บันทึกไว้เพื่ออ่านเท่านั้น','This visit or review task is closed. Saved values are view only.'):t('เทียบชื่อ ค่า หน่วย และช่วงอ้างอิงกับต้นฉบับด้านบน แก้ไขก่อนยืนยันได้','Compare each cell with the source above. Make corrections before confirming.')}</p><div className="labclear-review-grid-head" aria-hidden="true"><span>Test</span><span>Value</span><span>Unit</span><span>Reference</span><span>Printed flag</span></div>{fields.map((cell,index)=><fieldset className="labclear-review-row" disabled={locked} key={cell.source_index}><legend>{t('รายการที่ ','Row ')}{index+1}</legend>{(['name','value','unit','reference','printed_flag'] as const).map(key=><label key={key}><span>{{name:'Test',value:'Value',unit:'Unit',reference:'Reference',printed_flag:'Printed flag'}[key]}</span><input aria-label={`${{name:'Test',value:'Value',unit:'Unit',reference:'Reference',printed_flag:'Printed flag'}[key]} row ${index+1}`} value={cell[key]} maxLength={{name:100,value:150,unit:60,reference:150,printed_flag:25}[key]} required={key==='name'} onChange={event=>{const value=event.target.value;setFields(previous=>previous.map((row,i)=>i===index?{...row,[key]:value}:row));setConfirmedPerson(false)}}/></label>)}</fieldset>)}{!readOnly&&<label className="labclear-review-confirm-person"><input type="checkbox" checked={confirmedPerson} disabled={locked} onChange={event=>setConfirmedPerson(event.target.checked)}/><span>{t('ฉันตรวจค่าครบแล้ว และยืนยันว่าเป็นผลของผู้ป่วยในบริบทนี้','I reviewed every value and confirmed that this source belongs to the selected patient.')}</span></label>}{binding&&<details className="labclear-review-technical"><summary>Review details</summary><dl><dt>Source revision</dt><dd>{binding.source_version}</dd><dt>Source hash</dt><dd>{binding.source_sha256}</dd><dt>Review reference</dt><dd>{binding.id}</dd>{receipt?.review&&<><dt>Confirmed revision</dt><dd>{receipt.review.revision}</dd><dt>Reviewer</dt><dd>{receipt.review.reviewer_id}</dd></>}</dl></details>}</section>}
    </>}
   </>}
  </div>
  <footer className="labclear-review-footer"><p>{t('การทบทวนนี้ไม่เปลี่ยนผลแล็บต้นฉบับ','This review leaves the released laboratory result unchanged.')}</p><div className="button-row">{pending?<><button className="primary" disabled={busy||!ready||!retryAllowed} onClick={()=>run(pending)}>{busy?t('กำลังตรวจผล…','Checking outcome…'):t('Retry ด้วยคำสั่งเดิม','Retry the same request')}</button>{binding&&pending.kind!=='task'&&<button className="secondary" disabled={busy} onClick={recoverReview}>{t('ตรวจคำสั่งที่รออยู่','Check pending request')}</button>}</>:receipt?.state==='draft'&&!readOnly&&<button className="primary" disabled={!canWork||!confirmedPerson||fields.some(cell=>!cell.name.trim())} onClick={confirmReview}>{t('ยืนยันการทบทวน','Confirm reviewed values')}</button>}<button className="secondary" disabled={!!pending} onClick={requestClose}>{t('ปิด','Close')}</button></div></footer>
 </section></div>,document.body)
}
