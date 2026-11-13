"""Offline package consistency check (stdlib)."""
import csv,json,re
from pathlib import Path
R=Path(__file__).resolve().parents[1]
required=['START_HERE.md','README.md','GOAL.md','PLAN.md','AGENTS.md','docs/ARCHITECTURE.md','docs/DECISIONS.md','docs/DOMAIN_SCOPE.csv','docs/DATA_DICTIONARY.csv','docs/WORKFLOWS.md','docs/OPERATIONS.md','BACKLOG.md','CODEX_HANDOFF.md','INPUT_MANIFEST.md','SOURCE_REGISTER.json','VALIDATION_REPORT.md','.env.example','STARTER_PROMPT_TH.md','apps/web/package.json','apps/web/package-lock.json','apps/web/TEMPLATE_PROVENANCE.json','data/OPEN_DATA_MANIFEST.json','docs/AUDIT_RESOLUTION.md','docs/MIGRATIONS.md']
for f in required:assert (R/f).is_file(),f
rows=list(csv.DictReader((R/'docs/DOMAIN_SCOPE.csv').open(encoding='utf-8-sig')))
assert len(rows)==38
idfield='id' if 'id' in rows[0] else 'domain_id'
assert {r[idfield] for r in rows}=={f'D{i:02d}' for i in range(1,39)}
def own(p):return not any(x in p.parts for x in ('node_modules','dist','vendor','__pycache__'))
for p in R.rglob('*.json'):
 if own(p):json.loads(p.read_text())
c=json.loads((R/'config/runtime.json').read_text());assert c['provider']=='mock' and c['inference_profile']=='mock_demo'
reg=json.loads((R/'config/provider_registry.json').read_text());assert all(not x['enabled'] for x in reg['providers'] if x['id']!='mock')
for p in (R/'contracts/v1').glob('*.schema.json'):
 for ref in re.findall(r'"\$ref"\s*:\s*"([^"]+)"',p.read_text()):
  if not ref.startswith(('https:','#')):assert (p.parent/ref.split('#')[0]).is_file(),ref
for p in R.rglob('*.md'):
 if not own(p):continue
 for dest in re.findall(r'\]\(([^)]+)\)',p.read_text()):
  if not dest.startswith(('http:','https:','#','mailto:')):assert (p.parent/dest.split('#')[0]).exists(),f'{p}: {dest}'
print('PASS: required deliverables, 38 unique domains, JSON parse, schema references, Markdown links, explicit mock + disabled live routes')
# Frontend copies must match their canonical inventories/fixtures.
web=R/'apps/web'
assert json.loads((web/'src/data/workflow.json').read_text()) == json.loads((R/'contracts/v1/fixtures/workflow.json').read_text()), 'stale API response copy'
assert json.loads((web/'src/data/thai_records.json').read_text()) == json.loads((R/'data/fixtures/thai_records.json').read_text()), 'stale record copy'
nav=json.loads((web/'src/data/domains.json').read_text())
assert [(x['id'],x['name_th'],x['status']) for x in nav] == [(x['id'],x['name_th'],x['status']) for x in rows], 'domain navigation drift'
assert json.loads((web/'package.json').read_text())['version']=='0.2.0'
assert json.loads((web/'package-lock.json').read_text())['version']=='0.2.0'
print('PASS: frontend copies match canonical domains and fixtures; package versions 0.2.0')
