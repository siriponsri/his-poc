import {Client,HttpError} from './client'
import type {AssistantConfig,AssistantRun,AssistantWorklist,OperationsMap,OperationsZone,AssistantProfileId,AssistantEffect,Source} from './assistant-types'

export const activeExecution=(state:string)=>['queued','waiting_for_capacity','running'].includes(state)
export const executionLabels:Record<string,string>={queued:'Queued',waiting_for_capacity:'Waiting for capacity',running:'Preparing',succeeded:'Prepared',failed:'Preparation failed',timeout:'Timed out',invalid_output:'Output could not be verified',abstained:'No supported draft',stale_context:'Source changed',interrupted:'Interrupted',idle:'Idle'}
export const reviewLabels:Record<string,string>={unavailable:'No draft',pending:'Ready for your review',accepted:'Used',rejected:'Not used',superseded:'Newer revision available',stale:'Source changed'}
export const effectLabels:Record<string,string>={create_visit_draft:'Save visit draft',create_nursing_draft:'Save handover draft',create_document_review_task:'Add document review',create_nursing_followup_task:'Add nursing follow-up',create_records_review_task:'Add records review',link_lab_review_task:'Open lab review'}
/** Primary citations use source titles; exact aliases and raw fields remain in the evidence disclosure. */
export function sourceLabel(source:Source|undefined,lang='th'){const kinds:Record<string,[string,string]>={patient:['ทะเบียนผู้ป่วย','Patient record'],encounter:['การรับบริการ','Visit record'],document:['เอกสารผู้ป่วย','Patient document'],lab:['ผลตรวจห้องปฏิบัติการ','Laboratory result'],task:['งานติดตาม','Follow-up task'],handover:['บันทึกส่งต่อเวร','Handover record']};return source?.label|| (typeof source?.fields?.title==='string'?source.fields.title:'')||kinds[source?.kind||'']?.[lang==='en'?1:0]||(lang==='en'?'Source record':'ข้อมูลต้นทาง')}
export function validRun(value:AssistantRun):AssistantRun{if(!value||!value.id||!value.profile||!value.patient_id||!value.encounter_id||typeof value.patient_label!=='string'||!value.execution_state||!value.review_state||typeof value.source_digest!=='string'||!Array.isArray(value.sources)||!Array.isArray(value.effects)||value.revision!==null&&(!value.revision?.id||!Number.isInteger(value.revision.version)||!value.revision.content_hash||!Array.isArray(value.revision.facts)||!Array.isArray(value.revision.work_gaps)||!Array.isArray(value.revision.drafts)||!Array.isArray(value.revision.suggested_effects)))throw new HttpError('INVALID_ASSISTANT_RUN');return value}
export function validWorklist(value:AssistantWorklist):AssistantWorklist{if(!value||value.scope!=='authorized_work'||!Array.isArray(value.items)||!Array.isArray(value.eligible_contexts)||!Array.isArray(value.watches))throw new HttpError('INVALID_ASSISTANT_WORKLIST');value.items.forEach(validRun);return value}
export function validConfig(value:AssistantConfig):AssistantConfig{if(!value||typeof value.enabled!=='boolean'||!Array.isArray(value.profiles))throw new HttpError('ASSISTANT_UNAVAILABLE');return value}
export function validOperations(value:OperationsMap):OperationsMap{if(!value||value.scope!=='authorized_work'||!Array.isArray(value.zones)||!Array.isArray(value.agents))throw new HttpError('INVALID_OPERATIONS_MAP');return value}
export function canUseRun(run:AssistantRun){return run.execution_state==='succeeded'&&run.review_state==='pending'&&!!run.revision&&run.source_freshness==='current'}
export function runBinding(run:AssistantRun){return [run.id,run.patient_id,run.encounter_id,run.source_digest,run.revision?.id,run.revision?.version,run.revision?.content_hash].join(':')}
export function applyBody(run:AssistantRun,selected:string[],edited:string|null){if(!canUseRun(run)||!run.revision)throw new Error('Draft is not current');const allowed=new Set(run.revision.suggested_effects.map(effect=>effect.action_id));if(!selected.length||selected.some(id=>!allowed.has(id)))throw new Error('Select a supported action');return {expected_revision_id:run.revision.id,expected_version:run.revision.version,expected_content_hash:run.revision.content_hash,expected_source_digest:run.source_digest,selected_action_ids:selected,edited_draft_text:edited}}
export function internalSourceUrl(url?:string){if(!url||!/^\/(domains\/D\d{2}|worklist)(\?|$)/.test(url)||url.includes('\\'))return null;return url}
export function effectDestination(effect:AssistantEffect,run:AssistantRun){if(effect.document_id)return '/domains/D22?'+new URLSearchParams({record:effect.document_id,patient_id:run.patient_id,encounter_id:run.encounter_id});if(effect.task_id&&effect.domain&&['D01','D06','D10','D22','D37'].includes(effect.domain))return '/domains/'+effect.domain+'?'+new URLSearchParams({task_id:effect.task_id,patient_id:run.patient_id,encounter_id:run.encounter_id});return internalSourceUrl(effect.href)}
export function profileForZone(zone:OperationsZone):AssistantProfileId|null{const ids=zone.domains;if(ids.includes('D10'))return 'laboratory_handoff';if(ids.includes('D06'))return 'nursing_handover';if(ids.includes('D37'))return 'visit_preparation';if(ids.includes('D01')||ids.includes('D22'))return 'records_readiness';if(ids.includes('D03'))return 'visit_preparation';return null}
export function scopedCount(value:number|null,available:boolean){return available&&typeof value==='number'?String(value):'Unavailable'}
export type AssistantPending={path:string;body:Record<string,unknown>;key:string;binding?:string;subject?:Pick<AssistantRun,'id'|'patient_id'|'encounter_id'>;label:string}
export function validateAssistantResponse(operation:AssistantPending,value:unknown){
 const data=value as {run?:AssistantRun;runs?:AssistantRun[];watches?:unknown[];eligible_context_count?:number;decision_id?:string;effects?:unknown[];watch?:{id?:string;status?:string;profile?:string;patient_id?:string;encounter_id?:string}}
 const body=operation.body
 const matchesContext=(run:AssistantRun)=>!!run?.id&&run.profile===body.profile&&run.patient_id===body.patient_id&&run.encounter_id===body.encounter_id
 let valid=false
 if(operation.path==='assistant/runs')valid=!!data?.run&&matchesContext(data.run)
 else if(operation.path==='assistant/batches')valid=Array.isArray(data?.runs)&&Array.isArray(data.watches)&&typeof data.eligible_context_count==='number'&&data.runs.every(run=>!!run.id&&run.profile===body.profile)
 else if(operation.path.endsWith('/apply'))valid=!!data?.run&&operation.path==='assistant/runs/'+encodeURIComponent(data.run.id)+'/apply'&&(!operation.subject||data.run.patient_id===operation.subject.patient_id&&data.run.encounter_id===operation.subject.encounter_id)&&!!data.decision_id&&Array.isArray(data.effects)
 else if(operation.path==='assistant/watches')valid=!!data?.watch?.id&&data.watch.profile===body.profile&&data.watch.patient_id===body.patient_id&&data.watch.encounter_id===body.encounter_id
 else if(operation.path.endsWith('/pause'))valid=!!data?.watch?.id&&operation.path==='assistant/watches/'+encodeURIComponent(data.watch.id)+'/pause'&&data.watch.status==='paused'
 if(!valid)throw new HttpError('UNCONFIRMED_ASSISTANT_RESPONSE')
 if(data.run)validRun(data.run)
 data.runs?.forEach(validRun)
 return data
}
/** Replaying this exact operation is safe after an unknown response. Never mint a retry key. */
export async function sendAssistantOperation<T>(client:Client,operation:AssistantPending){const result=await client.mutate<T>(operation.path,operation.body,operation.key);validateAssistantResponse(operation,result);return result}
