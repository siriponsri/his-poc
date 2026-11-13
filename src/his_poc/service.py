import hashlib
import json
import sqlite3
import time
import uuid
from contextlib import contextmanager
from .providers import resolve_provider, ProviderError

# This v1 demo has one named document-completeness workflow. This is an explicit
# scope restriction, not generic encounter-to-task routing. Multi-task support
# must persist the target task on the proposal before expanding this mapping.
DEMO_DOCUMENT_COMPLETENESS_TARGET = {
    'patient': 'p-demo', 'encounter': 'e-demo', 'task': 'task-demo'
}
MAX_ABSTAIN_REASON_LENGTH = 1000

def encoded(x): return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
def digest(x): return hashlib.sha256(encoded(x).encode()).hexdigest()
def ident(): return str(uuid.uuid4())

class DomainError(Exception):
    def __init__(self, code, status=409): self.code, self.status = code, status; super().__init__(code)

def require_version(value):
    # bool is an int subclass in Python, but is not a JSON integer version.
    if type(value) is not int or value < 1:
        raise DomainError('INVALID_VERSION', 400)

class Service:
    def __init__(self, path, config=None):
        self.path = str(path)
        self.config = config or {'inference_profile': 'mock_demo'}
        with self.db() as c:
            new_task_table = not c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='tasks'").fetchone()
            schema = '''
            CREATE TABLE IF NOT EXISTS patients(id TEXT PRIMARY KEY, tenant TEXT, label TEXT);
            CREATE TABLE IF NOT EXISTS encounters(id TEXT PRIMARY KEY, patient TEXT, version INTEGER, status TEXT);
            CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY, tenant TEXT, role TEXT, patient TEXT, active INTEGER);
            CREATE TABLE IF NOT EXISTS documents(id TEXT PRIMARY KEY, encounter TEXT, version INTEGER, content TEXT);
            CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY, encounter TEXT, status TEXT);
            CREATE TABLE IF NOT EXISTS proposals(id TEXT PRIMARY KEY, patient TEXT, encounter TEXT, version INTEGER, action TEXT, action_hash TEXT, snapshot TEXT, status TEXT, expires REAL, run_id TEXT);
            CREATE TABLE IF NOT EXISTS proposal_versions(proposal TEXT, version INTEGER, action TEXT, action_hash TEXT, PRIMARY KEY(proposal,version));
            CREATE TABLE IF NOT EXISTS reviews(id TEXT PRIMARY KEY, proposal TEXT, version INTEGER, action_hash TEXT, reviewer TEXT, decision TEXT, edits TEXT, created REAL);
            CREATE TABLE IF NOT EXISTS results(id TEXT PRIMARY KEY, proposal TEXT UNIQUE, patient TEXT, encounter TEXT, action TEXT, review TEXT, created REAL);
            CREATE TABLE IF NOT EXISTS idempotency(key TEXT PRIMARY KEY, actor TEXT, payload_hash TEXT, result TEXT);
            CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY, encounter TEXT, outcome TEXT, provider TEXT, model_revision TEXT, latency_ms REAL, usage TEXT, cost REAL, error TEXT, demo INTEGER, abstain_reason TEXT);
            CREATE TABLE IF NOT EXISTS audit(id TEXT PRIMARY KEY, actor TEXT, event TEXT, entity TEXT, details TEXT, created REAL);
            '''
            # Keep initialization/migration inside db()'s transaction;
            # executescript would implicitly commit before the migration.
            for statement in schema.split(';'):
                if statement.strip(): c.execute(statement)
            if 'abstain_reason' not in {row['name'] for row in c.execute('PRAGMA table_info(runs)')}:
                # Additive v0.1.0 migration: existing runs retain NULL rather
                # than inventing a reason that was never recorded.
                c.execute('ALTER TABLE runs ADD COLUMN abstain_reason TEXT')
            c.execute('INSERT OR IGNORE INTO patients VALUES(?,?,?)', ('p-demo','t-demo','ผู้ป่วยสังเคราะห์ DEMO'))
            c.execute('INSERT OR IGNORE INTO encounters VALUES(?,?,?,?)', ('e-demo','p-demo',1,'open'))
            c.execute('INSERT OR IGNORE INTO users VALUES(?,?,?,?,?)', ('reviewer-demo','t-demo','reviewer','p-demo',1))
            c.execute('INSERT OR IGNORE INTO users VALUES(?,?,?,?,?)', ('viewer-demo','t-demo','viewer','p-demo',1))
            c.execute('INSERT OR IGNORE INTO documents VALUES(?,?,?,?)', ('d-demo','e-demo',1,encoded({'text':'Synthetic encounter document', 'author':'demo-author'})))
            target = DEMO_DOCUMENT_COMPLETENESS_TARGET
            if new_task_table:
                # A deleted target in an existing DB is an unavailable task;
                # restarting the service must not silently recreate/reopen it.
                c.execute('INSERT INTO tasks VALUES(?,?,?)', (target['task'],target['encounter'],'open'))

    @contextmanager
    def db(self):
        c = sqlite3.connect(self.path, timeout=5)
        c.row_factory = sqlite3.Row
        c.execute('PRAGMA foreign_keys=ON')
        c.execute('BEGIN IMMEDIATE')
        try: yield c; c.commit()
        except: c.rollback(); raise
        finally: c.close()

    def audit(self,c,actor,event,entity,details):
        c.execute('INSERT INTO audit VALUES(?,?,?,?,?,?)',(ident(),actor,event,entity,encoded(details),time.time()))

    def authorize(self,c,actor,patient,encounter,write=False):
        u=c.execute('SELECT * FROM users WHERE id=?',(actor,)).fetchone()
        p=c.execute('SELECT * FROM patients WHERE id=?',(patient,)).fetchone()
        e=c.execute('SELECT * FROM encounters WHERE id=?',(encounter,)).fetchone()
        if not u or not u['active'] or not p or not e or e['patient']!=patient or u['patient']!=patient or u['tenant']!=p['tenant'] or (write and u['role']!='reviewer'):
            raise DomainError('FORBIDDEN_SCOPE',403)
        return e

    def evidence(self,c,actor,patient,encounter):
        # Tool boundary independently enforces scope even when called outside generate.
        e=self.authorize(c,actor,patient,encounter)
        d=c.execute('SELECT * FROM documents WHERE encounter=?',(encounter,)).fetchone()
        return e,d,{'encounter_version':e['version'],'document_id':d['id'],'document_version':d['version'],'document_hash':digest(json.loads(d['content'])),'locator':'document.content','data_class':'synthetic'}

    def document_completeness_task(self,c,patient,encounter):
        target = DEMO_DOCUMENT_COMPLETENESS_TARGET
        if patient != target['patient'] or encounter != target['encounter']:
            raise DomainError('UNSUPPORTED_TASK_SCOPE')
        task = c.execute('SELECT * FROM tasks WHERE id=?', (target['task'],)).fetchone()
        if not task:
            raise DomainError('TASK_NOT_FOUND')
        if task['encounter'] != encounter:
            raise DomainError('TASK_CONTEXT_MISMATCH')
        if task['status'] != 'open':
            raise DomainError('TASK_NOT_OPEN')
        return task

    def context(self,actor,patient='p-demo',encounter='e-demo'):
        with self.db() as c:
            e,d,s=self.evidence(c,actor,patient,encounter)
            return {'demo':True,'patient':patient,'encounter':dict(e),'document':dict(d),'evidence':s,
                'tasks':[dict(r) for r in c.execute('SELECT * FROM tasks WHERE encounter=?',(encounter,))],
                'reviews':[dict(r) for r in c.execute('SELECT * FROM reviews WHERE proposal IN (SELECT id FROM proposals WHERE encounter=?)',(encounter,))],
                'proposal_versions':[dict(r) for r in c.execute('SELECT * FROM proposal_versions WHERE proposal IN (SELECT id FROM proposals WHERE encounter=?)',(encounter,))],
                'proposals':[dict(r) for r in c.execute('SELECT * FROM proposals WHERE encounter=?',(encounter,))],
                'results':[dict(r) for r in c.execute('SELECT * FROM results WHERE encounter=?',(encounter,))],
                'runs':[dict(r) for r in c.execute('SELECT * FROM runs WHERE encounter=?',(encounter,))],
                'audit':[dict(r) for r in c.execute('SELECT * FROM audit WHERE entity=? OR entity IN (SELECT id FROM proposals WHERE encounter=?) ORDER BY created',(encounter,encounter))]}

    def propose(self,actor,patient,encounter,scenario='success',data_class='synthetic'):
        if scenario not in ('success','timeout','failure','invalid','abstain'): raise DomainError('INVALID_SCENARIO',400)
        with self.db() as c:
            self.authorize(c,actor,patient,encounter,True)
            e,d,s=self.evidence(c,actor,patient,encounter)
            if e['status']!='open': raise DomainError('ENCOUNTER_CLOSED')
            self.document_completeness_task(c,patient,encounter)
        start=time.perf_counter(); outcome='failed'; error=None; response=None; provider_name=None; revision=None; abstain_reason=None
        try:
            provider=resolve_provider(self.config,data_class); provider_name=provider.name; revision=provider.revision
            response=provider.generate({'document':json.loads(d['content']),'scenario':scenario})
            if not isinstance(response,dict): error='INVALID_PROVIDER_OUTPUT'
            elif response.get('outcome')=='abstained' and isinstance(response.get('reason'),str):
                outcome='abstained'
                # Persist only the bounded public explanation, not raw provider
                # payloads or model reasoning. Treat this text as untrusted data.
                abstain_reason=response['reason'][:MAX_ABSTAIN_REASON_LENGTH]
            elif response.get('outcome')=='success' and isinstance(response.get('action'),dict) and response['action'].get('kind')=='document_completeness' and isinstance(response['action'].get('summary'),str) and isinstance(response['action'].get('missing_fields'),list) and all(isinstance(x,str) for x in response['action']['missing_fields']) and set(response['action'])=={'kind','summary','missing_fields'}: outcome='success'
            else: error='INVALID_PROVIDER_OUTPUT'
        except TimeoutError: outcome='timeout'; error='PROVIDER_TIMEOUT'
        except ProviderError as exc: error=str(exc)
        except Exception: error='PROVIDER_UNEXPECTED_ERROR'
        latency=(time.perf_counter()-start)*1000; run=ident()
        with self.db() as c:
            # Revalidate after inference; retain the attempt even if authorization or inputs changed.
            if outcome=='success':
                try:
                    self.authorize(c,actor,patient,encounter,True)
                    current_e,current_d,current_snapshot=self.evidence(c,actor,patient,encounter)
                    if current_e['status']!='open' or current_snapshot!=s:
                        raise DomainError('STALE_CONTEXT')
                    self.document_completeness_task(c,patient,encounter)
                except DomainError as exc:
                    outcome='failed'; error=exc.code
            c.execute('INSERT INTO runs (id,encounter,outcome,provider,model_revision,latency_ms,usage,cost,error,demo,abstain_reason) VALUES(?,?,?,?,?,?,?,?,?,?,?)',(run,encounter,outcome,provider_name,revision,latency,'null',None,error,1,abstain_reason))
            self.audit(c,actor,'ai_run',encounter,{'run_id':run,'outcome':outcome,'error':error,'abstain_reason':abstain_reason,'demo':True})
            if outcome!='success': return {'demo':True,'run_id':run,'outcome':outcome,'error':error,'reason':abstain_reason}
            pid=ident(); action=response['action']
            c.execute('INSERT INTO proposals VALUES(?,?,?,?,?,?,?,?,?,?)',(pid,patient,encounter,1,encoded(action),digest(action),encoded(s),'pending',time.time()+900,run))
            c.execute('INSERT INTO proposal_versions VALUES(?,?,?,?)',(pid,1,encoded(action),digest(action)))
            self.audit(c,actor,'proposal_created',pid,{'version':1,'action_hash':digest(action),'run_id':run,'demo':True})
            return {'demo':True,'run_id':run,'outcome':'success','proposal':dict(c.execute('SELECT * FROM proposals WHERE id=?',(pid,)).fetchone())}

    def proposal(self,c,pid):
        p=c.execute('SELECT * FROM proposals WHERE id=?',(pid,)).fetchone()
        if not p: raise DomainError('NOT_FOUND',404)
        return p

    def current(self,c,actor,p,version,action_hash):
        e,d,s=self.evidence(c,actor,p['patient'],p['encounter'])
        self.authorize(c,actor,p['patient'],p['encounter'],True)
        if p['version']!=version or p['action_hash']!=action_hash: raise DomainError('STALE_PROPOSAL')
        if p['expires']<time.time(): raise DomainError('EXPIRED_PROPOSAL')
        if e['status']!='open' or s!=json.loads(p['snapshot']): raise DomainError('STALE_CONTEXT')

    def review(self,actor,pid,version,action_hash,decision,edits=None):
        require_version(version)
        if decision not in ('approve','reject','edit'): raise DomainError('INVALID_DECISION',400)
        if decision!='edit' and edits is not None: raise DomainError('INVALID_EDITS',400)
        with self.db() as c:
            p=self.proposal(c,pid); self.current(c,actor,p,version,action_hash)
            if p['status']!='pending': raise DomainError('INVALID_STATE')
            if decision=='edit' and (not isinstance(edits,str) or not edits.strip() or len(edits)>4000): raise DomainError('INVALID_EDITS',400)
            self.document_completeness_task(c,p['patient'],p['encounter'])
            rid=ident()
            c.execute('INSERT INTO reviews VALUES(?,?,?,?,?,?,?,?)',(rid,pid,version,action_hash,actor,decision,encoded(edits),time.time()))
            if decision=='edit':
                action=json.loads(p['action']); action['summary']=edits
                c.execute('UPDATE proposals SET version=version+1,action=?,action_hash=?,status=? WHERE id=?',(encoded(action),digest(action),'pending',pid))
                c.execute('INSERT INTO proposal_versions VALUES(?,?,?,?)',(pid,version+1,encoded(action),digest(action)))
            else: c.execute('UPDATE proposals SET status=? WHERE id=?',('approved' if decision=='approve' else 'rejected',pid))
            self.audit(c,actor,'review_'+decision,pid,{'review_id':rid,'version':version,'action_hash':action_hash})
            return {'review_id':rid,'proposal':dict(self.proposal(c,pid))}

    def commit(self,actor,pid,version,action_hash,idempotency_key):
        require_version(version)
        if not isinstance(idempotency_key,str) or not 8<=len(idempotency_key)<=128: raise DomainError('INVALID_IDEMPOTENCY_KEY',400)
        payload_hash=digest({'proposal':pid,'version':version,'action_hash':action_hash})
        with self.db() as c:
            p=self.proposal(c,pid)
            self.authorize(c,actor,p['patient'],p['encounter'],True)
            old=c.execute('SELECT * FROM idempotency WHERE key=?',(idempotency_key,)).fetchone()
            if old:
                if old['actor']!=actor or old['payload_hash']!=payload_hash: raise DomainError('IDEMPOTENCY_CONFLICT')
                return {'result':json.loads(old['result']),'replayed':True}
            self.current(c,actor,p,version,action_hash)
            if p['status']!='approved': raise DomainError('NOT_APPROVED')
            r=c.execute("SELECT * FROM reviews WHERE proposal=? AND version=? AND action_hash=? AND decision='approve' ORDER BY created DESC LIMIT 1",(pid,version,action_hash)).fetchone()
            if not r: raise DomainError('NOT_APPROVED')
            self.authorize(c,r['reviewer'],p['patient'],p['encounter'],True)
            task=self.document_completeness_task(c,p['patient'],p['encounter'])
            result={'id':ident(),'proposal':pid,'patient':p['patient'],'encounter':p['encounter'],'action':json.loads(p['action']),'review':r['id'],'demo':True}
            c.execute('INSERT INTO results VALUES(?,?,?,?,?,?,?)',(result['id'],pid,p['patient'],p['encounter'],p['action'],r['id'],time.time()))
            c.execute("UPDATE proposals SET status='committed' WHERE id=?",(pid,))
            c.execute("UPDATE tasks SET status='completed' WHERE id=? AND encounter=? AND status='open'",(task['id'],p['encounter']))
            c.execute('INSERT INTO idempotency VALUES(?,?,?,?)',(idempotency_key,actor,payload_hash,encoded(result)))
            self.audit(c,actor,'result_committed',pid,{'result_id':result['id'],'review_id':r['id'],'action_hash':action_hash})
            return {'result':result,'replayed':False}

    def update_document(self,actor,patient,encounter,expected_version,content):
        require_version(expected_version)
        if (not isinstance(content,dict) or 'text' not in content
                or not set(content).issubset({'text','author','signed_at'})
                or any(not isinstance(value,str) for value in content.values())):
            raise DomainError('INVALID_DOCUMENT',400)
        with self.db() as c:
            self.authorize(c,actor,patient,encounter,True)
            d=c.execute('SELECT * FROM documents WHERE encounter=?',(encounter,)).fetchone()
            if d['version']!=expected_version: raise DomainError('STALE_DOCUMENT')
            c.execute('UPDATE documents SET version=version+1,content=? WHERE id=?',(encoded(content),d['id']))
            self.audit(c,actor,'document_updated',encounter,{'version':expected_version+1})
            return {'version':expected_version+1}
