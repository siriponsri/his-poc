"""Actual PostgreSQL backup/restore assertions, designed for disposable cluster wrapper."""
import hashlib,json,os,pathlib,subprocess,sys,unittest,uuid
import psycopg
from backend.app.domains.operations import backup_database,restore_isolated,load_backup,pg_url,table_inventory

@unittest.skipUnless(os.environ.get('HIS_TEST_DATABASE_URL'),'Use scripts/test_with_postgres.py')
class PostgreSQLOperations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.url=os.environ['DATABASE_URL'];cls.files=pathlib.Path(os.environ['FILE_STORAGE_ROOT']);cls.backups=pathlib.Path(os.environ['BACKUP_ROOT']);cls.files.mkdir(parents=True,exist_ok=True)
        subprocess.run([sys.executable,'-m','alembic','-c','backend/alembic.ini','upgrade','head'],check=True)
        subprocess.run([sys.executable,'-m','backend.app.seed'],check=True)
        with psycopg.connect(pg_url(cls.url)) as c:
            c.execute('CREATE TABLE ops_test_files(id text PRIMARY KEY,file_path text NOT NULL,file_sha256 text NOT NULL)')
    def test_01_backup_restore_rows_files_and_foreign_keys(self):
        content=b'SYNTHETIC OPS FILE\n';name=hashlib.sha256(content).hexdigest()+'.bin';(self.files/name).write_bytes(content)
        with psycopg.connect(pg_url(self.url)) as c:c.execute('INSERT INTO ops_test_files VALUES (%s,%s,%s)',('ops-file',name,hashlib.sha256(content).hexdigest()))
        manifest=backup_database(self.url,self.files,self.backups)
        self.assertGreater(len(manifest['tables']),20);self.assertEqual(len(manifest['file_references']),1)
        restored=restore_isolated(self.url,self.backups,manifest['artifact_id'])
        self.assertEqual(restored['status'],'restore_verified');self.assertTrue(restored['isolated_database'].startswith('his_restore_'));self.assertEqual(restored['tables'],manifest['tables']);self.assertEqual(restored['file_count'],1)
        evidence=pathlib.Path('evidence/v0.3/operations');evidence.mkdir(parents=True,exist_ok=True)
        (evidence/'restore-result.json').write_text(json.dumps({'backup_id':manifest['artifact_id'],'postgres_version':manifest['postgres_version'],'dump_sha256':manifest['dump_sha256'],'file_references':manifest['file_references'],'result':restored},indent=2))
    def test_02_missing_referenced_file_fails_backup(self):
        with psycopg.connect(pg_url(self.url)) as c:c.execute('INSERT INTO ops_test_files VALUES (%s,%s,%s)',('missing','missing.bin','0'*64))
        try:
            with self.assertRaisesRegex(RuntimeError,'REFERENCED_FILE_MISSING'):backup_database(self.url,self.files,self.backups)
        finally:
            with psycopg.connect(pg_url(self.url)) as c:c.execute('DELETE FROM ops_test_files WHERE id=%s',('missing',))
    def test_03_tamper_blocks_restore(self):
        manifest=backup_database(self.url,self.files,self.backups);dump=self.backups/manifest['artifact_id']/'database.dump';dump.write_bytes(dump.read_bytes()+b'TAMPER')
        with self.assertRaisesRegex(ValueError,'BACKUP_CHECKSUM_MISMATCH'):restore_isolated(self.url,self.backups,manifest['artifact_id'])
    def test_04_path_traversal_rejected(self):
        with self.assertRaisesRegex(ValueError,'INVALID_BACKUP_ID'):load_backup(self.backups,'../../active')
    def test_05_auditor_cannot_schedule_job(self):
        from fastapi.testclient import TestClient
        from backend.app.main import app
        with TestClient(app) as client:
            login=client.post('/api/v2/auth/login',json={'username':'auditor','password':os.environ['HIS_SEED_PASSWORD']});self.assertEqual(login.status_code,200,login.text)
            resp=client.post('/api/v2/operations/jobs',json={'kind':'backup'},headers={'X-CSRF-Token':login.json()['csrf_token'],'Idempotency-Key':'ops-negative'})
            self.assertEqual(resp.status_code,403,resp.text)
    def test_06_real_job_and_idempotent_replay(self):
        from fastapi.testclient import TestClient
        from backend.app.main import app
        with TestClient(app) as client:
            login=client.post('/api/v2/auth/login',json={'username':'operations_admin','password':os.environ['HIS_SEED_PASSWORD']});self.assertEqual(login.status_code,200,login.text)
            self.assertTrue(client.get('/api/v2/operations/health').json()['can_run_global_operations'])
            headers={'X-CSRF-Token':login.json()['csrf_token'],'Idempotency-Key':'ops-one'}
            response=client.post('/api/v2/operations/jobs',json={'kind':'backup'},headers=headers);self.assertEqual(response.status_code,202,response.text)
            second=client.post('/api/v2/operations/jobs',json={'kind':'backup'},headers=headers);self.assertEqual(second.json()['id'],response.json()['id'])
            jobs=client.get('/api/v2/operations/jobs').json()['items'];self.assertEqual(len(jobs),1);self.assertEqual(jobs[0]['status'],'completed',str(jobs))
            restore=client.post('/api/v2/operations/jobs',json={'kind':'isolated_restore','backup_id':jobs[0]['artifact_id']},headers={**headers,'Idempotency-Key':'ops-restore'});self.assertEqual(restore.status_code,202,restore.text)
            jobs=client.get('/api/v2/operations/jobs').json()['items'];self.assertEqual(jobs[0]['status'],'restore_verified',str(jobs))
            bad=client.post('/api/v2/operations/jobs',json={'kind':'shell','backup_id':'f'*32},headers={**headers,'Idempotency-Key':'ops-invalid'});self.assertEqual(bad.status_code,422)

    def test_07_queued_and_interrupted_job_recovery(self):
        from datetime import timedelta
        from fastapi.testclient import TestClient
        from backend.app.main import app
        from backend.app.db import SessionLocal
        from backend.app.domains.operations import OperationalJob
        from backend.app.common import utcnow
        with SessionLocal.begin() as db:
            db.add(OperationalJob(id='queued-recovery',organization_id='org-demo',facility_id='facility-demo',actor_id='user-operations_admin',command_kind='backup',status='requested',result={}))
            db.add(OperationalJob(id='interrupted-recovery',organization_id='org-demo',facility_id='facility-demo',actor_id='user-operations_admin',command_kind='backup',status='running',started_at=utcnow()-timedelta(minutes=11),result={}))
            db.add(OperationalJob(id='active-recovery',organization_id='org-demo',facility_id='facility-demo',actor_id='user-operations_admin',command_kind='backup',status='running',started_at=utcnow(),result={}))
        with TestClient(app) as client:
            login=client.post('/api/v2/auth/login',json={'username':'operations_admin','password':os.environ['HIS_SEED_PASSWORD']});headers={'X-CSRF-Token':login.json()['csrf_token']}
            recovered=client.post('/api/v2/operations/jobs/queued-recovery/recover',headers=headers);self.assertEqual(recovered.status_code,200,recovered.text)
            interrupted=client.post('/api/v2/operations/jobs/interrupted-recovery/recover',headers=headers);self.assertEqual(interrupted.json()['status'],'failed');self.assertEqual(interrupted.json()['error_code'],'INTERRUPTED_JOB_REQUIRES_NEW_REQUEST')
            active=client.post('/api/v2/operations/jobs/active-recovery/recover',headers=headers);self.assertEqual(active.status_code,409)
            jobs={j['id']:j for j in client.get('/api/v2/operations/jobs').json()['items']};self.assertEqual(jobs['queued-recovery']['status'],'completed')

    def test_08_row_fingerprints_normalize_session_timezone(self):
        with psycopg.connect(pg_url(self.url)) as c:
            c.execute("SET TIME ZONE 'Asia/Bangkok'");first=table_inventory(c)
            c.execute("SET TIME ZONE 'America/New_York'");second=table_inventory(c)
            self.assertEqual(first,second)

    def test_09_worker_rechecks_revoked_permission(self):
        from backend.app.db import SessionLocal
        from backend.app.models import Membership
        from backend.app.domains.operations import OperationalJob,execute_job
        with SessionLocal.begin() as db:
            db.get(Membership,'membership-operations_admin').active=False
            db.add(OperationalJob(id='denied-at-worker',organization_id='org-demo',facility_id='facility-demo',actor_id='user-operations_admin',command_kind='backup',status='requested',result={}))
        try:
            execute_job('denied-at-worker')
            with SessionLocal() as db:
                job=db.get(OperationalJob,'denied-at-worker');self.assertEqual(job.status,'failed');self.assertEqual(job.error_code,'JOB_PERMISSION_REVOKED');self.assertIsNone(job.artifact_id)
        finally:
            with SessionLocal.begin() as db:db.get(Membership,'membership-operations_admin').active=True
    def test_10_scoped_role_cannot_grant_global_backup_access(self):
        from fastapi.testclient import TestClient
        from backend.app.main import app
        from backend.app.db import SessionLocal
        from backend.app.models import Membership
        with SessionLocal.begin() as db:db.add(Membership(id='other-ops-role',user_id='user-other',facility_id='facility-other',role='operations_admin',active=True))
        for username in ['other_registration','system_admin']:
            with TestClient(app) as client:
                login=client.post('/api/v2/auth/login',json={'username':username,'password':os.environ['HIS_SEED_PASSWORD']});self.assertEqual(login.status_code,200,login.text)
                self.assertFalse(client.get('/api/v2/operations/health').json()['can_run_global_operations'])
                response=client.post('/api/v2/operations/jobs',json={'kind':'backup'},headers={'X-CSRF-Token':login.json()['csrf_token'],'Idempotency-Key':'global-denied-'+username})
                self.assertEqual(response.status_code,403,response.text);self.assertEqual(response.json()['detail']['code'],'PLATFORM_OPERATION_NOT_AUTHORIZED')
    def test_11_reader_receives_no_global_file_references(self):
        from fastapi.testclient import TestClient
        from backend.app.main import app
        with TestClient(app) as client:
            login=client.post('/api/v2/auth/login',json={'username':'auditor','password':os.environ['HIS_SEED_PASSWORD']});self.assertEqual(login.status_code,200,login.text)
            jobs=client.get('/api/v2/operations/jobs').json()['items'];self.assertGreater(len(jobs),0)
            for job in jobs:self.assertEqual(set(job['result']),{'status','manifest_access'})

    def test_12_cli_uses_authenticated_backend_and_revokes_sessions(self):
        import socket,time,urllib.request
        from sqlalchemy import select,func
        from backend.app.db import SessionLocal
        from backend.app.models import SessionRecord
        from backend.app.domains.operations import OperationalJob
        with socket.socket() as probe:probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
        server=subprocess.Popen([sys.executable,'-m','uvicorn','backend.app.main:app','--host','127.0.0.1','--port',str(port)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            deadline=time.monotonic()+20
            while time.monotonic()<deadline:
                try:
                    with urllib.request.urlopen(f'http://127.0.0.1:{port}/ready',timeout=1) as r:
                        if r.status==200:break
                except Exception:time.sleep(.1)
            else:self.fail('Local test app readiness timeout')
            with SessionLocal() as db:before=db.scalar(select(func.count()).select_from(SessionRecord).where(SessionRecord.revoked_at.is_(None)))
            environment={**os.environ,'HIS_OPERATOR_USERNAME':'auditor','HIS_OPERATOR_PASSWORD':os.environ['HIS_SEED_PASSWORD'],'DATABASE_URL':'sqlite:///must-not-be-used-by-cli'}
            command=[sys.executable,'scripts/backup.py','--url',f'http://127.0.0.1:{port}','--idempotency-key','cli-backup-one']
            denied=subprocess.run(command,env=environment,capture_output=True,text=True,timeout=30)
            self.assertEqual(denied.returncode,1,denied.stdout);self.assertIn('PERMISSION_DENIED',denied.stderr);self.assertNotIn(environment['HIS_OPERATOR_PASSWORD'],denied.stderr)
            environment['HIS_OPERATOR_USERNAME']='operations_admin'
            allowed=subprocess.run(command,env=environment,capture_output=True,text=True,timeout=30);self.assertEqual(allowed.returncode,0,allowed.stderr)
            result=json.loads(allowed.stdout);self.assertEqual(result['status'],'completed')
            replay=subprocess.run(command,env=environment,capture_output=True,text=True,timeout=30);self.assertEqual(replay.returncode,0,replay.stderr);self.assertEqual(json.loads(replay.stdout)['job_id'],result['job_id'])
            restored=subprocess.run([sys.executable,'scripts/restore.py',result['artifact_id'],'--url',f'http://127.0.0.1:{port}'],env=environment,capture_output=True,text=True,timeout=30)
            self.assertEqual(restored.returncode,0,restored.stderr);self.assertEqual(json.loads(restored.stdout)['status'],'restore_verified')
            with SessionLocal() as db:
                after=db.scalar(select(func.count()).select_from(SessionRecord).where(SessionRecord.revoked_at.is_(None)));self.assertEqual(before,after)
                self.assertEqual(db.get(OperationalJob,result['job_id']).actor_id,'user-operations_admin')
        finally:
            server.terminate();server.wait(timeout=10)
    def test_13_cli_refuses_external_credential_target(self):
        from scripts.operations_client import OperationsClient,OperationsClientError
        with self.assertRaisesRegex(OperationsClientError,'LOOPBACK_APPLICATION_URL_REQUIRED'):OperationsClient('https://external.example')
        with self.assertRaisesRegex(OperationsClientError,'LOOPBACK_APPLICATION_URL_REQUIRED'):OperationsClient('http://secret@127.0.0.1:8000')

if __name__=='__main__':unittest.main()
