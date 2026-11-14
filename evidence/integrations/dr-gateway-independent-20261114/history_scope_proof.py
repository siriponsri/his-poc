from pathlib import Path
import sys,json
from datetime import timedelta
ROOT=Path('C:/Users/User/Desktop/myProject/his-poc')
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'backend/tests'))
from test_dr_gateway_pg import explicit_seed,login,BASE
from backend.app.common import uid,utcnow
from backend.app.db import SessionLocal
from backend.app.models_dr import DRCapabilityGrant

def test_no_d11_grant_history_cannot_reveal_existence():
    with SessionLocal.begin() as db:
        grant=DRCapabilityGrant(organization_id='org-demo',facility_id='facility-demo',user_id='user-registration',
            capability='dr.report.sign',status='active',valid_from=utcnow()-timedelta(minutes=1),
            valid_until=utcnow()+timedelta(hours=1),verification_status='verified',
            evidence_reference='synthetic-validation:independent-no-d11-history-scope',verifier_id='user-quality',version=1)
        db.add(grant);db.flush();grant_id=grant.id
    client=login('registration')
    existing=client.get(BASE+f'/capability-grants/{grant_id}/history')
    absent=client.get(BASE+f'/capability-grants/{uid()}/history')
    assert existing.status_code==absent.status_code==403,(existing.text,absent.text)
    assert existing.json()==absent.json(),(existing.text,absent.text)
    print(json.dumps({'fixed':'GRANT_HISTORY_PERMISSION_BEFORE_LOOKUP','existing_status':existing.status_code,
        'absent_status':absent.status_code,'same_response':True}))
