from pathlib import Path
import sys,json,hashlib
ROOT=Path('C:/Users/User/Desktop/myProject/his-poc');sys.path.insert(0,str(ROOT))
from backend.tests.test_dr_client_unit import receipt
from backend.app.dr_client import DRClient
from backend.app.dr_protocol import digest

before=hashlib.sha256((ROOT/'backend/app/dr_client.py').read_bytes()).hexdigest()
destination,operation,value=receipt(signed=True)
report=value['snapshot']['report'];witness=report['carebalance_review_witness']
witness['cases'][0].update(confirm_revision=None,grade_review_revision=None,grade_status='NOT_REVIEWED',reviewed_grade=None,quality='UNGRADABLE')
report['carebalance_review_witness_sha256']=digest(witness)
value['snapshot']['report_sha256']=digest(report)
value['snapshot_sha256']=digest(value['snapshot'])
value['review_freshness']['witness_sha256']=value['review_freshness']['current_witness_sha256']=digest(witness)
result=DRClient(destination).validate_report(value,operation)
assert result['review_freshness']['state']=='CURRENT'
assert result['snapshot']['report']['carebalance_review_witness']['cases'][0]['confirm_revision'] is None
out={'observation':'SIGNED_CURRENT_WITHOUT_IMAGE_OR_GRADE_CONFIRMATION_ACCEPTED','method':'Direct sender strict-receipt validator, self-consistent canonical hashes; no service/model call',
     'source_before':before,'source_after':hashlib.sha256((ROOT/'backend/app/dr_client.py').read_bytes()).hexdigest(),
     'grade_status':'NOT_REVIEWED','confirm_revision':None,'grade_review_revision':None,'freshness':'CURRENT'}
Path(__file__).with_suffix('.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out))
