"""Run an existing suite against a migrated disposable PostgreSQL schema.
Use through scripts/test_with_postgres.py. Does not seed: suite owns explicit seed.
"""
import os,subprocess,sys
assert os.getenv('HIS_TEST_DATABASE_URL'),'Disposable PostgreSQL test wrapper required'
subprocess.run([sys.executable,'-m','alembic','-c','backend/alembic.ini','upgrade','head'],check=True)
subprocess.run([sys.executable,'-m','pytest',*sys.argv[1:]],check=True)
