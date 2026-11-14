"""Server-only connector transport. Application authorization belongs to callers."""
from __future__ import annotations

import ipaddress
import hashlib
import json
import os
import re
import secrets
import time
from dataclasses import dataclass
from typing import Literal
from urllib.parse import urlsplit

import httpx
from pydantic import Field, ValidationError, TypeAdapter

from .integration_protocol import AuthenticationError, LaunchContext, Message, SourceReference, sign_request, validate_context_lifetime


class ReviewedCell(Message):
    source_index: int = Field(ge=0, le=59)
    name: str = Field(min_length=1, max_length=100)
    value: str = Field(max_length=150)
    unit: str = Field(max_length=60)
    reference: str = Field(max_length=150)
    printed_flag: str = Field(max_length=25)


class ConfirmedCell(ReviewedCell):
    id: str = Field(pattern=r"^r[1-9][0-9]?$", max_length=3)
    status: Literal["low", "high", "within", "unknown"]


class ReviewReceipt(Message):
    revision: int = Field(ge=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    reviewer_id: str = Field(min_length=1, max_length=64)
    confirmed_at: float = Field(ge=0, allow_inf_nan=False)
    same_person_confirmed: Literal[True]
    source_revision: int = Field(ge=1)
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    corrected_source_indices: tuple[int, ...] = Field(max_length=60)


class DraftReceipt(Message):
    protocol: Literal["carebalance.connector.v1"]
    report_id: str = Field(pattern=r"^cb_report_[0-9a-f]{64}$")
    state: Literal["draft"]
    source: SourceReference
    snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    fields: tuple[ReviewedCell, ...] = Field(min_length=1, max_length=60)
    review: None


class ConfirmedReceipt(DraftReceipt):
    state: Literal["confirmed"]
    fields: tuple[ConfirmedCell, ...] = Field(min_length=1, max_length=60)
    review: ReviewReceipt


RECEIPT = TypeAdapter(DraftReceipt | ConfirmedReceipt)


class ConnectorUnavailable(RuntimeError):
    pass


class ConnectorRejected(RuntimeError):
    def __init__(self, status_code: int):
        self.status_code = status_code
        super().__init__("Specialist connector rejected the operation")


class ConnectorOutcomeUnknown(RuntimeError):
    """A retry must keep its original semantic request ID and payload."""


@dataclass(frozen=True)
class ConnectorConfig:
    audience: str
    origin: str
    key: bytes

    def __post_init__(self):
        if self.audience not in {"carebalance-labclear", "carebalance-dr"}:
            raise ConnectorUnavailable("Unsupported connector")
        parsed = urlsplit(self.origin)
        try:
            address = ipaddress.ip_address(parsed.hostname or "")
            port = parsed.port
        except ValueError:
            raise ConnectorUnavailable("Connector must use an explicit loopback IP") from None
        if (parsed.scheme != "http" or not address.is_loopback or not port
                or parsed.username is not None or parsed.password is not None
                or parsed.path not in {"", "/"} or parsed.query or parsed.fragment):
            raise ConnectorUnavailable("Connector origin is outside the dedicated loopback boundary")
        if not isinstance(self.key, bytes) or len(self.key) < 32:
            raise ConnectorUnavailable("Connector key is unavailable")

    @classmethod
    def from_environment(cls, audience: str) -> ConnectorConfig:
        prefix = {"carebalance-labclear": "HIS_LABCLEAR", "carebalance-dr": "HIS_DR"}.get(audience)
        if not prefix or os.environ.get(prefix + "_ENABLED") != "true":
            raise ConnectorUnavailable("Connector is not enabled")
        return cls(audience, os.environ.get(prefix + "_ORIGIN", ""),
                   os.environ.get(prefix + "_KEY", "").encode("utf-8"))


class LabClearClient:
    def __init__(self, config: ConnectorConfig, *, transport: httpx.BaseTransport | None = None):
        if config.audience != "carebalance-labclear":
            raise ConnectorUnavailable("Wrong connector audience")
        self.config = config
        self.transport = transport

    def _post(self, path: str, context: LaunchContext, extra: dict | None = None) -> dict:
        if context.audience != self.config.audience:
            raise ConnectorUnavailable("Wrong context audience")
        now = int(time.time())
        try:
            validate_context_lifetime(context, expected_audience=self.config.audience, now=now)
        except AuthenticationError:
            raise ConnectorUnavailable("Connector context is expired or exceeds its lifetime") from None
        payload = {"context": context.model_dump(mode="json"), **(extra or {})}
        body = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False).encode("utf-8")
        if len(body) > 256 * 1024:
            raise ConnectorUnavailable("Connector message exceeds its size limit")
        nonce = secrets.token_urlsafe(32)
        signature = sign_request(self.config.key, method="POST", path=path, timestamp=now,
                                 nonce=nonce, audience=context.audience, body=body)
        headers = {"Content-Type": "application/json", "X-CareBalance-Timestamp": str(now),
                   "X-CareBalance-Nonce": nonce, "X-CareBalance-Audience": context.audience,
                   "X-CareBalance-Signature": signature}
        try:
            with httpx.Client(transport=self.transport, timeout=httpx.Timeout(10.0, connect=2.0),
                              trust_env=False, follow_redirects=False) as client:
                with client.stream("POST", self.config.origin.rstrip("/") + path,
                                   content=body, headers=headers) as response:
                    # Never forward upstream errors, stack traces, credentials or redirects.
                    if response.status_code >= 500:
                        raise ConnectorOutcomeUnknown("Connector outcome needs reconciliation")
                    if not 200 <= response.status_code < 300:
                        raise ConnectorRejected(response.status_code)
                    if response.headers.get("content-type", "").split(";")[0].strip() != "application/json":
                        raise ConnectorOutcomeUnknown("Connector returned an invalid receipt")
                    chunks, size = [], 0
                    for chunk in response.iter_bytes():
                        size += len(chunk)
                        if size > 2 * 1024 * 1024:
                            raise ConnectorOutcomeUnknown("Connector receipt exceeds its size limit")
                        chunks.append(chunk)
            data = json.loads(b"".join(chunks))
            if not isinstance(data, dict):
                raise ConnectorOutcomeUnknown("Connector receipt must be an object")
            self._validate_receipt(context, data)
            return data
        except (httpx.HTTPError, ValueError, RecursionError):
            raise ConnectorOutcomeUnknown("Connector outcome needs reconciliation") from None

    def import_report(self, context: LaunchContext) -> dict:
        # LabClear's narrower reviewed-cell contract is an explicit capability limit.
        if any(len(row.analyte) > 100 or len(row.printed_value) > 150 for row in context.lab_values):
            raise ConnectorUnavailable("Source cells exceed LabClear's supported limits")
        return self._post("/api/connector/reports/import", context)

    @staticmethod
    def _report_id(report_id: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,96}", report_id):
            raise ConnectorUnavailable("Invalid connector report reference")
        return report_id

    @staticmethod
    def _validate_receipt(context: LaunchContext, data: dict) -> None:
        try:
            RECEIPT.validate_json(json.dumps(data, ensure_ascii=False, allow_nan=False))
        except (ValidationError, ValueError, TypeError):
            raise ConnectorOutcomeUnknown("Connector returned an invalid receipt schema") from None
        def digest(value):
            return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                             separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()
        cells = [row.model_dump(mode="json") for row in context.lab_values]
        expected_report_id = "cb_report_" + digest(context.binding_id)
        fields = data.get("fields")
        if (data.get("protocol") != context.protocol or data.get("report_id") != expected_report_id
                or data.get("source") != context.source.model_dump(mode="json")
                or data.get("snapshot_sha256") != digest(cells)
                or data.get("state") not in {"draft", "confirmed"}
                or not isinstance(fields, list) or len(fields) != len(cells)
                or any(not isinstance(row, dict) or type(row.get("source_index")) is not int
                       or row["source_index"] != index for index, row in enumerate(fields))):
            raise ConnectorOutcomeUnknown("Connector receipt does not match the requested source")
        review = data.get("review")
        if data["state"] == "draft":
            if review is not None:
                raise ConnectorOutcomeUnknown("Draft connector receipt has an invalid review")
        elif (not isinstance(review, dict) or type(review.get("revision")) is not int
              or review["revision"] < 1 or review.get("sha256") != digest(fields)
              or review.get("reviewer_id") != context.actor_id
              or review.get("source_revision") != context.source.version
              or review.get("source_sha256") != context.source.sha256
              or review.get("same_person_confirmed") is not True):
            raise ConnectorOutcomeUnknown("Connector review is not bound to the requested source")
        if data["state"] == "draft":
            expected_fields = [{"source_index": i, "name": row.analyte.strip(),
                                "value": row.printed_value.strip(), "unit": (row.unit or "").strip(),
                                "reference": (row.reference_range or "").strip(), "printed_flag": ""}
                               for i, row in enumerate(context.lab_values)]
            if fields != expected_fields:
                raise ConnectorOutcomeUnknown("Connector draft cells differ from the transferred source")
        else:
            if any(row["id"] != f"r{i + 1}" for i, row in enumerate(fields)):
                raise ConnectorOutcomeUnknown("Connector row identities changed")
            corrected = review["corrected_source_indices"]
            if (any(type(index) is not int or not 0 <= index < len(cells) for index in corrected)
                    or corrected != sorted(set(corrected))):
                raise ConnectorOutcomeUnknown("Connector correction mapping is invalid")

    def read_report(self, context: LaunchContext, report_id: str) -> dict:
        result = self._post(f"/api/connector/reports/{self._report_id(report_id)}/read", context)
        if result["report_id"] != report_id:
            raise ConnectorOutcomeUnknown("Connector report reference changed")
        return result

    def confirm_report(self, context: LaunchContext, report_id: str, *, fields: list[dict],
                       same_person_confirmed: bool) -> dict:
        if same_person_confirmed is not True:
            raise ConnectorUnavailable("Explicit same-person confirmation is required")
        try:
            reviewed = [ReviewedCell.model_validate(row) for row in fields]
            if [row.source_index for row in reviewed] != list(range(len(context.lab_values))):
                raise ValueError("Incomplete source mapping")
            normalized = [{key: value.strip() if isinstance(value, str) else value
                           for key, value in row.model_dump().items()} for row in reviewed]
        except (ValidationError, ValueError, TypeError):
            raise ConnectorUnavailable("Review all source cells in their original order") from None
        result = self._post(f"/api/connector/reports/{self._report_id(report_id)}/confirm", context,
                            {"fields": fields, "same_person_confirmed": True,
                             "source_revision": context.source.version,
                             "source_sha256": context.source.sha256})
        if result["report_id"] != report_id or result["state"] != "confirmed":
            raise ConnectorOutcomeUnknown("Connector confirmation is incomplete")
        returned = [{key: value for key, value in row.items() if key not in {"id", "status"}}
                    for row in result["fields"]]
        if returned != normalized:
            raise ConnectorOutcomeUnknown("Connector confirmed different reviewed cells")
        return result
