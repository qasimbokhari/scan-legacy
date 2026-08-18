"""
Ingestion script for PubChem analyte compound data.
Parses the preprocessed molecular reference properties and inserts into analyte_compounds table.

NOTE: This dataset contains 8 analyte compounds with molecular properties from PubChem.
These are reference data for analytes that can be matched against in Design Studio searches.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
from sqlalchemy.orm import sessionmaker

# Add parent directory to path for imports (running from api/ directory)
sys.path.append(str(Path(__file__).parent.parent.parent))

from app.db.models import AnalyteCompound
from app.db.session import engine

# Set UTF-8 encoding for output
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

# Define paths
BASE_DIR = Path(__file__).parent.parent.parent.parent  # Go up to scan_legacy root
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"
PROCESSED_DATA_FILE = "pubchem_analytes_clean.csv"


def insert_to_database(df, session):
    """Insert cleaned data into database with duplicate prevention."""
    compounds_inserted = 0
    duplicates_skipped = 0
    
    for _, row in df.iterrows():
        # Check for duplicate compound by name and pubchem_cid
        existing = session.query(AnalyteCompound).filter(
            AnalyteCompound.name == row['name']
        ).first()
        
        if existing:
            duplicates_skipped += 1
            continue
        
        # Insert new compound
        compound_data = {
            'name': row['name'],
            'pubchem_cid': row['pubchem_cid'] if pd.notna(row['pubchem_cid']) else None,
            'molecular_formula': row['molecular_formula'] if pd.notna(row['molecular_formula']) else None,
            'molecular_weight': row['molecular_weight'] if pd.notna(row['molecular_weight']) else None,
            'xlogp': row['xlogp'] if pd.notna(row['xlogp']) else None,
            'tpsa': row['tpsa'] if pd.notna(row['tpsa']) else None,
            'hbond_donor_count': row['hbond_donor_count'] if pd.notna(row['hbond_donor_count']) else None,
            'hbond_acceptor_count': row['hbond_acceptor_count'] if pd.notna(row['hbond_acceptor_count']) else None,
            'complexity': row['complexity'] if pd.notna(row['complexity']) else None,
            'source_type': row['source_type'],
        }
        
        compound = AnalyteCompound(**compound_data)
        session.add(compound)
        compounds_inserted += 1
    
    session.commit()
    
    return compounds_inserted, duplicates_skipped


def main():
    """Main ingestion pipeline."""
    print("="*80)
    print("PUBCHEM ANALYTE DATA INGESTION")
    print("="*80)
    print("\nNOTE: This dataset contains 8 analyte compounds with molecular properties")
    print("from PubChem. These are reference data for Design Studio searches.")
    
    # Get database session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    try:
        # Load preprocessed data
        processed_file = PROCESSED_DATA_DIR / PROCESSED_DATA_FILE
        if not processed_file.exists():
            print(f"\nERROR: Processed file not found: {processed_file}")
            print("Please run preprocess_pubchem.py first.")
            return
        
        df = pd.read_csv(processed_file)
        print(f"\nLoaded {len(df)} rows from {PROCESSED_DATA_FILE}")
        
        # Get current database count
        count_before = session.query(AnalyteCompound).count()
        print(f"Current analyte_compounds count: {count_before}")
        
        # Insert into database
        print("\nInserting into database...")
        compounds_inserted, duplicates_skipped = insert_to_database(df, session)
        
        # Get final database count
        count_after = session.query(AnalyteCompound).count()
        
        print(f"\nInsertion summary:")
        print(f"  Compounds inserted: {compounds_inserted}")
        print(f"  Duplicates skipped: {duplicates_skipped}")
        print(f"  Database count before: {count_before}")
        print(f"  Database count after: {count_after}")
        print(f"  Net change: {count_after - count_before}")
        
        if compounds_inserted > 0:
            print(f"\nCompounds loaded: {list(df['name'])}")
        
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
