"""Forensic import of a closed v0.1/v0.2 SQLite copy into read-only PG evidence.

No current record is changed, no missing text is reconstructed, no old approval
is promoted into a v2 approval. SQL strings stored in rows remain inert text.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sqlite3
from urllib.parse import quote

TABLES = ('patients', 'encounters', 'users', 'documents', 'tasks', 'proposals',
          'proposal_versions', 'reviews', 'results', 'idempotency', 'runs', 'audit')


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def sha(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def parse_json(value):
    try:
        return json.loads(value)
    except (ValueError, TypeError):
        return None


def inspect_sqlite(source: str | Path) -> dict:
    """Read a stable source copy without running the old application or migrations."""
    source = Path(source).resolve(strict=True)
    if source.suffix.lower() not in {'.sqlite', '.sqlite3', '.db'}:
        raise ValueError('SOURCE_MUST_BE_SQLITE_FILE')
    if any(Path(str(source) + suffix).exists() and Path(str(source) + suffix).stat().st_size
           for suffix in ('-wal', '-journal')):
        raise ValueError('SOURCE_NOT_CLOSED_COPY: checkpoint/backup the source first')
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    conn = sqlite3.connect('file:' + quote(str(source)) + '?mode=ro', uri=True)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute('PRAGMA trusted_schema=OFF')
        conn.execute('PRAGMA query_only=ON')
        conn.execute('BEGIN')
        integrity = conn.execute('PRAGMA integrity_check').fetchone()[0]
        if integrity != 'ok':
            raise ValueError('SOURCE_INTEGRITY_FAILURE')
        schema = [dict(r) for r in conn.execute("SELECT name,sql FROM sqlite_master WHERE type='table' ORDER BY name")]
        available = {r['name'] for r in schema}
        missing = sorted(set(TABLES) - available)
        if missing:
            raise ValueError('MISSING_SOURCE_TABLES:' + ','.join(missing))
        # Fixed allowlist only. Table/column names never derive from caller input.
        rows = {table: [dict(r) for r in conn.execute('SELECT * FROM "' + table + '"')]
                for table in TABLES}
    finally:
        conn.close()
    after = hashlib.sha256(source.read_bytes()).hexdigest()
    if before != after:
        raise ValueError('SOURCE_CHANGED_DURING_READ')
    by_id = {t: {r.get('id'): r for r in records if 'id' in r} for t, records in rows.items()}
    patients = by_id['patients']
    encounters = by_id['encounters']
    proposals = by_id['proposals']
    docs = by_id['documents']
    results = by_id['results']
    archive = []
    gaps = []
    for table in TABLES:
        for row in rows[table]:
            identity = str(row.get('id', row.get('key', '')))
            if table == 'proposal_versions':
                identity = canonical([row.get('proposal'), row.get('version')])
            local_gaps = []
            proposal = proposals.get(row.get('proposal')) if table in ('proposal_versions', 'reviews', 'results') else row if table == 'proposals' else None
            encounter = encounters.get(row.get('encounter') or (proposal or {}).get('encounter'))
            patient_id = row.get('patient') or (proposal or {}).get('patient') or (encounter or {}).get('patient')
            if table == 'patients': patient_id = row['id']
            if table == 'idempotency':
                prior_payload = parse_json(row.get('result'))
                prior = results.get(prior_payload.get('id')) if isinstance(prior_payload, dict) else None
                patient_id = (prior or {}).get('patient')
                if not prior: local_gaps.append('RESULT_REFERENCE_MISSING')
            if table == 'audit':
                target = row.get('entity')
                related = proposals.get(target)
                patient_id = (related or {}).get('patient') or encounters.get(target, {}).get('patient')
            if table in ('reviews', 'proposal_versions', 'results') and not proposal:
                local_gaps.append('PROPOSAL_REFERENCE_MISSING')
            if patient_id and patient_id not in patients:
                local_gaps.append('PATIENT_REFERENCE_MISSING')
            if row.get('encounter') and not encounter:
                local_gaps.append('ENCOUNTER_REFERENCE_MISSING')
            if table in ('proposals', 'proposal_versions'):
                action = parse_json(row.get('action'))
                if action is None or sha(canonical(action)) != row.get('action_hash'):
                    local_gaps.append('ACTION_HASH_MISMATCH')
            if proposal is not None:
                snapshot = parse_json(proposal.get('snapshot'))
                if not isinstance(snapshot, dict):
                    local_gaps.append('EVIDENCE_SNAPSHOT_INVALID')
                else:
                    document = docs.get(snapshot.get('document_id'))
                    content = parse_json((document or {}).get('content'))
                    if not document or content is None or document.get('version') != snapshot.get('document_version') or sha(canonical(content)) != snapshot.get('document_hash'):
                        local_gaps.append('EVIDENCE_REVISION_UNAVAILABLE')
                    elif document.get('encounter') != proposal.get('encounter'):
                        local_gaps.append('EVIDENCE_CONTEXT_MISMATCH')
            raw = canonical(row)
            status = 'evidence_unavailable' if 'EVIDENCE_REVISION_UNAVAILABLE' in local_gaps else 'quarantined' if local_gaps else 'read_only'
            entry = dict(source_table=table, legacy_id=identity, legacy_patient_id=patient_id,
                         source_row_json=raw, row_sha256=sha(raw), status=status, gaps=local_gaps)
            archive.append(entry)
            if local_gaps:
                gaps.append({k: entry[k] for k in ('source_table', 'legacy_id', 'gaps')})
    return {'format': 'his-legacy-evidence/1', 'source_sha256': before, 'source_name': source.name,
            'source_counts': {t: len(rows[t]) for t in TABLES}, 'source_schema': schema,
            'unimported_tables': sorted(available-set(TABLES)), 'rows': archive,
            'gaps': gaps, 'policy': 'READ_ONLY_ARCHIVE_NO_NEW_COMMITS',
            'canonicalization': 'v1-json-utf8-sorted-compact; original JSON-string columns preserved verbatim'}


def persist_archive(db, actor, report: dict, patient_mapping: dict[str, str]):
    from sqlalchemy import select, text
    from fastapi import HTTPException
    from .auth import require_domain, scoped_patient, revalidate_actor
    from .models_legacy import LegacyImport, LegacyRow
    from .common import audit
    revalidate_actor(db, actor)
    require_domain(actor, 'D38', write=True)
    for legacy_id, patient_id in patient_mapping.items():
        scoped_patient(db, actor, patient_id)
        if legacy_id not in {r['legacy_id'] for r in report['rows'] if r['source_table'] == 'patients'}:
            raise HTTPException(422, 'UNKNOWN_LEGACY_PATIENT_MAPPING')
    mapping_hash = sha(canonical(patient_mapping))
    lock_key = actor.organization_id + ':' + actor.facility_id + ':' + report['source_sha256']
    db.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:identity,0))'), {'identity':lock_key})
    existing = db.scalar(select(LegacyImport).where(LegacyImport.organization_id == actor.organization_id,
        LegacyImport.facility_id == actor.facility_id, LegacyImport.source_sha256 == report['source_sha256']))
    if existing:
        if existing.mapping_sha256 != mapping_hash:
            raise HTTPException(409, 'SOURCE_ALREADY_IMPORTED_WITH_DIFFERENT_MAPPING')
        return {'import_id': existing.id, 'replayed': True, 'source_sha256': existing.source_sha256}
    summary = {k:v for k,v in report.items() if k != 'rows'}
    batch = LegacyImport(organization_id=actor.organization_id, facility_id=actor.facility_id,
        source_sha256=report['source_sha256'], mapping_sha256=mapping_hash, source_name=report['source_name'],
        report_json=canonical(summary), created_by=actor.user_id)
    db.add(batch); db.flush()
    for row in report['rows']:
        db.add(LegacyRow(import_id=batch.id, source_table=row['source_table'], legacy_id=row['legacy_id'],
            legacy_patient_id=row['legacy_patient_id'], mapped_patient_id=patient_mapping.get(row['legacy_patient_id']),
            source_row_json=row['source_row_json'], row_sha256=row['row_sha256'], status=row['status'], gap_json=canonical(row['gaps'])))
    audit(db, actor, 'D38', batch.id, 'legacy_imported', {'source_sha256':report['source_sha256'], 'counts':report['source_counts'], 'gaps':len(report['gaps'])})
    db.flush()
    return {'import_id':batch.id, 'replayed':False, **summary}


# Importing inspect_sqlite alone does not require the PostgreSQL application.
def make_router():
    from fastapi import APIRouter, Depends, HTTPException
    from sqlalchemy import select
    from .auth import current_actor, require, require_domain, scoped_patient
    from .db import get_db
    from .models_legacy import LegacyImport, LegacyRow
    router = APIRouter(tags=['legacy-evidence'])

    @router.get('/legacy/results')
    def archived_results(patient_id: str, db=Depends(get_db, scope="function"), actor=Depends(current_actor)):
        require_domain(actor, 'D22')
        require(actor, 'documents.content')
        scoped_patient(db, actor, patient_id)
        matches = db.execute(select(LegacyRow, LegacyImport).join(LegacyImport, LegacyRow.import_id == LegacyImport.id).where(
            LegacyImport.organization_id == actor.organization_id, LegacyImport.facility_id == actor.facility_id,
            LegacyRow.mapped_patient_id == patient_id, LegacyRow.source_table == 'results')).all()
        return {'items':[{'id': row.id, 'import_id':batch.id, 'legacy_id':row.legacy_id, 'status':row.status,
            'result':json.loads(row.source_row_json), 'gaps':json.loads(row.gap_json), 'read_only':True,
            'source_sha256':batch.source_sha256} for row,batch in matches]}

    @router.post('/legacy/results/{legacy_result_id}/commit')
    def disallow_legacy_commit(legacy_result_id: str, db=Depends(get_db, scope="function"), actor=Depends(current_actor)):
        require_domain(actor, 'D22', write=True)
        row = db.get(LegacyRow, legacy_result_id)
        batch = db.get(LegacyImport, row.import_id) if row else None
        if not row or not batch or batch.organization_id != actor.organization_id or batch.facility_id != actor.facility_id or not row.mapped_patient_id:
            raise HTTPException(404, 'NOT_FOUND')
        scoped_patient(db, actor, row.mapped_patient_id)
        raise HTTPException(409, 'LEGACY_EVIDENCE_READ_ONLY_NO_NEW_COMMIT')
    return router
