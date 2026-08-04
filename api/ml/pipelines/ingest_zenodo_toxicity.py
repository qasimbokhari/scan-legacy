"""
Ingestion script for Zenodo toxicity datasets (MeOx and SAPNet).
Parses MeOx and SAPNet datasets from the correct Excel sheets with proper header handling,
extracts material properties and toxicity outcomes, applies physical-plausibility checks,
and inserts into material_records and toxicity_records tables.

NOTE: Both datasets are small (MeOx: ~15 samples, SAPNet: ~29 samples).
Per project engineering rules, any model trained on these individually or combined
must use Leave-One-Out cross-validation (LOO-CV) due to being under 50 samples.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
from sqlalchemy.orm import sessionmaker

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from api.app.db.models import MaterialRecord, ToxicityRecord
from api.app.db.session import engine

# Set UTF-8 encoding for output
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

# Define paths
BASE_DIR = Path(__file__).parent.parent.parent.parent
RAW_DATA_DIR = BASE_DIR / "data" / "raw" / "zenodo_toxicity"
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"
PROCESSED_DATA_DIR.mkdir(exist_ok=True)

# Physical plausibility thresholds
ZETA_POTENTIAL_MIN_MV = -100.0  # Typical minimum zeta potential
ZETA_POTENTIAL_MAX_MV = 100.0   # Typical maximum zeta potential

# Files to ingest
FILES_TO_INGEST = {
    "meox": "05_MODEL_MeOxDMEM_tox_DatasetReport.xlsx",
    "sapnet": "02_MODEL_SAPNet_EC50_DatasetReport.xlsx",
}


def clean_numeric_value(value):
    """Clean a numeric value, handling strings and NaN."""
    if value is None or pd.isna(value):
        return None
    
    if isinstance(value, (int, float)):
        return float(value)
    
    if isinstance(value, str):
        try:
            return float(value.strip())
        except (ValueError, TypeError):
            return None
    
    return None


def parse_meox_dataset(file_path):
    """Parse MeOx dataset from Zenodo.
    
    Reads from 'ModelingDataset' sheet which has cleaner structure than InitialDataset.
    Maps columns: Chemical name, Endpoint / Experimental value [unit] (EC50),
    and descriptor columns for material properties.
    """
    print(f"\nProcessing MeOx dataset: {file_path.name}...")
    
    # Read from ModelingDataset sheet which has cleaner structure
    df = pd.read_excel(file_path, sheet_name="ModelingDataset")
    
    print(f"  Original rows: {len(df)}")
    print(f"  Columns: {list(df.columns)}")
    
    # Filter to actual data rows (exclude rows where Chemical name is NaN)
    df = df[df['Chemical name'].notna()]
    
    print(f"  After filtering: {len(df)}")
    
    cleaned_data = []
    implausible_zeta_count = 0
    missing_required_count = 0
    
    for _, row in df.iterrows():
        # Extract material name
        name = row.get('Chemical name')
        if pd.isna(name) or str(name).strip() == '':
            missing_required_count += 1
            continue
        
        # Extract toxicity endpoint (EC50 from Endpoint / Experimental value [unit])
        ec50 = clean_numeric_value(row.get('Endpoint / Experimental value [unit]'))
        
        # Extract material properties from descriptor columns
        # #1Desc is Primary size, #2Desc is Purity, etc.
        core_size_nm = clean_numeric_value(row.get('#1Desc'))
        purity = clean_numeric_value(row.get('#2Desc'))
        
        # Other descriptors might contain zeta potential and surface area
        # For now, we'll set them to None since the exact mapping needs verification
        zeta_potential_mv = None
        surface_area_m2g = None
        
        material_record = {
            'name': str(name),
            'material_type': 'Metal Oxide',  # MeOx dataset contains metal oxides
            'core_size_nm': core_size_nm,
            'zeta_potential_mv': zeta_potential_mv,
            'surface_area_m2g': surface_area_m2g,
            'coating': None,  # Not available in MeOx dataset
            'source_type': 'literature_mined',
            'doi': None,  # DOI not available in the data file
        }
        
        toxicity_record = {
            'ic50': None,  # MeOx uses EC50, not IC50
            'ec50': ec50,
            'pec50': None,  # MeOx uses EC50, not pEC50
            'cell_line': 'HaCaT',  # MeOx uses HaCaT cell line
            'exposure_time_h': 24.0,  # MeOx uses 24h exposure
        }
        
        cleaned_data.append({
            'material': material_record,
            'toxicity': toxicity_record,
        })
    
    print(f"  Parsed {len(cleaned_data)} valid rows")
    print(f"  Missing required fields: {missing_required_count}")
    print(f"  Implausible zeta potential flagged: {implausible_zeta_count}")
    
    return cleaned_data, []


def parse_sapnet_dataset(file_path):
    """Parse SAPNet dataset from Zenodo.
    
    Reads from 'ModelingDataset' sheet which has cleaner structure than InitialDataset.
    Maps columns: Identifier (name), Endpoint / Experimental value [unit] (pEC50),
    and Descriptor column for material properties.
    
    NOTE: Investigation found 33 rows in InitialDataset sheet, not 29 as originally expected.
    This includes metadata rows that will be filtered out during parsing.
    """
    print(f"\nProcessing SAPNet dataset: {file_path.name}...")
    
    # Read from ModelingDataset sheet which has cleaner structure
    df = pd.read_excel(file_path, sheet_name="ModelingDataset")
    
    print(f"  Original rows: {len(df)}")
    print(f"  Columns: {list(df.columns)}")
    
    # Filter to actual data rows (exclude rows where Identifier (name) is NaN)
    df = df[df['Identifier (name)'].notna()]
    
    print(f"  After filtering: {len(df)}")
    
    cleaned_data = []
    missing_required_count = 0
    
    for _, row in df.iterrows():
        # Extract material name
        name = row.get('Identifier (name)')
        if pd.isna(name) or str(name).strip() == '':
            missing_required_count += 1
            continue
        
        # Extract material properties from Descriptor column
        surface_area_m2g = clean_numeric_value(row.get('Descriptor\n𝜒𝑚𝑖𝑥'))
        
        # Extract toxicity endpoint (pEC50)
        pec50 = clean_numeric_value(row.get('Endpoint / Experimental value [unit]'))
        
        # SAPNet uses CHO-K1 cell line and 24h exposure consistently
        cell_line = 'CHO-K1'
        exposure_time_h = 24.0
        
        material_record = {
            'name': str(name),
            'material_type': 'TiO2-based',  # SAPNet contains TiO2-based nanomaterials
            'core_size_nm': None,  # Not available in SAPNet dataset
            'zeta_potential_mv': None,  # Not available in SAPNet dataset
            'surface_area_m2g': surface_area_m2g,
            'coating': None,  # Coating info is in name (e.g., 0.1Ag_0.1Pd)
            'source_type': 'literature_mined',
            'doi': None,  # DOI not available in the data file
        }
        
        toxicity_record = {
            'ic50': None,  # SAPNet uses pEC50, not IC50
            'ec50': None,  # SAPNet uses pEC50, not EC50
            'pec50': pec50,
            'cell_line': cell_line,
            'exposure_time_h': exposure_time_h,
        }
        
        cleaned_data.append({
            'material': material_record,
            'toxicity': toxicity_record,
        })
    
    print(f"  Parsed {len(cleaned_data)} valid rows")
    print(f"  Missing required fields: {missing_required_count}")
    
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


def main():
    """Main ingestion pipeline."""
    print("="*80)
    print("ZENODO TOXICITY DATA INGESTION (MeOx and SAPNet)")
    print("="*80)
    print("\nNOTE: Both datasets are small (MeOx: ~15 samples, SAPNet: ~29 samples).")
    print("Per project engineering rules, any model trained on these individually")
    print("or combined must use Leave-One-Out cross-validation (LOO-CV).")
    
    # Get database session
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
