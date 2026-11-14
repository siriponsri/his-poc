"""Versioned, source-bound output contract for synthetic care preparation."""

from __future__ import annotations

import json
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = "carebalance-assistant-v1.1"
PROFILES = (
    "visit_preparation",
    "nursing_handover",
    "records_readiness",
    "laboratory_handoff",
)
EFFECT_KINDS = (
    "create_visit_draft",
    "create_nursing_draft",
    "create_document_review_task",
    "create_nursing_followup_task",
    "create_records_review_task",
    "link_lab_review_task",
)
GAP_KINDS = (
    "missing_document",
    "incomplete_metadata",
    "pending_task",
    "review_required",
    "follow_up",
)
PROFILE_EFFECTS = {
    "visit_preparation": {"create_visit_draft", "create_document_review_task"},
    "nursing_handover": {"create_nursing_draft", "create_nursing_followup_task"},
    "records_readiness": {"create_records_review_task"},
    "laboratory_handoff": {"link_lab_review_task"},
}


def canonical(value) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Fact(StrictModel):
    source_ref: str = Field(pattern=r"^s[1-9][0-9]*$", max_length=16)
    field: str | None = Field(default=None, min_length=1, max_length=80)
    quote: str | None = Field(default=None, min_length=1, max_length=400)
    display: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def one_evidence_kind(self):
        if (self.field is None) == (self.quote is None):
            raise ValueError("ONE_EXACT_EVIDENCE_KIND_REQUIRED")
        return self


class WorkGap(Fact):
    kind: Literal[
        "missing_document",
        "incomplete_metadata",
        "pending_task",
        "review_required",
        "follow_up",
    ]
    title: str | None = Field(default=None, max_length=240)


class Draft(StrictModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,63}$")
    title: str = Field(min_length=1, max_length=240)
    text: str = Field(min_length=1, max_length=4000)
    source_refs: list[str] = Field(min_length=1, max_length=12)


class SuggestedEffect(StrictModel):
    action_id: str = Field(pattern=r"^a[1-9][0-9]*$", max_length=16)
    kind: Literal[
        "create_visit_draft",
        "create_nursing_draft",
        "create_document_review_task",
        "create_nursing_followup_task",
        "create_records_review_task",
        "link_lab_review_task",
    ]
    source_refs: list[str] = Field(min_length=1, max_length=12)
    draft_id: str | None = Field(default=None, max_length=64)


class AssistantArtifact(StrictModel):
    facts: list[Fact] = Field(max_length=8)
    work_gaps: list[WorkGap] = Field(max_length=6)
    drafts: list[Draft] = Field(max_length=1)
    suggested_effects: list[SuggestedEffect] = Field(max_length=4)
    requires_review: Literal[True]


def output_schema(inference_view: dict | None = None) -> dict:
    """Generate only offered evidence/actions; validate independently afterward.

    Normalized DTOs still carry server-built displays. Those fields are absent
    from the model grammar, which binds references to their actual field keys.
    """
    schema = AssistantArtifact.model_json_schema()
    if inference_view is None:
        return schema

    def constant(value):
        return {"type": "string", "enum": [value]}

    def object_schema(properties):
        return {
            "type": "object",
            "properties": properties,
            "required": list(properties),
            "additionalProperties": False,
        }

    sources = inference_view["sources"]
    refs = [source["ref"] for source in sources]
    facts, gaps = [], []
    for source in sources:
        fields = [
            key
            for key, value in source["fields"].items()
            if value is None or isinstance(value, (str, int, float, bool))
        ]
        if fields:
            facts.append(
                object_schema(
                    {
                        "source_ref": constant(source["ref"]),
                        "field": {"type": "string", "enum": fields},
                    }
                )
            )
        if source.get("text"):
            facts.append(
                object_schema(
                    {
                        "source_ref": constant(source["ref"]),
                        "quote": {"type": "string", "minLength": 1, "maxLength": 400},
                    }
                )
            )
        for field in fields:
            for kind in GAP_KINDS:
                if _gap_supported({"field": field, "kind": kind}, source):
                    gaps.append(
                        object_schema(
                            {
                                "source_ref": constant(source["ref"]),
                                "field": constant(field),
                                "kind": constant(kind),
                            }
                        )
                    )
    schema["$defs"]["Fact"] = {"anyOf": facts}
    if gaps:
        schema["$defs"]["WorkGap"] = {"anyOf": gaps}
    else:
        schema["properties"]["work_gaps"]["maxItems"] = 0

    candidates = inference_view.get("effect_candidates", [])
    effects = []
    for candidate in candidates:
        properties = {
            "action_id": constant(candidate["action_id"]),
            "kind": constant(candidate["kind"]),
            "source_refs": {
                "type": "array",
                "items": {"type": "string", "enum": candidate["source_refs"]},
                "minItems": 1,
                "maxItems": 12,
                "uniqueItems": True,
            },
        }
        if candidate.get("draft_id"):
            properties["draft_id"] = constant(candidate["draft_id"])
        effects.append(object_schema(properties))
    if effects:
        schema["$defs"]["SuggestedEffect"] = {"anyOf": effects}
        schema["properties"]["suggested_effects"]["maxItems"] = len(effects)
    else:
        schema["properties"]["suggested_effects"]["maxItems"] = 0
    draft_ids = [
        candidate["draft_id"] for candidate in candidates if candidate.get("draft_id")
    ]
    if draft_ids:
        schema["$defs"]["Draft"]["properties"]["id"] = {
            "type": "string",
            "enum": draft_ids,
        }
        schema["$defs"]["Draft"]["properties"]["source_refs"]["items"] = {
            "type": "string",
            "enum": refs,
        }
    else:
        schema["properties"]["drafts"]["maxItems"] = 0
    return schema


def assert_profile_sources(profile, rows):
    if profile == "records_readiness":
        forbidden = {
            "content",
            "document_content",
            "body",
            "text",
            "author",
            "created_by",
            "created_by_id",
            "summary",
            "pending_tasks",
        }
        if any(
            row.get("text")
            or row.get("kind") in ("lab", "handover")
            or forbidden & set(row.get("fields", {}))
            for row in rows
        ):
            raise ValueError("RECORDS_PROFILE_CONTENT_FORBIDDEN")
    if profile == "nursing_handover" and any(row.get("kind") == "lab" for row in rows):
        raise ValueError("NURSING_LAB_CONTENT_FORBIDDEN")


def _references(values, sources):
    if len(values) != len(set(values)) or any(value not in sources for value in values):
        raise ValueError("ASSISTANT_SOURCE_REFERENCE_INVALID")


def _scalar_display(value, locale):
    if isinstance(value, bool):
        return (
            ("ใช่" if value else "ไม่ใช่")
            if locale == "th"
            else ("Yes" if value else "No")
        )
    if value is None:
        return "ยังไม่ระบุ" if locale == "th" else "Not recorded"
    if isinstance(value, (str, int, float)) and not isinstance(value, bool):
        return str(value)
    raise ValueError("ASSISTANT_TYPED_FIELD_NOT_SCALAR")


def _evidence(item, sources, locale):
    source = sources.get(item.source_ref)
    if source is None:
        raise ValueError("ASSISTANT_SOURCE_REFERENCE_INVALID")
    if item.field is not None:
        fields = source.get("fields", {})
        if item.field not in fields:
            raise ValueError("ASSISTANT_TYPED_FIELD_INVALID")
        value = fields[item.field]
        display = _scalar_display(value, locale)
        # An optional server-built display is authoritative, never model-built.
        supplied = source.get("display_fields", {}).get(item.field)
        if supplied is not None:
            if not isinstance(supplied, str):
                raise ValueError("ASSISTANT_TYPED_DISPLAY_INVALID")
            display = supplied
    else:
        quote = item.quote
        text = source.get("text")
        if (
            not isinstance(text, str)
            or not quote
            or not quote.strip()
            or quote not in text
        ):
            raise ValueError("ASSISTANT_QUOTE_NOT_IN_SOURCE")
        display = quote
    if item.display is not None and item.display != display:
        raise ValueError("ASSISTANT_TYPED_DISPLAY_MISMATCH")
    value = item.model_dump()
    value["display"] = display
    return value


def _gap_supported(item, source):
    """The cited typed field must itself establish the workflow claim."""
    field = item.get("field")
    fields = source.get("fields", {})
    value = fields.get(field)
    kind = source.get("kind")
    claim = item["kind"]
    if claim == "missing_document":
        return (
            kind == "workflow"
            and field == "missing_document_count"
            and isinstance(value, int)
            and not isinstance(value, bool)
            and value > 0
        )
    if claim == "incomplete_metadata":
        return field in {"display_name", "sex", "birth_date", "title"} and (
            value is None or value == "" or (field == "sex" and value == "unknown")
        )
    pending = (
        kind == "task"
        and field == "status"
        and value in {"open", "in_progress", "pending"}
    )
    if claim == "pending_task":
        return pending
    if claim == "review_required":
        return pending or (
            field == "status"
            and (
                (kind == "document" and value == "draft")
                or (kind == "lab" and value in {"released", "corrected"})
                or (kind == "handover" and value == "draft")
            )
        )
    if claim == "follow_up":
        return pending or (
            kind == "workflow" and field == "follow_up" and value is True
        )
    return False


def validate_assistant_artifact(profile: str, artifact, inference_view: dict) -> dict:
    """Validate model output, not clinical meaning or newly human-authored facts."""
    if profile not in PROFILES or inference_view.get("profile") != profile:
        raise ValueError("ASSISTANT_PROFILE_INVALID")
    if isinstance(artifact, str):
        if len(artifact.encode("utf-8")) > 24000:
            raise ValueError("ASSISTANT_OUTPUT_LIMIT")
        parsed = AssistantArtifact.model_validate_json(artifact, strict=True)
    else:
        parsed = AssistantArtifact.model_validate(artifact, strict=True)
    rows = inference_view.get("sources")
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError("ASSISTANT_SOURCE_PACKET_INVALID")
    sources = {row.get("ref"): row for row in rows}
    if len(sources) != len(rows) or any(
        not isinstance(ref, str) or not re.fullmatch(r"s[1-9][0-9]*", ref)
        for ref in sources
    ):
        raise ValueError("ASSISTANT_SOURCE_PACKET_INVALID")
    assert_profile_sources(profile, rows)
    if profile == "records_readiness":
        if parsed.drafts or any(row.get("text") for row in rows):
            raise ValueError("RECORDS_PROFILE_CONTENT_FORBIDDEN")
        if any(item.quote is not None for item in [*parsed.facts, *parsed.work_gaps]):
            raise ValueError("RECORDS_PROFILE_CONTENT_FORBIDDEN")

    locale = inference_view.get("locale", "th")
    facts = [_evidence(item, sources, locale) for item in parsed.facts]
    gaps = [_evidence(item, sources, locale) for item in parsed.work_gaps]
    gap_labels = {
        "missing_document": ("ตรวจเอกสารที่พร้อมทบทวน", "Review available documentation"),
        "incomplete_metadata": ("ทบทวนข้อมูลที่ยังไม่ครบ", "Review incomplete metadata"),
        "pending_task": ("ติดตามงานที่เปิดไว้", "Follow up an open task"),
        "review_required": ("เตรียมงานทบทวน", "Prepare review work"),
        "follow_up": ("เตรียมติดตามงาน", "Prepare follow-up work"),
    }
    for item in gaps:
        if not _gap_supported(item, sources[item["source_ref"]]):
            raise ValueError("ASSISTANT_GAP_NOT_SUPPORTED")
        title = gap_labels[item["kind"]][0 if locale == "th" else 1]
        if item.get("title") not in (None, title):
            raise ValueError("ASSISTANT_GAP_TITLE_TEMPLATE_MISMATCH")
        item["title"] = title

    candidates_list = inference_view.get("effect_candidates", [])
    if not isinstance(candidates_list, list) or any(
        not isinstance(c, dict) for c in candidates_list
    ):
        raise ValueError("ASSISTANT_EFFECT_CANDIDATES_INVALID")
    candidates = {
        candidate.get("action_id"): candidate for candidate in candidates_list
    }
    if len(candidates) != len(candidates_list):
        raise ValueError("ASSISTANT_EFFECT_CANDIDATES_INVALID")
    draft_candidates = {
        candidate.get("draft_id")
        for candidate in candidates_list
        if candidate.get("kind") in ("create_visit_draft", "create_nursing_draft")
    }
    drafts = {}
    # Generated draft numbers must be present in authorized source data. This is
    # deliberately conservative; reviewed human edits are a separate revision.
    for draft in parsed.drafts:
        if draft.id in drafts or draft.id not in draft_candidates:
            raise ValueError("ASSISTANT_DRAFT_REFERENCE_INVALID")
        if profile not in ("visit_preparation", "nursing_handover"):
            raise ValueError("ASSISTANT_DRAFT_PROFILE_FORBIDDEN")
        _references(draft.source_refs, sources)
        cited = [sources[ref] for ref in draft.source_refs]
        source_text = "\n".join(
            str(value)
            for source in cited
            for value in source.get("fields", {}).values()
        )
        source_text += "\n" + "\n".join(source.get("text", "") for source in cited)
        numbers = set(re.findall(r"-?\d+(?:[.,]\d+)*", source_text))
        if (
            set(re.findall(r"-?\d+(?:[.,]\d+)*", draft.title + "\n" + draft.text))
            - numbers
        ):
            raise ValueError("ASSISTANT_DRAFT_NUMBER_NOT_IN_SOURCE")
        drafts[draft.id] = draft.model_dump()
    effects = []
    seen = set()
    for effect in parsed.suggested_effects:
        candidate = candidates.get(effect.action_id)
        if (
            effect.action_id in seen
            or candidate is None
            or effect.kind not in PROFILE_EFFECTS[profile]
        ):
            raise ValueError("ASSISTANT_EFFECT_NOT_ALLOWED")
        if (
            candidate.get("kind") != effect.kind
            or candidate.get("draft_id") != effect.draft_id
        ):
            raise ValueError("ASSISTANT_EFFECT_NOT_ALLOWED")
        _references(effect.source_refs, sources)
        if not set(effect.source_refs) <= set(candidate.get("source_refs", [])):
            raise ValueError("ASSISTANT_EFFECT_SOURCE_MISMATCH")
        if effect.draft_id is not None and effect.draft_id not in drafts:
            raise ValueError("ASSISTANT_EFFECT_DRAFT_MISSING")
        if effect.draft_id is not None and not set(
            drafts[effect.draft_id]["source_refs"]
        ) <= set(effect.source_refs):
            raise ValueError("ASSISTANT_EFFECT_DRAFT_SOURCE_MISMATCH")
        seen.add(effect.action_id)
        effects.append(effect.model_dump())
    return {
        "facts": facts,
        "work_gaps": gaps,
        "drafts": list(drafts.values()),
        "suggested_effects": effects,
        "requires_review": True,
    }
