import type {Row} from './client'

type PatientIdentifier={issuer:string;value:string}

/** Only explicit hospital/demo registration issuers are labelled HN. Values are never invented. */
export function patientReference(patient:Row|undefined,lang:string='th'):{label:string;value:string;issuer:string|null;internal:boolean}{
 const identifiers=(Array.isArray(patient?.identifiers)?patient.identifiers:[]).filter((entry):entry is PatientIdentifier=>!!entry&&typeof entry==='object'&&typeof entry.issuer==='string'&&!!entry.issuer.trim()&&typeof entry.value==='string'&&!!entry.value.trim())
 const knownHN=(entry:PatientIdentifier)=>['HN','CAREBALANCE_DEMO'].includes(entry.issuer.toUpperCase())
 const selected=identifiers.find(entry=>entry.issuer.toUpperCase()==='HN')||identifiers.find(knownHN)||identifiers[0]
 if(selected)return {label:knownHN(selected)?'HN':lang==='en'?'Patient ID':'เลขประจำตัว',value:selected.value,issuer:selected.issuer,internal:false}
 return {label:lang==='en'?'Record ID':'รหัสแฟ้ม',value:typeof patient?.id==='string'?patient.id:'',issuer:null,internal:true}
}

export function patientReferenceText(patient:Row|undefined,lang:string='th'){
 const reference=patientReference(patient,lang)
 return reference.value?reference.label+' '+reference.value:''
}

/** Completed calendar years, using date-only storage and local as-of calendar fields. */
export function completedAge(birthDate:unknown,asOf:Date=new Date()):number|null{
 if(typeof birthDate!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(birthDate)||!Number.isFinite(asOf.getTime()))return null
 const [year,month,day]=birthDate.split('-').map(Number)
 if(year<1||month<1||month>12||day<1||day>31)return null
 const parsed=new Date(0);parsed.setUTCFullYear(year,month-1,day)
 if(parsed.getUTCFullYear()!==year||parsed.getUTCMonth()!==month-1||parsed.getUTCDate()!==day)return null
 const currentYear=asOf.getFullYear(),currentMonth=asOf.getMonth()+1,currentDay=asOf.getDate()
 const age=currentYear-year-(currentMonth<month||currentMonth===month&&currentDay<day?1:0)
 return age>=0?age:null
}

export function patientSexLabel(sex:unknown,lang:string='th'){
 const labels:Record<string,[string,string]>={female:['หญิง','Female'],male:['ชาย','Male'],other:['อื่น ๆ','Other'],unknown:['ไม่ระบุเพศ','Sex not recorded']}
 return typeof sex==='string'&&Object.hasOwn(labels,sex)?labels[sex][lang==='en'?1:0]:''
}

export function patientDemographics(patient:Row|undefined,lang:string='th',asOf:Date=new Date()){
 if(!patient)return []
 const age=completedAge(patient.birth_date,asOf)
 return [age===null?'':String(age)+(lang==='en'?' years':' ปี'),patientSexLabel(patient.sex,lang)].filter(Boolean)
}

export function patientSummary(patient:Row|undefined,lang:string='th',asOf:Date=new Date()){
 return [patientReferenceText(patient,lang),...patientDemographics(patient,lang,asOf)].filter(Boolean)
}

/** Use actual visit metadata; a shortened record ID is only a labelled display fallback. */
export function visitReferenceText(visit:Row|undefined,lang:string='th',fallbackId:unknown=visit?.id){
 const created=typeof visit?.created_at==='string'&&/^\d{4}-\d{2}-\d{2}T/.test(visit.created_at)?new Date(visit.created_at):null
 const id=typeof fallbackId==='string'?fallbackId:''
 const reference=created&&Number.isFinite(created.getTime())?created.toLocaleDateString(lang==='en'?'en-GB':'th-TH',{dateStyle:'medium'}):id?(lang==='en'?'Visit ':'การรับบริการ ')+(/^[0-9a-f]{8}-[0-9a-f]{4}-/i.test(id)?id.slice(0,8):id):''
 return [typeof visit?.kind==='string'?visit.kind:'',reference].filter(Boolean).join(' · ')
}
