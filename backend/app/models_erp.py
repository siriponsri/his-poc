"""Relational revenue, inventory, enterprise and secondary-use prototype models."""
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import String, Text, ForeignKey, Numeric, Date, DateTime, Integer, Boolean, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB
from .db import Base
from uuid import uuid4
from datetime import timezone
def uid(): return str(uuid4())
def utcnow(): return datetime.now(timezone.utc)

class Scoped:
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    facility_id: Mapped[str] = mapped_column(ForeignKey("facilities.id"), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(40), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class PriceVersion(Scoped, Base):
    __tablename__ = "price_versions"
    name: Mapped[str] = mapped_column(String(200))
    effective_from: Mapped[date] = mapped_column(Date)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18,2))
    currency: Mapped[str] = mapped_column(String(3), default="THB")
    __table_args__ = (CheckConstraint("unit_price >= 0", name="erp_check_1"),)

class CoverageRecord(Scoped, Base):
    __tablename__ = "coverage_records"
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    payer_name: Mapped[str] = mapped_column(String(200))
    evidence: Mapped[str] = mapped_column(Text)

class Charge(Scoped, Base):
    __tablename__ = "charges"
    encounter_id: Mapped[str] = mapped_column(ForeignKey("encounters.id"), index=True)
    invoice_id: Mapped[str | None] = mapped_column(ForeignKey("invoices.id"), nullable=True)
    price_version_id: Mapped[str | None] = mapped_column(ForeignKey("price_versions.id"), nullable=True)
    source_id: Mapped[str] = mapped_column(String(200))
    label: Mapped[str] = mapped_column(String(300))
    quantity: Mapped[Decimal] = mapped_column(Numeric(18,3))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18,2))
    amount: Mapped[Decimal] = mapped_column(Numeric(18,2))
    __table_args__ = (UniqueConstraint("organization_id", "source_id"), CheckConstraint("quantity > 0 AND unit_price >= 0 AND amount >= 0", name="erp_check_2"))

class Invoice(Scoped, Base):
    __tablename__ = "invoices"
    encounter_id: Mapped[str] = mapped_column(ForeignKey("encounters.id"), index=True)
    label: Mapped[str] = mapped_column(String(200))
    currency: Mapped[str] = mapped_column(String(3), default="THB")
    billed: Mapped[Decimal] = mapped_column(Numeric(18,2), default=0)

class InvoiceAdjustment(Scoped, Base):
    __tablename__ = "invoice_adjustments"
    invoice_id: Mapped[str] = mapped_column(ForeignKey("invoices.id"), index=True)
    original_charge_id: Mapped[str] = mapped_column(ForeignKey("charges.id"))
    amount: Mapped[Decimal] = mapped_column(Numeric(18,2))
    reason: Mapped[str] = mapped_column(Text)
    approver_id: Mapped[str] = mapped_column(ForeignKey("users.id"))

class Claim(Scoped, Base):
    __tablename__ = "claims"
    invoice_id: Mapped[str] = mapped_column(ForeignKey("invoices.id"), unique=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"))
    encounter_id: Mapped[str] = mapped_column(ForeignKey("encounters.id"))
    payer_name: Mapped[str] = mapped_column(String(200))
    submitted: Mapped[Decimal] = mapped_column(Numeric(18,2), default=0)
    approved: Mapped[Decimal] = mapped_column(Numeric(18,2), default=0)
    exported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class ClaimLine(Scoped, Base):
    __tablename__ = "claim_lines"
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.id"), index=True)
    charge_id: Mapped[str] = mapped_column(ForeignKey("charges.id"))
    billed: Mapped[Decimal] = mapped_column(Numeric(18,2))
    __table_args__ = (UniqueConstraint("claim_id", "charge_id"),)

class Remittance(Scoped, Base):
    __tablename__ = "remittances"
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.id"), unique=True)
    source_key: Mapped[str] = mapped_column(String(160))
    approved_amount: Mapped[Decimal] = mapped_column(Numeric(18,2))
    synthetic: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (UniqueConstraint("organization_id", "source_key"), CheckConstraint("approved_amount >= 0", name="erp_check_3"))

class Receipt(Scoped, Base):
    __tablename__ = "payment_receipts"
    invoice_id: Mapped[str] = mapped_column(ForeignKey("invoices.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18,2))
    payer_name: Mapped[str] = mapped_column(String(200))
    recorded_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    __table_args__ = (CheckConstraint("amount > 0", name="erp_check_4"),)

class Allocation(Scoped, Base):
    __tablename__ = "payment_allocations"
    receipt_id: Mapped[str] = mapped_column(ForeignKey("payment_receipts.id"), unique=True)
    invoice_id: Mapped[str] = mapped_column(ForeignKey("invoices.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18,2))

class Refund(Scoped, Base):
    __tablename__ = "refunds"
    receipt_id: Mapped[str] = mapped_column(ForeignKey("payment_receipts.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18,2))
    reason: Mapped[str] = mapped_column(Text)
    requested_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    approved_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    release_allocation: Mapped[bool] = mapped_column(Boolean, default=False)
    __table_args__ = (CheckConstraint("amount > 0", name="erp_check_5"),)

class LedgerEntry(Scoped, Base):
    __tablename__ = "ledger_entries"
    source_id: Mapped[str] = mapped_column(String(100), unique=True)
    kind: Mapped[str] = mapped_column(String(30))
    original_entry_id: Mapped[str | None] = mapped_column(ForeignKey("ledger_entries.id"))

class LedgerLine(Base):
    __tablename__ = "ledger_lines"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=uid)
    entry_id: Mapped[str] = mapped_column(ForeignKey("ledger_entries.id"), index=True)
    account: Mapped[str] = mapped_column(String(80))
    debit: Mapped[Decimal] = mapped_column(Numeric(18,2), default=0)
    credit: Mapped[Decimal] = mapped_column(Numeric(18,2), default=0)
    __table_args__ = (CheckConstraint("debit >= 0 AND credit >= 0 AND (debit = 0 OR credit = 0)", name="erp_check_6"),)

class CostEntry(Scoped, Base):
    __tablename__ = "cost_entries"
    encounter_id: Mapped[str | None] = mapped_column(ForeignKey("encounters.id"))
    department_id: Mapped[str | None] = mapped_column(ForeignKey("departments.id"))
    source_movement_id: Mapped[str | None] = mapped_column(ForeignKey("stock_movements.id"))
    label: Mapped[str] = mapped_column(String(200))
    amount: Mapped[Decimal] = mapped_column(Numeric(18,2))
    method_version: Mapped[str] = mapped_column(String(100))
    original_id: Mapped[str | None] = mapped_column(ForeignKey("cost_entries.id"))

class BudgetVersion(Scoped, Base):
    __tablename__ = "budget_versions"
    department_id: Mapped[str] = mapped_column(ForeignKey("departments.id"))
    period: Mapped[str] = mapped_column(String(30))
    amount: Mapped[Decimal] = mapped_column(Numeric(18,2))
    method_version: Mapped[str] = mapped_column(String(100))

class Supplier(Scoped, Base):
    __tablename__ = "suppliers"
    name: Mapped[str] = mapped_column(String(200))

class Purchase(Scoped, Base):
    __tablename__ = "purchases"
    supplier_id: Mapped[str] = mapped_column(ForeignKey("suppliers.id"))
    item_id: Mapped[str] = mapped_column(ForeignKey("inventory_items.id"))
    department_id: Mapped[str | None] = mapped_column(ForeignKey("departments.id"))
    quantity: Mapped[Decimal] = mapped_column(Numeric(18,3))
    received_quantity: Mapped[Decimal] = mapped_column(Numeric(18,3), default=0)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18,2))
    requested_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    approved_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    __table_args__ = (CheckConstraint("quantity > 0 AND received_quantity >= 0 AND received_quantity <= quantity AND unit_price >= 0", name="erp_check_7"),)

class GoodsReceipt(Scoped, Base):
    __tablename__ = "goods_receipts"
    purchase_id: Mapped[str] = mapped_column(ForeignKey("purchases.id"), index=True)
    lot_id: Mapped[str] = mapped_column(ForeignKey("inventory_lots.id"))
    movement_id: Mapped[str] = mapped_column(ForeignKey("stock_movements.id"), unique=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18,3))
    amount: Mapped[Decimal] = mapped_column(Numeric(18,2))
    receipt_key: Mapped[str] = mapped_column(String(160))
    __table_args__ = (UniqueConstraint("organization_id", "receipt_key"),)

class SupplierObligation(Scoped, Base):
    __tablename__ = "supplier_obligations"
    purchase_id: Mapped[str] = mapped_column(ForeignKey("purchases.id"), unique=True)
    supplier_id: Mapped[str] = mapped_column(ForeignKey("suppliers.id"))
    amount: Mapped[Decimal] = mapped_column(Numeric(18,2))

class InventoryItem(Scoped, Base):
    __tablename__ = "inventory_items"
    name: Mapped[str] = mapped_column(String(200))
    unit: Mapped[str] = mapped_column(String(30))

class InventoryLot(Scoped, Base):
    __tablename__ = "inventory_lots"
    item_id: Mapped[str] = mapped_column(ForeignKey("inventory_items.id"))
    lot_number: Mapped[str] = mapped_column(String(100))
    expiry_date: Mapped[date] = mapped_column(Date)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(18,2))
    __table_args__ = (UniqueConstraint("organization_id", "item_id", "lot_number"), CheckConstraint("unit_cost >= 0", name="erp_check_8"))

class StockLocation(Scoped, Base):
    __tablename__ = "stock_locations"
    name: Mapped[str] = mapped_column(String(200))

class StockBalance(Base):
    __tablename__ = "stock_balances"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=uid)
    lot_id: Mapped[str] = mapped_column(ForeignKey("inventory_lots.id"))
    location_id: Mapped[str] = mapped_column(ForeignKey("stock_locations.id"))
    available: Mapped[Decimal] = mapped_column(Numeric(18,3), default=0)
    quarantined: Mapped[Decimal] = mapped_column(Numeric(18,3), default=0)
    __table_args__ = (UniqueConstraint("lot_id", "location_id"), CheckConstraint("available >= 0 AND quarantined >= 0", name="erp_check_9"))

class StockMovement(Scoped, Base):
    __tablename__ = "stock_movements"
    lot_id: Mapped[str] = mapped_column(ForeignKey("inventory_lots.id"))
    location_id: Mapped[str] = mapped_column(ForeignKey("stock_locations.id"))
    quantity: Mapped[Decimal] = mapped_column(Numeric(18,3))
    source_id: Mapped[str] = mapped_column(String(200))
    operation_key: Mapped[str] = mapped_column(String(200))
    original_movement_id: Mapped[str | None] = mapped_column(ForeignKey("stock_movements.id"))
    disposition: Mapped[str] = mapped_column(String(30), default="available")
    __table_args__ = (UniqueConstraint("organization_id", "operation_key"), CheckConstraint("quantity <> 0", name="erp_check_10"))

class EquipmentAsset(Scoped, Base):
    __tablename__ = "equipment_assets"
    name: Mapped[str] = mapped_column(String(200))
    location_id: Mapped[str] = mapped_column(ForeignKey("locations.id"))
    department_id: Mapped[str | None] = mapped_column(ForeignKey("departments.id"))
    maintenance_due: Mapped[date | None] = mapped_column(Date)

class MaintenanceWorkOrder(Scoped, Base):
    __tablename__ = "maintenance_work_orders"
    asset_id: Mapped[str] = mapped_column(ForeignKey("equipment_assets.id"), index=True)
    technician_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    evidence: Mapped[str | None] = mapped_column(Text)
    verifier_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))

class StaffMember(Scoped, Base):
    __tablename__ = "staff_members"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), unique=True)
    department_id: Mapped[str] = mapped_column(ForeignKey("departments.id"))
    credential_status: Mapped[str] = mapped_column(String(30), default="active")
    credential_valid_until: Mapped[date] = mapped_column(Date)
    privilege: Mapped[str] = mapped_column(String(80))

class Roster(Scoped, Base):
    __tablename__ = "rosters"
    staff_id: Mapped[str] = mapped_column(ForeignKey("staff_members.id"), index=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    original_id: Mapped[str | None] = mapped_column(ForeignKey("rosters.id"))
    __table_args__ = (CheckConstraint("ends_at > starts_at", name="erp_check_11"),)

class CSSDCycle(Scoped, Base):
    __tablename__ = "cssd_cycles"
    asset_id: Mapped[str] = mapped_column(ForeignKey("equipment_assets.id"))
    operator_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    cycle_code: Mapped[str] = mapped_column(String(100))
    evidence: Mapped[str | None] = mapped_column(Text)
    reviewer_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))

class LinenDispatch(Scoped, Base):
    __tablename__ = "linen_dispatches"
    location_id: Mapped[str] = mapped_column(ForeignKey("locations.id"))
    quantity: Mapped[Decimal] = mapped_column(Numeric(18,3))
    returned_quantity: Mapped[Decimal] = mapped_column(Numeric(18,3), default=0)

class FacilityWorkOrder(Scoped, Base):
    __tablename__ = "facility_work_orders"
    location_id: Mapped[str] = mapped_column(ForeignKey("locations.id"))
    description: Mapped[str] = mapped_column(Text)
    assignee_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    evidence: Mapped[str | None] = mapped_column(Text)

class Incident(Scoped, Base):
    __tablename__ = "incidents"
    encounter_id: Mapped[str | None] = mapped_column(ForeignKey("encounters.id"))
    asset_id: Mapped[str | None] = mapped_column(ForeignKey("equipment_assets.id"))
    reporter_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    description: Mapped[str] = mapped_column(Text)
    classification: Mapped[str | None] = mapped_column(String(100))
    case_definition_version: Mapped[str | None] = mapped_column(String(100))

class CAPA(Scoped, Base):
    __tablename__ = "corrective_actions"
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"), unique=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    action_plan: Mapped[str] = mapped_column(Text)
    evidence: Mapped[str | None] = mapped_column(Text)
    reviewer_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))

class ReportBatch(Scoped, Base):
    __tablename__ = "report_batches"
    name: Mapped[str] = mapped_column(String(200))
    definition_version: Mapped[str] = mapped_column(String(100), default="encounters-by-status-v1")
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    original_id: Mapped[str | None] = mapped_column(ForeignKey("report_batches.id"))
    summary: Mapped[dict | None] = mapped_column(JSONB)

class ReportLineage(Base):
    __tablename__ = "report_lineage"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=uid)
    batch_id: Mapped[str] = mapped_column(ForeignKey("report_batches.id"), index=True)
    encounter_id: Mapped[str] = mapped_column(ForeignKey("encounters.id"))
    source_version: Mapped[int] = mapped_column(Integer)
    source_status: Mapped[str] = mapped_column(String(40))
    __table_args__ = (UniqueConstraint("batch_id", "encounter_id"),)

class IntegrationMessage(Scoped, Base):
    __tablename__ = "integration_messages"
    source_id: Mapped[str] = mapped_column(String(160))
    sequence: Mapped[int] = mapped_column(Integer)
    contract_version: Mapped[str] = mapped_column(String(100))
    kind: Mapped[str] = mapped_column(String(40))
    source_record_id: Mapped[str] = mapped_column(String(64))
    content_hash: Mapped[str] = mapped_column(String(64))
    error: Mapped[str | None] = mapped_column(String(300))
    __table_args__ = (UniqueConstraint("organization_id", "source_id", "sequence"),)

class DeliveryAttempt(Scoped, Base):
    __tablename__ = "delivery_attempts"
    message_id: Mapped[str] = mapped_column(ForeignKey("integration_messages.id"), index=True)
    outcome: Mapped[str] = mapped_column(String(40))
    adapter: Mapped[str] = mapped_column(String(50), default="local_explicit_stub")

class DatasetVersion(Scoped, Base):
    __tablename__ = "dataset_versions"
    name: Mapped[str] = mapped_column(String(200))
    encounter_kind: Mapped[str] = mapped_column(String(30))
    definition_version: Mapped[str] = mapped_column(String(50), default="cohort-allowlist-v1")
    snapshot_hash: Mapped[str | None] = mapped_column(String(64))

class DatasetRow(Base):
    __tablename__ = "dataset_rows"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=uid)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("dataset_versions.id"), index=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"))
    encounter_id: Mapped[str] = mapped_column(ForeignKey("encounters.id"))
    source_version: Mapped[int] = mapped_column(Integer)
    partition: Mapped[str] = mapped_column(String(10))
    snapshot: Mapped[dict] = mapped_column(JSONB)
    __table_args__ = (UniqueConstraint("dataset_id", "encounter_id"), CheckConstraint("partition IN ('train','test')", name="erp_check_12"))

class StockReservation(Scoped, Base):
    __tablename__ = 'stock_reservations'
    task_id: Mapped[str] = mapped_column(ForeignKey('tasks.id'),index=True)
    lot_id: Mapped[str] = mapped_column(ForeignKey('inventory_lots.id'))
    location_id: Mapped[str] = mapped_column(ForeignKey('stock_locations.id'))
    quantity: Mapped[Decimal] = mapped_column(Numeric(18,3))
    movement_id: Mapped[str | None] = mapped_column(ForeignKey('stock_movements.id'))
    __table_args__ = (CheckConstraint('quantity > 0',name='reservation_positive'),)

class StockCount(Scoped, Base):
    __tablename__ = 'stock_counts'
    lot_id: Mapped[str] = mapped_column(ForeignKey('inventory_lots.id'))
    location_id: Mapped[str] = mapped_column(ForeignKey('stock_locations.id'))
    observed_available: Mapped[Decimal] = mapped_column(Numeric(18,3))
    counted_available: Mapped[Decimal] = mapped_column(Numeric(18,3))
    reason: Mapped[str] = mapped_column(Text)
    counted_by: Mapped[str] = mapped_column(ForeignKey('users.id'))
    approved_by: Mapped[str | None] = mapped_column(ForeignKey('users.id'))
    movement_id: Mapped[str | None] = mapped_column(ForeignKey('stock_movements.id'))
    __table_args__ = (CheckConstraint('observed_available >= 0 AND counted_available >= 0',name='count_nonnegative'),)

class IntegrationReceipt(Scoped, Base):
    __tablename__ = 'integration_receipts'
    message_id: Mapped[str] = mapped_column(ForeignKey('integration_messages.id'),unique=True)
    source_record_id: Mapped[str] = mapped_column(String(64))
    receipt_kind: Mapped[str] = mapped_column(String(40))

class ReconciliationTask(Scoped, Base):
    __tablename__ = 'reconciliation_tasks'
    message_id: Mapped[str] = mapped_column(ForeignKey('integration_messages.id'),unique=True)
    integration_receipt_id: Mapped[str] = mapped_column(ForeignKey('integration_receipts.id'))
    title: Mapped[str] = mapped_column(String(200))

class ReportAcknowledgment(Scoped, Base):
    __tablename__ = 'report_acknowledgments'
    batch_id: Mapped[str] = mapped_column(ForeignKey('report_batches.id'),index=True)
    source_type: Mapped[str] = mapped_column(String(40))
    reference: Mapped[str] = mapped_column(Text)
    recorded_by: Mapped[str] = mapped_column(ForeignKey('users.id'))

class DatasetAccess(Scoped, Base):
    __tablename__ = 'dataset_access'
    dataset_id: Mapped[str] = mapped_column(ForeignKey('dataset_versions.id'),index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    granted_by: Mapped[str] = mapped_column(ForeignKey('users.id'))
    purpose: Mapped[str] = mapped_column(Text)
    __table_args__ = (UniqueConstraint('dataset_id','user_id'),)
