"""Loopback-only synthetic demonstration. Not a production HTTP/auth server."""
import json, os
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from .service import Service, DomainError
from .request_validation import REQUEST_SCHEMAS, validate_request
ROOT=Path(__file__).resolve().parents[2]
CONFIG=ROOT/'config/runtime.json'

def unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError('Duplicate JSON property')
        value[key] = item
    return value

def reject_constant(value):
    raise ValueError('Non-finite JSON number')

def make_server(service,port=8080):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass  # Never log Authorization headers or request bodies.
        def send(self,status,body,content_type='application/json'):
            data=json.dumps(body,ensure_ascii=False).encode() if content_type=='application/json' else body
            self.send_response(status); self.send_header('Content-Type',content_type); self.send_header('Content-Length',str(len(data)))
            self.send_header('Cache-Control','no-store'); self.send_header('X-Content-Type-Options','nosniff'); self.end_headers(); self.wfile.write(data)
        def actor(self):
            # Demo tokens identify seeded users; production session/OIDC integration NOT implemented.
            token=self.headers.get('Authorization','')
            if token=='Bearer '+os.environ.get('HIS_DEMO_TOKEN','demo-reviewer-token'): return 'reviewer-demo'
            if token=='Bearer demo-viewer-token': return 'viewer-demo'
            raise DomainError('UNAUTHENTICATED',401)
        def do_GET(self):
            try:
                if self.path=='/': return self.send(200,(ROOT/'web/index.html').read_bytes(),'text/html; charset=utf-8')
                if self.path=='/health': return self.send(200,{'status':'ok','demo':True,'inference_profile':service.config.get('inference_profile')})
                if self.path=='/api/v1/context': return self.send(200,service.context(self.actor()))
                self.send(404,{'error':'NOT_FOUND'})
            except DomainError as e: self.send(e.status,{'error':e.code})
            except Exception: self.send(500,{'error':'INTERNAL_ERROR'})
        def do_POST(self):
            try:
                actor=self.actor()
                if self.path not in REQUEST_SCHEMAS: raise DomainError('NOT_FOUND',404)
                if self.headers.get_content_type() != 'application/json': raise DomainError('INVALID_CONTENT_TYPE',400)
                lengths = self.headers.get_all('Content-Length', [])
                if len(lengths) != 1 or self.headers.get('Transfer-Encoding') is not None: raise DomainError('INVALID_BODY_SIZE',400)
                try: n=int(lengths[0])
                except ValueError: raise DomainError('INVALID_BODY_SIZE',400)
                if n<1 or n>65536: raise DomainError('INVALID_BODY_SIZE',400)
                self.connection.settimeout(5)
                try:
                    data=self.rfile.read(n)
                    if len(data) != n: raise ValueError('Incomplete request body')
                    b=json.loads(data.decode('utf-8'),object_pairs_hook=unique_object,parse_constant=reject_constant)
                except (ValueError,RecursionError,TimeoutError): raise DomainError('INVALID_REQUEST',400)
                b=validate_request(self.path,b)
                if self.path=='/api/v1/proposals': r=service.propose(actor,b['patient'],b['encounter'],b.get('scenario','success'),b.get('data_class','synthetic'))
                elif self.path=='/api/v1/reviews': r=service.review(actor,b['proposal_id'],b['version'],b['action_hash'],b['decision'],b.get('edits'))
                elif self.path=='/api/v1/commits': r=service.commit(actor,b['proposal_id'],b['version'],b['action_hash'],b['idempotency_key'])
                elif self.path=='/api/v1/documents': r=service.update_document(actor,b['patient'],b['encounter'],b['expected_version'],b['content'])
                else: raise DomainError('NOT_FOUND',404)
                self.send(200,r)
            except DomainError as e: self.send(e.status,{'error':e.code})
            except Exception: self.send(500,{'error':'INTERNAL_ERROR'})
    return ThreadingHTTPServer(('127.0.0.1',port),Handler)

def main():
    config=json.loads(CONFIG.read_text()) if CONFIG.exists() else {'inference_profile':'mock_demo','provider':'mock'}
    db=Path(os.environ.get('HIS_DB_PATH',str(ROOT/'demo.sqlite3')))
    service=Service(db,config)
    server=make_server(service,int(os.environ.get('HIS_PORT','8080')))
    print('DEMO / SYNTHETIC / MOCK ONLY http://127.0.0.1:'+str(server.server_port),flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
if __name__=='__main__': main()
