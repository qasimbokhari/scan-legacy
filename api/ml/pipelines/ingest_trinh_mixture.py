"""
Ingestion script for Trinh mixture toxicity dataset.
Parses the Trinh mixture toxicity dataset (classification data: toxic/not-toxic),
cleans data, and inserts into material_records and toxicity_records tables.

NOTE: This dataset contains classification outcomes (toxic/not-toxic) rather than
continuous IC50/EC50 values. Since the ToxicityRecord schema doesn't have a dedicated
classification field, we store the classification in the ic50 field using a sentinel pattern:
- toxic: ic50 = 1.0
- not-toxic: ic50 = 0.0
- unknown: ic50 = None

This approach allows the data to be stored while clearly indicating that these are
classification labels, not continuous toxicity values. A schema adjustment may be
needed in the future to properly support classification data.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
from sqlalchemy.orm import Session
from sqlalchemy import create_engine

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from api.app.db.models import MaterialRecord, ToxicityRecord
from api.app.db.session import get_db

# Set UTF-8 encoding for output
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

# Define paths
BASE_DIR = Path(__file__).parent.parent.parent.parent
RAW_DATA_DIR = BASE_DIR / "data" / "raw" / "zenodo_nanomaterials"
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"
PROCESSED_DATA_DIR.mkdir(exist_ok=True)

# File to ingest
TRINH_FILE = "Supplementary-materials-Trinh-and-Kim-Nanomaterials-2021.xlsx"


def parse_trinh_dataset(file_path):
    """Parse Trinh mixture toxicity dataset."""
    print(f"\nProcessing Trinh mixture dataset: {file_path.name}...")
    df = pd.read_excel(file_path)
    print(f"  Original rows: {len(df)}")
    print(f"  Columns: {list(df.columns)}")
    
    cleaned_data = []
    
    for _, row in df.iterrows():
        # Extract nanomaterial name
        nanomaterial = row.get('Nanomaterials', 'Unknown')
        
        material_record = {
            'name': nanomaterial,
            'material_type': 'Mixture',
            'core_size_nm': None,
            'zeta_potential_mv': None,
            'surface_area_m2g': None,
            'coating': None,
            'source_type': 'literature_mined',
            'doi': None,  # DOI may be in the Article column
        }
        
        # Extract DOI from Article column if available
        article = row.get('Article', '')
        if 'doi' in str(article).lower() or '10.' in str(article):
            material_record['doi'] = str(article)
        
        # Parse toxicity classification
        # This is classification data, not continuous IC50/EC50
        # We'll use a sentinel pattern in ic50 field:
        # toxic = 1.0, not-toxic = 0.0, unknown = None
        toxicity_class = row.get('Toxicology category', '').lower()
        
        if 'toxic' in toxicity_class:
            ic50_sentinel = 1.0  # Sentinel for toxic
        elif 'non' in toxicity_class or 'not' in toxicity_class:
            ic50_sentinel = 0.0  # Sentinel for non-toxic
        else:
            ic50_sentinel = None  # Unknown
        
        toxicity_record = {
            'ic50': ic50_sentinel,  # Using sentinel pattern for classification
            'ec50': None,
            'cell_line': row.get('Test organism'),
            'exposure_time_h': None,
        }
        
        cleaned_data.append({
            'material': material_record,
            'toxicity': toxicity_record,
            'raw_classification': toxicity_class,  # Store for reference
        })
    
    return cleaned_data


def insert_to_database(cleaned_data, session):
    """Insert cleaned data into database with duplicate prevention."""
    materials_inserted = 0
    toxicities_inserted = 0
    duplicates_skipped = 0
    
    for item in cleaned_data:
        material_data = item['material']
        toxicity_data = item['toxicity']
        
        # Check for duplicate material
        existing = session.query(MaterialRecord).filter(
            MaterialRecord.name == material_data['name'],
            MaterialRecord.material_type == material_data['material_type'],
            MaterialRecord.source_type == material_data['source_type']
        ).first()
        
        if existing:
            duplicates_skipped += 1
            continue
        
        # Insert material
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
    print("TRINH MIXTURE TOXICITY DATA INGESTION")
    print("="*80)
    print("\nNOTE: This dataset contains classification outcomes (toxic/not-toxic).")
    print("Since the schema doesn't have a dedicated classification field,")
    print("we use a sentinel pattern in ic50: toxic=1.0, non-toxic=0.0.")
    print("A schema adjustment may be needed for proper classification support.")
    
    # Get database session
    from api.app.db.session import engine
    from sqlalchemy.orm import sessionmaker
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    try:
        # Process Trinh dataset
        trinh_file = RAW_DATA_DIR / TRINH_FILE
        if not trinh_file.exists():
            print(f"\nERROR: Trinh file not found: {trinh_file}")
            return
        
        cleaned_data = parse_trinh_dataset(trinh_file)
        
        if cleaned_data:
            # Create processed CSV for inspection
            processed_df = pd.DataFrame([
                {**item['material'], **item['toxicity'], 'raw_classification': item['raw_classification']}
                for item in cleaned_data
            ])
            output_path = PROCESSED_DATA_DIR / "trinh_clean.csv"
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
            
            # Count classifications
            toxic_count = sum(1 for item in cleaned_data if item['raw_classification'] and 'toxic' in item['raw_classification'].lower())
            nontoxic_count = sum(1 for item in cleaned_data if item['raw_classification'] and ('non' in item['raw_classification'].lower() or 'not' in item['raw_classification'].lower()))
            unknown_count = len(cleaned_data) - toxic_count - nontoxic_count
            
            print(f"\nClassification breakdown:")
            print(f"  Toxic: {toxic_count}")
            print(f"  Non-toxic: {nontoxic_count}")
            print(f"  Unknown: {unknown_count}")
        
        print(f"\nTotal records parsed: {len(cleaned_data)}")
        
        # Insert into database
        print("\nInserting into database...")
        materials_inserted, toxicities_inserted, duplicates_skipped = insert_to_database(
            cleaned_data, session
        )
        
        print(f"\nInsertion summary:")
        print(f"  Materials inserted: {materials_inserted}")
        print(f"  Toxicity records inserted: {toxicities_inserted}")
        print(f"  Duplicates skipped: {duplicates_skipped}")
        
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
