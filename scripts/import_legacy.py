#!/usr/bin/env python3
"""Inspect a stopped legacy SQLite COPY; explicitly archive it in PostgreSQL.

Default is inspect-only. --apply requires a real local operations/admin account,
password and explicit facility. No old proposal is made executable by this tool.
"""
from pathlib import Path
import argparse
import getpass
import json
import os
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.app.legacy_import import inspect_sqlite, persist_archive

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--mapping', type=Path, help='JSON object: legacy patient ID -> current patient ID; explicit only')
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--username')
    parser.add_argument('--facility-id')
    args=parser.parse_args()
    report=inspect_sqlite(args.source)
    mapping=json.loads(args.mapping.read_text()) if args.mapping else {}
    if not isinstance(mapping,dict) or any(not isinstance(k,str) or not isinstance(v,str) for k,v in mapping.items()):
        parser.error('mapping must be an object of string IDs')
    result={'inspection':{k:v for k,v in report.items() if k!='rows'},'postgresql_import':'NOT_RUN'}
    if args.apply:
        if not args.username or not args.facility_id:parser.error('--apply needs --username and --facility-id')
        if not os.getenv('DATABASE_URL'):parser.error('--apply needs explicit PostgreSQL DATABASE_URL')
        from datetime import timedelta
        import secrets
        from sqlalchemy import select
        from backend.app.db import SessionLocal
        from backend.app.auth import password_hasher, actor_for
        from backend.app.common import text_hash, utcnow
        from backend.app.models import User, SessionRecord
        import backend.app.models_legacy
        password=os.getenv('HIS_IMPORT_PASSWORD') or getpass.getpass('Local account password: ')
        with SessionLocal.begin() as db:
            user=db.scalar(select(User).where(User.username==args.username).with_for_update())
            if not user or user.status!='active':raise RuntimeError('INVALID_CREDENTIALS')
            try:password_hasher.verify(user.password_hash,password)
            except Exception:raise RuntimeError('INVALID_CREDENTIALS') from None
            token=secrets.token_urlsafe(32);csrf=secrets.token_urlsafe(32)
            session=SessionRecord(user_id=user.id,facility_id=args.facility_id,token_hash=text_hash(token),csrf_hash=text_hash(csrf),csrf_token=csrf,expires_at=utcnow()+timedelta(minutes=5))
            db.add(session);db.flush()
            actor=actor_for(db,user,session)
            result['postgresql_import']=persist_archive(db,actor,report,mapping)
            session.revoked_at=utcnow()
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'report':str(args.report),'source_sha256':report['source_sha256'],'source_rows':sum(report['source_counts'].values()),'gaps':len(report['gaps']),'applied':args.apply}))
if __name__=='__main__':main()
