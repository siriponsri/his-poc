import {HttpError} from './client'
import type {AssistantProfileId,ExecutionState,ReviewState} from './assistant-types'

export type TaskOwner={id:string;display_name:string;username:string}
export type TaskCapability='claim'|'release'|'assign'|'schedule'|'escalate'
export type TeamTask={id:string;version:number;domain:string;kind:string;title:string;status:string;patient_id:string;encounter_id:string;patient_label:string;assignee_id?:string|null;assignee:TaskOwner|null;due_at:string|null;priority:'low'|'normal'|'high';escalation_level:number;escalation_reason:string|null;escalated_at:string|null;overdue:boolean;capabilities:Record<TaskCapability,boolean>;created_at?:string;updated_at?:string}
export type TeamQueuePage={items:TeamTask[];total:number;offset:number;limit:number;scope:'authorized_work';observed_at:string;counts:{active:number;mine:number;unassigned:number;overdue:number;escalated:number};counts_scope:'authorized_active_work'}
export type TaskCommand={path:string;body:Record<string,unknown>;key:string;subject:Pick<TeamTask,'id'|'patient_id'|'encounter_id'|'domain'>;label:string}
export type AIOperationsItem={id:string;profile:AssistantProfileId;execution_state:ExecutionState;review_state:ReviewState;error:string|null;created_at:string;started_at:string|null;completed_at:string|null;elapsed_ms:number|null;queue_age_seconds?:number|null;usage:Record<'prompt_eval_count'|'eval_count'|'prompt_eval_duration'|'eval_duration'|'total_duration',number|null>;measured_cost:string|null;coverage:Record<'eligible_sources'|'included_sources'|'omitted_sources'|'partial_sources',number|null>;revision_count:number;effect_count:number;evidence_freshness:'not_checked_for_admin'}
export type AIOperations={observed_at:string;scope:{organization_id:string;facility_id:string};provider:{enabled:boolean;configured:boolean;route:string|null;model:string|null;model_digest:string|null;engine_version:string|null;declared_qualified_profiles:string[];context_tokens:number|null;max_output_tokens:number|null;live_status:'not_checked';selection_version?:string;qualification_scope?:string};worker:{heartbeat_status:'not_observed';heartbeat_at:null;last_started_at:string|null;last_completed_at:string|null;persisted_running:number};counts:Record<string,number>;profiles:{profile:AssistantProfileId;counts:Record<string,number>}[];items:AIOperationsItem[];total:number;offset:number;limit:number;active_watches:number}
const count=(value:unknown)=>Number.isInteger(value)&&Number(value)>=0
export function validTeamTask(value:TeamTask):TeamTask{
  if(!value||typeof value.id!=='string'||!value.id||!Number.isInteger(value.version)||value.version<1||!/^D(?:0[1-9]|[12]\d|3[0-8])$/.test(value.domain)||typeof value.title!=='string'||typeof value.patient_id!=='string'||typeof value.encounter_id!=='string'||typeof value.patient_label!=='string'||!['open','in_progress','completed','cancelled'].includes(value.status)||!['low','normal','high'].includes(value.priority)||typeof value.overdue!=='boolean'||!count(value.escalation_level)||value.escalation_level>3||!(value.due_at===null||typeof value.due_at==='string'&&Number.isFinite(Date.parse(value.due_at)))||!value.capabilities||['claim','release','assign','schedule','escalate'].some(key=>typeof value.capabilities[key as TaskCapability]!=='boolean')||!(value.assignee===null||typeof value.assignee?.id==='string'&&typeof value.assignee?.display_name==='string'&&typeof value.assignee?.username==='string'))throw new HttpError('INVALID_TEAM_TASK')
  return value
}
export function validTeamPage(value:TeamQueuePage):TeamQueuePage{
  if(!value||value.scope!=='authorized_work'||value.counts_scope!=='authorized_active_work'||!Array.isArray(value.items)||!count(value.total)||!count(value.offset)||!count(value.limit)||value.limit<1||!value.counts||['active','mine','unassigned','overdue','escalated'].some(key=>!count(value.counts[key as keyof TeamQueuePage['counts']])))throw new HttpError('INVALID_TEAM_QUEUE')
  value.items.forEach(validTeamTask);return value
}
export function taskReceipt(command:TaskCommand,value:TeamTask){
  validTeamTask(value)
  if(value.version!==Number(command.body.version)+1||['id','patient_id','encounter_id','domain'].some(key=>value[key as keyof TeamTask]!==command.subject[key as keyof TaskCommand['subject']]))throw new HttpError('UNCONFIRMED_TEAM_RESPONSE')
  return value
}
export function validAIOperations(value:AIOperations,scope:{organization_id:string;facility_id:string}):AIOperations{
  const states=['queued','waiting_for_capacity','running','succeeded','failed','timeout','invalid_output','abstained','stale_context','interrupted'],profiles=['visit_preparation','nursing_handover','records_readiness','laboratory_handoff']
  const countsValid=(counts:Record<string,number>)=>!!counts&&[...states,'awaiting_review'].every(key=>count(counts[key]))
  const measurement=(number:unknown)=>number===null||typeof number==='number'&&Number.isFinite(number)&&number>=0
  if(!value||value.scope?.organization_id!==scope.organization_id||value.scope?.facility_id!==scope.facility_id||!Array.isArray(value.items)||!Array.isArray(value.profiles)||!count(value.total)||!count(value.offset)||!count(value.limit)||value.limit<1||value.limit>50||!count(value.active_watches)||typeof value.observed_at!=='string'||value.provider?.live_status!=='not_checked'||typeof value.provider.enabled!=='boolean'||typeof value.provider.configured!=='boolean'||value.worker?.heartbeat_status!=='not_observed'||value.worker.heartbeat_at!==null||!count(value.worker.persisted_running)||!Array.isArray(value.provider.declared_qualified_profiles)||!countsValid(value.counts)||value.profiles.some(item=>!profiles.includes(item.profile)||!countsValid(item.counts)))throw new HttpError('INVALID_AI_OPERATIONS')
  for(const item of value.items)if(!item?.id||!profiles.includes(item.profile)||!states.includes(item.execution_state)||item.evidence_freshness!=='not_checked_for_admin'||!item.usage||!item.coverage||['prompt_eval_count','eval_count','prompt_eval_duration','eval_duration','total_duration'].some(key=>!measurement(item.usage[key as keyof AIOperationsItem['usage']]))||['eligible_sources','included_sources','omitted_sources','partial_sources'].some(key=>!measurement(item.coverage[key as keyof AIOperationsItem['coverage']]))||!count(item.revision_count)||!count(item.effect_count)||!(item.measured_cost===null||typeof item.measured_cost==='string'&&/^\d+(?:\.\d+)?$/.test(item.measured_cost))||!measurement(item.elapsed_ms))throw new HttpError('INVALID_AI_OPERATIONS_ITEM')
  return value
}
export function localDateTime(value:string|null){
  if(!value)return ''
  const date=new Date(value),pad=(number:number)=>String(number).padStart(2,'0')
  return `${date.getFullYear()}-${pad(date.getMonth()+1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}
