export type Mode = 'fixture'|'api'
export type DocumentContent = {text:string;author?:string;signed_at?:string}
export type Action = {kind:'document_completeness';summary:string;missing_fields:string[]}
export type Evidence = {encounter_version:number;document_id:string;document_version:number;document_hash:string;locator:string;data_class:string}
export type Proposal = {id:string;patient:string;encounter:string;version:number;action:Action;action_hash:string;snapshot:Evidence;status:'pending'|'approved'|'rejected'|'committed';expires:number;run_id:string}
export type Result = {id:string;proposal:string;patient:string;encounter:string;action:Action;review:string;created?:number}
export type Run = {id:string;outcome:string;provider:string|null;model_revision:string|null;latency_ms:number;cost:number|null;usage:unknown;error:string|null;abstain_reason:string|null}
export type Audit = {id:string;actor:string;event:string;entity:string;details:Record<string,unknown>;created:number}
export type Context = {demo:boolean;patient:string;encounter:{id:string;patient:string;version:number;status:string};document:{id:string;version:number;content:DocumentContent};evidence:Evidence;tasks:{id:string;status:string}[];proposals:Proposal[];results:Result[];runs:Run[];audit:Audit[];reviews:{id:string;proposal:string;version:number;reviewer:string;decision:string;edits:unknown;created:number}[];proposal_versions:{proposal:string;version:number;action:Action;action_hash:string}[]}
export type CommitPayload = {proposal_id:string;version:number;action_hash:string;idempotency_key:string}
export type ProposalResponse = {demo:boolean;run_id:string;outcome:string;error?:string|null;reason?:string|null;proposal?:Proposal}
// All v1 JSON-string column conversion lives here. Immediate commit action is already an object.
function object(x:unknown):Record<string,any>{if(!x||typeof x!=='object'||Array.isArray(x))throw new Error('INVALID_RESPONSE');return x as Record<string,any>}
function jsonColumn<T>(x:unknown):T{if(typeof x!=='string')throw new Error('INVALID_RESPONSE_COLUMN');return JSON.parse(x) as T}
export function decodeProposal(x:unknown):Proposal{const p=object(x);return {...p,action:jsonColumn<Action>(p.action),snapshot:jsonColumn<Evidence>(p.snapshot)} as Proposal}
export function decodeContext(x:unknown):Context{const c=object(x);if(!Array.isArray(c.proposals)||!Array.isArray(c.results))throw new Error('INVALID_RESPONSE');return {...c,document:{...c.document,content:jsonColumn<DocumentContent>(c.document.content)},proposals:c.proposals.map(decodeProposal),results:c.results.map((r:any)=>({...r,action:jsonColumn<Action>(r.action)})),runs:c.runs.map((r:any)=>({...r,usage:jsonColumn(r.usage)})),audit:c.audit.map((a:any)=>({...a,details:jsonColumn(a.details)})),reviews:c.reviews.map((r:any)=>({...r,edits:jsonColumn(r.edits)})),proposal_versions:c.proposal_versions.map((v:any)=>({...v,action:jsonColumn<Action>(v.action)}))} as Context}
export class ApiError extends Error {status:number;constructor(code:string,status=0){super(code);this.status=status}}
export class HisApi {
 token:string;fetcher:typeof fetch
 constructor(token:string,fetcher:typeof fetch=fetch){this.token=token;this.fetcher=fetcher}
 async request(path:string,body?:unknown):Promise<any>{let r:Response;try{r=await this.fetcher('/api/v1/'+path,{method:body===undefined?'GET':'POST',headers:{'Content-Type':'application/json','Authorization':'Bearer '+this.token},...(body===undefined?{}:{body:JSON.stringify(body)})})}catch{throw new ApiError('NETWORK_ERROR')}
 let data:any;try{data=await r.json()}catch{throw new ApiError('NON_JSON_RESPONSE',r.status)}
 if(!r.ok)throw new ApiError(typeof data?.error==='string'?data.error:'HTTP_ERROR',r.status);return data
 }
 async context(){return decodeContext(await this.request('context'))}
 async save(content:DocumentContent,expected_version:number){return this.request('documents',{patient:'p-demo',encounter:'e-demo',content,expected_version})}
 async propose(scenario='success'):Promise<ProposalResponse>{const r=await this.request('proposals',{patient:'p-demo',encounter:'e-demo',data_class:'synthetic',scenario});return {...r,...(r.proposal?{proposal:decodeProposal(r.proposal)}:{})}}
 async review(p:Proposal,decision:'edit'|'approve'|'reject',edits?:string){const r=await this.request('reviews',{proposal_id:p.id,version:p.version,action_hash:p.action_hash,decision,...(decision==='edit'?{edits}:{})});return {review_id:r.review_id,proposal:decodeProposal(r.proposal)}}
 async commit(payload:CommitPayload):Promise<{result:Result;replayed:boolean}>{const r=await this.request('commits',payload);object(r.result.action);return r}
}
export function requireApi(mode:Mode){if(mode!=='api')throw new ApiError('FIXTURE_READ_ONLY')}
export function commitPayload(p:Proposal,old:CommitPayload|null,newKey:()=>string):CommitPayload{if(old){if(old.proposal_id!==p.id||old.version!==p.version||old.action_hash!==p.action_hash)throw new Error('PENDING_COMMIT_CONFLICT');return old}return {proposal_id:p.id,version:p.version,action_hash:p.action_hash,idempotency_key:newKey()}}
export function errorMessage(e:unknown){const code=e instanceof Error?e.message:String(e);const messages:Record<string,string>={UNAUTHENTICATED:'กรุณาตรวจ Demo token แล้วเชื่อมต่อใหม่',FORBIDDEN_SCOPE:'ไม่มีสิทธิ์ทำรายการนี้ ข้อมูลยังไม่ได้ถูกแก้ไข',STALE_CONTEXT:'หลักฐานเปลี่ยนแล้ว กรุณาโหลดข้อมูลล่าสุดและสร้างข้อเสนอใหม่',STALE_DOCUMENT:'เอกสารมีรุ่นใหม่ ร่างของคุณยังอยู่ ตรวจข้อมูลล่าสุดก่อนบันทึก',STALE_PROPOSAL:'ข้อเสนอมีรุ่นใหม่ กรุณาโหลดและทบทวนฉบับล่าสุด',EXPIRED_PROPOSAL:'ข้อเสนอหมดอายุ กรุณาสร้างและทบทวนใหม่',TASK_NOT_OPEN:'งานนี้ปิดแล้ว อ่านผลเดิมได้ เริ่ม journey ใหม่ด้วยฐานข้อมูลใหม่',TASK_NOT_FOUND:'ไม่พบ task ตัวอย่าง ไม่สามารถบันทึกต่อได้',NETWORK_ERROR:'เชื่อมต่อไม่สำเร็จ ผลรายการอาจยังไม่แน่นอน กรุณาอ่านข้อมูลล่าสุดหรือ retry รายการเดิม',NON_JSON_RESPONSE:'คำตอบจากเซิร์ฟเวอร์ไม่ใช่ JSON กรุณาตรวจการเชื่อมต่อ',INVALID_REQUEST:'ข้อมูลที่ส่งไม่ตรงสัญญา กรุณาตรวจช่องกรอก',NOT_APPROVED:'ต้องอนุมัติข้อเสนอรุ่นนี้ก่อนบันทึก',INVALID_STATE:'สถานะเปลี่ยนแล้ว กรุณาโหลดข้อมูลล่าสุด',FIXTURE_READ_ONLY:'Fixture mode อ่านอย่างเดียว ไม่มีการเขียนไปยัง API'};return (messages[code]||'ทำรายการไม่สำเร็จ กรุณาตรวจรายละเอียดและโหลดข้อมูลล่าสุด')+' · '+code}
export class FixtureAdapter {
 readonly mode='fixture'
 fixtures:{responses:{name:string;response:unknown}[]}
 constructor(fixtures:{responses:{name:string;response:unknown}[]}){this.fixtures=fixtures}
 context(name:string){const row=this.fixtures.responses.find(r=>r.name===name&&name.startsWith('context_'));if(!row)throw new ApiError('FIXTURE_NOT_FOUND');return decodeContext(row.response)}
 mutate():never{throw new ApiError('FIXTURE_READ_ONLY')}
}
export function reconcileDraft(current:{text:string;version:number;content:DocumentContent;dirty:boolean},incoming:{version:number;content:DocumentContent},discard=false){return current.dirty&&!discard?current:{text:incoming.content.text,version:incoming.version,content:incoming.content,dirty:false}}
export function approvalReady(p:Proposal|null,dirtyReview:boolean,dirtyDocument:boolean){return !!p&&p.status==='pending'&&!dirtyReview&&!dirtyDocument}

export function bindReview(p:Proposal,binding:{id:string;version:number;action_hash:string}|null):Proposal{if(!binding||binding.id!==p.id)throw new Error("REVIEW_BINDING_MISSING");return {...p,version:binding.version,action_hash:binding.action_hash}}
