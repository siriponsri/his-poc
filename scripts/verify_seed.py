"""Reproducible explicit seed inventory from an empty disposable migrated PostgreSQL."""
import hashlib,json,os,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
assert os.getenv('HIS_TEST_DATABASE_URL'),'Disposable test database required'
from sqlalchemy import select,text
from backend.app.db import engine,SessionLocal
from backend.app import model_registry
from backend.app.models import Patient,Encounter,Task,User,Membership
from backend.app.domains.operations import table_inventory
ROOT=Path(__file__).resolve().parents[1]
subprocess.run([sys.executable,'-m','alembic','-c','backend/alembic.ini','upgrade','head'],check=True)
subprocess.run([sys.executable,'-m','backend.app.seed'],check=True)
from backend.app.domains.operations import pg_url
import psycopg
with psycopg.connect(pg_url(os.environ['DATABASE_URL'])) as conn:before=table_inventory(conn)
subprocess.run([sys.executable,'-m','backend.app.seed'],check=True)
with psycopg.connect(pg_url(os.environ['DATABASE_URL'])) as conn:after=table_inventory(conn)
assert before==after,'Seed changed rows on repeat'
with SessionLocal() as db:
 report={'schema_version':'1.0','status':'PASS','data_class':'AUTHORED_SYNTHETIC','external_data_imported':False,'source':'backend/app/seed.py + domain seed helpers','postgres_version':db.scalar(text('show server_version')),'repeat_seed_unchanged':True,'table_inventory':after,'records':{}}
 for cls,fields in [(Patient,['id','organization_id','facility_id','display_name']),(Encounter,['id','patient_id','status']),(Task,['id','encounter_id','domain','kind','status']),(User,['id','username','status']),(Membership,['id','user_id','facility_id','role','active'])]:
  report['records'][cls.__tablename__]=[{f:getattr(row,f) for f in fields} for row in db.scalars(select(cls).order_by(cls.id))]
 report['generator_sha256']={str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest() for path in [ROOT/'backend/app/seed.py',ROOT/'backend/app/domains/clinical.py',ROOT/'backend/app/domains/erp.py']}
 report['limitations']=['No actual patient data; not a clinical benchmark','Role credentials are local environment inputs; not bundled','Read-only historical18 ThaiUI fixtures remain separate; not counted as PGseed patients','Synthea external artifact NOT_DOWNLOADED/NOT_IMPORTED/NOT_BUNDLED']
 out=ROOT/'data/POSTGRES_SEED_MANIFEST.json';out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'status':'PASS','repeat_unchanged':True,'counts':{k:len(v) for k,v in report['records'].items()}}))
