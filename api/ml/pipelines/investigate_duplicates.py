"""
Investigate duplicate detection issue in nanoPharos and Zenodo ingestion.
Compare CSV data with database records to identify wrongly collapsed rows.
"""

import pandas as pd
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from sqlalchemy.orm import sessionmaker
from sqlalchemy import func
from api.app.db.models import MaterialRecord, ToxicityRecord
from api.app.db.session import engine

# Set UTF-8 encoding for output
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

BASE_DIR = Path(__file__).parent.parent.parent.parent
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"


def main():
    """Investigate duplicate detection."""
    print("="*80)
    print("DUPLICATE DETECTION INVESTIGATION")
    print("="*80)
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    try:
        # Load nanoPharos CSV
        nanopharos_csv = PROCESSED_DATA_DIR / "nanopharos_clean.csv"
        nanopharos_df = pd.read_csv(nanopharos_csv)
        
        print(f"\nNANOPHAROS CSV ANALYSIS:")
        print(f"Total rows in CSV: {len(nanopharos_df)}")
        
        # Check for missing names
        missing_names = nanopharos_df['name'].isna().sum()
        print(f"Rows with missing name: {missing_names}")
        
        # Check unique (name, material_type, source_type) combinations
        unique_key_combos = nanopharos_df.groupby(['name', 'material_type', 'source_type']).size()
        print(f"Unique (name + material_type + source_type) combinations: {len(unique_key_combos)}")
        
        # Show combinations with multiple rows
        multi_row_combos = unique_key_combos[unique_key_combos > 1]
        print(f"Combinations with multiple rows: {len(multi_row_combos)}")
        
        if len(multi_row_combos) > 0:
            print(f"\nTop 10 combinations with most rows:")
            for (name, mat_type, src_type), count in multi_row_combos.nlargest(10).items():
                print(f"  ({name}, {mat_type}, {src_type}): {count} rows")
        
        # Check database state
        print(f"\nDATABASE STATE:")
        total_materials = session.query(func.count(MaterialRecord.id)).scalar()
        total_toxicities = session.query(func.count(ToxicityRecord.id)).scalar()
        
        print(f"Total MaterialRecord rows: {total_materials}")
        print(f"Total ToxicityRecord rows: {total_toxicities}")
        
        # Get nanoPharos materials from database (exclude caNanoLab which has material_type='Unknown')
        nanopharos_materials = session.query(MaterialRecord).filter(
            MaterialRecord.material_type != 'Unknown'
        ).all()
        
        print(f"MaterialRecord rows with material_type != 'Unknown' (likely nanoPharos): {len(nanopharos_materials)}")
        
        # Show sample materials
        print(f"\nSample materials in database:")
        for i, mat in enumerate(nanopharos_materials[:15], 1):
            print(f"  {i}. name={mat.name}, type={mat.material_type}, core_size={mat.core_size_nm}, zeta={mat.zeta_potential_mv}")
        
        # Check MeOx/SAPNet CSVs
        print(f"\n\nMEOX/SAPNET CSV ANALYSIS:")
        meox_csv = PROCESSED_DATA_DIR / "meox_clean.csv"
        sapnet_csv = PROCESSED_DATA_DIR / "sapnet_clean.csv"
        
        if meox_csv.exists():
            meox_df = pd.read_csv(meox_csv)
            print(f"MeOx CSV rows: {len(meox_df)}")
            print(f"MeOx missing names: {meox_df['name'].isna().sum()}")
            unique_meox = meox_df.groupby(['name', 'material_type', 'source_type']).size()
            print(f"MeOx unique key combos: {len(unique_meox)}")
        
        if sapnet_csv.exists():
            sapnet_df = pd.read_csv(sapnet_csv)
            print(f"SAPNet CSV rows: {len(sapnet_df)}")
            print(f"SAPNet missing names: {sapnet_df['name'].isna().sum()}")
            unique_sapnet = sapnet_df.groupby(['name', 'material_type', 'source_type']).size()
            print(f"SAPNet unique key combos: {len(unique_sapnet)}")
        
        # Detailed analysis: show specific examples
        print(f"\n\nDETAILED EXAMPLE: ZnO rows in CSV")
        zno_rows = nanopharos_df[nanopharos_df['name'] == 'ZnO'].head(10)
        print(f"First 10 ZnO rows:")
        for i, row in zno_rows.iterrows():
            print(f"  Row {i}: core_size={row['core_size_nm']}, zeta={row['zeta_potential_mv']}, cell_line={row['cell_line']}")
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()
    
    print("\n" + "="*80)
    print("INVESTIGATION COMPLETE")
    print("="*80)


if __name__ == "__main__":
    main()
