import concurrent.futures
import json
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.request
import urllib.error
from pathlib import Path
from src.his_poc.service import Service, DomainError
from src.his_poc.server import make_server

class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.s=Service(Path(self.tmp.name)/'test.db'); self.actor='reviewer-demo'
    def tearDown(self): self.tmp.cleanup()
    def proposal(self): return self.s.propose(self.actor,'p-demo','e-demo')['proposal']
    def approve(self,p): return self.s.review(self.actor,p['id'],p['version'],p['action_hash'],'approve')
    def commit(self,p,key='test-key-0001'): return self.s.commit(self.actor,p['id'],p['version'],p['action_hash'],key)
    def fails(self,code,fn):
        with self.assertRaises(DomainError) as e: fn()
        self.assertEqual(e.exception.code,code)
    def test_journey_persists_review_result_audit(self):
        p=self.proposal(); self.approve(p); r=self.commit(p)
        fresh=Service(self.s.path).context(self.actor)
        self.assertEqual(len(fresh['results']),1); self.assertEqual(fresh['results'][0]['id'],r['result']['id'])
        self.assertIn('result_committed',[a['event'] for a in fresh['audit']])
        with self.s.db() as c: self.assertEqual(c.execute('SELECT count(*) FROM reviews').fetchone()[0],1)
    def test_retry_is_idempotent(self):
        p=self.proposal(); self.approve(p); a=self.commit(p); b=self.commit(p)
        self.assertEqual(a['result'],b['result']); self.assertTrue(b['replayed'])
        self.fails('IDEMPOTENCY_CONFLICT',lambda:self.s.commit(self.actor,p['id'],2,p['action_hash'],'test-key-0001'))
    def test_concurrent_retry_commits_once(self):
        p=self.proposal(); self.approve(p)
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(lambda _:self.commit(p),range(2)))
        self.assertEqual(sum(not r['replayed'] for r in results),1)
    def test_different_key_cannot_duplicate(self):
        p=self.proposal(); self.approve(p); self.commit(p)
        self.fails('NOT_APPROVED',lambda:self.commit(p,'different-key'))
    def test_scope_and_tool_boundary(self):
        self.fails('FORBIDDEN_SCOPE',lambda:self.s.propose(self.actor,'p-other','e-demo'))
        self.fails('FORBIDDEN_SCOPE',lambda:self.s.propose('viewer-demo','p-demo','e-demo'))
        with self.s.db() as c: self.fails('FORBIDDEN_SCOPE',lambda:self.s.evidence(c,self.actor,'p-other','e-demo'))
    def test_no_approval_no_commit(self):
        p=self.proposal(); self.fails('NOT_APPROVED',lambda:self.commit(p))
    def test_document_staleness(self):
        p=self.proposal(); self.approve(p)
        self.s.update_document(self.actor,'p-demo','e-demo',1,{'text':'changed'})
        self.fails('STALE_CONTEXT',lambda:self.commit(p))
    def test_encounter_status_and_version_staleness(self):
        for sql in ["UPDATE encounters SET status='cancelled'",'UPDATE encounters SET version=version+1']:
            p=self.proposal(); self.approve(p)
            with self.s.db() as c: c.execute(sql)
            self.fails('STALE_CONTEXT',lambda:self.commit(p))
            with self.s.db() as c: c.execute("UPDATE encounters SET status='open'")
    def test_edit_requires_new_review(self):
        p=self.proposal(); r=self.s.review(self.actor,p['id'],1,p['action_hash'],'edit','Reviewer correction')
        q=r['proposal']; self.assertEqual(q['version'],2)
        self.fails('STALE_PROPOSAL',lambda:self.approve(p)); self.fails('NOT_APPROVED',lambda:self.commit(q))
        self.approve(q); self.assertEqual(self.commit(q)['result']['action']['summary'],'Reviewer correction')
    def test_rejection(self):
        p=self.proposal(); self.s.review(self.actor,p['id'],1,p['action_hash'],'reject'); self.fails('NOT_APPROVED',lambda:self.commit(p))
    def test_expiry(self):
        p=self.proposal(); self.approve(p)
        with self.s.db() as c: c.execute('UPDATE proposals SET expires=0')
        self.fails('EXPIRED_PROPOSAL',lambda:self.commit(p))
    def test_revoked_permission(self):
        p=self.proposal(); self.approve(p)
        with self.s.db() as c: c.execute('UPDATE users SET active=0 WHERE id=?',(self.actor,))
        self.fails('FORBIDDEN_SCOPE',lambda:self.commit(p))
    def test_failures_abstention_and_usage_recorded(self):
        for scenario,outcome in [('timeout','timeout'),('failure','failed'),('invalid','failed'),('abstain','abstained')]:
            r=self.s.propose(self.actor,'p-demo','e-demo',scenario); self.assertEqual(r['outcome'],outcome)
        x=self.s.context(self.actor); self.assertEqual(len(x['proposals']),0); self.assertEqual(len(x['runs']),4)
        for r in x['runs']: self.assertIsNone(r['cost']); self.assertEqual(r['usage'],'null'); self.assertGreaterEqual(r['latency_ms'],0)
    def test_restricted_and_live_fail_closed(self):
        r=self.s.propose(self.actor,'p-demo','e-demo',data_class='restricted'); self.assertEqual(r['error'],'DATA_POLICY_DENIED')
        self.s.config={'inference_profile':'cloud','provider':'cloud'}
        r=self.s.propose(self.actor,'p-demo','e-demo'); self.assertEqual(r['error'],'LIVE_PROVIDER_NOT_IMPLEMENTED'); self.assertFalse(self.s.context(self.actor)['proposals'])
    def test_provider_unexpected_error_sanitized(self):
        with patch('src.his_poc.service.resolve_provider') as resolver:
            resolver.return_value.name='test'; resolver.return_value.revision='test'
            resolver.return_value.generate.side_effect=RuntimeError('sensitive credential must not persist')
            r=self.s.propose(self.actor,'p-demo','e-demo')
        self.assertEqual(r['error'],'PROVIDER_UNEXPECTED_ERROR')
        self.assertNotIn('sensitive',json.dumps(self.s.context(self.actor)))
    def test_schema_rejects_extra_actions_or_nonstring_missing_fields(self):
        for action in [{'kind':'document_completeness','summary':'test','missing_fields':[1]},
                       {'kind':'document_completeness','summary':'test','missing_fields':[],'execute':'bad'}]:
            with patch('src.his_poc.service.resolve_provider') as resolver:
                resolver.return_value.name='test'; resolver.return_value.revision='test'
                resolver.return_value.generate.return_value={'outcome':'success','action':action}
                self.assertEqual(self.s.propose(self.actor,'p-demo','e-demo')['error'],'INVALID_PROVIDER_OUTPUT')
    def test_prior_action_versions_retained(self):
        p=self.proposal()
        self.s.review(self.actor,p['id'],1,p['action_hash'],'edit','changed summary')
        versions=self.s.context(self.actor)['proposal_versions']
        self.assertEqual(len(versions),2)
        self.assertEqual(versions[0]['action'],p['action'])
    def test_nonobject_provider_response_retains_failed_attempt(self):
        for output in [['bad'],None,'bad',17]:
            with patch('src.his_poc.service.resolve_provider') as resolver:
                resolver.return_value.name='test'; resolver.return_value.revision='test'
                resolver.return_value.generate.return_value=output
                result=self.s.propose(self.actor,'p-demo','e-demo')
                self.assertEqual(result['error'],'INVALID_PROVIDER_OUTPUT')
        context=self.s.context(self.actor)
        self.assertEqual(len(context['runs']),4)
        self.assertEqual(len(context['proposals']),0)
        self.assertEqual(sum(a['event']=='ai_run' for a in context['audit']),4)
    def test_revocation_during_inference_retains_attempt(self):
        def generate(_):
            with self.s.db() as c: c.execute('UPDATE users SET active=0 WHERE id=?',(self.actor,))
            return {'outcome':'success','action':{'kind':'document_completeness','summary':'demo','missing_fields':[]}}
        with patch('src.his_poc.service.resolve_provider') as resolver:
            resolver.return_value.name='test'; resolver.return_value.revision='test'; resolver.return_value.generate.side_effect=generate
            result=self.s.propose(self.actor,'p-demo','e-demo')
        self.assertEqual(result['error'],'FORBIDDEN_SCOPE'); self.assertEqual(result['outcome'],'failed')
        with self.s.db() as c:
            self.assertEqual(c.execute('SELECT count(*) FROM proposals').fetchone()[0],0)
            self.assertEqual(c.execute('SELECT outcome FROM runs').fetchone()[0],'failed')
            self.assertEqual(c.execute("SELECT count(*) FROM audit WHERE event='ai_run'").fetchone()[0],1)
    def test_context_change_during_inference_retains_attempt(self):
        def generate(_):
            self.s.update_document(self.actor,'p-demo','e-demo',1,{'text':'changed during inference'})
            return {'outcome':'success','action':{'kind':'document_completeness','summary':'demo','missing_fields':[]}}
        with patch('src.his_poc.service.resolve_provider') as resolver:
            resolver.return_value.name='test'; resolver.return_value.revision='test'; resolver.return_value.generate.side_effect=generate
            result=self.s.propose(self.actor,'p-demo','e-demo')
        self.assertEqual(result['error'],'STALE_CONTEXT'); self.assertEqual(result['outcome'],'failed')
        context=self.s.context(self.actor)
        self.assertEqual(len(context['proposals']),0); self.assertEqual(len(context['runs']),1)
    def test_document_optimistic_update(self):
        self.s.update_document(self.actor,'p-demo','e-demo',1,{'text':'new'})
        self.fails('STALE_DOCUMENT',lambda:self.s.update_document(self.actor,'p-demo','e-demo',1,{'text':'lost update'}))
    def test_http_auth_and_full_journey(self):
        server=make_server(self.s,0); thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
        base='http://127.0.0.1:'+str(server.server_port)
        def req(path,body=None,token='demo-reviewer-token'):
            headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'}
            return json.load(urllib.request.urlopen(urllib.request.Request(base+path,data=json.dumps(body).encode() if body else None,headers=headers)))
        try:
            self.assertTrue(req('/health')['demo'])
            with urllib.request.urlopen(base+'/') as r: self.assertIn(b'EXPLICIT MOCK PROVIDER',r.read())
            with self.assertRaises(urllib.error.HTTPError) as e: req('/api/v1/context',token='wrong')
            self.assertEqual(e.exception.code,401)
            p=req('/api/v1/proposals',{'patient':'p-demo','encounter':'e-demo'})['proposal']
            b={'proposal_id':p['id'],'version':p['version'],'action_hash':p['action_hash']}
            req('/api/v1/reviews',{**b,'decision':'approve'})
            req('/api/v1/commits',{**b,'idempotency_key':'http-test-001'})
            self.assertEqual(len(req('/api/v1/context')['results']),1)
        finally: server.shutdown(); server.server_close(); thread.join()

if __name__=='__main__': unittest.main()
