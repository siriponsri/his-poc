"""Copy versioned read-only inputs into bundled frontend assets; never seed runtime DB."""
import csv,json,shutil
from pathlib import Path
app=Path(__file__).resolve().parents[1];root=app.parents[1]
rows=list(csv.DictReader((root/'docs/DOMAIN_SCOPE.csv').open(encoding='utf-8-sig')))
(app/'src/data/domains.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
shutil.copyfile(root/'data/fixtures/thai_records.json',app/'src/data/thai_records.json')
shutil.copyfile(root/'contracts/v1/fixtures/workflow.json',app/'src/data/workflow.json')
print(f'Synced {len(rows)} domain records and read-only fixture assets; no database writes')
