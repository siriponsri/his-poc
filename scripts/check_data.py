"""Validate staging data integrity; schema validation needs optional jsonschema. No writes/network."""
from pathlib import Path
import hashlib,json,sys
from generate_fixtures import build
ROOT=Path(__file__).resolve().parents[1]
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
 from jsonschema import Draft202012Validator
 f=ROOT/'data/fixtures/thai_records.json';payload=json.loads(f.read_text())
 schema=json.loads((ROOT/'data/fixtures/thai_records.schema.json').read_text());Draft202012Validator.check_schema(schema);Draft202012Validator(schema).validate(payload)
 assert f.read_bytes()==(json.dumps(build(),ensure_ascii=False,indent=2)+'\n').encode()
 rows=payload['records'];assert len({x['fixture_id'] for x in rows})==len(rows)
 assert all(x['patient_id']!='p-demo' and x['encounter_id']!='e-demo' and not x['contains_real_patient_source_data'] for x in rows)
 manifest=json.loads((ROOT/'data/OPEN_DATA_MANIFEST.json').read_text());asset=next(x for x in manifest['assets'] if x['asset_id']=='ASSET-THAI-RECORDS-001')
 assert asset['sha256']==digest(f)
 assert asset['generator_provenance']['generator_sha256']==digest(ROOT/'scripts/generate_fixtures.py')
 ext=next(x for x in manifest['assets'] if x['source_id']=='SRC-SYNTHEA');assert ext['status']=='NOT_DOWNLOADED' and ext['sha256'] is None and ext['retrieved_at'] is None
 assert not any(x for x in (ROOT/'data/raw').iterdir() if x.name!='README.md')
 index=json.loads((ROOT/'data/fixtures/api_response_index.json').read_text());canonical=ROOT/index['canonical_path'];assert digest(canonical)==index['canonical_sha256'];responses=json.loads(canonical.read_text())['responses'];assert len(responses)==len(index['names'])
 print(json.dumps({'status':'PASS','record_count':len(rows),'record_schema_validated':True,'deterministic_bytes':True,'canonical_api_response_index_count':len(responses),'external_datasets_bundled':0,'backend_import_executed':False}))
if __name__=='__main__':main()
