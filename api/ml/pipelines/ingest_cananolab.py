"""
Ingestion script for caNanoLab dataset.
Parses the caNanoLab manifest CSV (metadata-only dataset),
cleans data, and inserts into material_records table only.

NOTE: This is primarily metadata with no toxicity outcomes.
Records are inserted into material_records only, marked as metadata-only entries.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
from sqlalchemy.orm import Session
from sqlalchemy import create_engine

# Add parent directory to path for imports (running from api/ directory)
sys.path.append(str(Path(__file__).parent.parent.parent))

from app.db.models import MaterialRecord
from app.db.session import get_db

# Set UTF-8 encoding for output
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

# Define paths
BASE_DIR = Path(__file__).parent.parent.parent.parent  # Go up to scan_legacy root
RAW_DATA_DIR = BASE_DIR / "data" / "raw" / "caNanoLab"
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"
PROCESSED_DATA_DIR.mkdir(exist_ok=True)

# File to ingest
CANANOLAB_FILE = "GC File Manifest 2026-05-24 10-59-23.csv"


def parse_cananolab_dataset(file_path):
    """Parse caNanoLab manifest CSV."""
    print(f"\nProcessing caNanoLab manifest: {file_path.name}...")
    df = pd.read_csv(file_path)
    print(f"  Original rows: {len(df)}")
    print(f"  Columns: {list(df.columns)}")
    
    cleaned_data = []
    
    for _, row in df.iterrows():
        # Extract material name from file name
        file_name = row.get('name', 'Unknown')
        
        # Create a material name from the file name
        # Remove file extension and clean up
        material_name = str(file_name).replace('.csv', '').replace('.xlsx', '').strip()
        
        material_record = {
            'name': material_name,
            'material_type': 'Unknown',  # caNanoLab doesn't specify material type
            'core_size_nm': None,
            'zeta_potential_mv': None,
            'surface_area_m2g': None,
            'coating': None,
            'source_type': 'literature_mined',
            'doi': row.get('Accession'),  # Use Accession as DOI reference
        }
        
        cleaned_data.append({
            'material': material_record,
            'metadata': {
                'drs_uri': row.get('drs_uri'),
                'sample_id': row.get('Sample Id'),
                'study_name': row.get('Study Name'),
                'file_type': row.get('File Type'),
            }
        })
    
    return cleaned_data


def insert_to_database(cleaned_data, session):
    """Insert cleaned data into database with duplicate prevention."""
    materials_inserted = 0
    duplicates_skipped = 0
    
    for item in cleaned_data:
        material_data = item['material']
        
        # Check for duplicate material
        existing = session.query(MaterialRecord).filter(
            MaterialRecord.name == material_data['name'],
            MaterialRecord.source_type == material_data['source_type']
        ).first()
        
        if existing:
            duplicates_skipped += 1
            continue
        
        # Insert material (no toxicity record for caNanoLab)
        material = MaterialRecord(**material_data)
        session.add(material)
        materials_inserted += 1
    
    session.commit()
    
    return materials_inserted, duplicates_skipped


def validate_processed_data(df):
    """Validate that no NaN values remain in critical columns."""
    critical_columns = ['name', 'material_type']
    issues = []
    
    for col in critical_columns:
        if col in df.columns and df[col].isna().any():
            issues.append(f"NaN values found in {col}")
    
    return issues


def main():
    """Main ingestion pipeline."""
    print("="*80)
    print("CANANOLAB DATA INGESTION")
    print("="*80)
    print("\nNOTE: This is a metadata-only dataset with no toxicity outcomes.")
    print("Records are inserted into material_records only.")
    
    # Get database session
    from app.db.session import engine
    from sqlalchemy.orm import sessionmaker
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    try:
        # Process caNanoLab dataset
        cananolab_file = RAW_DATA_DIR / CANANOLAB_FILE
        if not cananolab_file.exists():
            print(f"\nERROR: caNanoLab file not found: {cananolab_file}")
            return
        
        cleaned_data = parse_cananolab_dataset(cananolab_file)
        
        if cleaned_data:
            # Create processed CSV for inspection
            processed_df = pd.DataFrame([
                {**item['material'], **item['metadata']}
                for item in cleaned_data
            ])
            output_path = PROCESSED_DATA_DIR / "cananolab_clean.csv"
            processed_df.to_csv(output_path, index=False)
            print(f"\nProcessed data saved to: {output_path}")
            
            # Validate
            issues = validate_processed_data(processed_df)
            if issues:
                print("\nVALIDATION ISSUES:")
                for issue in issues:
                    print(f"  - {issue}")
            else:
                print("\nValidation passed: No NaN values in critical columns")
        
        print(f"\nTotal records parsed: {len(cleaned_data)}")
        
        # Insert into database
        print("\nInserting into database...")
        materials_inserted, duplicates_skipped = insert_to_database(
            cleaned_data, session
        )
        
        print(f"\nInsertion summary:")
        print(f"  Materials inserted: {materials_inserted}")
        print(f"  Duplicates skipped: {duplicates_skipped}")
        print(f"  Toxicity records inserted: 0 (metadata-only dataset)")
        
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
