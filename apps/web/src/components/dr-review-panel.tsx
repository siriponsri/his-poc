import {useEffect,useId,useRef,useState} from 'react'
import {createPortal} from 'react-dom'
import {Client,HttpError,rows,type Row,type PendingOperation} from '../lib/client'
import {useLang} from '../lib/i18n'

type Context={patient_id:string;encounter_id:string}
type Source={source_id:string;source_version:number;provenance_id:string;laterality:'L'|'R';modality:'CFP'|'UWF';label:string;preview_url:string;source_origin:'SYNTHETIC'|'PUBLIC';dataset_provenance?:{dataset_title:string;dataset_url:string;license_id:string;attribution:string}|null}
type SourceSet=Row&{patient_id:string;encounter_id:string;task_id:string;availability:string;destination_id:string;sources:{source_id:string;source_version:number;image_sha256:string;laterality:'L'|'R';modality:string}[]}
type Binding={id:string;state:string;workspace_url:string;pending:null|{operation:string}}
type Operation=PendingOperation&{kind:'task'|'set'|'import'}
const consent={confirmed:true,wording_version:'carebalance.dr-transfer.v2',purpose:'manual-dr-screening'}
const scopedTask=(task:Row,context:Context)=>task.domain==='D11'&&task.kind==='dr_screening_review'&&task.patient_id===context.patient_id&&task.encounter_id===context.encounter_id
const bindingUrl=(binding:Binding)=>/^[A-Za-z0-9_-]{1,64}$/.test(binding.id)&&binding.workspace_url===`/integrations/dr/${binding.id}/app/`?binding.workspace_url:null
const opaque=(value:unknown)=>typeof value==='string'&&/^[A-Za-z0-9_-]{1,64}$/.test(value)
const publicProvenance=(value:unknown)=>{if(!value||typeof value!=='object'||Array.isArray(value))return false;const p=value as Row;return p.dataset_title==='MMRDR'&&p.dataset_url==='https://figshare.com/articles/dataset/MMRDR/29423747'&&p.license_id==='CC-BY-4.0'&&typeof p.attribution==='string'&&p.attribution.length>0&&p.attribution.length<=1000}
const sourceRow=(row:Row)=>opaque(row.source_id)&&Number.isInteger(row.source_version)&&Number(row.source_version)>0&&opaque(row.provenance_id)&&typeof row.label==='string'&&row.label.length<=1000&&typeof row.preview_url==='string'&&['L','R'].includes(String(row.laterality))&&['CFP','UWF'].includes(String(row.modality))&&['SYNTHETIC','PUBLIC'].includes(String(row.source_origin))&&(row.source_origin!=='PUBLIC'||publicProvenance(row.dataset_provenance))
const setRow=(row:Row,context:Context)=>opaque(row.id)&&opaque(row.task_id)&&opaque(row.destination_id)&&row.patient_id===context.patient_id&&row.encounter_id===context.encounter_id&&['provisioned','unavailable'].includes(String(row.availability))&&Array.isArray(row.sources)&&row.sources.length>0&&row.sources.length<=8&&row.sources.every((item:any)=>item&&opaque(item.source_id)&&Number.isInteger(item.source_version)&&item.source_version>0&&/^[0-9a-f]{64}$/.test(String(item.image_sha256))&&['L','R'].includes(item.laterality)&&['CFP','UWF'].includes(item.modality))

/** Explicit source transfer into a separate, fixed-patient clinical workspace. */
export function DRReviewPanel({client,source,context,onClose,readOnly=false}:{client:Client;source:Row;context:Context;onClose:()=>void;readOnly?:boolean}){
 const {t}=useLang(),titleId=useId(),overlay=useRef<HTMLDivElement>(null),closeButton=useRef<HTMLButtonElement>(null)
 const identity=JSON.stringify([context.patient_id,context.encounter_id,source.id,source.patient_id,source.encounter_id,source.version,source.status,source.file_sha256]),liveIdentity=useRef(identity);liveIdentity.current=identity
 const mounted=useRef(true),generation=useRef(0),busyRef=useRef(false),closeRef=useRef(onClose);closeRef.current=onClose
 const [sources,setSources]=useState<Source[]>([]),[sets,setSets]=useState<SourceSet[]>([]),[tasks,setTasks]=useState<Row[]>([]),[selected,setSelected]=useState<string[]>([]),[taskId,setTaskId]=useState(''),[setId,setSetId]=useState(''),[binding,setBinding]=useState<Binding|null>(null),[agreed,setAgreed]=useState(false),[loaded,setLoaded]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState(''),[reload,setReload]=useState(0),[names,setNames]=useState({patient:'',visit:''}),[pending,setPending]=useState<Operation|null>(null)
 const pendingRef=useRef(pending);pendingRef.current=pending
 const [loadFailed,setLoadFailed]=useState(false)
 const valid=!!context.patient_id&&!!context.encounter_id&&source.patient_id===context.patient_id&&source.encounter_id===context.encounter_id&&['released','corrected'].includes(String(source.status))&&Number.isInteger(source.version)&&Number(source.version)>0
 const activeSet=sets.find(item=>item.id===setId),ready=loaded===identity&&valid
 const selectedSources=sources.filter(item=>selected.includes(item.source_id))
 function message(cause:unknown){
  if(cause instanceof HttpError){
   if(cause.status===401)return t('เซสชันหมดอายุ กรุณาเข้าสู่ระบบอีกครั้ง','Your session expired. Sign in again.')
   if(cause.status===403)return t('บัญชีนี้ไม่มีสิทธิ์ทำรายการกับชุดภาพนี้','This account cannot perform this action on these images.')
   if(cause.status===409)return t('ข้อมูล สิทธิ์ หรือคำสั่งเดิมเปลี่ยนแล้ว กรุณาตรวจผลล่าสุด','The source, access or an earlier request changed. Check the latest state.')
   if(cause.status===503)return t('ยังไม่ได้เปิดพื้นที่ DR สำหรับชุดภาพนี้ หรือการเชื่อมต่อยังไม่พร้อม','This image set has no available DR destination yet.')
   if(cause.status===404)return t('ไม่พบข้อมูลในขอบเขตปัจจุบัน','The record is unavailable in your current scope.')
  }
  return t('ยังยืนยันข้อมูลที่ตอบกลับไม่ได้ กรุณาตรวจอีกครั้ง','The specialist response could not be confirmed. Check again.')
 }
 function requestClose(){if(pendingRef.current||busyRef.current){setNotice(t('กรุณาตรวจผลคำสั่งเดิมก่อนปิด','Check the original pending request before closing.'));return}closeRef.current()}
 useEffect(()=>{
  mounted.current=true;const previous=document.activeElement instanceof HTMLElement?document.activeElement:null
  const background=[...document.body.children].filter(node=>node!==overlay.current&&node instanceof HTMLElement) as HTMLElement[],inert=background.map(node=>node.hasAttribute('inert'))
  background.forEach(node=>node.setAttribute('inert',''));const overflow=document.body.style.overflow;document.body.style.overflow='hidden';closeButton.current?.focus()
  const key=(event:KeyboardEvent)=>{if(event.key==='Escape'){event.preventDefault();requestClose();return}if(event.key!=='Tab')return
   const controls=[...overlay.current!.querySelectorAll<HTMLElement>('button:not(:disabled),a[href],input:not(:disabled),select:not(:disabled)')].filter(node=>!node.closest('[inert]')&&!node.closest('[hidden]'))
   const first=controls[0],last=controls.at(-1);if(!first||!last)return
   if(event.shiftKey&&(document.activeElement===first||!overlay.current?.contains(document.activeElement))){event.preventDefault();last.focus()}
   else if(!event.shiftKey&&(document.activeElement===last||!overlay.current?.contains(document.activeElement))){event.preventDefault();first.focus()}}
  document.addEventListener('keydown',key,true)
  return()=>{mounted.current=false;generation.current++;document.removeEventListener('keydown',key,true);background.forEach((node,index)=>{if(!inert[index])node.removeAttribute('inert')});document.body.style.overflow=overflow;if(previous?.isConnected)previous.focus({preventScroll:true})}
 },[])
 useEffect(()=>{window.dispatchEvent(new CustomEvent('his-pending',{detail:!!pending}));const warn=(event:BeforeUnloadEvent)=>{if(pending){event.preventDefault();event.returnValue=''}};window.addEventListener('beforeunload',warn);return()=>{window.removeEventListener('beforeunload',warn);window.dispatchEvent(new CustomEvent('his-pending',{detail:false}))}},[pending])
 useEffect(()=>{
  const token=++generation.current;setLoaded('');setLoadFailed(false);setSources([]);setSets([]);setTasks([]);setSelected([]);setTaskId('');setSetId('');setBinding(null);setAgreed(false);setError('');setNotice('');setPending(null);setBusy(false)
  if(!valid)return
  const query=new URLSearchParams(context)
  Promise.all([client.get('integrations/dr/sources?'+query),client.get('integrations/dr/source-sets?'+query),client.get('tasks?'+query)]).then(([available,existing,work])=>{
   if(!mounted.current||token!==generation.current||liveIdentity.current!==identity)return
   const rawImages=rows(available),rawSets=rows(existing);if(!rawImages.every(sourceRow)||!rawSets.every(row=>setRow(row,context)))throw new Error('Invalid DR source response')
   const imageRows=rawImages as unknown as Source[],reviews=rawSets as SourceSet[]
   const eligible=rows(work).filter(row=>scopedTask(row,context)&&['open','in_progress'].includes(String(row.status)))
   const candidates=reviews.filter(row=>row.sources.some(item=>item.source_id===source.id&&item.source_version===source.version))
   setSources(imageRows);setSets(reviews);setTasks(eligible);setTaskId(eligible.length===1?eligible[0].id:'');setSelected(imageRows.some(row=>row.source_id===source.id)?[source.id]:[])
   if(candidates.length===1){setSetId(candidates[0].id);setTaskId(candidates[0].task_id);setSelected(candidates[0].sources.map(item=>item.source_id))}
   setLoaded(identity)
  }).catch(cause=>{if(mounted.current&&token===generation.current){setError(message(cause));setLoadFailed(true);setLoaded(identity)}})
 },[client,identity,reload])
 useEffect(()=>{let active=true;setNames({patient:'',visit:''});if(!valid)return
  Promise.allSettled([client.get('reference/patients'),client.get('reference/encounters?patient_id='+encodeURIComponent(context.patient_id))]).then(([people,visits])=>{if(!active||liveIdentity.current!==identity)return
   const patient=people.status==='fulfilled'?rows(people.value).find(item=>item.id===context.patient_id):null,visit=visits.status==='fulfilled'?rows(visits.value).find(item=>item.id===context.encounter_id&&item.patient_id===context.patient_id):null
   setNames({patient:String(patient?.display_name||''),visit:String(visit?.kind||'')})});return()=>{active=false}
 },[client,identity])
 useEffect(()=>{let current=true;setBinding(null);setAgreed(false);if(!setId||!ready)return
  client.get('integrations/dr/source-sets/'+encodeURIComponent(setId)).then(data=>{if(!current||liveIdentity.current!==identity)return
   if(data.id!==setId||data.patient_id!==context.patient_id||data.encounter_id!==context.encounter_id)throw new Error(t('ชุดภาพไม่ตรงกับบริบทนี้','The image set does not match this context.'))
   const own=Array.isArray(data.bindings)?data.bindings:[];if(own.length===1){const found=own[0] as Binding;if(!bindingUrl(found))throw new Error('Invalid DR workspace reference');setBinding(found)}
  }).catch(cause=>{if(current)setError(message(cause))});return()=>{current=false}
 },[client,setId,loaded,identity])
 async function refreshBinding(id:string){const data=await client.get('integrations/dr/bindings/'+encodeURIComponent(id))
  if(data.binding_id!==id||data.patient_id!==context.patient_id||data.encounter_id!==context.encounter_id||data.source_set?.id!==setId)throw new Error('Invalid DR workspace context')
  const found={id,state:data.state,workspace_url:data.workspace_url,pending:data.pending} as Binding;if(!bindingUrl(found))throw new Error('Invalid DR workspace reference');return found}
 async function run(operation:Operation){if(busyRef.current||readOnly||!valid)return;busyRef.current=true;setBusy(true);setError('');setNotice('');setPending(operation);const original=identity
  try{const data=await client.mutate(operation.path,operation.body,operation.key,operation.method);if(!mounted.current||liveIdentity.current!==original)return
   if(operation.kind==='task'){if(!scopedTask(data,context)||!['open','in_progress'].includes(String(data.status)))throw new Error('Invalid DR review task');setTasks(old=>[...old.filter(item=>item.id!==data.id),data]);setTaskId(data.id)}
   if(operation.kind==='set'){if(!data.id||data.patient_id!==context.patient_id||data.encounter_id!==context.encounter_id||!Array.isArray(data.sources))throw new Error('Invalid DR image-set response');setSets(old=>[...old.filter(item=>item.id!==data.id),data as SourceSet]);setSetId(data.id);setAgreed(false);setNotice(t('จัดชุดภาพแล้ว การส่งภาพเป็นอีกขั้นตอนหนึ่ง','The image set is prepared. Transfer is a separate step.'))}
   if(operation.kind==='import'){
    if(typeof data.binding_id!=='string'||!/^[A-Za-z0-9_-]{1,64}$/.test(data.binding_id))throw new Error('Invalid DR binding reference')
    if(data.outcome==='rejected'){setPending(null);setError(t('คำสั่งถูกปฏิเสธ โปรดตรวจข้อมูลก่อนลองใหม่','The request was rejected. Check the source before trying again.'));return}
    if(data.outcome!=='succeeded'){if(!['unknown','running'].includes(data.outcome))throw new Error('Invalid DR request outcome');setBinding({id:data.binding_id,state:'unknown',workspace_url:`/integrations/dr/${data.binding_id}/app/`,pending:{operation:'import'}});setNotice(t('ยังไม่ทราบผลการส่งภาพ เก็บคำสั่งเดิมไว้เพื่อตรวจผล','The transfer outcome is unknown. Keep the original request for recovery.'));return}
    const found=await refreshBinding(data.binding_id);if(!mounted.current||liveIdentity.current!==original)return;if(found.state!=='imported'||found.pending)throw new Error('DR import not confirmed');setBinding(found);setNotice(t('ส่งภาพแล้ว เปิดพื้นที่ตรวจภาพได้','Transfer confirmed. The DR workspace is available.'))
   }
   setPending(null)
  }catch(cause){if(mounted.current&&liveIdentity.current===original){setError(message(cause));if(cause instanceof HttpError&&(cause.definitive||cause.message==='DR_DESTINATION_UNAVAILABLE'))setPending(null)}}finally{busyRef.current=false;if(mounted.current)setBusy(false)}
 }
 async function recover(){if(!binding||busyRef.current||readOnly||!valid)return;busyRef.current=true;setBusy(true);setError('');const original=identity
  try{const data=await client.mutate('integrations/dr/bindings/'+binding.id+'/recover',{});if(!mounted.current||liveIdentity.current!==original)return
   if(data.binding_id!==binding.id||!Array.isArray(data.commands)||data.automatic_replay!==false)throw new Error('Invalid DR recovery response')
   const command=data.commands.find((item:any)=>item.operation==='import')
   if(command){if(typeof command.key!=='string'||!command.body?.transfer_consent||command.body.transfer_consent.confirmed!==true)throw new Error('Invalid original DR command');setPending({kind:'import',path:'integrations/dr/source-sets/'+setId+'/bindings',key:command.key,body:command.body});setNotice(t('พบคำสั่งเดิมแล้ว ใช้คำสั่งนี้ตรวจผลโดยไม่สร้างรายการใหม่','The original request is available. Retry it without creating another.'))}
   else if(data.commands.length){setNotice(t('มีคำสั่งจากพื้นที่ตรวจภาพที่ต้องตรวจหลักฐานก่อนทำต่อ','A clinical workspace request needs evidence review before further changes.'))}
   else{const found=await refreshBinding(binding.id);if(mounted.current&&liveIdentity.current===original){setBinding(found);setPending(null)}}
  }catch(cause){if(mounted.current&&liveIdentity.current===original)setError(message(cause))}finally{busyRef.current=false;if(mounted.current)setBusy(false)}
 }
 const createTask=()=>run({kind:'task',path:'tasks',key:crypto.randomUUID(),body:{...context,domain:'D11',kind:'dr_screening_review',title:'DR screening review'}})
 const createSet=()=>selectedSources.length&&taskId&&agreed&&run({kind:'set',path:'integrations/dr/source-sets',key:crypto.randomUUID(),body:{...context,task_id:taskId,destination_id:'carebalance-dr-his-poc',sources:selected.map(id=>{const item=sources.find(image=>image.source_id===id)!;return {source_id:item.source_id,source_version:item.source_version,provenance_id:item.provenance_id}}),transfer_consent:{...consent}}})
 const send=()=>setId&&agreed&&run({kind:'import',path:'integrations/dr/source-sets/'+setId+'/bindings',key:crypto.randomUUID(),body:{transfer_consent:{...consent}}})
 const workspace=binding&&binding.state==='imported'?bindingUrl(binding):null
 const canLeavePending=!!pending&&(!!binding||pending.kind==='import'&&!!activeSet)
 return createPortal(<div className="labclear-review-overlay" ref={overlay}><section className="labclear-review-dialog" role="dialog" aria-modal="true" aria-labelledby={titleId}>
  <header className="labclear-review-header"><div><span className="labclear-review-eyebrow">CareBalance / DR</span><h2 id={titleId}>DR screening</h2><p>{t('ตรวจภาพในบริบทผู้ป่วยและการรับบริการเดิม','Review images in the same patient and encounter context.')}</p></div><button className="icon-button" aria-label="Close DR review" ref={closeButton} disabled={busy} onClick={requestClose}>×</button></header>
  <div className="labclear-review-body"><div className="labclear-review-context"><strong>{names.patient||t('ผู้ป่วยที่เลือก','Selected patient')}</strong><span>{names.visit||t('การรับบริการปัจจุบัน','Current encounter')}</span></div>
   {!valid?<p role="alert">{t('โปรดเลือกผู้ป่วยและการรับบริการที่ตรงกับภาพ','Select the patient and encounter that own this image.')}</p>:!ready?<p role="status">{t('กำลังโหลดภาพที่ลงทะเบียน…','Loading registered images…')}</p>:<>
    {error&&<p role="alert" className="labclear-review-error">{error}</p>}{notice&&<p role="status" className="labclear-review-notice">{notice}</p>}
    {sets.length>0&&<label className="field"><span>Review workspace</span><select aria-label="Existing DR review" value={setId} disabled={busy||!!pending} onChange={event=>{const next=sets.find(item=>item.id===event.target.value);setSetId(next?.id||'');setSelected(next?next.sources.map(item=>item.source_id):sources.some(item=>item.source_id===source.id)?[source.id]:[]);setTaskId(next?.task_id||'');setAgreed(false)}}><option value="">{t('จัดชุดภาพใหม่','Prepare a new image set')}</option>{sets.map(item=><option key={item.id} value={item.id}>{item.sources.map(image=>(image.laterality==='R'?'Right':'Left')+' '+image.modality).join(' / ')}</option>)}</select></label>}
    {!loadFailed&&<section className="dr-review-images-section"><h3>Images</h3>{sources.length===0?<p>{t('ยังไม่มีภาพที่ลงทะเบียนพร้อมข้อมูลข้างตาสำหรับบริบทนี้','No registered images with eye metadata are available in this context.')}</p>:<div className="dr-review-images">{sources.filter(item=>!activeSet||activeSet.sources.some(image=>image.source_id===item.source_id)).map(item=>{const preview=`/api/v2/integrations/dr/sources/${encodeURIComponent(item.source_id)}/preview?provenance_id=${encodeURIComponent(item.provenance_id)}`;return <label className="dr-review-image" key={item.source_id}><input type="checkbox" aria-label={`${item.laterality==='R'?'Right':'Left'} eye ${item.modality}`} checked={selected.includes(item.source_id)} disabled={readOnly||!!activeSet||busy||!!pending||!selected.includes(item.source_id)&&selected.length>=8} onChange={event=>{setSelected(old=>event.target.checked?[...old,item.source_id]:old.filter(id=>id!==item.source_id));setAgreed(false)}}/>{item.preview_url===preview&&<img src={preview} alt={`${item.laterality==='R'?'Right':'Left'} eye ${item.source_origin==='PUBLIC'?'public dataset':'synthetic'} source`}/>}<span><strong>{item.laterality==='R'?'Right eye':'Left eye'} · {item.modality}</strong><small>{item.label}</small><small>{item.source_origin==='PUBLIC'?'MMRDR · Public dataset · CC BY 4.0':'Authored synthetic source'}</small>{item.source_origin==='PUBLIC'&&item.dataset_provenance&&<small>{item.dataset_provenance.attribution}</small>}</span></label>})}</div>}</section>}
    {!readOnly&&!activeSet&&sources.length>0&&<section className="labclear-review-start"><h3>Review task</h3>{tasks.length?<label><span>{t('งานทบทวนภาพแยกจากงานถ่ายภาพเดิม','Review task, separate from acquisition')}</span><select aria-label="DR review task" value={taskId} disabled={busy||!!pending} onChange={event=>{setTaskId(event.target.value);setAgreed(false)}}><option value="">{t('เลือกงานทบทวน','Select a review task')}</option>{tasks.map(item=><option value={item.id} key={item.id}>{String(item.title)}</option>)}</select></label>:<button className="secondary" disabled={busy||!!pending} onClick={createTask}>{t('สร้างงานทบทวนภาพ','Create review task')}</button>}</section>}
    {!readOnly&&!workspace&&selected.length>0&&!binding?.pending&&<label className="labclear-review-confirm-person"><input type="checkbox" checked={agreed} disabled={busy||!!pending} onChange={event=>setAgreed(event.target.checked)}/><span>{t('ฉันตรวจสอบชุดภาพและที่มาแล้ว และยืนยันให้ส่งไปยัง CareBalance DR เพื่อทบทวนภาพโดยคน การยืนยันนี้ไม่อนุญาตให้เรียกโมเดล','I checked this image set and its source information, and confirm transfer to CareBalance DR for manual review. This does not authorize model inference.')}</span></label>}
    {activeSet&&activeSet.availability!=='provisioned'&&<p>{t('จัดชุดภาพไว้แล้ว ผู้ดูแลต้องเปิดพื้นที่ตรวจเฉพาะชุดนี้ก่อนส่งภาพ','The image set is prepared. Its dedicated review destination must be provisioned before transfer.')}</p>}
    {binding?.pending&&<p>{t('มีคำสั่งเดิมที่ยังรอตรวจผล การสร้างคำสั่งใหม่ถูกระงับไว้','An earlier request needs recovery before another mutation can start.')}</p>}
   </>}
  </div>
  <footer className="labclear-review-footer"><p>{t('การตรวจภาพไม่ปิดงานหรือเผยแพร่ผล HIS อัตโนมัติ','Image review does not automatically complete tasks or release HIS results.')}</p><div className="button-row">
   {pending?<button className="primary" disabled={busy} onClick={()=>run(pending)}>{t('ตรวจด้วยคำสั่งเดิม','Retry original request')}</button>:workspace?<a className="primary dr-review-open" href={workspace} target="_blank" rel="noopener">{binding?.pending?"Open review (read only)":"Open DR workspace"}</a>:readOnly?<span>{t("บัญชีนี้เปิดอ่านพื้นที่ตรวจเดิมได้เมื่อมีสิทธิ์","This account can open an existing authorized review.")}</span>:binding?.pending?<button className="secondary" disabled={busy} onClick={recover}>{t('ตรวจคำสั่งที่รออยู่','Check pending request')}</button>:activeSet?<button className="primary" disabled={busy||!agreed||activeSet.availability!=='provisioned'} onClick={send}>{t('ส่งภาพและเตรียมเปิดการตรวจ','Send images to DR')}</button>:sources.length>0?<button className="primary" disabled={busy||!agreed||!taskId||selectedSources.length===0} onClick={()=>void createSet()}>{t('จัดชุดภาพสำหรับตรวจ','Prepare image set')}</button>:<button className="secondary" disabled={busy} onClick={()=>setReload(value=>value+1)}>{t('โหลดล่าสุด','Refresh')}</button>}
   {canLeavePending&&<button className="secondary" disabled={busy} onClick={()=>{if(!busyRef.current)closeRef.current()}}>{t('ปิดและเก็บคำสั่งที่รอตรวจ','Close and keep pending request')}</button>}
   <button className="secondary" disabled={busy||!!pending} onClick={requestClose}>{t('ปิด','Close')}</button></div></footer>
 </section></div>,document.body)
}
