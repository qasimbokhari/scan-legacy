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
    zeta_potential_flagged = Column(Integer, nullable=True)  # 1 if flagged as implausible, 0 or null otherwise
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


# ---------------------------------------------------------------------------
# ISOLATED BENCHMARK TABLE — Unverified / Possibly Synthetic External Data
# ---------------------------------------------------------------------------
# This table is intentionally SEPARATE from material_records and toxicity_records.
# Those tables hold literature-mined, lab-validated data with real provenance.
# sensor_benchmark_records holds the Kaggle "Electrochemical Carbon Nano-Sensor
# Dataset" (uploader: colabsss, CC0), whose provenance is unverified: no cited
# source paper or lab, and structural indicators (rolling means, Previous_Reading
# columns, perfectly bounded numeric ranges) suggest possible synthetic origin.
#
# Permitted uses:
#   - Plausibility-range reference for the physics rules engine
#     (typical Rct / Capacitance / Peak_Current ranges for these materials)
#   - Larger-volume retrieval-ranking testbed for Module 2 once built
#
# NOT permitted:
#   - Training the cytotoxicity / pEC50 ML models
#   - Ground-truth validation of the physics layer parser
#   - Presentation as literature-grade or experimentally validated data
# ---------------------------------------------------------------------------
class SensorBenchmarkRecord(Base):
    __tablename__ = "sensor_benchmark_records"

    # --- Identity ---
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sensor_id = Column(String, nullable=False)          # e.g. "S1", "S2"

    # --- Material ---
    material_type = Column(String, nullable=False)      # Graphene | MWCNT | Hybrid
    surface_area = Column(Float, nullable=True)         # m²/g (as-reported, unit unverified)
    conductivity = Column(Float, nullable=True)         # S/m (as-reported, unit unverified)
    functionalization = Column(String, nullable=True)   # NH2 | COOH | null

    # --- Electrochemical measurements ---
    peak_current_ua = Column(Float, nullable=True)      # µA
    peak_voltage_v = Column(Float, nullable=True)       # V
    charge_transfer_resistance_ohm = Column(Float, nullable=True)   # Ω
    capacitance_f = Column(Float, nullable=True)        # F
    cv_area = Column(Float, nullable=True)
    dpv_peak_height = Column(Float, nullable=True)
    snr = Column(Float, nullable=True)

    # --- Environmental parameters ---
    temperature_c = Column(Float, nullable=True)        # °C
    ph = Column(Float, nullable=True)
    dissolved_oxygen_mg_l = Column(Float, nullable=True)
    water_conductivity_us_cm = Column(Float, nullable=True)

    # --- Pollutant concentrations ---
    pb_concentration_ppb = Column(Float, nullable=True)
    hg_concentration_ppb = Column(Float, nullable=True)
    no2_concentration_ppm = Column(Float, nullable=True)
    benzene_concentration_ppm = Column(Float, nullable=True)

    # --- Classification labels ---
    pollutant_class = Column(String, nullable=True)     # HeavyMetal | Gas | Organic
    pollution_level = Column(String, nullable=True)     # Low | Medium | High

    # --- Provenance (set at ingest time, immutable per-row) ---
    source_type = Column(
        String, nullable=False,
        default="kaggle_unverified",
    )
    source_url = Column(
        String, nullable=True,
        default="https://www.kaggle.com/datasets/colabsss/electrochemical-carbon-nano-sensor-dataset",
    )
    provenance_note = Column(
        Text, nullable=True,
        default=(
            "Provenance unverified. No cited source paper or lab. "
            "Structural indicators suggest possible synthetic origin. "
            "Use only as a plausibility-range reference, not as "
            "literature-grade or experimentally validated data."
        ),
    )

    created_at = Column(DateTime, default=datetime.utcnow)
