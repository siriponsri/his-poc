import type {OperationsMap} from './assistant-types'
/** Authored illustration only. Positions are never interpreted as real facilities or people. */
export const hospitalStations=[
 {id:'registration',name:'Registration',x:-5,z:2,color:0xe6eaf0},
 {id:'outpatient',name:'Outpatient',x:0,z:2,color:0xe8edf6},
 {id:'nursing',name:'Nursing',x:5,z:2,color:0xe8eeea},
 {id:'laboratory',name:'Laboratory',x:-5,z:-3,color:0xf0e6e9},
 {id:'records',name:'Records',x:0,z:-3,color:0xe9e9ec},
 {id:'ai_workspace',name:'AI review',x:5,z:-3,color:0xe4eaf5},
] as const
export type HospitalPick={kind:'zone';id:string}|{kind:'agent';index:number}
export function resolveHospitalPick(data:OperationsMap,pick:HospitalPick){if(pick.kind==='zone'){const zone=data.zones.find(item=>item.id===pick.id);return zone?.available?{kind:'zone' as const,zone}:null}const agent=data.agents[pick.index];return agent?.run_id?{kind:'agent' as const,agent}:null}
export function supportsHospitalWebGL(){return typeof window!=='undefined'&&typeof window.WebGL2RenderingContext!=='undefined'}
