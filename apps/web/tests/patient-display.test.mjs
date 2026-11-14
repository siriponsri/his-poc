import {test} from 'node:test'
import assert from 'node:assert/strict'
import {completedAge,patientReference,patientReferenceText,patientDemographics,patientSexLabel,patientSummary,visitReferenceText} from '../src/lib/patient-display.ts'

const asOf=new Date(2026,10,14,12)
test('completed age uses the exact birthday and a controlled calendar date',()=>{
 assert.equal(completedAge('1981-11-14',asOf),45)
 assert.equal(completedAge('1981-11-15',asOf),44)
 assert.equal(completedAge('1981-11-13',asOf),45)
 assert.equal(completedAge('2026-11-14',asOf),0)
 assert.equal(completedAge('2000-02-29',new Date(2025,1,28,12)),24)
 assert.equal(completedAge('2000-02-29',new Date(2025,2,1,12)),25)
})
test('missing, invalid and future birth dates never fabricate an age',()=>{
 for(const value of [undefined,null,'','not-a-date','1981-02-30','2001-02-29','2026-13-01','0000-01-01','2026-11-15','2027-01-01','1981-11-14T00:00:00Z'])assert.equal(completedAge(value,asOf),null)
 assert.equal(completedAge('1981-01-01',new Date('invalid')),null)
})
test('actual HN and the documented authored-demo issuer retain exact values including zeroes',()=>{
 const patient={id:'patient-001',identifiers:[{issuer:'SYNTHETIC',value:'SYN-001'},{issuer:'CAREBALANCE_DEMO',value:'06901425'}]}
 assert.deepEqual(patientReference(patient,'en'),{label:'HN',value:'06901425',issuer:'CAREBALANCE_DEMO',internal:false})
 assert.equal(patientReferenceText(patient,'th'),'HN 06901425')
 assert.equal(patientReferenceText({...patient,identifiers:[...patient.identifiers,{issuer:'HN',value:'0000123'}]},'en'),'HN 0000123')
})
test('other stored identifiers remain truthful and missing identifiers use an explicitly labelled internal ID',()=>{
 assert.deepEqual(patientReference({id:'patient-001',identifiers:[{issuer:'SYNTHETIC',value:'SYN-001'}]},'en'),{label:'Patient ID',value:'SYN-001',issuer:'SYNTHETIC',internal:false})
 assert.equal(patientReferenceText({id:'patient-001'},'en'),'Record ID patient-001')
 assert.equal(patientReferenceText({id:'patient-001',identifiers:[{issuer:'HN',value:6901425},{issuer:'HN',value:''},null]},'en'),'Record ID patient-001')
 assert.equal(patientReferenceText(undefined,'en'),'')
})
test('localized demographic facts use only provided metadata and preserve patient identity',()=>{
 const patient={id:'patient-001',birth_date:'1981-11-15',sex:'female',identifiers:[{issuer:'CAREBALANCE_DEMO',value:'6901425'}]}
 assert.deepEqual(patientDemographics(patient,'th',asOf),['44 ปี','หญิง'])
 assert.deepEqual(patientDemographics(patient,'en',asOf),['44 years','Female'])
 assert.deepEqual(patientSummary(patient,'en',asOf),['HN 6901425','44 years','Female'])
 assert.equal(patient.id,'patient-001')
 assert.deepEqual(patientDemographics({id:'reference-only'},'en',asOf),[])
 assert.equal(patientSexLabel('unknown','th'),'ไม่ระบุเพศ')
 assert.equal(patientSexLabel('unexpected-code','th'),'')
})
test('visit labels use authorized actual dates or an explicitly labelled ID prefix without inventing a visit number',()=>{
 const id='abcd1234-5678-1234-1234-123456789abc'
 const visit={id,kind:'OPD',created_at:'2026-11-14T12:00:00Z'}
 assert.match(visitReferenceText(visit,'en'),/^OPD · .*2026$/)
 assert.doesNotMatch(visitReferenceText(visit,'en'),/abcd1234/)
 assert.equal(visitReferenceText({id,kind:'OPD'},'en'),'OPD · Visit abcd1234')
 assert.equal(visitReferenceText({id,kind:'OPD',created_at:'invalid'},'en'),'OPD · Visit abcd1234')
 assert.equal(visitReferenceText(undefined,'en','e1'),'Visit e1')
 assert.equal(visit.id,id)
})
