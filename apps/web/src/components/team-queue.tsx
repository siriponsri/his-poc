import {useCallback,useEffect,useId,useRef,useState,type FormEvent} from 'react'
import {Client,HttpError,errorText,hasPermission,rows,type Session} from '../lib/client'
import {localDateTime,taskReceipt,validTeamPage,validTeamTask,type TaskCapability,type TaskCommand,type TaskOwner,type TeamQueuePage,type TeamTask} from '../lib/team-operations'
import {formatMoment,shortId,statusLabel} from './workspace'
import type {PatientRecordRequest} from './patient-record-panel'
import domains from '../data/full-domains.json'

type Mode='assign'|'schedule'|'escalate'
const priorityLabels={low:'ต่ำ',normal:'ปกติ',high:'สูง'}
const emptyCounts={active:0,mine:0,unassigned:0,overdue:0,escalated:0}
export function TeamQueue({client,session,navigate,onOpenPatient,requestedTaskId}:{client:Client;session:Session;navigate:(path:string)=>void;onOpenPatient:(request:PatientRecordRequest)=>void;requestedTaskId?:string|null}){
  const [page,setPage]=useState<TeamQueuePage|null>(null),[query,setQuery]=useState(''),[view,setView]=useState('all'),[status,setStatus]=useState('active'),[domain,setDomain]=useState(''),[offset,setOffset]=useState(0)
  const [loading,setLoading]=useState(true),[error,setError]=useState(''),[detailError,setDetailError]=useState(''),[selected,setSelected]=useState<TeamTask|null>(null),[reading,setReading]=useState(false),[notice,setNotice]=useState('')
  const [pending,setPending]=useState<TaskCommand|null>(null),[sending,setSending]=useState(false),[commandError,setCommandError]=useState(''),[needsReload,setNeedsReload]=useState(false)
  const [mode,setMode]=useState<Mode|null>(null),[assignees,setAssignees]=useState<TaskOwner[]>([]),[assignee,setAssignee]=useState(''),[reason,setReason]=useState(''),[due,setDue]=useState(''),[priority,setPriority]=useState<TeamTask['priority']>('normal'),[peopleLoading,setPeopleLoading]=useState(false),[peopleError,setPeopleError]=useState('')
  const listSequence=useRef(0),detailSequence=useRef(0),peopleSequence=useRef(0),mounted=useRef(true),pendingRef=useRef(pending),sendingRef=useRef(false),dialog=useRef<HTMLDivElement>(null),returnFocus=useRef<HTMLElement|null>(null),detailHeading=useRef<HTMLHeadingElement>(null),lastRequested=useRef<string|null|undefined>(undefined)
  pendingRef.current=pending
  const initialTaskId=useRef(new URLSearchParams(location.search).get('task_id'))
  const dialogId=useId(),locked=!!pending||!!mode,counts=page?.counts||emptyCounts
  const load=useCallback(async()=>{
    const request=++listSequence.current;setLoading(true)
    const parameters=new URLSearchParams({q:query.trim(),view,status,limit:'25',offset:String(offset),...(domain?{domain}:{})})
    try{const value=validTeamPage(await client.get<TeamQueuePage>('team-queue?'+parameters));if(mounted.current&&request===listSequence.current){setPage(value);setError('')}}catch(reason){if(mounted.current&&request===listSequence.current){setPage(null);setError(errorText(reason))}}finally{if(mounted.current&&request===listSequence.current)setLoading(false)}
  },[client,query,view,status,offset,domain])
  const readTask=useCallback(async(id:string)=>{
    const request=++detailSequence.current;setReading(true);setSelected(null);setDetailError('');setCommandError('');setNotice('');setNeedsReload(false)
    try{const value=validTeamTask(await client.get<TeamTask>('team-queue/tasks/'+encodeURIComponent(id)));if(value.id!==id)throw new HttpError('FOREIGN_TEAM_TASK');if(mounted.current&&request===detailSequence.current)setSelected(value)}catch(reason){if(mounted.current&&request===detailSequence.current)setDetailError(errorText(reason))}finally{if(mounted.current&&request===detailSequence.current)setReading(false)}
  },[client])
  useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;listSequence.current++;detailSequence.current++;peopleSequence.current++}},[])
  useEffect(()=>{const timer=setTimeout(()=>void load(),query?200:0);return()=>{clearTimeout(timer);listSequence.current++}},[load,query])
  useEffect(()=>{const id=requestedTaskId===undefined?initialTaskId.current:requestedTaskId;if(pending||id===lastRequested.current)return;lastRequested.current=id;if(id)void readTask(id);else{detailSequence.current++;setSelected(null);setDetailError('')}},[requestedTaskId,readTask,pending])
  useEffect(()=>{if(selected?.id&&!loading&&!dialog.current){detailHeading.current?.scrollIntoView?.({block:'start',behavior:'auto'});detailHeading.current?.focus({preventScroll:true})}},[selected?.id,loading])
  useEffect(()=>{window.dispatchEvent(new CustomEvent('his-pending',{detail:!!pending}));const warn=(event:BeforeUnloadEvent)=>{if(pendingRef.current){event.preventDefault();event.returnValue=''}};window.addEventListener('beforeunload',warn);return()=>{window.removeEventListener('beforeunload',warn);window.dispatchEvent(new CustomEvent('his-pending',{detail:false}))}},[pending])
  useEffect(()=>{
    if(!mode)return
    const previous=document.activeElement as HTMLElement|null,overflow=document.body.style.overflow;returnFocus.current=previous;document.body.style.overflow='hidden'
    dialog.current?.querySelector<HTMLElement>('input:not(:disabled),select:not(:disabled),textarea:not(:disabled),button:not(:disabled)')?.focus()
    const key=(event:KeyboardEvent)=>{
      if(event.key==='Escape'&&!pendingRef.current){event.preventDefault();setMode(null);return}
      if(event.key!=='Tab')return
      const controls=[...(dialog.current?.querySelectorAll<HTMLElement>('button:not(:disabled),input:not(:disabled),select:not(:disabled),textarea:not(:disabled)')||[])]
      if(!controls.length)return
      const index=controls.indexOf(document.activeElement as HTMLElement),next=index<0?0:(index+(event.shiftKey?-1:1)+controls.length)%controls.length
      event.preventDefault();controls[next].focus()
    }
    document.addEventListener('keydown',key,true)
    return()=>{document.removeEventListener('keydown',key,true);document.body.style.overflow=overflow;if(previous?.isConnected)previous.focus()}
  },[mode])
  function selectTask(id:string){if(locked)return;const url=new URL(location.href);url.searchParams.set('task_id',id);history.replaceState(history.state,'',url.pathname+url.search);void readTask(id)}
  function filter(change:()=>void){if(locked)return;change();setOffset(0);setSelected(null);setDetailError('');setCommandError('');setNeedsReload(false);detailSequence.current++}
  async function execute(command:TaskCommand){
    if(sendingRef.current)return
    sendingRef.current=true;setSending(true);setPending(command);setCommandError('');setNotice('')
    try{const value=taskReceipt(command,await client.mutate<TeamTask>(command.path,command.body,command.key));if(!mounted.current)return;setSelected(value);setPending(null);setMode(null);setNeedsReload(false);setNotice(command.label+'แล้ว อ่านกลับจากเซิร์ฟเวอร์สำเร็จ');await load()}
    catch(reason){if(!mounted.current)return;if(reason instanceof HttpError&&reason.definitive){setPending(null);if([403,404,409].includes(reason.status))setNeedsReload(true)}setCommandError(errorText(reason))}
    finally{sendingRef.current=false;if(mounted.current)setSending(false)}
  }
  function command(action:TaskCapability,body:Record<string,unknown>,label:string){if(!selected||pendingRef.current||needsReload||!selected.capabilities[action])return;void execute({path:'team-queue/tasks/'+encodeURIComponent(selected.id)+'/'+action,body:{version:selected.version,...body},key:crypto.randomUUID(),subject:{id:selected.id,patient_id:selected.patient_id,encounter_id:selected.encounter_id,domain:selected.domain},label})}
  async function open(next:Mode){
    if(!selected||locked||needsReload||!selected.capabilities[next])return
    setMode(next);setReason('');setAssignee('');setDue(localDateTime(selected.due_at));setPriority(selected.priority);setCommandError('');setPeopleError('');setAssignees([])
    if(next!=='assign')return
    const request=++peopleSequence.current,id=selected.id;setPeopleLoading(true)
    try{const list=rows(await client.get('team-queue/tasks/'+encodeURIComponent(id)+'/assignees')) as TaskOwner[];if(list.some(item=>!item.id||typeof item.display_name!=='string'||typeof item.username!=='string'))throw new HttpError('INVALID_TASK_ASSIGNEES');if(mounted.current&&request===peopleSequence.current)setAssignees(list)}catch(reason){if(mounted.current&&request===peopleSequence.current)setPeopleError(errorText(reason))}finally{if(mounted.current&&request===peopleSequence.current)setPeopleLoading(false)}
  }
  function submit(event:FormEvent){
    event.preventDefault();if(!mode||!selected||pending)return
    if(mode==='assign'){if(!assignees.some(item=>item.id===assignee)||!reason.trim())return;command('assign',{assignee_id:assignee,reason:reason.trim()},'มอบหมายงาน');return}
    if(mode==='escalate'){if(reason.trim())command('escalate',{reason:reason.trim()},'ยกระดับการติดตาม');return}
    let dueAt:string|null=null
    if(due){const parsed=new Date(due);if(!Number.isFinite(parsed.getTime())){setCommandError('กรุณาระบุวันและเวลาที่ถูกต้อง');return}dueAt=parsed.toISOString()}
    command('schedule',{due_at:dueAt,priority},'บันทึกกำหนดงาน')
  }
  const pendingNotice=()=>pending&&<div className="team-pending" role="status"><strong>{sending?'กำลังส่งคำสั่ง…':'ยังยืนยันผลคำสั่งไม่ได้'}</strong><p>เก็บงานและคำสั่งเดิมไว้ ตรวจผลด้วยคำสั่งเดิมก่อนเปลี่ยนบริบท</p>{!sending&&<button type="button" className="secondary" onClick={()=>void execute(pending)}>ตรวจผลคำสั่งเดิม</button>}</div>
  const pageStart=page?.items.length?offset+1:0,pageEnd=offset+(page?.items.length||0)
  return <section className="team-queue" aria-labelledby="team-queue-title"><header className="team-heading"><div><p className="care-eyebrow">CareBalance / Team coordination</p><h1 id="team-queue-title">Team queue</h1><p>เห็นผู้รับผิดชอบ กำหนดงาน และงานที่ต้องส่งต่อในที่เดียว</p></div><button className="secondary" disabled={loading||locked} onClick={()=>void load()}>อ่านล่าสุด</button></header>
    {error&&<p className="care-error" role="alert">อ่านคิวงานไม่สำเร็จ {error}</p>}
    {page&&<><dl className="team-counts"><div><dt>Active work</dt><dd>{counts.active}</dd></div><div><dt>Assigned to me</dt><dd>{counts.mine}</dd></div><div><dt>Unassigned</dt><dd>{counts.unassigned}</dd></div><div><dt>Overdue</dt><dd>{counts.overdue}</dd></div></dl><p className="team-count-scope">จำนวนงานที่ยังเปิด ภายใต้คำค้นและส่วนงานที่เลือก · ยกระดับการติดตาม {counts.escalated} งาน · {formatMoment(page.observed_at,'th')}</p></>}
    <nav className="team-view-tabs" aria-label="Task ownership view">{[['all','Team'],['mine','My work'],['unassigned','Unassigned']].map(([key,label])=><button key={key} disabled={locked} aria-current={view===key?'page':undefined} onClick={()=>filter(()=>setView(key))}>{label}</button>)}</nav>
    <div className="team-filters"><label><span className="sr-only">ค้นหาคิวงาน</span><input aria-label="ค้นหาคิวงาน" value={query} maxLength={100} disabled={locked} placeholder="ค้นหางานหรือผู้ป่วย…" onChange={event=>filter(()=>setQuery(event.target.value))}/></label><label><span className="sr-only">สถานะคิวงาน</span><select aria-label="สถานะคิวงาน" value={status} disabled={locked} onChange={event=>filter(()=>setStatus(event.target.value))}>{[['active','Active work'],['open','Open'],['in_progress','In progress'],['completed','Completed'],['cancelled','Cancelled'],['all','All states']].map(([key,label])=><option key={key} value={key}>{label}</option>)}</select></label><label><span className="sr-only">ส่วนงานในคิว</span><select aria-label="ส่วนงานในคิว" value={domain} disabled={locked} onChange={event=>filter(()=>setDomain(event.target.value))}><option value="">All workspaces</option>{domains.filter(item=>hasPermission(session.user,item.id)).map(item=><option key={item.id} value={item.id}>{item.id} · {item.name_th}</option>)}</select></label></div>
    {!mode&&pendingNotice()}{!mode&&commandError&&<p className="care-error" role="alert">{commandError}</p>}{notice&&<p className="care-notice" role="status">{notice}</p>}
    <div className="team-task-table-wrap" aria-busy={loading}><table className="team-task-table"><thead><tr><th>Task / patient</th><th>Owner</th><th>Due</th><th>Priority</th><th>State</th></tr></thead><tbody>{page?.items.map(item=><tr key={item.id} className={selected?.id===item.id?'selected-row':''}><th scope="row"><button disabled={locked} onClick={()=>selectTask(item.id)}>{item.title}</button><small>{item.patient_label} · {item.domain}</small></th><td>{item.assignee?.display_name||'ยังไม่มีผู้รับผิดชอบ'}</td><td className={item.overdue?'team-overdue':''}>{item.due_at?formatMoment(item.due_at,'th'):'ยังไม่กำหนด'}{item.overdue&&<small>เลยกำหนด</small>}</td><td>{priorityLabels[item.priority]}{item.escalation_level>0&&<small>ติดตามระดับ {item.escalation_level}</small>}</td><td>{statusLabel(item.status,'en')}</td></tr>)}</tbody></table>{loading&&<p role="status">กำลังอ่านคิวงาน…</p>}{!loading&&page&&!page.items.length&&<p className="team-empty">ไม่มีงานตามเงื่อนไขในขอบเขตที่คุณเข้าถึงได้</p>}</div>
    <div className="team-pagination"><span>{pageStart}–{pageEnd} / {page?.total??'—'} งาน</span><div><button className="secondary" disabled={locked||loading||offset===0} onClick={()=>setOffset(Math.max(0,offset-25))}>ก่อนหน้า</button><button className="secondary" disabled={locked||loading||!page||offset+page.items.length>=page.total} onClick={()=>setOffset(offset+25)}>ถัดไป</button></div></div>
    <section className="team-task-detail" aria-label="Task responsibility"><header><h2 ref={detailHeading} tabIndex={-1}>{selected?.title||'Task responsibility'}</h2>{selected&&<span>{statusLabel(selected.status,'en')} · v{selected.version}</span>}</header>{detailError&&<p className="care-error" role="alert">{detailError}</p>}{reading?<p role="status">กำลังอ่านงานที่เลือก…</p>:!selected?<p className="team-empty">เลือกงานเพื่ออ่านผู้รับผิดชอบและจัดการการส่งต่องาน</p>:<>
      <div className="team-task-subject"><span>{selected.patient_label} · {selected.domain} · Visit {shortId(selected.encounter_id)}</span><button className="text-button" disabled={!!pending} onClick={()=>onOpenPatient({patient_id:selected.patient_id,encounter_id:selected.encounter_id,task_id:selected.id})}>Open patient record</button></div>
      <dl className="team-responsibility"><div><dt>ผู้รับผิดชอบ</dt><dd>{selected.assignee?.display_name||'ยังไม่มีผู้รับผิดชอบ'}{selected.assignee&&<small>{selected.assignee.username}</small>}</dd></div><div><dt>กำหนดงาน</dt><dd>{selected.due_at?formatMoment(selected.due_at,'th'):'ยังไม่กำหนด'}{selected.overdue&&<small className="team-overdue">เลยกำหนด</small>}</dd></div><div><dt>ความสำคัญของงาน</dt><dd>{priorityLabels[selected.priority]}</dd></div><div><dt>ระดับติดตาม</dt><dd>{selected.escalation_level} / 3</dd></div></dl>
      {selected.escalation_reason&&<p className="team-escalation-reason"><strong>เหตุผลติดตาม</strong> {selected.escalation_reason}</p>}
      {needsReload?<div className="team-conflict" role="status"><p>ข้อมูลหรือสิทธิ์ของงานเปลี่ยนแล้ว อ่านงานนี้ล่าสุดก่อนทำรายการใหม่</p><button className="secondary" disabled={!!pending} onClick={()=>void readTask(selected.id)}>อ่านงานนี้ล่าสุด</button></div>:<div className="team-actions">{!selected.assignee&&selected.capabilities.claim&&<button className="primary" disabled={locked} onClick={()=>command('claim',{},'รับผิดชอบงาน')}>รับผิดชอบงานนี้</button>}{selected.capabilities.release&&<button className="secondary" disabled={locked} onClick={()=>command('release',{},'คืนงานให้ทีม')}>คืนงานให้ทีม</button>}{selected.capabilities.assign&&<button className="secondary" disabled={locked} onClick={()=>void open('assign')}>ส่งต่องาน</button>}{selected.capabilities.schedule&&<button className="secondary" disabled={locked} onClick={()=>void open('schedule')}>กำหนดงาน</button>}{selected.capabilities.escalate&&<button className="secondary" disabled={locked} onClick={()=>void open('escalate')}>ยกระดับการติดตาม</button>}</div>}
      <footer><p>กำหนดเวลาและความสำคัญนี้ใช้ติดตามงาน การลงนามและการตัดสินใจดูแลผู้ป่วยยังทำในพื้นที่งานเดิม</p><div><button className="secondary" disabled={!!pending} onClick={()=>navigate('/domains/'+selected.domain+'?'+new URLSearchParams({patient_id:selected.patient_id,encounter_id:selected.encounter_id,task_id:selected.id}))}>Open workspace</button><button className="text-button" disabled={!!pending} onClick={()=>navigate('/worklist?'+new URLSearchParams({record:selected.id,patient_id:selected.patient_id,encounter_id:selected.encounter_id}))}>สถานะงานและประวัติ</button></div></footer>
    </>}</section>
    {mode&&selected&&<div className="team-dialog-backdrop"><section ref={dialog} className="team-dialog" role="dialog" aria-modal="true" aria-labelledby={dialogId}><header><div><p>Task responsibility</p><h2 id={dialogId}>{mode==='assign'?'ส่งต่องาน':mode==='schedule'?'กำหนดเวลาและความสำคัญ':'ยกระดับการติดตาม'}</h2><p>{selected.title} · {selected.assignee?.display_name||'ยังไม่มีผู้รับผิดชอบ'}</p></div><button type="button" className="text-button" aria-label="Close task responsibility dialog" disabled={!!pending} onClick={()=>{peopleSequence.current++;setMode(null)}}>×</button></header><form onSubmit={submit}>
      {mode==='assign'&&<><label className="field"><span>ผู้รับผิดชอบคนใหม่</span><select aria-label="ผู้รับผิดชอบคนใหม่" value={assignee} onChange={event=>setAssignee(event.target.value)} disabled={!!pending||peopleLoading||!!peopleError} required><option value="">เลือกผู้รับงาน</option>{assignees.map(person=><option key={person.id} value={person.id}>{person.display_name} · {person.username}</option>)}</select></label>{peopleLoading&&<p role="status">กำลังอ่านผู้รับงานที่มีสิทธิ์…</p>}{peopleError&&<p className="care-error" role="alert">{peopleError}</p>}{!peopleLoading&&!peopleError&&!assignees.length&&<p>ไม่มีผู้รับงานที่ผ่านเงื่อนไขในขอบเขตนี้</p>}</>}
      {mode==='schedule'&&<><label className="field"><span>กำหนดงาน</span><input type="datetime-local" aria-label="กำหนดงาน" value={due} onChange={event=>setDue(event.target.value)} disabled={!!pending}/><small>เวลาตามอุปกรณ์: {Intl.DateTimeFormat().resolvedOptions().timeZone} · เว้นว่างเพื่อล้างกำหนดเดิม</small></label><label className="field"><span>ความสำคัญของงาน</span><select aria-label="ความสำคัญของงาน" value={priority} onChange={event=>setPriority(event.target.value as TeamTask['priority'])} disabled={!!pending}>{Object.entries(priorityLabels).map(([key,label])=><option key={key} value={key}>{label}</option>)}</select></label><p className="team-form-note">ใช้เพื่อจัดลำดับงานและการติดตาม</p></>}
      {mode!=='schedule'&&<label className="field"><span>{mode==='assign'?'เหตุผลส่งต่องาน':'เหตุผลยกระดับการติดตาม'}</span><textarea aria-label={mode==='assign'?'เหตุผลส่งต่องาน':'เหตุผลยกระดับการติดตาม'} value={reason} onChange={event=>setReason(event.target.value)} disabled={!!pending} required maxLength={1000} rows={4}/></label>}
      {commandError&&<p className="care-error" role="alert">{commandError}</p>}{pendingNotice()}{needsReload&&<p>อ่านงานนี้ล่าสุดหลังปิดแบบฟอร์ม ก่อนส่งคำสั่งใหม่</p>}<footer><button type="button" className="secondary" disabled={!!pending} onClick={()=>{peopleSequence.current++;setMode(null)}}>ยกเลิก</button><button className="primary" disabled={!!pending||needsReload||mode==='assign'&&(peopleLoading||!!peopleError||!assignee)} type="submit">ยืนยัน{mode==='assign'?'ส่งต่องาน':mode==='schedule'?'กำหนดงาน':'ยกระดับการติดตาม'}</button></footer>
    </form></section></div>}
  </section>
}
