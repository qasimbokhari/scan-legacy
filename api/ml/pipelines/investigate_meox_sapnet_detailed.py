"""
Investigate MeOx and SAPNet source files - detailed analysis.
Save output to file for full visibility.
"""

import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent.parent
RAW_DATA_DIR = BASE_DIR / "data" / "raw" / "zenodo_toxicity"
OUTPUT_FILE = BASE_DIR / "meox_sapnet_investigation.txt"

FILES_TO_INVESTIGATE = [
    "05_MODEL_MeOxDMEM_tox_DatasetReport.xlsx",
    "02_MODEL_SAPNet_EC50_DatasetReport.xlsx",
    "04_MODEL_Hydro-diameter_MeOx_DMEM_ Dataset Report.xlsx",
]

with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    f.write("="*80 + "\n")
    f.write("MEOX AND SAPNET SOURCE FILE INVESTIGATION\n")
    f.write("="*80 + "\n\n")
    
    for filename in FILES_TO_INVESTIGATE:
        file_path = RAW_DATA_DIR / filename
        
        if not file_path.exists():
            f.write(f"\n{'='*80}\n")
            f.write(f"FILE NOT FOUND: {filename}\n")
            f.write(f"{'='*80}\n")
            continue
        
        f.write(f"\n{'='*80}\n")
        f.write(f"FILE: {filename}\n")
        f.write(f"{'='*80}\n")
        
        try:
            xl_file = pd.ExcelFile(file_path)
            f.write(f"\nSheet names: {xl_file.sheet_names}\n")
            
            for sheet_name in xl_file.sheet_names:
                f.write(f"\n--- SHEET: {sheet_name} ---\n")
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                
                f.write(f"Row count: {len(df)}\n")
                f.write(f"Column count: {len(df.columns)}\n")
                f.write(f"\nColumn headers:\n")
                for i, col in enumerate(df.columns, 1):
                    f.write(f"  {i}. {col}\n")
                
                f.write(f"\nColumn dtypes:\n")
                f.write(df.dtypes.to_string())
                
                f.write(f"\n\nSample rows (first 5):\n")
                f.write(df.head(5).to_string())
                
                f.write(f"\n\nNull value counts per column:\n")
                null_counts = df.isnull().sum()
                for col, count in null_counts.items():
                    f.write(f"  {col}: {count} null ({count/len(df)*100:.1f}%)\n")
                
                f.write(f"\n\n")
        
        except Exception as e:
            f.write(f"\nERROR reading file: {e}\n")
            import traceback
            traceback.print_exc(file=f)
    
    f.write(f"\n{'='*80}\n")
    f.write("INVESTIGATION COMPLETE\n")
    f.write(f"{'='*80}\n")

print(f"Investigation complete. Output saved to: {OUTPUT_FILE}")
