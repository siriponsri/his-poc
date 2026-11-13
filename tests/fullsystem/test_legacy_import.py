"""Synthetic archive inspection; PG import tests run separately with DATABASE_URL."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from backend.app.legacy_import import inspect_sqlite, sha
from src.his_poc.service import Service

class LegacyImportInspectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'source.sqlite3'
        self.service = Service(self.path)
        self.proposal = self.service.propose('reviewer-demo', 'p-demo', 'e-demo')['proposal']
        self.service.review('reviewer-demo', self.proposal['id'], 1, self.proposal['action_hash'], 'approve')
        self.result = self.service.commit('reviewer-demo', self.proposal['id'], 1, self.proposal['action_hash'], 'legacy-key-001')['result']
    def tearDown(self): self.temp.cleanup()
    def test_exact_ids_hashes_and_json_strings_survive_without_source_mutation(self):
        old = self.path.read_bytes(); report = inspect_sqlite(self.path)
        self.assertEqual(self.path.read_bytes(), old)
        self.assertEqual(report['source_sha256'], hashlib.sha256(old).hexdigest())
        self.assertEqual(report['gaps'], [])
        p = next(r for r in report['rows'] if r['source_table'] == 'proposals')
        preserved = json.loads(p['source_row_json'])
        self.assertEqual(preserved['id'], self.proposal['id'])
        self.assertEqual(preserved['action_hash'], self.proposal['action_hash'])
        self.assertEqual(preserved['action'], self.proposal['action'])
        self.assertEqual(p['row_sha256'], sha(p['source_row_json']))
        idem = next(r for r in report['rows'] if r['source_table'] == 'idempotency')
        self.assertEqual(idem['legacy_patient_id'], 'p-demo')
        self.assertEqual(json.loads(json.loads(idem['source_row_json'])['result']), self.result)
    def test_overwritten_revision_is_unavailable_not_recreated(self):
        self.service.update_document('reviewer-demo', 'p-demo', 'e-demo', 1, {'text':'NEW text must never become old revision'})
        report = inspect_sqlite(self.path)
        proposal = next(r for r in report['rows'] if r['source_table'] == 'proposals')
        result = next(r for r in report['rows'] if r['source_table'] == 'results')
        self.assertEqual(proposal['status'], 'evidence_unavailable')
        self.assertEqual(result['status'], 'evidence_unavailable')
        self.assertIn('EVIDENCE_REVISION_UNAVAILABLE', proposal['gaps'])
        self.assertEqual(json.loads(proposal['source_row_json'])['snapshot'], self.proposal['snapshot'])
        self.assertNotIn('NEW text', proposal['source_row_json'])
        self.assertEqual(len([r for r in report['rows'] if r['source_table'] == 'documents']), 1)
    def test_invalid_action_hash_is_quarantined_and_original_retained(self):
        with self.service.db() as db: db.execute('UPDATE proposals SET action_hash=?', ('broken-original',))
        report = inspect_sqlite(self.path)
        proposal = next(r for r in report['rows'] if r['source_table'] == 'proposals')
        self.assertEqual(proposal['status'], 'quarantined')
        self.assertIn('ACTION_HASH_MISMATCH', proposal['gaps'])
        self.assertEqual(json.loads(proposal['source_row_json'])['action_hash'], 'broken-original')
    def test_orphan_references_preserved_and_reported(self):
        with self.service.db() as db: db.execute("DELETE FROM patients WHERE id='p-demo'")
        report = inspect_sqlite(self.path)
        proposal = next(r for r in report['rows'] if r['source_table'] == 'proposals')
        self.assertEqual(proposal['legacy_patient_id'], 'p-demo')
        self.assertIn('PATIENT_REFERENCE_MISSING', proposal['gaps'])
        self.assertEqual(report['source_counts']['patients'], 0)
    def test_wal_source_is_rejected_before_read(self):
        Path(str(self.path)+'-wal').write_bytes(b'pending copy')
        with self.assertRaisesRegex(ValueError, 'SOURCE_NOT_CLOSED_COPY'): inspect_sqlite(self.path)
    def test_repeat_inspection_is_identical(self): self.assertEqual(inspect_sqlite(self.path), inspect_sqlite(self.path))


import os
@unittest.skipUnless((os.getenv('HIS_LEGACY_TEST_DATABASE_URL') or os.getenv('HIS_TEST_DATABASE_URL')), 'NOT_RUN: set dedicated HIS_LEGACY_TEST_DATABASE_URL')
class LegacyPostgresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from sqlalchemy import create_engine
        from backend.app.db import Base
        import backend.app.models
        import backend.app.models_legacy
        import backend.app.model_registry
        url=os.environ.get('HIS_LEGACY_TEST_DATABASE_URL') or os.environ['HIS_TEST_DATABASE_URL']
        if not any(url.endswith('/'+name) for name in ('his_legacy_tests','his_test')): raise RuntimeError('DEDICATED_LEGACY_TEST_DATABASE_REQUIRED')
        cls.engine=create_engine(url)
        Base.metadata.create_all(cls.engine)
    @classmethod
    def tearDownClass(cls): cls.engine.dispose()
    def setUp(self):
        from uuid import uuid4
        from datetime import timedelta
        from sqlalchemy.orm import Session
        from backend.app.models import Organization, Facility, Patient, User, Membership, SessionRecord, Role, Permission, RolePermission, CareAssignment
        from backend.app.auth import actor_for, permissions_for
        from backend.app.common import utcnow
        self.db=Session(self.engine)
        suffix=uuid4().hex
        self.org='org-'+suffix;self.fac='fac-'+suffix;self.other='other-'+suffix
        self.db.add(Organization(id=self.org,name='Synthetic legacy tests'));self.db.flush()
        self.db.add_all([Facility(id=self.fac,organization_id=self.org,name='A'),Facility(id=self.other,organization_id=self.org,name='B')]);self.db.flush()
        self.pid='patient-'+suffix
        self.db.add(Patient(id=self.pid,organization_id=self.org,facility_id=self.fac,display_name='Synthetic legacy',status='active'))
        self.user=User(id='user-'+suffix,organization_id=self.org,username='legacy-'+suffix,display_name='Synthetic reviewer',password_hash='unused-test-account')
        self.db.add(self.user);self.db.flush()
        for role in ('system_admin','clinician'):
            if not self.db.get(Role,role): self.db.add(Role(id=role,label=role)); self.db.flush()
            for permission in permissions_for({role}):
                if not self.db.get(Permission,permission): self.db.add(Permission(id=permission)); self.db.flush()
                if not self.db.get(RolePermission,(role,permission)): self.db.add(RolePermission(role_id=role,permission_id=permission))
        self.db.add(CareAssignment(user_id=self.user.id,patient_id=self.pid))
        self.db.flush()
        self.db.add_all([Membership(user_id=self.user.id,facility_id=self.fac,role='system_admin'),Membership(user_id=self.user.id,facility_id=self.fac,role='clinician'),Membership(user_id=self.user.id,facility_id=self.other,role='clinician')])
        self.session=SessionRecord(id='session-'+suffix,user_id=self.user.id,facility_id=self.fac,token_hash=suffix*2,csrf_hash=suffix*2,csrf_token='test-only',expires_at=utcnow()+timedelta(hours=1))
        self.db.add(self.session);self.db.flush();self.actor=actor_for(self.db,self.user,self.session)
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'source.sqlite3'
        service=Service(self.path);p=service.propose('reviewer-demo','p-demo','e-demo')['proposal']
        service.review('reviewer-demo',p['id'],1,p['action_hash'],'approve')
        service.commit('reviewer-demo',p['id'],1,p['action_hash'],'test-legacy-key')
        service.update_document('reviewer-demo','p-demo','e-demo',1,{'text':'Current revision after committed legacy result'})
        self.report=inspect_sqlite(self.path)
    def tearDown(self):self.db.rollback();self.db.close();self.temp.cleanup()
    def test_archive_persistence_replay_and_missing_revision_survive_reconnect(self):
        from sqlalchemy import select, func
        from backend.app.models_legacy import LegacyImport, LegacyRow
        from backend.app.legacy_import import persist_archive
        first=persist_archive(self.db,self.actor,self.report,{'p-demo':self.pid})
        second=persist_archive(self.db,self.actor,self.report,{'p-demo':self.pid})
        self.assertFalse(first['replayed']);self.assertTrue(second['replayed'])
        self.assertEqual(first['import_id'],second['import_id'])
        self.db.commit();self.db.close()
        from sqlalchemy.orm import Session
        self.db=Session(self.engine)
        records=list(self.db.scalars(select(LegacyRow).where(LegacyRow.import_id==first['import_id'])))
        self.assertEqual(len(records),sum(self.report['source_counts'].values()))
        result=next(r for r in records if r.source_table=='results')
        self.assertEqual(result.status,'evidence_unavailable')
        self.assertEqual(result.mapped_patient_id,self.pid)
        self.assertIn('EVIDENCE_REVISION_UNAVAILABLE',json.loads(result.gap_json))
        self.assertEqual(self.db.scalar(select(func.count()).select_from(LegacyImport).where(LegacyImport.id==first['import_id'])),1)
    def test_archive_read_is_scoped_and_commit_always_denied(self):
        from fastapi import HTTPException
        from backend.app.legacy_import import persist_archive,make_router
        from backend.app.auth import actor_for
        persist_archive(self.db,self.actor,self.report,{'p-demo':self.pid})
        router=make_router();read=next(r.endpoint for r in router.routes if r.path=='/legacy/results')
        commit=next(r.endpoint for r in router.routes if r.path.endswith('/commit'))
        from dataclasses import replace
        metadata_only=replace(self.actor,permissions=self.actor.permissions-{'documents.content'})
        with self.assertRaises(HTTPException) as raised:read(self.pid,self.db,metadata_only)
        self.assertEqual(raised.exception.status_code,403)
        records=read(self.pid,self.db,self.actor)['items'];self.assertEqual(len(records),1)
        with self.assertRaises(HTTPException) as raised:commit(records[0]['id'],self.db,self.actor)
        self.assertEqual(raised.exception.status_code,409)
        self.session.facility_id=self.other;self.db.flush();other=actor_for(self.db,self.user,self.session)
        with self.assertRaises(HTTPException) as raised:read(self.pid,self.db,other)
        self.assertEqual(raised.exception.status_code,404)
    def test_replay_different_mapping_and_revoked_permission_rejected(self):
        from fastapi import HTTPException
        from sqlalchemy import select
        from backend.app.models import Membership
        from backend.app.legacy_import import persist_archive
        persist_archive(self.db,self.actor,self.report,{'p-demo':self.pid})
        with self.assertRaises(HTTPException) as raised:persist_archive(self.db,self.actor,self.report,{})
        self.assertEqual(raised.exception.status_code,409)
        member=self.db.scalar(select(Membership).where(Membership.user_id==self.user.id,Membership.role=='system_admin'));member.active=False;self.db.flush()
        with self.assertRaises(HTTPException) as raised:persist_archive(self.db,self.actor,self.report,{'p-demo':self.pid})
        self.assertEqual(raised.exception.status_code,403)

    def test_cli_apply_verifies_password_archives_and_revokes_operator_session(self):
        import subprocess, sys
        from sqlalchemy import select,func
        from backend.app.auth import password_hasher
        from backend.app.models import SessionRecord
        from backend.app.models_legacy import LegacyImport
        password='Synthetic-Import-Test-Only-2026!'
        self.user.password_hash=password_hasher.hash(password)
        username=self.user.username;session_id=self.session.id;uid=self.user.id
        self.db.commit()
        mapping=Path(self.temp.name)/'mapping.json';mapping.write_text(json.dumps({'p-demo':self.pid}))
        report=Path(self.temp.name)/'report.json'
        env=dict(os.environ,HIS_IMPORT_PASSWORD=password,DATABASE_URL=self.engine.url.render_as_string(hide_password=False))
        command=[sys.executable,'scripts/import_legacy.py',str(self.path),'--report',str(report),'--mapping',str(mapping),'--apply','--username',username,'--facility-id',self.fac]
        result=subprocess.run(command,env=env,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        result_report=json.loads(report.read_text())
        self.assertFalse(result_report['postgresql_import']['replayed'])
        self.assertNotIn(password,result.stdout+result.stderr+report.read_text())
        self.db.expire_all()
        self.assertEqual(self.db.scalar(select(func.count()).select_from(LegacyImport).where(LegacyImport.organization_id==self.org)),1)
        sessions=list(self.db.scalars(select(SessionRecord).where(SessionRecord.user_id==uid,SessionRecord.id!=session_id)))
        self.assertEqual(len(sessions),1);self.assertIsNotNone(sessions[0].revoked_at)

if __name__ == "__main__": unittest.main()
