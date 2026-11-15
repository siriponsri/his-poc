export type Row = {id:string;version?:number;status?:string;[key:string]:unknown}
export type User = {id:string;username:string;display_name:string;organization_id:string;facility_id:string;roles:string[];permissions:string[];patient_scope:string|null;memberships?:{id:string;role:string;facility_id:string}[]}
export type Session = {user:User;csrf_token:string;expires_at:string;memberships?:{id:string;role:string;facility_id:string}[]}
export type CompletenessItem={key:string;label:string;status:'present'|'missing'|'unclear';evidence_quote:string}
export type CompletenessReport={checklist_id:string;items:CompletenessItem[];summary:string;requires_human_review:true}
export type ProposalV2 = Row & {version:number;action_hash:string;task_id:string;demo?:boolean;provider?:string;action:{text:string;completeness?:CompletenessReport};evidence:{document_version_id:string;content_hash:string;encounter_version:number}}
export type PendingOperation = {path:string;body:Record<string,unknown>;key:string;proposal_id?:string;version?:number;action_hash?:string;method?:string}
export class HttpError extends Error {status:number;definitive:boolean;constructor(code:string,status=0){super(code);this.status=status;this.definitive=[400,401,403,404,409,422].includes(status)}}
export class Client {
 csrf='';fetcher:typeof fetch
 constructor(fetcher:typeof fetch=globalThis.fetch.bind(globalThis)){this.fetcher=fetcher}
 async get<T=any>(path:string):Promise<T>{return this.request<T>(path)}
 async mutate<T=any>(path:string,body:Record<string,unknown>,key:string=crypto.randomUUID(),method='POST'):Promise<T>{return this.request<T>(path,{method,body:JSON.stringify(body),headers:{'Idempotency-Key':key}})}
 async request<T>(path:string,init:RequestInit={}):Promise<T>{
  let response:Response;try{response=await this.fetcher('/api/v2/'+path,{...init,credentials:'same-origin',headers:{'Content-Type':'application/json',...(this.csrf?{'X-CSRF-Token':this.csrf}:{}),...init.headers}})}catch{throw new HttpError('NETWORK_ERROR')}
  let data:any;try{data=await response.json()}catch{throw new HttpError('INVALID_SERVER_RESPONSE',response.status)}
  if(!response.ok){if(response.status===401&&path!=='auth/login'&&typeof window!=='undefined')window.dispatchEvent(new Event('his-session-expired'));const detail=data.detail;throw new HttpError(typeof detail==='string'?detail:typeof detail?.code==='string'?detail.code:typeof data.error==='string'?data.error:Array.isArray(detail)?'INVALID_REQUEST: '+detail.map((e:any)=>[...(e.loc||[]),e.msg||'Invalid field'].join(' ')).join('; '):'HTTP_ERROR',response.status)}
  return data as T
 }
}
export function rows(value:unknown):Row[]{if(Array.isArray(value))return value as Row[];if(value&&typeof value==='object'&&Array.isArray((value as {items?:unknown}).items))return (value as {items:Row[]}).items;if(value===null||value===undefined)return [];throw new HttpError('INVALID_COLLECTION_RESPONSE')}
export function parseSession(value:unknown):Session{const s=value as Session;if(!s||typeof s.csrf_token!=='string'||!s.csrf_token||typeof s.expires_at!=='string'||!s.user||typeof s.user.id!=='string'||!Array.isArray(s.user.permissions)||!Array.isArray(s.user.roles))throw new HttpError('INVALID_SESSION_RESPONSE');return s}
export function normalizeMutation(current:Row[],incoming:Row):Row[]{return current.some(row=>row.id===incoming.id)?current.map(row=>row.id===incoming.id?incoming:row):[incoming,...current]}
export function sameProposalBinding(displayed:ProposalV2,binding:{id:string;version:number;action_hash:string}){return displayed.id===binding.id&&displayed.version===binding.version&&displayed.action_hash===binding.action_hash}
// Matching identity is mandatory; a successful GET alone does not confirm a write.
export function reconcileOperation(pending:PendingOperation|null,results:Row[]):Row|null{
 if(!pending?.proposal_id)return null
 return results.find(r=>r.proposal_id===pending.proposal_id&&r.proposal_version===pending.version&&r.action_hash===pending.action_hash&&(r.operation_key===pending.key||r.idempotency_key===pending.key))||null
}
export function routePath(path:string){if(path==='/'||path==='/home')return 'home';if(path==='/login')return 'login';const d=path.match(/^\/domains\/(D(?:0[1-9]|[12][0-9]|3[0-8]))\/?$/);return d?d[1]:path==='/worklist'?'worklist':path==='/audit'?'audit':path==='/admin'||path==='/admin/'?'admin':'not-found'}
export function hasPermission(user:User,domain:string,write=false){const permissions=user.permissions;return permissions.includes('*')||permissions.includes(`${domain}.${write?'write':'read'}`)||permissions.includes(`${domain}:${write?'write':'read'}`)||permissions.includes(`domain:${domain}:${write?'write':'read'}`)}
export const errorText=(error:unknown)=>error instanceof HttpError?({401:'เซสชันหมดอายุหรือถูกถอน กรุณาเข้าสู่ระบบอีกครั้ง',403:'บัญชีนี้ไม่มีสิทธิ์ทำรายการนี้',404:'ไม่พบข้อมูลในขอบเขตที่คุณเข้าถึงได้',409:'ข้อมูลหรือสถานะเปลี่ยนแล้ว กรุณาโหลดรุ่นล่าสุดก่อนทำรายการ'}[error.status]||error.message):String(error)
