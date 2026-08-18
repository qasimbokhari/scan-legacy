"""
Ingestion script for nanoPharos dataset.
Parses nanoPharos files, extracts material properties and toxicity outcomes,
cleans data, and inserts into material_records and toxicity_records tables.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError

# Add parent directory to path for imports (running from api/ directory)
sys.path.append(str(Path(__file__).parent.parent.parent))

from app.db.models import MaterialRecord, ToxicityRecord
from app.db.session import get_db

# Set UTF-8 encoding for output
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

# Define paths
BASE_DIR = Path(__file__).parent.parent.parent.parent  # Go up to scan_legacy root
RAW_DATA_DIR = BASE_DIR / "data" / "raw" / "nanopharos"
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"
PROCESSED_DATA_DIR.mkdir(exist_ok=True)

# Files to ingest
FILES_TO_INGEST = [
    "Metal_Oxide_cytotoxicity.xlsx",
    "Metal_oxide_facet_cytotoxicity.xlsx",
    "NanoPharos_HepaRG.xlsx",
    "ICNP_CellViability.csv",
]


def clean_numeric_value(value):
    """Clean a numeric value, handling strings like '40.7/25.3'."""
    if value is None or pd.isna(value):
        return None
    
    if isinstance(value, (int, float)):
        return float(value)
    
    if isinstance(value, str):
        # Handle strings like '40.7/25.3' - take the first value
        if '/' in value:
            parts = value.split('/')
            try:
                return float(parts[0].strip())
            except (ValueError, TypeError):
                return None
        
        # Try to convert to float directly
        try:
            return float(value.strip())
        except (ValueError, TypeError):
            return None
    
    return None


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


def parse_metal_oxide_cytotoxicity(file_path):
    """Parse Metal_Oxide_cytotoxicity.xlsx."""
    print(f"\nProcessing {file_path.name}...")
    df = pd.read_excel(file_path)
    print(f"  Original rows: {len(df)}")
    
    # Map columns to schema
    cleaned_data = []
    dropped_columns = []
    
    for _, row in df.iterrows():
        material_record = {
            'name': row.get('Material type', f"Unknown_{row.get('ERM ID', '')}"),
            'material_type': row.get('Material type', 'Unknown'),
            'core_size_nm': clean_numeric_value(row.get('Core size (nm)')),
            'zeta_potential_mv': clean_numeric_value(row.get('Surface charge (mV)')),
            'surface_area_m2g': clean_numeric_value(row.get('Surface area (m2/g)')),
            'coating': None,
            'source_type': 'literature_mined',
            'doi': None,
        }
        
        # Parse exposure time (e.g., "24h" -> 24.0)
        exposure_time_str = row.get('Exposure time', '')
        if isinstance(exposure_time_str, str):
            exposure_time_str = exposure_time_str.replace('h', '').strip()
        try:
            exposure_time = float(exposure_time_str) if exposure_time_str else None
        except (ValueError, TypeError):
            exposure_time = None
        
        toxicity_record = {
            'ic50': None,
            'ec50': None,
            'cell_line': row.get('Cell name'),
            'exposure_time_h': exposure_time,
        }
        
        cleaned_data.append({
            'material': material_record,
            'toxicity': toxicity_record,
        })
    
    return cleaned_data, dropped_columns


def parse_metal_oxide_facet_cytotoxicity(file_path):
    """Parse Metal_oxide_facet_cytotoxicity.xlsx."""
    print(f"\nProcessing {file_path.name}...")
    df = pd.read_excel(file_path)
    print(f"  Original rows: {len(df)}")
    
    cleaned_data = []
    
    for _, row in df.iterrows():
        material_record = {
            'name': row.get('Metal oxide', 'Unknown'),
            'material_type': row.get('Metal oxide', 'Unknown'),
            'core_size_nm': clean_numeric_value(row.get('Core Size (nm)')),
            'zeta_potential_mv': clean_numeric_value(row.get('Surface Charge (mV)')),
            'surface_area_m2g': None,
            'coating': None,
            'source_type': 'literature_mined',
            'doi': None,
        }
        
        toxicity_record = {
            'ic50': None,
            'ec50': None,
            'cell_line': None,
            'exposure_time_h': None,
        }
        
        cleaned_data.append({
            'material': material_record,
            'toxicity': toxicity_record,
        })
    
    return cleaned_data, []


def parse_nanopharos_heparg(file_path):
    """Parse NanoPharos_HepaRG.xlsx."""
    print(f"\nProcessing {file_path.name}...")
    df = pd.read_excel(file_path)
    print(f"  Original rows: {len(df)}")
    
    cleaned_data = []
    
    for _, row in df.iterrows():
        material_record = {
            'name': row.get('Nanoparticle', 'Unknown'),
            'material_type': row.get('metal core', 'Unknown'),
            'core_size_nm': clean_numeric_value(row.get('Size in ASCOT [nm]')),
            'zeta_potential_mv': None,
            'surface_area_m2g': None,
            'coating': None,
            'source_type': 'literature_mined',
            'doi': None,
        }
        
        toxicity_record = {
            'ic50': None,
            'ec50': None,
            'cell_line': 'HepaRG',
            'exposure_time_h': None,
        }
        
        cleaned_data.append({
            'material': material_record,
            'toxicity': toxicity_record,
        })
    
    return cleaned_data, []


def parse_icnp_cellviability(file_path):
    """Parse ICNP_CellViability.csv."""
    print(f"\nProcessing {file_path.name}...")
    df = pd.read_csv(file_path)
    print(f"  Original rows: {len(df)}")
    
    cleaned_data = []
    
    for _, row in df.iterrows():
        # Create composite name from core and shell
        core = row.get('Iron Carbide core phase', 'Unknown')
        shell = row.get('Shell material', 'Unknown')
        name = f"{core}/{shell}"
        
        material_record = {
            'name': name,
            'material_type': f"{core}_{shell}",
            'core_size_nm': clean_numeric_value(row.get('Core size (nm)')),
            'zeta_potential_mv': None,
            'surface_area_m2g': None,
            'coating': row.get('Surface Functionalisation'),
            'source_type': 'literature_mined',
            'doi': row.get('DOI'),
        }
        
        toxicity_record = {
            'ic50': None,
            'ec50': None,
            'cell_line': row.get('Cell line'),
            'exposure_time_h': None,
        }
        
        cleaned_data.append({
            'material': material_record,
            'toxicity': toxicity_record,
        })
    
    return cleaned_data, []


def insert_to_database(cleaned_data, session):
    """Insert cleaned data into database with improved duplicate prevention.
    
    Duplicate detection logic:
    - MaterialRecord: Match on (name + material_type + core_size_nm + zeta_potential_mv + 
                        surface_area_m2g + coating) - all material properties
    - ToxicityRecord: Match on (material_id + cell_line + exposure_time_h) - allow multiple
                      toxicity records per material if they have different test conditions
    """
    materials_inserted = 0
    toxicities_inserted = 0
    duplicates_skipped = 0
    
    for item in cleaned_data:
        material_data = item['material']
        toxicity_data = item['toxicity']
        
        # Check for duplicate material using all material properties
        existing = session.query(MaterialRecord).filter(
            MaterialRecord.name == material_data['name'],
            MaterialRecord.material_type == material_data['material_type'],
            MaterialRecord.source_type == material_data['source_type'],
            MaterialRecord.core_size_nm == material_data['core_size_nm'],
            MaterialRecord.zeta_potential_mv == material_data['zeta_potential_mv'],
            MaterialRecord.surface_area_m2g == material_data['surface_area_m2g'],
            MaterialRecord.coating == material_data['coating']
        ).first()
        
        if existing:
            # Material exists, check if toxicity record already exists for this test condition
            if any(toxicity_data.values()):
                existing_tox = session.query(ToxicityRecord).filter(
                    ToxicityRecord.material_id == existing.id,
                    ToxicityRecord.cell_line == toxicity_data['cell_line'],
                    ToxicityRecord.exposure_time_h == toxicity_data['exposure_time_h']
                ).first()
                
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
    print("NANOPHAROS DATA INGESTION")
    print("="*80)
    
    # Get database session
    from app.db.session import engine
    from sqlalchemy.orm import sessionmaker
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    try:
        all_cleaned_data = []
        all_dropped_columns = []
        
        # Parse all files
        for filename in FILES_TO_INGEST:
            file_path = RAW_DATA_DIR / filename
            if not file_path.exists():
                print(f"  WARNING: File not found: {filename}")
                continue
            
            if filename == "Metal_Oxide_cytotoxicity.xlsx":
                cleaned_data, dropped_cols = parse_metal_oxide_cytotoxicity(file_path)
            elif filename == "Metal_oxide_facet_cytotoxicity.xlsx":
                cleaned_data, dropped_cols = parse_metal_oxide_facet_cytotoxicity(file_path)
            elif filename == "NanoPharos_HepaRG.xlsx":
                cleaned_data, dropped_cols = parse_nanopharos_heparg(file_path)
            elif filename == "ICNP_CellViability.csv":
                cleaned_data, dropped_cols = parse_icnp_cellviability(file_path)
            else:
                print(f"  WARNING: Unknown file type: {filename}")
                continue
            
            all_cleaned_data.extend(cleaned_data)
            all_dropped_columns.extend(dropped_cols)
        
        print(f"\nTotal records parsed: {len(all_cleaned_data)}")
        
        if all_dropped_columns:
            print("\nColumns dropped due to excessive missing data:")
            for col in all_dropped_columns:
                print(f"  - {col}")
        
        # Create processed CSV for inspection
        if all_cleaned_data:
            processed_df = pd.DataFrame([
                {**item['material'], **item['toxicity']} 
                for item in all_cleaned_data
            ])
            output_path = PROCESSED_DATA_DIR / "nanopharos_clean.csv"
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
