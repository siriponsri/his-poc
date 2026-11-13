"""Authenticated loopback client for D38. No direct database/tool bypass."""
from __future__ import annotations
import argparse,getpass,http.cookiejar,json,os,sys,time,uuid
from urllib.parse import urlsplit
from urllib.request import Request,build_opener,HTTPCookieProcessor
from urllib.error import HTTPError,URLError

class OperationsClientError(RuntimeError):
    def __init__(self,code,*,job_id=None,operation_key=None):
        super().__init__(code);self.code=code;self.job_id=job_id;self.operation_key=operation_key

def local_url(value):
    parsed=urlsplit(value)
    if parsed.scheme not in {'http','https'} or parsed.hostname not in {'127.0.0.1','localhost','::1'} or parsed.username or parsed.password or parsed.path not in {'','/'} or parsed.query or parsed.fragment:
        raise OperationsClientError('LOOPBACK_APPLICATION_URL_REQUIRED')
    return value.rstrip('/')

class OperationsClient:
    def __init__(self,base_url):
        self.base_url=local_url(base_url);self.cookies=http.cookiejar.CookieJar()
        self.opener=build_opener(HTTPCookieProcessor(self.cookies));self.csrf=None
    def request(self,method,path,payload=None,operation_key=None):
        headers={'Accept':'application/json'}
        body=None
        if payload is not None:headers['Content-Type']='application/json';body=json.dumps(payload).encode()
        if self.csrf:headers['X-CSRF-Token']=self.csrf
        if operation_key:headers['Idempotency-Key']=operation_key
        try:
            with self.opener.open(Request(self.base_url+path,data=body,headers=headers,method=method),timeout=15) as response:
                return json.loads(response.read())
        except HTTPError as exc:
            # Never echo response bodies: validation responses may contain submitted input.
            code='HTTP_'+str(exc.code)
            try:
                detail=json.loads(exc.read(8192)).get('detail')
                if isinstance(detail,dict) and isinstance(detail.get('code'),str) and detail['code'].replace('_','').isalnum():code=detail['code']
            except Exception:pass
            raise OperationsClientError(code,operation_key=operation_key) from None
        except (URLError,TimeoutError,OSError):
            raise OperationsClientError('NETWORK_OUTCOME_UNKNOWN' if operation_key else 'APPLICATION_UNREACHABLE',operation_key=operation_key) from None
        except (ValueError,TypeError):raise OperationsClientError('INVALID_SERVER_RESPONSE',operation_key=operation_key) from None
    def login(self,username,password):
        if not username or not password:raise OperationsClientError('OPERATOR_CREDENTIALS_REQUIRED')
        response=self.request('POST','/api/v2/auth/login',{'username':username,'password':password})
        self.csrf=response.get('csrf_token')
        if not self.csrf:raise OperationsClientError('INVALID_LOGIN_RESPONSE')
        return response
    def logout(self):
        try:
            if self.csrf:self.request('POST','/api/v2/auth/logout',{})
        finally:self.csrf=None;self.cookies.clear()
    def run_job(self,kind,username,password,*,backup_id=None,operation_key=None,timeout=180):
        if kind not in {'backup','isolated_restore'}:raise OperationsClientError('INVALID_JOB_KIND')
        operation_key=operation_key or str(uuid.uuid4());job_id=None;failure=None;result=None
        self.login(username,password)
        try:
            # Authorization is authoritative in POST /operations/jobs and worker claim.
            payload={'kind':kind}
            if backup_id is not None:payload['backup_id']=backup_id
            job=self.request('POST','/api/v2/operations/jobs',payload,operation_key)
            job_id=job['id'];deadline=time.monotonic()+timeout
            while True:
                jobs=self.request('GET','/api/v2/operations/jobs')['items']
                current=next((row for row in jobs if row['id']==job_id),None)
                if current is None:raise OperationsClientError('JOB_NOT_VISIBLE',job_id=job_id,operation_key=operation_key)
                if current['status'] in {'completed','restore_verified'}:
                    detail=current.get('result') or {}
                    result={'job_id':job_id,'status':current['status'],'operation_key':operation_key,'artifact_id':current.get('artifact_id'),
                        'dump_sha256':detail.get('dump_sha256'),'isolated_database':detail.get('isolated_database')};break
                if current['status'] in {'failed','restore_failed'}:
                    raise OperationsClientError(current.get('error_code') or 'OPERATION_FAILED',job_id=job_id,operation_key=operation_key)
                if time.monotonic()>=deadline:raise OperationsClientError('JOB_OUTCOME_PENDING',job_id=job_id,operation_key=operation_key)
                time.sleep(.2)
        except OperationsClientError as exc:failure=exc
        finally:
            try:self.logout()
            except OperationsClientError:
                if failure is None:failure=OperationsClientError('SESSION_REVOCATION_UNCONFIRMED',job_id=job_id,operation_key=operation_key)
        if failure:raise failure
        return result

def run_cli(kind):
    parser=argparse.ArgumentParser(description='Authenticated local HIS D38 operation; application must be running.')
    if kind=='isolated_restore':parser.add_argument('backup_id')
    parser.add_argument('--url',default=os.environ.get('HIS_BASE_URL','http://127.0.0.1:8000'))
    parser.add_argument('--idempotency-key',default=None,help='Reuse the same value to recover an uncertain prior submission')
    parser.add_argument('--timeout',type=int,default=180)
    args=parser.parse_args()
    if not 1<=args.timeout<=300:parser.error('--timeout must be between 1 and 300 seconds')
    try:
        client=OperationsClient(args.url)
        username=os.environ.get('HIS_OPERATOR_USERNAME') or input('Operator username: ')
        password=os.environ.get('HIS_OPERATOR_PASSWORD') or getpass.getpass('Operator password: ')
        result=client.run_job(kind,username,password,backup_id=getattr(args,'backup_id',None),operation_key=args.idempotency_key,timeout=args.timeout)
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0
    except OperationsClientError as exc:
        print(json.dumps({'error':exc.code,'job_id':exc.job_id,'operation_key':exc.operation_key,
            'recovery':'Inspect D38 job status. For an uncertain submission, reuse its operation_key with --idempotency-key; never infer completion from a timeout.'}),file=sys.stderr)
        return 1
    except (KeyboardInterrupt,EOFError):print('Operator command cancelled.',file=sys.stderr);return 1
