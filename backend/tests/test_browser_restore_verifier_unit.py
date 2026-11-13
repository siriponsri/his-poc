"""Read-only browser restore verifier target and exact-record binding safety."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import MagicMock,patch

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('browser_restore_verifier',ROOT/'scripts/verify_browser_restore.py')
verifier=importlib.util.module_from_spec(spec);spec.loader.exec_module(verifier)

class BrowserRestoreVerifierTests(unittest.TestCase):
 def test_connection_enforces_read_only_and_closes_if_server_does_not_confirm_it(self):
  connection=MagicMock()
  connection.execute.return_value.fetchone.return_value=('off',)
  with patch.object(verifier.psycopg,'connect',return_value=connection) as connect:
   with self.assertRaisesRegex(ValueError,'READ_ONLY_TRANSACTION_REQUIRED'):
    verifier.readonly_connection('postgresql://synthetic@127.0.0.1/his_test')
  self.assertEqual(connect.call_args.kwargs['options'],'-c default_transaction_read_only=on')
  self.assertIn('READ ONLY',connection.execute.call_args_list[0].args[0])
  connection.close.assert_called_once()

 def test_active_and_arbitrary_targets_are_rejected_before_connection(self):
  source='postgresql://synthetic:private-placeholder@127.0.0.1/his_restore_'+'a'*32
  with self.assertRaisesRegex(ValueError,'ACTIVE_TARGET_FORBIDDEN'):
   verifier.isolated_target_url(source,'his_restore_'+'a'*32)
  for target in ['production','his_restore_other','his_restore_'+('b'*32)+'/extra',None]:
   with self.assertRaises(ValueError):verifier.isolated_target_url(source,target)
  target=verifier.isolated_target_url(source,'his_restore_'+'b'*32)
  self.assertTrue(target.endswith('/his_restore_'+'b'*32))

 def test_exact_browser_ids_map_to_fixed_tables_and_missing_ids_fail_closed(self):
  report={'status':'PASS','journeys':{journey:{'status':'PASS','record_ids':{}} for journey in ['J01','J05','J08']}}
  report['journeys']['J01']['record_ids']={'patient_id':'patient-ui','encounter_id':'encounter-ui','document_id':'document-ui','result_id':'result-ui'}
  report['journeys']['J05']['record_ids']={'receipt_id':'receipt-ui','invoice_id':'invoice-ui'}
  report['journeys']['J08']['record_ids']={'study_id':'study-ui','document_id':'imaging-doc-ui','file_sha256':'a'*64}
  records,sha=verifier.browser_records(report)
  self.assertEqual(len(records),8);self.assertEqual(sha,'a'*64)
  self.assertIn({'journey':'J08','field':'study_id','table':'clinical_imaging','id':'study-ui'},records)
  from backend.app.models_erp import Receipt
  self.assertIn({'journey':'J05','field':'receipt_id','table':Receipt.__tablename__,'id':'receipt-ui'},records)
  del report['journeys']['J01']['record_ids']['result_id']
  with self.assertRaisesRegex(ValueError,'MISSING_BROWSER_RECORD_J01_result_id'):
   verifier.browser_records(report)

if __name__=='__main__':unittest.main()
