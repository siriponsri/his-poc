"""Exported ERP input contracts match current runtime request models, without a DB."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('contract_export',ROOT/'scripts/export_contracts_v2.py')
exporter=importlib.util.module_from_spec(spec);spec.loader.exec_module(exporter)
from backend.app.domains.erp import CREATES,ACTIONS


class ContractExportTests(unittest.TestCase):
 def test_all_erp_input_contracts_export_current_create_and_action_schemas(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);(root/'docs').mkdir()
   with patch.object(exporter,'ROOT',root),contextlib.redirect_stdout(io.StringIO()):
    exporter.main()
   actual=json.loads((root/'contracts/v2/erp-inputs.json').read_text(encoding='utf-8'))
   self.assertEqual(len(actual),13)
   self.assertEqual(set(actual),set(CREATES))
   self.assertEqual(set(actual),set(ACTIONS))
   for domain in CREATES:
    self.assertEqual(set(actual[domain]),{'create','action'})
    self.assertEqual(actual[domain]['create'],CREATES[domain].model_json_schema(),domain)
    self.assertEqual(actual[domain]['action'],ACTIONS[domain].model_json_schema(),domain)
   self.assertEqual(actual['D35']['create']['properties']['sequence']['type'],'integer')
   self.assertEqual(actual['D35']['create']['properties']['sequence']['minimum'],1)


if __name__=='__main__':unittest.main()
