"""Versioned connector messages and request authentication, independent of transport.

This module does not grant application access. Callers must authorize the current
HIS session and source and atomically persist nonce consumption before acting.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Message(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class SourceReference(Message):
    domain: Literal["D10", "D11"]
    record_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    version: int = Field(ge=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class LabValue(Message):
    """Printed strings are deliberately not parsed, converted or normalized."""
    analyte: str = Field(min_length=1, max_length=150)
    printed_value: str = Field(min_length=1, max_length=200)
    unit: str | None = Field(default=None, max_length=60)
    reference_range: str | None = Field(default=None, max_length=150)


class LaunchContext(Message):
    protocol: Literal["carebalance.connector.v1"]
    request_id: str = Field(min_length=16, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    audience: Literal["carebalance-dr", "carebalance-labclear"]
    binding_id: str = Field(min_length=16, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    organization_id: str = Field(min_length=1, max_length=64)
    facility_id: str = Field(min_length=1, max_length=64)
    actor_id: str = Field(min_length=1, max_length=64)
    patient_id: str = Field(min_length=1, max_length=64)
    encounter_id: str = Field(min_length=1, max_length=64)
    task_id: str = Field(min_length=1, max_length=64)
    source: SourceReference
    purpose: Literal["lab-value-review", "retinal-screening-review"]
    expires_at: datetime
    lab_values: tuple[LabValue, ...] = Field(default=(), max_length=60)

    @field_validator("expires_at", mode="before")
    @classmethod
    def timestamp_wire_format(cls, value):
        if isinstance(value, str) and not re.fullmatch(
                r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z", value):
            raise ValueError("expires_at must use an explicit UTC ISO timestamp")
        if not isinstance(value, (str, datetime)):
            raise ValueError("expires_at cannot be an epoch timestamp")
        return datetime.fromisoformat(value.replace("Z", "+00:00")) if isinstance(value, str) else value

    @field_validator("expires_at")
    @classmethod
    def aware_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None or value.utcoffset().total_seconds() != 0:
            raise ValueError("expires_at must use UTC")
        return value

    @model_validator(mode="after")
    def connector_source(self) -> LaunchContext:
        if self.audience == "carebalance-labclear":
            if self.source.domain != "D10" or self.purpose != "lab-value-review" or not self.lab_values:
                raise ValueError("LabClear requires a D10 source and explicit lab values")
        elif self.source.domain != "D11" or self.purpose != "retinal-screening-review" or self.lab_values:
            raise ValueError("DR requires a D11 source without lab values")
        return self


def canonical_bytes(message: Message) -> bytes:
    return json.dumps(message.model_dump(mode="json"), ensure_ascii=False,
                      sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


class AuthenticationError(ValueError):
    """Intentionally exposes no candidate signature or shared secret."""


def validate_context_lifetime(context: LaunchContext, *, expected_audience: str,
                              now: int, max_lifetime_seconds: int = 120) -> None:
    """Required by both HTTP adapters after parsing and before any operation."""
    if (type(now) is not int or type(max_lifetime_seconds) is not int
            or not 1 <= max_lifetime_seconds <= 120
            or context.audience != expected_audience
            or not now < context.expires_at.timestamp() <= now + max_lifetime_seconds):
        raise AuthenticationError("Expired or mismatched connector context")


def _signed_bytes(method: str, path: str, timestamp: int, nonce: str,
                  audience: str, body: bytes) -> bytes:
    if method not in {"GET", "POST"} or not re.fullmatch(r"/api/connector/[A-Za-z0-9/_-]+", path):
        raise AuthenticationError("Unsupported connector request target")
    if type(timestamp) is not int or timestamp < 0:
        raise AuthenticationError("Invalid timestamp")
    if not re.fullmatch(r"[A-Za-z0-9_-]{32,96}", nonce):
        raise AuthenticationError("Invalid nonce")
    if audience not in {"carebalance-dr", "carebalance-labclear"}:
        raise AuthenticationError("Invalid audience")
    return "\n".join(("carebalance.connector.v1", method, path, str(timestamp),
                       nonce, audience, hashlib.sha256(body).hexdigest())).encode("ascii")


def sign_request(key: bytes, *, method: str, path: str, timestamp: int,
                 nonce: str, audience: str, body: bytes) -> str:
    if not isinstance(key, bytes) or len(key) < 32:
        raise AuthenticationError("Connector key must contain at least 32 bytes")
    return hmac.new(key, _signed_bytes(method, path, timestamp, nonce, audience, body),
                    hashlib.sha256).hexdigest()


def verify_request(key: bytes, *, method: str, path: str, timestamp: int,
                   nonce: str, audience: str, body: bytes, signature: str,
                   expected_audience: str, now: int, max_skew_seconds: int = 30) -> None:
    """Verify integrity/time/audience; nonce consumption is the caller's transaction.

    The body must be bounded and read once by the HTTP adapter. No action may run
    until the caller records this nonce in a UNIQUE-constrained persistent store.
    Keep the nonce through max(now, timestamp) + max_skew_seconds inclusive;
    keeping consumed nonces permanently is valid for this bounded POC.
    """
    if (type(now) is not int or type(timestamp) is not int
            or type(max_skew_seconds) is not int or not 1 <= max_skew_seconds <= 60
            or abs(now - timestamp) > max_skew_seconds):
        raise AuthenticationError("Expired connector request")
    if audience != expected_audience:
        raise AuthenticationError("Connector audience mismatch")
    if not isinstance(signature, str) or not re.fullmatch(r"[0-9a-f]{64}", signature):
        raise AuthenticationError("Invalid connector signature")
    expected = sign_request(key, method=method, path=path, timestamp=timestamp,
                            nonce=nonce, audience=audience, body=body)
    if not hmac.compare_digest(expected, signature):
        raise AuthenticationError("Invalid connector signature")
