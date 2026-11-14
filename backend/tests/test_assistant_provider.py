"""Real transport-boundary doubles, source validation and no-fallback regressions."""

from copy import deepcopy
import json

import httpx
import pytest

from backend.app.assistant_provider import (
    AssistantOllamaProvider,
    MODEL,
    MODEL_DIGEST,
    assistant_provider_config,
)
from backend.app.assistant_schema import validate_assistant_artifact
from backend.app.providers import OllamaSettings


def packet(profile="visit_preparation"):
    return {
        "profile": profile,
        "locale": "th",
        "sources": [
            {
                "ref": "s1",
                "kind": "patient",
                "fields": {"display_name": "สุเมธ ภัทรกุล", "age": "58"},
            },
            {
                "ref": "s2",
                "kind": "document",
                "fields": {"title": "ติดตามเบาหวาน", "status": "draft"},
                "text": "ติดตามเบาหวานตามนัด BP 138/84 mmHg รอทบทวนยาและการแพ้ยา",
            },
        ],
        "coverage": {
            "eligible_sources": 2,
            "included_sources": 2,
            "omitted_sources": 0,
            "unavailable_domains": [],
        },
        "effect_candidates": [
            {
                "action_id": "a1",
                "kind": "create_visit_draft",
                "source_refs": ["s2"],
                "draft_id": "visit",
            }
        ],
    }


def artifact():
    return {
        "facts": [
            {"source_ref": "s1", "field": "age"},
            {"source_ref": "s2", "quote": "ติดตามเบาหวานตามนัด"},
        ],
        "work_gaps": [],
        "drafts": [
            {
                "id": "visit",
                "title": "ร่างบันทึก",
                "text": "ติดตามเบาหวานตามนัด BP 138/84 mmHg",
                "source_refs": ["s2"],
            }
        ],
        "suggested_effects": [
            {
                "action_id": "a1",
                "kind": "create_visit_draft",
                "source_refs": ["s2"],
                "draft_id": "visit",
            }
        ],
        "requires_review": True,
    }


def provider(handler):
    settings = OllamaSettings(
        "http://127.0.0.1:11435",
        MODEL,
        MODEL_DIGEST,
        "0.12.6",
        timeout_seconds=5,
        context_tokens=4096,
        max_output_tokens=1024,
    )
    return AssistantOllamaProvider(settings, transport=httpx.MockTransport(handler))


def responder(
    output=None, *, drift_after=False, error=None, capabilities=("completion",)
):
    calls = []
    generated = False

    def handle(request):
        nonlocal generated
        calls.append((request.method, request.url.path))
        if request.url.path == "/api/version":
            return httpx.Response(200, json={"version": "0.12.6"})
        if request.url.path == "/api/tags":
            return httpx.Response(
                200,
                json={
                    "models": [
                        {
                            "name": MODEL,
                            "digest": "0" * 64
                            if drift_after and generated
                            else MODEL_DIGEST,
                            "details": {},
                        }
                    ]
                },
            )
        if request.url.path == "/api/show":
            return httpx.Response(
                200,
                json={
                    "template": "test-template",
                    "parameters": "",
                    "capabilities": list(capabilities)
                    if isinstance(capabilities, tuple)
                    else capabilities,
                },
            )
        if request.url.path == "/api/chat":
            generated = True
            body = json.loads(request.content)
            assert (
                body["keep_alive"] == 0
                and body["options"]["num_thread"] == 6
                and body["options"]["num_ctx"] == 4096
                and body["stream"] is False
            )
            assert body["format"]["additionalProperties"] is False
            assert len(body["messages"]) == 2 and body["model"] == MODEL
            if error:
                raise error
            return httpx.Response(
                200,
                json={
                    "model": MODEL,
                    "done": True,
                    "done_reason": "stop",
                    "message": {
                        "role": "assistant",
                        "content": json.dumps(
                            output if output is not None else artifact(),
                            ensure_ascii=False,
                        ),
                    },
                    "prompt_eval_count": 400,
                    "eval_count": 200,
                    "total_duration": 1000,
                },
            )
        raise AssertionError("Unexpected endpoint " + request.url.path)

    return handle, calls


def test_pinned_private_transport_validates_sources_and_calls_generate_once(
    monkeypatch,
):
    monkeypatch.delenv("HIS_ASSISTANT_TEMPLATE_SHA256", raising=False)
    handler, calls = responder()
    result = provider(handler).prepare("visit_preparation", "th", packet())
    assert (
        result["outcome"] == "success"
        and result["artifact"]["facts"][0]["display"] == "58"
    )
    assert calls.count(("POST", "/api/chat")) == 1
    assert (
        result["provenance"]["model_digest"] == MODEL_DIGEST
        and result["usage"]["eval_count"] == 200
    )
    assert result["measured_cost"] is None


@pytest.mark.parametrize(
    "mutation", ["quote", "value", "reference", "effect", "number"]
)
def test_forged_source_or_action_is_rejected(mutation):
    output = artifact()
    if mutation == "quote":
        output["facts"][1]["quote"] = "ไม่มีในต้นฉบับ"
    if mutation == "value":
        output["facts"][0]["display"] = "90"
    if mutation == "reference":
        output["facts"][0]["source_ref"] = "s99"
    if mutation == "effect":
        output["suggested_effects"][0]["kind"] = "link_lab_review_task"
    if mutation == "number":
        output["drafts"][0]["text"] = "อายุ90ปี"
    with pytest.raises(ValueError):
        validate_assistant_artifact("visit_preparation", output, packet())


def test_records_hidden_body_and_nursing_labs_fail_before_any_network():
    for profile in ["records_readiness", "nursing_handover"]:
        view = packet(profile)
        if profile == "nursing_handover":
            view["sources"].append(
                {"ref": "s3", "kind": "lab", "fields": {"result_value": "152"}}
            )
        calls = []
        result = provider(lambda request: calls.append(request)).prepare(
            profile, "th", view
        )
        assert result["outcome"] == "invalid_output" and calls == []


def test_records_metadata_output_has_no_clinical_draft_or_arbitrary_title():
    view = packet("records_readiness")
    view["sources"][1].pop("text")
    view["effect_candidates"] = []
    output = {
        "facts": [{"source_ref": "s2", "field": "status"}],
        "work_gaps": [
            {"source_ref": "s2", "field": "status", "kind": "review_required"}
        ],
        "drafts": [],
        "suggested_effects": [],
        "requires_review": True,
    }
    checked = validate_assistant_artifact("records_readiness", output, view)
    assert checked["work_gaps"][0]["title"] == "เตรียมงานทบทวน"
    output["work_gaps"][0]["title"] = "Invented clinical conclusion"
    with pytest.raises(ValueError):
        validate_assistant_artifact("records_readiness", output, view)
    view["sources"][1]["fields"]["content"] = "Hidden body"
    with pytest.raises(ValueError):
        validate_assistant_artifact("records_readiness", checked, view)


def test_context_budget_failure_never_dispatches_or_truncates():
    view = packet()
    view["sources"][1]["text"] = "ก" * 4000
    original = deepcopy(view)
    calls = []
    result = provider(lambda request: calls.append(request)).prepare(
        "visit_preparation", "th", view
    )
    assert (
        result["reason"] == "ASSISTANT_CONTEXT_BUDGET_EXCEEDED"
        and calls == []
        and view == original
    )


def test_post_generation_identity_drift_retains_failure_without_second_call(
    monkeypatch,
):
    monkeypatch.delenv("HIS_ASSISTANT_TEMPLATE_SHA256", raising=False)
    handler, calls = responder(drift_after=True)
    result = provider(handler).prepare("visit_preparation", "th", packet())
    assert (
        result["outcome"] == "failed" and result["reason"] == "MODEL_IDENTITY_MISMATCH"
    )
    assert result["artifact"] is None and calls.count(("POST", "/api/chat")) == 1


def test_timeout_is_retained_without_retry_or_mock(monkeypatch):
    monkeypatch.delenv("HIS_ASSISTANT_TEMPLATE_SHA256", raising=False)
    handler, calls = responder(error=httpx.ReadTimeout("test timeout"))
    result = provider(handler).prepare("visit_preparation", "th", packet())
    assert result["outcome"] == "timeout" and result["artifact"] is None
    assert (
        calls.count(("POST", "/api/chat")) == 1
        and result["provenance"]["provider"] == "his_assistant_ollama"
    )


def test_default_assistant_configuration_is_disabled(monkeypatch):
    monkeypatch.delenv("HIS_ASSISTANT_ENABLED", raising=False)
    config = assistant_provider_config()
    assert (
        config["enabled"] is False
        and config["configured"] is False
        and config["qualified"] is False
    )
    assert config["profiles_qualified"] == []


@pytest.mark.parametrize(
    "capabilities", ["completion", {"completion": True}, ["completion", 7], None]
)
def test_malformed_capability_metadata_cannot_dispatch(capabilities, monkeypatch):
    monkeypatch.delenv("HIS_ASSISTANT_TEMPLATE_SHA256", raising=False)
    handler, calls = responder(capabilities=capabilities)
    result = provider(handler).prepare("visit_preparation", "th", packet())
    assert result["reason"] == "ASSISTANT_MODEL_CAPABILITY_INVALID"
    assert ("POST", "/api/chat") not in calls


@pytest.mark.parametrize("location", ["text", "title"])
def test_draft_cannot_borrow_number_from_uncited_source(location):
    output = artifact()
    output["drafts"][0][location] += " อายุ58ปี"
    with pytest.raises(ValueError, match="ASSISTANT_DRAFT_NUMBER_NOT_IN_SOURCE"):
        validate_assistant_artifact("visit_preparation", output, packet())


def test_effect_must_include_its_draft_citations():
    output = artifact()
    view = packet()
    view["effect_candidates"][0]["source_refs"] = ["s1", "s2"]
    output["suggested_effects"][0]["source_refs"] = ["s1"]
    with pytest.raises(ValueError, match="ASSISTANT_EFFECT_DRAFT_SOURCE_MISMATCH"):
        validate_assistant_artifact("visit_preparation", output, view)


def test_gap_kind_and_title_need_supporting_typed_field():
    view = packet()
    output = artifact()
    output["work_gaps"] = [
        {"source_ref": "s2", "field": "status", "kind": "missing_document"}
    ]
    with pytest.raises(ValueError, match="ASSISTANT_GAP_NOT_SUPPORTED"):
        validate_assistant_artifact("visit_preparation", output, view)
    output["work_gaps"][0]["kind"] = "review_required"
    checked = validate_assistant_artifact("visit_preparation", output, view)
    assert checked["work_gaps"][0]["title"] == "เตรียมงานทบทวน"
    output["work_gaps"][0]["title"] = "Invented clinical claim"
    with pytest.raises(ValueError, match="ASSISTANT_GAP_TITLE_TEMPLATE_MISMATCH"):
        validate_assistant_artifact("visit_preparation", output, view)
