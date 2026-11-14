import json
import unittest
from datetime import datetime, timezone

from pydantic import ValidationError

from backend.app.integration_protocol import (
    AuthenticationError, LaunchContext, canonical_bytes, sign_request, verify_request,
    validate_context_lifetime,
)


class ConnectorProtocolTests(unittest.TestCase):
    def context(self):
        return {
            "protocol": "carebalance.connector.v1", "request_id": "r" * 32,
            "audience": "carebalance-labclear", "binding_id": "b" * 32,
            "organization_id": "org-a", "facility_id": "facility-a",
            "actor_id": "clinician-a", "patient_id": "patient-a",
            "encounter_id": "visit-a", "task_id": "task-a",
            "source": {"domain": "D10", "record_id": "lab-a", "version": 4, "sha256": "a" * 64},
            "purpose": "lab-value-review", "expires_at": "2026-11-14T10:00:00Z",
            "lab_values": [{"analyte": "Glucose", "printed_value": "< 5.0",
                            "unit": "mmol/L", "reference_range": "3.9 – 5.5"}],
        }

    def parse(self, value):
        return LaunchContext.model_validate_json(json.dumps(value, ensure_ascii=False))

    def test_printed_values_are_lossless_and_canonical(self):
        payload = self.context()
        ctx = self.parse(payload)
        self.assertEqual(ctx.lab_values[0].printed_value, "< 5.0")
        self.assertEqual(ctx.lab_values[0].reference_range, "3.9 – 5.5")
        self.assertEqual(ctx.expires_at, datetime(2026, 11, 14, 10, tzinfo=timezone.utc))
        self.assertEqual(canonical_bytes(ctx), canonical_bytes(self.parse(dict(reversed(list(payload.items()))))))

    def test_unknown_fields_and_coercion_rejected(self):
        for mutate in (
            lambda p: p.update(admin=True),
            lambda p: p["source"].update(version=True),
            lambda p: p["source"].update(version="4"),
            lambda p: p["lab_values"][0].update(printed_value=5.0),
            lambda p: p.update(expires_at="2026-11-14T10:00:00"),
            lambda p: p.update(expires_at="0"),
            lambda p: p.update(expires_at=123456),
            lambda p: p.update(expires_at="2026-11-14T17:00:00+07:00"),
            lambda p: p.update(protocol="carebalance.connector.v2"),
            lambda p: p["source"].update(sha256="A" * 64),
        ):
            with self.subTest(mutate=mutate):
                payload = self.context()
                mutate(payload)
                with self.assertRaises(ValidationError):
                    self.parse(payload)

    def test_connector_must_match_source_and_purpose(self):
        for mutate in (
            lambda p: p.update(audience="carebalance-dr"),
            lambda p: p["source"].update(domain="D11"),
            lambda p: p.update(lab_values=[]),
            lambda p: p.update(purpose="retinal-screening-review"),
        ):
            payload = self.context()
            mutate(payload)
            with self.assertRaises(ValidationError):
                self.parse(payload)
        payload = self.context()
        payload.update(audience="carebalance-dr", purpose="retinal-screening-review", lab_values=[])
        payload["source"]["domain"] = "D11"
        self.assertEqual(self.parse(payload).source.domain, "D11")

    def test_context_and_nested_cells_immutable(self):
        ctx = self.parse(self.context())
        with self.assertRaises(ValidationError):
            ctx.patient_id = "different-patient"
        with self.assertRaises(ValidationError):
            ctx.lab_values[0].printed_value = "different-value"

    def test_context_lifetime_and_capacity_boundaries(self):
        ctx = self.parse(self.context())
        expiry = int(ctx.expires_at.timestamp())
        for now in (expiry - 1, expiry - 120):
            validate_context_lifetime(ctx, expected_audience=ctx.audience, now=now)
        for now in (expiry, expiry + 1, expiry - 121):
            with self.assertRaises(AuthenticationError):
                validate_context_lifetime(ctx, expected_audience=ctx.audience, now=now)
        with self.assertRaises(AuthenticationError):
            validate_context_lifetime(ctx, expected_audience="carebalance-dr", now=expiry - 1)
        payload = self.context()
        payload["lab_values"] *= 60
        self.assertEqual(len(self.parse(payload).lab_values), 60)
        payload["lab_values"].append(payload["lab_values"][0])
        with self.assertRaises(ValidationError):
            self.parse(payload)

    def request(self):
        return dict(method="POST", path="/api/connector/exchange", timestamp=123456,
                    nonce="n" * 32, audience="carebalance-labclear",
                    body=canonical_bytes(self.parse(self.context())))

    def test_signature_binds_every_request_dimension(self):
        key = b"synthetic-test-key-only-no-runtime" * 2
        request = self.request()
        signature = sign_request(key, **request)
        verify_request(key, **request, signature=signature, expected_audience=request["audience"], now=123456)
        for field, value in (
            ("method", "GET"), ("path", "/api/connector/reports"),
            ("timestamp", 123457), ("nonce", "x" * 32),
            ("audience", "carebalance-dr"), ("body", request["body"] + b" "),
        ):
            changed = {**request, field: value}
            with self.subTest(field=field), self.assertRaises(AuthenticationError):
                verify_request(key, **changed, signature=signature,
                               expected_audience=changed["audience"], now=123456)

    def test_time_audience_keys_and_target_validation(self):
        key = b"synthetic-test-key-only-no-runtime" * 2
        request = self.request()
        signature = sign_request(key, **request)
        for overrides in (
            {"now": 123487}, {"now": 123425},
            {"expected_audience": "carebalance-dr"}, {"signature": "z" * 64},
            {"max_skew_seconds": 600}, {"timestamp": True},
        ):
            kwargs = {**request, "signature": signature,
                      "expected_audience": request["audience"], "now": 123456, **overrides}
            with self.subTest(overrides=overrides), self.assertRaises(AuthenticationError):
                verify_request(key, **kwargs)
        for path in ("https://other/api/connector/exchange", "/api/connector/exchange?patient=a",
                     "/api/connector/../admin", "/api/connector/exchange\nheader"):
            with self.subTest(path=path), self.assertRaises(AuthenticationError):
                sign_request(key, **{**request, "path": path})
        with self.assertRaises(AuthenticationError):
            sign_request(b"short", **request)


if __name__ == "__main__":
    unittest.main()
