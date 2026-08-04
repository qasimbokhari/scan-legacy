"""
Investigate MeOx and SAPNet source files to understand why ingestion produces placeholder data.
"""

import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent.parent
RAW_DATA_DIR = BASE_DIR / "data" / "raw" / "zenodo_toxicity"

FILES_TO_INVESTIGATE = [
    "05_MODEL_MeOxDMEM_tox_DatasetReport.xlsx",
    "02_MODEL_SAPNet_EC50_DatasetReport.xlsx",
    "04_MODEL_Hydro-diameter_MeOx_DMEM_ Dataset Report.xlsx",
]

print("="*80)
print("MEOX AND SAPNET SOURCE FILE INVESTIGATION")
print("="*80)

for filename in FILES_TO_INVESTIGATE:
    file_path = RAW_DATA_DIR / filename
    
    if not file_path.exists():
        print(f"\n{'='*80}")
        print(f"FILE NOT FOUND: {filename}")
        print(f"{'='*80}")
        continue
    
    print(f"\n{'='*80}")
    print(f"FILE: {filename}")
    print(f"{'='*80}")
    
    # Try to read Excel file
    try:
        # First, check sheet names
        xl_file = pd.ExcelFile(file_path)
        print(f"\nSheet names: {xl_file.sheet_names}")
        
        # Read each sheet
        for sheet_name in xl_file.sheet_names:
            print(f"\n--- SHEET: {sheet_name} ---")
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            
            print(f"Row count: {len(df)}")
            print(f"Column count: {len(df.columns)}")
            print(f"\nColumn headers:")
            for i, col in enumerate(df.columns, 1):
                print(f"  {i}. {col}")
            
            print(f"\nColumn dtypes:")
            print(df.dtypes)
            
            print(f"\nSample rows (first 5):")
            print(df.head(5).to_string())
            
            # Check for null values
            print(f"\nNull value counts per column:")
            null_counts = df.isnull().sum()
            for col, count in null_counts.items():
                print(f"  {col}: {count} null ({count/len(df)*100:.1f}%)")
    
    except Exception as e:
        print(f"\nERROR reading file: {e}")
        import traceback
        traceback.print_exc()

print(f"\n{'='*80}")
print("INVESTIGATION COMPLETE")
print(f"{'='*80}")
