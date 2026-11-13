"""Check the public Cloudflare Access boundary without authenticating or exposing tokens."""
import argparse,json,sys
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime,timezone
import httpx
def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--output-dir',type=Path,required=True)
 args=parser.parse_args()
 results=[]
 with httpx.Client(timeout=20,follow_redirects=False,trust_env=False) as client:
  for path,headers in [('/login',{}),('/api/v2/auth/me',{}),('/ready',{}),('/domains/D37',{}),('/api/v2/patients',{'Cf-Access-Jwt-Assertion':'invalid-test-assertion'})]:
   try:
    response=client.get('https://his.ai-cie.com'+path,headers=headers)
    destination=urlparse(response.headers.get('location',''))
    denied=response.status_code in (301,302,303,307,308) and destination.scheme=='https' and destination.hostname=='ai-cie.cloudflareaccess.com'
    results.append({'path':path,'invalid_assertion_sent':bool(headers),'status_code':response.status_code,'redirect_hostname':destination.hostname,'redirect_path':destination.path,'access_gate_observed':denied})
   except httpx.HTTPError as error:
    results.append({'path':path,'status':'FAIL','reason':type(error).__name__,'access_gate_observed':False})
 report={'observed_at':datetime.now(timezone.utc).isoformat(),'status':'PASS' if all(x['access_gate_observed'] for x in results) else 'FAIL','method':'Unauthenticated HTTPS GETs; certificate verification enabled; redirects not followed; no cookies or tokens stored','checks':results,'authenticated_acceptance':'separate browser evidence required'}
 args.output_dir.mkdir(parents=True,exist_ok=True)
 (args.output_dir/'access-boundary.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(report,indent=2));return int(report['status']!='PASS')
if __name__=='__main__':sys.exit(main())
