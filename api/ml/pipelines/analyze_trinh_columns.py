"""
Analyze Trinh mixture toxicity dataset columns.
Lists all column headers and their unique values to identify
which column contains genuine toxicity outcomes.
"""

import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent.parent
RAW_DATA_DIR = BASE_DIR / "data" / "raw" / "zenodo_nanomaterials"

TRINH_FILE = "Supplementary-materials-Trinh-and-Kim-Nanomaterials-2021.xlsx"

df = pd.read_excel(RAW_DATA_DIR / TRINH_FILE)

print("="*80)
print("TRINH MIXTURE TOXICITY DATASET - COLUMN ANALYSIS")
print("="*80)

print(f"\nTotal rows: {len(df)}")
print(f"\nCOLUMNS ({len(df.columns)}):")
for i, col in enumerate(df.columns, 1):
    print(f"  {i}. {col}")

print("\n" + "="*80)
print("UNIQUE VALUES PER COLUMN")
print("="*80)

for col in df.columns:
    print(f"\n{col}:")
    unique_vals = df[col].unique()
    if len(unique_vals) <= 15:
        print(f"  All unique values ({len(unique_vals)}):")
        for val in unique_vals:
            print(f"    - {val}")
    else:
        print(f"  First 15 unique values (of {len(unique_vals)}):")
        for val in unique_vals[:15]:
            print(f"    - {val}")

print("\n" + "="*80)
print("SAMPLE ROWS (first 10, all columns)")
print("="*80)
print(df.head(10).to_string())
