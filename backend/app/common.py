import hashlib,json
from datetime import date,datetime,timezone
from decimal import Decimal
from uuid import uuid4
from fastapi import HTTPException
from sqlalchemy import inspect,text
from .models import AuditEvent,Operation

def uid(): return str(uuid4())
def utcnow(): return datetime.now(timezone.utc)
def canonical(data): return json.dumps(data,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False,default=lambda o: str(o) if isinstance(o,(Decimal,date,datetime)) else o.model_dump(mode='json'))
def digest(data): return hashlib.sha256(canonical(data).encode()).hexdigest()
def text_hash(value): return hashlib.sha256(value.encode()).hexdigest()
def serialize(model):
    result={}
    for c in inspect(model).mapper.column_attrs:
        value=getattr(model,c.key)
        if isinstance(value,(date,datetime)): value=value.isoformat()
        elif isinstance(value,Decimal): value=str(value)
        result[c.key]=value
    return result

def audit(db,actor,domain,entity_id,action,details=None):
    db.add(AuditEvent(facility_id=actor.facility_id,organization_id=actor.organization_id,actor_id=actor.user_id,domain=domain,entity_id=str(entity_id),action=action,details=details or {}))

def check_version(model,expected):
    if isinstance(expected,bool) or model.version != expected: raise HTTPException(409,detail={'code':'STALE_VERSION','outcome':'not_written','current_version':model.version})
def transition(record,target,allowed,version):
    check_version(record,version)
    if target not in allowed.get(record.status,()): raise HTTPException(409,detail={'code':'INVALID_TRANSITION','outcome':'not_written'})
    record.status=target;record.version+=1

def begin_operation(db,actor,key,operation,payload):
    if not key or len(key)>120: raise HTTPException(400,detail={'code':'IDEMPOTENCY_KEY_REQUIRED','outcome':'not_written'})
    # Serializes same actor+key even before a row exists; collisions only reduce concurrency.
    lock=int.from_bytes(hashlib.sha256((actor.user_id+':'+key).encode()).digest()[:8],'big',signed=True)
    db.execute(text('SELECT pg_advisory_xact_lock(:key)'),{'key':lock})
    old=db.get(Operation,(actor.user_id,key))
    if old:
        if old.authorization_hash!=authorization_hash(actor) or old.operation!=operation or old.payload_hash!=digest({'organization_id':actor.organization_id,'facility_id':actor.facility_id,'payload':payload}): raise HTTPException(409,detail={'code':'IDEMPOTENCY_CONFLICT','outcome':'not_written'})
        return old.response
    return None

def finish_operation(db,actor,key,operation,payload,response):
    db.add(Operation(authorization_hash=authorization_hash(actor),organization_id=actor.organization_id,facility_id=actor.facility_id,actor_id=actor.user_id,key=key,operation=operation,payload_hash=digest({'organization_id':actor.organization_id,'facility_id':actor.facility_id,'payload':payload}),response=response))
    db.flush()
    return response

def authorization_hash(actor):
    return digest({'organization':actor.organization_id,'facility':actor.facility_id,'permissions':sorted(actor.permissions),'patient_scope':actor.patient_scope,'care_patients':sorted(actor.care_patient_ids) if actor.care_patient_ids is not None else None})
