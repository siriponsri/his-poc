"""D38: real PostgreSQL + file backup and isolated restore, with durable outcomes.

Only two allowlisted job kinds exist. No shell/command/target database supplied by
clients. Backup metadata contains hashes, never credentials or session values.
"""
from __future__ import annotations
import hashlib,json,os,pathlib,re,shutil,subprocess,time,uuid
from datetime import datetime,timezone,timedelta
from urllib.parse import urlsplit,urlunsplit
from psycopg.conninfo import conninfo_to_dict
import psycopg
from psycopg import sql
from fastapi import APIRouter,BackgroundTasks,Depends,HTTPException,Header
from pydantic import BaseModel,ConfigDict,Field
from sqlalchemy import String,DateTime,ForeignKey,Text,select,CheckConstraint,text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped,mapped_column,Session
from backend.app.db import Base,get_db,SessionLocal
from backend.app.auth import current_actor,require_domain,revalidate_actor,permissions_for
from backend.app.models import AuditEvent,User,Membership
from backend.app.common import uid,utcnow,serialize,audit,begin_operation,finish_operation

router=APIRouter(tags=['operations'])

class OperationalJob(Base):
    __tablename__='operational_jobs'
    id:Mapped[str]=mapped_column(String,primary_key=True)
    organization_id:Mapped[str]=mapped_column(ForeignKey('organizations.id'),index=True)
    facility_id:Mapped[str]=mapped_column(ForeignKey('facilities.id'),index=True)
    actor_id:Mapped[str]=mapped_column(ForeignKey('users.id'))
    command_kind:Mapped[str]=mapped_column(String,nullable=False)
    status:Mapped[str]=mapped_column(String,nullable=False,default='requested')
    source_backup_id:Mapped[str|None]=mapped_column(String,nullable=True)
    artifact_id:Mapped[str|None]=mapped_column(String,nullable=True)
    result:Mapped[dict]=mapped_column(JSONB,nullable=False,default=dict)
    error_code:Mapped[str|None]=mapped_column(String,nullable=True)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)
    started_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)
    __table_args__=(CheckConstraint("command_kind IN ('backup','isolated_restore')",name='allowed_command'),CheckConstraint("status IN ('requested','running','completed','failed','restore_verified','restore_failed')",name='allowed_status'))
    finished_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)

class JobRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    kind:str=Field(pattern=r'^(backup|isolated_restore)$')
    backup_id:str|None=Field(default=None,pattern=r'^[a-f0-9]{32}$')


def pg_url(value):
    if not value.startswith(('postgresql://','postgresql+psycopg://')):
        raise ValueError('POSTGRESQL_REQUIRED')
    return value.replace('postgresql+psycopg://','postgresql://',1)

def run_pg(tool,url,args):
    env=dict(os.environ)
    info=conninfo_to_dict(pg_url(url))
    for key,value in info.items():
        variable={'dbname':'PGDATABASE','user':'PGUSER','password':'PGPASSWORD','host':'PGHOST','port':'PGPORT','sslmode':'PGSSLMODE','connect_timeout':'PGCONNECT_TIMEOUT','options':'PGOPTIONS'}.get(key)
        if variable:env[variable]=value
    if tool=='pg_restore':args=['--dbname',info['dbname'],*args]
    # Passing the DSN in env keeps passwords out of command-line logs.
    try:subprocess.run([tool,*args],env=env,check=True,capture_output=True,timeout=120)
    except FileNotFoundError:raise RuntimeError('PG_CLIENT_UNAVAILABLE') from None
    except subprocess.TimeoutExpired:raise RuntimeError('PG_COMMAND_TIMEOUT') from None
    except subprocess.CalledProcessError:raise RuntimeError('PG_COMMAND_FAILED') from None

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()

def table_inventory(conn):
    # Keep fingerprints stable across server locale/timezone defaults.
    conn.execute("SET LOCAL TIME ZONE 'UTC'")
    conn.execute("SET LOCAL DateStyle = 'ISO, YMD'")
    conn.execute("SET LOCAL IntervalStyle = 'iso_8601'")
    tables=conn.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename").fetchall()
    result={}
    for (table,) in tables:
        query=sql.SQL('SELECT row_to_json(t)::text FROM {} t ORDER BY row_to_json(t)::text COLLATE "C"').format(sql.Identifier(table))
        h=hashlib.sha256();count=0
        for (row,) in conn.execute(query):h.update(row.encode());h.update(b'\n');count+=1
        result[table]={'rows':count,'sha256':h.hexdigest()}
    return result

def file_inventory(root):
    out={}
    if not root.exists():return out
    for f in sorted(root.rglob('*')):
        if f.is_symlink():raise RuntimeError('SYMLINK_IN_FILE_STORE')
        if f.is_file():out[f.relative_to(root).as_posix()]={'bytes':f.stat().st_size,'sha256':sha(f)}
    return out

def verify_file_references(conn,inventory):
    """Verify each persisted image reference, including missing-before-backup cases."""
    refs=[]
    names=conn.execute("SELECT table_name FROM information_schema.columns WHERE table_schema='public' AND column_name IN ('file_path','file_sha256') GROUP BY table_name HAVING count(*)=2").fetchall()
    for (table,) in names:
        for row_id,path,expected in conn.execute(sql.SQL('SELECT id,file_path,file_sha256 FROM {} WHERE file_path IS NOT NULL').format(sql.Identifier(table))):
            if pathlib.PurePosixPath(path).is_absolute() or '..' in pathlib.PurePosixPath(path).parts or path not in inventory:
                raise RuntimeError('REFERENCED_FILE_MISSING')
            if not expected or inventory[path]['sha256']!=expected:raise RuntimeError('REFERENCED_FILE_CHECKSUM_MISMATCH')
            refs.append({'table':table,'id':str(row_id),'path':path,'sha256':expected})
    return refs

def backup_database(url,files_root,backups_root):
    artifact=uuid.uuid4().hex; folder=pathlib.Path(backups_root)/artifact
    folder.mkdir(parents=True,mode=0o700,exist_ok=False)
    files_root=pathlib.Path(files_root)
    try:
        before=file_inventory(files_root)
        with psycopg.connect(pg_url(url)) as conn:
            conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
            snapshot=conn.execute('SELECT pg_export_snapshot()').fetchone()[0]
            version=conn.execute('SHOW server_version').fetchone()[0]
            inventory=table_inventory(conn)
            references=verify_file_references(conn,before)
            run_pg('pg_dump',url,['--format=custom','--no-owner','--no-acl','--snapshot='+snapshot,'--file='+str(folder/'database.dump')])
            shutil.copytree(files_root,folder/'files') if files_root.exists() else (folder/'files').mkdir()
            if file_inventory(folder/'files')!=before or file_inventory(files_root)!=before:
                raise RuntimeError('FILE_STORE_CHANGED_DURING_BACKUP')
        manifest={'format':'his-backup-v1','artifact_id':artifact,'created_at':datetime.now(timezone.utc).isoformat(),
            'file_references':references,'postgres_version':version,'dump_sha256':sha(folder/'database.dump'),'tables':inventory,'files':before,
            'consistency':'PostgreSQL exported snapshot; immutable file inventory stable across copy',
            'contains_sensitive_account_data':True}
        (folder/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
        return manifest
    except Exception:
        (folder/'INCOMPLETE').write_text('Backup incomplete; never restore this artifact.');raise

def load_backup(backups_root,artifact):
    if not re.fullmatch('[a-f0-9]{32}',artifact):raise ValueError('INVALID_BACKUP_ID')
    base=pathlib.Path(backups_root).resolve();folder=base/artifact
    if folder.is_symlink() or not folder.is_dir() or (folder/'INCOMPLETE').exists():raise ValueError('BACKUP_UNAVAILABLE')
    manifest=json.loads((folder/'manifest.json').read_text())
    if manifest.get('format')!='his-backup-v1' or manifest.get('artifact_id')!=artifact:raise ValueError('BACKUP_MANIFEST_MISMATCH')
    if sha(folder/'database.dump')!=manifest['dump_sha256'] or file_inventory(folder/'files')!=manifest['files']:
        raise ValueError('BACKUP_CHECKSUM_MISMATCH')
    return folder,manifest

def restore_isolated(url,backups_root,artifact):
    folder,manifest=load_backup(backups_root,artifact)
    source=pg_url(url); parts=urlsplit(source)
    target='his_restore_'+uuid.uuid4().hex
    if parts.path.strip('/')==target:raise ValueError('ACTIVE_DATABASE_RESTORE_FORBIDDEN')
    target_url=urlunsplit((parts.scheme,parts.netloc,'/'+target,parts.query,''))
    target_files=pathlib.Path(backups_root).parent/'restores'/target/'files'
    with psycopg.connect(source,autocommit=True) as conn:
        conn.execute(sql.SQL('CREATE DATABASE {} TEMPLATE template0').format(sql.Identifier(target)))
    try:
        run_pg('pg_restore',target_url,['--no-owner','--no-acl','--exit-on-error',str(folder/'database.dump')])
        shutil.copytree(folder/'files',target_files)
        with psycopg.connect(target_url) as conn:
            actual=table_inventory(conn)
            verify_file_references(conn,file_inventory(target_files))
            invalid=conn.execute("SELECT conname FROM pg_constraint WHERE contype='f' AND NOT convalidated").fetchall()
        if actual!=manifest['tables'] or file_inventory(target_files)!=manifest['files'] or invalid:
            raise RuntimeError('RESTORE_VERIFICATION_MISMATCH')
        result={'status':'restore_verified','isolated_database':target,'file_directory':str(target_files),
            'tables':actual,'file_count':len(manifest['files']),'backup_id':artifact,
            'verified_checks':['table row counts','canonical row hashes','validated foreign keys','file checksums']}
        (target_files.parent/'verification.json').write_text(json.dumps(result,indent=2))
        return result
    except Exception:
        # Retain isolated target for diagnosis; never touch source or automatically drop DBs.
        raise RuntimeError('ISOLATED_RESTORE_FAILED_TARGET_RETAINED') from None

def platform_operator(user_id):
    # This server-only allowlist cannot be granted through application memberships.
    return user_id in {v.strip() for v in os.getenv('HIS_PLATFORM_OPERATORS','').split(',') if v.strip()}

def require_platform(actor):
    if not platform_operator(actor.user_id):raise HTTPException(403,detail={'code':'PLATFORM_OPERATION_NOT_AUTHORIZED','outcome':'not_written'})

def job_dto(job,actor):
    value=serialize(job)
    if not platform_operator(actor.user_id):
        result=value.get('result') or {}
        value['result']={'status':job.status,'manifest_access':'restricted_to_platform_operator'}
    return value

def execute_job(job_id):
    with SessionLocal() as db:
        job=db.get(OperationalJob,job_id)
        if not job:return
        lock=int.from_bytes(hashlib.sha256(('his-authz:'+job.organization_id).encode()).digest()[:8],'big',signed=True)
        db.execute(text('SELECT pg_advisory_xact_lock(:key)'),{'key':lock})
        job=db.get(OperationalJob,job_id,with_for_update=True,populate_existing=True)
        if job.status!='requested':return
        user=db.get(User,job.actor_id,with_for_update=True)
        roles=set(db.scalars(select(Membership.role).where(Membership.user_id==job.actor_id,Membership.facility_id==job.facility_id,Membership.active.is_(True))).all())
        if not user or user.status!='active' or user.organization_id!=job.organization_id or not platform_operator(job.actor_id) or 'D38.write' not in permissions_for(roles):
            job.status='failed' if job.command_kind=='backup' else 'restore_failed';job.error_code='JOB_PERMISSION_REVOKED';job.finished_at=utcnow()
            db.add(AuditEvent(organization_id=job.organization_id,facility_id=job.facility_id,actor_id=job.actor_id,domain='D38',entity_id=job.id,action='job_denied_at_boundary',details={'error_code':job.error_code}));db.commit();return
        job.status='running';job.started_at=utcnow();claimed=job.started_at;kind=job.command_kind;artifact=job.source_backup_id;db.commit()
    try:
        url=os.environ['DATABASE_URL']; files=os.environ.get('FILE_STORAGE_ROOT','./var/files'); backups=os.environ.get('BACKUP_ROOT','./var/backups')
        result=backup_database(url,files,backups) if kind=='backup' else restore_isolated(url,backups,artifact)
        status='completed' if kind=='backup' else 'restore_verified';error=None
    except Exception as exc:
        result={};status='failed' if kind=='backup' else 'restore_failed'
        error=str(exc) if re.fullmatch('[A-Z_]+',str(exc)) else 'OPERATION_FAILED'
    with SessionLocal() as db:
        job=db.get(OperationalJob,job_id,with_for_update=True)
        if job.status!='running' or job.started_at!=claimed:return
        job.result=result;job.status=status;job.error_code=error;job.finished_at=utcnow()
        db.add(AuditEvent(organization_id=job.organization_id,facility_id=job.facility_id,actor_id=job.actor_id,domain='D38',entity_id=job.id,action=status,details={'kind':kind,'error_code':error}))
        if kind=='backup' and not error:job.artifact_id=result['artifact_id']
        db.commit()

@router.get('/operations/jobs')
def jobs(actor=Depends(current_actor),db:Session=Depends(get_db, scope="function")):
    require_domain(actor,'D38')
    rows=db.scalars(select(OperationalJob).where(OperationalJob.organization_id==actor.organization_id,OperationalJob.facility_id==actor.facility_id).order_by(OperationalJob.created_at.desc())).all()
    return {'items':[job_dto(r,actor) for r in rows]}

@router.post('/operations/jobs',status_code=202)
def request_job(body:JobRequest,background:BackgroundTasks,actor=Depends(current_actor),db:Session=Depends(get_db, scope="function"),idempotency_key:str=Header(alias='Idempotency-Key')):
    revalidate_actor(db,actor);require_domain(actor,'D38',write=True);require_platform(actor)
    payload=body.model_dump(); prior=begin_operation(db,actor,idempotency_key,'operations.job',payload)
    if prior is not None:return prior
    if body.kind=='isolated_restore':
        source=db.scalar(select(OperationalJob).where(OperationalJob.organization_id==actor.organization_id,OperationalJob.facility_id==actor.facility_id,OperationalJob.artifact_id==body.backup_id,OperationalJob.status=='completed'))
        if not source:raise HTTPException(404,'Completed backup not found')
    job=OperationalJob(id=uid(),organization_id=actor.organization_id,facility_id=actor.facility_id,actor_id=actor.user_id,command_kind=body.kind,source_backup_id=body.backup_id,status='requested',result={})
    db.add(job);db.flush();response=serialize(job)
    audit(db,actor,'D38',job.id,'job_requested',{'kind':body.kind})
    finish_operation(db,actor,idempotency_key,'operations.job',payload,response)
    db.commit();background.add_task(execute_job,job.id);return response

@router.get('/operations/health')
def health(actor=Depends(current_actor),db:Session=Depends(get_db, scope="function")):
    require_domain(actor,'D38')
    from sqlalchemy import text
    version=db.scalar(text('SHOW server_version'))
    migration=db.scalar(text('SELECT version_num FROM alembic_version'))
    return {'database':'reachable','postgres_version':version,'migration':migration,
        'can_run_global_operations':platform_operator(actor.user_id) and 'D38.write' in actor.permissions,
        'pg_dump_available':shutil.which('pg_dump') is not None,'pg_restore_available':shutil.which('pg_restore') is not None,
        'backup_root_configured':bool(os.environ.get('BACKUP_ROOT')),
        'external_monitoring':'NOT_CONFIGURED','backup_verification':'See actual job results; health is not a restore test'}

@router.post('/operations/jobs/{job_id}/recover')
def recover_job(job_id:str,background:BackgroundTasks,actor=Depends(current_actor),db:Session=Depends(get_db,scope='function')):
    revalidate_actor(db,actor);require_domain(actor,'D38',write=True);require_platform(actor)
    job=db.scalar(select(OperationalJob).where(OperationalJob.id==job_id,OperationalJob.organization_id==actor.organization_id,OperationalJob.facility_id==actor.facility_id).with_for_update())
    if not job:raise HTTPException(404,'Job not found')
    if job.status=='requested':
        audit(db,actor,'D38',job.id,'requested_job_rescheduled');db.commit();background.add_task(execute_job,job.id)
    elif job.status=='running' and job.started_at and job.started_at < utcnow()-timedelta(minutes=10):
        job.status='failed' if job.command_kind=='backup' else 'restore_failed';job.error_code='INTERRUPTED_JOB_REQUIRES_NEW_REQUEST';job.finished_at=utcnow()
        audit(db,actor,'D38',job.id,'interrupted_job_marked_failed');db.commit()
    else:raise HTTPException(409,'Only queued or running-for-over-ten-minutes jobs can be recovered; completed artifacts are retained')
    return serialize(job)
