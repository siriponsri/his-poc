// Shell composition retains the pinned MIT shadcn sidebar-01 provenance in vendor/.
import {useEffect,useRef,useState,type FormEvent,type KeyboardEvent as ReactKeyboardEvent} from 'react'
import {Sidebar,SidebarGroup,SidebarInset,SidebarProvider,SidebarTrigger,useSidebar} from './components/sidebar'
import {Client,HttpError,rows,errorText,routePath,hasPermission,parseSession,type Session,type Row} from './lib/client'
import {ResourceWorkspace,DetailValues,Status,Alert,EmptyState,SkeletonRows,statusLabel,shortId,formatMoment} from './components/workspace'
import {AIWorkspace,DocumentWorkspace,patientResource,encounterResource,taskResource,orderResource} from './components/core-workspaces'
import {OperationsWorkspace} from './components/operations'
import {PortalRecords} from './components/portal'
import {Icon} from './components/icons'
import {field,type DomainDef,type Resource} from './lib/catalog'
import {LangProvider,useLang,groupNames,groupOrder,domainNamesEn} from './lib/i18n'
import domains from './data/full-domains.json'
import resourceCatalog from './data/resource-catalog.json'

const client=new Client()
function safeDestination(path:string){return path.startsWith('/domains/')||path==='/worklist'||path==='/audit'?path:'/home'}
function useNames(){
 const {lang}=useLang()
 return {
  domainName:(id:string)=>{const d=domains.find(x=>x.id===id);return d?(lang==='en'&&domainNamesEn[id])||d.name_th:id},
  groupName:(group:string)=>groupNames[group]?.[lang==='en'?1:0]||group.replaceAll('_',' '),
 }
}
function LanguageToggle(){
 const {lang,setLang}=useLang()
 return <div className="lang-toggle" role="group" aria-label="ภาษา / Language">
  <button type="button" aria-pressed={lang==='th'} onClick={()=>setLang('th')} lang="th">ไทย</button>
  <button type="button" aria-pressed={lang==='en'} onClick={()=>setLang('en')} lang="en">EN</button>
 </div>
}
function Brand({caption,onClick}:{caption:string;onClick?:()=>void}){
 return <a className="brand" href={onClick?'/home':'/'} onClick={onClick?e=>{e.preventDefault();onClick()}:undefined}><span className="brand-icon" aria-hidden="true"><svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round"><path d="M12 5v14M5 12h14"/></svg></span><span>CareBalance<small>{caption}</small></span></a>
}

function Login({onLogin,error:sessionError}:{onLogin:(session:Session)=>void;error:string}){
 const {t}=useLang()
 const [username,setUsername]=useState('');const [password,setPassword]=useState('');const [busy,setBusy]=useState(false);const [error,setError]=useState(sessionError)
 async function submit(event:FormEvent){event.preventDefault();setBusy(true);setError('');try{const session=parseSession(await client.mutate<Session>('auth/login',{username,password}));client.csrf=session.csrf_token;setPassword('');onLogin(session)}catch(e){setError(e instanceof HttpError&&e.status===401?t('ชื่อบัญชีหรือรหัสผ่านไม่ถูกต้อง กรุณาตรวจสอบแล้วลองอีกครั้ง','The username or password is incorrect. Check them and try again.'):errorText(e))}finally{setBusy(false)}}
 return <main className="login-page">
  <section className="login-story">
   <Brand caption="Hospital workspace"/>
   <div className="login-copy">
    <h1>{t('พื้นที่ทำงานของทีมโรงพยาบาล','Your hospital workspace')}</h1>
    <p>{t('เวชระเบียน งานบริการ และการตรวจเอกสาร ในบริบทผู้ป่วยเดียวกัน','Records, care workflows and document review in one patient context.')}</p>
    <ol className="login-points">
     <li><Icon name="user"/><div><strong>{t('เลือกผู้ป่วยและการรับบริการ','Patient & encounter')}</strong><span>{t('เปิดงานที่เกี่ยวข้องกับผู้ป่วยจากพื้นที่ทำงานของคุณ','Open the relevant work from your assigned workspace.')}</span></div></li>
     <li><Icon name="list"/><div><strong>{t('ทำงานร่วมกันตามหน้าที่','Work together')}</strong><span>{t('บันทึก ส่งต่อ และติดตามสถานะด้วยสิทธิ์ของบัญชี','Record, hand over and follow work within your permissions.')}</span></div></li>
     <li><Icon name="history"/><div><strong>{t('ทบทวนก่อนบันทึกผล','Review before recording')}</strong><span>{t('ตรวจเอกสารต้นฉบับและอนุมัติข้อเสนอ AI ก่อนใช้งาน','Check source documents and approve AI proposals before recording.')}</span></div></li>
    </ol>
   </div>
   <p className="login-note">{t('HIS POC · ใช้ข้อมูลสังเคราะห์ในการสาธิต','HIS POC · synthetic demonstration data')}</p>
  </section>
  <section className="login-panel">
   <div className="login-form-box">
    <div className="login-form-top"><LanguageToggle/></div>
    <h2>{t('เข้าสู่ระบบ','Sign in')}</h2>
    <p>{t('ใช้บัญชีที่ผู้ดูแลระบบจัดเตรียมให้','Use the account your administrator prepared for you')}</p>
    {error&&<Alert kind="error">{error}</Alert>}
    <form onSubmit={submit}>
     <label className="field"><span>{t('ชื่อบัญชี','Username')}</span><input value={username} onChange={e=>setUsername(e.target.value)} autoComplete="username" autoCapitalize="none" spellCheck={false} required autoFocus/></label>
     <label className="field"><span>{t('รหัสผ่าน','Password')}</span><input type="password" value={password} onChange={e=>setPassword(e.target.value)} autoComplete="current-password" required/></label>
     <button className="primary full" disabled={busy} type="submit">{busy?t('กำลังตรวจสอบบัญชี…','Checking account…'):t('เข้าสู่ระบบ','Sign in')}</button>
    </form>
    <small>{t('หากลืมรหัสผ่าน กรุณาติดต่อผู้ดูแลระบบเพื่อรีเซ็ตบัญชี','Forgot your password? Ask your administrator to reset the account.')}</small>
   </div>
  </section>
 </main>
}

const navLabels:Record<string,[string,string]>={
 D01:['ทะเบียนผู้ป่วย','Patients'],D02:['นัดหมายและคิว','Appointments & queues'],D03:['เวชระเบียนผู้ป่วยนอก','Outpatient visits'],
 D04:['ฉุกเฉิน','Emergency'],D05:['ผู้ป่วยในและเตียง','Admissions & beds'],D06:['งานพยาบาล','Nursing'],D07:['คำสั่งและรายการงาน','Orders & tasks'],
 D08:['เภสัชกรรม','Pharmacy'],D09:['การให้ยา','Medication administration'],D10:['ห้องปฏิบัติการ','Laboratory'],D11:['รังสีและภาพการแพทย์','Radiology'],
 D12:['ห้องผ่าตัด','Operating room'],D13:['ICU','ICU'],D14:['สูติกรรม','Obstetrics'],D15:['กุมารเวชกรรม','Pediatrics'],D16:['เวชศาสตร์ฟื้นฟู','Rehabilitation'],
 D17:['ทันตกรรมและคลินิก','Dental & specialty'],D18:['ธนาคารเลือด','Blood bank'],D19:['โภชนาการ','Nutrition'],D20:['ส่งต่อและติดตาม','Referrals & follow-up'],
 D21:['พอร์ทัลผู้ป่วย','Patient portal'],D22:['เอกสารและเวชระเบียน','Documents'],D23:['ราคาและสิทธิรักษา','Charges & coverage'],D24:['เคลมและลูกหนี้','Claims'],
 D25:['การเงินและรับชำระ','Payments & finance'],D26:['ต้นทุนและงบประมาณ','Costing & budget'],D27:['จัดซื้อและสัญญา','Procurement'],D28:['คลังยาและเวชภัณฑ์','Inventory'],
 D29:['ครุภัณฑ์','Assets'],D30:['บุคลากรและตารางเวร','Staff & rosters'],D31:['บริการสนับสนุน','Support services'],D32:['คุณภาพและความเสี่ยง','Quality & risk'],
 D33:['รายงานสาธารณสุข','Public health reports'],D34:['บัญชีและสิทธิ์','Accounts & access'],D35:['การเชื่อมต่อระบบ','Integrations'],D36:['ข้อมูลและการวิเคราะห์','Analytics'],
 D37:['ตรวจเอกสารด้วย AI','AI document review'],D38:['ดูแลระบบและกู้คืน','Operations & recovery']}
function langNav(id:string,t:(th:string,en:string)=>string,fallback:string){const names=navLabels[id];return names?t(...names):fallback}

function Navigation({session,route,navigate}:{session:Session;route:string;navigate:(path:string)=>void}){
 const {t}=useLang();const {domainName,groupName}=useNames()
 const [query,setQuery]=useState('');const [collapsed,setCollapsed]=useState<Record<string,boolean>>({});const {close}=useSidebar();const searchRef=useRef<HTMLInputElement>(null);const navRef=useRef<HTMLElement>(null)
 const needle=query.trim().toLowerCase()
 const visible=domains.filter(d=>hasPermission(session.user,d.id)).filter(d=>(d.id+' '+d.name_th+' '+(domainNamesEn[d.id]||'')).toLowerCase().includes(needle))
 const groups=[...new Set(visible.map(d=>d.domain_group))].sort((a,b)=>groupOrder.indexOf(a)-groupOrder.indexOf(b))
 function go(path:string){navigate(path);close()}
 useEffect(()=>{const key=(e:KeyboardEvent)=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();searchRef.current?.focus();searchRef.current?.select()}};window.addEventListener('keydown',key);return()=>window.removeEventListener('keydown',key)},[])
 useEffect(()=>{navRef.current?.querySelector<HTMLElement>('[aria-current=page]')?.scrollIntoView?.({block:'nearest'})},[route])
 const canAudit=session.user.permissions.some(p=>p.includes('audit')||p==='*')||session.user.roles.some(r=>['auditor','system_admin'].includes(r))
 const link=(target:string,icon:string,label:string)=><button className={'nav-link '+(route===target?'active':'')} aria-current={route===target?'page':undefined} onClick={()=>go('/'+target)}><Icon name={icon} size={19}/><span>{label}</span></button>
 return <Sidebar>
  <Brand caption={session.user.patient_scope?'PATIENT PORTAL':'HOSPITAL WORKSPACE'} onClick={()=>go('/home')}/>
  <div className="nav-search"><Icon name="search" size={17}/><input ref={searchRef} aria-label="ค้นหาเมนู" value={query} onChange={e=>setQuery(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'&&visible.length===1)go('/domains/'+visible[0].id);if(e.key==='Escape')setQuery('')}} placeholder={t('ค้นหาพื้นที่งาน…','Find a workspace…')}/><kbd aria-hidden="true">Ctrl K</kbd></div>
  <nav ref={navRef} aria-label={t('พื้นที่ทำงาน','Workspaces')}>
   {!needle&&<SidebarGroup title={t('งานของฉัน','My work')}>
    {link('home','home',t('ภาพรวมงาน','Overview'))}
    {link('worklist','list',t('รายการงาน','Worklist'))}
    {canAudit&&link('audit','history',t('ประวัติการเข้าถึง','Access history'))}
   </SidebarGroup>}
   {groups.map(group=>{const members=visible.filter(d=>d.domain_group===group);const open=!!needle||!collapsed[group]||members.some(d=>d.id===route)
    return <div className="sidebar-group" key={group}>
     <h2><button type="button" className="group-toggle" aria-expanded={open} onClick={()=>setCollapsed(old=>({...old,[group]:!old[group]}))}><span>{groupName(group)}</span><span className="group-count">{members.length}</span><Icon name="chevron" size={14}/></button></h2>
     {open&&members.map(d=><button className={'nav-link domain-link '+(route===d.id?'active':'')} aria-current={route===d.id?'page':undefined} key={d.id} aria-label={d.id+' '+domainName(d.id)} onClick={()=>go('/domains/'+d.id)}><span className="domain-code">{d.id}</span><span title={domainName(d.id)}>{langNav(d.id,t,domainName(d.id))}</span></button>)}
    </div>})}
   {needle&&!visible.length&&<p className="nav-empty">{t('ไม่พบพื้นที่งานที่ตรงกับ','No workspace matches')} “{query}”</p>}
  </nav>
  <div className="sidebar-footer"><span className="avatar" aria-hidden="true">{session.user.display_name.slice(0,2)}</span><div><strong>{session.user.display_name}</strong><small>{session.user.roles.join(' / ')} · {session.user.facility_id}</small></div></div>
 </Sidebar>
}

type DomainCount={domain:string;record_count:number;pending_count:number;href:string;pending_states_rule:string}
function Home({session,navigate}:{session:Session;navigate:(path:string)=>void}){
 const {lang,t}=useLang();const {domainName,groupName}=useNames()
 const [data,setData]=useState<Record<string,unknown>|null>(null);const [error,setError]=useState('');const [showAll,setShowAll]=useState(false);const [allCounts,setAllCounts]=useState(false)
 useEffect(()=>{let active=true;client.get('home').then(d=>{if(active)setData(d)}).catch(e=>{if(active)setError(errorText(e))});return()=>{active=false}},[session.user.id])
 const counters=data?.counters||data?.counts||(data?{'งานที่เปิด':data.open_tasks}:null)
 const work=rows(data?.tasks||data?.worklist||data?.items)
 const domainCounts=Array.isArray(data?.domain_counts)?data.domain_counts as DomainCount[]:[]
 const worklists=Array.isArray(data?.worklists)?data.worklists as {domain:string;id:string;status:string}[]:[]
 const allowed=domains.filter(d=>hasPermission(session.user,d.id))
 const groups=[...new Set(allowed.map(d=>d.domain_group))].sort((a,b)=>groupOrder.indexOf(a)-groupOrder.indexOf(b))
 const counterName=(name:string)=>name==='งานที่เปิด'?t('งานที่เปิด','Open tasks'):name.replaceAll('_',' ')
 const recent=showAll?worklists:worklists.slice(0,8)
 const rankedCounts=domainCounts.slice().sort((a,b)=>b.pending_count-a.pending_count);const shownCounts=allCounts?rankedCounts:rankedCounts.slice(0,5)
 return <>
  <header className="home-header">
   <div><h1>{t('ภาพรวมงาน','Work overview')}</h1><p>{session.user.display_name} <span aria-hidden="true">/</span> {session.user.facility_id}</p></div>
   {counters&&typeof counters==='object'&&<dl className="stat-strip">{Object.entries(counters).map(([name,value])=><div key={name}><dt>{counterName(name)}</dt><dd><button className="stat-button" onClick={()=>navigate('/worklist')} aria-label={counterName(name)+' '+String(value)}><strong>{String(value)}</strong><Icon name="chevron" size={16}/></button></dd></div>)}</dl>}
  </header>
  {error&&<Alert kind="error">{error}</Alert>}
  <div className="workspace-shortcuts" aria-label={t('เปิดงานที่ใช้บ่อย','Frequent workspaces')}>
   {['D01','D03','D22','D37'].filter(id=>hasPermission(session.user,id)).map(id=><button key={id} className="shortcut" onClick={()=>navigate('/domains/'+id)}><Icon name={id==='D01'?'user':id==='D37'?'spark':'list'} size={19}/><span>{langNav(id,t,domainName(id))}</span><Icon name="chevron" size={15}/></button>)}
  </div>
  <div className="home-grid">
   <section className="card flush">
    <div className="section-heading"><h2>{t('งานที่เกี่ยวข้อง','Your tasks')}</h2><button className="text-button" onClick={()=>navigate('/worklist')}>{t('เปิดรายการงาน →','Open worklist →')}</button></div>
    {!data&&!error?<SkeletonRows label={t('กำลังโหลดงานจากเซิร์ฟเวอร์…','Loading tasks from the server…')}/>:work.length?work.slice(0,5).map(row=><button key={row.id} className="record-button" onClick={()=>navigate('/domains/'+String(row.domain||'D07'))}>
     <div><strong>{String(row.title||row.id)}</strong><small className="record-meta">{row.domain?<span>{String(row.domain)} {domainName(String(row.domain))}</span>:null}{row.encounter_id?<span title={String(row.encounter_id)}>{shortId(row.encounter_id)}</span>:null}{row.created_at?<span>{formatMoment(row.created_at,lang)}</span>:null}</small></div>
     {row.status?<Status value={row.status}/>:null}<span className="chevron"><Icon name="chevron" size={18}/></span>
    </button>):<EmptyState title={t('ไม่มีงานในรายการที่โหลด','No tasks in your list')}>{t('สร้างหรือรับงานจากโมดูลที่คุณมีสิทธิ์','Create or pick up a task from a workspace you can access')}</EmptyState>}
   </section>
   {domainCounts.length>0&&<section className="card flush">
    <div className="section-heading"><h2>{t('ปริมาณงานตามพื้นที่','Workload by workspace')}</h2>{domainCounts.length>5&&<button className="text-button" aria-expanded={allCounts} onClick={()=>setAllCounts(!allCounts)}>{allCounts?t('แสดงน้อยลง','Show fewer'):t('แสดงทั้งหมด','Show all')+' ('+domainCounts.length+')'}</button>}</div>
    <table className="data-table"><thead><tr><th scope="col">{t('พื้นที่งาน','Workspace')}</th><th scope="col" className="num">{t('ค้างดำเนินการ','Pending')}</th><th scope="col" className="num">{t('ทั้งหมด','Total')}</th></tr></thead>
     <tbody>{shownCounts.map(c=><tr key={c.domain}><th scope="row"><button className="table-link" onClick={()=>navigate('/domains/'+c.domain)}><span className="domain-code">{c.domain}</span>{domainName(c.domain)}</button></th><td className={'num'+(c.pending_count?' strong':'')} title={c.pending_states_rule}>{c.pending_count}</td><td className="num">{c.record_count}</td></tr>)}</tbody>
    </table>
   </section>}
  </div>
  {worklists.length>0&&<details className="recent-records"><summary>{t('รายการล่าสุดในหน่วยงาน','Latest records in this facility')} <span className="count">{worklists.length}</span></summary><section className="card flush">
   <div className="section-heading"><h2>{t('รายการล่าสุดในหน่วยงาน','Latest records in this facility')}</h2>{worklists.length>8&&<button className="text-button" aria-expanded={showAll} onClick={()=>setShowAll(!showAll)}>{showAll?t('แสดงน้อยลง','Show fewer'):t('แสดงทั้งหมด','Show all')+' ('+worklists.length+')'}</button>}</div>
   <table className="data-table"><thead><tr><th scope="col">{t('พื้นที่งาน','Workspace')}</th><th scope="col">{t('รายการ','Record')}</th><th scope="col">{t('สถานะ','Status')}</th></tr></thead>
    <tbody>{recent.map(r=><tr key={r.domain+r.id}><th scope="row"><span className="domain-code">{r.domain}</span>{domainName(r.domain)}</th><td><button className="table-link" title={r.id} onClick={()=>navigate('/domains/'+r.domain+'?record='+encodeURIComponent(r.id))}>{shortId(r.id)}</button></td><td><Status value={r.status}/></td></tr>)}</tbody>
   </table>
  </section></details>}
  <details className="workspace-directory"><summary>{t('พื้นที่ทำงานทั้งหมด','All workspaces')} <span className="count">{allowed.length}</span></summary><section className="workspace-index" aria-labelledby="workspace-index-title">
   <div className="section-heading"><h2 id="workspace-index-title">{t('เปิดพื้นที่ทำงาน','Open a workspace')}</h2><small>{t('แสดงตามสิทธิ์จากเซิร์ฟเวอร์','Shown according to server permissions')}</small></div>
   <div className="index-groups">{groups.map(group=><div key={group}><h3>{groupName(group)}</h3><ul>{allowed.filter(d=>d.domain_group===group).map(d=><li key={d.id}><button className="index-link" onClick={()=>navigate('/domains/'+d.id)}><span className="domain-code">{d.id}</span><span>{domainName(d.id)}</span></button></li>)}</ul></div>)}</div>
  </section></details>
 </>
}

function Admin({session}:{session:Session}){
 const {t}=useLang()
 const roleOptions=['registration','clinician','nurse','laboratory','imaging','pharmacist','billing','finance','inventory','quality','system_admin','operations_admin','auditor']
 const resources:Resource[]=[{id:'users',label:'บัญชีและสิทธิ์',path:'admin/users',detailPath:false,fields:[field('username','ชื่อบัญชี'),field('display_name','ชื่อแสดง'),field('password','รหัสผ่านอย่างน้อย 12 ตัวอักษร','password'),{...field('role','บทบาท','select'),options:roleOptions},{...field('facility_id','รหัสหน่วยบริการ'),default:session.user.facility_id}],actions:[{name:'suspended',label:'ระงับบัญชี',from:['active'],target:'suspended',path:'admin/users/{id}/transition'},{name:'active',label:'เปิดบัญชี',from:['created','suspended'],target:'active',path:'admin/users/{id}/transition'},{name:'disabled',label:'ปิดบัญชี',from:['active','suspended'],target:'disabled',path:'admin/users/{id}/transition'},{name:'membership',label:'ปรับ membership',path:'admin/users/{id}/memberships',fields:[{...field('role','บทบาท','select'),options:roleOptions},{...field('facility_id','รหัสหน่วยบริการ'),default:session.user.facility_id},{...field('active','เปิดใช้สิทธิ์','checkbox',false),default:true}]},{name:'reset',label:'รีเซ็ตรหัสผ่าน',path:'admin/users/{id}/reset-password',fields:[field('password','รหัสผ่านใหม่อย่างน้อย 12 ตัวอักษร','password')]},{name:'care',label:'มอบหมายผู้ป่วย',path:'admin/users/{id}/care-assignments',omitVersion:true,fields:[field('patient_id','รหัสผู้ป่วยในหน่วยบริการ'),{...field('active','เปิดการมอบหมาย','checkbox',false),default:true}]}]},{id:'sessions',label:'เซสชัน',path:'admin/sessions',detailPath:false,fields:[],actions:[{name:'revoke',label:'ถอนเซสชัน',path:'admin/sessions/{id}/revoke',omitVersion:true}]}]
 return <><details className="card disclosure"><summary>{t('บัญชีและสิทธิ์ปัจจุบันของคุณ','Your current account and permissions')}</summary><DetailValues record={{...session.user}}/></details><DomainResources resources={resources} context={{patient_id:'',encounter_id:''}}/></>
}

function DomainResources({resources,context,readOnly=false}:{resources:Resource[];context:{patient_id:string;encounter_id:string};readOnly?:boolean}){
 const [tab,setTab]=useState(resources[0]?.id||'');const resource=resources.find(r=>r.id===tab)||resources[0]
 function arrows(e:ReactKeyboardEvent<HTMLDivElement>){if(e.key!=='ArrowRight'&&e.key!=='ArrowLeft')return;e.preventDefault();const container=e.currentTarget;const index=resources.findIndex(r=>r.id===resource?.id);const next=resources[(index+(e.key==='ArrowRight'?1:-1)+resources.length)%resources.length];setTab(next.id);setTimeout(()=>container.querySelector<HTMLElement>('[aria-selected=true]')?.focus(),0)}
 return <><div className={'resource-tabs'+(resources.length<2?' single':'')} role="tablist" onKeyDown={arrows}>{resources.map(r=><button key={r.id} role="tab" aria-selected={r.id===resource?.id} tabIndex={r.id===resource?.id?0:-1} onClick={()=>setTab(r.id)}>{r.label}</button>)}</div>{resource&&<ResourceWorkspace key={resource.id+context.patient_id+context.encounter_id} client={client} resource={resource} context={context} readOnly={readOnly}/>}</>
}

function Workspace(){
 const {lang,t}=useLang();const {domainName,groupName}=useNames()
 const authGeneration=useRef(0);const booted=useRef(false);const [session,setSession]=useState<Session|null>(null);const [booting,setBooting]=useState(true);const [sessionError,setSessionError]=useState('');const [path,setPath]=useState(location.pathname);const [patient,setPatient]=useState('');const [encounter,setEncounter]=useState('');const [patients,setPatients]=useState<Row[]>([]);const [encounters,setEncounters]=useState<Row[]>([]);const [contextError,setContextError]=useState('');const [pending,setPending]=useState(false);const originalDestination=useRef(safeDestination(location.pathname));const route=routePath(path);const domain=domains.find(d=>d.id===route);const mainRef=useRef<HTMLDivElement>(null)
 // A 401 while the first session probe is still running means "not signed in yet", not "session expired".
 useEffect(()=>{const pop=()=>setPath(location.pathname);const event=(e:Event)=>setPending(Boolean((e as CustomEvent).detail));const expired=()=>{if(!booted.current)return;authGeneration.current++;client.csrf='';setSession(null);setPatient('');setEncounter('');setPatients([]);setEncounters([]);setPending(false);setSessionError('เซสชันหมดอายุหรือถูกถอน กรุณาเข้าสู่ระบบอีกครั้ง');history.replaceState({},'','/login');setPath('/login')};window.addEventListener('his-session-expired',expired);window.addEventListener('popstate',pop);window.addEventListener('his-pending',event);client.get<Session>('auth/me').then(raw=>{const s=parseSession(raw);client.csrf=s.csrf_token;setSession(s);if(location.pathname==='/login'||location.pathname==='/'){history.replaceState({},'',originalDestination.current);setPath(originalDestination.current)}}).catch(e=>{client.csrf='';if(!(e instanceof HttpError&&e.status===401))setSessionError(errorText(e));history.replaceState({},'','/login');setPath('/login')}).finally(()=>{booted.current=true;setBooting(false)});return()=>{window.removeEventListener('his-session-expired',expired);window.removeEventListener('popstate',pop);window.removeEventListener('his-pending',event)}},[])
 useEffect(()=>{if(!session)return;let current=true;setPatients([]);setEncounters([]);setPatient(session.user.patient_scope||'');setEncounter('');if(!session.user.patient_scope&&!hasPermission(session.user,'D01'))return()=>{current=false};if(session.user.patient_scope){setPatients([{id:session.user.patient_scope,display_name:session.user.display_name}]);return()=>{current=false}}client.get('patients').then(data=>{if(current)setPatients(rows(data))}).catch(e=>{if(current)setContextError(errorText(e))});return()=>{current=false}},[session?.user.id,session?.user.facility_id])
 useEffect(()=>{let current=true;setEncounters([]);setEncounter('');if(patient&&!session?.user.patient_scope)client.get('encounters?patient_id='+encodeURIComponent(patient)).then(data=>{if(current)setEncounters(rows(data))}).catch(e=>{if(current)setContextError(errorText(e))});return()=>{current=false}},[patient])
 function navigate(to:string){if(pending){window.alert('ยังมีรายการที่ไม่ยืนยันผล กรุณาอ่านผลล่าสุดหรือ retry คำสั่งเดิมก่อนเปลี่ยนหน้า');return}history.pushState({},'',to);setPath(location.pathname);if(new URL(to,location.origin).searchParams.has('record')){setPatient('');setEncounter('')}setTimeout(()=>mainRef.current?.focus(),0)}
 function enter(s:Session){const generation=++authGeneration.current;client.get<Session>('auth/me').then(raw=>{const fresh=parseSession(raw);if(generation===authGeneration.current)setSession(fresh)}).catch(()=>{});client.csrf=s.csrf_token;setSession(s);setPatient('');setEncounter('');setPatients([]);setEncounters([]);setSessionError('');const destination=originalDestination.current;history.replaceState({},'',destination);setPath(destination)}
 async function switchMembership(id:string){if(pending)return;try{await client.mutate('auth/context',{membership_id:id});const fresh=parseSession(await client.get<Session>('auth/me'));setPatient('');setEncounter('');setPatients([]);setEncounters([]);setContextError('');setSession(fresh);navigate('/home')}catch(e){setContextError(errorText(e))}}
 async function logout(){if(pending&&!window.confirm('มีรายการรอยืนยัน การออกระบบจะล้างร่างและ key ในหน้านี้ ควรตรวจผลหลังเข้าสู่ระบบอีกครั้ง ออกจากระบบหรือไม่?'))return;try{authGeneration.current++;await client.mutate('auth/logout',{});client.csrf='';setSession(null);setPatient('');setEncounter('');setPatients([]);setEncounters([]);setPending(false);history.replaceState({},'','/login');setPath('/login')}catch(e){setContextError(errorText(e))}}
 if(booting)return <main className="boot-screen"><span className="brand-icon" aria-hidden="true"><svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round"><path d="M12 5v14M5 12h14"/></svg></span><h1>{t('กำลังตรวจเซสชัน','Checking your session')}</h1><p>{t('โหลดสิทธิ์และขอบเขตจากเซิร์ฟเวอร์','Loading permissions and scope from the server')}</p></main>
 if(!session)return <Login onLogin={enter} error={sessionError}/>
 const context={patient_id:patient,encounter_id:encounter};const activePatient=patients.find(p=>p.id===patient);const activeEncounter=encounters.find(e=>e.id===encounter);const clinical=domain&&Number(domain.id.slice(1))<=22||route==='D37';const resources=(resourceCatalog as DomainDef[]).find(d=>d.id===route)?.resources||[]
 const pageName=domain?domainName(domain.id):({home:t('ภาพรวมงาน','Overview'),worklist:t('รายการงานร่วมกัน','Shared worklist'),audit:t('ประวัติการเข้าถึง','Access history'),'not-found':t('ไม่พบหน้า','Not found')}[route]||t('ภาพรวมงาน','Overview'))
 const patientFacts=activePatient?[activePatient.id,activePatient.sex&&activePatient.sex!=='unknown'?String(activePatient.sex):'',activePatient.birth_date?t('เกิด ','Born ')+new Date(String(activePatient.birth_date)).toLocaleDateString(lang==='en'?'en-GB':'th-TH',{dateStyle:'medium'}):''].filter(Boolean):[]
 return <SidebarProvider><button className="skip-link" onClick={()=>mainRef.current?.focus()}>ข้ามไปยังเนื้อหา</button><Navigation session={session} route={route} navigate={navigate}/><SidebarInset>
  <header className="topbar">
   <div className="breadcrumb"><SidebarTrigger/><span>{domain?groupName(domain.domain_group):session.user.patient_scope?t('พอร์ทัลผู้ป่วย','Patient portal'):t('งานของฉัน','My work')}</span><b aria-hidden="true">/</b><strong>{pageName}</strong></div>
   <div className="top-actions">
    {session.memberships&&session.memberships.length>1&&<select aria-label="ขอบเขตหน่วยบริการ" disabled={pending} value={session.memberships.find(m=>m.facility_id===session.user.facility_id)?.id||''} onChange={e=>switchMembership(e.target.value)}>{session.memberships.map(m=><option key={m.id} value={m.id}>{m.facility_id} · {m.role}</option>)}</select>}
    <span className="demo-pill" title={t('ข้อมูลสังเคราะห์สำหรับการพัฒนา','Synthetic development data')}>SYNTHETIC</span>
    <LanguageToggle/>
    <button className="secondary logout" onClick={logout}><Icon name="logout" size={17}/>{t('ออกจากระบบ','Sign out')}</button>
   </div>
  </header>
  {clinical&&!session.user.patient_scope&&<section className={'patient-context'+(activePatient?'':' unset')} aria-label={t('บริบทผู้ป่วย','Patient context')}>
   <div className="context-title">
    <span className="patient-avatar" aria-hidden="true">{activePatient?String(activePatient.display_name).slice(0,2):<Icon name="user" size={20}/>}</span>
    <div><small>{activePatient?t('กำลังทำงานกับ','Working with'):t('บริบทการทำงาน','Working context')}</small><strong>{String(activePatient?.display_name||t('เลือกผู้ป่วยก่อนทำงาน','Select a patient to begin'))}</strong>
     {activePatient&&<span className="context-facts">{patientFacts.map((fact,i)=><span key={i}>{fact}</span>)}{activeEncounter?<span className="context-encounter">{String(activeEncounter.kind)} · {statusLabel(String(activeEncounter.status),lang)}</span>:<span>{t('ทุกการรับบริการ','All encounters')}</span>}</span>}
    </div>
   </div>
   <label><span>{t('ผู้ป่วย','Patient')}</span><select value={patient} disabled={pending||!!session.user.patient_scope} onChange={e=>setPatient(e.target.value)}><option value="">{t('ยังไม่เลือก','Not selected')}</option>{patients.map(p=><option key={p.id} value={p.id}>{String(p.display_name)} · {p.id}</option>)}</select></label>
   <label><span>{t('การรับบริการ','Encounter')}</span><select value={encounter} disabled={pending||!patient} onChange={e=>setEncounter(e.target.value)}><option value="">{t('ทุก encounter ของผู้ป่วย','All encounters for this patient')}</option>{encounters.map(e=><option key={e.id} value={e.id}>{String(e.kind)} · {e.id} · {statusLabel(String(e.status),lang)}</option>)}</select></label>
  </section>}
  <div className="page" ref={mainRef} tabIndex={-1}>
   {contextError&&<Alert kind="error">{contextError}</Alert>}
   {route==='home'||route==='login'?<Home session={session} navigate={navigate}/>:route==='not-found'?<section className="card empty"><h1>404 · ไม่พบหน้านี้</h1><p>{t('URL นี้ไม่มีพื้นที่ทำงานที่รองรับ','This address does not match any workspace')}</p><button className="primary" onClick={()=>navigate('/home')}>{t('กลับภาพรวม','Back to overview')}</button></section>:domain&&!hasPermission(session.user,domain.id)?<section className="card empty"><span className="empty-icon"><Icon name="shield" size={26}/></span><h1>ไม่มีสิทธิ์เข้าพื้นที่นี้</h1><p>{t('สิทธิ์ปัจจุบันกำหนดโดย membership ของบัญชี ไม่สามารถเปลี่ยนบทบาทจากหน้าเว็บเองได้','Access is set by this account’s membership and cannot be changed from the browser')}</p><button className="secondary" onClick={()=>navigate('/home')}>{t('กลับภาพรวม','Back to overview')}</button></section>:<>
    <div className="page-title"><h1>{pageName}</h1>{domain&&<span className="domain-chip" title={groupName(domain.domain_group)}>{domain.id}</span>}{domain&&!hasPermission(session.user,domain.id,true)&&<span className="scope-chip">{t('อ่านอย่างเดียว','Read only')}</span>}</div>
    <div key={session.user.id+route+patient+encounter}>{route==='D01'?<ResourceWorkspace readOnly={!hasPermission(session.user,'D01',true)} resource={patientResource} client={client} context={context} onSelectContext={row=>{setPatient(row.id);navigate('/domains/D03')}}/>:route==='D03'?<ResourceWorkspace readOnly={!hasPermission(session.user,'D03',true)} resource={encounterResource} client={client} context={context} onSelectContext={row=>{setPatient(String(row.patient_id));setEncounter(row.id)}}/>:route==='D07'?<DomainResources resources={[orderResource,taskResource]} context={context} readOnly={!hasPermission(session.user,'D07',true)}/>:route==='D38'?<OperationsWorkspace client={client}/>:route==='worklist'?<ResourceWorkspace resource={taskResource} client={client} context={context}/>:route==='D22'?<DocumentWorkspace client={client} context={context} canEdit={hasPermission(session.user,'D22',true)&&(session.user.permissions.includes('documents.content')||session.user.permissions.includes('*'))}/>:route==='D37'?<AIWorkspace client={client} context={context} canWrite={hasPermission(session.user,'D37',true)} canReview={session.user.permissions.includes('clinical.approve')||session.user.permissions.includes('*')}/>:route==='D34'?<Admin session={session}/>:route==='audit'?<ResourceWorkspace resource={{id:'audit',label:'Audit trail',path:'audit',detailPath:false,fields:[],actions:[]}} client={client} context={context}/>:resources.length?<>{route==='D21'&&session.user.patient_scope&&<PortalRecords client={client}/>}<DomainResources resources={resources} context={context} readOnly={!hasPermission(session.user,route,true)}/></>:<Alert kind="error">ไม่พบ contract ของหน้าจอ {route} ใน build นี้ กรุณาตรวจการสร้าง resource catalog</Alert>}</div>
   </>}
   <footer className="page-footer"><span>CareBalance · HIS POC · Development prototype</span><span>{t('ข้อมูลสังเคราะห์ · ไม่ใช้ตัดสินใจรักษา','Synthetic data · not for clinical decisions')}</span></footer>
  </div>
 </SidebarInset></SidebarProvider>
}
export default function App(){return <LangProvider><Workspace/></LangProvider>}
