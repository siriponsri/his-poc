import {useEffect,useRef,useState} from 'react'
import {Client,HttpError,rows,normalizeMutation,reconcileOperation,errorText,type Row,type ProposalV2,type PendingOperation} from '../lib/client'
import {DataForm} from './forms'
import {ResourceWorkspace,Status,DetailValues,Alert,EmptyState,formatMoment,shortId,statusLabel} from './workspace'
import {Icon} from './icons'
import {useLang} from '../lib/i18n'
import {field,type Resource} from '../lib/catalog'
const patientFields=[field('display_name','ชื่อผู้ป่วยสังเคราะห์'),field('identifier','เลขประจำตัวผู้ป่วย'),{...field('issuer','หน่วยออกเลข'),default:'LOCAL'},field('birth_date','วันเกิด','date',false),{...field('sex','เพศ','select'),options:['unknown','female','male','other']}]
const versionTransition=(name:string,label:string,from:string[])=>({name,label,from,path:'patients/{id}/transition',target:name})
export const patientResource:Resource={id:'patients',label:'ผู้ป่วย',path:'patients',fields:patientFields,actions:[{name:'demographics',label:'แก้ไขข้อมูลทะเบียน',path:'patients/{id}',method:'PATCH',fields:[field('display_name','ชื่อผู้ป่วย'),field('birth_date','วันเกิด','date',false),{...field('sex','เพศ','select'),options:['unknown','female','male','other']}]},versionTransition('verified','ตรวจยืนยัน',['draft']),versionTransition('active','เปิดใช้แฟ้ม',['verified']),versionTransition('inactive','ปิดใช้แฟ้ม',['active'])]}
export const encounterResource:Resource={id:'encounters',label:'การรับบริการ',path:'encounters',patient_context:true,fields:[{...field('patient_id','ผู้ป่วย','select'),source:'patients'},{...field('kind','ประเภทการรับบริการ','select'),options:['OPD','IPD','ER'],default:'OPD'},field('department_id','รหัสแผนก','text',false)],actions:[['in_consult','เริ่มตรวจ',['waiting']],['reviewed','ทบทวน',['in_consult']],['completed','ตรวจเสร็จ',['reviewed']],['closed','ปิดการรับบริการ',['completed']]].map(([name,label,from])=>({name:String(name),label:String(label),from:from as string[],path:'encounters/{id}/transition',target:String(name),fields:[field('reason','เหตุผล / สรุป','textarea',false),field('acknowledge_pending','ตรวจรายการงานค้างและยืนยันการปิดด้วยตนเอง','checkbox',false)]}))}
export const taskResource:Resource={id:'tasks',label:'งานที่มอบหมาย',path:'tasks',encounter_context:true,fields:[{...field('patient_id','ผู้ป่วย','select'),source:'patients'},{...field('encounter_id','การรับบริการ','select'),source:'encounters'},field('domain','รหัส Domain เช่น D07'),field('kind','ประเภทงาน'),field('title','ชื่องาน')],actions:[{name:'in_progress',label:'เริ่มงาน',from:['open'],path:'tasks/{id}/transition',target:'in_progress'},{name:'completed',label:'ปิดงาน',from:['in_progress'],path:'tasks/{id}/transition',target:'completed'},{name:'cancelled',label:'ยกเลิกงาน',from:['open','in_progress'],path:'tasks/{id}/transition',target:'cancelled'}]}
export const orderResource:Resource={id:'orders',label:'คำสั่งตรวจและรักษา',path:'orders',encounter_context:true,fields:[{...field('patient_id','ผู้ป่วย','select'),source:'patients'},{...field('encounter_id','การรับบริการ','select'),source:'encounters'},{...field('kind','ประเภทคำสั่ง','select'),options:['lab','medication','imaging','procedure','rehab']},field('code','รหัสรายการ'),field('label','รายการที่สั่ง'),field('instructions','คำสั่งโดยบุคลากร','textarea'),{...field('quantity','จำนวน','number'),default:1},field('unit','หน่วย')],actions:[{name:'revise',label:'เพิ่มฉบับแก้คำสั่ง',path:'orders/{id}/revise',fields:[field('instructions','คำสั่งฉบับแก้โดยบุคลากร','textarea')]},...[['signed','ลงนามคำสั่ง',['draft']],['acknowledged','รับทราบคำสั่ง',['signed']],['in_progress','เริ่มดำเนินงาน',['acknowledged']],['completed','ดำเนินงานเสร็จ',['in_progress']],['cancelled','ยกเลิกคำสั่ง',['signed','acknowledged']]].map(([name,label,from])=>({name:String(name),label:String(label),from:from as string[],path:'orders/{id}/transition',target:String(name)}))]}
export function DocumentWorkspace({client,context,canEdit=true}:{client:Client;context:{patient_id:string;encounter_id:string};canEdit?:boolean}){const resource:Resource={id:'documents',label:'เอกสารและฉบับแก้ไข',path:'documents',encounter_context:true,fields:[{...field('patient_id','ผู้ป่วย','select'),source:'patients'},{...field('encounter_id','การรับบริการ','select'),source:'encounters'},field('title','ชื่อเอกสาร'),field('content','เนื้อหาเอกสาร','textarea')],actions:[{name:'revise',label:'สร้างฉบับแก้ไข',path:'documents/{id}/revise',fields:[field('content','เนื้อหาฉบับใหม่','textarea'),field('reason','เหตุผลแก้ไข','textarea')]},...([['in_review','ส่งตรวจทาน',['draft','amended']],['attested','รับรองฉบับที่แสดง',['in_review']],['returned','ส่งคืนแก้ไข',['in_review']],['draft','กลับสู่ร่าง',['returned']]] as [string,string,string[]][]).map(([name,label,from])=>({name,label,from,path:'documents/{id}/transition',target:name,fields:[field('content_hash','ข้อมูลผูกฉบับที่แสดง','hidden')]}))]};return <ResourceWorkspace resource={resource} client={client} context={context} readOnly={!canEdit}/>}
type AIProfile={active_provider:string;demo:boolean;live_routes_enabled:boolean;model?:string|null;model_digest?:string|null;supported_task_kinds:string[]}
const completenessKeys=['chief_complaint','history','assessment','plan','author']
const completenessLabels:Record<string,string>={chief_complaint:'อาการสำคัญ / เหตุผลที่มารับบริการ',history:'ประวัติที่เกี่ยวข้อง',assessment:'ผลประเมินโดยผู้บันทึก',plan:'แผนการดูแล',author:'ผู้บันทึกเอกสาร'}
const completenessLabelsEn:Record<string,string>={chief_complaint:'Chief complaint / reason for visit',history:'Relevant history',assessment:'Assessment recorded by the author',plan:'Care plan',author:'Document author'}
function parseAIProfile(value:unknown):AIProfile{
 const p=value as AIProfile
 if(!p||typeof p.active_provider!=='string'||typeof p.demo!=='boolean'||typeof p.live_routes_enabled!=='boolean'||p.demo===p.live_routes_enabled)throw new HttpError('INVALID_AI_CONFIGURATION')
 if(!p.demo&&(p.active_provider!=='dr_train_ollama'||!Array.isArray(p.supported_task_kinds)||p.supported_task_kinds.some(k=>typeof k!=='string')))throw new HttpError('INVALID_AI_CONFIGURATION')
 return {...p,supported_task_kinds:p.supported_task_kinds||['document_review','imaging_review','dr_review']}
}
function validCompleteness(value:unknown){
 const c=value as ProposalV2['action']['completeness']
 return !!c&&c.checklist_id==='SYNTHETIC_DOCUMENT_COMPLETENESS_V1'&&c.requires_human_review===true&&typeof c.summary==='string'&&Array.isArray(c.items)&&c.items.length===completenessKeys.length&&c.items.every(i=>!!i&&typeof i==='object'&&completenessKeys.includes(i.key)&&['present','missing','unclear'].includes(i.status)&&typeof i.evidence_quote==='string')&&new Set(c.items.map(i=>i.key)).size===completenessKeys.length
}
// Each finding state has its own word, symbol and colour so it never depends on colour alone.
const findingStates={present:{icon:'check',th:'พบหลักฐาน',en:'Evidence found'},missing:{icon:'missing',th:'ไม่พบหลักฐาน',en:'No evidence found'},unclear:{icon:'unclear',th:'ยังไม่ชัดเจน',en:'Unclear'}} as const
function CompletenessReview({report}:{report:NonNullable<ProposalV2['action']['completeness']>}){
 const {lang,t}=useLang()
 const order=['present','missing','unclear'] as const
 return <section className="findings" aria-label="ผลตรวจความครบถ้วนเอกสาร">
  <div className="findings-head"><h4>{t('รายการตรวจจากโมเดล','Model checklist')}</h4><p className="finding-tally">{order.map(state=><span key={state} className={'finding-state '+state}><Icon name={findingStates[state].icon} size={17}/>{findingStates[state][lang]} <b>{report.items.filter(i=>i.status===state).length}</b></span>)}</p></div>
  <p className="findings-summary">{report.summary}</p>
  <ul className="checklist">{report.items.map(item=><li key={item.key} className={'finding '+item.status}>
   <span className={'finding-state '+item.status}><Icon name={findingStates[item.status].icon} size={20}/></span>
   <div><p className="finding-title"><strong>{(lang==='en'?completenessLabelsEn[item.key]:completenessLabels[item.key])||item.label}</strong> <span className={'finding-label '+item.status}>{findingStates[item.status][lang]}</span></p>
   {item.evidence_quote?<blockquote>{item.evidence_quote}</blockquote>:<p className="muted">{item.status==='missing'?t('ยังไม่พบในเอกสาร','Not found in the document'):t('โมเดลยังระบุไม่ได้ชัดเจน','The model could not determine this')} · {t('ไม่มีข้อความอ้างอิงสำหรับรายการนี้','no source quote for this item')}</p>}</div>
  </li>)}</ul>
  <p className="muted findings-note">{t('รายการนี้เป็นการตรวจข้อความตามแบบตรวจสังเคราะห์ ผู้ตรวจต้องเทียบกับเอกสารต้นฉบับก่อนอนุมัติ','This checks wording against a synthetic checklist. The reviewer must compare it with the source document before approving.')}</p>
 </section>
}
/** Source text with the model's exact quotes marked; unmatched quotes are simply not marked. */
function SourceDocument({content,quotes}:{content:string;quotes:string[]}){
 const marks=quotes.filter(Boolean).map(q=>({start:content.indexOf(q),end:content.indexOf(q)+q.length})).filter(m=>m.start>=0).sort((a,b)=>a.start-b.start)
 const parts:{text:string;mark:boolean}[]=[];let cursor=0
 for(const m of marks){if(m.start<cursor)continue;if(m.start>cursor)parts.push({text:content.slice(cursor,m.start),mark:false});parts.push({text:content.slice(m.start,m.end),mark:true});cursor=m.end}
 if(cursor<content.length)parts.push({text:content.slice(cursor),mark:false})
 return <p className="document-content">{parts.map((part,i)=>part.mark?<mark key={i}>{part.text}</mark>:<span key={i}>{part.text}</span>)}</p>
}
function runModel(run:Row){
 const p=run.provenance as Record<string,unknown>|undefined
 const value=p?.model_id||p?.model_name||p?.model
 return typeof value==='string'?value:null
}
function runTokens(run:Row){
 const usage=run.usage as Record<string,unknown>|null
 const input=usage?.input_tokens??usage?.prompt_eval_count
 const output=usage?.output_tokens??usage?.eval_count
 return typeof input==='number'&&typeof output==='number'?'เข้า '+input+' · ออก '+output:null
}
/** Long registry identifiers: readable name first, exact identifier kept beneath and allowed to wrap. */
function ModelName({model}:{model:string}){
 const last=model.split('/').pop()||model;const [name,tag]=last.split(':')
 return <span className="model-name"><strong>{name}</strong>{tag&&<span className="model-tag">{tag}</span>}{last!==model||tag?<code className="model-id">{model}</code>:null}</span>
}
function SourceBadge({demo}:{demo:boolean|undefined}){
 const {t}=useLang()
 return demo===false?<span className="source-badge live"><Icon name="spark" size={14}/>{t('AI จริง','Real AI')}</span>:demo===true?<span className="source-badge mock">DEMO mock</span>:<span className="source-badge unknown">{t('แหล่งที่มายังไม่ระบุ','Source not recorded')}</span>
}
export function AIWorkspace({client,context,canReview=true,canWrite=true}:{client:Client;context:{patient_id:string;encounter_id:string};canReview?:boolean;canWrite?:boolean}){
 const {lang,t}=useLang()
 const matchesContext=(row:Row)=>(!context.patient_id||row.patient_id===context.patient_id)&&(!context.encounter_id||row.encounter_id===context.encounter_id)
 const canActOn=(proposal:ProposalV2)=>!!context.patient_id&&!!context.encounter_id&&proposal.patient_id===context.patient_id&&proposal.encounter_id===context.encounter_id&&(!task||proposal.task_id===task)
 const requestGeneration=useRef(0)
 const [profile,setProfile]=useState<AIProfile|null>(null)
 const [pendingCreate,setPendingCreate]=useState<(PendingOperation&{binding:string})|null>(null)
 const [tasks,setTasks]=useState<Row[]>([]);const [docs,setDocs]=useState<Row[]>([]);const [proposals,setProposals]=useState<ProposalV2[]>([]);const [runs,setRuns]=useState<Row[]>([]);const [results,setResults]=useState<Row[]>([]);const [task,setTask]=useState(()=>new URLSearchParams(location.search).get('task_id')||'');const [doc,setDoc]=useState(()=>new URLSearchParams(location.search).get('document_id')||'');const [selected,setSelected]=useState<ProposalV2|null>(null);const [draft,setDraft]=useState('');const [scenario,setScenario]=useState('success');const [busy,setBusy]=useState(false);const [error,setError]=useState('');const [notice,setNotice]=useState('');const [pending,setPending]=useState<PendingOperation|null>(null);const [confirmed,setConfirmed]=useState<Row|null>(null);const [creating,setCreating]=useState(false)
 const contextBinding=useRef('');contextBinding.current=[context.patient_id,context.encounter_id,task,doc].join('|')
 useEffect(()=>{window.dispatchEvent(new CustomEvent('his-pending',{detail:!!pending||!!pendingCreate}));return()=>{window.dispatchEvent(new CustomEvent('his-pending',{detail:false}))}},[pending,pendingCreate])
 async function refresh(syncSelection=true){
  const generation=++requestGeneration.current;setProfile(null);const suffix=context.encounter_id?'?encounter_id='+encodeURIComponent(context.encounter_id):''
  const [t,d,p,r,out,configuration]=await Promise.all([client.get('tasks'+suffix),client.get('documents'+suffix),client.get('proposals'+(task?'?task_id='+encodeURIComponent(task):'')),client.get('runs'+(task?'?task_id='+encodeURIComponent(task):'')),client.get('results'+suffix),client.get('ai/config')])
  if(generation!==requestGeneration.current)return
  const nextProfile=parseAIProfile(configuration);const scopedTasks=rows(t).filter(matchesContext);const taskIds=new Set(scopedTasks.map(row=>row.id));const scopedProposals=(rows(p) as ProposalV2[]).filter(row=>matchesContext(row)&&(!task||row.task_id===task));const scopedResults=rows(out).filter(row=>(!context.patient_id&&!context.encounter_id)||taskIds.has(String(row.task_id)));setProfile(nextProfile);setTasks(scopedTasks);const scopedDocs=rows(d).filter(matchesContext);setDocs(scopedDocs);setDoc(current=>scopedDocs.some(row=>row.id===current)?current:'');setProposals(scopedProposals);setRuns(rows(r).filter(row=>(!context.patient_id&&!context.encounter_id)||taskIds.has(String(row.task_id))));setResults(scopedResults)
  const matched=reconcileOperation(pending,scopedResults);if(matched){setConfirmed(matched);setPending(null);setNotice('อ่านกลับยืนยันผลที่ตรง operation / proposal / version / hash แล้ว')}
  if(syncSelection&&selected){const fresh=scopedProposals.find(x=>x.id===selected.id);if(fresh&&draft===selected.action.text){setSelected(fresh);setDraft(fresh.action.text)}}
 }
 useEffect(()=>{let current=true;setTasks([]);setDocs([]);setProposals([]);setSelected(null);setDraft('');setResults([]);setRuns([]);setProfile(null);refresh().catch(e=>{if(current)setError(errorText(e))});return()=>{current=false;requestGeneration.current++}},[client,context.patient_id,context.encounter_id,task])
 async function execute(fn:()=>Promise<void>){if(busy)return;setBusy(true);setError('');setNotice('');try{await fn()}catch(e){setError(errorText(e))}finally{setBusy(false)}}
 async function propose(retry=false){
  if(!profile)return
  const operation=retry&&pendingCreate?pendingCreate:{path:'proposals',body:{task_id:task,document_id:doc,scenario:profile.demo?scenario:'success'},key:crypto.randomUUID(),binding:contextBinding.current}
  setCreating(true)
  await execute(async()=>{
   setPendingCreate(operation)
   try{
    const result=await client.mutate(operation.path,operation.body,operation.key)
    if(operation.binding!==contextBinding.current){setPendingCreate(null);return}
    if(result.pending===true){setNotice('AI กำลังประมวลผลคำสั่งเดิม กด retry เพื่ออ่านผลโดยใช้ key เดิม');return}
    setPendingCreate(null)
    if(result.proposal){setSelected(result.proposal);setDraft(result.proposal.action.text);setProposals(old=>normalizeMutation(old,result.proposal) as ProposalV2[])}else{setSelected(null);setDraft('')}
    const actualDemo=result.demo===true||result.run?.provider==='mock_demo'
    const actualLive=result.demo===false||result.run?.provider==='dr_train_ollama'
    setNotice((actualDemo?'DEMO mock: ':actualLive?'ผลจาก AI จริง: ':'ผลจาก provider: ')+String(result.run?.outcome||result.outcome)+(result.run?.reason?' · '+result.run.reason:''))
    try{await refresh(false)}catch(e){setError('ได้รับผล provider แล้ว แต่โหลดรายการไม่สำเร็จ: '+errorText(e))}
   }catch(e){
    if(e instanceof HttpError&&e.definitive){setPendingCreate(null);setNotice('เซิร์ฟเวอร์ปฏิเสธการสร้างข้อเสนอ กรุณาโหลดหลักฐานและตรวจข้อมูลล่าสุด')}
    else setNotice('ยังไม่ทราบผลการเรียก AI เก็บคำสั่งและ key เดิมไว้ กด retry เพื่อยืนยันโดยไม่สร้างคำขอใหม่')
    throw e
   }
  })
  setCreating(false)
 }
 async function review(decision:string){if(!selected||!canActOn(selected))return;const binding={id:selected.id,version:selected.version,action_hash:selected.action_hash};await execute(async()=>{const response=await client.mutate(`proposals/${binding.id}/review`,{version:binding.version,action_hash:binding.action_hash,decision,...(decision==='edit'?{edited_text:draft}:{})});const incoming=(response.proposal||response) as ProposalV2;setProposals(old=>normalizeMutation(old,incoming) as ProposalV2[]);setSelected(incoming);setDraft(incoming.action.text);setNotice('บันทึกการทบทวนรุ่น '+incoming.version+' แล้ว');try{const fresh=(rows(await client.get('proposals'+(task?'?task_id='+task:''))) as ProposalV2[]).filter(row=>matchesContext(row)&&(!task||row.task_id===task));setProposals(fresh)}catch(e){setError('บันทึกแล้ว รุ่นที่แสดงตรงกับ response แต่โหลดรายการล่าสุดไม่สำเร็จ: '+errorText(e))}})}
 async function commit(retry=false){if((!selected&&!pending)||(selected&&!canActOn(selected)))return;const op=retry&&pending?pending:{path:`proposals/${selected!.id}/commit`,body:{version:selected!.version,action_hash:selected!.action_hash},key:crypto.randomUUID(),proposal_id:selected!.id,version:selected!.version,action_hash:selected!.action_hash};await execute(async()=>{setPending(op);try{const response=await client.mutate(op.path,op.body,op.key);setConfirmed(response.result||response);setPending(null);setSelected(p=>p?{...p,status:'committed'}:null);setNotice('บันทึกผลสำเร็จแล้ว');try{await refresh()}catch(e){setError('ผลบันทึกยืนยันแล้ว แต่โหลดรายการล่าสุดไม่สำเร็จ: '+errorText(e))}}catch(e){if(e instanceof HttpError&&e.definitive){setPending(null);setNotice('เซิร์ฟเวอร์ปฏิเสธคำสั่ง สามารถโหลดข้อมูลและสร้างข้อเสนอใหม่ได้')}else setNotice('ผล commit ยังไม่แน่นอน อ่านผลล่าสุดหรือ retry ด้วย key เดิม');throw e}})}
 const wrongProposalContext=!!selected&&!canActOn(selected)
 const dirty=!!selected&&draft!==selected.action.text
 const visibleTasks=profile&&!profile.demo?tasks.filter(t=>profile.supported_task_kinds.includes(String(t.kind))):tasks
 const invalidLiveReport=selected?.demo===false&&!validCompleteness(selected.action.completeness)
 const locked=busy||!!pending||!!pendingCreate
 const report=selected&&validCompleteness(selected.action.completeness)?selected.action.completeness!:null
 const evidence=(selected?.evidence||{}) as Record<string,unknown>
 const sourceText=typeof evidence.content==='string'?evidence.content:''
 const hint=!selected?'':selected.status==='committed'?t('บันทึกผลแล้ว ข้อเสนอนี้แก้ไขหรืออนุมัติซ้ำไม่ได้','The result is recorded. This proposal can no longer be edited or approved.'):selected.status==='rejected'?t('ข้อเสนอนี้ถูกปฏิเสธ หากต้องการผลใหม่ให้สร้างข้อเสนออีกครั้ง','This proposal was rejected. Create a new proposal if another result is needed.'):!canReview?t('บัญชีนี้ไม่มีสิทธิ์อนุมัติหรือบันทึกผล','This account is not permitted to approve or record results.'):invalidLiveReport?'':selected.status==='approved'?t('อนุมัติรุ่นนี้แล้ว กดยืนยันบันทึกผลเพื่อเขียนผลลงระบบ','This version is approved. Confirm to write the result.'):dirty?t('มีการแก้ไขที่ยังไม่บันทึก บันทึกเป็นรุ่นใหม่ก่อน แล้วจึงอนุมัติรุ่นนั้น','You have unsaved edits. Save them as a new version, then approve that version.'):t('อ่านข้อค้นพบเทียบกับเอกสารต้นฉบับ แล้วอนุมัติรุ่นที่แสดง หรือแก้ข้อความสรุปก่อน','Compare the findings with the source document, then approve this version or edit the summary first.')
 return <div className="workspace-stack ai-workbench">
  <div className="section-toolbar ai-toolbar">
   <div><p className="workspace-description">{profile&&!profile.demo?t('ตรวจเอกสารสังเคราะห์โดยมีผู้ตรวจอนุมัติก่อนบันทึก','Synthetic document review with human approval before recording'):t('หลักฐาน ข้อเสนอ และผลที่ผู้ตรวจยืนยัน','Evidence, proposals and reviewer-confirmed results')}</p></div>
   <div className="button-row"><span className={'mode-pill '+(profile?(profile.demo?'mock':'live'):'checking')}>{profile?(profile.demo?'EXPLICIT MOCK · ไม่มี live fallback':'AI จริง · dr-train'):t('กำลังตรวจการตั้งค่า AI','Checking AI configuration')}</span><button className="secondary" disabled={busy} onClick={()=>refresh().catch(e=>setError(errorText(e)))}>โหลดและยืนยันผลล่าสุด</button></div>
  </div>
  {error&&<Alert kind="error">{error}</Alert>}{notice&&<Alert kind="info">{notice}</Alert>}
  {busy&&creating&&profile?.demo===false&&<Alert kind="info">{t('กำลังส่งเอกสารให้โมเดลตรวจ อาจใช้เวลาถึง 3 นาที กรุณาอย่าปิดหรือเปลี่ยนหน้า','The document is with the model. This can take up to 3 minutes; please keep this page open.')}</Alert>}
  {pendingCreate&&!busy&&<div className="pending-banner"><Icon name="clock" size={18}/><p>{t('คำขอ AI รอยืนยัน','AI request awaiting confirmation')} <code>{pendingCreate.key}</code></p><button className="secondary" onClick={()=>propose(true)}>Retry สร้างข้อเสนอเดิม</button></div>}
  <section className="ai-intake" aria-label={t('เลือกงานและหลักฐาน','Choose task and evidence')}>
   <label className="field"><span>งานที่ผูกผู้ป่วย / encounter</span><select value={task} onChange={e=>setTask(e.target.value)} disabled={locked}><option value="">{t('เลือกงาน','Select a task')}</option>{visibleTasks.map(row=><option key={row.id} value={row.id}>{String(row.title)}: {statusLabel(String(row.status),lang)}</option>)}</select></label>
   <label className="field"><span>เอกสารหลักฐาน</span><select value={doc} onChange={e=>setDoc(e.target.value)} disabled={locked}><option value="">{t('เลือกเอกสาร','Select a document')}</option>{docs.map(d=><option value={d.id} key={d.id}>{String(d.title)}: v{d.version}</option>)}</select></label>
   {profile?.demo&&<label className="field"><span>สถานการณ์ mock</span><select value={scenario} onChange={e=>setScenario(e.target.value)}>{['success','failure','timeout','abstain','invalid'].map(s=><option key={s}>{s}</option>)}</select></label>}
   <button className="primary" disabled={!canWrite||locked||!profile||!visibleTasks.some(t=>t.id===task&&['open','in_progress'].includes(String(t.status)))||!docs.some(d=>d.id===doc&&tasks.some(t=>t.id===task&&t.patient_id===d.patient_id&&t.encounter_id===d.encounter_id))} onClick={()=>propose()}>{busy&&profile?.demo===false?'กำลังตรวจเอกสารกับ dr-train…':'สร้างข้อเสนอจากเอกสารที่บันทึก'}</button>
   {visibleTasks.some(row=>row.id===task)&&!visibleTasks.some(row=>row.id===task&&['open','in_progress'].includes(String(row.status)))&&<p className="field-hint">{t('งานนี้ปิดแล้ว เปิดงานตรวจเอกสารใหม่หากต้องการเรียก AI อีกครั้ง','This task is closed. Open a new review task to request another check.')}</p>}
   {!context.encounter_id&&<p className="field-hint">{t('เลือกบริบทผู้ป่วยด้านบนเพื่อจำกัดงานและเอกสาร','Select the patient context above to narrow tasks and documents.')}</p>}
  </section>
  <details className="proposal-browser" open={!selected}><summary>{t('ข้อเสนอของงาน','Proposals for this task')} <span className="count">{proposals.length}</span>{selected&&<span className="muted">{t('กำลังอ่านรุ่น','Reading version')} {selected.version}</span>}</summary>
   {proposals.length?<div className="proposal-list">{proposals.map(p=><button className={'record-button '+(selected?.id===p.id?'selected':'')} key={p.id} aria-current={selected?.id===p.id?'true':undefined} disabled={locked} onClick={()=>{setSelected(p);setDraft(p.action.text)}}><div><strong>{p.action.text}</strong><small className="record-meta"><span>v{p.version}</span><SourceBadge demo={p.demo}/><span className="record-id" title={p.id}>{shortId(p.id)}</span></small></div><Status value={p.status}/></button>)}</div>:<p className="muted">{task?t('งานนี้ยังไม่มีข้อเสนอ','No proposals for this task yet'):t('เลือกงานเพื่อดูข้อเสนอของงานนั้น หรือดูรายการทั้งหมดที่คุณเข้าถึงได้','Select a task to see its proposals')}</p>}
  </details>
  <div className="ai-review-layout">
   <section className="source-panel" aria-label={t('เอกสารต้นฉบับ','Source document')}>
    <div className="panel-heading"><h2>{t('เอกสารต้นฉบับ','Source document')}</h2>{(evidence.document_version||evidence.version)?<span>{t('รุ่นหลักฐาน','Evidence revision')} {String(evidence.document_version||evidence.version)}</span>:null}</div>
    {sourceText?<><SourceDocument content={sourceText} quotes={report?report.items.map(i=>i.evidence_quote):[]}/><p className="source-note">{t('ข้อความที่โมเดลอ้างถึงถูกเน้นไว้','Quoted passages are highlighted.')}</p></>:<EmptyState icon="document" title={t('เลือกข้อเสนอเพื่ออ่านหลักฐาน','Select a proposal to read its evidence')}>{t('แสดงต้นฉบับรุ่นเดียวกับที่ใช้ตรวจ','The exact revision used for this review appears here.')}</EmptyState>}
    {selected&&<details className="technical"><summary>{t('หลักฐานและรหัสผูกรุ่น','Evidence binding and identifiers')}</summary><p className="hash">Action hash: {selected.action_hash}</p><DetailValues record={{id:selected.id,...Object.fromEntries(Object.entries(evidence).filter(([key])=>key!=='content'))}}/></details>}
   </section>
   <section className="review-card" aria-label={t('ผลตรวจและการอนุมัติ','Findings and approval')}>{selected?<>
    <div className="panel-heading"><h2>ทบทวนรุ่น {selected.version}</h2><Status value={selected.status}/></div>
    <p className="review-bound-subject"><span>{t('ผู้ป่วย','Patient')}: {String(selected.patient_id||t('ยังไม่ระบุ','not recorded'))}</span><span>{t('การรับบริการ','Encounter')}: {String(selected.encounter_id||t('ยังไม่ระบุ','not recorded'))}</span></p>{wrongProposalContext&&<Alert kind="warning">{t('เลือกผู้ป่วยและการรับบริการที่ตรงกับข้อเสนอนี้ก่อนแก้ไข อนุมัติ หรือบันทึกผล','Select the matching patient and encounter before editing, approving or recording this proposal.')}</Alert>}<p className="review-source"><SourceBadge demo={selected.demo}/><span>{selected.demo===false?'ข้อเสนอจาก AI จริง':selected.demo===true?'ข้อเสนอ DEMO mock':'ข้อเสนอที่บันทึกไว้'}</span></p>
    {report&&<CompletenessReview report={report}/>}
    {invalidLiveReport&&<p role="alert" className="alert error">รายการตรวจของข้อเสนอ AI ไม่ครบตามแบบตรวจ กรุณาโหลดข้อมูลล่าสุดก่อนอนุมัติ</p>}
    <div className="review-decision">
     <label className="field"><span>ข้อเสนอที่ตรวจจริง</span><textarea rows={4} value={draft} disabled={locked||selected.status!=='pending'} onChange={e=>setDraft(e.target.value)}/></label>
     {hint&&<p className={'field-hint'+(dirty?' attention':'')}>{hint}</p>}
     <div className="button-row review-actions"><button className="secondary" disabled={!canReview||wrongProposalContext||locked||!dirty||selected.status!=='pending'} onClick={()=>review('edit')}>บันทึกเป็นรุ่นใหม่</button><button className="primary" disabled={!canReview||wrongProposalContext||locked||dirty||!!invalidLiveReport||selected.status!=='pending'} onClick={()=>review('approve')}>อนุมัติรุ่นที่แสดง</button><button className="danger-button" disabled={!canReview||wrongProposalContext||locked||dirty||selected.status!=='pending'} onClick={()=>review('reject')}>ปฏิเสธ</button><button className="primary commit" disabled={!canReview||wrongProposalContext||locked||dirty||!!invalidLiveReport||selected.status!=='approved'} onClick={()=>commit()}>ยืนยันบันทึกผล</button></div>
    </div>
    </>:<EmptyState icon="document" title={t('ยังไม่ได้เลือกข้อเสนอ','No proposal selected')}>{t('เลือกงานและเอกสารเพื่อสร้างข้อเสนอ หรือเปิดรายการเดิม','Choose a task and document to create a proposal, or open an existing one')}</EmptyState>}
    {pending&&<div className="pending-banner"><Icon name="clock" size={18}/><p>{t('เก็บ key','Kept key')} {pending.key}</p><button className="secondary" disabled={busy} onClick={()=>commit(true)}>Retry commit เดิม</button></div>}
    {confirmed&&<div className="confirmed"><Icon name="check" size={20}/><div><strong>ยืนยันผลที่บันทึกแล้ว</strong><code>{confirmed.id}</code></div></div>}
   </section>
  </div>
  {profile&&!profile.demo&&<details className="model-details"><summary>{t('โมเดลและที่มาของผลตรวจ','Model and result provenance')}</summary>{profile.model?<ModelName model={profile.model}/>:<strong>{t('ยังไม่ระบุ','Not specified')}</strong>}</details>}
  <details className="card ai-run-history"><summary>{t('ประวัติการเรียก AI','AI call history')} <span className="count">{runs.length}</span></summary>
   {runs.length?<div className="run-list">{runs.map(r=>{const model=runModel(r);const tokens=runTokens(r);const note=r.error||r.reason||r.abstain_reason;return <div className="run-row" key={r.id}>
    <div className="run-outcome"><Status value={r.outcome}/><SourceBadge demo={r.provider==='mock_demo'?true:r.provider==='dr_train_ollama'?false:undefined}/></div>
    <div className="run-source">{model?<ModelName model={model}/>:<strong>{r.provider==='mock_demo'?'DEMO mock':t('ไม่ระบุโมเดล','Model not recorded')}</strong>}<small>provider: {String(r.provider||t('ไม่ระบุ provider','not recorded'))}{typeof r.created_at==='string'?' · '+formatMoment(r.created_at,lang):''}</small>{note?<p className="run-note">{String(note)}</p>:null}</div>
    <dl className="run-metrics">
     <div><dt>{t('เวลา','Time')}</dt><dd>{typeof r.elapsed_ms==='number'?<>{(r.elapsed_ms/1000).toFixed(1)} {t('วินาที','s')} <small>({r.elapsed_ms} ms)</small></>:'UNKNOWN'}</dd></div>
     <div><dt>โทเคน</dt><dd>{tokens||<>{' '}UNKNOWN <small>{t('ไม่ทราบจำนวน','not reported')}</small></>}</dd></div>
     <div><dt>{'ต้นทุน '}</dt><dd>{(r.measured_cost??r.cost)!=null?String(r.measured_cost??r.cost):<>UNKNOWN <small>{t('ไม่ทราบ ยังไม่ได้วัด','not measured')}</small></>}</dd></div>
    </dl>
   </div>})}</div>:<p className="muted">{task?t('งานนี้ยังไม่มีการเรียก AI','No AI calls for this task yet'):t('เลือกงานเพื่อดูประวัติการเรียก AI ของงานนั้น','Select a task to see its AI call history')}</p>}
  </details>
  <details className="card ai-results"><summary>{t('ผลที่บันทึก','Recorded results')} <span className="count">{results.length}</span></summary>
   {results.length?results.map(r=>{const text=(r.action as {text?:string}|undefined)?.text;return <details className="result-row" key={r.id}><summary><span>{text||r.id}</span><small>{typeof r.created_at==='string'?formatMoment(r.created_at,lang)+' · ':''}<span title={r.id}>{shortId(r.id)}</span></small></summary><DetailValues record={r}/></details>}):<p className="muted">{t('ยังไม่มีผลที่บันทึกในบริบทนี้','No results recorded in this context yet')}</p>}
  </details>
 </div>
}
