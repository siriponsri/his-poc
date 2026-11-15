"""Explicit private provisioning for the named synthetic POC, never startup.

Only this operator entrypoint accepts an 8+ character POC password. Public user
creation/reset and seed policy remain unchanged. Password input is stdin only.
The caller owns the transaction for provision_poc_admin; main commits atomically.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

from sqlalchemy import select,text
from sqlalchemy.exc import SQLAlchemyError
from argon2.exceptions import VerifyMismatchError,VerificationError,InvalidHashError

from .auth import password_hasher,permissions_for
from .common import uid
from .models import Facility,Membership,Organization,Role,RolePermission,SecurityEvent,User

MIGRATION='0005_assistant_workspaces'
DISPLAY_NAME='POC Administrator'


class ProvisionError(ValueError):
    """Fixed, non-secret operator error code."""


def check(condition,code):
    if not condition:raise ProvisionError(code)


def provision_poc_admin(db,*,username,organization_id,facility_id,password):
    """Caller-supplied private transaction; no migration/reset/role grants/network."""
    check(username=='admin' and organization_id=='org-demo' and facility_id=='facility-demo','NAMED_SYNTHETIC_POC_ONLY')
    check(isinstance(password,str) and 8<=len(password)<=200 and password==password.strip() and not any(c in password for c in '\r\n\0'),'POC_PRIVATE_PASSWORD_POLICY')
    lock=int.from_bytes(hashlib.sha256(('his-authz:'+organization_id).encode()).digest()[:8],'big',signed=True)
    db.execute(text('SELECT pg_advisory_xact_lock(:key)'),{'key':lock})
    check(db.scalar(text('SELECT version_num FROM alembic_version'))==MIGRATION,'CURRENT_0005_REQUIRED')
    check(db.get(Organization,organization_id) is not None,'ORGANIZATION_NOT_FOUND')
    facility=db.get(Facility,facility_id)
    check(facility is not None and facility.organization_id==organization_id,'FACILITY_SCOPE_MISMATCH')
    check(db.get(Role,'system_admin') is not None,'SYSTEM_ADMIN_ROLE_UNAVAILABLE')
    persisted=set(db.scalars(select(RolePermission.permission_id).where(RolePermission.role_id=='system_admin')))
    check(persisted==permissions_for({'system_admin'}),'SYSTEM_ADMIN_PERMISSION_DRIFT')
    user=db.scalar(select(User).where(User.username==username).with_for_update())
    platform_operators={item.strip() for item in os.getenv('HIS_PLATFORM_OPERATORS','').split(',') if item.strip()}
    if user:
        check(user.organization_id==organization_id and user.status=='active' and user.display_name==DISPLAY_NAME and user.id not in platform_operators,'EXISTING_IDENTITY_CONFLICT')
        memberships=db.scalars(select(Membership).where(Membership.user_id==user.id).order_by(Membership.id)).all()
        check(len(memberships)==1 and memberships[0].role=='system_admin' and memberships[0].facility_id==facility_id and memberships[0].active is True,'EXISTING_MEMBERSHIP_CONFLICT')
        try:matches=password_hasher.verify(user.password_hash,password)
        except (VerifyMismatchError,VerificationError,InvalidHashError):matches=False
        check(matches,'EXISTING_PASSWORD_CONFLICT')
        # Deliberately no needs_rehash/reset/version/audit mutation on a replay.
        status='UNCHANGED'
    else:
        identity=uid();check(identity not in platform_operators,'PLATFORM_OPERATOR_IDENTITY_CONFLICT')
        user=User(id=identity,organization_id=organization_id,username=username,display_name=DISPLAY_NAME,password_hash=password_hasher.hash(password),status='active')
        db.add(user);db.flush()
        db.add(Membership(id=uid(),user_id=user.id,facility_id=facility_id,role='system_admin',active=True))
        # AuditEvent.actor_id is NOT NULL in 0005. Use the existing nullable
        # operator-origin security ledger, never pretend the new admin acted.
        db.add(SecurityEvent(organization_id=organization_id,facility_id=facility_id,actor_id=None,method='CLI',
            route_template='/operator/provision-poc-admin/users/'+user.id,status_code=201,event='poc_admin_provisioned'))
        db.flush();status='CREATED'
    return {'status':status,'user_id':user.id,'username':username,'organization_id':organization_id,'facility_id':facility_id,'role':'system_admin','origin':'private_operator_cli','password_policy':'named_poc_private_min8'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--username',required=True)
    parser.add_argument('--organization',required=True)
    parser.add_argument('--facility',required=True)
    parser.add_argument('--password-stdin',action='store_true',required=True)
    args=parser.parse_args()
    try:
        check(bool(os.getenv('DATABASE_URL')),'EXPLICIT_DATABASE_URL_REQUIRED')
        check(not sys.stdin.isatty(),'PRIVATE_STDIN_REQUIRED')
        raw=sys.stdin.read(203)
        check(len(raw)<=202,'POC_PRIVATE_PASSWORD_POLICY')
        password=raw.removesuffix('\n').removesuffix('\r')
        from .db import SessionLocal
        with SessionLocal.begin() as db:
            result=provision_poc_admin(db,username=args.username,organization_id=args.organization,facility_id=args.facility,password=password)
    except ProvisionError as error:
        print(json.dumps({'status':'NOT_PROVISIONED','code':str(error)}),file=sys.stderr);return 2
    except SQLAlchemyError:
        print(json.dumps({'status':'NOT_PROVISIONED','code':'DATABASE_OPERATION_FAILED'}),file=sys.stderr);return 2
    print(json.dumps(result));return 0


if __name__=='__main__':raise SystemExit(main())
