"""
Preprocessing script for nanotox_dataset.csv.
Cleans and validates the nanoparticle toxicity data for ingestion.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys

# Set UTF-8 encoding for output
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

# Define paths
BASE_DIR = Path(__file__).parent.parent.parent.parent  # Go up to scan_legacy root
RAW_DATA_DIR = BASE_DIR / "data" / "raw" / "other"
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"
PROCESSED_DATA_DIR.mkdir(exist_ok=True)

INPUT_FILE = "nanotox_dataset.csv"
OUTPUT_FILE = "nanotox_clean.csv"


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


def preprocess_nanotox():
    """Preprocess nanotox dataset."""
    print("="*80)
    print("NANOTOX DATA PREPROCESSING")
    print("="*80)
    
    # Load raw data
    input_path = RAW_DATA_DIR / INPUT_FILE
    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}")
        return
    
    df = pd.read_csv(input_path)
    print(f"\nLoaded {len(df)} rows from {INPUT_FILE}")
    print(f"Columns: {list(df.columns)}")
    
    # Report data quality
    print(f"\nData quality assessment:")
    print(f"  Missing values: {df.isnull().sum().sum()}")
    print(f"  Duplicate rows: {df.duplicated().sum()}")
    
    # No missing values - this is suspicious for real experimental data
    if df.isnull().sum().sum() == 0:
        print("  WARNING: Zero missing values - unusual for experimental data")
    
    # Report unique materials
    print(f"\nUnique materials: {df['NPs'].unique()}")
    print(f"Class distribution: {df['class'].value_counts().to_dict()}")
    
    # Map columns to database schema
    # The dataset has:
    # NPs -> material_type
    # coresize -> core_size_nm
    # surfcharge -> zeta_potential_mv
    # surfarea -> surface_area_m2g
    # Ec -> ec50 (appears to be log-transformed, negative values)
    # Expotime -> exposure_time_h
    # dosage -> additional field (will store as extra data)
    # class -> toxicity classification (will not store in main schema)
    
    cleaned_data = []
    
    for _, row in df.iterrows():
        material_record = {
            'name': str(row['NPs']),
            'material_type': str(row['NPs']),  # Use material name as type
            'core_size_nm': clean_numeric_value(row['coresize']),
            'zeta_potential_mv': clean_numeric_value(row['surfcharge']),
            'surface_area_m2g': clean_numeric_value(row['surfarea']),
            'coating': None,  # No coating information in this dataset
            'source_type': 'literature_mined',
            'doi': None,
        }
        
        # Ec appears to be log-transformed EC50 (negative values)
        # We'll store it as-is; it may need to be exponentiated for actual EC50 values
        ec50_value = clean_numeric_value(row['Ec'])
        
        toxicity_record = {
            'ic50': None,
            'ec50': ec50_value,  # Store as-is (may be log-transformed)
            'pec50': None,
            'cell_line': None,  # Not specified in dataset
            'exposure_time_h': clean_numeric_value(row['Expotime']),
        }
        
        cleaned_data.append({
            'material': material_record,
            'toxicity': toxicity_record,
            'extra_data': {
                'hydrosize': clean_numeric_value(row['hydrosize']),
                'dosage': clean_numeric_value(row['dosage']),
                'e': clean_numeric_value(row['e']),
                'NOxygen': clean_numeric_value(row['NOxygen']),
                'class': row['class'],
            }
        })
    
    # Create processed DataFrame
    processed_df = pd.DataFrame([
        {**item['material'], **item['toxicity'], **item['extra_data']}
        for item in cleaned_data
    ])
    
    # Ensure proper data types - replace NaN with None for string columns
    processed_df['coating'] = processed_df['coating'].astype(object).where(pd.notnull(processed_df['coating']), None)
    processed_df['cell_line'] = processed_df['cell_line'].astype(object).where(pd.notnull(processed_df['cell_line']), None)
    
    # Save processed data
    output_path = PROCESSED_DATA_DIR / OUTPUT_FILE
    processed_df.to_csv(output_path, index=False)
    
    print(f"\nProcessed data saved to: {output_path}")
    print(f"Final row count: {len(processed_df)}")
    print(f"Final columns: {list(processed_df.columns)}")
    
    # Note about EC50 values
    print(f"\nNOTE: EC50 values appear to be log-transformed (negative values).")
    print(f"      These are stored as-is and may need to be exponentiated for actual EC50.")
    
    print("\n" + "="*80)
    print("PREPROCESSING COMPLETE")
    print("="*80)


if __name__ == "__main__":
    preprocess_nanotox()
