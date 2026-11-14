// Shell composition retains the pinned MIT shadcn sidebar-01 provenance in vendor/.
import {useEffect,useLayoutEffect,useRef,useState,type FormEvent,type KeyboardEvent as ReactKeyboardEvent} from 'react'
import {Sidebar,SidebarGroup,SidebarInset,SidebarProvider,SidebarTrigger,useSidebar} from './components/sidebar'
import {Client,HttpError,rows,errorText,routePath,hasPermission,parseSession,type Session,type Row} from './lib/client'
import {ResourceWorkspace,DetailValues,Alert,statusLabel} from './components/workspace'
import {AIWorkspace,DocumentWorkspace,patientResource,encounterResource,taskResource,orderResource} from './components/core-workspaces'
import {OperationsWorkspace} from './components/operations'
import {PortalRecords} from './components/portal'
import {Icon} from './components/icons'
import {Brand,BrandMark} from './components/brand'
import {Home} from './components/home-workspace'
import {PatientRecordPanel,type PatientRecordRequest} from './components/patient-record-panel'
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
function Login({onLogin,error:sessionError}:{onLogin:(session:Session)=>void;error:string}){
 const {t}=useLang()
 const [username,setUsername]=useState('');const [password,setPassword]=useState('');const [busy,setBusy]=useState(false);const [error,setError]=useState(sessionError)
 async function submit(event:FormEvent){event.preventDefault();setBusy(true);setError('');try{const session=parseSession(await client.mutate<Session>('auth/login',{username,password}));client.csrf=session.csrf_token;setPassword('');onLogin(session)}catch(e){setError(e instanceof HttpError&&e.status===401?t('ชื่อบัญชีหรือรหัสผ่านไม่ถูกต้อง กรุณาตรวจสอบแล้วลองอีกครั้ง','The username or password is incorrect. Check them and try again.'):errorText(e))}finally{setBusy(false)}}
 return <main className="login-page">
  <header className="login-header"><Brand/><span>Clinical workspace</span><LanguageToggle/></header>
  <div className="login-layout">
  <section className="login-story">
   <span className="login-eyebrow">Care, in context.</span>
   <h1>A clearer view<br/>of every record.</h1>
   <p>{t('เวชระเบียน เอกสาร และการทบทวนข้อมูล ในพื้นที่ทำงานเดียวกัน','Records, documents and review in one connected workspace.')}</p>
   <div className="public-workflow"><span><Icon name="user" size={17}/>Records</span><span aria-hidden="true">→</span><span><Icon name="document" size={17}/>Documents</span><span aria-hidden="true">→</span><span><Icon name="check" size={17}/>Review</span></div>
   <div className="document-illustration" aria-hidden="true"><div className="outline-back"/><div className="outline-sheet"><div className="outline-heading"><Icon name="document" size={17}/>Clinical record</div><div className="outline-rule long"/><div className="outline-rule medium"/><div className="outline-divider"/><div className="outline-rule long"/><div className="outline-rule short"/><div className="outline-divider"/><div className="outline-rule long"/><div className="outline-rule medium"/></div></div>
  </section>
  <section className="login-panel">
   <div className="login-form-box">
    <span className="signin-eyebrow">YOUR WORKSPACE</span>
    <h2>Sign in</h2>
    <p>{t('ใช้บัญชีที่ผู้ดูแลระบบจัดเตรียมให้','Use the account your administrator prepared for you')}</p>
    {error&&<Alert kind="error">{error}</Alert>}
    <form onSubmit={submit}>
     <label className="field"><span>Username</span><input value={username} onChange={e=>setUsername(e.target.value)} autoComplete="username" autoCapitalize="none" spellCheck={false} required autoFocus/></label>
     <label className="field"><span>Password</span><input type="password" value={password} onChange={e=>setPassword(e.target.value)} autoComplete="current-password" required/></label>
     <button className="primary full" disabled={busy} type="submit">{busy?t('กำลังตรวจสอบบัญชี…','Checking account…'):'Sign in'}<span aria-hidden="true">→</span></button>
    </form>
    <small>{t('หากลืมรหัสผ่าน กรุณาติดต่อผู้ดูแลระบบเพื่อรีเซ็ตบัญชี','Forgot your password? Ask your administrator to reset the account.')}</small>
   </div>
  </section>
  </div>
  <footer className="login-footer"><span>CareBalance / HIS POC</span><span>{t('ข้อมูลสังเคราะห์สำหรับทดสอบ','Synthetic demonstration data')}</span></footer>
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
 const [query,setQuery]=useState('');const [collapsed,setCollapsed]=useState<Record<string,boolean>>(()=>Object.fromEntries(groupOrder.map(group=>[group,true])));const {close}=useSidebar();const searchRef=useRef<HTMLInputElement>(null);const navRef=useRef<HTMLElement>(null)
 const needle=query.trim().toLowerCase()
 const visible=domains.filter(d=>hasPermission(session.user,d.id)).filter(d=>(d.id+' '+d.name_th+' '+(domainNamesEn[d.id]||'')).toLowerCase().includes(needle))
 const primaryDomains=['D01','D22','D37'];const groupedVisible=needle?visible:visible.filter(d=>!primaryDomains.includes(d.id))
 const groups=[...new Set(groupedVisible.map(d=>d.domain_group))].sort((a,b)=>groupOrder.indexOf(a)-groupOrder.indexOf(b))
 function go(path:string){navigate(path);close()}
 useEffect(()=>{const key=(e:KeyboardEvent)=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();searchRef.current?.focus();searchRef.current?.select()}};window.addEventListener('keydown',key);return()=>window.removeEventListener('keydown',key)},[])
 useEffect(()=>{navRef.current?.querySelector<HTMLElement>('[aria-current=page]')?.scrollIntoView?.({block:'nearest'})},[route])
 const canAudit=session.user.permissions.some(p=>p.includes('audit')||p==='*')||session.user.roles.some(r=>['auditor','system_admin'].includes(r))
 const link=(target:string,icon:string,label:string)=><button className={'nav-link '+(route===target?'active':'')} aria-current={route===target?'page':undefined} onClick={()=>go('/'+target)}><Icon name={icon} size={19}/><span>{label}</span></button>
 return <Sidebar>
  <Brand onClick={()=>go('/home')}/>
  <div className="workspace-switch"><span className="workspace-monogram"><Icon name="document" size={17}/></span><div>Clinical workspace<small>{session.user.facility_id}</small></div></div>
  <div className="nav-search"><Icon name="search" size={17}/><input ref={searchRef} aria-label="ค้นหาเมนู" value={query} onChange={e=>setQuery(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'&&visible.length===1)go('/domains/'+visible[0].id);if(e.key==='Escape')setQuery('')}} placeholder={t('ค้นหาพื้นที่งาน…','Find a workspace…')}/><kbd aria-hidden="true">Ctrl K</kbd></div>
  <nav ref={navRef} aria-label={t('พื้นที่ทำงาน','Workspaces')}>
   {!needle&&<SidebarGroup title="Workspace">
    {link('home','list','Work queue')}
    {hasPermission(session.user,'D01')&&<button className={'nav-link '+(route==='D01'?'active':'')} aria-current={route==='D01'?'page':undefined} onClick={()=>go('/domains/D01')}><Icon name="user" size={17}/><span>Patients</span></button>}
    {hasPermission(session.user,'D22')&&<button className={'nav-link '+(route==='D22'?'active':'')} aria-current={route==='D22'?'page':undefined} onClick={()=>go('/domains/D22')}><Icon name="document" size={17}/><span>Documents</span></button>}
    {hasPermission(session.user,'D37')&&<button className={'nav-link '+(route==='D37'?'active':'')} aria-current={route==='D37'?'page':undefined} onClick={()=>go('/domains/D37')}><Icon name="check" size={17}/><span>Reviews</span></button>}
    {link('worklist','list','All tasks')}
    {canAudit&&link('audit','history','Activity')}
   </SidebarGroup>}
   {groups.map(group=>{const members=groupedVisible.filter(d=>d.domain_group===group);const open=!!needle||!collapsed[group]||members.some(d=>d.id===route)
    return <div className="sidebar-group" key={group}>
     <h2><button type="button" className="group-toggle" aria-expanded={open} onClick={()=>setCollapsed(old=>({...old,[group]:!old[group]}))}><span>{groupNames[group]?.[1]||groupName(group)}</span><Icon name="chevron" size={14}/></button></h2>
     {open&&members.map(d=><button className={'nav-link domain-link '+(route===d.id?'active':'')} aria-current={route===d.id?'page':undefined} key={d.id} aria-label={d.id+' '+domainName(d.id)} onClick={()=>go('/domains/'+d.id)}><span className="domain-code">{d.id}</span><span title={domainName(d.id)}>{langNav(d.id,t,domainName(d.id))}</span></button>)}
    </div>})}
   {needle&&!visible.length&&<p className="nav-empty">{t('ไม่พบพื้นที่งานที่ตรงกับ','No workspace matches')} “{query}”</p>}
  </nav>
  <div className="sidebar-footer"><span className="avatar" aria-hidden="true">{session.user.display_name.slice(0,2)}</span><div><strong>{session.user.display_name}</strong><small>{session.user.roles.join(', ')}<span>{session.user.facility_id}</span></small></div></div>
 </Sidebar>
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
 const [recordRequest,setRecordRequest]=useState<PatientRecordRequest|null>(null)
 const [scrollReset,setScrollReset]=useState(0)
 const authGeneration=useRef(0);const booted=useRef(false);const [session,setSession]=useState<Session|null>(null);const [booting,setBooting]=useState(true);const [sessionError,setSessionError]=useState('');const [path,setPath]=useState(location.pathname);const [patient,setPatient]=useState('');const [encounter,setEncounter]=useState('');const [patients,setPatients]=useState<Row[]>([]);const [encounters,setEncounters]=useState<Row[]>([]);const [contextError,setContextError]=useState('');const [pending,setPending]=useState(false);const originalDestination=useRef(safeDestination(location.pathname));const route=routePath(path.split('?')[0]);const domain=domains.find(d=>d.id===route);const mainRef=useRef<HTMLDivElement>(null)
 // Explicit navigation starts at the page heading; modal toggles and browser history keep their scroll.
 useLayoutEffect(()=>{if(!booting&&scrollReset>0)window.scrollTo({top:0,left:0,behavior:'instant'})},[scrollReset,booting])
 useEffect(()=>{setRecordRequest(null)},[session?.user.id,session?.user.facility_id])
 // A 401 while the first session probe is still running means "not signed in yet", not "session expired".
 useEffect(()=>{const pop=()=>setPath(location.pathname+location.search);const event=(e:Event)=>setPending(Boolean((e as CustomEvent).detail));const expired=()=>{if(!booted.current)return;authGeneration.current++;client.csrf='';setSession(null);setPatient('');setEncounter('');setPatients([]);setEncounters([]);setPending(false);setSessionError('เซสชันหมดอายุหรือถูกถอน กรุณาเข้าสู่ระบบอีกครั้ง');history.replaceState({},'','/login');setPath('/login');setScrollReset(value=>value+1)};window.addEventListener('his-session-expired',expired);window.addEventListener('popstate',pop);window.addEventListener('his-pending',event);client.get<Session>('auth/me').then(raw=>{const s=parseSession(raw);client.csrf=s.csrf_token;setSession(s);if(location.pathname==='/login'||location.pathname==='/'){history.replaceState({},'',originalDestination.current);setPath(originalDestination.current);setScrollReset(value=>value+1)}}).catch(e=>{client.csrf='';if(!(e instanceof HttpError&&e.status===401))setSessionError(errorText(e));history.replaceState({},'','/login');setPath('/login');setScrollReset(value=>value+1)}).finally(()=>{booted.current=true;setBooting(false)});return()=>{window.removeEventListener('his-session-expired',expired);window.removeEventListener('popstate',pop);window.removeEventListener('his-pending',event)}},[])
 useEffect(()=>{if(!session)return;let current=true;setPatients([]);setEncounters([]);setPatient(session.user.patient_scope||'');setEncounter('');const canReference=session.user.permissions.includes('patient.reference')||session.user.permissions.includes('*');if(!session.user.patient_scope&&!hasPermission(session.user,'D01')&&!canReference)return()=>{current=false};if(session.user.patient_scope){setPatients([{id:session.user.patient_scope,display_name:session.user.display_name}]);return()=>{current=false}}client.get(hasPermission(session.user,'D01')?'patients':'reference/patients').then(data=>{if(current)setPatients(rows(data))}).catch(e=>{if(current)setContextError(errorText(e))});return()=>{current=false}},[session?.user.id,session?.user.facility_id])
 useEffect(()=>{let current=true;setEncounters([]);setEncounter('');if(patient&&!session?.user.patient_scope)client.get((hasPermission(session!.user,'D03')?'encounters':'reference/encounters')+'?patient_id='+encodeURIComponent(patient)).then(data=>{if(current){const available=rows(data);setEncounters(available);const wanted=new URLSearchParams(location.search).get('encounter_id');if(wanted&&available.some(row=>row.id===wanted))setEncounter(wanted)}}).catch(e=>{if(current)setContextError(errorText(e))});return()=>{current=false}},[patient])
 // Browser history restores a scoped task destination as well as its route.
 useEffect(()=>{if(!session)return;const desired=new URLSearchParams(location.search);if(!desired.has('patient_id'))return;const requestedPatient=desired.get('patient_id')||'';if(requestedPatient!==patient){setPatient(requestedPatient);return}const requestedEncounter=desired.get('encounter_id');if(requestedEncounter&&encounters.some(row=>row.id===requestedEncounter))setEncounter(requestedEncounter)},[path,session?.user.id])
 function navigate(to:string){if(pending){window.alert('ยังมีรายการที่ไม่ยืนยันผล กรุณาอ่านผลล่าสุดหรือ retry คำสั่งเดิมก่อนเปลี่ยนหน้า');return}setScrollReset(value=>value+1);history.pushState({},'',to);setPath(location.pathname+location.search);const desired=new URL(to,location.origin).searchParams;if(desired.has('patient_id')){const desiredPatient=desired.get('patient_id')||'';setPatient(desiredPatient);if(desiredPatient===patient){const wanted=desired.get('encounter_id');setEncounter(wanted&&encounters.some(row=>row.id===wanted)?wanted:'')}else setEncounter('')}if(desired.has('record')&&!desired.has('patient_id')){setPatient('');setEncounter('')}setTimeout(()=>mainRef.current?.focus({preventScroll:true}),0)}
 function openPatientRecord(request:PatientRecordRequest){if(pending)return;setRecordRequest(request)}
 function openCurrentPatientRecord(){if(!patient)return;const query=new URLSearchParams(location.search);const taskId=query.get('task_id');const documentId=route==='D22'?query.get('record'):query.get('document_id');openPatientRecord({patient_id:patient,...(encounter?{encounter_id:encounter}:{}),...(taskId?{task_id:taskId}:{}),...(documentId?{document_id:documentId}:{})})}
 function navigateContext(nextPatient:string,nextEncounter:string){const parameters=new URLSearchParams({patient_id:nextPatient});if(nextEncounter)parameters.set('encounter_id',nextEncounter);navigate(location.pathname+'?'+parameters)}
 function enter(s:Session){const generation=++authGeneration.current;client.get<Session>('auth/me').then(raw=>{const fresh=parseSession(raw);if(generation===authGeneration.current)setSession(fresh)}).catch(()=>{});client.csrf=s.csrf_token;setSession(s);setPatient('');setEncounter('');setPatients([]);setEncounters([]);setSessionError('');const destination=originalDestination.current;history.replaceState({},'',destination);setPath(destination);setScrollReset(value=>value+1)}
 async function switchMembership(id:string){if(pending)return;try{await client.mutate('auth/context',{membership_id:id});const fresh=parseSession(await client.get<Session>('auth/me'));setPatient('');setEncounter('');setPatients([]);setEncounters([]);setContextError('');setSession(fresh);navigate('/home')}catch(e){setContextError(errorText(e))}}
 async function logout(){if(pending&&!window.confirm('มีรายการรอยืนยัน การออกระบบจะล้างร่างและ key ในหน้านี้ ควรตรวจผลหลังเข้าสู่ระบบอีกครั้ง ออกจากระบบหรือไม่?'))return;try{authGeneration.current++;await client.mutate('auth/logout',{});client.csrf='';setSession(null);setPatient('');setEncounter('');setPatients([]);setEncounters([]);setPending(false);history.replaceState({},'','/login');setPath('/login');setScrollReset(value=>value+1)}catch(e){setContextError(errorText(e))}}
 if(booting)return <main className="boot-screen"><BrandMark/><h1>{t('กำลังตรวจเซสชัน','Checking your session')}</h1><p>{t('โหลดสิทธิ์และขอบเขตจากเซิร์ฟเวอร์','Loading permissions and scope from the server')}</p></main>
 if(!session)return <Login onLogin={enter} error={sessionError}/>
 const context={patient_id:patient,encounter_id:encounter};const activePatient=patients.find(p=>p.id===patient);const activeEncounter=encounters.find(e=>e.id===encounter);const clinical=domain&&Number(domain.id.slice(1))<=22||route==='D37';const resources=(resourceCatalog as DomainDef[]).find(d=>d.id===route)?.resources||[]
 const pageName=domain?(navLabels[domain.id]?.[1]||domainName(domain.id)):({home:'Work queue',worklist:'All tasks',audit:'Activity','not-found':t('ไม่พบหน้า','Not found')}[route]||t('ภาพรวมงาน','Overview'))
 const patientFacts=activePatient?[activePatient.id,activePatient.sex&&activePatient.sex!=='unknown'?String(activePatient.sex):'',activePatient.birth_date?t('เกิด ','Born ')+new Date(String(activePatient.birth_date)).toLocaleDateString(lang==='en'?'en-GB':'th-TH',{dateStyle:'medium'}):''].filter(Boolean):[]
 return <><SidebarProvider><button className="skip-link" onClick={()=>mainRef.current?.focus()}>ข้ามไปยังเนื้อหา</button><Navigation session={session} route={route} navigate={navigate}/><SidebarInset>
  <div className={clinical?'patient-workspace':'general-workspace'}>
  <header className="topbar">
   {clinical&&<div className="record-topnav"><Brand onClick={()=>navigate('/home')}/><nav aria-label="Main navigation"><button onClick={()=>navigate('/home')}>Overview</button>{[['D01','Patients'],['D22','Documents'],['D37','Reviews']].filter(([id])=>hasPermission(session.user,id)).map(([id,label])=><button key={id} aria-current={route===id?'page':undefined} onClick={()=>navigate('/domains/'+id+'?'+new URLSearchParams({...(patient?{patient_id:patient}:{}),...(encounter?{encounter_id:encounter}:{})}))}>{label}</button>)}</nav></div>}
   <div className="breadcrumb"><SidebarTrigger/><span>{domain?groupName(domain.domain_group):session.user.patient_scope?t('พอร์ทัลผู้ป่วย','Patient portal'):t('งานของฉัน','My work')}</span><b aria-hidden="true">/</b><strong>{pageName}</strong></div>
   <div className="top-actions">
    {session.memberships&&session.memberships.length>1&&<select aria-label="ขอบเขตหน่วยบริการ" disabled={pending} value={session.memberships.find(m=>m.facility_id===session.user.facility_id)?.id||''} onChange={e=>switchMembership(e.target.value)}>{session.memberships.map(m=><option key={m.id} value={m.id}>{m.facility_id} · {m.role}</option>)}</select>}
    <span className="synthetic-note" title={t('ข้อมูลสังเคราะห์สำหรับการพัฒนา','Synthetic development data')}>HIS POC</span>
    <LanguageToggle/>
    <button className="secondary logout" onClick={logout}><Icon name="logout" size={17}/>{t('ออกจากระบบ','Sign out')}</button>
   </div>
  </header>
  {clinical&&!session.user.patient_scope&&<section className={'patient-context'+(activePatient?'':' unset')} aria-label={t('บริบทผู้ป่วย','Patient context')}>
   <div className="context-title">
    <span className="patient-avatar" aria-hidden="true">{activePatient?String(activePatient.display_name).slice(0,2):<Icon name="user" size={20}/>}</span>
    <div><small>{activePatient?t('กำลังทำงานกับ','Working with'):t('บริบทการทำงาน','Working context')}</small><strong>{patient?<button className="patient-record-identity-link" disabled={pending} onClick={openCurrentPatientRecord}>{String(activePatient?.display_name||patient)}</button>:t('เลือกผู้ป่วยก่อนทำงาน','Select a patient to begin')}</strong>
     {activePatient&&<span className="context-facts">{patientFacts.map((fact,i)=><span key={i}>{fact}</span>)}{activeEncounter?<span className="context-encounter">{String(activeEncounter.kind)} · {statusLabel(String(activeEncounter.status),lang)}</span>:<span>{t('ทุกการรับบริการ','All encounters')}</span>}</span>}
    </div>
   </div>
   <label><span>{t('ผู้ป่วย','Patient')}</span><select value={patient} disabled={pending||!!session.user.patient_scope} onChange={e=>navigateContext(e.target.value,'')}><option value="">{t('ยังไม่เลือก','Not selected')}</option>{patients.map(p=><option key={p.id} value={p.id}>{String(p.display_name)} · {p.id}</option>)}</select></label>
   <label><span>{t('การรับบริการ','Encounter')}</span><select value={encounter} disabled={pending||!patient} onChange={e=>navigateContext(patient,e.target.value)}><option value="">{t('ทุก encounter ของผู้ป่วย','All encounters for this patient')}</option>{encounters.map(e=><option key={e.id} value={e.id}>{String(e.kind)} · {e.id} · {statusLabel(String(e.status),lang)}</option>)}</select></label>
  </section>}
  {clinical&&!session.user.patient_scope&&<nav className="patient-tabs" aria-label="Patient record">{[['D03','Visits'],['D22','Documents'],['D07','Tasks'],['D37','Review']].filter(([id])=>hasPermission(session.user,id)).map(([id,label])=><button key={id} aria-current={route===id?'page':undefined} disabled={pending} onClick={()=>navigate('/domains/'+id+'?'+new URLSearchParams({...(patient?{patient_id:patient}:{}),...(encounter?{encounter_id:encounter}:{})}))}>{label}</button>)}</nav>}
  <div className="page" ref={mainRef} tabIndex={-1}>
   {contextError&&<Alert kind="error">{contextError}</Alert>}
   {route==='home'||route==='login'?<Home client={client} session={session} navigate={navigate} onOpenPatient={openPatientRecord}/>:route==='not-found'?<section className="card empty"><h1>404 · ไม่พบหน้านี้</h1><p>{t('URL นี้ไม่มีพื้นที่ทำงานที่รองรับ','This address does not match any workspace')}</p><button className="primary" onClick={()=>navigate('/home')}>{t('กลับภาพรวม','Back to overview')}</button></section>:domain&&!hasPermission(session.user,domain.id)?<section className="card empty"><span className="empty-icon"><Icon name="shield" size={26}/></span><h1>ไม่มีสิทธิ์เข้าพื้นที่นี้</h1><p>{t('สิทธิ์ปัจจุบันกำหนดโดย membership ของบัญชี ไม่สามารถเปลี่ยนบทบาทจากหน้าเว็บเองได้','Access is set by this account’s membership and cannot be changed from the browser')}</p><button className="secondary" onClick={()=>navigate('/home')}>{t('กลับภาพรวม','Back to overview')}</button></section>:<>
    <div className="page-title"><h1>{pageName}</h1>{domain&&<span className="domain-chip" title={groupName(domain.domain_group)}>{domain.id}</span>}{domain&&!hasPermission(session.user,domain.id,true)&&<span className="scope-chip">{t('อ่านอย่างเดียว','Read only')}</span>}</div>
    <div key={session.user.id+route+patient+encounter+(new URLSearchParams(location.search).get('task_id')||'')+(new URLSearchParams(location.search).get('document_id')||'')}>{route==='D01'?<ResourceWorkspace readOnly={!hasPermission(session.user,'D01',true)} resource={patientResource} onOpenPatientRecord={id=>openPatientRecord({patient_id:id})} client={client} context={context} onSelectContext={row=>navigate('/domains/D03?'+new URLSearchParams({patient_id:row.id}))}/>:route==='D03'?<ResourceWorkspace readOnly={!hasPermission(session.user,'D03',true)} resource={encounterResource} client={client} context={context} onSelectContext={row=>navigate('/domains/D03?'+new URLSearchParams({patient_id:String(row.patient_id),encounter_id:row.id}))}/>:route==='D07'?<DomainResources resources={[orderResource,taskResource]} context={context} readOnly={!hasPermission(session.user,'D07',true)}/>:route==='D38'?<OperationsWorkspace client={client}/>:route==='worklist'?<ResourceWorkspace resource={taskResource} client={client} context={context}/>:route==='D22'?<DocumentWorkspace client={client} context={context} canEdit={hasPermission(session.user,'D22',true)&&(session.user.permissions.includes('documents.content')||session.user.permissions.includes('*'))}/>:route==='D37'?<AIWorkspace client={client} context={context} canWrite={hasPermission(session.user,'D37',true)} canReview={session.user.permissions.includes('clinical.approve')||session.user.permissions.includes('*')}/>:route==='D34'?<Admin session={session}/>:route==='audit'?<ResourceWorkspace resource={{id:'audit',label:'Audit trail',path:'audit',detailPath:false,fields:[],actions:[]}} client={client} context={context}/>:resources.length?<>{route==='D21'&&session.user.patient_scope&&<PortalRecords client={client}/>}<DomainResources resources={resources} context={context} readOnly={!hasPermission(session.user,route,true)}/></>:<Alert kind="error">ไม่พบ contract ของหน้าจอ {route} ใน build นี้ กรุณาตรวจการสร้าง resource catalog</Alert>}</div>
   </>}
   <footer className="page-footer"><span>CareBalance / HIS POC</span><span>{t('ข้อมูลสังเคราะห์ · ไม่ใช้ตัดสินใจรักษา','Synthetic data · not for clinical decisions')}</span></footer>
  </div>
  </div>
 </SidebarInset></SidebarProvider>{recordRequest&&<PatientRecordPanel client={client} session={session} request={recordRequest} onClose={()=>setRecordRequest(null)} onNavigate={target=>{setRecordRequest(null);navigate(target)}}/>}</>
}
export default function App(){return <LangProvider><Workspace/></LangProvider>}
