"""
Ingestion script for AIE_CNES_Dataset.csv.
Parses the preprocessed graphene/CNT sensor data and inserts into aie_cnes_records table.

NOTE: This dataset is loaded into an isolated table (aie_cnes_records) due to
unverified provenance. Structural indicators suggest possible synthetic origin:
perfect data quality (0 missing values), tightly bounded numeric ranges,
and binary classification labels. No source paper or laboratory provenance provided.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
from sqlalchemy.orm import sessionmaker

# Add parent directory to path for imports (running from api/ directory)
sys.path.append(str(Path(__file__).parent.parent.parent))

from app.db.models import AieCnesRecord
from app.db.session import engine

# Set UTF-8 encoding for output
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

# Define paths
BASE_DIR = Path(__file__).parent.parent.parent.parent  # Go up to scan_legacy root
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"
PROCESSED_DATA_FILE = "aie_cnes_clean.csv"


def insert_to_database(df, session):
    """Insert cleaned data into database with duplicate prevention."""
    records_inserted = 0
    duplicates_skipped = 0
    
    for _, row in df.iterrows():
        # Check for duplicate record using all measurable fields
        existing = session.query(AieCnesRecord).filter(
            AieCnesRecord.graphene_ratio_pct == row['graphene_ratio_pct'],
            AieCnesRecord.cnt_ratio_pct == row['cnt_ratio_pct'],
            AieCnesRecord.electrode_surface_area_cm2 == row['electrode_surface_area_cm2'],
            AieCnesRecord.conductivity_s_m == row['conductivity_s_m'],
            AieCnesRecord.ph_level == row['ph_level'],
            AieCnesRecord.temperature_c == row['temperature_c'],
            AieCnesRecord.potential_v == row['potential_v'],
            AieCnesRecord.current_ua == row['current_ua'],
            AieCnesRecord.scan_rate_mv_s == row['scan_rate_mv_s'],
            AieCnesRecord.pulse_amplitude_mv == row['pulse_amplitude_mv'],
            AieCnesRecord.peak_current_ua == row['peak_current_ua'],
            AieCnesRecord.peak_potential_v == row['peak_potential_v'],
            AieCnesRecord.snr == row['snr'],
            AieCnesRecord.interference_level_pct == row['interference_level_pct'],
            AieCnesRecord.pollutant_type == row['pollutant_type'],
            AieCnesRecord.pollutant_concentration_ppm == row['pollutant_concentration_ppm'],
            AieCnesRecord.detection_status == row['detection_status']
        ).first()
        
        if existing:
            duplicates_skipped += 1
            continue
        
        # Insert new record
        record_data = {
            'graphene_ratio_pct': row['graphene_ratio_pct'],
            'cnt_ratio_pct': row['cnt_ratio_pct'],
            'electrode_surface_area_cm2': row['electrode_surface_area_cm2'],
            'conductivity_s_m': row['conductivity_s_m'],
            'ph_level': row['ph_level'],
            'temperature_c': row['temperature_c'],
            'potential_v': row['potential_v'],
            'current_ua': row['current_ua'],
            'scan_rate_mv_s': row['scan_rate_mv_s'],
            'pulse_amplitude_mv': row['pulse_amplitude_mv'],
            'peak_current_ua': row['peak_current_ua'],
            'peak_potential_v': row['peak_potential_v'],
            'snr': row['snr'],
            'interference_level_pct': row['interference_level_pct'],
            'pollutant_type': row['pollutant_type'],
            'pollutant_concentration_ppm': row['pollutant_concentration_ppm'],
            'detection_status': row['detection_status'],
            'source_type': row['source_type'],
            'provenance_note': row['provenance_note'],
        }
        
        record = AieCnesRecord(**record_data)
        session.add(record)
        records_inserted += 1
    
    session.commit()
    
    return records_inserted, duplicates_skipped


def main():
    """Main ingestion pipeline."""
    print("="*80)
    print("AIE-CNES DATA INGESTION")
    print("="*80)
    print("\nNOTE: This dataset is loaded into an isolated table (aie_cnes_records)")
    print("due to unverified provenance. Structural indicators suggest possible")
    print("synthetic origin. Use only as plausibility-range reference.")
    
    # Get database session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    try:
        # Load preprocessed data
        processed_file = PROCESSED_DATA_DIR / PROCESSED_DATA_FILE
        if not processed_file.exists():
            print(f"\nERROR: Processed file not found: {processed_file}")
            print("Please run preprocess_aie_cnes.py first.")
            return
        
        df = pd.read_csv(processed_file)
        print(f"\nLoaded {len(df)} rows from {PROCESSED_DATA_FILE}")
        
        # Get current database count
        count_before = session.query(AieCnesRecord).count()
        print(f"Current aie_cnes_records count: {count_before}")
        
        # Insert into database
        print("\nInserting into database...")
        records_inserted, duplicates_skipped = insert_to_database(df, session)
        
        # Get final database count
        count_after = session.query(AieCnesRecord).count()
        
        print(f"\nInsertion summary:")
        print(f"  Records inserted: {records_inserted}")
        print(f"  Duplicates skipped: {duplicates_skipped}")
        print(f"  Database count before: {count_before}")
        print(f"  Database count after: {count_after}")
        print(f"  Net change: {count_after - count_before}")
        
    except Exception as e:
        session.rollback()
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()
    
    print("\n" + "="*80)
    print("INGESTION COMPLETE")
    print("="*80)


if __name__ == "__main__":
    main()
