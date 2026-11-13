import {useEffect,useRef,useState} from 'react'
import {Client,HttpError,rows,normalizeMutation,reconcileOperation,errorText,type Row,type ProposalV2,type PendingOperation} from '../lib/client'
import {DataForm} from './forms'
import {ResourceWorkspace,Status,DetailValues} from './workspace'
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
function CompletenessReview({report}:{report:NonNullable<ProposalV2['action']['completeness']>}){
 const statusLabels={present:'พบในเอกสาร',missing:'ยังไม่พบในเอกสาร',unclear:'ยังไม่ชัดเจน'}
 return <section aria-label="ผลตรวจความครบถ้วนเอกสาร"><h4>รายการตรวจจากโมเดล</h4><p>{report.summary}</p><ul className="history">{report.items.map(item=><li key={item.key}><strong>{completenessLabels[item.key]||item.label}</strong> <span className={'status status-'+(item.status==='present'?'verified':item.status==='missing'?'returned':'pending')}>{statusLabels[item.status]}</span>{item.evidence_quote?<blockquote>{item.evidence_quote}</blockquote>:<p className="muted">ไม่มีข้อความอ้างอิงสำหรับรายการนี้</p>}</li>)}</ul><p className="muted">รายการนี้เป็นการตรวจข้อความตามแบบตรวจสังเคราะห์ ผู้ตรวจต้องเทียบกับเอกสารต้นฉบับก่อนอนุมัติ</p></section>
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
 return typeof input==='number'&&typeof output==='number'?'โทเคนเข้า '+input+' · ออก '+output:'จำนวนโทเคน UNKNOWN'
}
export function AIWorkspace({client,context,canReview=true,canWrite=true}:{client:Client;context:{patient_id:string;encounter_id:string};canReview?:boolean;canWrite?:boolean}){
 const requestGeneration=useRef(0)
 const [profile,setProfile]=useState<AIProfile|null>(null)
 const [pendingCreate,setPendingCreate]=useState<(PendingOperation&{binding:string})|null>(null)
 const [tasks,setTasks]=useState<Row[]>([]);const [docs,setDocs]=useState<Row[]>([]);const [proposals,setProposals]=useState<ProposalV2[]>([]);const [runs,setRuns]=useState<Row[]>([]);const [results,setResults]=useState<Row[]>([]);const [task,setTask]=useState('');const [doc,setDoc]=useState('');const [selected,setSelected]=useState<ProposalV2|null>(null);const [draft,setDraft]=useState('');const [scenario,setScenario]=useState('success');const [busy,setBusy]=useState(false);const [error,setError]=useState('');const [notice,setNotice]=useState('');const [pending,setPending]=useState<PendingOperation|null>(null);const [confirmed,setConfirmed]=useState<Row|null>(null)
 const contextBinding=useRef('');contextBinding.current=[context.patient_id,context.encounter_id,task,doc].join('|')
 useEffect(()=>{window.dispatchEvent(new CustomEvent('his-pending',{detail:!!pending||!!pendingCreate}));return()=>{window.dispatchEvent(new CustomEvent('his-pending',{detail:false}))}},[pending,pendingCreate])
 async function refresh(syncSelection=true){
  const generation=++requestGeneration.current;setProfile(null);const suffix=context.encounter_id?'?encounter_id='+encodeURIComponent(context.encounter_id):''
  const [t,d,p,r,out,configuration]=await Promise.all([client.get('tasks'+suffix),client.get('documents'+suffix),client.get('proposals'+(task?'?task_id='+encodeURIComponent(task):'')),client.get('runs'+(task?'?task_id='+encodeURIComponent(task):'')),client.get('results'+suffix),client.get('ai/config')])
  if(generation!==requestGeneration.current)return
  const nextProfile=parseAIProfile(configuration);setProfile(nextProfile);setTasks(rows(t));setDocs(rows(d));setProposals(rows(p) as ProposalV2[]);setRuns(rows(r));setResults(rows(out))
  const matched=reconcileOperation(pending,rows(out));if(matched){setConfirmed(matched);setPending(null);setNotice('อ่านกลับยืนยันผลที่ตรง operation / proposal / version / hash แล้ว')}
  if(syncSelection&&selected){const fresh=(rows(p) as ProposalV2[]).find(x=>x.id===selected.id);if(fresh&&draft===selected.action.text){setSelected(fresh);setDraft(fresh.action.text)}}
 }
 useEffect(()=>{let current=true;setTasks([]);setDocs([]);setProposals([]);setSelected(null);setDraft('');setResults([]);setRuns([]);setProfile(null);refresh().catch(e=>{if(current)setError(errorText(e))});return()=>{current=false;requestGeneration.current++}},[client,context.encounter_id,task])
 async function execute(fn:()=>Promise<void>){if(busy)return;setBusy(true);setError('');setNotice('');try{await fn()}catch(e){setError(errorText(e))}finally{setBusy(false)}}
 async function propose(retry=false){
  if(!profile)return
  const operation=retry&&pendingCreate?pendingCreate:{path:'proposals',body:{task_id:task,document_id:doc,scenario:profile.demo?scenario:'success'},key:crypto.randomUUID(),binding:contextBinding.current}
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
 }
 async function review(decision:string){if(!selected)return;const binding={id:selected.id,version:selected.version,action_hash:selected.action_hash};await execute(async()=>{const response=await client.mutate(`proposals/${binding.id}/review`,{version:binding.version,action_hash:binding.action_hash,decision,...(decision==='edit'?{edited_text:draft}:{})});const incoming=(response.proposal||response) as ProposalV2;setProposals(old=>normalizeMutation(old,incoming) as ProposalV2[]);setSelected(incoming);setDraft(incoming.action.text);setNotice('บันทึกการทบทวนรุ่น '+incoming.version+' แล้ว');try{const fresh=rows(await client.get('proposals'+(task?'?task_id='+task:''))) as ProposalV2[];setProposals(fresh)}catch(e){setError('บันทึกแล้ว รุ่นที่แสดงตรงกับ response แต่โหลดรายการล่าสุดไม่สำเร็จ: '+errorText(e))}})}
 async function commit(retry=false){if(!selected&&!pending)return;const op=retry&&pending?pending:{path:`proposals/${selected!.id}/commit`,body:{version:selected!.version,action_hash:selected!.action_hash},key:crypto.randomUUID(),proposal_id:selected!.id,version:selected!.version,action_hash:selected!.action_hash};await execute(async()=>{setPending(op);try{const response=await client.mutate(op.path,op.body,op.key);setConfirmed(response.result||response);setPending(null);setSelected(p=>p?{...p,status:'committed'}:null);setNotice('บันทึกผลสำเร็จแล้ว');try{await refresh()}catch(e){setError('ผลบันทึกยืนยันแล้ว แต่โหลดรายการล่าสุดไม่สำเร็จ: '+errorText(e))}}catch(e){if(e instanceof HttpError&&e.definitive){setPending(null);setNotice('เซิร์ฟเวอร์ปฏิเสธคำสั่ง สามารถโหลดข้อมูลและสร้างข้อเสนอใหม่ได้')}else setNotice('ผล commit ยังไม่แน่นอน อ่านผลล่าสุดหรือ retry ด้วย key เดิม');throw e}})}
 const dirty=!!selected&&draft!==selected.action.text
 const visibleTasks=profile&&!profile.demo?tasks.filter(t=>profile.supported_task_kinds.includes(String(t.kind))):tasks
 const invalidLiveReport=selected?.demo===false&&!validCompleteness(selected.action.completeness)
 return <div className="workspace-stack">
  <div className="section-toolbar"><div><h2>AI workbench</h2><p>หลักฐาน → ข้อเสนอ → ทบทวน → บันทึกผล</p></div><span className="demo-pill">{profile?(profile.demo?'EXPLICIT MOCK · ไม่มี live fallback':'AI จริง · dr-train'):'กำลังตรวจการตั้งค่า AI'}</span></div>
  {profile&&!profile.demo&&<section className="card"><strong>โมเดล {profile.model||'ยังไม่ระบุ'}</strong><p>ตรวจความครบถ้วนเอกสารสังเคราะห์ ผลจากโมเดลต้องผ่านผู้ตรวจอนุมัติก่อนบันทึก</p></section>}
  {error&&<div role="alert" className="alert error">{error}</div>}{notice&&<div role="status" className="alert info">{notice}</div>}
  <button className="secondary" disabled={busy} onClick={()=>refresh().catch(e=>setError(errorText(e)))}>โหลดและยืนยันผลล่าสุด</button>
  {pendingCreate&&!busy&&<div className="pending-banner"><p>คำขอ AI รอยืนยัน · <code>{pendingCreate.key}</code></p><button className="secondary" onClick={()=>propose(true)}>Retry สร้างข้อเสนอเดิม</button></div>}
  <div className="record-layout"><section className="card"><h3>เลือกงานและหลักฐาน</h3>
   <label className="field"><span>งานที่ผูกผู้ป่วย / encounter</span><select value={task} onChange={e=>setTask(e.target.value)} disabled={busy||!!pending||!!pendingCreate}><option value="">เลือกงาน</option>{visibleTasks.map(t=><option key={t.id} value={t.id}>{String(t.title)} · {t.status}</option>)}</select></label>
   <label className="field"><span>เอกสารหลักฐาน</span><select value={doc} onChange={e=>setDoc(e.target.value)} disabled={busy||!!pending||!!pendingCreate}><option value="">เลือกเอกสาร</option>{docs.map(d=><option value={d.id} key={d.id}>{String(d.title)} · v{d.version}</option>)}</select></label>
   {profile?.demo&&<label className="field"><span>สถานการณ์ mock</span><select value={scenario} onChange={e=>setScenario(e.target.value)}>{['success','failure','timeout','abstain','invalid'].map(s=><option key={s}>{s}</option>)}</select></label>}
   <button className="primary full" disabled={!canWrite||busy||!!pending||!!pendingCreate||!profile||!visibleTasks.some(t=>t.id===task)||!doc} onClick={()=>propose()}>{busy&&profile?.demo===false?'กำลังตรวจเอกสารกับ dr-train…':'สร้างข้อเสนอจากเอกสารที่บันทึก'}</button>
   <h3>ข้อเสนอของงาน</h3>{proposals.map(p=><button className="record-button" key={p.id} disabled={busy||!!pending||!!pendingCreate} onClick={()=>{setSelected(p);setDraft(p.action.text)}}><div><strong>{p.action.text}</strong><small>v{p.version} · {p.id} · {p.demo===false?'AI จริง':p.demo===true?'DEMO mock':'แหล่งที่มายังไม่ระบุ'}</small></div><Status value={p.status}/></button>)}
  </section><section className="card">{selected?<>
   <div className="section-heading"><h3>ทบทวนรุ่น {selected.version}</h3><Status value={selected.status}/></div>
   <p className="hash">Action hash: {selected.action_hash}</p><p>{selected.demo===false?'ข้อเสนอจาก AI จริง':selected.demo===true?'ข้อเสนอ DEMO mock':'ข้อเสนอที่บันทึกไว้'}</p>
   <DetailValues record={{id:'evidence',...selected.evidence}}/>
   {validCompleteness(selected.action.completeness)&&<CompletenessReview report={selected.action.completeness!}/>}
   {invalidLiveReport&&<p role="alert" className="alert error">รายการตรวจของข้อเสนอ AI ไม่ครบตามแบบตรวจ กรุณาโหลดข้อมูลล่าสุดก่อนอนุมัติ</p>}
   <label className="field"><span>ข้อเสนอที่ตรวจจริง</span><textarea rows={6} value={draft} disabled={busy||!!pending||!!pendingCreate||selected.status!=='pending'} onChange={e=>setDraft(e.target.value)}/></label>
   <div className="button-row"><button className="secondary" disabled={!canReview||busy||!!pending||!!pendingCreate||!dirty||selected.status!=='pending'} onClick={()=>review('edit')}>บันทึกเป็นรุ่นใหม่</button><button className="primary" disabled={!canReview||busy||!!pending||!!pendingCreate||dirty||!!invalidLiveReport||selected.status!=='pending'} onClick={()=>review('approve')}>อนุมัติรุ่นที่แสดง</button><button className="danger-button" disabled={!canReview||busy||!!pending||!!pendingCreate||dirty||selected.status!=='pending'} onClick={()=>review('reject')}>ปฏิเสธ</button></div>
   <button className="primary full" disabled={!canReview||busy||!!pending||!!pendingCreate||dirty||!!invalidLiveReport||selected.status!=='approved'} onClick={()=>commit()}>ยืนยันบันทึกผล</button>
   </>:<div className="empty"><h3>ยังไม่ได้เลือกข้อเสนอ</h3><p>เลือกงานและเอกสารเพื่อสร้างข้อเสนอ หรือเปิดรายการเดิม</p></div>}
   {pending&&<div className="pending-banner"><p>เก็บ key {pending.key}</p><button className="secondary" disabled={busy} onClick={()=>commit(true)}>Retry commit เดิม</button></div>}
   {confirmed&&<div className="confirmed"><strong>ยืนยันผลที่บันทึกแล้ว</strong><code>{confirmed.id}</code></div>}
  </section></div>
  <div className="record-layout"><section className="card"><h3>Provider attempts ({runs.length})</h3>{runs.map(r=><div className="run-row" key={r.id}><Status value={r.outcome}/><span>{r.provider==='mock_demo'?'DEMO mock':String(r.provider||'ไม่ระบุ provider')}{runModel(r)?' · '+runModel(r):''}</span><span>{String(r.error||r.reason||r.abstain_reason||'—')}</span><small>เวลา {typeof r.elapsed_ms==='number'?r.elapsed_ms+' ms':'UNKNOWN'} · {runTokens(r)} · ต้นทุน {String(r.measured_cost??r.cost??'UNKNOWN')}</small></div>)}</section><section className="card"><h3>ผลที่บันทึก ({results.length})</h3>{results.map(r=><details key={r.id}><summary>{r.id}</summary><DetailValues record={r}/></details>)}</section></div>
 </div>
}
