"""
Ingestion script for Zenodo toxicity datasets.
Parses MeOx and SAPNet datasets, extracts material properties and toxicity outcomes,
cleans data, and inserts into material_records and toxicity_records tables.
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
RAW_DATA_DIR = BASE_DIR / "data" / "raw" / "zenodo_toxicity"
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"
PROCESSED_DATA_DIR.mkdir(exist_ok=True)

# Zenodo DOI for the dataset
ZENODO_DOI = "10.5281/zenodo.XXXXXX"  # Placeholder - will check if DOI exists in files

# Files to ingest
FILES_TO_INGEST = {
    "meox": "05_MODEL_MeOxDMEM_tox_DatasetReport.xlsx",
    "sapnet": "02_MODEL_SAPNet_EC50_DatasetReport.xlsx",
}


def clean_and_impute(df, column_name):
    """
    Clean a column: median imputation if <20% missing, drop if >50% missing.
    Returns the cleaned column and a log message.
    """
    missing_pct = df[column_name].isna().sum() / len(df) * 100
    
    if missing_pct > 50:
        df = df.drop(columns=[column_name])
        return None, f"Dropped column '{column_name}' ({missing_pct:.1f}% missing)"
    elif missing_pct > 0:
        median_val = df[column_name].median()
        df[column_name] = df[column_name].fillna(median_val)
        return df[column_name], f"Imputed {missing_pct:.1f}% missing in '{column_name}' with median {median_val}"
    else:
        return df[column_name], f"No missing values in '{column_name}'"


def parse_meox_dataset(file_path):
    """Parse MeOx dataset from Zenodo."""
    print(f"\nProcessing MeOx dataset: {file_path.name}...")
    df = pd.read_excel(file_path)
    print(f"  Original rows: {len(df)}")
    print(f"  Columns: {list(df.columns)}")
    
    cleaned_data = []
    dropped_columns = []
    
    # Try to identify material and toxicity columns
    # Based on typical Zenodo toxicity dataset structure
    for _, row in df.iterrows():
        # Attempt to map columns - this will be adjusted based on actual structure
        material_record = {
            'name': 'Unknown_MeOx',
            'material_type': 'Metal Oxide',
            'core_size_nm': None,
            'zeta_potential_mv': None,
            'surface_area_m2g': None,
            'coating': None,
            'source_type': 'literature_mined',
            'doi': ZENODO_DOI,
        }
        
        toxicity_record = {
            'ic50': None,
            'ec50': None,
            'cell_line': None,
            'exposure_time_h': None,
        }
        
        # Try to extract EC50 if column exists
        ec50_col = None
        for col in df.columns:
            if 'ec50' in col.lower() or 'EC50' in col:
                ec50_col = col
                break
        
        if ec50_col:
            try:
                toxicity_record['ec50'] = float(row[ec50_col])
            except (ValueError, TypeError):
                pass
        
        # Try to extract material name
        material_col = None
        for col in df.columns:
            if 'material' in col.lower() or 'oxide' in col.lower() or 'nanoparticle' in col.lower():
                material_col = col
                break
        
        if material_col:
            material_record['name'] = str(row[material_col])
            material_record['material_type'] = str(row[material_col])
        
        # Try to extract cell line
        cell_col = None
        for col in df.columns:
            if 'cell' in col.lower():
                cell_col = col
                break
        
        if cell_col:
            toxicity_record['cell_line'] = str(row[cell_col])
        
        cleaned_data.append({
            'material': material_record,
            'toxicity': toxicity_record,
        })
    
    return cleaned_data, dropped_columns


def parse_sapnet_dataset(file_path):
    """Parse SAPNet dataset from Zenodo."""
    print(f"\nProcessing SAPNet dataset: {file_path.name}...")
    df = pd.read_excel(file_path)
    print(f"  Original rows: {len(df)}")
    print(f"  Columns: {list(df.columns)}")
    
    cleaned_data = []
    dropped_columns = []
    
    for _, row in df.iterrows():
        material_record = {
            'name': 'Unknown_SAPNet',
            'material_type': 'Unknown',
            'core_size_nm': None,
            'zeta_potential_mv': None,
            'surface_area_m2g': None,
            'coating': None,
            'source_type': 'literature_mined',
            'doi': ZENODO_DOI,
        }
        
        toxicity_record = {
            'ic50': None,
            'ec50': None,
            'cell_line': None,
            'exposure_time_h': None,
        }
        
        # Try to extract EC50 if column exists
        ec50_col = None
        for col in df.columns:
            if 'ec50' in col.lower() or 'EC50' in col:
                ec50_col = col
                break
        
        if ec50_col:
            try:
                toxicity_record['ec50'] = float(row[ec50_col])
            except (ValueError, TypeError):
                pass
        
        # Try to extract material name
        material_col = None
        for col in df.columns:
            if 'material' in col.lower() or 'nanoparticle' in col.lower():
                material_col = col
                break
        
        if material_col:
            material_record['name'] = str(row[material_col])
            material_record['material_type'] = str(row[material_col])
        
        cleaned_data.append({
            'material': material_record,
            'toxicity': toxicity_record,
        })
    
    return cleaned_data, dropped_columns


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
    print("ZENODO TOXICITY DATA INGESTION")
    print("="*80)
    
    # Get database session
    from api.app.db.session import engine
    from sqlalchemy.orm import sessionmaker
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    try:
        # Process MeOx dataset
        meox_file = RAW_DATA_DIR / FILES_TO_INGEST['meox']
        if meox_file.exists():
            meox_data, meox_dropped = parse_meox_dataset(meox_file)
            
            if meox_data:
                meox_df = pd.DataFrame([
                    {**item['material'], **item['toxicity']} 
                    for item in meox_data
                ])
                meox_output = PROCESSED_DATA_DIR / "meox_clean.csv"
                meox_df.to_csv(meox_output, index=False)
                print(f"  MeOx processed data saved to: {meox_output}")
                
                issues = validate_processed_data(meox_df)
                if issues:
                    print("  VALIDATION ISSUES:")
                    for issue in issues:
                        print(f"    - {issue}")
        else:
            print(f"  WARNING: MeOx file not found: {meox_file}")
            meox_data = []
        
        # Process SAPNet dataset
        sapnet_file = RAW_DATA_DIR / FILES_TO_INGEST['sapnet']
        if sapnet_file.exists():
            sapnet_data, sapnet_dropped = parse_sapnet_dataset(sapnet_file)
            
            if sapnet_data:
                sapnet_df = pd.DataFrame([
                    {**item['material'], **item['toxicity']} 
                    for item in sapnet_data
                ])
                sapnet_output = PROCESSED_DATA_DIR / "sapnet_clean.csv"
                sapnet_df.to_csv(sapnet_output, index=False)
                print(f"  SAPNet processed data saved to: {sapnet_output}")
                
                issues = validate_processed_data(sapnet_df)
                if issues:
                    print("  VALIDATION ISSUES:")
                    for issue in issues:
                        print(f"    - {issue}")
        else:
            print(f"  WARNING: SAPNet file not found: {sapnet_file}")
            sapnet_data = []
        
        # Combine all data
        all_cleaned_data = meox_data + sapnet_data
        
        print(f"\nTotal records parsed: {len(all_cleaned_data)}")
        print(f"  MeOx: {len(meox_data)}")
        print(f"  SAPNet: {len(sapnet_data)}")
        
        # Insert into database
        print("\nInserting into database...")
        materials_inserted, toxicities_inserted, duplicates_skipped = insert_to_database(
            all_cleaned_data, session
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
