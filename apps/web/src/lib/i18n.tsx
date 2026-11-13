// Display-language preference only. Permissions, scope and data never depend on it.
import {createContext,useContext,useEffect,useState,type ReactNode} from 'react'
export type Lang='th'|'en'
const KEY='his-display-language'
function stored():Lang{try{return globalThis.localStorage?.getItem(KEY)==='en'?'en':'th'}catch{return 'th'}}
const LangContext=createContext<{lang:Lang;setLang:(lang:Lang)=>void}>({lang:'th',setLang:()=>{}})
export function LangProvider({children}:{children:ReactNode}){
 const [lang,setLang]=useState<Lang>(stored)
 useEffect(()=>{try{globalThis.localStorage?.setItem(KEY,lang)}catch{/* preference stays in memory */}document.documentElement.lang=lang},[lang])
 return <LangContext value={{lang,setLang}}>{children}</LangContext>
}
/** `t(thai, english)` keeps both wordings beside the control they describe. */
export function useLang(){const {lang,setLang}=useContext(LangContext);return {lang,setLang,t:(th:string,en:string)=>lang==='en'?en:th}}

export const groupOrder=['patient_access','clinical_care','diagnostics_and_treatment','coordination_and_records','revenue_and_finance','enterprise_operations','governance_and_platform']
export const groupNames:Record<string,[string,string]>={
 patient_access:['ทะเบียนและการเข้าถึง','Registration & access'],
 clinical_care:['การดูแลผู้ป่วย','Clinical care'],
 diagnostics_and_treatment:['ตรวจวินิจฉัยและการรักษา','Diagnostics & treatment'],
 coordination_and_records:['ประสานงานและเวชระเบียน','Coordination & records'],
 revenue_and_finance:['รายได้และการเงิน','Revenue & finance'],
 enterprise_operations:['งานสนับสนุนองค์กร','Enterprise operations'],
 governance_and_platform:['กำกับดูแลและแพลตฟอร์ม','Governance & platform'],
}
export const domainNamesEn:Record<string,string>={
 D01:'Patient registration & identity',D02:'Appointments, queues & capacity',D03:'Outpatient & visit records',D04:'Emergency department',
 D05:'Inpatient, beds & discharge',D06:'Nursing & shift handover',D07:'Clinical orders',D08:'Pharmacy & dispensing',
 D09:'Medication administration',D10:'Laboratory & critical results',D11:'Radiology, RIS & imaging',D12:'Operating room & anesthesia',
 D13:'ICU & device data',D14:'Obstetrics, maternal & newborn',D15:'Pediatrics & growth',D16:'Rehabilitation & physiotherapy',
 D17:'Dental & specialty clinics',D18:'Blood bank & transfusion',D19:'Nutrition & patient meals',D20:'Referrals & follow-up',
 D21:'Patient portal & access',D22:'Medical records, documents & attestation',D23:'Charges, prices & coverage',
 D24:'Claims, receivables & remittance',D25:'Accounting, payments & refunds',D26:'Service costing, budget & resource analysis',
 D27:'Procurement, contracts, receiving & payables',D28:'Drug & supply inventory',D29:'Assets & biomedical engineering',
 D30:'Staff, rosters & competencies',D31:'CSSD, laundry, facilities & support',D32:'Quality, risk & infection control',
 D33:'Public health reporting & network data',D34:'User identity, permissions & access audit',
 D35:'Integration, terminology & exchange quality',D36:'Analytics, research data & secondary use',
 D37:'AI & decision support',D38:'Operations, continuity & recovery',
}
export const statusNamesEn:Record<string,string>={draft:'Draft',pending:'Awaiting review',verified:'Verified',active:'Active',inactive:'Inactive',open:'Open',in_progress:'In progress',completed:'Completed',cancelled:'Cancelled',requested:'Requested',booked:'Booked',checked_in:'Checked in',called:'Called',waiting:'Waiting',in_consult:'In consultation',reviewed:'Reviewed',closed:'Closed',approved:'Approved',rejected:'Rejected',committed:'Result recorded',posted:'Posted',released:'Released',attested:'Attested',returned:'Returned',in_review:'In review',amended:'Amended',failed:'Failed',timeout:'Timed out',abstained:'Abstained',success:'Succeeded',requested_restore:'Restore requested',restore_verified:'Restore verified'}
