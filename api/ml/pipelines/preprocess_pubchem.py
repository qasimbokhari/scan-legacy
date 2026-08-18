"""
Preprocessing script for PubChem analyte compound data.
Cleans and validates molecular reference properties for analytes.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
import os

# Set UTF-8 encoding for output
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

# Define paths
# Script is in api/ml/pipelines/, need to go up 4 levels to reach scan_legacy root
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
RAW_DATA_DIR = BASE_DIR / "data" / "raw" / "pubchem"
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"
PROCESSED_DATA_DIR.mkdir(exist_ok=True)

# PubChem files to process
PUBCHEM_FILES = {
    'arsenic.csv': 'Arsenic',
    'cadmium.csv': 'Cadmium',
    'cotisol.csv': 'Cotisol',
    'dopamine.csv': 'Dopamine',
    'glucose.csv': 'Glucose',
    'lead.csv': 'Lead',
    'mercury.csv': 'Mercury',
    'nitrate.csv': 'Nitrate',
}

OUTPUT_FILE = "pubchem_analytes_clean.csv"


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


def preprocess_pubchem():
    """Preprocess PubChem analyte data."""
    print("="*80)
    print("PUBCHEM ANALYTE DATA PREPROCESSING")
    print("="*80)
    
    all_data = []
    
    for filename, compound_name in PUBCHEM_FILES.items():
        input_path = RAW_DATA_DIR / filename
        if not input_path.exists():
            print(f"WARNING: File not found: {filename}")
            continue
        
        df = pd.read_csv(input_path)
        print(f"\nProcessing {filename} ({compound_name})")
        print(f"  Rows: {len(df)}")
        print(f"  Columns: {list(df.columns)}")
        
        if len(df) == 0:
            print(f"  WARNING: Empty file")
            continue
        
        # Extract first row (each file contains 1 row)
        row = df.iloc[0]
        
        # Clean numeric values
        hbond_donor = clean_numeric_value(row.get('HBondDonorCount'))
        hbond_acceptor = clean_numeric_value(row.get('HBondAcceptorCount'))
        
        compound_data = {
            'name': compound_name,
            'pubchem_cid': clean_numeric_value(row.get('CID')),
            'molecular_formula': row.get('MolecularFormula'),
            'molecular_weight': clean_numeric_value(row.get('MolecularWeight')),
            'xlogp': clean_numeric_value(row.get('XLogP')),
            'tpsa': clean_numeric_value(row.get('TPSA')),
            'hbond_donor_count': int(hbond_donor) if hbond_donor is not None else None,
            'hbond_acceptor_count': int(hbond_acceptor) if hbond_acceptor is not None else None,
            'complexity': clean_numeric_value(row.get('Complexity')),
            'source_type': 'pubchem',
        }
        
        all_data.append(compound_data)
        print(f"  Formula: {compound_data['molecular_formula']}")
        print(f"  Molecular weight: {compound_data['molecular_weight']}")
    
    if not all_data:
        print("\nERROR: No data processed")
        return
    
    # Create processed DataFrame
    processed_df = pd.DataFrame(all_data)
    
    # Save processed data
    output_path = PROCESSED_DATA_DIR / OUTPUT_FILE
    processed_df.to_csv(output_path, index=False)
    
    print(f"\nProcessed data saved to: {output_path}")
    print(f"Total compounds processed: {len(processed_df)}")
    print(f"Compounds: {list(processed_df['name'])}")
    
    print("\n" + "="*80)
    print("PREPROCESSING COMPLETE")
    print("="*80)


if __name__ == "__main__":
    preprocess_pubchem()
