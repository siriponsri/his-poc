"""Real loopback HTTP production-build/restart smoke on an explicit disposable PG DB.
This is HTTP integration evidence, not a browser rendering assertion.
"""
from __future__ import annotations
import hashlib,http.cookiejar,json,os,pathlib,socket,subprocess,sys,time,urllib.request,urllib.error,uuid
ROOT=pathlib.Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'evidence/fullsystem/same-origin';EVIDENCE.mkdir(parents=True,exist_ok=True)
assert os.environ.get('HIS_TEST_DATABASE_URL'), 'Run only with disposable test PostgreSQL via test_with_postgres.py'
assert (ROOT/'apps/web/dist/index.html').is_file(), 'Run frontend production build first'
log=(EVIDENCE/'runtime.txt').open('w');report={'status':'FAIL','kind':'real_HTTP_not_browser','assertions':[],'records':[]};proc=None

def check(name,truth,observed=None):
 report['assertions'].append({'name':name,'pass':bool(truth),'observed':observed})
 if not truth:raise AssertionError(name+': '+str(observed))

def request(path,body=None,headers=None):
 req=urllib.request.Request(url+path,data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json',**(headers or {})})
 try:
  with opener.open(req,timeout=15) as r:return r.status,r.read(),dict(r.headers)
 except urllib.error.HTTPError as e:return e.code,e.read(),dict(e.headers)

def start():
 global proc
 proc=subprocess.Popen([sys.executable,'-m','uvicorn','backend.app.main:app','--host','127.0.0.1','--port',str(port)],cwd=ROOT,env=env,stdout=log,stderr=log)
 deadline=time.monotonic()+20
 while time.monotonic()<deadline:
  if proc.poll() is not None:raise RuntimeError('Application exited; see runtime.txt')
  try:
   if request('/health')[0]==200:return
  except OSError:pass
  time.sleep(.1)
 raise TimeoutError('Application did not start')
try:
 subprocess.run([sys.executable,'-m','alembic','-c','backend/alembic.ini','upgrade','head'],cwd=ROOT,check=True,stdout=log,stderr=log)
 subprocess.run([sys.executable,'-m','backend.app.seed'],cwd=ROOT,check=True,stdout=log,stderr=log)
 with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
 url=f'http://127.0.0.1:{port}';env=dict(os.environ,HIS_ALLOWED_ORIGINS=url,WEB_DIST=str(ROOT/'apps/web/dist'))
 jar=http.cookiejar.CookieJar();opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar));start()
 code,raw,_=request('/ready');check('migration readiness',code==200,raw.decode())
 baseline=request('/login');check('production login HTML',baseline[0]==200 and b'<div id="root"' in baseline[1])
 check('production deep-link SPA',request('/domains/D10')[1]==baseline[1]);check('unknown API404',request('/api/v2/does-not-exist')[0]==404)
 check('legacy v1 not mounted',request('/api/v1/context',headers={'Authorization':'Bearer demo-reviewer-token'})[0]==404)
 check('public demo token cannot authenticate',request('/api/v2/auth/me',headers={'Authorization':'Bearer demo-reviewer-token'})[0]==401)
 code,raw,headers=request('/api/v2/auth/login',{'username':'registration','password':os.environ['HIS_SEED_PASSWORD']}, {'Origin':url});check('server login',code==200)
 identity=json.loads(raw);csrf=identity['csrf_token'];cookie=headers.get('set-cookie',headers.get('Set-Cookie',''));check('HttpOnly/SameSite cookie','httponly' in cookie.lower() and 'samesite=strict' in cookie.lower())
 check('me server roles','registration' in json.loads(request('/api/v2/auth/me')[1])['user']['roles'])
 code,raw,_=request('/api/v2/patients',{'display_name':'DEMO smoke denied','sex':'unknown','identifier':uuid.uuid4().hex}, {'Idempotency-Key':uuid.uuid4().hex});check('CSRF blocks mutation',code==403)
 for n in range(2):
  body={'display_name':f'DEMO HTTP persistence {n}','sex':'unknown','identifier':'HTTP-'+uuid.uuid4().hex,'issuer':'SYNTHETIC_HTTP'};key=uuid.uuid4().hex
  code,raw,_=request('/api/v2/patients',body,{'X-CSRF-Token':csrf,'Idempotency-Key':key});check('patient create '+str(n),code in (200,201),raw.decode())
  item=json.loads(raw);report['records'].append({'patient_id':item['id'],'actor':'registration'})
  replay=request('/api/v2/patients',body,{'X-CSRF-Token':csrf,'Idempotency-Key':key});check('idempotent same patient '+str(n),json.loads(replay[1])['id']==item['id'])
 check('role denied AI request',request('/api/v2/proposals',{'task_id':'task-patient-001','document_id':'document-patient-001'},{'X-CSRF-Token':csrf,'Idempotency-Key':uuid.uuid4().hex})[0]==403)
 proc.terminate();proc.wait(timeout=10);proc=None;start()
 for x in report['records']:
  code,raw,_=request('/api/v2/patients/'+x['patient_id']);check('record survives app restart '+x['patient_id'],code==200)
 code,_,_=request('/api/v2/auth/logout',{}, {'X-CSRF-Token':csrf});check('logout',code==200)
 check('logged-out session denied',request('/api/v2/auth/me')[0]==401)
 report.update(status='PASS',http_assertions=len(report['assertions']),browser_assertions=0,frontend_sha256=hashlib.sha256(baseline[1]).hexdigest())
except Exception as exc:
 report['error']=str(exc);raise
finally:
 if proc and proc.poll() is None:proc.terminate();proc.wait(timeout=10)
 log.close();(EVIDENCE/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'status':report['status'],'http_assertions':len(report['assertions']),'browser_assertions':0}))
