"""
Ingestion script for nanotox_dataset.csv.
Parses the preprocessed nanoparticle toxicity data and inserts into 
material_records and toxicity_records tables.

NOTE: This dataset contains 881 rows with 487 apparent duplicates - these are
likely the same materials tested under different conditions (dosage, exposure time).
The EC50 values appear to be log-transformed (negative values) and are stored as-is.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
from sqlalchemy.orm import sessionmaker

# Add parent directory to path for imports (running from api/ directory)
sys.path.append(str(Path(__file__).parent.parent.parent))

from app.db.models import MaterialRecord, ToxicityRecord
from app.db.session import engine

# Set UTF-8 encoding for output
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

# Define paths
BASE_DIR = Path(__file__).parent.parent.parent.parent  # Go up to scan_legacy root
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"
PROCESSED_DATA_FILE = "nanotox_clean.csv"


def insert_to_database(df, session):
    """Insert cleaned data into database with duplicate prevention.
    
    Duplicate detection logic:
    - MaterialRecord: Match on (name + material_type + core_size_nm + zeta_potential_mv + 
                        surface_area_m2g + coating) - all material properties
    - ToxicityRecord: Match on (material_id + cell_line + exposure_time_h) - allow multiple
                      toxicity records per material if they have different test conditions
    """
    materials_inserted = 0
    toxicities_inserted = 0
    duplicates_skipped = 0
    
    for _, row in df.iterrows():
        # Convert NaN to None for proper handling
        coating_value = row['coating'] if pd.notna(row['coating']) else None
        cell_line_value = row['cell_line'] if pd.notna(row['cell_line']) else None
        
        material_data = {
            'name': row['name'],
            'material_type': row['material_type'],
            'core_size_nm': row['core_size_nm'] if pd.notna(row['core_size_nm']) else None,
            'zeta_potential_mv': row['zeta_potential_mv'] if pd.notna(row['zeta_potential_mv']) else None,
            'surface_area_m2g': row['surface_area_m2g'] if pd.notna(row['surface_area_m2g']) else None,
            'coating': coating_value,
            'source_type': row['source_type'],
            'doi': row['doi'] if pd.notna(row['doi']) else None,
        }
        
        toxicity_data = {
            'ic50': row['ic50'] if pd.notna(row['ic50']) else None,
            'ec50': row['ec50'] if pd.notna(row['ec50']) else None,
            'pec50': row['pec50'] if pd.notna(row['pec50']) else None,
            'cell_line': cell_line_value,
            'exposure_time_h': row['exposure_time_h'] if pd.notna(row['exposure_time_h']) else None,
        }
        
        # Check for duplicate material using all material properties
        # Use proper NULL handling for coating field
        query = session.query(MaterialRecord).filter(
            MaterialRecord.name == material_data['name'],
            MaterialRecord.material_type == material_data['material_type'],
            MaterialRecord.source_type == material_data['source_type'],
            MaterialRecord.core_size_nm == material_data['core_size_nm'],
            MaterialRecord.zeta_potential_mv == material_data['zeta_potential_mv'],
            MaterialRecord.surface_area_m2g == material_data['surface_area_m2g']
        )
        
        # Add coating condition with proper NULL handling
        if material_data['coating'] is None:
            query = query.filter(MaterialRecord.coating.is_(None))
        else:
            query = query.filter(MaterialRecord.coating == material_data['coating'])
        
        existing = query.first()
        
        if existing:
            # Material exists, check if toxicity record already exists for this test condition
            if any(toxicity_data.values()):
                query = session.query(ToxicityRecord).filter(
                    ToxicityRecord.material_id == existing.id
                )
                
                # Add cell_line condition with proper NULL handling
                if toxicity_data['cell_line'] is None:
                    query = query.filter(ToxicityRecord.cell_line.is_(None))
                else:
                    query = query.filter(ToxicityRecord.cell_line == toxicity_data['cell_line'])
                
                # Add exposure_time_h condition with proper NULL handling
                if toxicity_data['exposure_time_h'] is None:
                    query = query.filter(ToxicityRecord.exposure_time_h.is_(None))
                else:
                    query = query.filter(ToxicityRecord.exposure_time_h == toxicity_data['exposure_time_h'])
                
                existing_tox = query.first()
                
                if existing_tox:
                    duplicates_skipped += 1
                    continue
                else:
                    # Insert new toxicity record for existing material
                    toxicity_data['material_id'] = existing.id
                    toxicity = ToxicityRecord(**toxicity_data)
                    session.add(toxicity)
                    toxicities_inserted += 1
            else:
                duplicates_skipped += 1
                continue
        else:
            # Insert new material
            material = MaterialRecord(**material_data)
            session.add(material)
            session.flush()  # Get the ID
            
            materials_inserted += 1
            
            # Insert toxicity if any toxicity data exists
            if any(toxicity_data.values()):
                toxicity_data['material_id'] = material.id
                toxicity = ToxicityRecord(**toxicity_data)
                session.add(toxicity)
                toxicities_inserted += 1
    
    session.commit()
    
    return materials_inserted, toxicities_inserted, duplicates_skipped


def main():
    """Main ingestion pipeline."""
    print("="*80)
    print("NANOTOX DATA INGESTION")
    print("="*80)
    print("\nNOTE: This dataset contains 881 rows with apparent duplicates.")
    print("These are likely the same materials tested under different conditions.")
    print("EC50 values appear to be log-transformed and are stored as-is.")
    
    # Get database session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    try:
        # Load preprocessed data
        processed_file = PROCESSED_DATA_DIR / PROCESSED_DATA_FILE
        if not processed_file.exists():
            print(f"\nERROR: Processed file not found: {processed_file}")
            print("Please run preprocess_nanotox.py first.")
            return
        
        df = pd.read_csv(processed_file)
        print(f"\nLoaded {len(df)} rows from {PROCESSED_DATA_FILE}")
        
        # Get current database counts
        count_materials_before = session.query(MaterialRecord).count()
        count_toxicity_before = session.query(ToxicityRecord).count()
        print(f"Current material_records count: {count_materials_before}")
        print(f"Current toxicity_records count: {count_toxicity_before}")
        
        # Insert into database
        print("\nInserting into database...")
        materials_inserted, toxicities_inserted, duplicates_skipped = insert_to_database(df, session)
        
        # Get final database counts
        count_materials_after = session.query(MaterialRecord).count()
        count_toxicity_after = session.query(ToxicityRecord).count()
        
        print(f"\nInsertion summary:")
        print(f"  Materials inserted: {materials_inserted}")
        print(f"  Toxicity records inserted: {toxicities_inserted}")
        print(f"  Duplicates skipped: {duplicates_skipped}")
        print(f"  Material records before: {count_materials_before}")
        print(f"  Material records after: {count_materials_after}")
        print(f"  Net material change: {count_materials_after - count_materials_before}")
        print(f"  Toxicity records before: {count_toxicity_before}")
        print(f"  Toxicity records after: {count_toxicity_after}")
        print(f"  Net toxicity change: {count_toxicity_after - count_toxicity_before}")
        
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
