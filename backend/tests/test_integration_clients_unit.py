import json
import hashlib
import time
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

import httpx

from backend.app.integration_clients import (
    ConnectorConfig, ConnectorOutcomeUnknown, ConnectorRejected, ConnectorUnavailable, LabClearClient,
)
from backend.app.integration_protocol import verify_request
from backend.tests import test_integration_protocol_unit as protocol_fixtures


class ConnectorTransportTests(unittest.TestCase):
    key = b"synthetic-only-key-never-used-in-runtime" * 2

    def context(self):
        value = protocol_fixtures.ConnectorProtocolTests().context()
        value["expires_at"] = datetime.fromtimestamp(int(time.time()) + 60, timezone.utc).isoformat().replace("+00:00", "Z")
        return protocol_fixtures.ConnectorProtocolTests().parse(value)

    def client(self, handler):
        return LabClearClient(ConnectorConfig("carebalance-labclear", "http://127.0.0.1:18090", self.key),
                              transport=httpx.MockTransport(handler))

    @staticmethod
    def receipt(request, confirmed=False):
        context = json.loads(request.content)["context"]
        def digest(value):
            return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                             separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        fields = [{"source_index": i, "name": row["analyte"], "value": row["printed_value"],
                   "unit": row["unit"] or "", "reference": row["reference_range"] or "", "printed_flag": ""}
                  for i, row in enumerate(context["lab_values"])]
        if confirmed:
            fields = [{**row, "id": f"r{i + 1}", "status": "unknown"} for i, row in enumerate(fields)]
        return {"protocol": context["protocol"], "report_id": "cb_report_" + digest(context["binding_id"]),
                "state": "confirmed" if confirmed else "draft", "source": context["source"],
                "snapshot_sha256": digest(context["lab_values"]), "fields": fields,
                "review": {"revision": 1, "sha256": digest(fields), "reviewer_id": context["actor_id"],
                           "same_person_confirmed": True, "source_revision": context["source"]["version"],
                           "source_sha256": context["source"]["sha256"], "confirmed_at": float(time.time()),
                           "corrected_source_indices": []} if confirmed else None}

    def test_transport_authenticates_exact_body_and_retry_keeps_semantic_request(self):
        requests = []
        def receive(request):
            payload = json.loads(request.content)
            self.assertEqual(payload["context"]["lab_values"][0]["printed_value"], "< 5.0")
            headers = request.headers
            self.assertNotIn("cookie", headers)
            self.assertNotIn("authorization", headers)
            verify_request(self.key, method=request.method, path=request.url.path,
                           timestamp=int(headers["x-carebalance-timestamp"]),
                           nonce=headers["x-carebalance-nonce"], audience=headers["x-carebalance-audience"],
                           body=request.content, signature=headers["x-carebalance-signature"],
                           expected_audience="carebalance-labclear", now=int(time.time()))
            requests.append(request)
            return httpx.Response(201, json=self.receipt(request))
        client, context = self.client(receive), self.context()
        self.assertEqual(client.import_report(context)["state"], "draft")
        client.import_report(context)
        self.assertEqual(requests[0].content, requests[1].content)
        self.assertNotEqual(requests[0].headers["x-carebalance-nonce"], requests[1].headers["x-carebalance-nonce"])

    def test_origins_are_fixed_loopback_without_credentials_or_redirects(self):
        for origin in ("https://outside.test", "http://localhost:18090", "http://127.0.0.1:18090/private",
                       "http://user:pass@127.0.0.1:18090", "http://127.0.0.1:18090?next=x",
                       "http://127.0.0.1:18090#x", "http://10.0.0.1:18090"):
            with self.subTest(origin=origin), self.assertRaises(ConnectorUnavailable):
                ConnectorConfig("carebalance-labclear", origin, self.key)
        requests = []
        def redirect(request):
            requests.append(str(request.url))
            return httpx.Response(302, headers={"location": "https://outside.test/secret"})
        with self.assertRaises(ConnectorRejected):
            self.client(redirect).import_report(self.context())
        self.assertEqual(len(requests), 1)

    def test_disabled_configuration_and_narrower_cells_fail_before_network(self):
        with patch.dict("os.environ", {}, clear=True), self.assertRaises(ConnectorUnavailable):
            ConnectorConfig.from_environment("carebalance-labclear")
        context = self.context()
        oversized = context.model_copy(update={"lab_values": (context.lab_values[0].model_copy(update={"analyte": "x" * 101}),)})
        with self.assertRaises(ConnectorUnavailable):
            self.client(lambda _: self.fail("Network must not be called")).import_report(oversized)

    def test_timeout_bad_receipt_and_server_failure_are_unknown_outcomes(self):
        def timeout(request):
            raise httpx.ReadTimeout("private upstream diagnostic", request=request)
        handlers = [timeout,
                    lambda _: httpx.Response(503, text="private server stack"),
                    lambda _: httpx.Response(200, text="not a receipt"),
                    lambda _: httpx.Response(200, json=[]),
                    lambda _: httpx.Response(200, headers={"content-type": "application/json"}, content=b"broken"),
                    lambda _: httpx.Response(200, headers={"content-type": "application/json"},
                                             content=b'{"x":' * 20000 + b'0' + b'}' * 20000),
                    lambda _: httpx.Response(200, json={"oversized": "x" * (2 * 1024 * 1024)})]
        for handler in handlers:
            with self.subTest(handler=handler), self.assertRaises(ConnectorOutcomeUnknown) as error:
                self.client(handler).import_report(self.context())
            self.assertNotIn("private", str(error.exception))

    def test_confirmation_is_explicit_and_bound_to_reviewed_source(self):
        requests = []
        def receive(request):
            requests.append(request)
            return httpx.Response(200, json=self.receipt(request, confirmed=True))
        client, context = self.client(receive), self.context()
        with self.assertRaises(ConnectorUnavailable):
            client.confirm_report(context, "report_a", fields=[], same_person_confirmed=False)
        with self.assertRaises(ConnectorUnavailable):
            client.read_report(context, "../other")
        self.assertEqual(requests, [])
        fields = [{"source_index": 0, "name": "Glucose", "value": "< 5.0", "unit": "mmol/L",
                   "reference": "3.9 – 5.5", "printed_flag": ""}]
        fake_request = httpx.Request("POST", "http://test", json={"context": context.model_dump(mode="json")})
        report_id = self.receipt(fake_request)["report_id"]
        self.assertEqual(len(report_id), 74)
        client.confirm_report(context, report_id, fields=fields, same_person_confirmed=True)
        payload = json.loads(requests[0].content)
        self.assertEqual(payload["source_revision"], context.source.version)
        self.assertEqual(payload["source_sha256"], context.source.sha256)
        self.assertEqual(payload["fields"], fields)

    def test_mismatched_source_or_review_receipt_cannot_be_presented_as_success(self):
        for mutate in (
            lambda p: p.update(report_id="foreign-report"),
            lambda p: p["source"].update(version=999),
            lambda p: p.update(snapshot_sha256="b" * 64),
            lambda p: p["fields"][0].update(source_index=True),
            lambda p: p["review"].update(reviewer_id="another-actor"),
            lambda p: p["review"].update(sha256="b" * 64),
            lambda p: p.update(state=[]),
            lambda p: p.update(fields=[{"source_index": 0}]),
        ):
            def receive(request):
                result = self.receipt(request, confirmed=True)
                mutate(result)
                return httpx.Response(200, json=result)
            with self.subTest(mutate=mutate), self.assertRaises(ConnectorOutcomeUnknown):
                self.client(receive).import_report(self.context())

    def test_self_consistent_but_different_confirmed_cells_are_rejected(self):
        def receive(request):
            receipt = self.receipt(request, confirmed=True)
            receipt["fields"][0]["value"] = "999"
            receipt["review"]["sha256"] = hashlib.sha256(json.dumps(
                receipt["fields"], ensure_ascii=False, sort_keys=True,
                separators=(",", ":")).encode()).hexdigest()
            return httpx.Response(200, json=receipt)
        context = self.context()
        fake = httpx.Request("POST", "http://test", json={"context": context.model_dump(mode="json")})
        baseline = self.receipt(fake)
        with self.assertRaises(ConnectorOutcomeUnknown):
            self.client(receive).confirm_report(context, baseline["report_id"],
                                               fields=baseline["fields"], same_person_confirmed=True)


if __name__ == "__main__":
    unittest.main()
