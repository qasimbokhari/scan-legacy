import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, ForeignKey, Text, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from api.app.db.session import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False)  # "owner" | "contributor" | "viewer"
    created_at = Column(DateTime, default=datetime.utcnow)


class MaterialRecord(Base):
    __tablename__ = "material_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    material_type = Column(String, nullable=False)
    core_size_nm = Column(Float, nullable=True)
    zeta_potential_mv = Column(Float, nullable=True)
    surface_area_m2g = Column(Float, nullable=True)
    coating = Column(String, nullable=True)
    source_type = Column(String, nullable=False)  # "literature_mined" | "user_contribution" | "api_sync"
    doi = Column(String, nullable=True)
    extraction_confidence = Column(Float, nullable=True)
    contributor_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ToxicityRecord(Base):
    __tablename__ = "toxicity_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    material_id = Column(UUID(as_uuid=True), ForeignKey("material_records.id"), nullable=False)
    ic50 = Column(Float, nullable=True)
    ec50 = Column(Float, nullable=True)
    pec50 = Column(Float, nullable=True)
    cell_line = Column(String, nullable=True)
    exposure_time_h = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class SensorPerformanceRecord(Base):
    __tablename__ = "sensor_performance_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nanomaterial = Column(String, nullable=False)
    analyte = Column(String, nullable=False)
    lod_mol_per_l = Column(Float, nullable=True)
    sensitivity_value = Column(Float, nullable=True)
    sensitivity_unit = Column(String, nullable=True)
    linear_range_low = Column(Float, nullable=True)
    linear_range_high = Column(Float, nullable=True)
    response_time_s = Column(Float, nullable=True)
    source_type = Column(String, nullable=False)
    doi = Column(String, nullable=True)
    extraction_confidence = Column(Float, nullable=True)
    contributor_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class RecordVersion(Base):
    __tablename__ = "record_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    record_type = Column(String, nullable=False)  # e.g. "material_record"
    record_id = Column(UUID(as_uuid=True), nullable=False)
    version_number = Column(Integer, nullable=False)
    data_snapshot = Column(JSON, nullable=False)
    edited_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class RecordReview(Base):
    __tablename__ = "record_reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    record_type = Column(String, nullable=False)
    record_id = Column(UUID(as_uuid=True), nullable=False)
    status = Column(String, nullable=False)  # "pending" | "approved" | "rejected"
    reviewer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    notes = Column(Text, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
