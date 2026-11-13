"""Source-only snapshot and Linux deployment contract validation; never publishes."""
from pathlib import Path
import argparse, hashlib, json, os, subprocess, sys, tarfile
ROOT = Path(__file__).resolve().parents[1]
ALLOWED = {'backend', 'apps', 'scripts', 'config', 'contracts', 'data', 'spec', 'deploy'}
EXCLUDED = {'node_modules', '__pycache__', 'dist', 'evidence', '.test-out', '.venv', 'var', '.git', '.pytest_cache'}
EXTENSIONS = {'.py','.ts','.tsx','.mts','.mjs','.js','.json','.md','.txt','.sql','.ini','.toml','.yaml','.yml','.css','.html','.svg','.png','.jpg','.jpeg','.webp','.csv','.woff','.woff2'}
FILES = {'Dockerfile', '.dockerignore', 'requirements-backend.txt', '.env.example', 'AGENTS.md'}
def candidates(root=ROOT):
    output=[]
    for folder in ALLOWED:
        base=root/folder
        if not base.exists(): continue
        for p in base.rglob('*'):
            rel=p.relative_to(root)
            if p.is_file() and not p.is_symlink() and not any(x in EXCLUDED or x.startswith('.env') for x in rel.parts) and p.suffix.lower() in EXTENSIONS and p.name!='vite.design.config.mts' and not any(x in p.name.lower() for x in ['credential','private-key','private_key','secret']):
                output.append(p)
    output += [root/n for n in FILES if (root/n).is_file()]
    return sorted(set(output))
def snapshot(output, root=ROOT):
    if output.exists(): raise ValueError('SNAPSHOT_ALREADY_EXISTS')
    paths=candidates(root)
    hashes={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    with tarfile.open(output,'w:gz') as tar:
        for p in paths: tar.add(p,arcname=p.relative_to(root).as_posix(),recursive=False)
    for p in paths:
        if hashlib.sha256(p.read_bytes()).hexdigest()!=hashes[p.relative_to(root).as_posix()]:
            raise ValueError('SOURCE_CHANGED_DURING_SNAPSHOT')
    return {'files':len(paths),'source_sha256':hashes,'archive_sha256':hashlib.sha256(output.read_bytes()).hexdigest()}
def validate_contract(root=ROOT):
    d=json.loads((root/'deploy/dr-train/compose.json').read_text())
    app=d['services']['app'];db=d['services']['db'];cf=d['services']['connector']
    assert app['network_mode']=='host' and app['command'][-4:]==['--host','127.0.0.1','--port','18080']
    assert 'ports' not in app and 'ports' not in cf
    assert db['ports']==['127.0.0.1:15432:5432']
    assert app['environment']['HIS_COOKIE_SECURE']=='true'
    assert app['environment']['HIS_ALLOWED_ORIGINS']=='https://his.ai-cie.com'
    assert app['environment']['DR_TRAIN_BASE_URL']=='http://127.0.0.1:11434'
    assert cf['profiles']==['public'] and cf['network_mode']=='host'
    assert '--disable-path-normalization=false' in cf['command']
    assert all(v['read_only'] for v in cf['volumes'])
    assert all(d['services'][x]['restart']=='unless-stopped' for x in ['app','db','connector'])
    t=json.loads((root/'deploy/dr-train/tunnel.json').read_text())
    assert len(t['ingress'])==2 and t['ingress'][-1]=={'service':'http_status:404'}
    first=t['ingress'][0]
    assert first['hostname']=='his.ai-cie.com' and first['service']=='http://127.0.0.1:18080'
    assert first['originRequest']['access']=={'required':True,'teamName':'ai-cie','audTag':['eabe9c9519847005480c723a7d4c306a8204ffe1e30905f60460298f85441cd2']}
    return {'status':'PASS','scope':'Static Linux loopback, pinned model, exact HTTPS origin and Access-required contract; not runtime acceptance'}
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['snapshot','validate']);p.add_argument('--output',type=Path);a=p.parse_args()
    if a.action=='validate': result=validate_contract()
    else:
        if not a.output:p.error('--output required')
        result=snapshot(a.output);a.output.with_suffix('.manifest.json').write_text(json.dumps(result,indent=2)+'\n')
        result={'files':result['files'],'archive_sha256':result['archive_sha256']}
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
