"""
Spot-check physical measurements against source spreadsheet cells.
Verify that surface_area_m2g and core_size_nm contain real physical measurements,
not descriptor values.
"""

import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent.parent
RAW_DATA_DIR = BASE_DIR / "data" / "raw" / "zenodo_toxicity"

print("="*80)
print("SPOT-CHECK PHYSICAL MEASUREMENTS AGAINST SOURCE SPREADSHEET")
print("="*80)

# MeOx file
meox_file = RAW_DATA_DIR / "05_MODEL_MeOxDMEM_tox_DatasetReport.xlsx"
print(f"\nMeOx file: {meox_file.name}")

# Read from InitialDataset sheet without header to access by column index
df_meox = pd.read_excel(meox_file, sheet_name="InitialDataset", header=None)

# Row 0 is metadata, row 1 is header, data starts at row 2
# Skip row 0 and row 1, start from row 2
df_meox = df_meox.iloc[2:].reset_index(drop=True)

print("\nMeOx Spot-Check (first 5 rows):")
print("Row | Name | core_size_nm (col 26) | zeta_potential_mv (col 14) | surface_area_m2g (col 10)")
print("-" * 100)

for idx in range(min(5, len(df_meox))):
    row = df_meox.iloc[idx]
    name = row.iloc[2] if len(row) > 2 else None
    core_size = row.iloc[26] if len(row) > 26 else None
    zeta = row.iloc[14] if len(row) > 14 else None
    surface_area = row.iloc[10] if len(row) > 10 else None
    print(f"{idx+1} | {name} | {core_size} | {zeta} | {surface_area}")

# SAPNet file
sapnet_file = RAW_DATA_DIR / "02_MODEL_SAPNet_EC50_DatasetReport.xlsx"
print(f"\n\nSAPNet file: {sapnet_file.name}")

# Read from InitialDataset sheet without header to access by column index
df_sapnet = pd.read_excel(sapnet_file, sheet_name="InitialDataset", header=None)

# Row 0 is metadata, row 1 is header, data starts at row 2
# Skip row 0 and row 1, start from row 2
df_sapnet = df_sapnet.iloc[2:].reset_index(drop=True)

print("\nSAPNet Spot-Check (first 5 rows):")
print("Row | Name | surface_area_m2g (col 21 - BETarea)")
print("-" * 80)

for idx in range(min(5, len(df_sapnet))):
    row = df_sapnet.iloc[idx]
    name = row.iloc[1] if len(row) > 1 else None
    surface_area = row.iloc[21] if len(row) > 21 else None
    print(f"{idx+1} | {name} | {surface_area}")

print("\n" + "="*80)
print("VERIFICATION COMPLETE")
print("="*80)
