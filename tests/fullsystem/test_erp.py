"""PostgreSQL API acceptance for ERP workflows. Requires disposable migrated DB."""
import os,json,unittest,uuid
from pathlib import Path
from datetime import date,timedelta
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from alembic.config import Config
from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import select,func,text
from backend.app.main import app
from backend.app.db import SessionLocal,engine
from backend.app.seed import seed
from backend.app.models_erp import *
from backend.app.domains.erp import post_stock_movement,credential_allows

TRACE={}
def key():return str(uuid.uuid4())

class ERPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.getenv('HIS_TEST_DATABASE_URL'):raise unittest.SkipTest('Requires explicit disposable PostgreSQL test URL')
        command.upgrade(Config('backend/alembic.ini'),'head')
        with SessionLocal.begin() as db:seed(db,os.environ['HIS_SEED_PASSWORD'])
        cls.clients={}
        for role in ['billing','finance','finance_reviewer','inventory','procurement_approver','quality','support_reviewer','nurse','auditor','clinician','system_admin','other_registration']:
            client=TestClient(app);r=client.post('/api/v2/auth/login',json={'username':role,'password':os.environ['HIS_SEED_PASSWORD']});assert r.status_code==200,r.text
            client.headers.update({'X-CSRF-Token':r.json()['csrf_token']});cls.clients[role]=client
    @classmethod
    def tearDownClass(cls):
        Path('evidence/fullsystem').mkdir(parents=True,exist_ok=True)
        with engine.connect() as c:db_version=c.scalar(text('select version()'))
        Path('evidence/fullsystem/erp-journeys.json').write_text(json.dumps({'database':db_version,'kind':'executed_api_postgresql','browser':'NOT_RUN','journeys':TRACE},ensure_ascii=False,indent=2)+'\n')
        for c in cls.clients.values():c.close()
    def post(self,role,path,payload,expected=200,idem=None):
        r=self.clients[role].post('/api/v2'+path,json=payload,headers={'Idempotency-Key':idem or key()})
        self.assertEqual(r.status_code,expected,r.text)
        return r.json()
    def make(self,role,domain,payload):return self.post(role,f'/erp/{domain}/records',payload)
    def action(self,role,domain,row,action,**fields):return self.post(role,f'/erp/{domain}/records/{row["id"]}/actions',dict(version=row['version'],action=action,**fields))
    def invoice(self):
        price=self.post('billing','/erp/prices',{'name':'Synthetic v1','effective_from':'2026-01-01','unit_price':'1000.00'})
        charge=self.post('billing','/erp/charges',{'encounter_id':'encounter-001','source_id':key(),'label':'Synthetic service','quantity':'1','price_version_id':price['id']})
        inv=self.make('billing','D23',{'encounter_id':'encounter-001','label':'Test invoice'})
        for a in ['price','review','invoice']:inv=self.action('billing','D23',inv,a)
        return inv,charge,price
    def test_J05_money_separate_and_refund_retry(self):
        inv,charge,price=self.invoice();self.assertEqual(inv['financials']['billed'],'1000.00')
        self.post('billing','/erp/prices',{'name':'Synthetic v2','effective_from':'2026-01-01','unit_price':'2000.00'})
        self.assertEqual(self.clients['billing'].get('/api/v2/erp/D23/records/'+inv['id']).json()['billed'],'1000.00')
        claim=self.make('billing','D24',{'invoice_id':inv['id'],'payer_name':'Synthetic payer'})
        for a in ['validate','export','simulate_submit']:claim=self.action('billing','D24',claim,a)
        claim=self.action('billing','D24',claim,'remittance',approved_amount='800.00',source_key=key())
        self.assertEqual(claim['financials']['gross_received'],'0.00')
        claim=self.action('billing','D24',claim,'reconcile')
        receipt=self.make('finance','D25',{'invoice_id':inv['id'],'payer_name':'Synthetic payer','amount':'800.00'})
        receipt=self.action('finance','D25',receipt,'review');receipt=self.action('finance','D25',receipt,'post')
        receipt=self.action('finance','D25',receipt,'refund_request',amount='100.00',reason='Synthetic refund',release_allocation=False)
        rid=receipt['refunds'][0]['id']
        self.post('finance',f'/erp/D25/records/{receipt["id"]}/actions',{'version':receipt['version'],'action':'refund_approve','refund_id':rid},403)
        receipt=self.action('finance_reviewer','D25',receipt,'refund_approve',refund_id=rid)
        payload={'version':receipt['version'],'action':'refund','refund_id':rid};idem=key()
        refunded=self.post('finance','/erp/D25/records/'+receipt['id']+'/actions',payload,idem=idem)
        again=self.post('finance','/erp/D25/records/'+receipt['id']+'/actions',payload,idem=idem);self.assertEqual(refunded,again)
        for label,value in [('materials','200'),('labor','100')]:
            cost=self.make('finance','D26',{'encounter_id':'encounter-001','label':label,'amount':value,'method_version':'manual-synthetic-v1'})
            cost=self.action('finance','D26',cost,'review');self.action('finance','D26',cost,'post')
        summary=self.clients['finance'].get('/api/v2/erp/D23/records/'+inv['id']).json()['financials']
        self.assertEqual({k:summary[k] for k in ['billed','submitted','approved','gross_received','refunded','net_received','outstanding','cost']},{'billed':'1000.00','submitted':'1000.00','approved':'800.00','gross_received':'800.00','refunded':'100.00','net_received':'700.00','outstanding':'200.00','cost':'300.00'})
        journal=self.clients['finance'].get('/api/v2/erp/ledger').json()['items']
        for entry in journal:self.assertEqual(sum(Decimal(l['debit']) for l in entry['lines']),sum(Decimal(l['credit']) for l in entry['lines']))
        TRACE['J05']={'actors':['user-billing','user-finance','user-finance_reviewer'],'invoice_id':inv['id'],'claim_id':claim['id'],'receipt_id':receipt['id'],'refund_id':rid,'financials':summary,'assertions':'separate billed/submitted/approved/gross/refund/net/outstanding/cost; balanced ledger; independent refund approval; same-key replay'}
    def test_J06_procurement_partial_receipt_stock_return(self):
        purchase=self.make('inventory','D27',{'supplier_id':'supplier-demo','item_id':'item-demo','quantity':'10','unit_price':'20'})
        self.post('inventory',f'/erp/D27/records/{purchase["id"]}/actions',{'version':purchase['version'],'action':'approve'},403)
        purchase=self.action('procurement_approver','D27',purchase,'approve');purchase=self.action('inventory','D27',purchase,'record_po')
        payload={'version':purchase['version'],'action':'receive','lot_id':'lot-demo','location_id':'stock-main','quantity':'4','receipt_key':key()};idem=key()
        purchase=self.post('inventory',f'/erp/D27/records/{purchase["id"]}/actions',payload,idem=idem)
        again=self.post('inventory',f'/erp/D27/records/{purchase["id"]}/actions',payload,idem=idem);self.assertEqual(again,purchase)
        self.assertEqual(purchase['status'],'part_received')
        purchase=self.action('inventory','D27',purchase,'receive',lot_id='lot-demo',location_id='stock-main',quantity='6',receipt_key=key())
        purchase=self.action('inventory','D27',purchase,'verify_invoice');purchase=self.action('inventory','D27',purchase,'close')
        movement=self.make('inventory','D28',{'lot_id':'lot-demo','location_id':'stock-main','quantity':'-3','source_id':purchase['id']})
        movement=self.action('inventory','D28',movement,'validate');movement=self.action('inventory','D28',movement,'post')
        returned=self.action('inventory','D28',movement,'reverse',quantity='2',disposition='quarantine')
        self.post('inventory',f'/erp/D28/records/{returned["id"]}/actions',{'version':returned['version'],'action':'reverse','quantity':'2','disposition':'quarantine'},409)
        with SessionLocal() as db:
            payable=db.scalar(select(SupplierObligation).where(SupplierObligation.purchase_id==purchase['id']));self.assertEqual(payable.amount,Decimal('200'))
            original=db.get(StockMovement,movement['id']);self.assertEqual(original.quantity,Decimal('-3'))
        TRACE['J06']={'actors':['user-inventory','user-procurement_approver'],'purchase_id':purchase['id'],'receipt_ids':[x['id'] for x in purchase['receipts']],'issue_id':movement['id'],'assertions':'partial4+6 receipt10; replay stable; obligation200; issue3 quarantine return2; over-return denied'}
    def test_J09_support_quality_reports(self):
        asset=self.make('inventory','D29',{'name':'Synthetic analyzer','location_id':'location-store'})
        asset=self.action('inventory','D29',asset,'activate');asset=self.action('inventory','D29',asset,'schedule',maintenance_due='2026-11-12');asset=self.action('inventory','D29',asset,'start')
        self.post('inventory',f'/erp/D29/records/{asset["id"]}/actions',{'version':asset['version'],'action':'release'},409)
        asset=self.action('inventory','D29',asset,'record',evidence='Synthetic manual maintenance evidence');asset=self.action('quality','D29',asset,'verify');asset=self.action('inventory','D29',asset,'release')
        cycle=self.make('inventory','D31',{'kind':'cssd','asset_id':asset['id'],'cycle_code':'SYN-CYCLE-1'})
        cycle=self.action('inventory','D31',cycle,'clean');cycle=self.action('inventory','D31',cycle,'record_cycle',evidence='Synthetic cycle parameters manually reviewed')
        cycle=self.action('support_reviewer','D31',cycle,'review_release');cycle=self.action('inventory','D31',cycle,'release')
        linen=self.make('inventory','D31',{'kind':'linen','location_id':'location-ward','quantity':'5'})
        linen=self.action('inventory','D31',linen,'return_linen',returned_quantity='5');linen=self.action('inventory','D31',linen,'reconcile')
        self.assertEqual(self.clients['inventory'].get('/api/v2/erp/D31/records/'+cycle['id']).json()['status'],'released')
        work=self.make('inventory','D31',{'kind':'facility','location_id':'location-store','description':'Synthetic repair'})
        work=self.action('inventory','D31',work,'assign',assignee_id='user-inventory');work=self.action('inventory','D31',work,'verify',evidence='Inspected manually');work=self.action('inventory','D31',work,'close')
        incident=self.make('quality','D32',{'description':'Synthetic incident','asset_id':asset['id']})
        incident=self.action('quality','D32',incident,'triage',classification='synthetic maintenance');incident=self.action('quality','D32',incident,'investigate');incident=self.action('quality','D32',incident,'plan',owner_id='user-quality',action_plan='Record repair and followup')
        incident=self.action('quality','D32',incident,'evidence',evidence='Manual followup complete')
        self.post('quality',f'/erp/D32/records/{incident["id"]}/actions',{'version':incident['version'],'action':'review'},403)
        incident=self.action('support_reviewer','D32',incident,'review');incident=self.action('support_reviewer','D32',incident,'close')
        redacted=self.clients['auditor'].get('/api/v2/erp/D32/records/'+incident['id']).json();self.assertNotIn('reporter_id',redacted)
        report=self.make('quality','D33',{'name':'Encounter operational report','period_start':'2020-01-01','period_end':'2035-12-31'})
        report=self.action('quality','D33',report,'generate');self.assertGreaterEqual(report['summary']['total_encounters'],4)
        report=self.action('quality','D33',report,'review');report=self.action('quality','D33',report,'export')
        ack=self.post('quality','/erp/report-acknowledgments',{'batch_id':report['id'],'source_type':'local_stub','reference':'Synthetic local acknowledgment, not external acceptance'})
        self.assertEqual(ack['status'],'recorded_unverified_external')
        corrected=self.action('quality','D33',report,'correct')
        self.assertNotEqual(corrected['id'],report['id']);self.assertEqual(corrected['original_id'],report['id'])
        TRACE['J09']={'actors':['user-inventory','user-quality','user-support_reviewer'],'asset_id':asset['id'],'cycle_id':cycle['id'],'linen_id':linen['id'],'facility_order_id':work['id'],'incident_id':incident['id'],'report_id':report['id'],'lineage_count':len(report['lineage']),'assertions':'unverified asset unavailable; separate CSSD/linen/facility states; independent CAPA review; real encounter lineage; exported correction preserved','D38':'tested separately by operations suite'}
    def test_D30_roster_and_credential(self):
        roster=self.make('quality','D30',{'staff_id':'staff-nurse','starts_at':'2030-01-01T08:00:00Z','ends_at':'2030-01-01T16:00:00Z'})
        roster=self.action('quality','D30',roster,'review');roster=self.action('quality','D30',roster,'publish')
        other=self.make('quality','D30',{'staff_id':'staff-nurse','starts_at':'2030-01-01T09:00:00Z','ends_at':'2030-01-01T10:00:00Z'})
        self.post('quality',f'/erp/D30/records/{other["id"]}/actions',{'version':other['version'],'action':'review'},409)
        roster=self.action('nurse','D30',roster,'acknowledge');self.assertEqual(roster['status'],'acknowledged')
        staff=self.clients['quality'].get('/api/v2/erp/staff').json()['items'];staff=next(s for s in staff if s['id']=='staff-nurse')
        self.post('nurse',f'/erp/D30/records/{other["id"]}/actions',{'version':other['version'],'action':'review'},403)
        next_roster=self.make('quality','D30',{'staff_id':'staff-nurse','starts_at':'2030-01-02T08:00:00Z','ends_at':'2030-01-02T16:00:00Z'})
        next_roster=self.action('quality','D30',next_roster,'review');next_roster=self.action('quality','D30',next_roster,'publish')
        suspended=self.post('quality','/erp/staff/staff-nurse/credential',{'version':staff['version'],'status':'suspended','reason':'Synthetic negative test'})
        self.post('nurse',f'/erp/D30/records/{next_roster["id"]}/actions',{'version':next_roster['version'],'action':'acknowledge'},403)
        self.post('quality','/erp/staff/staff-nurse/credential',{'version':suspended['version'],'status':'active','reason':'Synthetic restore'})
        self.action('nurse','D30',next_roster,'acknowledge')
    def test_D35_message_dedup_order_and_retry(self):
        payload={'source_id':key(),'sequence':1,'contract_version':'his-local-event-v1','kind':'test','source_record_id':'synthetic-event'}
        row=self.make('system_admin','D35',payload);duplicate=self.make('system_admin','D35',payload);self.assertEqual(row['id'],duplicate['id'])
        row=self.action('system_admin','D35',row,'validate');row=self.action('system_admin','D35',row,'queue');row=self.action('system_admin','D35',row,'fail');row=self.action('system_admin','D35',row,'retry');row=self.action('system_admin','D35',row,'deliver');row=self.action('system_admin','D35',row,'acknowledge')
        self.assertEqual(len(row['attempts']),2);self.assertEqual(row['external_integration_status'],'NOT_CONNECTED')
        invalid=self.make('system_admin','D35',dict(payload,source_id=key(),contract_version='invalid'))
        invalid=self.action('system_admin','D35',invalid,'validate');self.assertEqual(invalid['status'],'rejected')
    def test_D36_snapshot_export_and_revoke(self):
        ds=self.make('quality','D36',{'name':'Synthetic cohort','encounter_kind':'OPD'})
        for a in ['preview','approve','freeze']:ds=self.action('quality','D36',ds,a)
        snapshot=self.clients['quality'].get('/api/v2/erp/datasets/'+ds['id']+'/export').json();self.assertGreater(len(snapshot['items']),0)
        partitions={}
        for row in snapshot['items']:
            self.assertEqual(partitions.setdefault(row['patient_id'],row['partition']),row['partition'])
        self.assertNotIn('rows',self.clients['auditor'].get('/api/v2/erp/D36/records/'+ds['id']).json())
        self.assertEqual(self.clients['auditor'].get('/api/v2/erp/datasets/'+ds['id']+'/export').status_code,403)
        with SessionLocal.begin() as db:
            from backend.app.models import Encounter
            enc=db.get(Encounter,snapshot['items'][0]['encounter_id']);enc.version+=1
        self.assertEqual(snapshot,self.clients['quality'].get('/api/v2/erp/datasets/'+ds['id']+'/export').json())
        self.assertEqual(self.clients['support_reviewer'].get('/api/v2/erp/datasets/'+ds['id']+'/export').status_code,403)
        grant=self.post('quality','/erp/dataset-access',{'dataset_id':ds['id'],'user_id':'user-support_reviewer','purpose':'Synthetic evaluation'})
        self.assertEqual(self.clients['support_reviewer'].get('/api/v2/erp/datasets/'+ds['id']+'/export').status_code,200)
        self.post('quality',f'/erp/dataset-access/{grant["id"]}/actions',{'version':grant['version'],'action':'revoke'})
        self.assertEqual(self.clients['support_reviewer'].get('/api/v2/erp/datasets/'+ds['id']+'/export').status_code,403)
        ds=self.action('quality','D36',ds,'revoke');self.assertEqual(self.clients['quality'].get('/api/v2/erp/datasets/'+ds['id']+'/export').status_code,409)
    def test_scope_role_stale_and_invalid_transition(self):
        self.post('auditor','/erp/D29/records',{'name':'Denied','location_id':'location-store'},403)
        self.post('billing','/erp/D23/records',{'encounter_id':'encounter-other','label':'Denied cross scope'},404)
        self.post('billing','/erp/D23/records',{'encounter_id':'encounter-second','label':'Denied branch'},404)
        asset=self.make('inventory','D29',{'name':'Version test','location_id':'location-store'})
        self.post('inventory',f'/erp/D29/records/{asset["id"]}/actions',{'version':99,'action':'activate'},409)
        self.post('inventory',f'/erp/D29/records/{asset["id"]}/actions',{'version':1,'action':'release'},409)
        self.assertEqual(self.clients['other_registration'].get('/api/v2/erp/D29/records/'+asset['id']).status_code,403)
    def test_stock_last_unit_concurrent_and_quarantine(self):
        lot=self.post('inventory','/erp/lots',{'item_id':'item-demo','lot_number':key(),'expiry_date':'2035-12-31','unit_cost':'1'})
        initial=self.make('inventory','D28',{'lot_id':lot['id'],'location_id':'stock-main','quantity':'1','source_id':key()})
        initial=self.action('inventory','D28',initial,'validate');self.action('inventory','D28',initial,'post')
        drafts=[]
        for role in ['inventory','procurement_approver']:
            draft=self.make(role,'D28',{'lot_id':lot['id'],'location_id':'stock-main','quantity':'-1','source_id':key()});draft=self.action(role,'D28',draft,'validate');drafts.append((role,draft))
        def issue(pair):
            role,draft=pair
            return self.clients[role].post('/api/v2/erp/D28/records/'+draft['id']+'/actions',json={'version':draft['version'],'action':'post'},headers={'Idempotency-Key':key()}).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(issue,drafts))
        self.assertEqual(sorted(results),[200,409])
        with SessionLocal() as db:
            balance=db.scalar(select(StockBalance).where(StockBalance.lot_id==lot['id']));self.assertEqual(balance.available,Decimal('0'))
    def test_adjustment_original_and_cost_reversal(self):
        inv,charge,_=self.invoice();adjusted=self.action('billing','D23',inv,'adjust',original_charge_id=charge['id'],amount='-100',reason='Synthetic credit')
        self.assertEqual(adjusted['billed'],'1000.00');self.assertEqual(adjusted['financials']['outstanding'],'900.00')
        with SessionLocal() as db:self.assertEqual(db.get(Charge,charge['id']).amount,Decimal('1000'))
        cost=self.make('finance','D26',{'encounter_id':'encounter-002','label':'Reversible cost','amount':'100','method_version':'manual-v1'})
        cost=self.action('finance','D26',cost,'review');cost=self.action('finance','D26',cost,'post');rev=self.action('finance','D26',cost,'reverse')
        self.assertEqual(rev['amount'],'100.00');self.post('finance',f'/erp/D26/records/{rev["id"]}/actions',{'version':rev['version'],'action':'reverse'},409)

    def test_reservation_count_and_zero_validation(self):
        self.post('inventory','/erp/D28/records',{'lot_id':'lot-demo','location_id':'stock-main','quantity':'0','source_id':key()},422)
        reservation=self.post('inventory','/erp/reservations',{'task_id':'task-patient-002','lot_id':'lot-demo','location_id':'stock-main','quantity':'2'})
        consumed=self.post('inventory',f'/erp/reservations/{reservation["id"]}/actions',{'version':reservation['version'],'action':'consume'})
        self.assertEqual(consumed['status'],'consumed');self.assertIsNotNone(consumed['movement_id'])
        count=self.post('inventory','/erp/counts',{'lot_id':'lot-demo','location_id':'stock-main','counted_available':'120','reason':'Synthetic physical count'})
        self.post('inventory',f'/erp/counts/{count["id"]}/actions',{'version':count['version'],'action':'approve'},403)
        count=self.post('procurement_approver',f'/erp/counts/{count["id"]}/actions',{'version':count['version'],'action':'approve'})
        count=self.post('inventory',f'/erp/counts/{count["id"]}/actions',{'version':count['version'],'action':'post'})
        self.assertEqual(count['status'],'posted')
        with SessionLocal() as db:self.assertEqual(db.scalar(select(StockBalance).where(StockBalance.lot_id=='lot-demo',StockBalance.location_id=='stock-main')).available,Decimal('120'))
    def test_database_immutable_financial_and_balanced_journal(self):
        from sqlalchemy.exc import DBAPIError
        inv,charge,_=self.invoice()
        receipt=self.make('finance','D25',{'invoice_id':inv['id'],'payer_name':'Test','amount':'10'})
        receipt=self.action('finance','D25',receipt,'review');receipt=self.action('finance','D25',receipt,'post')
        with self.assertRaises(DBAPIError):
            with SessionLocal.begin() as db:db.execute(text('update payment_receipts set amount=11 where id=:id'),{'id':receipt['id']})
        with self.assertRaises(DBAPIError):
            with SessionLocal.begin() as db:
                entry=LedgerEntry(id=key(),organization_id='org-demo',facility_id='facility-demo',source_id=key(),kind='test',status='posted');db.add(entry);db.flush()
                db.add(LedgerLine(entry_id=entry.id,account='cash',debit=10,credit=0))
        with self.assertRaises(DBAPIError):
            with SessionLocal.begin() as db:db.execute(text("update stock_movements set quantity=999 where id='movement-opening'"))
    def test_local_delivery_creates_single_reconciliation_transaction(self):
        message=self.make('system_admin','D35',{'source_id':key(),'sequence':1,'contract_version':'his-local-event-v1','kind':'test','source_record_id':'event'})
        message=self.action('system_admin','D35',message,'validate');message=self.action('system_admin','D35',message,'queue')
        payload={'version':message['version'],'action':'deliver'};idem=key()
        delivered=self.post('system_admin',f'/erp/D35/records/{message["id"]}/actions',payload,idem=idem)
        self.assertEqual(delivered,self.post('system_admin',f'/erp/D35/records/{message["id"]}/actions',payload,idem=idem))
        with SessionLocal() as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(IntegrationReceipt).where(IntegrationReceipt.message_id==message['id'])),1)
            self.assertEqual(db.scalar(select(func.count()).select_from(ReconciliationTask).where(ReconciliationTask.message_id==message['id'])),1)
    def test_budget_review_post_and_period_variance(self):
        budget=self.post('finance','/erp/budgets',{'department_id':'department-demo','period':'2026','amount':'500','method_version':'manual-v1'})
        for action in ['review','post']:budget=self.post('finance',f'/erp/budgets/{budget["id"]}/actions',{'version':budget['version'],'action':action})
        self.assertEqual(budget['status'],'posted')
        variance=self.clients['finance'].get('/api/v2/erp/budget-variance').json()['items']
        self.assertTrue(any(x['budget_id']==budget['id'] for x in variance))

if __name__=='__main__':unittest.main(verbosity=2)
