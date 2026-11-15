import {useCallback,useEffect,useRef,useState,type FormEvent,type KeyboardEvent as ReactKeyboardEvent} from 'react'
import {Client,HttpError,errorText,hasPermission,rows,type Row,type Session,type User} from '../lib/client'
import {formatMoment} from './workspace'
import {Icon} from './icons'
import {useLang} from '../lib/i18n'

type Membership={id:string;role:string;facility_id:string;active:boolean}
type Account=Row&{username:string;display_name:string;status:string;version:number;memberships?:Membership[]}
type Role={role:string;permissions:string[]}
type Overview={scope:{organization_id:string;facility_id:string};users:{total:number;active:number;suspended:number;disabled:number};sessions:{active:number;revoked:number;expired:number};security:{recent_denial_count:number;window_hours:number};database:{reachable:boolean;migration:string};assistant:{configured:boolean;route:string;engine_version:string;profiles_qualified:string[];counts:{queued:number;running:number;succeeded:number;failed:number;awaiting_review:number;active_watches:number};live_status:string};observed_at:string}
type Tab='users'|'roles'|'sessions'|'activity'
type Mode='create'|'account'|'membership'|'password'|'care'|'status'|'revoke'
type Operation={path:string;body:Record<string,unknown>;key:string}
const staffRoleNames=['registration','clinician','nurse','laboratory','imaging','pharmacist','billing','finance','inventory','quality','system_admin','operations_admin','auditor']

export function canManageIdentity(user:User){return hasPermission(user,'D34')&&(user.permissions.includes('identity.admin')||user.permissions.includes('*'))}
export function defaultWorkspace(session:Session){return session.user.roles.includes('system_admin')&&canManageIdentity(session.user)?'/admin':'/home'}
const profileNames:Record<string,string>={visit_preparation:'Visit preparation',nursing_handover:'Nursing handover',records_readiness:'Records readiness',laboratory_handoff:'Laboratory handoff'}

export function AdminWorkspace({client,session,navigate}:{client:Client;session:Session;navigate:(path:string)=>void}){
 const {t,lang}=useLang()
 const allowed=canManageIdentity(session.user)
 const [tab,setTab]=useState<Tab>('users'),[accounts,setAccounts]=useState<Account[]>([]),[roles,setRoles]=useState<Role[]>([]),[facilities,setFacilities]=useState<Row[]>([]),[sessions,setSessions]=useState<Row[]>([]),[events,setEvents]=useState<Row[]>([])
 const [overview,setOverview]=useState<Overview|null>(null),[loading,setLoading]=useState(true),[refreshing,setRefreshing]=useState(false),[errors,setErrors]=useState<Record<string,string>>({}),[notice,setNotice]=useState('')
 const [query,setQuery]=useState(''),[filter,setFilter]=useState('all'),[selected,setSelected]=useState<Account|null>(null),[mode,setMode]=useState<Mode|null>(null),[revokeSession,setRevokeSession]=useState<Row|null>(null),[target,setTarget]=useState('suspended')
 const [offset,setOffset]=useState(0),[total,setTotal]=useState(0),[loadingUsers,setLoadingUsers]=useState(true),[loadingActivity,setLoadingActivity]=useState(false)
 const [username,setUsername]=useState(''),[displayName,setDisplayName]=useState(''),[password,setPassword]=useState(''),[role,setRole]=useState('clinician'),[facility,setFacility]=useState(session.user.facility_id),[active,setActive]=useState(true),[patientId,setPatientId]=useState('')
 const [pending,setPending]=useState<Operation|null>(null),[sending,setSending]=useState(false),[commandError,setCommandError]=useState('')
 const mounted=useRef(true),sequence=useRef(0),userSequence=useRef(0),activitySequence=useRef(0),dialogEpoch=useRef(0),pendingRef=useRef<Operation|null>(null),sendingRef=useRef(false),dialog=useRef<HTMLDivElement>(null),returnFocus=useRef<HTMLElement|null>(null)

 const loadUsers=useCallback(async()=>{
  const request=++userSequence.current;setLoadingUsers(true)
  const parameters=new URLSearchParams({limit:'100',offset:String(offset),...(query.trim()?{q:query.trim()}:{}),...(filter==='all'?{}:{status:filter})})
  try{const value=await client.get('admin/users?'+parameters);const list=rows(value) as Account[];if(!mounted.current||request!==userSequence.current)return;setAccounts(list);setTotal(typeof value.total==='number'?value.total:list.length);setErrors(old=>{const next={...old};delete next['admin/users'];return next})}
  catch(error){if(mounted.current&&request===userSequence.current){setAccounts([]);setTotal(0);setErrors(old=>({...old,'admin/users':errorText(error)}))}}
  finally{if(mounted.current&&request===userSequence.current)setLoadingUsers(false)}
 },[client,offset,query,filter])

 const refresh=useCallback(async()=>{
  const request=++sequence.current;setRefreshing(true)
  const paths=['admin/overview','admin/roles','facilities','admin/sessions']
  const result=await Promise.allSettled(paths.map(path=>client.get(path)))
  if(!mounted.current||request!==sequence.current)return
  const failures:Record<string,string>={}
  result.forEach((item,index)=>{
   if(item.status==='rejected'){failures[paths[index]]=errorText(item.reason);return}
   const value=item.value
   try{if(index===0){if(!value?.scope||!value?.assistant?.counts||value.scope.organization_id!==session.user.organization_id||value.scope.facility_id!==session.user.facility_id)throw new HttpError('INVALID_ADMIN_OVERVIEW');setOverview(value)}
    else if(index===1)setRoles((value.items||[]) as Role[])
    else if(index===2)setFacilities(rows(value))
    else setSessions(rows(value))
   }catch(error){failures[paths[index]]=errorText(error)}
  })
  setErrors(old=>({...Object.fromEntries(Object.entries(old).filter(([key])=>!paths.includes(key))),...failures}));setLoading(false);setRefreshing(false)
 },[client,session.user.organization_id,session.user.facility_id])
 useEffect(()=>{mounted.current=true;if(allowed)void refresh();else setLoading(false);return()=>{mounted.current=false;sequence.current++;userSequence.current++}},[allowed,refresh])
 useEffect(()=>{if(!allowed)return;const timer=setTimeout(()=>void loadUsers(),query?200:0);return()=>{clearTimeout(timer);userSequence.current++}},[allowed,loadUsers,query])
 const loadActivity=useCallback(async()=>{const request=++activitySequence.current;setLoadingActivity(true);try{const value=await client.get('admin/security-events');if(!mounted.current||request!==activitySequence.current)return;setEvents(rows(value));setErrors(old=>{const next={...old};delete next.activity;return next})}catch(error){if(mounted.current&&request===activitySequence.current)setErrors(old=>({...old,activity:errorText(error)}))}finally{if(mounted.current&&request===activitySequence.current)setLoadingActivity(false)}},[client])
 useEffect(()=>{if(tab==='activity'&&allowed)void loadActivity();return()=>{activitySequence.current++}},[tab,allowed,loadActivity])
 useEffect(()=>{window.dispatchEvent(new CustomEvent('his-pending',{detail:!!pending}));return()=>{window.dispatchEvent(new CustomEvent('his-pending',{detail:false}))}},[pending])
 useEffect(()=>{
  if(!mode)return
  const previous=document.activeElement as HTMLElement;returnFocus.current=previous
  dialog.current?.querySelector<HTMLElement>('input,select,button')?.focus()
  const keys=(event:KeyboardEvent)=>{
   if(event.key==='Escape'&&!pendingRef.current&&!sendingRef.current){event.preventDefault();dialogEpoch.current++;setMode(null);setPassword('')}
   if(event.key==='Tab'&&dialog.current){const list=[...dialog.current.querySelectorAll<HTMLElement>('button:not(:disabled),input:not(:disabled),select:not(:disabled),[tabindex="0"]')].filter(node=>!node.hidden);if(!list.length)return;const first=list[0],last=list[list.length-1];if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus()}else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus()}}
  }
  document.addEventListener('keydown',keys)
  return()=>{document.removeEventListener('keydown',keys);returnFocus.current?.focus()}
 },[!!mode])
 useEffect(()=>{if(mode)dialog.current?.querySelector<HTMLElement>('input,select,button')?.focus()},[mode])

 function open(next:Mode,account:Account|null=null){if(pendingRef.current||sendingRef.current)return;const membership=account?.memberships?.find(item=>item.active&&item.facility_id===session.user.facility_id);dialogEpoch.current++;setSelected(account);setMode(next);setCommandError('');setPassword('');setUsername('');setDisplayName('');setRole(membership?.role||'clinician');setFacility(session.user.facility_id);setActive(true);setPatientId('');setNotice('')}
 function close(){if(pendingRef.current||sendingRef.current)return;dialogEpoch.current++;setMode(null);setSelected(null);setPassword('');setCommandError('')}
 async function execute(operation:Operation){
  if(sendingRef.current)return
  sendingRef.current=true;pendingRef.current=operation;setPending(operation);setSending(true);setCommandError('')
  try{
   await client.mutate(operation.path,operation.body,operation.key)
   if(!mounted.current)return
   pendingRef.current=null;setPending(null);setPassword('');setMode(null);setSelected(null);setNotice(t('บันทึกการเปลี่ยนแปลงแล้ว','Changes saved.'))
   await Promise.all([refresh(),loadUsers(),...(tab==='activity'?[loadActivity()]:[])])
  }catch(error){if(!mounted.current)return;if(error instanceof HttpError&&error.definitive){pendingRef.current=null;setPending(null)}setCommandError(errorText(error))}
  finally{sendingRef.current=false;if(mounted.current)setSending(false)}
 }
 function submit(event:FormEvent){
  event.preventDefault();if(pendingRef.current||sendingRef.current)return
  let path='',body:Record<string,unknown>={}
  if(mode==='create'){path='admin/users';body={username:username.trim(),display_name:displayName.trim(),password,role,facility_id:facility}}
  else if(mode==='revoke'&&revokeSession){path=`admin/sessions/${encodeURIComponent(revokeSession.id)}/revoke`}
  else if(selected){
   const base=`admin/users/${encodeURIComponent(selected.id)}`
   if(mode==='membership'){path=base+'/memberships';body={version:selected.version,role,facility_id:facility,active}}
   if(mode==='password'){path=base+'/reset-password';body={version:selected.version,password}}
   if(mode==='care'){path=base+'/care-assignments';body={patient_id:patientId.trim(),active}}
   if(mode==='status'){path=base+'/transition';body={version:selected.version,target}}
  }
  if(path)void execute({path,body,key:crypto.randomUUID()})
 }
 async function readLatest(){if(!selected||pendingRef.current)return;const epoch=dialogEpoch.current;try{const latest=await client.get<Account>('admin/users/'+encodeURIComponent(selected.id));if(!mounted.current||epoch!==dialogEpoch.current)return;if(latest.id!==selected.id)throw new HttpError('FOREIGN_ADMIN_ACCOUNT');setSelected(latest);setPassword('');setCommandError('');setMode('account');await loadUsers()}catch(error){if(mounted.current&&epoch===dialogEpoch.current)setCommandError(errorText(error))}}
 const filtered=accounts
 const userNames=new Map(accounts.map(item=>[item.id,item.display_name]))
 function sessionIdentity(item:Row){const user=item.user as {id?:string;username?:string;display_name?:string}|undefined;return user&&user.id===item.user_id&&typeof user.username==='string'&&typeof user.display_name==='string'?user.display_name+' · '+user.username:(userNames.get(String(item.user_id))||String(item.user_id))}
 const now=Date.now()
 const currentRole=roles.find(item=>item.role===role)
 const staffRoles=roles.filter(item=>staffRoleNames.includes(item.role))
 const tabs:{id:Tab;label:string;count:number}[]=[{id:'users',label:'Users',count:overview?.users.total??total},{id:'roles',label:'Roles & access',count:roles.length},{id:'sessions',label:'Sessions',count:sessions.filter(item=>!item.revoked_at&&Date.parse(String(item.expires_at))>now).length},{id:'activity',label:'Security activity',count:overview?.security.recent_denial_count||0}]
 function tabKeys(event:ReactKeyboardEvent<HTMLDivElement>){if(!['ArrowRight','ArrowLeft','Home','End'].includes(event.key))return;event.preventDefault();let index=tabs.findIndex(item=>item.id===tab);index=event.key==='Home'?0:event.key==='End'?tabs.length-1:(index+(event.key==='ArrowRight'?1:-1)+tabs.length)%tabs.length;setTab(tabs[index].id);event.currentTarget.querySelector<HTMLButtonElement>(`[data-admin-tab="${tabs[index].id}"]`)?.focus()}
 if(!allowed)return <section className="admin-denied"><Icon name="shield" size={28}/><h1>Administration</h1><p>{t('บัญชีนี้ไม่มีสิทธิ์จัดการผู้ใช้และสิทธิ์ของระบบ','This account cannot manage users or access.')}</p><button className="secondary" onClick={()=>navigate('/home')}>{t('กลับ Workspace','Back to Workspace')}</button></section>
 return <section className="admin-workspace" aria-labelledby="admin-title">
  <header className="admin-header"><div><p className="admin-eyebrow">Workspace / Administration</p><h1 id="admin-title">Administration</h1><p>{t('ดูแลบัญชี สิทธิ์ และการเข้าถึงของทีม','Manage accounts, permissions and team access.')}</p></div><div className="admin-actions"><button className="secondary" disabled={refreshing||!!pending} onClick={()=>void Promise.all([refresh(),loadUsers(),...(tab==='activity'?[loadActivity()]:[])])}><Icon name="refresh" size={15}/>{refreshing?t('กำลังอ่าน…','Refreshing…'):t('อ่านล่าสุด','Refresh')}</button><button className="primary" disabled={!!pending} onClick={()=>open('create')}>{t('เพิ่มผู้ใช้','Add user')}</button></div></header>
  {notice&&<p className="admin-notice" role="status">{notice}</p>}
  {Object.entries(errors).map(([key,value])=><div className="admin-error" role="alert" key={key}><strong>{key==='admin/overview'?'Overview':key==='activity'?'Security activity':key.replace('admin/','')}</strong><span>{value}</span></div>)}
  {overview&&<><dl className="admin-stat-strip"><div><dt>Active users</dt><dd>{overview.users.active}<small>{t(`จาก ${overview.users.total} บัญชี`,`of ${overview.users.total} accounts`)}</small></dd></div><div><dt>Active sessions</dt><dd>{overview.sessions.active}<small>{t('เซสชันที่ยังไม่หมดอายุ','unexpired sessions')}</small></dd></div><div><dt>AI preparation</dt><dd>{overview.assistant.counts.queued+overview.assistant.counts.running}<small>{t('กำลังรอหรือประมวลผล','queued or running')}</small></dd></div><div><dt>Access denials</dt><dd>{overview.security.recent_denial_count}<small>{t(`${overview.security.window_hours} ชั่วโมงล่าสุด`,`last ${overview.security.window_hours} hours`)}</small></dd></div></dl>
   <div className="admin-service-line"><span><span className="admin-service-label">Database</span> {overview.database.reachable?t('พร้อมใช้งาน','Available'):t('ไม่พร้อม','Unavailable')}<small>schema {overview.database.migration}</small></span><span><span className="admin-service-label">AI service</span> {overview.assistant.configured?t('ตั้งค่าสำหรับทีมแล้ว','Configured for staff'):t('ยังไม่ตั้งค่า','Not configured')}<small>{overview.assistant.profiles_qualified.length} preparation profiles · {t('ยังไม่ได้ตรวจสถานะโมเดลสด','live model status not checked')}</small></span><span className="admin-observed"><time dateTime={overview.observed_at}>{formatMoment(overview.observed_at,lang)}</time></span></div></>}
  <div className="admin-tabs" role="tablist" aria-label="Administration sections" onKeyDown={tabKeys}>{tabs.map(item=><button role="tab" id={`admin-tab-${item.id}`} aria-controls="admin-tab-panel" aria-selected={tab===item.id} data-admin-tab={item.id} tabIndex={tab===item.id?0:-1} key={item.id} onClick={()=>setTab(item.id)} disabled={!!pending}>{item.label}<span>{item.count}</span></button>)}</div>
  <div role="tabpanel" id="admin-tab-panel" aria-labelledby={`admin-tab-${tab}`}>
   {loading?<p className="admin-empty" role="status">{t('กำลังอ่านข้อมูลผู้ดูแล…','Loading administration…')}</p>:tab==='users'?<>
    <div className="admin-toolbar"><label className="admin-search"><Icon name="search" size={16}/><input aria-label={t('ค้นหาผู้ใช้','Search users')} value={query} maxLength={120} onChange={event=>{setQuery(event.target.value);setOffset(0)}} placeholder={t('ค้นหาชื่อหรือบัญชี','Search name or username')}/></label><label className="admin-filter"><span>{t('สถานะ','Status')}</span><select value={filter} onChange={event=>{setFilter(event.target.value);setOffset(0)}}><option value="all">All accounts</option><option value="active">Active</option><option value="suspended">Suspended</option><option value="disabled">Disabled</option></select></label><p role="status">{loadingUsers?t('กำลังค้นหา…','Searching…'):`${total?offset+1:0}–${offset+filtered.length} / ${total}`}</p></div>
    <div className="admin-table-wrap" aria-busy={loadingUsers}><table className="admin-table"><thead><tr><th>User</th><th>Access</th><th>Status</th><th><span className="sr-only">Actions</span></th></tr></thead><tbody>{filtered.map(account=><tr key={account.id}><th scope="row"><span className="admin-account-name">{account.display_name}{account.id===session.user.id&&<small> · You</small>}</span><span className="admin-account-sub">{account.username}</span></th><td>{(account.memberships||[]).filter(m=>m.active).map(m=><span className="admin-membership" key={m.id}>{m.role.replaceAll('_',' ')}<small>{String(facilities.find(item=>item.id===m.facility_id)?.name||m.facility_id)}</small></span>)}{!(account.memberships||[]).some(m=>m.active)&&<span className="admin-muted">{t('ไม่มีสิทธิ์ที่เปิดใช้','No active membership')}</span>}</td><td><span className={account.status==='active'?'admin-state':'admin-state admin-state-off'}>{account.status}</span></td><td><button className="secondary" aria-label={`Manage ${account.username}`} onClick={()=>open('account',account)}>{t('จัดการ','Manage')}<Icon name="chevron" size={14}/></button></td></tr>)}</tbody></table>{!loadingUsers&&!filtered.length&&<p className="admin-empty">{query?t('ไม่พบบัญชีที่ตรงกับคำค้น','No accounts match your search.'):t('ยังไม่มีบัญชีในรายการนี้','No accounts in this view.')}</p>}</div><div className="admin-pagination"><button className="secondary" disabled={loadingUsers||offset===0} onClick={()=>setOffset(value=>Math.max(0,value-100))}>{t('ก่อนหน้า','Previous')}</button><button className="secondary" disabled={loadingUsers||offset+filtered.length>=total} onClick={()=>setOffset(value=>value+100)}>{t('ถัดไป','Next')}</button></div>
   </>:tab==='roles'?<section className="admin-role-section"><header><h2>Roles & access</h2><p>{t('สิทธิ์ที่บันทึกอยู่จริงของแต่ละบทบาท การเลือกดูไม่เปลี่ยนสิทธิ์','Persisted permissions for each role. Viewing a role does not grant access.')}</p></header><div className="admin-role-list">{roles.map(item=><details key={item.role}><summary><span>{item.role.replaceAll('_',' ')}</span><small>{item.permissions.length} permissions</small></summary><ul>{item.permissions.map(permission=><li key={permission}><code>{permission}</code></li>)}</ul></details>)}</div></section>:tab==='sessions'?<><div className="admin-section-heading"><h2>Sessions</h2><p>{t('ถอนการเข้าถึงได้เป็นรายเซสชัน โดยไม่เปลี่ยนบทบาทของบัญชี','Revoke a session without changing the account’s role.')}</p></div><div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Account</th><th>Created</th><th>Expires</th><th>State</th><th><span className="sr-only">Actions</span></th></tr></thead><tbody>{sessions.slice().sort((a,b)=>String(b.created_at).localeCompare(String(a.created_at))).map(item=>{const state=item.revoked_at?'Revoked':Date.parse(String(item.expires_at))<=now?'Expired':'Active';return <tr key={item.id}><th scope="row">{sessionIdentity(item)}</th><td>{formatMoment(item.created_at,lang)}</td><td>{formatMoment(item.expires_at,lang)}</td><td>{state}</td><td>{state==='Active'&&<button className="secondary" aria-label={`Revoke session ${item.id}`} onClick={()=>{setRevokeSession(item);open('revoke')}}>{t('ถอนเซสชัน','Revoke')}</button>}</td></tr>})}</tbody></table>{!sessions.length&&<p className="admin-empty">{t('ยังไม่มีเซสชัน','No sessions recorded.')}</p>}</div></>:<><div className="admin-section-heading"><h2>Security activity</h2><p>{t('เหตุการณ์ที่บันทึกในหน่วยบริการนี้ ล่าสุดไม่เกิน 200 รายการ','Up to 200 recent security events in this facility.')}</p></div><div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Event</th><th>Account</th><th>When</th></tr></thead><tbody>{events.map(item=><tr key={item.id}><th scope="row">{String(item.event||item.event_type||item.kind||item.action||'Security event').replaceAll('_',' ')}</th><td>{userNames.get(String(item.actor_id))||t('ไม่ระบุบัญชี','Unattributed')}</td><td>{formatMoment(item.created_at,lang)}</td></tr>)}</tbody></table>{loadingActivity&&<p className="admin-empty" role="status">{t('กำลังอ่านเหตุการณ์…','Loading security activity…')}</p>}{!loadingActivity&&!events.length&&!errors.activity&&<p className="admin-empty">{t('ยังไม่มีเหตุการณ์ในรายการนี้','No security events in this view.')}</p>}</div></>}
  </div>
  {mode&&<div className="admin-dialog-backdrop"><div className="admin-dialog" role="dialog" aria-modal="true" aria-labelledby="admin-dialog-title" ref={dialog}><header><div><p className="admin-eyebrow">Accounts & access</p><h2 id="admin-dialog-title">{mode==='create'?'Add user':mode==='account'?selected?.display_name:mode==='membership'?'Manage access':mode==='password'?'Reset password':mode==='care'?'Patient assignment':mode==='status'?'Change account status':'Revoke session'}</h2>{selected&&<p>{selected.username} · {selected.status}</p>}</div><button className="text-button" disabled={!!pending||sending} aria-label="Close administration dialog" onClick={close}><Icon name="close" size={18}/></button></header>
   {commandError&&<div className="admin-error" role="alert"><span>{commandError}</span>{!pending&&selected&&<button className="text-button" onClick={()=>void readLatest()}>{t('อ่านบัญชีรุ่นล่าสุด','Read latest account')}</button>}</div>}
   {pending&&<div className="admin-pending" role="status"><p>{t('กำลังยืนยันผลคำสั่งเดิม กรุณาคงหน้านี้ไว้ การส่งซ้ำใช้คำสั่งและ key เดิม','Confirming the original request. Keep this dialog open; retry uses the same command and key.')}</p>{!sending&&<button className="secondary" onClick={()=>void execute(pending)}>{t('ตรวจด้วยคำสั่งเดิม','Retry original request')}</button>}</div>}
   {mode==='account'&&selected?<div className="admin-account-detail"><h3>Memberships</h3>{(selected.memberships||[]).map(item=><div className="admin-membership-row" key={item.id}><span>{item.role.replaceAll('_',' ')}<small>{item.facility_id}</small></span><span>{item.active?'Active':'Inactive'}</span></div>)}<div className="admin-account-options"><button className="secondary" onClick={()=>setMode('membership')}>Manage access</button><button className="secondary" onClick={()=>setMode('password')}>Reset password</button><button className="secondary" onClick={()=>setMode('care')}>Patient assignment</button>{selected.id!==session.user.id&&selected.status!=='disabled'&&<button className="secondary" onClick={()=>{setTarget(selected.status==='active'?'suspended':'active');setMode('status')}}>{selected.status==='active'?'Suspend account':'Activate account'}</button>}{selected.id!==session.user.id&&['active','suspended'].includes(selected.status)&&<button className="secondary" onClick={()=>{setTarget('disabled');setMode('status')}}>Disable account</button>}</div>{selected.id===session.user.id&&<p className="admin-muted">{t('คงสิทธิ์ผู้ดูแลของบัญชีปัจจุบันไว้ เพื่อกลับมาจัดการระบบต่อได้','Keep the current administrator membership active to retain access.')}</p>}<details><summary>Account reference</summary><dl><dt>ID</dt><dd>{selected.id}</dd><dt>Version</dt><dd>{selected.version}</dd></dl></details></div>:<form onSubmit={submit}>
    {mode==='create'&&<><label className="field"><span>Full name</span><input value={displayName} onChange={event=>setDisplayName(event.target.value)} required maxLength={200} disabled={!!pending}/></label><label className="field"><span>Username</span><input value={username} onChange={event=>setUsername(event.target.value)} required minLength={3} maxLength={100} autoComplete="off" autoCapitalize="none" disabled={!!pending}/></label></>}
    {(mode==='create'||mode==='password')&&<label className="field"><span>{mode==='create'?'Initial password':'New password'}</span><input type="password" value={password} onChange={event=>setPassword(event.target.value)} required minLength={12} maxLength={200} autoComplete="new-password" disabled={!!pending}/><small>{t('อย่างน้อย 12 ตัวอักษร รหัสผ่านไม่แสดงในรายการบัญชี','At least 12 characters. Passwords are never shown in the directory.')}</small></label>}
    {(mode==='create'||mode==='membership')&&<><label className="field"><span>Role</span><select value={role} onChange={event=>setRole(event.target.value)} required disabled={!!pending}>{staffRoles.map(item=><option key={item.role} value={item.role}>{item.role.replaceAll('_',' ')}</option>)}</select></label><label className="field"><span>Facility</span><select value={facility} onChange={event=>setFacility(event.target.value)} required disabled={!!pending}>{facilities.map(item=><option key={item.id} value={item.id}>{String(item.name||item.display_name||item.id)}</option>)}</select></label>{currentRole&&<details className="admin-role-preview"><summary>{currentRole.permissions.length} persisted permissions</summary><ul>{currentRole.permissions.map(permission=><li key={permission}><code>{permission}</code></li>)}</ul></details>}</>}
    {(mode==='membership'||mode==='care')&&<label className="admin-check"><input type="checkbox" checked={active} onChange={event=>setActive(event.target.checked)} disabled={!!pending||(mode==='membership'&&selected?.id===session.user.id&&role==='system_admin'&&facility===session.user.facility_id)}/><span>{t('เปิดการเข้าถึงนี้','Enable this access')}</span></label>}
    {mode==='care'&&<label className="field"><span>Patient reference</span><input value={patientId} onChange={event=>setPatientId(event.target.value)} required maxLength={100} disabled={!!pending}/><small>{t('ใช้รหัสผู้ป่วยที่ตรวจสอบแล้วในหน่วยบริการนี้','Use a verified patient ID in this facility.')}</small></label>}
    {mode==='password'&&<p className="admin-muted">{t('การรีเซ็ตจะถอนเซสชันที่เปิดอยู่ของบัญชีนี้','Resetting revokes this account’s active sessions.')}</p>}
    {mode==='status'&&<p>{t('เปลี่ยนสถานะบัญชี','Change account status')}: <strong>{selected?.display_name}</strong> → <strong>{target}</strong></p>}
    {mode==='revoke'&&revokeSession&&<p>{t('ถอนเซสชันของ','Revoke session for')} <strong>{sessionIdentity(revokeSession)}</strong><br/>{t('สร้างเมื่อ','Created')} {formatMoment(revokeSession.created_at,lang)}</p>}
    <footer><button className="secondary" type="button" disabled={!!pending||sending} onClick={close}>{t('ยกเลิก','Cancel')}</button><button className="primary" disabled={!!pending||sending||((mode==='create'||mode==='membership')&&(!staffRoles.some(item=>item.role===role)||!facilities.some(item=>item.id===facility)))} type="submit">{sending?t('กำลังบันทึก…','Saving…'):mode==='create'?t('สร้างบัญชี','Create account'):mode==='revoke'?t('ถอนเซสชัน','Revoke session'):t('บันทึกการเปลี่ยนแปลง','Save changes')}</button></footer>
   </form>}
  </div></div>}
 </section>
}
