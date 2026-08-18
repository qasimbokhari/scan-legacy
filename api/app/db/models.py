import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, ForeignKey, Text, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.session import Base


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


# ---------------------------------------------------------------------------
# ISOLATED AIE-CNES TABLE — Unverified Graphene/CNT Sensor Dataset
# ---------------------------------------------------------------------------
# This table is intentionally SEPARATE from sensor_performance_records.
# The AIE_CNES_Dataset.csv (7,654 rows) shows structural indicators of 
# possible synthetic origin: perfect data quality (0 missing values), 
# tightly bounded numeric ranges, and binary classification labels.
# No source paper or laboratory provenance provided.
#
# Permitted uses:
#   - Plausibility-range reference for graphene/CNT sensor design
#   - Benchmark dataset for sensor classification algorithm testing
#
# NOT permitted:
#   - Training primary sensor performance models
#   - Ground-truth validation of sensor physics calculations
#   - Presentation as literature-grade or experimentally validated data
# ---------------------------------------------------------------------------
class AieCnesRecord(Base):
    __tablename__ = "aie_cnes_records"

    # --- Identity ---
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # --- Material composition ---
    graphene_ratio_pct = Column(Float, nullable=True)     # Graphene percentage
    cnt_ratio_pct = Column(Float, nullable=True)           # CNT percentage

    # --- Electrode properties ---
    electrode_surface_area_cm2 = Column(Float, nullable=True)
    conductivity_s_m = Column(Float, nullable=True)

    # --- Experimental conditions ---
    ph_level = Column(Float, nullable=True)
    temperature_c = Column(Float, nullable=True)
    potential_v = Column(Float, nullable=True)
    current_ua = Column(Float, nullable=True)
    scan_rate_mv_s = Column(Float, nullable=True)
    pulse_amplitude_mv = Column(Float, nullable=True)

    # --- Sensor response ---
    peak_current_ua = Column(Float, nullable=True)
    peak_potential_v = Column(Float, nullable=True)
    snr = Column(Float, nullable=True)
    interference_level_pct = Column(Float, nullable=True)

    # --- Analyte information ---
    pollutant_type = Column(String, nullable=True)          # Pesticide | Arsenic | Lead | Nitrate | Mercury
    pollutant_concentration_ppm = Column(Float, nullable=True)
    detection_status = Column(Integer, nullable=True)       # Binary classification label

    # --- Provenance (set at ingest time, immutable per-row) ---
    source_type = Column(
        String, nullable=False,
        default="aie_cnes_unverified",
    )
    provenance_note = Column(
        Text, nullable=True,
        default=(
            "Provenance unverified. No cited source paper or laboratory. "
            "Structural indicators suggest possible synthetic origin: "
            "perfect data quality (0 missing values), tightly bounded numeric ranges, "
            "binary classification labels. Use only as plausibility-range reference, "
            "not as literature-grade or experimentally validated data."
        ),
    )

    created_at = Column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------------------
# ANALYTE REFERENCE TABLES — Molecular Properties for Design Studio
# ---------------------------------------------------------------------------

class AnalyteCompound(Base):
    __tablename__ = "analyte_compounds"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)  # Common name (e.g., "Arsenic", "Glucose")
    pubchem_cid = Column(Integer, nullable=True)  # PubChem Compound ID
    molecular_formula = Column(String, nullable=True)  # Chemical formula (e.g., "As", "C6H12O6")
    molecular_weight = Column(Float, nullable=True)  # g/mol
    xlogp = Column(Float, nullable=True)  # XLogP3 (octanol-water partition coefficient)
    tpsa = Column(Float, nullable=True)  # Topological Polar Surface Area
    hbond_donor_count = Column(Integer, nullable=True)  # Hydrogen bond donor count
    hbond_acceptor_count = Column(Integer, nullable=True)  # Hydrogen bond acceptor count
    complexity = Column(Float, nullable=True)  # Molecular complexity score
    source_type = Column(String, nullable=False, default="pubchem")
    created_at = Column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------------------
# ANALYZER MODULE TABLES — CV/LSV and EIS Analysis Results
# ---------------------------------------------------------------------------

class AnalyzerResult(Base):
    __tablename__ = "analyzer_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_type = Column(String, nullable=False)  # "cv-lsv" | "eis"
    
    # Raw uploaded data stored as JSONB
    raw_data = Column(JSONB, nullable=False)
    
    # Parsed results stored as JSONB
    processed_results = Column(JSONB, nullable=False)
    
    # Fit metadata (residuals, R², etc.)
    fit_metadata = Column(JSONB, nullable=True)
    
    # User who uploaded the data
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Optional: scan rate for CV/LSV (if single file)
    scan_rate_v_s = Column(Float, nullable=True)
    
    # Optional: experimental parameters
    electrode_area_cm2 = Column(Float, nullable=True)
    concentration_mol_cm3 = Column(Float, nullable=True)
    n_electrons = Column(Integer, nullable=True)
    temperature_k = Column(Float, nullable=True)


# ---------------------------------------------------------------------------
# ISOLATED NANOREG TABLE — ENANOMAPPER Complex Metrics
# ---------------------------------------------------------------------------
class NanoregRecord(Base):
    __tablename__ = "nanoreg_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    substance_name = Column(String, nullable=False)
    jrc_id = Column(String, nullable=True)
    topcategory = Column(String, nullable=True)
    endpointcategory = Column(String, nullable=True)
    endpoint = Column(String, nullable=True)
    value_numeric = Column(Float, nullable=True)
    unit = Column(String, nullable=True)
    text_value = Column(String, nullable=True)
    reference = Column(String, nullable=True)
    source_type = Column(String, nullable=False, default="nanoreg_mined")
    provenance_note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

