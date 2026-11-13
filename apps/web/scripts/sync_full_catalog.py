"""Copy the backend-authored, typed UI contracts into the frontend build."""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[3]
web=root/'apps/web'
def fix_fields(fields,domain):
 result=[]
 for field in fields:
  f=dict(field)
  source=f.get('source')
  if source in ['slots','beds','blood-units','medications','admissions','staff','cssd-cycles','therapy-sessions','released-documents','assets','device-assignments'] and domain.startswith('clinical'):f['source']='clinical/catalog/'+source
  if source in ['items','lots']:f['source']=('clinical/catalog/' if domain.startswith('clinical') else 'erp/options/')+source
  if source=='stock-locations':f['source']='erp/options/stock-locations'
  if source=='orders':f['source']='orders';f['order_kind']={'D08':'medication','D09':'medication','D10':'lab','D11':'imaging','D12':'procedure'}.get(domain.split('/')[-1])
  if f['name']=='document_revision_id' and not source:f['source']='document-revisions';f['label']='เอกสารฉบับที่ใช้เป็นหลักฐาน'
  if f['name']=='cssd_cycle_id' and not source:f['source']='clinical/catalog/cssd-cycles';f['label']='ชุดเครื่องมือที่ตรวจปล่อยแล้ว'
  if f['name']=='file_base64':f['type']='file';f['label']='ไฟล์ภาพหรือเอกสารสังเคราะห์ (PNG/TXT ไม่เกิน 1 MB)'
  if f['name']=='file_mime':f['type']='hidden'
  if f['name']=='task_ids':f['type']='multi-select';f['source']='tasks';f['label']='งานค้างที่ส่งต่อ'
  result.append(f)
 return result
registry=json.loads((web/'src/data/full-domains.json').read_text(encoding='utf-8'))
byid={x['id']:{**x,'resources':[]} for x in registry}
clinical=json.loads((root/'backend/app/domains/clinical_catalog.json').read_text(encoding='utf-8'))['items']
for domain in clinical:
 did=domain['id'];byid[did]['resources']=[{'id':did+'-records','label':domain['name_th'],'path':domain['api_path'].lstrip('/'),'patient_context':True,'encounter_context':did not in ['D02','D14','D21'],'fields':fix_fields(domain['fields'],'clinical/'+did),'actions':[{**a,'fields':fix_fields(a.get('fields',[]),'clinical/'+did)} for a in domain['actions']]}]
erp=json.loads((root/'backend/app/domains/erp_catalog.json').read_text(encoding='utf-8'))
labels={'prices':'บัญชีราคา','coverage':'สิทธิการรักษา','charges':'ค่าบริการ','suppliers':'ผู้จำหน่าย','items':'ทะเบียนสินค้า','lots':'ล็อตสินค้า','stock-locations':'คลังสินค้า','staff':'บุคลากร','budgets':'งบประมาณ','reservations':'สำรองคลัง','counts':'ตรวจนับคลัง','report-acknowledgments':'บันทึกหลักฐานตอบรับรายงาน','dataset-access':'สิทธิ์ชุดข้อมูล'}
for domain in erp:
 did=domain['id'];resources=[{'id':did+'-records','label':domain['name_th'],'path':'erp/'+did+'/records','fields':fix_fields(domain['fields'],'erp/'+did),'actions':[{**a,'fields':fix_fields(a.get('fields',[]),'erp/'+did)} for a in domain['actions']]}]
 for sub in domain.get('subresources',[]):resources.append({'id':did+'-'+sub['name'],'label':labels.get(sub['name'],sub['label']),'path':sub['endpoint'].removeprefix('/api/v2/'),'fields':fix_fields(sub['fields'],'erp/'+did),'actions':[{**a,'fields':fix_fields(a.get('fields',[]),'erp/'+did),**({'path':sub['endpoint'].removeprefix('/api/v2/')+'/{id}/'+a['endpoint_suffix']} if a.get('endpoint_suffix') else {})} for a in sub.get('actions',[])]})
 # Support registers expose authorized list/create/action routes, not GET /{id}.
 for resource in resources[1:]:resource['detailPath']=False
 byid[did]['resources']=resources
(web/'src/data/resource-catalog.json').write_text(json.dumps(list(byid.values()),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(f'Synced {len(clinical)} clinical + {len(erp)} ERP domain contracts; core screens authored separately.')
