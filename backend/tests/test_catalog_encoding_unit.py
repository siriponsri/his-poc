"""Typed frontend generation preserves Thai, scoped options and integer contracts."""
import json,pathlib,runpy,shutil,tempfile,unittest
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[2]

class CatalogEncodingTests(unittest.TestCase):
 def test_sync_under_thai_legacy_locale_retains_utf8_contracts(self):
  original_open=pathlib.Path.open
  def legacy_locale_open(path,mode='r',buffering=-1,encoding=None,errors=None,newline=None):
   if 'b' not in mode and encoding is None:encoding='cp874'
   return original_open(path,mode,buffering,encoding,errors,newline)
  files=['apps/web/scripts/sync_full_catalog.py','apps/web/src/data/full-domains.json','backend/app/domains/clinical_catalog.json','backend/app/domains/erp_catalog.json']
  with tempfile.TemporaryDirectory() as directory:
   isolated=pathlib.Path(directory)
   for relative in files:
    target=isolated/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/relative,target)
   with patch.object(pathlib.Path,'open',legacy_locale_open):
    runpy.run_path(str(isolated/'apps/web/scripts/sync_full_catalog.py'),run_name='__main__')
   generated=json.loads((isolated/'apps/web/src/data/resource-catalog.json').read_text(encoding='utf-8'))
   source=json.loads((isolated/'backend/app/domains/clinical_catalog.json').read_text(encoding='utf-8'))['items']
   byid={row['id']:row for row in generated}
   self.assertEqual(len(generated),38)
   for row in source:
    self.assertEqual(byid[row['id']]['resources'][0]['label'],row['name_th'])
   self.assertTrue(any('\u0e01'<=char<='\u0e7f' for row in source for char in row['name_th']))
   dispense=next(action for action in byid['D08']['resources'][0]['actions'] if action['name']=='dispensed')
   location=next(field for field in dispense['fields'] if field['name']=='location_id')
   self.assertEqual(location['source'],'erp/options/stock-locations')
   sequence=next(field for field in byid['D35']['resources'][0]['fields'] if field['name']=='sequence')
   self.assertEqual(sequence['type'],'integer')
   self.assertEqual(sequence['min'],1)
   self.assertTrue(sequence['required'])
   erp=json.loads((isolated/'backend/app/domains/erp_catalog.json').read_text(encoding='utf-8'))
   for domain in erp:
    resources=byid[domain['id']]['resources']
    self.assertNotEqual(resources[0].get('detailPath'),False)
    for sub in domain.get('subresources',[]):
     generated_sub=next(resource for resource in resources if resource['id']==domain['id']+'-'+sub['name'])
     self.assertIs(generated_sub.get('detailPath'),False,generated_sub['id'])
     self.assertEqual(generated_sub['path'],sub['endpoint'].removeprefix('/api/v2/'))

if __name__=='__main__':unittest.main()
