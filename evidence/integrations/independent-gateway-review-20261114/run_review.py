import sys
from pathlib import Path
from scripts.validate_fullsystem import validation_cases,run_cases
pg=sys.argv[1]
cases=validation_cases(pg,False)
child='import subprocess,sys; [subprocess.run([sys.executable]+args,check=True) for args in [[\'-m\',\'alembic\',\'-c\',\'backend/alembic.ini\',\'upgrade\',\'head\'],[\'-m\',\'backend.app.seed\'],[\'-m\',\'alembic\',\'-c\',\'backend/alembic.ini\',\'check\']]]'
cases.append(('alembic-current-schema-check',[sys.executable,'scripts/test_with_postgres.py','--pg-bin',pg,'--',sys.executable,'-c',child]))
sys.exit(run_cases(cases,Path(sys.argv[2]),pg))
