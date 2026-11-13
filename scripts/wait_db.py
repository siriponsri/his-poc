"""Bounded PostgreSQL readiness before migration; no fallback or schema creation."""
import argparse,os,time,sys
from sqlalchemy import create_engine,text
p=argparse.ArgumentParser();p.add_argument('--timeout',type=int,default=60);a=p.parse_args()
url=os.environ.get('DATABASE_URL','')
if not url.startswith('postgresql'):sys.exit('DATABASE_URL must select PostgreSQL')
engine=create_engine(url,connect_args={'connect_timeout':3}); deadline=time.monotonic()+a.timeout
while time.monotonic()<deadline:
    try:
        with engine.connect() as c:
            v=c.scalar(text('SHOW server_version'))
            if not str(v).startswith('18.'):sys.exit('PostgreSQL 18.x is required by this release')
        print('PostgreSQL ready: '+v);break
    except Exception:time.sleep(1)
else:sys.exit('PostgreSQL readiness timeout. Credentials/host details are not printed.')
