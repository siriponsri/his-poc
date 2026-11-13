"""Create a persisted, inspectable synthetic journey. Never overwrite an existing DB."""
import json, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.his_poc.service import Service
path=Path(sys.argv[1] if len(sys.argv)>1 else 'demo-evidence.sqlite3')
if path.exists(): raise SystemExit('Choose a new DB path; existing evidence is preserved.')
s=Service(path); actor='reviewer-demo'
p=s.propose(actor,'p-demo','e-demo')['proposal']
s.review(actor,p['id'],p['version'],p['action_hash'],'approve')
s.commit(actor,p['id'],p['version'],p['action_hash'],'demo-journey-001')
print(json.dumps(s.context(actor),ensure_ascii=False,indent=2))
