"""
Ingestion script: Kaggle Electrochemical Carbon Nano-Sensor Dataset → sensor_benchmark_records.

PURPOSE AND PERMITTED USES IN THE SCAN SYSTEM
==============================================
This script ingests data from a Kaggle dataset of uncertain provenance into the
isolated `sensor_benchmark_records` table.  It must NEVER write to `material_records`
or `toxicity_records`, which are reserved for literature-mined, lab-validated data.

(a) NOT used for training the cytotoxicity / pEC50 models.
    These models require literature-validated toxicity outcomes (IC50, EC50, pEC50)
    linked to real experimental protocols.  Unverified/synthetic sensor readings
    do not satisfy that requirement.

(b) NOT used as ground-truth validation for the physics layer parser.
    The physics layer parser validates extracted material property values against
    literature data; this dataset has no traceable source paper or lab measurements.

(c) Usable ONLY as a plausibility-range reference for the physics rules engine:
    typical Rct / Capacitance / Peak_Current ranges for Graphene / MWCNT / Hybrid
    sensor materials provide rough sanity bounds when no other reference is available.
    Also usable as a larger-volume retrieval-ranking testbed for Module 2's
    retrieval logic once that module is built (the dataset's 6 786 rows offer
    reasonable volume for ranking experiments).

PROVENANCE WARNING
==================
Source     : Kaggle — "Electrochemical Carbon Nano-Sensor Dataset"
Uploader   : colabsss
License    : CC0 (public domain dedication)
URL        : https://www.kaggle.com/datasets/colabsss/electrochemical-carbon-nano-sensor-dataset
Issues     :
  - No cited source paper, institution, or experimental lab.
  - Rolling_Mean_5, Rolling_Std_5, Previous_Reading columns are engineered
    time-series features — atypical of raw experimental data.
  - Numeric ranges are suspiciously uniform across all sensors.
  - Timestamps start at 2026-01-01, with perfectly sequential 1-minute intervals.
  These structural signals suggest the dataset is likely synthetic.

Every row inserted by this script carries an immutable `provenance_note` field
and `source_type = 'kaggle_unverified'` to make the data's status machine-readable
and surface it clearly in any dashboard or API response.
"""

import sys
import uuid
from datetime import datetime
from pathlib import Path

import pandas as pd

# Add repo root to sys.path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from sqlalchemy.orm import sessionmaker

from api.app.db.models import MaterialRecord, SensorBenchmarkRecord, ToxicityRecord
from api.app.db.session import engine

# Set UTF-8 output on Windows
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent.parent.parent.parent
CSV_PATH = BASE_DIR / "data" / "raw" / "kaggle_electrochemical_sensor" / "environmental_nanosensor_dataset.csv"

SOURCE_TYPE = "kaggle_unverified"
SOURCE_URL = "https://www.kaggle.com/datasets/colabsss/electrochemical-carbon-nano-sensor-dataset"
PROVENANCE_NOTE = (
    "Provenance unverified. No cited source paper or lab. "
    "Structural indicators suggest possible synthetic origin. "
    "Use only as a plausibility-range reference, not as "
    "literature-grade or experimentally validated data."
)

# CSV column → model attribute (explicit mapping for clarity and safety)
COLUMN_MAP = {
    "Sensor_ID":                    "sensor_id",
    "Material_Type":                "material_type",
    "Surface_Area":                 "surface_area",
    "Conductivity":                 "conductivity",
    "Functionalization":            "functionalization",
    "Peak_Current":                 "peak_current_ua",
    "Peak_Voltage":                 "peak_voltage_v",
    "Charge_Transfer_Resistance":   "charge_transfer_resistance_ohm",
    "Capacitance":                  "capacitance_f",
    "CV_Area":                      "cv_area",
    "DPV_Peak_Height":              "dpv_peak_height",
    "SNR":                          "snr",
    "Temperature":                  "temperature_c",
    "pH":                           "ph",
    "Dissolved_Oxygen":             "dissolved_oxygen_mg_l",
    "Water_Conductivity":           "water_conductivity_us_cm",
    "Pb_Concentration":             "pb_concentration_ppb",
    "Hg_Concentration":             "hg_concentration_ppb",
    "NO2_Concentration":            "no2_concentration_ppm",
    "Benzene_Concentration":        "benzene_concentration_ppm",
    "Pollutant_Class":              "pollutant_class",
    "Pollution_Level":              "pollution_level",
    # Timestamp / Time_Index / Previous_Reading / Rolling_Mean_5 / Rolling_Std_5
    # are intentionally excluded — they are engineered features, not physical measurements.
}


def load_and_clean(csv_path: Path) -> pd.DataFrame:
    """Load the CSV and apply minimal cleaning.

    Cleaning steps:
    1. Verify all expected columns are present.
    2. Drop rows missing sensor_id or material_type (required fields).
    3. Convert float columns; leave NaN → None for nullable DB columns.
    4. Strip whitespace from string columns.
    5. Retain only the columns needed for the DB schema (discard engineered features).
    """
    df = pd.read_csv(csv_path)

    # --- Verify expected columns ---
    missing = [c for c in COLUMN_MAP if c not in df.columns]
    if missing:
        raise ValueError(f"Missing expected columns in CSV: {missing}")

    # --- Keep only mapped columns ---
    df = df[list(COLUMN_MAP.keys())].copy()
    df.rename(columns=COLUMN_MAP, inplace=True)

    # --- Drop rows with missing required fields ---
    before = len(df)
    df.dropna(subset=["sensor_id", "material_type"], inplace=True)
    dropped = before - len(df)
    if dropped:
        print(f"  Dropped {dropped} rows with null sensor_id or material_type")

    # --- Strip string columns ---
    for col in ["sensor_id", "material_type", "functionalization", "pollutant_class", "pollution_level"]:
        if col in df.columns:
            df[col] = df[col].where(df[col].notna(), None)
            df[col] = df[col].apply(lambda x: x.strip() if isinstance(x, str) else x)

    # --- Coerce float columns (already float64, but ensure NaN → None at insert) ---
    float_cols = [
        "surface_area", "conductivity", "peak_current_ua", "peak_voltage_v",
        "charge_transfer_resistance_ohm", "capacitance_f", "cv_area",
        "dpv_peak_height", "snr", "temperature_c", "ph",
        "dissolved_oxygen_mg_l", "water_conductivity_us_cm",
        "pb_concentration_ppb", "hg_concentration_ppb",
        "no2_concentration_ppm", "benzene_concentration_ppm",
    ]
    for col in float_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def check_existing_data(df: pd.DataFrame, session) -> bool:
    """Check if data from this source already exists in sensor_benchmark_records.

    Uses sensor_id as the deduplication key since it's unique per row in the source CSV.
    Returns True if any duplicates are detected (meaning data already exists), False otherwise.
    """
    print("Checking for existing data from this source...")

    # Get all sensor_ids from the CSV
    csv_sensor_ids = set(df["sensor_id"].unique())
    print(f"  CSV contains {len(csv_sensor_ids)} unique sensor_ids")

    # Check if any of these sensor_ids already exist in the database
    existing_sensor_ids = session.query(SensorBenchmarkRecord.sensor_id).filter(
        SensorBenchmarkRecord.sensor_id.in_(csv_sensor_ids)
    ).all()

    existing_sensor_ids = set([sid[0] for sid in existing_sensor_ids])

    if existing_sensor_ids:
        print(f"  Found {len(existing_sensor_ids)} sensor_ids already in database")
        print(f"  Skipping insertion to avoid duplicates.")
        return True
    else:
        print(f"  No existing sensor_ids found. Safe to proceed.")
        return False


def insert_records(df: pd.DataFrame, session) -> int:
    """Bulk-insert cleaned rows into sensor_benchmark_records.

    Uses batch commits of 1000 rows to avoid large transactions.
    Returns the total number of rows inserted.
    """
    BATCH_SIZE = 1000
    inserted = 0
    now = datetime.utcnow()
    records = []

    for _, row in df.iterrows():
        def _float(val):
            """Return float or None for NaN."""
            import math
            if val is None:
                return None
            try:
                f = float(val)
                return None if math.isnan(f) else f
            except (TypeError, ValueError):
                return None

        rec = SensorBenchmarkRecord(
            id=uuid.uuid4(),
            sensor_id=str(row["sensor_id"]),
            material_type=str(row["material_type"]),
            surface_area=_float(row["surface_area"]),
            conductivity=_float(row["conductivity"]),
            functionalization=row["functionalization"] if pd.notna(row.get("functionalization")) else None,
            peak_current_ua=_float(row["peak_current_ua"]),
            peak_voltage_v=_float(row["peak_voltage_v"]),
            charge_transfer_resistance_ohm=_float(row["charge_transfer_resistance_ohm"]),
            capacitance_f=_float(row["capacitance_f"]),
            cv_area=_float(row["cv_area"]),
            dpv_peak_height=_float(row["dpv_peak_height"]),
            snr=_float(row["snr"]),
            temperature_c=_float(row["temperature_c"]),
            ph=_float(row["ph"]),
            dissolved_oxygen_mg_l=_float(row["dissolved_oxygen_mg_l"]),
            water_conductivity_us_cm=_float(row["water_conductivity_us_cm"]),
            pb_concentration_ppb=_float(row["pb_concentration_ppb"]),
            hg_concentration_ppb=_float(row["hg_concentration_ppb"]),
            no2_concentration_ppm=_float(row["no2_concentration_ppm"]),
            benzene_concentration_ppm=_float(row["benzene_concentration_ppm"]),
            pollutant_class=row["pollutant_class"] if pd.notna(row.get("pollutant_class")) else None,
            pollution_level=row["pollution_level"] if pd.notna(row.get("pollution_level")) else None,
            # Provenance — immutable, set on every row
            source_type=SOURCE_TYPE,
            source_url=SOURCE_URL,
            provenance_note=PROVENANCE_NOTE,
            created_at=now,
        )
        records.append(rec)

        if len(records) >= BATCH_SIZE:
            session.bulk_save_objects(records)
            session.commit()
            inserted += len(records)
            print(f"  ... committed batch, running total: {inserted}")
            records = []

    if records:
        session.bulk_save_objects(records)
        session.commit()
        inserted += len(records)

    return inserted


def main():
    """Main ingestion pipeline — sensor_benchmark_records only."""
    print("=" * 80)
    print("KAGGLE SENSOR BENCHMARK INGEST → sensor_benchmark_records")
    print("=" * 80)
    print()
    print("ISOLATION GUARANTEE: This script writes ONLY to sensor_benchmark_records.")
    print("  material_records and toxicity_records are NOT touched.")
    print()

    if not CSV_PATH.exists():
        print(f"ERROR: CSV not found at {CSV_PATH}")
        sys.exit(1)

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    try:
        # ------------------------------------------------------------------ #
        # Before-counts (isolation proof baseline)                            #
        # ------------------------------------------------------------------ #
        mat_before = session.query(MaterialRecord).count()
        tox_before = session.query(ToxicityRecord).count()
        bench_before = session.query(SensorBenchmarkRecord).count()
        print(f"[Before] material_records:          {mat_before}")
        print(f"[Before] toxicity_records:          {tox_before}")
        print(f"[Before] sensor_benchmark_records:  {bench_before}")
        print()

        # ------------------------------------------------------------------ #
        # Load & clean                                                         #
        # ------------------------------------------------------------------ #
        print(f"Loading CSV: {CSV_PATH}")
        df = load_and_clean(CSV_PATH)
        print(f"  Rows after cleaning: {len(df)}")
        print()

        # ------------------------------------------------------------------ #
        # Check for existing data (duplicate detection)                        #
        # ------------------------------------------------------------------ #
        if check_existing_data(df, session):
            print()
            print("=" * 60)
            print("DUPLICATE DETECTION")
            print("=" * 60)
            print("Data from this source already exists in sensor_benchmark_records.")
            print("Skipping insertion to avoid duplicates.")
            print("=" * 60)
            return

        # ------------------------------------------------------------------ #
        # Insert                                                               #
        # ------------------------------------------------------------------ #
        print("Inserting into sensor_benchmark_records ...")
        inserted = insert_records(df, session)

        # ------------------------------------------------------------------ #
        # After-counts (isolation verification)                               #
        # ------------------------------------------------------------------ #
        mat_after = session.query(MaterialRecord).count()
        tox_after = session.query(ToxicityRecord).count()
        bench_after = session.query(SensorBenchmarkRecord).count()

        print()
        print("=" * 60)
        print("INSERTION SUMMARY")
        print("=" * 60)
        print(f"  Rows inserted into sensor_benchmark_records: {inserted}")
        print()
        print("ISOLATION VERIFICATION (before → after):")
        print(f"  material_records:         {mat_before} → {mat_after}  {'✓ unchanged' if mat_after == mat_before else '✗ CHANGED — BUG!'}")
        print(f"  toxicity_records:         {tox_before} → {tox_after}  {'✓ unchanged' if tox_after == tox_before else '✗ CHANGED — BUG!'}")
        print(f"  sensor_benchmark_records: {bench_before} → {bench_after}")
        print()
        print(f"  source_type on all rows:  '{SOURCE_TYPE}'")
        print(f"  provenance_note:          '{PROVENANCE_NOTE}'")
        print()

        if mat_after != mat_before or tox_after != tox_before:
            print("CRITICAL: Isolation breach detected! Rolling back.")
            session.rollback()
            sys.exit(2)

        print("✓ Isolation confirmed — no rows leaked into material_records or toxicity_records.")

    except Exception as exc:
        session.rollback()
        print(f"\nERROR: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        session.close()

    print()
    print("=" * 80)
    print("INGEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
