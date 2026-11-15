"""Facility-scoped AI operations metadata; no chart, inference or host control."""
import math
import re
from typing import Literal
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from .auth import current_actor, require, require_domain
from .db import get_db
from .common import utcnow
from .models_assistant import AssistantRun as Run, AssistantRevision, AssistantEffect, AssistantWatch
from .assistant_profiles import PROFILES
from .assistant_provider import assistant_provider_config
from .assistant_evidence import SELECTION_VERSION

router = APIRouter(prefix='/admin', tags=['administration'])
STATES = ('queued','waiting_for_capacity','running','succeeded','failed','timeout','invalid_output','abstained','stale_context','interrupted')
SAFE_ERRORS = frozenset({
    'ASSISTANT_TIMEOUT','ASSISTANT_INVALID_OUTPUT','ASSISTANT_OUTPUT_INVALID',
    'ASSISTANT_QUOTE_NOT_IN_SOURCE','ASSISTANT_TYPED_DISPLAY_MISMATCH',
    'ASSISTANT_SOURCE_CHANGED','ASSISTANT_AUTHORIZATION_CHANGED',
    'ASSISTANT_CONTEXT_CLOSED','ASSISTANT_PROFILE_FORBIDDEN',
    'ASSISTANT_CONTEXT_BUDGET_EXCEEDED','ASSISTANT_COMPLETION_INVALID',
    'ASSISTANT_MODEL_CAPABILITY_INVALID','ASSISTANT_TEMPLATE_IDENTITY_MISMATCH',
    'ASSISTANT_INPUT_INVALID','ASSISTANT_DISPATCH_INTERRUPTED',
    'NEWER_SOURCE_QUEUED','SOURCE_CHANGED','AUTHORIZATION_CHANGED',
    'PROVIDER_TIMEOUT','PROVIDER_UNAVAILABLE','LEASE_EXPIRED',
})
USAGE = ('prompt_eval_count','eval_count','prompt_eval_duration','eval_duration','total_duration')
COVERAGE = ('eligible_sources','included_sources','omitted_sources','partial_sources')
State = Literal['queued','waiting_for_capacity','running','succeeded','failed','timeout','invalid_output','abstained','stale_context','interrupted']
Profile = Literal['visit_preparation','nursing_handover','records_readiness','laboratory_handoff']


def _number(value):
    return value if type(value) in (int, float) and 0 <= value <= 10**18 and math.isfinite(value) else None


def _iso(value):
    return value.isoformat() if value else None


def _counts():
    return {**dict.fromkeys(STATES, 0), 'awaiting_review': 0}


@router.get('/ai-operations')
def operations(profile: Profile | None = None, state: State | None = None,
               offset: int = Query(0, ge=0, le=1000000), limit: int = Query(25, ge=1, le=50),
               actor=Depends(current_actor), db=Depends(get_db, scope='function')):
    require_domain(actor, 'D34'); require(actor, 'identity.admin')
    observed = utcnow()
    scope = (Run.organization_id == actor.organization_id, Run.facility_id == actor.facility_id)
    counts = _counts(); per_profile = {key: _counts() for key in PROFILES}
    for key, execution, review, count in db.execute(select(Run.profile, Run.execution_state, Run.review_state, func.count()).where(*scope).group_by(Run.profile, Run.execution_state, Run.review_state)):
        if key not in per_profile or execution not in STATES: continue
        counts[execution] += count; per_profile[key][execution] += count
        if execution == 'succeeded' and review == 'pending':
            counts['awaiting_review'] += count; per_profile[key]['awaiting_review'] += count
    where = list(scope)
    if profile: where.append(Run.profile == profile)
    if state: where.append(Run.execution_state == state)
    total = db.scalar(select(func.count()).select_from(Run).where(*where))
    # SQL projects only individual allowlisted scalars. Never load an ORM Run or
    # full JSON body and then redact it after the fact.
    columns = [Run.id, Run.profile, Run.execution_state, Run.review_state, Run.error,
               Run.created_at, Run.started_at, Run.completed_at, Run.measured_cost]
    columns += [Run.usage[key].label('usage_' + key) for key in USAGE]
    columns += [(Run.source_manifest['coverage'][key] if key == 'partial_sources' else Run.inference_view['coverage'][key]).label('coverage_' + key) for key in COVERAGE]
    columns += [select(func.count()).select_from(AssistantRevision).where(AssistantRevision.run_id == Run.id).scalar_subquery().label('revision_count'),
                select(func.count()).select_from(AssistantEffect).where(AssistantEffect.run_id == Run.id).scalar_subquery().label('effect_count')]
    items = []
    for row in db.execute(select(*columns).where(*where).order_by(Run.created_at.desc(), Run.id).offset(offset).limit(limit)).mappings():
        elapsed = (row['completed_at'] - row['started_at']).total_seconds() * 1000 if row['completed_at'] and row['started_at'] else None
        cost = row['measured_cost']
        items.append({
            **{key: row[key] for key in ('id','profile','execution_state','review_state','revision_count','effect_count')},
            'error': row['error'] if row['error'] in SAFE_ERRORS else ('OTHER_FAILURE' if row['error'] else None),
            **{key: _iso(row[key]) for key in ('created_at','started_at','completed_at')},
            'elapsed_ms': round(elapsed) if elapsed is not None and elapsed >= 0 else None,
            'queue_age_seconds': round(max(0, (observed-row['created_at']).total_seconds())) if row['execution_state'] in ('queued','waiting_for_capacity') else None,
            'usage': {key: _number(row['usage_' + key]) for key in USAGE},
            'measured_cost': cost if isinstance(cost, str) and re.fullmatch(r'\d{1,12}(?:\.\d{1,8})?', cost) else None,
            'coverage': {key: _number(row['coverage_' + key]) for key in COVERAGE},
            'evidence_freshness': 'not_checked_for_admin',
        })
    started, completed = db.execute(select(func.max(Run.started_at), func.max(Run.completed_at)).where(*scope)).one()
    provider = assistant_provider_config()
    # Configuration values are owned by the pinned adapter, never persisted raw
    # per-run provider JSON (which can contain arbitrary transport diagnostics).
    declared = provider.get('profiles_qualified', [])
    safe_provider = {key: provider.get(key) for key in ('enabled','configured','route','model','model_digest','engine_version','context_tokens','max_output_tokens')}
    safe_provider.update(live_status='not_checked', declared_qualified_profiles=[key for key in PROFILES if key in declared],
                         selection_version=SELECTION_VERSION, qualification_scope='operator_declared_provider_profiles; current_selector_acceptance_separate')
    return {
        'observed_at': observed.isoformat(),
        'scope': {'organization_id': actor.organization_id, 'facility_id': actor.facility_id},
        'provider': safe_provider,
        'worker': {'heartbeat_status':'not_observed','heartbeat_at':None,'last_started_at':_iso(started),'last_completed_at':_iso(completed),'persisted_running':counts['running']},
        'counts': counts, 'profiles': [{'profile':key,'counts':value} for key,value in per_profile.items()],
        'items': items, 'total': total, 'offset': offset, 'limit': limit,
        'active_watches': db.scalar(select(func.count()).select_from(AssistantWatch).where(AssistantWatch.organization_id==actor.organization_id,AssistantWatch.facility_id==actor.facility_id,AssistantWatch.status=='active',AssistantWatch.expires_at>observed)),
    }
