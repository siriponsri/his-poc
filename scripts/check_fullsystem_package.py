"""Consistency checks, not domain/clinical/browser acceptance."""
from pathlib import Path
import json,sys,csv
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
ROOT=Path(__file__).resolve().parents[1]
from backend.app.main import app
from backend.app.domains.clinical import SPECS
from backend.app.domains.erp import MODELS
required=['START_HERE.md','README.md','GOAL.md','PLAN.md','AGENTS.md','BACKLOG.md','CODEX_HANDOFF.md','STARTER_PROMPT_TH.md','INPUT_MANIFEST.md','SOURCE_REGISTER.json','VALIDATION_REPORT.md','DOMAIN_COVERAGE.json','DOMAIN_COVERAGE.md','JOURNEY_COVERAGE.md','docs/ARCHITECTURE.md','docs/DECISIONS.md','docs/DATA_DICTIONARY.csv','docs/WORKFLOWS.md','docs/OPERATIONS.md','compose.yaml','.env.example','requirements-backend.txt','apps/web/package-lock.json','contracts/v2/openapi.json','contracts/v2/clinical-inputs.json','contracts/v2/erp-inputs.json','backend/alembic.ini','backend/app/seed.py','scripts/run.ps1']
failures=[]
for name in required:
 if not (ROOT/name).is_file():failures.append('missing '+name)
expected={f'D{i:02}' for i in range(1,39)}
implemented_routes=set(SPECS)|set(MODELS)|{'D01','D03','D07','D22','D34','D37','D38'}
if expected!=implemented_routes:failures.append('domain route inventory mismatch')
paths=set(app.openapi()['paths'])
for name in ['/api/v2/auth/login','/api/v2/auth/me','/api/v2/patients','/api/v2/encounters','/api/v2/tasks','/api/v2/documents','/api/v2/proposals','/ready']:
 if name not in paths:failures.append('missing runtime route '+name)
if any(x.startswith('/api/v1') for x in paths):failures.append('legacy API mounted in default app')
coverage=ROOT/'DOMAIN_COVERAGE.json'
if coverage.exists():
 rows=json.loads(coverage.read_text(encoding='utf-8'))['domains']
 if {x['id'] for x in rows}!=expected or len(rows)!=38:failures.append('coverage must contain38 unique IDs')
 for row in rows:
  for key in ['implementation_status','verified_level','verification_status','external_integration_status','limitations','evidence']:
   if key not in row:failures.append(row['id']+' missing '+key)
  if row['verified_level'] in ('L2','L3','L4') and not row['evidence']:failures.append(row['id']+' verified without evidence')
  for path in row.get('evidence',[]):
   if not (ROOT/path).exists():failures.append(row['id']+' missing evidence '+path)
# JSON syntax only, exclude dependencies/generated caches/history raw test traces.
for directory in ['config','contracts/v2','data']:
 for file in (ROOT/directory).rglob('*.json'):
  try:json.loads(file.read_text(encoding='utf-8'))
  except Exception as e:failures.append(str(file.relative_to(ROOT))+': '+str(e))
routing=json.loads((ROOT/'config/routing_policy.json').read_text(encoding='utf-8'))
if routing.get('cloud_fallback_enabled') or routing.get('live_to_mock_fallback_enabled'):failures.append('fallback policy must remain disabled')
# Current controlling docs must not carry old restrictive task directions.
for filename in ['GOAL.md','PLAN.md','AGENTS.md','BACKLOG.md','CODEX_HANDOFF.md','STARTER_PROMPT_TH.md']:
 content=(ROOT/filename).read_text(encoding='utf-8') if (ROOT/filename).exists() else ''
 for forbidden in ['runtime API ยังคง p-demo/e-demo/task-demo ชุดเดียว','ห้ามเพิ่ม patient seed','Runtime remains singleton','ไม่ปรับ data class']:
  if forbidden in content:failures.append('superseded instruction '+filename+': '+forbidden)
result={'check':'static_package_consistency_not_acceptance','status':'FAIL' if failures else 'PASS','domain_route_inventory':len(implemented_routes),'failures':failures}
print(json.dumps(result,ensure_ascii=False,indent=2));sys.exit(bool(failures))
