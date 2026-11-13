"""Read-only legacy archive; never executable proposals or current document history."""
from datetime import datetime, timezone
import uuid
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base


class LegacyImport(Base):
    __tablename__ = 'legacy_imports'
    __table_args__ = (UniqueConstraint('organization_id', 'facility_id', 'source_sha256'),)
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(ForeignKey('organizations.id'), index=True)
    facility_id: Mapped[str] = mapped_column(ForeignKey('facilities.id'), index=True)
    source_sha256: Mapped[str] = mapped_column(String(64))
    mapping_sha256: Mapped[str] = mapped_column(String(64))
    source_name: Mapped[str] = mapped_column(String(255))
    report_json: Mapped[str] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(ForeignKey('users.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class LegacyRow(Base):
    __tablename__ = 'legacy_rows'
    __table_args__ = (UniqueConstraint('import_id', 'source_table', 'legacy_id'),)
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    import_id: Mapped[str] = mapped_column(ForeignKey('legacy_imports.id'), index=True)
    source_table: Mapped[str] = mapped_column(String(40), index=True)
    legacy_id: Mapped[str] = mapped_column(Text)
    legacy_patient_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mapped_patient_id: Mapped[str | None] = mapped_column(ForeignKey('patients.id'), nullable=True, index=True)
    source_row_json: Mapped[str] = mapped_column(Text)
    row_sha256: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(40))
    gap_json: Mapped[str] = mapped_column(Text, default='[]')
