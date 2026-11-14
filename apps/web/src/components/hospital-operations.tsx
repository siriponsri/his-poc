import {lazy,Suspense,useEffect,useState} from 'react'
import {Client,errorText} from '../lib/client'
import {executionLabels,reviewLabels,scopedCount,validOperations} from '../lib/assistant-client'
import type {AssistantProfileId,OperationsMap,OperationsZone} from '../lib/assistant-types'
import {useLang} from '../lib/i18n'

const HospitalScene=lazy(()=>import('./hospital-scene'))
export default function HospitalOperations({client,onSelectZone,onSelectRun}:{client:Client;onSelectZone:(zone:OperationsZone)=>void;onSelectRun:(id:string,profile:AssistantProfileId)=>void}){
 const {t,lang}=useLang();const [data,setData]=useState<OperationsMap|null>(null),[error,setError]=useState(''),[loading,setLoading]=useState(true),[revision,setRevision]=useState(0)
 useEffect(()=>{let current=true;setLoading(true);client.get<OperationsMap>('assistant/operations-map').then(validOperations).then(result=>{if(current){setData(result);setError('')}}).catch(error=>{if(current)setError(errorText(error))}).finally(()=>{if(current)setLoading(false)});return()=>{current=false}},[client,revision])
 useEffect(()=>{const timer=window.setInterval(()=>setRevision(value=>value+1),15000);return()=>window.clearInterval(timer)},[])
 return <section className="care-operations"><header className="care-operations-heading"><div><h2>Operations</h2><p>{t('ผังสาธิตสำหรับดูงานในขอบเขตของคุณ ไม่ใช่ผังอาคารจริงหรือตำแหน่งบุคลากร','Illustrative layout of your authorized work. Not an actual building or staff locations.')}</p></div><button className="secondary" disabled={loading} onClick={()=>setRevision(value=>value+1)}>{t('อ่านข้อมูลล่าสุด','Refresh')}</button></header>
  {error&&<p role="alert" className="care-error">{t('อ่าน Operations ไม่สำเร็จ ข้อมูลที่แสดงอาจเปลี่ยนแล้ว','Operations could not refresh. Displayed data may have changed.')} {error}</p>}
  {!data?loading?<p role="status">{t('กำลังอ่านงาน…','Loading work…')}</p>:<p>{t('Operations ยังไม่พร้อม ใช้ Prepared work และ Work queue ต่อได้','Operations is unavailable. Prepared work and Work queue remain available.')}</p>:<>
   <Suspense fallback={<p role="status">{t('กำลังโหลดผัง 3D…','Loading 3D layout…')}</p>}><HospitalScene data={data} disabled={!!error} onSelectZone={onSelectZone} onSelectRun={onSelectRun}/></Suspense>
   <p className="care-map-help">{t('ลากเพื่อหมุน เลื่อนเพื่อซูม คลิกห้องหรือจุด AI เพื่อเปิดงาน ใช้รายการด้านล่างด้วยแป้นพิมพ์ได้เช่นกัน','Drag to orbit, scroll to zoom, select a room or AI marker to open its work. The lists below provide the same keyboard-accessible actions.')}</p>
   <div className="care-operations-lists"><section><h3>Departments</h3><ul className="care-zone-list">{data.zones.map(zone=><li key={zone.id}><button disabled={!!error||!zone.available} onClick={()=>onSelectZone(zone)}><strong>{zone.label}</strong><span>{t('งานเปิด','Open work')}: {scopedCount(zone.open_task_count,zone.available)} · {t('รอตรวจ','Awaiting review')}: {scopedCount(zone.awaiting_review_count,zone.available)}</span><small>{zone.available?t('เปิดรายการงาน','Open work list'):t('ไม่อยู่ในสิทธิ์หรือยังไม่พร้อม','Outside your permissions or unavailable')}</small></button></li>)}</ul></section>
   <section><h3>Preparation desk</h3><ul className="care-agent-list">{data.agents.map((agent,index)=><li key={agent.profile+':'+(agent.run_id||index)}><button disabled={!!error||!agent.run_id} onClick={()=>agent.run_id&&onSelectRun(agent.run_id,agent.profile)}><strong>{agent.label}</strong><span>{executionLabels[agent.execution_state]||agent.execution_state}{agent.execution_state!=='idle'?' · '+(reviewLabels[agent.review_state]||agent.review_state):''}</span>{agent.patient_label&&<small>{agent.patient_label}</small>}{!agent.run_id&&<small>{t('ไม่มีคำขอที่กำลังทำงาน','No active request')}</small>}</button></li>)}</ul></section></div>
   <p className="care-scope-note">{t('ขอบเขต: งานที่คุณมีสิทธิ์เข้าถึง','Scope: your authorized work')} · {t('อ่านล่าสุด','Read at')} {new Date(data.refreshed_at).toLocaleString(lang==='th'?'th-TH':'en-GB')}</p>
  </>}
 </section>
}
