"""
Asset Management Models — track physical assets, assignments, and maintenance.
"""
import enum
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Enum, DateTime, ForeignKey,
    Boolean, Text, Numeric, Date, UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base


class AssetStatus(str, enum.Enum):
    AVAILABLE = "available"
    ASSIGNED = "assigned"
    UNDER_MAINTENANCE = "under_maintenance"
    RETIRED = "retired"


class Asset(Base):
    __tablename__ = "assets"
    __table_args__ = (
        UniqueConstraint("company_id", "asset_code", name="uq_asset_company_code"),
        Index("idx_asset_company", "company_id"),
        Index("idx_asset_company_status", "company_id", "status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    asset_code = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)        # "Medical Equipment", "Kitchen", "Vehicle"
    purchase_date = Column(Date, nullable=True)
    purchase_price = Column(Numeric(14, 2), nullable=True)
    current_value = Column(Numeric(14, 2), nullable=True)
    status = Column(Enum(AssetStatus), nullable=False, default=AssetStatus.AVAILABLE)
    location = Column(String(200), nullable=True)
    serial_number = Column(String(150), nullable=True)
    manufacturer = Column(String(150), nullable=True)
    model_number = Column(String(150), nullable=True)
    warranty_expiry = Column(Date, nullable=True)
    custom_attributes = Column(JSONB, nullable=True)
    deleted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    assignments = relationship("AssetAssignment", back_populates="asset")
    maintenance_logs = relationship("AssetMaintenanceLog", back_populates="asset")


class AssetAssignment(Base):
    __tablename__ = "asset_assignments"
    __table_args__ = (
        Index("idx_asset_assign_company", "company_id"),
        Index("idx_asset_assign_asset", "asset_id"),
        Index("idx_asset_assign_employee", "employee_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="SET NULL"), nullable=True, index=True)
    assigned_date = Column(Date, nullable=False)
    returned_date = Column(Date, nullable=True)
    assigned_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    asset = relationship("Asset", back_populates="assignments")
    employee = relationship("Employee")
    assigned_by = relationship("User")


class AssetMaintenanceLog(Base):
    __tablename__ = "asset_maintenance_logs"
    __table_args__ = (
        Index("idx_asset_maint_company", "company_id"),
        Index("idx_asset_maint_asset", "asset_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True)
    maintenance_type = Column(String(100), nullable=True)   # "Repair", "Service", "Inspection"
    description = Column(Text, nullable=True)
    cost = Column(Numeric(12, 2), nullable=True)
    performed_by = Column(String(200), nullable=True)
    maintenance_date = Column(Date, nullable=False)
    next_maintenance_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    asset = relationship("Asset", back_populates="maintenance_logs")
