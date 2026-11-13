"""Typed local ERP workflows. External remittances/dispatch are explicit synthetic only."""
from __future__ import annotations
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Literal
import hashlib
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select, func, text
from sqlalchemy.orm import Session
from ..db import get_db
from ..auth import current_actor, require_domain, require, revalidate_actor, scoped_encounter, scoped_patient
from ..common import uid, utcnow, serialize, audit, check_version, begin_operation, finish_operation, digest
from ..models import Encounter, Patient, User, Department, Location, Membership, Task
from ..models_erp import *

router = APIRouter(tags=["ERP and enterprise workflows"])
Money = Decimal
ZERO = Decimal('0')

def fail(message, code=409):
    raise HTTPException(code, {'code':'ERP_REJECTED','message':message,'outcome':'not_written'})

def amount(value):
    return Decimal(value).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)

def values(actor, **kw):
    return dict(organization_id=actor.organization_id, facility_id=actor.facility_id, **kw)

def scoped(db, actor, model, identity, lock=False):
    query = select(model).where(model.id == identity, model.organization_id == actor.organization_id)
    if hasattr(model, 'facility_id'): query = query.where(model.facility_id == actor.facility_id)
    if lock: query = query.with_for_update()
    item = db.scalar(query)
    if item is None: fail('Record not found',404)
    return item

def rows(db, actor, model):
    q = select(model).where(model.organization_id == actor.organization_id)
    if hasattr(model, 'facility_id'): q = q.where(model.facility_id == actor.facility_id)
    if model in (Roster,StaffMember) and not {'quality','hr_officer','roster_manager','quality_officer','auditor','system_admin'}.intersection(actor.roles):
        q=q.where(StaffMember.user_id==actor.user_id) if model is StaffMember else q.where(Roster.staff_id.in_(select(StaffMember.id).where(StaffMember.user_id==actor.user_id)))
    return list(db.scalars(q))

def reference(db, actor, model, identity):
    if identity is None: return None
    if model is Encounter: return scoped_encounter(db, actor, identity)
    if model is Patient: return scoped_patient(db, actor, identity)
    if model is User:
        member=db.scalar(select(Membership).where(Membership.user_id==identity,Membership.facility_id==actor.facility_id,Membership.active.is_(True)))
        if not member:fail('Assigned user unavailable in facility',404)
    return scoped(db,actor,model,identity)

def set_state(row, target):
    row.status = target
    row.version += 1

def require_role(actor, *roles):
    if not set(roles).intersection(actor.roles): fail('Role does not authorize this action',403)

def credential_allows(db, user_id, permission):
    staff = db.scalar(select(StaffMember).where(StaffMember.user_id==user_id,StaffMember.privilege==permission).execution_options(populate_existing=True))
    return staff is None or (staff.credential_status=='active' and staff.credential_valid_until >= date.today())

def get_eligible_lot(db, actor, lot_id, item_id=None):
    lot = scoped(db,actor,InventoryLot,lot_id,lock=True)
    if item_id and lot.item_id != item_id: fail('Lot does not match item')
    if lot.status != 'available' or lot.expiry_date < date.today(): fail('Lot unavailable or expired')
    return lot

def post_stock_movement(db, actor, lot_id, location_id, quantity, source_id, key, original_id=None, disposition='available', reservation_id=None):
    """Same transaction as caller: lock lot then balance; append immutable signed movement."""
    if not any(f'{d}.write' in actor.permissions for d in ('D08','D27','D28')): fail('Stock permission required',403)
    quantity=Decimal(quantity)
    if quantity == 0 or quantity.as_tuple().exponent < -3: fail('Quantity must be nonzero with <=3 decimal places',422)
    if disposition not in ('available','quarantine'): fail('Unsupported disposition',422)
    lot=scoped(db,actor,InventoryLot,lot_id,lock=True)
    scoped(db,actor,StockLocation,location_id,lock=True)
    existing=db.scalar(select(StockMovement).where(StockMovement.organization_id==actor.organization_id,StockMovement.operation_key==key))
    if existing:
        if existing.facility_id!=actor.facility_id: fail('Movement source unavailable',409)
        if existing.status!='posted':fail('Movement key refers to an unposted draft')
        if (existing.lot_id,existing.location_id,existing.quantity,existing.source_id,existing.original_movement_id,existing.disposition)!=(lot_id,location_id,quantity,source_id,original_id,disposition): fail('Movement key reused with different content')
        return existing
    if quantity < 0:
        get_eligible_lot(db,actor,lot_id)
        if disposition != 'available': fail('Quarantined stock cannot be issued')
    if original_id:
        original=scoped(db,actor,StockMovement,original_id,lock=True)
        if original.lot_id!=lot_id or original.location_id!=location_id or original.quantity*quantity>=0: fail('Return must reverse original lot/location/direction')
        returned=db.scalar(select(func.coalesce(func.sum(func.abs(StockMovement.quantity)),0)).where(StockMovement.original_movement_id==original_id))
        if Decimal(returned)+abs(quantity)>abs(original.quantity): fail('Cumulative return exceeds original movement')
    balance=db.scalar(select(StockBalance).where(StockBalance.lot_id==lot_id,StockBalance.location_id==location_id).with_for_update())
    if not balance:
        balance=StockBalance(lot_id=lot_id,location_id=location_id,available=0,quarantined=0);db.add(balance);db.flush()
    field='quarantined' if disposition=='quarantine' else 'available'
    result=Decimal(getattr(balance,field))+quantity
    reserved=Decimal(db.scalar(select(func.coalesce(func.sum(StockReservation.quantity),0)).where(StockReservation.lot_id==lot_id,StockReservation.location_id==location_id,StockReservation.status=='reserved',StockReservation.id!=reservation_id)) or 0) if disposition=='available' else ZERO
    if result<0 or (quantity<0 and result<reserved): fail('Insufficient unreserved available stock')
    setattr(balance,field,result)
    movement=StockMovement(**values(actor,lot_id=lot_id,location_id=location_id,quantity=quantity,source_id=source_id,operation_key=key,original_movement_id=original_id,disposition=disposition,status='posted'))
    db.add(movement);db.flush()
    audit(db,actor,'D28',movement.id,'stock.posted',{'quantity':str(quantity),'lot_id':lot_id,'source_id':source_id,'disposition':disposition})
    return movement

def add_charge(db, actor, encounter_id, source_id, label, quantity, unit_price, key=None, price_version_id=None):
    if not any(f'{d}.write' in actor.permissions for d in ('D08','D10','D17','D23')): fail('Charge permission required',403)
    encounter=scoped_encounter(db,actor,encounter_id)
    quantity=Decimal(quantity);unit_price=amount(unit_price)
    if quantity<=0 or unit_price<0: fail('Invalid charge quantity/price',422)
    existing=db.scalar(select(Charge).where(Charge.organization_id==actor.organization_id,Charge.source_id==source_id))
    if existing:
        if existing.facility_id!=actor.facility_id: fail('Charge source unavailable',409)
        if (existing.encounter_id,existing.label,existing.quantity,existing.unit_price)!=(encounter_id,label,quantity,unit_price): fail('Charge source reused with different content')
        return existing
    record=Charge(**values(actor,encounter_id=encounter.id,source_id=source_id,label=label,quantity=quantity,unit_price=unit_price,amount=amount(quantity*unit_price),price_version_id=price_version_id,status='priced'))
    db.add(record);db.flush();audit(db,actor,'D23',record.id,'charge.created',{'source_id':source_id})
    return record

def ledger(db, actor, source_id, kind, value, debit, credit, original_id=None):
    value=amount(value)
    entry=LedgerEntry(**values(actor,source_id=source_id,kind=kind,original_entry_id=original_id,status='posted'))
    db.add(entry);db.flush()
    db.add_all([LedgerLine(entry_id=entry.id,account=debit,debit=value,credit=0),LedgerLine(entry_id=entry.id,account=credit,debit=0,credit=value)])
    return entry

def finance_summary(db,actor,invoice):
    adjustments=Decimal(db.scalar(select(func.coalesce(func.sum(InvoiceAdjustment.amount),0)).where(InvoiceAdjustment.invoice_id==invoice.id)))
    receipt_ids=list(db.scalars(select(Receipt.id).where(Receipt.invoice_id==invoice.id, Receipt.status.in_(['posted','refund_requested','refund_approved','refunded','reversed']))))
    gross=Decimal(db.scalar(select(func.coalesce(func.sum(Receipt.amount),0)).where(Receipt.id.in_(receipt_ids))))
    refunded=Decimal(db.scalar(select(func.coalesce(func.sum(Refund.amount),0)).where(Refund.receipt_id.in_(receipt_ids),Refund.status=='refunded')))
    allocated=Decimal(db.scalar(select(func.coalesce(func.sum(Allocation.amount),0)).where(Allocation.invoice_id==invoice.id)))
    released=Decimal(db.scalar(select(func.coalesce(func.sum(Refund.amount),0)).where(Refund.receipt_id.in_(receipt_ids),Refund.status=='refunded',Refund.release_allocation.is_(True))))
    claim=db.scalar(select(Claim).where(Claim.invoice_id==invoice.id))
    cost=Decimal(db.scalar(select(func.coalesce(func.sum(CostEntry.amount),0)).where(CostEntry.encounter_id==invoice.encounter_id,CostEntry.status=='posted')))
    return {k:str(amount(v)) for k,v in dict(billed=invoice.billed,submitted=claim.submitted if claim else ZERO,approved=claim.approved if claim else ZERO,gross_received=gross,refunded=refunded,net_received=gross-refunded,outstanding=invoice.billed+adjustments-allocated+released,cost=cost,adjustments=adjustments,allocated=allocated,allocation_released=released).items()}

class DTO(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
class InvoiceCreate(DTO):
    encounter_id: str
    label: str=Field(min_length=1,max_length=200)
class ClaimCreate(DTO):
    invoice_id: str
    payer_name: str=Field(min_length=1,max_length=200)
class ReceiptCreate(DTO):
    invoice_id: str
    payer_name: str=Field(min_length=1,max_length=200)
    amount: Decimal=Field(gt=0,max_digits=18,decimal_places=2)
class CostCreate(DTO):
    encounter_id: str|None=None
    department_id: str|None=None
    label: str=Field(min_length=1,max_length=200)
    amount: Decimal=Field(gt=0,max_digits=18,decimal_places=2)
    method_version: str=Field(min_length=1,max_length=100)
    source_movement_id: str|None=None
class PurchaseCreate(DTO):
    supplier_id: str
    item_id: str
    department_id: str|None=None
    quantity: Decimal=Field(gt=0,max_digits=18,decimal_places=3)
    unit_price: Decimal=Field(ge=0,max_digits=18,decimal_places=2)
class StockCreate(DTO):
    lot_id: str
    location_id: str
    quantity: Decimal=Field(max_digits=18,decimal_places=3)
    source_id: str=Field(min_length=1,max_length=160)
    original_movement_id: str|None=None
    disposition: Literal['available','quarantine']='available'
    @model_validator(mode='after')
    def nonzero(self):
        if self.quantity == 0:raise ValueError('Stock quantity must be nonzero')
        return self
class AssetCreate(DTO):
    name: str=Field(min_length=1,max_length=200)
    location_id: str
    department_id: str|None=None
class RosterCreate(DTO):
    staff_id: str
    starts_at: datetime
    ends_at: datetime
    @model_validator(mode='after')
    def dates(self):
        if not self.starts_at.tzinfo or not self.ends_at.tzinfo or self.ends_at<=self.starts_at: raise ValueError('Aware start/end and positive shift interval required')
        return self
class SupportCreate(DTO):
    kind: Literal['cssd','linen','facility']
    asset_id: str|None=None
    location_id: str|None=None
    cycle_code: str|None=Field(default=None,max_length=100)
    quantity: Decimal|None=Field(default=None,gt=0,max_digits=18,decimal_places=3)
    description: str|None=Field(default=None,max_length=2000)
    @model_validator(mode='after')
    def fields(self):
        required={'cssd':['asset_id','cycle_code'],'linen':['location_id','quantity'],'facility':['location_id','description']}[self.kind]
        if any(getattr(self,k) is None or getattr(self,k)=='' for k in required): raise ValueError('Required fields: '+', '.join(required))
        return self
class IncidentCreate(DTO):
    description: str=Field(min_length=1,max_length=4000)
    encounter_id: str|None=None
    asset_id: str|None=None
class ReportCreate(DTO):
    name: str=Field(min_length=1,max_length=200)
    period_start: date
    period_end: date
    @model_validator(mode='after')
    def dates(self):
        if self.period_end<self.period_start: raise ValueError('Invalid period')
        return self
class MessageCreate(DTO):
    source_id: str=Field(min_length=1,max_length=160)
    sequence: int=Field(ge=1,strict=True)
    contract_version: str=Field(min_length=1,max_length=100)
    kind: Literal['claim','referral','report','test']
    source_record_id: str=Field(min_length=1,max_length=64)
class DatasetCreate(DTO):
    name: str=Field(min_length=1,max_length=200)
    encounter_kind: Literal['OPD','IPD','ER']='OPD'

class Action(DTO):
    version: int=Field(ge=1,strict=True)
    action: str
class InvoiceAction(Action):
    price_version_id: str|None=None
    action: Literal['price','reprice','review','invoice','adjust','cancel']
    original_charge_id: str|None=None
    amount: Decimal|None=Field(default=None,max_digits=18,decimal_places=2)
    reason: str|None=Field(default=None,max_length=2000)
class ClaimAction(Action):
    action: Literal['validate','export','simulate_submit','remittance','reconcile']
    approved_amount: Decimal|None=Field(default=None,ge=0,max_digits=18,decimal_places=2)
    source_key: str|None=Field(default=None,max_length=160)
class ReceiptAction(Action):
    action: Literal['review','post','refund_request','refund_approve','refund','reverse']
    amount: Decimal|None=Field(default=None,gt=0,max_digits=18,decimal_places=2)
    refund_id: str|None=None
    reason: str|None=Field(default=None,max_length=2000)
    release_allocation: bool=False
class CostAction(Action):
    action: Literal['review','post','reverse']
class PurchaseAction(Action):
    action: Literal['approve','record_po','receive','verify_invoice','close']
    lot_id: str|None=None
    location_id: str|None=None
    quantity: Decimal|None=Field(default=None,gt=0,max_digits=18,decimal_places=3)
    receipt_key: str|None=Field(default=None,max_length=160)
class StockAction(Action):
    action: Literal['validate','post','reverse','transfer']
    quantity: Decimal|None=Field(default=None,gt=0,max_digits=18,decimal_places=3)
    location_id: str|None=None
    disposition: Literal['available','quarantine']='quarantine'
class AssetAction(Action):
    action: Literal['activate','schedule','start','record','verify','release','retire']
    maintenance_due: date|None=None
    evidence: str|None=Field(default=None,max_length=4000)
class RosterAction(Action):
    action: Literal['review','publish','acknowledge','revise']
    starts_at: datetime|None=None
    ends_at: datetime|None=None
class SupportAction(Action):
    action: Literal['clean','record_cycle','quarantine','review_release','release','return_linen','reconcile','assign','verify','close']
    evidence: str|None=Field(default=None,max_length=4000)
    returned_quantity: Decimal|None=Field(default=None,ge=0,max_digits=18,decimal_places=3)
    assignee_id: str|None=None
class IncidentAction(Action):
    action: Literal['triage','investigate','plan','evidence','review','close']
    classification: str|None=Field(default=None,max_length=100)
    case_definition_version: str|None=Field(default=None,max_length=100)
    owner_id: str|None=None
    action_plan: str|None=Field(default=None,max_length=4000)
    evidence: str|None=Field(default=None,max_length=4000)
class ReportAction(Action):
    action: Literal['generate','review','export','correct']
class MessageAction(Action):
    action: Literal['validate','queue','deliver','fail','retry','acknowledge']
class DatasetAction(Action):
    action: Literal['preview','approve','freeze','export','revoke']

MODELS={'D23':Invoice,'D24':Claim,'D25':Receipt,'D26':CostEntry,'D27':Purchase,'D28':StockMovement,'D29':EquipmentAsset,'D30':Roster,'D31':CSSDCycle,'D32':Incident,'D33':ReportBatch,'D35':IntegrationMessage,'D36':DatasetVersion}
CREATES={'D23':InvoiceCreate,'D24':ClaimCreate,'D25':ReceiptCreate,'D26':CostCreate,'D27':PurchaseCreate,'D28':StockCreate,'D29':AssetCreate,'D30':RosterCreate,'D31':SupportCreate,'D32':IncidentCreate,'D33':ReportCreate,'D35':MessageCreate,'D36':DatasetCreate}
ACTIONS={'D23':InvoiceAction,'D24':ClaimAction,'D25':ReceiptAction,'D26':CostAction,'D27':PurchaseAction,'D28':StockAction,'D29':AssetAction,'D30':RosterAction,'D31':SupportAction,'D32':IncidentAction,'D33':ReportAction,'D35':MessageAction,'D36':DatasetAction}

def must(body,*names):
    for name in names:
        if getattr(body,name,None) is None or getattr(body,name,None)=='': fail('Required action field: '+name,422)

def allowed(row,*states):
    if row.status not in states: fail('Invalid transition from '+row.status)

def detail(db,actor,domain,row):
    result=serialize(row)
    if domain=='D23': result.update(financials=finance_summary(db,actor,row),charges=[serialize(x) for x in db.scalars(select(Charge).where(Charge.invoice_id==row.id))],adjustments=[serialize(x) for x in db.scalars(select(InvoiceAdjustment).where(InvoiceAdjustment.invoice_id==row.id))])
    elif domain=='D24':
        inv=scoped(db,actor,Invoice,row.invoice_id); result['financials']=finance_summary(db,actor,inv);result['lines']=[serialize(x) for x in db.scalars(select(ClaimLine).where(ClaimLine.claim_id==row.id))]
    elif domain=='D25': result.update(refunds=[serialize(x) for x in db.scalars(select(Refund).where(Refund.receipt_id==row.id))],financials=finance_summary(db,actor,scoped(db,actor,Invoice,row.invoice_id)))
    elif domain=='D27': result['receipts']=[serialize(x) for x in db.scalars(select(GoodsReceipt).where(GoodsReceipt.purchase_id==row.id))]
    elif domain=='D29': result['maintenance']=[serialize(x) for x in db.scalars(select(MaintenanceWorkOrder).where(MaintenanceWorkOrder.asset_id==row.id))]
    elif domain=='D31': result['kind']='cssd' if isinstance(row,CSSDCycle) else ('linen' if isinstance(row,LinenDispatch) else 'facility')
    elif domain=='D32':
        if 'D32.restricted' not in actor.permissions: result.pop('reporter_id',None)
        capa=db.scalar(select(CAPA).where(CAPA.incident_id==row.id)); result['corrective_action']=serialize(capa) if capa else None
    elif domain=='D33':
        result['lineage']=[serialize(x) for x in db.scalars(select(ReportLineage).where(ReportLineage.batch_id==row.id))]
        result['acknowledgments']=[serialize(x) for x in db.scalars(select(ReportAcknowledgment).where(ReportAcknowledgment.batch_id==row.id))]
        result['quality_errors']=[] if row.summary is not None else [{'code':'NOT_GENERATED','message':'Generate before checking source lineage'}]
    elif domain=='D35':
        result['attempts']=[serialize(x) for x in db.scalars(select(DeliveryAttempt).where(DeliveryAttempt.message_id==row.id))]
        result['reconciliation_tasks']=[serialize(x) for x in db.scalars(select(ReconciliationTask).where(ReconciliationTask.message_id==row.id))]
        result['external_integration_status']='NOT_CONNECTED'
    elif domain=='D36':
        result['row_count']=db.scalar(select(func.count()).select_from(DatasetRow).where(DatasetRow.dataset_id==row.id))
        result['download_available']=row.status in ('frozen','exported') and 'D36.export' in actor.permissions and bool(db.scalar(select(DatasetAccess).where(DatasetAccess.dataset_id==row.id,DatasetAccess.user_id==actor.user_id,DatasetAccess.status=='active')))
        if row.status in ('draft','previewed','approved'):
            result['candidate_count']=db.scalar(select(func.count()).select_from(Encounter).where(Encounter.organization_id==actor.organization_id,Encounter.facility_id==actor.facility_id,Encounter.kind==row.encounter_kind))
    return result

def get_record(db,actor,domain,record_id,lock=False):
    if domain!='D31':
        row=scoped(db,actor,MODELS[domain],record_id,lock)
        if domain=='D30' and not {'quality','hr_officer','roster_manager','quality_officer','auditor','system_admin'}.intersection(actor.roles):
            staff=scoped(db,actor,StaffMember,row.staff_id)
            if staff.user_id!=actor.user_id:fail('Record not found',404)
        return row
    for model in (CSSDCycle,LinenDispatch,FacilityWorkOrder):
        q=select(model).where(model.id==record_id,model.organization_id==actor.organization_id,model.facility_id==actor.facility_id)
        if lock:q=q.with_for_update()
        row=db.scalar(q)
        if row:return row
    fail('Record not found',404)

def create_record(db,actor,domain,body,key):
    data=body.model_dump()
    if domain=='D23':
        scoped_encounter(db,actor,body.encounter_id);row=Invoice(**values(actor,**data,status='open',billed=0))
    elif domain=='D24':
        inv=scoped(db,actor,Invoice,body.invoice_id,True);allowed(inv,'invoiced','adjusted');enc=scoped_encounter(db,actor,inv.encounter_id)
        if db.scalar(select(Claim).where(Claim.invoice_id==inv.id)):fail('Invoice already has a claim')
        row=Claim(**values(actor,**data,patient_id=enc.patient_id,encounter_id=enc.id,status='draft',submitted=0,approved=0));db.add(row);db.flush()
        for ch in db.scalars(select(Charge).where(Charge.invoice_id==inv.id)):db.add(ClaimLine(**values(actor,claim_id=row.id,charge_id=ch.id,billed=ch.amount,status='draft')))
    elif domain=='D25':
        inv=scoped(db,actor,Invoice,body.invoice_id,True);allowed(inv,'invoiced','adjusted');row=Receipt(**values(actor,**data,recorded_by=actor.user_id,status='draft'))
    elif domain=='D26':
        reference(db,actor,Encounter,body.encounter_id);reference(db,actor,Department,body.department_id);reference(db,actor,StockMovement,body.source_movement_id)
        row=CostEntry(**values(actor,**data,status='draft'))
    elif domain=='D27':
        reference(db,actor,Supplier,body.supplier_id);reference(db,actor,InventoryItem,body.item_id);reference(db,actor,Department,body.department_id)
        row=Purchase(**values(actor,**data,requested_by=actor.user_id,status='draft',received_quantity=0))
    elif domain=='D28':
        reference(db,actor,InventoryLot,body.lot_id);reference(db,actor,StockLocation,body.location_id)
        row=StockMovement(**values(actor,**data,operation_key=key,status='draft'))
    elif domain=='D29':
        reference(db,actor,Location,body.location_id);reference(db,actor,Department,body.department_id)
        row=EquipmentAsset(**values(actor,**data,status='registered'))
    elif domain=='D30':
        require_role(actor,'quality','hr_officer','roster_manager','quality_officer')
        scoped(db,actor,StaffMember,body.staff_id,True);row=Roster(**values(actor,**data,status='draft'))
    elif domain=='D31':
        if body.kind=='cssd':
            reference(db,actor,EquipmentAsset,body.asset_id);row=CSSDCycle(**values(actor,asset_id=body.asset_id,cycle_code=body.cycle_code,operator_id=actor.user_id,status='received'))
        elif body.kind=='linen':
            reference(db,actor,Location,body.location_id);row=LinenDispatch(**values(actor,location_id=body.location_id,quantity=body.quantity,returned_quantity=0,status='issued'))
        else:
            reference(db,actor,Location,body.location_id);row=FacilityWorkOrder(**values(actor,location_id=body.location_id,description=body.description,status='opened'))
    elif domain=='D32':
        reference(db,actor,Encounter,body.encounter_id);reference(db,actor,EquipmentAsset,body.asset_id)
        row=Incident(**values(actor,**data,reporter_id=actor.user_id,status='reported'))
    elif domain=='D33': row=ReportBatch(**values(actor,**data,status='draft',definition_version='encounters-by-status-v1'))
    elif domain=='D35':
        # A durable inbox, not an external transmission. Invalid contract can enter error queue.
        previous=db.scalar(select(IntegrationMessage).where(IntegrationMessage.organization_id==actor.organization_id,IntegrationMessage.source_id==body.source_id,IntegrationMessage.sequence==body.sequence))
        content_hash=digest(data)
        if previous:
            if previous.facility_id!=actor.facility_id:fail('Source message identity unavailable',409)
            if previous.content_hash!=content_hash:fail('Source message identity reused with different content')
            return previous
        row=IntegrationMessage(**values(actor,**data,content_hash=content_hash,status='received'))
    elif domain=='D36': row=DatasetVersion(**values(actor,**data,status='draft'))
    else: fail('Unknown domain',404)
    db.add(row);db.flush()
    if domain=='D36':
        db.add(DatasetAccess(**values(actor,dataset_id=row.id,user_id=actor.user_id,granted_by=actor.user_id,purpose='Creator access for synthetic dataset evaluation',status='active')));db.flush()
    return row

def act_record(db,actor,domain,row,b,key):
    a=b.action
    if domain=='D23':
        if a=='price':
            allowed(row,'open');charges=list(db.scalars(select(Charge).where(Charge.encounter_id==row.encounter_id,Charge.invoice_id.is_(None)).with_for_update()))
            if not charges:fail('Add a charge before pricing')
            row.billed=sum((ch.amount for ch in charges),ZERO)
            for ch in charges:ch.invoice_id=row.id
            set_state(row,'priced')
        elif a=='reprice':
            allowed(row,'priced');must(b,'price_version_id','original_charge_id')
            price=scoped(db,actor,PriceVersion,b.price_version_id);charge=scoped(db,actor,Charge,b.original_charge_id,True)
            if charge.invoice_id!=row.id or price.effective_from>date.today():fail('Charge/price is not eligible for draft repricing')
            charge.price_version_id=price.id;charge.unit_price=price.unit_price;charge.amount=amount(charge.quantity*price.unit_price);charge.version+=1;db.flush()
            row.billed=Decimal(db.scalar(select(func.sum(Charge.amount)).where(Charge.invoice_id==row.id)));row.version+=1
        elif a=='review':allowed(row,'priced');set_state(row,'reviewed')
        elif a=='invoice':allowed(row,'reviewed');set_state(row,'invoiced')
        elif a=='cancel':allowed(row,'open');set_state(row,'cancelled')
        else:
            allowed(row,'invoiced','adjusted');must(b,'original_charge_id','amount','reason')
            require_role(actor,'billing','billing_officer','pricing_admin')
            charge=scoped(db,actor,Charge,b.original_charge_id,True)
            if charge.invoice_id!=row.id:fail('Original charge belongs to a different invoice')
            adjusted=Decimal(db.scalar(select(func.coalesce(func.sum(InvoiceAdjustment.amount),0)).where(InvoiceAdjustment.invoice_id==row.id)))
            if row.billed+adjusted+b.amount<0:fail('Adjustment exceeds billed amount')
            db.add(InvoiceAdjustment(**values(actor,invoice_id=row.id,original_charge_id=charge.id,amount=b.amount,reason=b.reason,approver_id=actor.user_id,status='posted')));set_state(row,'adjusted')
    elif domain=='D24':
        if a=='validate':
            allowed(row,'draft');invoice=scoped(db,actor,Invoice,row.invoice_id)
            if not db.scalar(select(ClaimLine).where(ClaimLine.claim_id==row.id)):fail('Claim lines required')
            if invoice.billed<=0:fail('Positive billed amount required')
            set_state(row,'validated')
        elif a=='export':allowed(row,'validated');require(actor,'D24.export');row.exported_at=utcnow();set_state(row,'exported')
        elif a=='simulate_submit':
            allowed(row,'exported');row.submitted=scoped(db,actor,Invoice,row.invoice_id).billed;set_state(row,'simulated_submitted')
        elif a=='remittance':
            allowed(row,'simulated_submitted');must(b,'approved_amount','source_key')
            if b.approved_amount>row.submitted:fail('Approved amount exceeds submitted amount')
            if db.scalar(select(Remittance).where(Remittance.organization_id==actor.organization_id,Remittance.source_key==b.source_key)):fail('Remittance source already imported')
            db.add(Remittance(**values(actor,claim_id=row.id,source_key=b.source_key,approved_amount=b.approved_amount,synthetic=True,status='recorded')))
            row.approved=b.approved_amount;set_state(row,'adjudicated')
        else:allowed(row,'adjudicated');set_state(row,'reconciliation_reviewed')
    elif domain=='D25':
        invoice=scoped(db,actor,Invoice,row.invoice_id,True)
        if a=='review':allowed(row,'draft');set_state(row,'reviewed')
        elif a=='post':
            allowed(row,'reviewed')
            outstanding=Decimal(finance_summary(db,actor,invoice)['outstanding'])
            if row.amount>outstanding:fail('Receipt exceeds outstanding receivable; no unallocated cash flow in this prototype')
            ledger(db,actor,row.id,'receipt',row.amount,'cash','receivable')
            db.add(Allocation(**values(actor,receipt_id=row.id,invoice_id=invoice.id,amount=row.amount,status='posted')));set_state(row,'posted')
        elif a=='refund_request':
            allowed(row,'posted','refunded');must(b,'amount','reason')
            existing=Decimal(db.scalar(select(func.coalesce(func.sum(Refund.amount),0)).where(Refund.receipt_id==row.id,Refund.status.in_(['refund_requested','refund_approved','refunded']))))
            if existing+b.amount>row.amount:fail('Refund exceeds remaining receipt amount')
            db.add(Refund(**values(actor,receipt_id=row.id,amount=b.amount,reason=b.reason,requested_by=actor.user_id,release_allocation=b.release_allocation,status='refund_requested')));set_state(row,'refund_requested')
        elif a=='refund_approve':
            allowed(row,'refund_requested');must(b,'refund_id');require_role(actor,'refund_approver','finance')
            refund=scoped(db,actor,Refund,b.refund_id,True)
            if refund.receipt_id!=row.id or refund.status!='refund_requested':fail('Refund does not match request')
            if refund.requested_by==actor.user_id:fail('Refund requester cannot approve own refund',403)
            refund.approved_by=actor.user_id;set_state(refund,'refund_approved');set_state(row,'refund_approved')
        elif a=='refund':
            allowed(row,'refund_approved');must(b,'refund_id');refund=scoped(db,actor,Refund,b.refund_id,True)
            if refund.receipt_id!=row.id or refund.status!='refund_approved':fail('Refund not approved')
            # Release allocation is an explicit recorded policy choice, not inferred from cash refund.
            ledger(db,actor,refund.id,'refund',refund.amount,'receivable' if refund.release_allocation else 'refund_expense','cash')
            set_state(refund,'refunded');set_state(row,'refunded')
        elif a=='reverse':
            allowed(row,'posted');must(b,'reason');require_role(actor,'accountant','finance')
            if db.scalar(select(Refund).where(Refund.receipt_id==row.id)):fail('Cannot reverse receipt with refund history')
            refund=Refund(**values(actor,receipt_id=row.id,amount=row.amount,reason=b.reason,requested_by=actor.user_id,approved_by=actor.user_id,release_allocation=True,status='refunded'));db.add(refund);db.flush()
            original=db.scalar(select(LedgerEntry).where(LedgerEntry.source_id==row.id))
            ledger(db,actor,refund.id,'reversal',row.amount,'receivable','cash',original.id if original else None);set_state(row,'reversed')
    elif domain=='D26':
        require_role(actor,'finance','cost_accountant','accountant')
        if a=='review':allowed(row,'draft');set_state(row,'reviewed')
        elif a=='post':allowed(row,'reviewed');set_state(row,'posted')
        else:
            allowed(row,'posted')
            if db.scalar(select(CostEntry).where(CostEntry.original_id==row.id)):fail('Cost already reversed')
            db.add(CostEntry(**values(actor,encounter_id=row.encounter_id,department_id=row.department_id,source_movement_id=row.source_movement_id,label='Reversal: '+row.label,amount=-row.amount,method_version=row.method_version,original_id=row.id,status='posted')))
            # Original posted amount/status stays immutable. Version changes for action concurrency only.
            row.version+=1
    elif domain=='D27':
        if a=='approve':
            allowed(row,'draft');require_role(actor,'purchase_approver','inventory','procurement')
            if row.requested_by==actor.user_id:fail('Purchase requester cannot approve own request',403)
            row.approved_by=actor.user_id;set_state(row,'approved')
        elif a=='record_po':allowed(row,'approved');set_state(row,'po_recorded')
        elif a=='receive':
            allowed(row,'po_recorded','part_received');must(b,'quantity','lot_id','location_id','receipt_key')
            lot=scoped(db,actor,InventoryLot,b.lot_id,True)
            if lot.item_id!=row.item_id:fail('Receipt lot does not match ordered item')
            if row.received_quantity+b.quantity>row.quantity:fail('Receipt exceeds ordered quantity')
            if db.scalar(select(GoodsReceipt).where(GoodsReceipt.organization_id==actor.organization_id,GoodsReceipt.receipt_key==b.receipt_key)):fail('Receipt key already posted')
            movement=post_stock_movement(db,actor,lot.id,b.location_id,b.quantity,row.id,'purchase:'+b.receipt_key)
            db.add(GoodsReceipt(**values(actor,purchase_id=row.id,lot_id=lot.id,movement_id=movement.id,quantity=b.quantity,amount=amount(b.quantity*row.unit_price),receipt_key=b.receipt_key,status='posted')))
            row.received_quantity+=b.quantity;set_state(row,'received' if row.received_quantity==row.quantity else 'part_received')
        elif a=='verify_invoice':
            allowed(row,'received');db.add(SupplierObligation(**values(actor,purchase_id=row.id,supplier_id=row.supplier_id,amount=amount(row.received_quantity*row.unit_price),status='verified')));set_state(row,'invoice_verified')
        else:allowed(row,'invoice_verified');set_state(row,'closed')
    elif domain=='D28':
        if a=='validate':
            allowed(row,'draft')
            if row.quantity<0:get_eligible_lot(db,actor,row.lot_id)
            set_state(row,'validated')
        elif a=='post':
            allowed(row,'validated')
            # Same invariants as post_stock_movement, but retain draft ID for history.
            draft_key=row.operation_key;row.operation_key='draft:'+row.id;db.flush()
            posted=post_stock_movement(db,actor,row.lot_id,row.location_id,row.quantity,row.source_id,draft_key,row.original_movement_id,row.disposition)
            row.status='posted_reference';row.version+=1
            return posted
        elif a=='reverse':
            allowed(row,'posted');must(b,'quantity')
            post_stock_movement(db,actor,row.lot_id,row.location_id,-b.quantity if row.quantity>0 else b.quantity,row.id,key,row.id,b.disposition if row.quantity<0 else 'available')
            row.version+=1
        else:
            allowed(row,'posted');must(b,'quantity','location_id')
            if b.location_id==row.location_id:fail('Transfer needs a different location')
            post_stock_movement(db,actor,row.lot_id,row.location_id,-b.quantity,row.id,key+':out')
            post_stock_movement(db,actor,row.lot_id,b.location_id,b.quantity,row.id,key+':in');row.version+=1
    elif domain=='D29':
        work=db.scalar(select(MaintenanceWorkOrder).where(MaintenanceWorkOrder.asset_id==row.id).order_by(MaintenanceWorkOrder.created_at.desc()))
        if a=='activate':allowed(row,'registered');set_state(row,'in_service')
        elif a=='schedule':allowed(row,'in_service');must(b,'maintenance_due');row.maintenance_due=b.maintenance_due;set_state(row,'maintenance_due')
        elif a=='start':
            allowed(row,'maintenance_due');db.add(MaintenanceWorkOrder(**values(actor,asset_id=row.id,technician_id=actor.user_id,status='under_maintenance')));set_state(row,'under_maintenance')
        elif a=='record':allowed(row,'under_maintenance');must(b,'evidence');work.evidence=b.evidence;row.version+=1
        elif a=='verify':
            allowed(row,'under_maintenance');require_role(actor,'biomedical_engineer','quality','quality_officer','inventory')
            if not work or not work.evidence:fail('Recorded maintenance evidence required')
            work.verifier_id=actor.user_id;set_state(work,'verified');set_state(row,'verified')
        elif a=='release':allowed(row,'verified');set_state(row,'in_service')
        else:allowed(row,'in_service');set_state(row,'retired')
    elif domain=='D30':
        if a!='acknowledge':require_role(actor,'quality','hr_officer','roster_manager','quality_officer')
        staff=scoped(db,actor,StaffMember,row.staff_id,True)
        if a=='review':
            allowed(row,'draft')
            overlap=db.scalar(select(Roster).where(Roster.staff_id==row.staff_id,Roster.id!=row.id,Roster.status.in_(['reviewed','published','acknowledged']),Roster.starts_at<row.ends_at,Roster.ends_at>row.starts_at))
            if overlap:fail('Roster shift overlaps existing reviewed or published shift')
            if staff.credential_status!='active' or staff.credential_valid_until<row.ends_at.date():fail('Credential invalid for shift')
            set_state(row,'reviewed')
        elif a=='publish':allowed(row,'reviewed');set_state(row,'published')
        elif a=='acknowledge':
            allowed(row,'published')
            if staff.user_id!=actor.user_id:fail('Only assigned staff can acknowledge shift',403)
            set_state(row,'acknowledged')
        else:
            allowed(row,'published','acknowledged');must(b,'starts_at','ends_at')
            validated=RosterCreate(staff_id=row.staff_id,starts_at=b.starts_at,ends_at=b.ends_at)
            revised=Roster(**values(actor,**validated.model_dump(),original_id=row.id,status='draft'));db.add(revised);row.version+=1;db.flush();return revised
    elif domain=='D31':
        if isinstance(row,CSSDCycle):
            if a=='clean':allowed(row,'received');set_state(row,'cleaned')
            elif a=='record_cycle':allowed(row,'cleaned');must(b,'evidence');row.evidence=b.evidence;set_state(row,'cycle_recorded')
            elif a=='quarantine':allowed(row,'cycle_recorded');set_state(row,'quarantined')
            elif a=='review_release':
                allowed(row,'cycle_recorded');require_role(actor,'cssd_release_reviewer','quality','quality_officer')
                if not row.evidence:fail('Cycle evidence required')
                row.reviewer_id=actor.user_id;set_state(row,'release_reviewed')
            elif a=='release':allowed(row,'release_reviewed');set_state(row,'released')
            else:fail('Action does not apply to CSSD cycle',422)
        elif isinstance(row,LinenDispatch):
            if a=='return_linen':
                allowed(row,'issued');must(b,'returned_quantity')
                if b.returned_quantity>row.quantity:fail('Return exceeds issued linen')
                row.returned_quantity=b.returned_quantity;set_state(row,'returned')
            elif a=='reconcile':allowed(row,'returned');set_state(row,'reconciled')
            else:fail('Action does not apply to linen',422)
        else:
            if a=='assign':allowed(row,'opened');must(b,'assignee_id');reference(db,actor,User,b.assignee_id);row.assignee_id=b.assignee_id;set_state(row,'assigned')
            elif a=='verify':allowed(row,'assigned');must(b,'evidence');row.evidence=b.evidence;set_state(row,'verified')
            elif a=='close':allowed(row,'verified');set_state(row,'closed')
            else:fail('Action does not apply to facility work order',422)
    elif domain=='D32':
        capa=db.scalar(select(CAPA).where(CAPA.incident_id==row.id))
        if a=='triage':allowed(row,'reported');must(b,'classification');row.classification=b.classification;row.case_definition_version=b.case_definition_version;set_state(row,'triaged')
        elif a=='investigate':allowed(row,'triaged');set_state(row,'investigating')
        elif a=='plan':
            allowed(row,'investigating');must(b,'owner_id','action_plan');reference(db,actor,User,b.owner_id)
            db.add(CAPA(**values(actor,incident_id=row.id,owner_id=b.owner_id,action_plan=b.action_plan,status='assigned')));set_state(row,'action_planned')
        elif a=='evidence':
            allowed(row,'action_planned');must(b,'evidence')
            if capa.owner_id!=actor.user_id:fail('CAPA owner must submit evidence',403)
            capa.evidence=b.evidence;set_state(capa,'evidence_recorded');set_state(row,'effectiveness_review')
        elif a=='review':
            allowed(row,'effectiveness_review');require_role(actor,'quality','quality_officer','risk_reviewer')
            if not capa or not capa.evidence:fail('CAPA evidence required')
            if capa.owner_id==actor.user_id:fail('Independent effectiveness reviewer required',403)
            capa.reviewer_id=actor.user_id;set_state(capa,'effectiveness_verified');row.version+=1
        else:
            allowed(row,'effectiveness_review')
            if not capa or not capa.reviewer_id:fail('Effectiveness review required')
            set_state(capa,'closed');set_state(row,'closed')
    elif domain=='D33':
        if a=='generate':
            allowed(row,'draft');encounters=list(db.scalars(select(Encounter).where(Encounter.organization_id==actor.organization_id,Encounter.facility_id==actor.facility_id,func.date(Encounter.created_at)>=row.period_start,func.date(Encounter.created_at)<=row.period_end)))
            summary={}
            for enc in encounters:
                summary[enc.status]=summary.get(enc.status,0)+1;db.add(ReportLineage(batch_id=row.id,encounter_id=enc.id,source_version=enc.version,source_status=enc.status))
            row.summary={'total_encounters':len(encounters),'by_status':summary,'missing_status':None,'definition_version':row.definition_version};set_state(row,'generated')
        elif a=='review':allowed(row,'generated');set_state(row,'reviewed')
        elif a=='export':allowed(row,'reviewed');require(actor,'D33.export');set_state(row,'exported')
        else:
            allowed(row,'exported');new=ReportBatch(**values(actor,name=row.name+' correction',period_start=row.period_start,period_end=row.period_end,definition_version=row.definition_version,original_id=row.id,status='draft'));db.add(new);db.flush();return new
    elif domain=='D35':
        if a=='validate':
            allowed(row,'received')
            earlier=db.scalar(select(func.max(IntegrationMessage.sequence)).where(IntegrationMessage.organization_id==actor.organization_id,IntegrationMessage.source_id==row.source_id,IntegrationMessage.id!=row.id,IntegrationMessage.status.in_(['validated','queued','delivered_local','acknowledged_local'])))
            expected=(earlier or 0)+1
            if row.contract_version!='his-local-event-v1' or row.sequence!=expected:
                row.error='Invalid contract version or out-of-order sequence';set_state(row,'rejected')
            else:
                if row.kind!='test':
                    from ..models_clinical import Referral
                    reference(db,actor,{'claim':Claim,'report':ReportBatch,'referral':Referral}[row.kind],row.source_record_id)
                set_state(row,'validated')
        elif a=='queue':allowed(row,'validated');set_state(row,'queued')
        elif a=='deliver':
            allowed(row,'queued')
            receipt=db.scalar(select(IntegrationReceipt).where(IntegrationReceipt.message_id==row.id))
            if not receipt:
                receipt=IntegrationReceipt(**values(actor,message_id=row.id,source_record_id=row.source_record_id,receipt_kind=row.kind,status='accepted_local'));db.add(receipt);db.flush()
                db.add(ReconciliationTask(**values(actor,message_id=row.id,integration_receipt_id=receipt.id,title='Review locally delivered '+row.kind,status='pending')))
            db.add(DeliveryAttempt(**values(actor,message_id=row.id,outcome='delivered_local',status='completed')));set_state(row,'delivered_local')
        elif a=='fail':allowed(row,'queued');db.add(DeliveryAttempt(**values(actor,message_id=row.id,outcome='simulated_failure',status='failed')));set_state(row,'failed')
        elif a=='retry':allowed(row,'failed');set_state(row,'queued')
        else:
            allowed(row,'delivered_local');task=db.scalar(select(ReconciliationTask).where(ReconciliationTask.message_id==row.id).with_for_update())
            if not task:fail('Local delivery receipt missing')
            set_state(task,'reconciled');set_state(row,'acknowledged_local')
    elif domain=='D36':
        if a=='preview':allowed(row,'draft');set_state(row,'previewed')
        elif a=='approve':allowed(row,'previewed');require_role(actor,'dataset_reviewer','quality','analyst','quality_officer');set_state(row,'approved')
        elif a=='freeze':
            allowed(row,'approved');encounters=list(db.scalars(select(Encounter).where(Encounter.organization_id==actor.organization_id,Encounter.facility_id==actor.facility_id,Encounter.kind==row.encounter_kind).order_by(Encounter.id)))
            snapshot=[]
            for enc in encounters:
                data={'patient_id':enc.patient_id,'encounter_id':enc.id,'status':enc.status,'kind':enc.kind,'source_version':enc.version}
                partition='test' if int(hashlib.sha256(enc.patient_id.encode()).hexdigest(),16)%5==0 else 'train'
                snapshot.append(dict(data,partition=partition));db.add(DatasetRow(dataset_id=row.id,patient_id=enc.patient_id,encounter_id=enc.id,source_version=enc.version,partition=partition,snapshot=data))
            row.snapshot_hash=digest(snapshot);set_state(row,'frozen')
        elif a=='export':
            allowed(row,'frozen');require(actor,'D36.export')
            if not db.scalar(select(DatasetAccess).where(DatasetAccess.dataset_id==row.id,DatasetAccess.user_id==actor.user_id,DatasetAccess.status=='active')):fail('Dataset access grant required',403)
            set_state(row,'exported')
        else:allowed(row,'frozen','exported');set_state(row,'revoked')
    db.flush();return row

# Separate typed resource forms supply the catalogs and references used in primary workflows.
class PriceCreate(DTO):
    name:str=Field(min_length=1,max_length=200)
    effective_from:date
    unit_price:Decimal=Field(ge=0,max_digits=18,decimal_places=2)
class CoverageCreate(DTO):
    patient_id:str
    payer_name:str=Field(min_length=1,max_length=200)
    evidence:str=Field(min_length=1,max_length=2000)
class ChargeCreate(DTO):
    encounter_id:str
    source_id:str=Field(min_length=1,max_length=160)
    label:str=Field(min_length=1,max_length=200)
    quantity:Decimal=Field(gt=0,max_digits=18,decimal_places=3)
    price_version_id:str
class SupplierCreate(DTO):
    name:str=Field(min_length=1,max_length=200)
class ItemCreate(DTO):
    name:str=Field(min_length=1,max_length=200)
    unit:str=Field(min_length=1,max_length=30)
class LotCreate(DTO):
    item_id:str
    lot_number:str=Field(min_length=1,max_length=100)
    expiry_date:date
    unit_cost:Decimal=Field(ge=0,max_digits=18,decimal_places=2)
class StockLocationCreate(DTO):
    name:str=Field(min_length=1,max_length=200)
class StaffCreate(DTO):
    user_id:str
    department_id:str
    credential_valid_until:date
    privilege:str=Field(pattern=r'^D\d{2}\.(write|action)$|^clinical\.approve$|^orders\.sign$')
class CredentialAction(DTO):
    version:int=Field(ge=1,strict=True)
    status:Literal['active','suspended']
    reason:str=Field(min_length=1,max_length=2000)
class BudgetCreate(DTO):
    department_id:str
    period:str=Field(pattern=r'^\d{4}(-(?:0[1-9]|1[0-2]))?$')
    amount:Decimal=Field(gt=0,max_digits=18,decimal_places=2)
    method_version:str=Field(min_length=1,max_length=100)
SUPPORT={
    'prices':('D23',PriceVersion,PriceCreate),'coverage':('D23',CoverageRecord,CoverageCreate),'charges':('D23',Charge,ChargeCreate),
    'suppliers':('D27',Supplier,SupplierCreate),'items':('D28',InventoryItem,ItemCreate),'lots':('D28',InventoryLot,LotCreate),
    'stock-locations':('D28',StockLocation,StockLocationCreate),'staff':('D30',StaffMember,StaffCreate),'budgets':('D26',BudgetVersion,BudgetCreate),
}

def create_support(db,actor,resource,body,key):
    domain,model,_=SUPPORT[resource];data=body.model_dump()
    if resource=='coverage':reference(db,actor,Patient,body.patient_id)
    if resource=='charges':
        price=scoped(db,actor,PriceVersion,body.price_version_id)
        if price.effective_from>date.today():fail('Price is not yet effective')
        return add_charge(db,actor,body.encounter_id,body.source_id,body.label,body.quantity,price.unit_price,key,price.id)
    if resource=='lots':reference(db,actor,InventoryItem,body.item_id)
    if resource=='staff':
        require_role(actor,'quality','hr_officer','roster_manager','quality_officer')
        reference(db,actor,User,body.user_id);reference(db,actor,Department,body.department_id)
        if db.scalar(select(StaffMember).where(StaffMember.user_id==body.user_id)):fail('Staff already registered')
    if resource=='budgets':reference(db,actor,Department,body.department_id)
    row=model(**values(actor,**data,status='available' if resource=='lots' else 'active'));db.add(row);db.flush();return row

@router.get('/erp/catalog')
def catalog(actor=Depends(current_actor)):
    import json
    from pathlib import Path
    entries=json.loads(Path(__file__).with_name('erp_catalog.json').read_text())
    return {'domains':[entry for entry in entries if entry['id']+'.read' in actor.permissions]}

@router.get('/erp/options/{resource}')
def options(resource:str,actor=Depends(current_actor),db=Depends(get_db,scope='function')):
    mapping={k:v[:2] for k,v in SUPPORT.items()}
    mapping.update({'invoices':('D23',Invoice),'receipts':('D25',Receipt),'assets':('D29',EquipmentAsset),'movements':('D28',StockMovement),'reports':('D33',ReportBatch),'datasets':('D36',DatasetVersion)})
    # Related lookup privileges are bounded to consumers; no unrestricted arbitrary-table endpoint.
    consumers={'suppliers':['D27'],'items':['D27','D28','D08','D15'],'lots':['D27','D28','D08','D15'],'stock-locations':['D27','D28','D08'],'prices':['D23'],'staff':['D30'],'assets':['D11','D12','D13','D29','D31','D32'],'invoices':['D23','D24','D25'],'receipts':['D25'],'movements':['D26','D28']}
    if resource not in mapping:fail('Unknown lookup',404)
    dom,model=mapping[resource]
    if not any(d+'.read' in actor.permissions for d in consumers.get(resource,[dom])):fail('Lookup permission denied',403)
    return {'items':[serialize(x) for x in rows(db,actor,model)]}

@router.get('/erp/stock')
def stock(actor=Depends(current_actor),db=Depends(get_db,scope='function')):
    if not any(d+'.read' in actor.permissions for d in ('D08','D27','D28')):fail('Stock permission required',403)
    lot_ids=[x.id for x in rows(db,actor,InventoryLot)]
    location_ids=[x.id for x in rows(db,actor,StockLocation)]
    return {'items':[serialize(x) for x in db.scalars(select(StockBalance).where(StockBalance.lot_id.in_(lot_ids),StockBalance.location_id.in_(location_ids)))]}

@router.get('/erp/ledger')
def journal(actor=Depends(current_actor),db=Depends(get_db,scope='function')):
    require_domain(actor,'D25');entries=rows(db,actor,LedgerEntry)
    return {'items':[dict(serialize(e),lines=[serialize(l) for l in db.scalars(select(LedgerLine).where(LedgerLine.entry_id==e.id))]) for e in entries]}

@router.post('/erp/staff/{record_id}/credential')
def credential(record_id:str,body:CredentialAction,actor=Depends(current_actor),db=Depends(get_db,scope='function'),idempotency_key:str=Header(alias='Idempotency-Key')):
    revalidate_actor(db,actor);require_domain(actor,'D30',True);require_role(actor,'quality','credential_reviewer','quality_officer')
    row=scoped(db,actor,StaffMember,record_id,True);payload=dict(body.model_dump(mode='json'),record_id=record_id)
    old=begin_operation(db,actor,idempotency_key,'staff.credential',payload)
    if old:return old
    check_version(row,body.version)
    # Serialize against active transaction actor revalidation so privilege removal cannot race a write.
    db.scalar(select(User).where(User.id==row.user_id).with_for_update())
    row.credential_status=body.status;row.version+=1
    audit(db,actor,'D30',row.id,'credential.'+body.status,{'privilege':row.privilege,'reason':body.reason})
    return finish_operation(db,actor,idempotency_key,'staff.credential',payload,serialize(row))

def register_domain(domain):
    model=MODELS[domain];create_type=CREATES[domain];action_type=ACTIONS[domain]
    def listing(q:str='',actor=Depends(current_actor),db=Depends(get_db,scope='function')):
        require_domain(actor,domain)
        models=(CSSDCycle,LinenDispatch,FacilityWorkOrder) if domain=='D31' else (model,)
        result=[detail(db,actor,domain,r) for m in models for r in rows(db,actor,m)]
        if q:result=[r for r in result if q.casefold() in str(r).casefold()]
        return {'items':result}
    def reading(record_id:str,actor=Depends(current_actor),db=Depends(get_db,scope='function')):
        require_domain(actor,domain);return detail(db,actor,domain,get_record(db,actor,domain,record_id))
    def creating(body,actor=Depends(current_actor),db=Depends(get_db,scope='function'),idempotency_key:str=Header(alias='Idempotency-Key')):
        revalidate_actor(db,actor);require_domain(actor,domain,True)
        if not credential_allows(db,actor.user_id,domain+'.write'):fail('Credential privilege suspended or expired',403)
        payload=body.model_dump(mode='json');operation=domain+'.create'
        old=begin_operation(db,actor,idempotency_key,operation,payload)
        if old:return old
        row=create_record(db,actor,domain,body,idempotency_key)
        audit(db,actor,domain,row.id,'created',{'status':row.status})
        return finish_operation(db,actor,idempotency_key,operation,payload,detail(db,actor,domain,row))
    def acting(record_id:str,body,actor=Depends(current_actor),db=Depends(get_db,scope='function'),idempotency_key:str=Header(alias='Idempotency-Key')):
        revalidate_actor(db,actor);require_domain(actor,domain,True)
        if not credential_allows(db,actor.user_id,domain+'.write'):fail('Credential privilege suspended or expired',403)
        row=get_record(db,actor,domain,record_id,True)
        payload=dict(body.model_dump(mode='json'),record_id=record_id);operation=domain+'.'+body.action
        old=begin_operation(db,actor,idempotency_key,operation,payload)
        if old:return old
        check_version(row,body.version);old_status=row.status
        result=act_record(db,actor,domain,row,body,idempotency_key)
        audit(db,actor,domain,row.id,body.action,{'from':old_status,'to':row.status,'result_id':result.id})
        return finish_operation(db,actor,idempotency_key,operation,payload,detail(db,actor,domain,result))
    creating.__annotations__['body']=create_type;acting.__annotations__['body']=action_type
    router.add_api_route('/erp/'+domain+'/records',listing,methods=['GET'],name=domain+'_list')
    router.add_api_route('/erp/'+domain+'/records/{record_id}',reading,methods=['GET'],name=domain+'_detail')
    router.add_api_route('/erp/'+domain+'/records',creating,methods=['POST'],name=domain+'_create')
    router.add_api_route('/erp/'+domain+'/records/{record_id}/actions',acting,methods=['POST'],name=domain+'_action')

for _domain in MODELS:register_domain(_domain)

def register_support(resource):
    domain,model,dto=SUPPORT[resource]
    def listing(actor=Depends(current_actor),db=Depends(get_db,scope='function')):
        require_domain(actor,domain);return {'items':[serialize(x) for x in rows(db,actor,model)]}
    def creating(body,actor=Depends(current_actor),db=Depends(get_db,scope='function'),idempotency_key:str=Header(alias='Idempotency-Key')):
        revalidate_actor(db,actor);require_domain(actor,domain,True);payload=body.model_dump(mode='json');op='catalog.'+resource
        old=begin_operation(db,actor,idempotency_key,op,payload)
        if old:return old
        row=create_support(db,actor,resource,body,idempotency_key);audit(db,actor,domain,row.id,'catalog.created',{'resource':resource})
        return finish_operation(db,actor,idempotency_key,op,payload,serialize(row))
    creating.__annotations__['body']=dto
    router.add_api_route('/erp/'+resource,listing,methods=['GET'],name=resource+'_list')
    router.add_api_route('/erp/'+resource,creating,methods=['POST'],name=resource+'_create')
for _resource in SUPPORT:register_support(_resource)

@router.get('/erp/datasets/{record_id}/export')
def export_dataset(record_id:str,actor=Depends(current_actor),db=Depends(get_db,scope='function')):
    require(actor,'D36.export');row=scoped(db,actor,DatasetVersion,record_id)
    if not db.scalar(select(DatasetAccess).where(DatasetAccess.dataset_id==row.id,DatasetAccess.user_id==actor.user_id,DatasetAccess.status=='active')):fail('Dataset access grant required',403)
    allowed(row,'frozen','exported')
    audit(db,actor,'D36',row.id,'dataset.download')
    return {'dataset_id':row.id,'snapshot_hash':row.snapshot_hash,'items':[serialize(x) for x in db.scalars(select(DatasetRow).where(DatasetRow.dataset_id==row.id).order_by(DatasetRow.encounter_id))]}

def seed_erp(db):
    """Explicit deterministic seed; no reset/overwrite on restart or repeated invocation."""
    scope={'organization_id':'org-demo','facility_id':'facility-demo'}
    def ensure(model,identity,**fields):
        old=db.get(model,identity)
        if old:return old
        row=model(id=identity,**scope,**fields);db.add(row);db.flush();return row
    ensure(PriceVersion,'price-demo',name='ค่าบริการสังเคราะห์ v1',effective_from=date(2026,1,1),unit_price=Decimal('1000'),status='active')
    ensure(Supplier,'supplier-demo',name='ผู้ขายสังเคราะห์',status='active')
    ensure(InventoryItem,'item-demo',name='วัสดุสังเคราะห์สำหรับ POC',unit='unit',status='active')
    ensure(InventoryLot,'lot-demo',item_id='item-demo',lot_number='SYN-001',expiry_date=date(2035,12,31),unit_cost=Decimal('20'),status='available')
    ensure(StockLocation,'stock-main',name='คลังหลักสังเคราะห์',status='active')
    ensure(StockLocation,'stock-ward',name='คลังหอผู้ป่วยสังเคราะห์',status='active')
    if not db.get(StockMovement,'movement-opening'):
        ensure(StockMovement,'movement-opening',lot_id='lot-demo',location_id='stock-main',quantity=Decimal('100'),source_id='synthetic-opening-v1',operation_key='seed-opening-v1',status='posted',disposition='available')
        db.add(StockBalance(id='balance-opening',lot_id='lot-demo',location_id='stock-main',available=Decimal('100'),quarantined=0));db.flush()
    ensure(EquipmentAsset,'asset-demo',name='เครื่องมือสังเคราะห์',location_id='location-store',department_id='department-demo',status='in_service')
    for username in ('nurse','clinician','quality','inventory'):
        ensure(StaffMember,'staff-'+username,user_id='user-'+username,department_id='department-demo',credential_valid_until=date(2035,12,31),privilege='orders.sign' if username=='clinician' else 'D30.write',credential_status='active',status='active')
    ensure(BudgetVersion,'budget-demo',department_id='department-demo',period='2026',amount=Decimal('100000'),method_version='synthetic-budget-v1',status='active')

class ReservationCreate(DTO):
    task_id:str
    lot_id:str
    location_id:str
    quantity:Decimal=Field(gt=0,max_digits=18,decimal_places=3)
class ReservationAction(Action):
    action:Literal['cancel','consume']
class CountCreate(DTO):
    lot_id:str
    location_id:str
    counted_available:Decimal=Field(ge=0,max_digits=18,decimal_places=3)
    reason:str=Field(min_length=1,max_length=2000)
class CountAction(Action):
    action:Literal['approve','post']

@router.get('/erp/reservations')
def reservations(actor=Depends(current_actor),db=Depends(get_db,scope='function')):
    require_domain(actor,'D28');return {'items':[serialize(x) for x in rows(db,actor,StockReservation)]}
@router.post('/erp/reservations')
def reserve(body:ReservationCreate,actor=Depends(current_actor),db=Depends(get_db,scope='function'),idempotency_key:str=Header(alias='Idempotency-Key')):
    revalidate_actor(db,actor);require_domain(actor,'D28',True);payload=body.model_dump(mode='json');op='stock.reserve'
    old=begin_operation(db,actor,idempotency_key,op,payload)
    if old:return old
    task=scoped(db,actor,Task,body.task_id)
    scoped_encounter(db,actor,task.encounter_id)
    if task.status in ('completed','cancelled'):fail('Task does not accept reservation')
    get_eligible_lot(db,actor,body.lot_id);reference(db,actor,StockLocation,body.location_id)
    balance=db.scalar(select(StockBalance).where(StockBalance.lot_id==body.lot_id,StockBalance.location_id==body.location_id).with_for_update())
    reserved=Decimal(db.scalar(select(func.coalesce(func.sum(StockReservation.quantity),0)).where(StockReservation.lot_id==body.lot_id,StockReservation.location_id==body.location_id,StockReservation.status=='reserved')))
    if not balance or balance.available-reserved<body.quantity:fail('Insufficient unreserved stock')
    row=StockReservation(**values(actor,**body.model_dump(),status='reserved'));db.add(row);db.flush();audit(db,actor,'D28',row.id,'stock.reserved')
    return finish_operation(db,actor,idempotency_key,op,payload,serialize(row))
@router.post('/erp/reservations/{record_id}/actions')
def reservation_action(record_id:str,body:ReservationAction,actor=Depends(current_actor),db=Depends(get_db,scope='function'),idempotency_key:str=Header(alias='Idempotency-Key')):
    revalidate_actor(db,actor);require_domain(actor,'D28',True);payload=dict(body.model_dump(mode='json'),record_id=record_id);op='stock.reservation.'+body.action
    old=begin_operation(db,actor,idempotency_key,op,payload)
    if old:return old
    row=scoped(db,actor,StockReservation,record_id,True);check_version(row,body.version);allowed(row,'reserved')
    if body.action=='consume':
        task=scoped(db,actor,Task,row.task_id,True)
        scoped_encounter(db,actor,task.encounter_id)
        if task.status in ('completed','cancelled'):fail('Task no longer accepts stock consumption')
        movement=post_stock_movement(db,actor,row.lot_id,row.location_id,-row.quantity,row.task_id,idempotency_key,reservation_id=row.id);row.movement_id=movement.id;set_state(row,'consumed')
    else:set_state(row,'cancelled')
    audit(db,actor,'D28',row.id,op)
    return finish_operation(db,actor,idempotency_key,op,payload,serialize(row))
@router.get('/erp/counts')
def counts(actor=Depends(current_actor),db=Depends(get_db,scope='function')):
    require_domain(actor,'D28');return {'items':[serialize(x) for x in rows(db,actor,StockCount)]}
@router.post('/erp/counts')
def count_stock(body:CountCreate,actor=Depends(current_actor),db=Depends(get_db,scope='function'),idempotency_key:str=Header(alias='Idempotency-Key')):
    revalidate_actor(db,actor);require_domain(actor,'D28',True);payload=body.model_dump(mode='json');op='stock.count'
    old=begin_operation(db,actor,idempotency_key,op,payload)
    if old:return old
    get_eligible_lot(db,actor,body.lot_id);reference(db,actor,StockLocation,body.location_id)
    balance=db.scalar(select(StockBalance).where(StockBalance.lot_id==body.lot_id,StockBalance.location_id==body.location_id).with_for_update())
    row=StockCount(**values(actor,**body.model_dump(),observed_available=balance.available if balance else ZERO,counted_by=actor.user_id,status='draft'))
    db.add(row);db.flush();audit(db,actor,'D28',row.id,op)
    return finish_operation(db,actor,idempotency_key,op,payload,serialize(row))
@router.post('/erp/counts/{record_id}/actions')
def count_action(record_id:str,body:CountAction,actor=Depends(current_actor),db=Depends(get_db,scope='function'),idempotency_key:str=Header(alias='Idempotency-Key')):
    revalidate_actor(db,actor);require_domain(actor,'D28',True);payload=dict(body.model_dump(mode='json'),record_id=record_id);op='stock.count.'+body.action
    old=begin_operation(db,actor,idempotency_key,op,payload)
    if old:return old
    row=scoped(db,actor,StockCount,record_id,True);check_version(row,body.version)
    if body.action=='approve':
        allowed(row,'draft');require_role(actor,'stock_approver','purchase_approver','inventory')
        if actor.user_id==row.counted_by:fail('Independent count approval required',403)
        row.approved_by=actor.user_id;set_state(row,'validated')
    else:
        allowed(row,'validated');get_eligible_lot(db,actor,row.lot_id)
        balance=db.scalar(select(StockBalance).where(StockBalance.lot_id==row.lot_id,StockBalance.location_id==row.location_id).with_for_update())
        current=balance.available if balance else ZERO
        if current!=row.observed_available:fail('Stock changed since count; record a new count')
        delta=row.counted_available-row.observed_available
        if delta:
            movement=post_stock_movement(db,actor,row.lot_id,row.location_id,delta,row.id,idempotency_key);row.movement_id=movement.id
        set_state(row,'posted')
    audit(db,actor,'D28',row.id,op)
    return finish_operation(db,actor,idempotency_key,op,payload,serialize(row))

class BudgetAction(Action):
    action:Literal['review','post','reverse']
@router.post('/erp/budgets/{record_id}/actions')
def budget_action(record_id:str,body:BudgetAction,actor=Depends(current_actor),db=Depends(get_db,scope='function'),idempotency_key:str=Header(alias='Idempotency-Key')):
    revalidate_actor(db,actor);require_domain(actor,'D26',True);payload=dict(body.model_dump(mode='json'),record_id=record_id);op='budget.'+body.action
    old=begin_operation(db,actor,idempotency_key,op,payload)
    if old:return old
    row=scoped(db,actor,BudgetVersion,record_id,True);check_version(row,body.version)
    target={'review':('active','reviewed'),'post':('reviewed','posted'),'reverse':('posted','reversed')}[body.action]
    allowed(row,target[0]);set_state(row,target[1]);audit(db,actor,'D26',row.id,op)
    return finish_operation(db,actor,idempotency_key,op,payload,serialize(row))
@router.get('/erp/budget-variance')
def budget_variance(actor=Depends(current_actor),db=Depends(get_db,scope='function')):
    require_domain(actor,'D26');result=[]
    for budget in rows(db,actor,BudgetVersion):
        spent=Decimal(db.scalar(select(func.coalesce(func.sum(CostEntry.amount),0)).where(CostEntry.organization_id==actor.organization_id,CostEntry.facility_id==actor.facility_id,CostEntry.department_id==budget.department_id,CostEntry.status=='posted',func.to_char(CostEntry.created_at,'YYYY-MM' if len(budget.period)==7 else 'YYYY')==budget.period)))
        result.append({'budget_id':budget.id,'department_id':budget.department_id,'period':budget.period,'budget':str(budget.amount),'recorded_cost':str(amount(spent)),'variance':str(amount(budget.amount-spent)),'method_version':budget.method_version,'policy':'Recorded departmental costs by UTC creation year/month; manual method/version retained'})
    return {'items':result}

class ReportAckCreate(DTO):
    batch_id:str
    source_type:Literal['manual_receipt','local_stub']
    reference:str=Field(min_length=1,max_length=2000)
class AccessCreate(DTO):
    dataset_id:str
    user_id:str
    purpose:str=Field(min_length=1,max_length=2000)
class AccessAction(Action):
    action:Literal['revoke','restore']
@router.get('/erp/report-definitions')
def report_definitions(actor=Depends(current_actor)):
    require_domain(actor,'D33')
    return {'items':[{'id':'encounters-by-status-v1','version':1,'fields':['status','count'],'source':'encounters','period_policy':'UTC creation date inclusive','quality_policy':'Missing distinct from zero; required status validated in database','external_standard':'NOT_VERIFIED'}]}
@router.get('/erp/report-acknowledgments')
def report_acks(actor=Depends(current_actor),db=Depends(get_db,scope='function')):
    require_domain(actor,'D33');return {'items':[serialize(x) for x in rows(db,actor,ReportAcknowledgment)]}
@router.post('/erp/report-acknowledgments')
def acknowledge_report(body:ReportAckCreate,actor=Depends(current_actor),db=Depends(get_db,scope='function'),idempotency_key:str=Header(alias='Idempotency-Key')):
    revalidate_actor(db,actor);require_domain(actor,'D33',True);payload=body.model_dump(mode='json');op='report.acknowledgment'
    old=begin_operation(db,actor,idempotency_key,op,payload)
    if old:return old
    batch=scoped(db,actor,ReportBatch,body.batch_id);allowed(batch,'exported')
    row=ReportAcknowledgment(**values(actor,**body.model_dump(),recorded_by=actor.user_id,status='recorded_unverified_external'));db.add(row);db.flush();audit(db,actor,'D33',batch.id,op,{'source_type':body.source_type,'external_integration':'NOT_CONNECTED'})
    return finish_operation(db,actor,idempotency_key,op,payload,serialize(row))
@router.get('/erp/dataset-access')
def dataset_access(actor=Depends(current_actor),db=Depends(get_db,scope='function')):
    require_domain(actor,'D36');return {'items':[serialize(x) for x in rows(db,actor,DatasetAccess)]}
@router.post('/erp/dataset-access')
def grant_access(body:AccessCreate,actor=Depends(current_actor),db=Depends(get_db,scope='function'),idempotency_key:str=Header(alias='Idempotency-Key')):
    revalidate_actor(db,actor);require_domain(actor,'D36',True);require_role(actor,'quality','data_steward','dataset_reviewer','quality_officer');payload=body.model_dump(mode='json');op='dataset.access'
    old=begin_operation(db,actor,idempotency_key,op,payload)
    if old:return old
    dataset=scoped(db,actor,DatasetVersion,body.dataset_id);reference(db,actor,User,body.user_id)
    if dataset.status=='revoked':fail('Dataset revoked')
    if db.scalar(select(DatasetAccess).where(DatasetAccess.dataset_id==dataset.id,DatasetAccess.user_id==body.user_id)):fail('Access record exists; use restore/revoke action')
    row=DatasetAccess(**values(actor,**body.model_dump(),granted_by=actor.user_id,status='active'));db.add(row);db.flush();audit(db,actor,'D36',dataset.id,op,{'user_id':body.user_id})
    return finish_operation(db,actor,idempotency_key,op,payload,serialize(row))
@router.post('/erp/dataset-access/{record_id}/actions')
def access_action(record_id:str,body:AccessAction,actor=Depends(current_actor),db=Depends(get_db,scope='function'),idempotency_key:str=Header(alias='Idempotency-Key')):
    revalidate_actor(db,actor);require_domain(actor,'D36',True);require_role(actor,'quality','data_steward','dataset_reviewer','quality_officer');payload=dict(body.model_dump(mode='json'),record_id=record_id);op='dataset.access.'+body.action
    old=begin_operation(db,actor,idempotency_key,op,payload)
    if old:return old
    row=scoped(db,actor,DatasetAccess,record_id,True);check_version(row,body.version)
    allowed(row,'active' if body.action=='revoke' else 'revoked');set_state(row,'revoked' if body.action=='revoke' else 'active');audit(db,actor,'D36',row.dataset_id,op,{'user_id':row.user_id})
    return finish_operation(db,actor,idempotency_key,op,payload,serialize(row))

@router.get('/erp/reports/{record_id}/export')
def export_report(record_id:str,actor=Depends(current_actor),db=Depends(get_db,scope='function')):
    require(actor,'D33.export');row=scoped(db,actor,ReportBatch,record_id);allowed(row,'exported')
    content={'format':'his-local-report-v1','id':row.id,'definition_version':row.definition_version,'period_start':row.period_start.isoformat(),'period_end':row.period_end.isoformat(),'summary':row.summary,'lineage':[serialize(x) for x in db.scalars(select(ReportLineage).where(ReportLineage.batch_id==row.id).order_by(ReportLineage.encounter_id))],'external_submission':'NOT_CONNECTED'}
    audit(db,actor,'D33',row.id,'report.download');return dict(content,sha256=digest(content))
@router.get('/erp/claims/{record_id}/export')
def export_claim(record_id:str,actor=Depends(current_actor),db=Depends(get_db,scope='function')):
    require(actor,'D24.export');row=scoped(db,actor,Claim,record_id);allowed(row,'exported','simulated_submitted','adjudicated','reconciliation_reviewed')
    content={'format':'his-local-synthetic-claim-v1','claim':serialize(row),'lines':[serialize(x) for x in db.scalars(select(ClaimLine).where(ClaimLine.claim_id==row.id).order_by(ClaimLine.id))],'external_submission':'NOT_CONNECTED','payer_format':'NOT_VERIFIED'}
    audit(db,actor,'D24',row.id,'claim.download');return dict(content,sha256=digest(content))
