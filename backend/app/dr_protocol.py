"""Strict wire DTOs and transport authentication for the bound DR receiver."""
from __future__ import annotations

from datetime import datetime, timezone
import base64
import hashlib
import hmac
import json
import re
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

PROTOCOL = "carebalance.dr.v1"
AUDIENCE = "carebalance-dr-his-poc"
MAX_IMAGE_BYTES = 1024 * 1024
MAX_BODY_BYTES = 12 * 1024 * 1024
MAX_RESPONSE_BYTES = 16 * 1024 * 1024
Identifier = Annotated[str, Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")]
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Capability = Literal["dr.read", "dr.prepare", "dr.grade.confirm", "dr.report.prepare", "dr.report.sign"]


class Message(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


def utc(value):
    if not isinstance(value, str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z", value
    ):
        raise ValueError("Explicit UTC Z timestamp required")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class WorkspaceScope(Message):
    organization_id: Identifier
    facility_id: Identifier
    patient_id: Identifier
    encounter_id: Identifier
    task_id: Identifier
    source_set_id: Identifier
    source_set_revision: int = Field(ge=1)
    source_set_sha256: Digest


class Context(Message):
    binding_id: Identifier
    actor_id: Identifier
    session_id: Identifier
    expires_at: datetime
    capabilities: tuple[Capability, ...] = Field(min_length=1, max_length=5)
    scope: WorkspaceScope

    @field_validator("expires_at", mode="before")
    @classmethod
    def parse_expiry(cls, value):
        return utc(value)

    @model_validator(mode="after")
    def unique_capabilities(self):
        if len(set(self.capabilities)) != len(self.capabilities):
            raise ValueError("Repeated capability")
        return self


class SourceManifest(Message):
    source_id: Identifier
    source_version: int = Field(ge=1)
    source_sha256: Digest
    image_sha256: Digest
    byte_size: int = Field(ge=1, le=MAX_IMAGE_BYTES)
    media_type: Literal["image/png", "image/jpeg"]
    laterality: Literal["L", "R"]
    modality: Literal["CFP", "UWF"]
    source_origin: Literal["SYNTHETIC", "PUBLIC"]
    consent_reference: Annotated[str, Field(min_length=1, max_length=120)]
    capture_time: str | None

    @field_validator("capture_time")
    @classmethod
    def timestamp(cls, value):
        if value is not None:
            utc(value)
        return value


class SourceInput(SourceManifest):
    image_base64: str = Field(min_length=4, max_length=((MAX_IMAGE_BYTES + 2) // 3) * 4)

    def manifest(self) -> dict:
        return self.model_dump(mode="json", exclude={"image_base64"})


class Operation(Message):
    protocol: Literal["carebalance.dr.v1"]
    request_id: Identifier
    context: Context


class Import(Operation):
    sources: tuple[SourceInput, ...] = Field(min_length=1, max_length=8)

    @model_validator(mode="after")
    def manifest_digest(self):
        manifest = [entry.manifest() for entry in self.sources]
        if digest(manifest) != self.context.scope.source_set_sha256:
            raise ValueError("Source-set digest mismatch")
        if len({entry.source_id for entry in self.sources}) != len(self.sources):
            raise ValueError("Duplicate source identifier")
        if len({entry.image_sha256 for entry in self.sources}) != len(self.sources):
            raise ValueError("Duplicate image hash")
        if sum(entry.byte_size for entry in self.sources) > 8 * MAX_IMAGE_BYTES:
            raise ValueError("Source-set too large")
        return self


class Dispatch(Operation):
    method: Literal["GET", "POST", "PUT"]
    path: str = Field(min_length=1, max_length=200)
    query: dict[str, str] = Field(max_length=4)
    body: dict | None


class ReadReport(Operation):
    case_id: Digest


class ClinicalEnvelope(Message):
    protocol: Literal['carebalance.dr.v1']
    request_id: Identifier
    binding_id: Identifier
    workspace_id: Identifier
    outcome: Literal['succeeded','rejected','unknown']
    status_code: int = Field(ge=100,le=599)
    content_type: Literal['application/json','text/html','image/png','image/jpeg']
    body_base64: str = Field(max_length=((MAX_RESPONSE_BYTES+2)//3)*4)
    response_sha256: Digest

    @model_validator(mode='after')
    def response_integrity(self):
        raw = base64.b64decode(self.body_base64,validate=True)
        if len(raw)>MAX_RESPONSE_BYTES or hashlib.sha256(raw).hexdigest()!=self.response_sha256:
            raise ValueError('Clinical response integrity mismatch')
        if ((self.outcome=='unknown' and self.status_code!=202)
                or (self.outcome=='succeeded' and not 200<=self.status_code<300)
                or (self.outcome=='rejected' and self.status_code<400)):
            raise ValueError('Inconsistent clinical outcome')
        return self


class CaseReviewWitness(Message):
    case_id: Digest
    source_sha256: Digest
    image_sha256: Digest
    confirm_revision: int | None = Field(ge=0)
    grade_review_revision: int | None = Field(ge=0)
    grade_status: Literal['NOT_REVIEWED','CONFIRMED','UNGRADABLE','NEEDS_SECOND_REVIEW','UNKNOWN']
    reviewed_grade: int | None = Field(ge=0,le=4)
    quality: Literal['GRADABLE','UNGRADABLE','NEEDS_REVIEW','NOT_EVALUATED']
    annotation_set_sha256: Digest
    annotation_review_revision: int | None = Field(ge=0)
    annotation_confirmation_sha256: Digest | None


class ReviewWitness(Message):
    source_set_sha256: Digest
    report_form_sha256: Digest
    cases: tuple[CaseReviewWitness, ...] = Field(min_length=1,max_length=8)

    @model_validator(mode='after')
    def unique_sorted_cases(self):
        identifiers = [case.case_id for case in self.cases]
        if identifiers!=sorted(set(identifiers)):
            raise ValueError('Review witness cases must be unique and sorted')
        return self


class ReviewFreshness(Message):
    state: Literal['CURRENT','CHANGED','UNAVAILABLE']
    witness_sha256: Digest | None
    current_witness_sha256: Digest | None
    checked_at: str
    changed_case_ids: tuple[Digest, ...] = Field(max_length=8)

    @field_validator('checked_at')
    @classmethod
    def checked_timestamp(cls,value):
        utc(value)
        return value

    @model_validator(mode='after')
    def consistent_assessment(self):
        if self.state=='CURRENT' and (self.witness_sha256 is None or self.witness_sha256!=self.current_witness_sha256
                                      or self.changed_case_ids):
            raise ValueError('Current review requires matching complete witnesses')
        if self.state=='CHANGED' and (self.witness_sha256 is None or self.current_witness_sha256 is None
                                      or self.witness_sha256==self.current_witness_sha256 or not self.changed_case_ids):
            raise ValueError('Changed review requires distinct complete witnesses')
        if self.state=='UNAVAILABLE' and self.current_witness_sha256 is not None:
            raise ValueError('Unavailable review must not claim a current witness')
        return self


def canonical(value) -> bytes:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def semantic_digest(operation: Operation) -> str:
    value = operation.model_dump(mode="json")
    value["context"].pop("expires_at")
    return digest(value)


def validate_context(context: Context, scope: WorkspaceScope, now: int) -> None:
    if context.scope != scope or not now < context.expires_at.timestamp() <= now + 120:
        raise ValueError("Expired or mismatched connector context")


def signed_bytes(method: str, path: str, timestamp: int, nonce: str, audience: str, body: bytes) -> bytes:
    if method != "POST" or path not in {
        "/api/connector/dr/import", "/api/connector/dr/dispatch", "/api/connector/dr/read-report"
    }:
        raise ValueError("Unsupported connector target")
    if type(timestamp) is not int or timestamp < 0:
        raise ValueError("Invalid transport timestamp")
    if not re.fullmatch(r"[A-Za-z0-9_-]{32,96}", nonce) or audience != AUDIENCE:
        raise ValueError("Invalid transport identity")
    return "\n".join(("carebalance.connector.v1", method, path, str(timestamp), nonce,
                      audience, hashlib.sha256(body).hexdigest())).encode("ascii")


def sign_request(key: bytes, *, method: str, path: str, timestamp: int,
                 nonce: str, audience: str, body: bytes) -> str:
    if not isinstance(key, bytes) or len(key) < 32:
        raise ValueError("Dedicated connector key required")
    return hmac.new(key, signed_bytes(method, path, timestamp, nonce, audience, body),
                    hashlib.sha256).hexdigest()


def verify_request(key: bytes, *, method: str, path: str, timestamp: int, nonce: str,
                   audience: str, body: bytes, signature: str, now: int) -> None:
    if type(now) is not int or type(timestamp) is not int or abs(now - timestamp) > 30:
        raise ValueError("Expired connector envelope")
    if not isinstance(signature, str) or not re.fullmatch(r"[0-9a-f]{64}", signature):
        raise ValueError("Invalid connector envelope")
    expected = sign_request(key, method=method, path=path, timestamp=timestamp,
                            nonce=nonce, audience=audience, body=body)
    if not hmac.compare_digest(expected, signature):
        raise ValueError("Invalid connector envelope")


def now_seconds() -> int:
    return int(datetime.now(timezone.utc).timestamp())
