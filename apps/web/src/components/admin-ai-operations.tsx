import {useCallback,useEffect,useRef,useState} from 'react'
import {Client,errorText,type Session} from '../lib/client'
import {executionLabels,reviewLabels} from '../lib/assistant-client'
import {validAIOperations,type AIOperations,type AIOperationsItem} from '../lib/team-operations'
import {formatMoment,shortId} from './workspace'

const profiles:Record<string,string>={visit_preparation:'Visit preparation',nursing_handover:'Nursing handover',records_readiness:'Records readiness',laboratory_handoff:'Laboratory handoff'}
const states=['queued','waiting_for_capacity','running','succeeded','failed','timeout','invalid_output','abstained','stale_context','interrupted']
const nullableNumber=(value:number|null|undefined)=>value===null||value===undefined?'ยังไม่วัด':new Intl.NumberFormat('th-TH',{maximumFractionDigits:2}).format(value)
const historicalTime=(value:string|null)=>value?formatMoment(value,'th'):'ยังไม่มีข้อมูล'
function problemCount(counts:Record<string,number>){return ['failed','timeout','invalid_output','abstained','interrupted'].reduce((sum,key)=>sum+(counts[key]||0),0)}

export function AdminAIOperations({client,session,permitted}:{client:Client;session:Session;permitted:boolean}){
  const [data,setData]=useState<AIOperations|null>(null),[error,setError]=useState(''),[loading,setLoading]=useState(true),[profile,setProfile]=useState(''),[state,setState]=useState(''),[offset,setOffset]=useState(0),[expanded,setExpanded]=useState('')
  const sequence=useRef(0),mounted=useRef(true)
  const load=useCallback(async()=>{
    if(!permitted)return
    const request=++sequence.current;setLoading(true)
    const parameters=new URLSearchParams({limit:'25',offset:String(offset),...(profile?{profile}:{}),...(state?{state}:{})})
    try{const value=validAIOperations(await client.get<AIOperations>('admin/ai-operations?'+parameters),session.user);if(mounted.current&&request===sequence.current){setData(value);setError('')}}catch(reason){if(mounted.current&&request===sequence.current){setData(null);setError(errorText(reason))}}finally{if(mounted.current&&request===sequence.current)setLoading(false)}
  },[client,permitted,profile,state,offset,session.user.organization_id,session.user.facility_id])
  useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;sequence.current++}},[])
  useEffect(()=>{setExpanded('');void load();return()=>{sequence.current++}},[load])
  useEffect(()=>{
    if(!permitted||!data||!(data.counts.queued+data.counts.waiting_for_capacity+data.counts.running))return
    const timer=window.setInterval(()=>{if(document.visibilityState==='visible')void load()},5000)
    return()=>window.clearInterval(timer)
  },[permitted,data,load])
  if(!permitted)return <p className="admin-empty">บัญชีนี้ไม่มีสิทธิ์อ่านการติดตามงาน AI</p>
  const selected=data?.items.find(item=>item.id===expanded)
  return <section className="admin-ai-operations" aria-labelledby="admin-ai-title"><header className="admin-ai-heading"><div><h2 id="admin-ai-title">AI operations</h2><p>คิวงาน ผลการประมวลผล และเหตุการณ์ที่ต้องติดตาม</p></div><button className="secondary" disabled={loading} onClick={()=>void load()}>อ่านสถานะล่าสุด</button></header>
    {error&&<p className="care-error" role="alert">อ่านข้อมูลการติดตามไม่ได้ {error}</p>}{loading&&!data&&!error&&<p role="status">กำลังอ่านข้อมูลการติดตาม…</p>}
    {data&&<><dl className="admin-ai-counts"><div><dt>Waiting</dt><dd>{data.counts.queued+data.counts.waiting_for_capacity}</dd></div><div><dt>Preparing</dt><dd>{data.counts.running}</dd></div><div><dt>Needs review</dt><dd>{data.counts.awaiting_review}</dd></div><div><dt>Needs attention</dt><dd>{problemCount(data.counts)}</dd></div></dl><p className="admin-ai-scope">สถานะที่บันทึกทั้งหมดในหน่วยบริการนี้ · ตัวกรองด้านล่างใช้กับตารางรายการ · อัปเดต {formatMoment(data.observed_at,'th')}</p>
      <div className="admin-ai-observation"><section><h3>Declared configuration</h3><p>{data.provider.configured?'ตั้งค่าการเตรียมงานแล้ว':'ยังไม่ตั้งค่าการเตรียมงาน'} · {data.provider.enabled?'เปิดใช้งานตามการตั้งค่า':'ปิดตามการตั้งค่า'}</p><p>สถานะโมเดลสด: <strong>ยังไม่ได้ตรวจ</strong></p><small>โปรไฟล์ที่ผู้ดูแลระบุว่าเปิดไว้ {data.provider.declared_qualified_profiles.length} โปรไฟล์ การยืนยันตัวเลือกข้อมูลรุ่นปัจจุบันเป็นผลตรวจแยกต่างหาก</small></section><section><h3>Worker activity</h3><p>Heartbeat: <strong>ยังไม่มีข้อมูลยืนยัน</strong></p><dl><div><dt>เริ่มงานล่าสุด</dt><dd>{historicalTime(data.worker.last_started_at)}</dd></div><div><dt>เสร็จงานล่าสุด</dt><dd>{historicalTime(data.worker.last_completed_at)}</dd></div></dl><small>เวลาเหล่านี้เป็นประวัติที่บันทึกไว้ ไม่ใช่สัญญาณว่า worker กำลังทำงานอยู่ขณะนี้</small></section></div>
      <details className="admin-ai-profiles"><summary>สถานะตามโปรไฟล์</summary><div className="admin-ai-table-wrap"><table className="admin-ai-table"><thead><tr><th>Preparation</th><th>Waiting</th><th>Preparing</th><th>Needs review</th><th>Needs attention</th></tr></thead><tbody>{data.profiles.map(item=><tr key={item.profile}><th scope="row">{profiles[item.profile]||item.profile}</th><td>{(item.counts.queued||0)+(item.counts.waiting_for_capacity||0)}</td><td>{item.counts.running||0}</td><td>{item.counts.awaiting_review||0}</td><td>{problemCount(item.counts)}</td></tr>)}</tbody></table></div></details>
      <div className="admin-ai-filters"><label><span>Preparation</span><select aria-label="AI operations profile" value={profile} onChange={event=>{setProfile(event.target.value);setOffset(0)}}><option value="">All profiles</option>{Object.entries(profiles).map(([key,label])=><option key={key} value={key}>{label}</option>)}</select></label><label><span>Execution</span><select aria-label="AI operations state" value={state} onChange={event=>{setState(event.target.value);setOffset(0)}}><option value="">All states</option>{states.map(key=><option value={key} key={key}>{executionLabels[key]}</option>)}</select></label><span>{data.items.length?offset+1:0}–{offset+data.items.length} / {data.total}</span></div>
      <div className="admin-ai-table-wrap" aria-busy={loading}><table className="admin-ai-table"><thead><tr><th>Preparation / run</th><th>Execution</th><th>Review</th><th>Created</th><th>Elapsed</th><th><span className="sr-only">Read metadata</span></th></tr></thead><tbody>{data.items.map(item=><tr key={item.id}><th scope="row">{profiles[item.profile]||item.profile}<small>{shortId(item.id)}</small></th><td>{executionLabels[item.execution_state]||'Unknown'}</td><td>{reviewLabels[item.review_state]||'Unknown'}</td><td>{formatMoment(item.created_at,'th')}{item.queue_age_seconds!==null&&item.queue_age_seconds!==undefined&&<small>รอมา {nullableNumber(item.queue_age_seconds)} วินาที</small>}</td><td>{item.elapsed_ms===null?'ยังไม่วัด':nullableNumber(item.elapsed_ms/1000)+' วินาที'}</td><td><button className="text-button" aria-label={'Read AI operation '+item.id} aria-expanded={expanded===item.id} onClick={()=>setExpanded(value=>value===item.id?'':item.id)}>รายละเอียด</button></td></tr>)}</tbody></table>{!data.items.length&&<p className="admin-empty">ไม่มีรายการตามตัวกรองนี้</p>}</div>
      <div className="team-pagination"><span>รายการภายใต้สิทธิ์ปัจจุบัน</span><div><button className="secondary" disabled={loading||offset===0} onClick={()=>setOffset(Math.max(0,offset-25))}>ก่อนหน้า</button><button className="secondary" disabled={loading||offset+data.items.length>=data.total} onClick={()=>setOffset(offset+25)}>ถัดไป</button></div></div>
      {selected&&<OperationDetails item={selected}/>}
      <details className="admin-ai-config"><summary>Configuration details</summary><dl><div><dt>Route</dt><dd>{data.provider.route||'ไม่ระบุ'}</dd></div><div><dt>Model</dt><dd>{data.provider.model||'ไม่ระบุ'}</dd></div><div><dt>Engine version</dt><dd>{data.provider.engine_version||'ไม่ระบุ'}</dd></div><div><dt>Selection version</dt><dd>{data.provider.selection_version||'ไม่ระบุ'}</dd></div><div><dt>Declared profiles</dt><dd>{data.provider.declared_qualified_profiles.map(key=>profiles[key]||key).join(' · ')||'ยังไม่ระบุ'}</dd></div><div><dt>Active watches</dt><dd>{data.active_watches}</dd></div></dl></details>
    </>}
  </section>
}

function OperationDetails({item}:{item:AIOperationsItem}){
  return <section className="admin-ai-detail" aria-label="AI operation metadata"><header><h3>{profiles[item.profile]||item.profile}</h3><p>{item.id}</p></header><dl><div><dt>ข้อผิดพลาดที่บันทึก</dt><dd>{item.error||'ไม่มีรหัสข้อผิดพลาด'}</dd></div><div><dt>ต้นทุนที่บันทึก</dt><dd>{item.measured_cost===null?'ยังไม่วัด':item.measured_cost}</dd></div><div><dt>Input tokens</dt><dd>{nullableNumber(item.usage.prompt_eval_count)}</dd></div><div><dt>Output tokens</dt><dd>{nullableNumber(item.usage.eval_count)}</dd></div><div><dt>Included sources</dt><dd>{nullableNumber(item.coverage.included_sources)} / {nullableNumber(item.coverage.eligible_sources)}</dd></div><div><dt>Partial / omitted sources</dt><dd>{nullableNumber(item.coverage.partial_sources)} / {nullableNumber(item.coverage.omitted_sources)}</dd></div><div><dt>Revisions / saved effects</dt><dd>{item.revision_count} / {item.effect_count}</dd></div><div><dt>เริ่ม / เสร็จ</dt><dd>{historicalTime(item.started_at)} / {historicalTime(item.completed_at)}</dd></div></dl><p>ความสดของหลักฐานยังไม่ได้ตรวจในหน้า Admin นี้ การอ่านข้อมูลการติดตามไม่เปิดเนื้อหาร่างหรือเวชระเบียน</p></section>
}
