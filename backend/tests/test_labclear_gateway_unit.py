"""Pure and controlled-session component checks, never PostgreSQL acceptance."""
from copy import deepcopy
from datetime import timedelta
from types import SimpleNamespace
import json
import unittest
from unittest.mock import Mock, patch

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from backend.app import integrations as gateway
from backend.app.auth import Actor
from backend.app.common import authorization_hash, digest, utcnow
from backend.app.integration_clients import ConnectorOutcomeUnknown, ConnectorRejected
from backend.app.models_integrations import ConnectorAttempt, ConnectorBinding, ConnectorExchange


def actor():
    return Actor("actor", "author", "Synthetic author", "org", "facility", {"laboratory"},
                 {"D10.write", "D10.read"}, None, "session", None)


def clinical_rows():
    scope = dict(organization_id="org", facility_id="facility", patient_id="patient", encounter_id="encounter")
    task = SimpleNamespace(**scope, id="task", domain="D10", kind="labclear_review", status="open", version=1)
    source = SimpleNamespace(**scope, id="source", order_id="order", order_version=1, version=5, status="released",
        analyte=" ALT ", result_value="< 5.0", unit="U/L", reference_range=None, specimen_type="serum", accession="ACC-synthetic")
    order = SimpleNamespace(**scope, id="order", kind="lab")
    encounter = SimpleNamespace(id="encounter", patient_id="patient", status="in_consult", version=2)
    return task, source, order, encounter


def binding():
    task, source, order, encounter = clinical_rows()
    snapshot = gateway.lab_snapshot(source)
    return ConnectorBinding(id="binding_0000000001", connector="labclear", organization_id="org", facility_id="facility",
        actor_id="actor", session_id="session", patient_id="patient", encounter_id="encounter", task_id="task",
        source_id="source", source_version=5, source_hash=digest(snapshot), source_snapshot=snapshot,
        lab_values=gateway.lab_values(snapshot), external_report_id=None, state="reserved", created_at=utcnow())


class ControlledSession:
    """Records transaction sequencing; not an SQL or authorization substitute."""
    def __init__(self, scalars=()):
        self.scalars_to_return = list(scalars)
        self.added = []
        self.objects = {}
        self.closed = False
        self.commits = 0

    def scalar(self, query): return self.scalars_to_return.pop(0)
    def add(self, value):
        self.added.append(value)
        self.objects[(type(value), value.id)] = value
    def get(self, kind, id, **kwargs): return self.objects[(kind, id)]
    def flush(self): pass
    def commit(self): self.commits += 1
    def close(self): self.closed = True
    def rollback(self): pass


class GatewayPureTests(unittest.TestCase):
    def test_exact_source_cells_and_hash_detect_revision_changes(self):
        _, source, _, _ = clinical_rows()
        snapshot = gateway.lab_snapshot(source)
        self.assertEqual(gateway.lab_values(snapshot), [{"analyte": " ALT ", "printed_value": "< 5.0", "unit": "U/L", "reference_range": None}])
        before = digest(snapshot)
        for key, value in [("unit", "IU/L"), ("result_value", "5.0"), ("version", 6), ("reference_range", "0-40")]:
            changed = {**snapshot, key: value}
            self.assertNotEqual(before, digest(changed))

    def test_source_capability_rejects_without_truncation(self):
        snapshot = binding().source_snapshot
        for key, value in [("analyte", "a" * 101), ("result_value", "1" * 151), ("result_value", None), ("analyte", " ")]:
            with self.subTest(key=key), self.assertRaises(HTTPException) as exc:
                gateway.lab_values({**snapshot, key: value})
            self.assertEqual(exc.exception.status_code, 422)

    def test_import_and_confirmation_dto_do_not_accept_owner_url_or_coercion(self):
        valid = {"patient_id": "patient", "encounter_id": "encounter", "task_id": "task", "source_id": "source", "source_version": 5}
        gateway.ImportInput(**valid)
        for changed in [{**valid, "source_version": True}, {**valid, "source_version": "5"},
                        {**valid, "owner": "admin"}, {**valid, "upstream_url": "http://outside.invalid"}]:
            with self.assertRaises(ValidationError): gateway.ImportInput(**changed)
        review = {"fields": [{"source_index": 0, "name": "ALT", "value": "42", "unit": "U/L", "reference": "", "printed_flag": ""}],
                  "same_person_confirmed": True, "source_version": 5, "source_sha256": "a" * 64}
        gateway.ConfirmInput(**review)
        with self.assertRaises(ValidationError): gateway.ConfirmInput(**{**review, "same_person_confirmed": "true"})

    def test_context_and_output_keep_opaque_long_external_ids(self):
        row = binding()
        context = gateway.context_for(row, "request_0000000001")
        self.assertEqual(context.source.sha256, row.source_hash)
        self.assertEqual(context.lab_values[0].printed_value, "< 5.0")
        self.assertEqual(context.patient_id, row.patient_id)
        self.assertTrue(context.model_dump(mode="json")["expires_at"].endswith("Z"))
        self.assertLessEqual((context.expires_at - utcnow()).total_seconds(), 90)
        row.external_report_id = "cb_report_" + "a" * 64
        self.assertEqual(len(gateway.binding_dto(row)["external_report_id"]), 74)
        ddl = str(CreateTable(ConnectorBinding.__table__).compile(dialect=postgresql.dialect()))
        self.assertIn("external_report_id VARCHAR(128)", ddl)
        self.assertIn("fk_connector_binding_encounter_scope", ddl)
        self.assertIn("uq_connector_binding_source", ddl)

    def test_default_transport_remains_disabled(self):
        with patch.dict("os.environ", {}, clear=True), self.assertRaises(HTTPException) as exc:
            gateway.resolve_client()
        self.assertEqual(exc.exception.status_code, 503)


class GatewayAuthorizationComponentTests(unittest.TestCase):
    def authorize(self, mutate=lambda *args: None, write=True):
        user = actor()
        task, source, order, encounter = clinical_rows()
        mutate(user, task, source, order, encounter)
        db = ControlledSession([task, source, order])
        with patch.object(gateway, "revalidate_actor", side_effect=lambda db, user: user), \
             patch.object(gateway, "scoped_patient"), patch.object(gateway, "scoped_encounter", return_value=encounter):
            return gateway._authorize_source(db, user, "patient", "encounter", "task", "source", write=write, version=5)

    def test_review_task_is_separate_from_completed_order_task(self):
        result = self.authorize(lambda user, task, source, order, encounter: setattr(order, "task_id", "completed-original-task"))
        self.assertEqual(result[1].kind, "labclear_review")

    def test_permission_and_each_explicit_row_scope(self):
        mutations = [lambda a, t, s, o, e: a.permissions.clear(),
                     lambda a, t, s, o, e: setattr(t, "patient_id", "other"),
                     lambda a, t, s, o, e: setattr(s, "encounter_id", "other"),
                     lambda a, t, s, o, e: setattr(o, "facility_id", "other"),
                     lambda a, t, s, o, e: setattr(e, "patient_id", "other"),
                     lambda a, t, s, o, e: setattr(t, "domain", "D11"),
                     lambda a, t, s, o, e: setattr(t, "kind", "lab"),
                     lambda a, t, s, o, e: setattr(o, "kind", "imaging"),
                     lambda a, t, s, o, e: setattr(s, "status", "preliminary"),
                     lambda a, t, s, o, e: setattr(s, "version", 6)]
        for mutation in mutations:
            with self.subTest(mutation=mutation), self.assertRaises(HTTPException): self.authorize(mutation)

    def test_closed_mutation_but_completed_task_historical_read(self):
        mutation = lambda a, t, s, o, e: (setattr(t, "status", "completed"), setattr(e, "status", "closed"))
        with self.assertRaises(HTTPException): self.authorize(mutation, write=True)
        self.assertEqual(self.authorize(mutation, write=False)[1].status, "completed")
        with self.assertRaises(HTTPException):
            self.authorize(lambda a, t, s, o, e: setattr(t, "status", "cancelled"), write=False)


class GatewayReservationComponentTests(unittest.TestCase):
    def reserve(self, prior=None, operation="import", payload=None):
        responses = [prior]
        if prior is None and operation in {"import", "confirm"}:
            responses.append(None)  # No different-key unresolved mutation.
        db = ControlledSession(responses)
        row, user = binding(), actor()
        task, _, _, encounter = clinical_rows()
        with patch.object(gateway, "_lock"), patch.object(gateway, "audit"):
            result = gateway._reserve_attempt(db, user, row, task, encounter, operation, "key", payload or {})
        return db, user, row, task, encounter, result

    def test_reservation_commits_and_closes_before_transport(self):
        db, user, row, task, encounter, reservation = self.reserve()
        self.assertIsInstance(reservation, gateway.Reservation)
        self.assertEqual(db.commits, 1)
        self.assertTrue(db.closed)
        self.assertEqual(len([value for value in db.added if isinstance(value, ConnectorExchange)]), 1)
        attempt = next(value for value in db.added if isinstance(value, ConnectorAttempt))
        self.assertEqual(attempt.request_id, reservation.context.request_id)
        self.assertEqual(attempt.lease_id, reservation.exchange_id)

    def test_unknown_retry_reuses_request_id_and_original_payload(self):
        db, user, row, task, encounter, first = self.reserve()
        prior = next(value for value in db.added if isinstance(value, ConnectorAttempt))
        prior.status = "unknown"
        retried = self.reserve(prior)[-1]
        self.assertEqual(retried.attempt_id, first.attempt_id)
        self.assertEqual(retried.context.request_id, first.context.request_id)
        self.assertNotEqual(retried.exchange_id, first.exchange_id)
        prior.status = "succeeded"
        prior.response = {"original": "immutable receipt"}
        self.assertEqual(self.reserve(prior)[-1], prior.response)

    def test_live_lease_blocks_second_http_and_changed_key_payload_conflicts(self):
        db, user, row, task, encounter, reservation = self.reserve()
        prior = next(value for value in db.added if isinstance(value, ConnectorAttempt))
        pending = self.reserve(prior)[-1]
        self.assertEqual(pending.status_code, 202)
        self.assertEqual(json.loads(pending.body)["outcome"], "running")
        with self.assertRaises(HTTPException): self.reserve(prior, payload={"different": "payload"})

    def test_actual_receipt_recorded_before_authorization_race_denies_response(self):
        for status, code in [(401, "SESSION_REVOKED"), (409, "CONNECTOR_SOURCE_STALE")]:
            db, user, row, task, encounter, reservation = self.reserve()
            receipt = {"report_id": "cb_report_" + "a" * 64, "private": "synthetic values"}
            client = Mock()
            client.import_report.side_effect = lambda ctx: receipt if db.closed else self.fail("transaction held across HTTP")
            with patch.object(gateway, "_store_exchange") as store, \
                 patch.object(gateway, "_owned_binding", side_effect=HTTPException(status, detail={"code": code})), \
                 patch.object(gateway, "_quarantine") as quarantine, self.assertRaises(HTTPException) as denied:
                gateway._execute(db, user, client, reservation)
            self.assertEqual(denied.exception.status_code, status)
            store.assert_called_once_with(reservation, "succeeded", receipt, None)
            quarantine.assert_called_once_with(reservation, code)

    def test_unknown_outcome_is_durable_and_reconcilable(self):
        db, user, row, task, encounter, reservation = self.reserve()
        client = Mock()
        client.import_report.side_effect = ConnectorOutcomeUnknown("timeout")
        with patch.object(gateway, "_store_exchange") as store, \
             patch.object(gateway, "_owned_binding", return_value=(row, task, encounter)), patch.object(gateway, "audit"):
            response = gateway._execute(db, user, client, reservation)
        self.assertEqual(response.status_code, 202)
        self.assertEqual(json.loads(response.body)["outcome"], "unknown")
        store.assert_called_once_with(reservation, "unknown", None, "LABCLEAR_OUTCOME_UNKNOWN")

    def test_read_retries_need_fresh_authorization_without_a_mutation_key(self):
        row = binding()
        attempt = ConnectorAttempt(id="attempt", operation="read", status="unknown")
        self.assertFalse(json.loads(gateway._pending(row, attempt).body)["retry_same_key"])
        attempt.operation = "confirm"
        self.assertTrue(json.loads(gateway._pending(row, attempt).body)["retry_same_key"])

    def test_different_key_pending_mutation_fails_before_reservation(self):
        row, user = binding(), actor()
        task, _, _, encounter = clinical_rows()
        db = ControlledSession([None, ConnectorAttempt(id="existing", status="unknown", operation="confirm")])
        with patch.object(gateway, "_lock"), patch.object(gateway, "audit"), self.assertRaises(HTTPException) as exc:
            gateway._reserve_attempt(db, user, row, task, encounter, "import", "new-key", {})
        self.assertEqual(exc.exception.detail, {"code": "CONNECTOR_PENDING_RECOVERY_REQUIRED", "binding_id": row.id})
        self.assertEqual(db.commits, 0)
        self.assertEqual(db.added, [])


if __name__ == "__main__": unittest.main()
