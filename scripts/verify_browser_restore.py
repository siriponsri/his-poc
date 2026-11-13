"""Read-only verification of a browser-created backup/isolated-restore job.

Run inside the isolated development app with its private DATABASE_URL/BACKUP_ROOT.
No migrations, backup, restore, reset or writes are performed by this verifier.
"""
from __future__ import annotations
import argparse,hashlib,json,os,re,sys
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlsplit,urlunsplit,unquote
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import psycopg
from psycopg import sql
from backend.app.domains.operations import pg_url,load_backup,table_inventory,file_inventory,verify_file_references


def isolated_target_url(source_url,target):
 parts=urlsplit(pg_url(source_url));active=unquote(parts.path.strip('/'))
 if target==active:raise ValueError('ACTIVE_TARGET_FORBIDDEN')
 if not isinstance(target,str) or not re.fullmatch(r'his_restore_[a-f0-9]{32}',target):raise ValueError('ISOLATED_TARGET_REQUIRED')
 return urlunsplit((parts.scheme,parts.netloc,'/'+target,parts.query,''))


def browser_records(report):
 mappings={'J01':{'patient_id':'patients','encounter_id':'encounters','document_id':'documents','result_id':'committed_results'},
           'J05':{'receipt_id':'payment_receipts','invoice_id':'invoices'},
           'J08':{'study_id':'clinical_imaging','document_id':'documents'}}
 if report.get('status')!='PASS':raise ValueError('BROWSER_REPORT_NOT_PASS')
 result=[]
 for journey,fields in mappings.items():
  evidence=report.get('journeys',{}).get(journey,{})
  if evidence.get('status')!='PASS':raise ValueError('BROWSER_JOURNEY_NOT_PASS_'+journey)
  records=evidence.get('record_ids',{})
  for key,table in fields.items():
   identifier=records.get(key)
   if not isinstance(identifier,str) or not identifier.strip():raise ValueError('MISSING_BROWSER_RECORD_'+journey+'_'+key)
   result.append({'journey':journey,'field':key,'table':table,'id':identifier})
 expected=report['journeys']['J08']['record_ids'].get('file_sha256')
 if not isinstance(expected,str) or not re.fullmatch('[a-f0-9]{64}',expected):raise ValueError('MISSING_BROWSER_FILE_SHA256')
 return result,expected


def readonly_connection(url):
 conn=psycopg.connect(pg_url(url),options='-c default_transaction_read_only=on',connect_timeout=10)
 try:
  conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
  conn.execute("SET LOCAL TIME ZONE 'UTC'")
  if conn.execute('SHOW transaction_read_only').fetchone()[0]!='on':raise ValueError('READ_ONLY_TRANSACTION_REQUIRED')
 except Exception:
  conn.close();raise
 return conn


def row_snapshot(conn,table,identifier):
 # Table names come only from the fixed browser_records mapping; ID is parameterized.
 row=conn.execute(sql.SQL('SELECT to_jsonb(t) FROM {} t WHERE id=%s').format(sql.Identifier(table)),(identifier,)).fetchone()
 if row is None:raise ValueError('BROWSER_RECORD_MISSING_'+table)
 return row[0]


def verify(report,restore_job_id,source_url,backups_root):
 records,expected_file_hash=browser_records(report)
 with readonly_connection(source_url) as source:
  row=source.execute('SELECT command_kind,status,source_backup_id,result FROM operational_jobs WHERE id=%s',(restore_job_id,)).fetchone()
  if not row:raise ValueError('RESTORE_JOB_NOT_FOUND')
  kind,status,artifact,result=row
  if kind!='isolated_restore' or status!='restore_verified' or result.get('status')!='restore_verified':raise ValueError('RESTORE_JOB_NOT_VERIFIED')
  if result.get('backup_id')!=artifact:raise ValueError('RESTORE_BACKUP_BINDING_MISMATCH')
  target=result.get('isolated_database');target_url=isolated_target_url(source_url,target)
  if source.execute('SELECT current_database()').fetchone()[0]==target:raise ValueError('ACTIVE_TARGET_FORBIDDEN')
  _,manifest=load_backup(backups_root,artifact)
  expected_files=Path(backups_root).absolute().parent/'restores'/target/'files'
  if expected_files.is_symlink() or any(parent.is_symlink() for parent in expected_files.parents):raise ValueError('RESTORE_FILES_SYMLINK')
  if Path(result.get('file_directory','')).resolve()!=expected_files.resolve():raise ValueError('RESTORE_FILES_PATH_MISMATCH')
  restored_files=file_inventory(expected_files)
  if restored_files!=manifest['files']:raise ValueError('RESTORE_FILE_INVENTORY_MISMATCH')
  with readonly_connection(target_url) as restored:
   if restored.execute('SELECT current_database()').fetchone()[0]!=target:raise ValueError('RESTORE_CONNECTION_TARGET_MISMATCH')
   inventory=table_inventory(restored)
   if inventory!=manifest['tables']:raise ValueError('RESTORED_TABLE_INVENTORY_MISMATCH')
   references=verify_file_references(restored,restored_files)
   if restored.execute("SELECT conname FROM pg_constraint WHERE contype='f' AND NOT convalidated").fetchall():raise ValueError('RESTORED_FOREIGN_KEY_NOT_VALIDATED')
   checked=[]
   for record in records:
    original=row_snapshot(source,record['table'],record['id']);copy=row_snapshot(restored,record['table'],record['id'])
    if original!=copy:raise ValueError('BROWSER_RECORD_RESTORE_MISMATCH_'+record['journey']+'_'+record['field'])
    if record['field']=='study_id':
     if copy.get('file_sha256')!=expected_file_hash:raise ValueError('BROWSER_STUDY_HASH_MISMATCH')
     relative=copy.get('file_path')
     if relative not in restored_files or restored_files[relative]['sha256']!=expected_file_hash:raise ValueError('BROWSER_STUDY_FILE_MISSING_OR_CHANGED')
    checked.append({**record,'status':'PASS','source_restored_row_equal':True})
 return {'status':'PASS','observed_at':datetime.now(timezone.utc).isoformat(),'mode':'READ_ONLY_POSTGRESQL_AND_FILES',
         'restore_job_id':restore_job_id,'backup_id':artifact,'isolated_database':target,
         'table_inventory_equal_backup':True,'tables_checked':len(inventory),'file_inventory_equal_backup':True,
         'files_checked':len(restored_files),'persisted_file_references_checked':len(references),'foreign_keys_validated':True,
         'browser_records':checked,'browser_imaging_file_sha256':expected_file_hash,
         'scope':'Restored snapshot compared to its backup; named stable browser rows compared to source. Current source audit/job changes are not treated as restore differences.'}


def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--journeys-report',required=True,type=Path)
 parser.add_argument('--restore-job-id',required=True)
 args=parser.parse_args()
 try:
  raw=args.journeys_report.read_bytes();report=json.loads(raw.decode('utf-8'))
  result=verify(report,args.restore_job_id,os.environ['DATABASE_URL'],os.environ['BACKUP_ROOT'])
  result['journeys_report_sha256']=hashlib.sha256(raw).hexdigest()
 except Exception as error:
  # Do not print connection errors, file paths or exception text that may contain secrets.
  code=str(error) if isinstance(error,ValueError) and re.fullmatch('[A-Z0-9_]+',str(error)) else type(error).__name__
  print(json.dumps({'status':'FAIL','error_code':code,'restore_job_id':args.restore_job_id}));return 1
 print(json.dumps(result,indent=2));return 0


if __name__=='__main__':sys.exit(main())
