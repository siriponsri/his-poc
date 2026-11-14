"""Foreground cron entrypoint. Requests are exclusive; no retry or enable command."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import supervisor

def read_private(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o077:
        raise ValueError('PRIVATE_FILE_REQUIRED')
    return path.read_bytes()

def ancestry():
    result=[];pid=os.getpid()
    for unused in range(5):
        folder=Path('/proc')/str(pid)
        try:
            name=(folder/'comm').read_text().strip()
            status=(folder/'status').read_text().splitlines()
            parent=int(next(row.split(':',1)[1].strip() for row in status if row.startswith('PPid:')))
        except (OSError,StopIteration):break
        result.append({'pid':pid,'parent_pid':parent,'comm':name})
        if parent<=1:break
        pid=parent
    return result

def validate_verify(config):
    supervisor.validate(config)
    if config['enabled'] is not False or config['profiles_qualified'] or config['worker_image_id'] is not None or config['worker_env_sha256'] is not None:
        raise ValueError('VERIFY_MUST_REMAIN_DISABLED_UNBOUND')

def consume(request_path,token_path,state,now):
    raw=read_private(request_path);request=json.loads(raw)
    if request['purpose'] not in ['VERIFY_ONLY','ENABLED_ONCE'] or request['root_authorized'] is not True:
        raise ValueError('ROOT_REQUEST_REQUIRED')
    if not re.fullmatch(r'[a-z][a-z0-9-]{0,63}',request['request_id']):raise ValueError('INVALID_REQUEST_ID')
    if hashlib.sha256(read_private(token_path)).hexdigest()!=request['root_token_sha256']:
        raise ValueError('ROOT_TOKEN_MISMATCH')
    if not datetime.fromisoformat(request['not_before_utc'])<=now<=datetime.fromisoformat(request['expires_utc']):
        raise ValueError('EXPIRED_OR_EARLY_REQUEST')
    if request_path.parent.resolve()!=state.resolve() or token_path.parent.resolve()!=state.resolve():
        raise ValueError('REQUEST_OUTSIDE_STATE')
    supervisor.write_once(state/(request['request_id']+'-consumed.json'),{'request_sha256':hashlib.sha256(raw).hexdigest(),'purpose':request['purpose'],'consumed_at':now.isoformat(),'pid':os.getpid()})
    return request

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--state',type=Path,required=True)
    modes=parser.add_mutually_exclusive_group(required=True);modes.add_argument('--reboot',action='store_true');modes.add_argument('--request',type=Path)
    parser.add_argument('--token',type=Path);args=parser.parse_args();state=args.state
    if not state.is_dir() or state.is_symlink():raise ValueError('EXISTING_PRIVATE_STATE_REQUIRED')
    config_raw=read_private(state/'config.json');config=json.loads(config_raw)
    if args.reboot:
        # A boot never consumes an old one-off token or restarts unknown work.
        if (state/'pause').exists() or (state/'HALTED_UNKNOWN.json').exists() or (state/'ACTIVE_DISPATCH.json').exists() or not (state/'enabled').exists():return
        approval=json.loads(read_private(state/'ENABLED_APPROVAL.json'))
        if approval['purpose']!='ENABLED_PERSISTENT' or approval['root_authorized'] is not True or approval['config_sha256']!=hashlib.sha256(config_raw).hexdigest():raise ValueError('ENABLED_APPROVAL_REQUIRED')
        supervisor.validate(config,bound=True)
    else:
        if args.token is None:raise ValueError('ROOT_TOKEN_FILE_REQUIRED')
        request=consume(args.request,args.token,state,datetime.now(timezone.utc))
        if request['config_sha256']!=hashlib.sha256(config_raw).hexdigest():raise ValueError('CONFIG_CHANGED')
        if request['purpose']=='VERIFY_ONLY':
            validate_verify(config)
            if not (state/'pause').exists() or (state/'enabled').exists():raise ValueError('EXPECTED_PAUSED_DISABLED')
            parents=ancestry()
            if not any(row['comm'] in ['cron','CRON','crond'] for row in parents):raise ValueError('CRON_PARENT_NOT_PROVEN')
            supervisor.write_once(state/'initial-cron-verified.json',{'status':'PASS_CRON_DISABLED_VALIDATION_ONLY','at':datetime.now(timezone.utc).isoformat(),'pid':os.getpid(),'parent_pid':os.getppid(),'uid':os.getuid(),'session_id':os.getsid(0),'ancestry':parents,'cgroup':Path('/proc/self/cgroup').read_text().strip(),'docker_calls':0,'http_calls':0,'database_calls':0,'model_calls':0,'runtime_persistence_validated':False})
            return
        supervisor.validate(config,bound=True)
        if (state/'pause').exists() or not (state/'enabled').exists() or (state/'HALTED_UNKNOWN.json').exists() or (state/'ACTIVE_DISPATCH.json').exists():raise ValueError('ENABLED_START_IS_FENCED')
    # Foreground under cron, no shell daemonization or login-session dependency.
    os.execv(sys.executable,[sys.executable,str(Path(__file__).with_name('supervisor.py')),'--config',str(state/'config.json'),'--run'])

if __name__=='__main__':main()
