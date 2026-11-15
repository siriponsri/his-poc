"""Deterministic bounded selection and immutable evidence presentation, no inference."""
from collections import Counter
import re
from urllib.parse import quote

SELECTION_VERSION = 'profile-passages-v2'
PROFILE_ORDER = {
    'visit_preparation': ('document', 'lab', 'task', 'encounter', 'patient'),
    'nursing_handover': ('handover', 'document', 'task', 'encounter', 'patient'),
    'records_readiness': ('document', 'task', 'encounter', 'patient'),
    'laboratory_handoff': ('lab', 'task', 'encounter', 'patient'),
}


def ordered_sources(rows, profile):
    """First available source of each permitted kind, then remaining newest rows."""
    order = PROFILE_ORDER[profile]
    ranked = sorted(enumerate(rows), key=lambda pair: (order.index(pair[1]['kind']) if pair[1]['kind'] in order else len(order), pair[0]))
    seen = set(); first = []; rest = []
    for _, row in ranked:
        (rest if row['kind'] in seen else first).append(row)
        seen.add(row['kind'])
    return first + rest


def excerpt(text, maximum_bytes=480):
    """Return an exact, disclosed passage; never synthesize or join source spans."""
    if len(text.encode('utf-8')) <= maximum_bytes:
        return text, 0, len(text)
    cue = re.search(r'อาการ|ประวัติ|แพ้ยา|ส่งเวร|งานค้าง|ติดตาม|chief|history|symptom|handover|pending|follow.up', text, re.IGNORECASE)
    start = text.rfind('\n', 0, cue.start()) + 1 if cue else 0
    if cue and len(text[start:cue.start()].encode('utf-8')) > maximum_bytes // 2:
        # A long unbroken line must not force a return to its cover-page prefix.
        # Retain bounded preceding context, including nearby negation, rather
        # than starting exactly at the keyword or synthesizing multiple spans.
        start = cue.start()
        while start > 0 and len(text[start-1:cue.start()].encode('utf-8')) <= maximum_bytes // 4:
            start -= 1
    while start < len(text) and text[start].isspace(): start += 1
    # Byte bound with complete Unicode code points, with original offsets retained.
    chunk = text[start:].encode('utf-8')[:maximum_bytes].decode('utf-8', errors='ignore')
    last = max(chunk.rfind('\n'), chunk.rfind('. '), chunk.rfind(' '))
    if last >= len(chunk) // 2: chunk = chunk[:last]
    chunk = chunk.rstrip()
    return chunk, start, start + len(chunk)


def source_dto(run, row):
    ref = row['ref']
    view = next((item for item in run.inference_view['sources'] if item['ref'] == ref), None)
    selection = row.get('selection', {})
    return {
        'ref': ref, 'kind': row['kind'], 'label': row.get('label', row['kind']),
        'fields': view.get('fields', {}) if view else {},
        'text': view.get('text') if view else None,
        'identity': row['id'], 'version': row['version'],
        'revision_id': row.get('fields', {}).get('revision'),
        'content_hash': row.get('fields', {}).get('content_hash'),
        'selection': selection.get('kind', 'whole'),
        'excerpt_start': selection.get('start', 0) if 'text' in row else None,
        'excerpt_end': selection.get('end', len(row.get('text', ''))) if 'text' in row else None,
        'offset_unit': 'unicode_code_points',
        'evidence_url': '/api/v2/assistant/runs/' + quote(run.id, safe='') + '/sources/' + ref,
    }


def quality_report(run, revision):
    from .assistant_schema import Fact, _evidence
    rows = run.source_manifest['sources']
    included = [row for row in rows if row.get('ref')]
    source_map = {row['ref']: row for row in run.inference_view['sources']}
    valid = 0
    for fact in revision.artifact.get('facts', []) if revision else []:
        row = source_map.get(fact.get('source_ref'))
        if not row: continue
        try:
            _evidence(Fact.model_validate(fact), source_map, run.locale)
        except ValueError:
            continue
        valid += 1
    return {
        'selection_version': run.source_manifest.get('selection_version', 'legacy-whole-sources-v1'),
        'eligible_by_kind': dict(Counter(row['kind'] for row in rows)),
        'included_by_kind': dict(Counter(row['kind'] for row in included)),
        'omitted_by_kind': dict(Counter(row['kind'] for row in rows if not row.get('ref'))),
        'partial_source_count': sum(row.get('selection', {}).get('kind') == 'excerpt' for row in included),
        'verified_fact_count': valid,
        'draft_attribution': 'source_references_only_requires_human_review',
    }


def snapshot(run, row, fresh, revision=None):
    from fastapi import HTTPException
    from .common import text_hash
    text = row.get('text')
    fields = row.get('fields', {})
    if text is not None and row['kind'] == 'document' and fields.get('content_hash') != text_hash(text):
        raise HTTPException(409, detail={'code': 'ASSISTANT_EVIDENCE_UNAVAILABLE'})
    dto = source_dto(run, row)
    selected = dto.pop('text')
    if text is not None:
        start, end = dto['excerpt_start'], dto['excerpt_end']
        if type(start) is not int or type(end) is not int or not 0 <= start <= end <= len(text) or selected != text[start:end]:
            raise HTTPException(409, detail={'code': 'ASSISTANT_EVIDENCE_UNAVAILABLE'})
    dto.update(fields=fields, text=text, selected_excerpt=selected, source_freshness='current' if fresh else 'stale')
    citations = []
    for fact in revision.artifact.get('facts', []) if revision else []:
        if fact.get('source_ref') != row['ref']: continue
        start = end = None
        if fact.get('quote'):
            start_at = dto['excerpt_start'] or 0
            end_at = dto['excerpt_end'] if dto['excerpt_end'] is not None else len(text or '')
            position = (text or '').find(fact['quote'], start_at, end_at)
            if position < 0: raise HTTPException(409, detail={'code': 'ASSISTANT_EVIDENCE_UNAVAILABLE'})
            start, end = position, position + len(fact['quote'])
        citations.append({'field': fact.get('field'), 'quote': fact.get('quote'), 'display': fact.get('display'), 'start': start, 'end': end})
    dto['citations'] = citations
    return dto
