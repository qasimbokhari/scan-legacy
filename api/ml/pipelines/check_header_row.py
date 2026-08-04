"""
Check exact header row index for MeOx and SAPNet files.
"""

import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent.parent
RAW_DATA_DIR = BASE_DIR / "data" / "raw" / "zenodo_toxicity"

print("="*80)
print("CHECK HEADER ROW INDEX")
print("="*80)

# MeOx file
meox_file = RAW_DATA_DIR / "05_MODEL_MeOxDMEM_tox_DatasetReport.xlsx"
print(f"\nMeOx file: {meox_file.name}")
print("\nRow 0 (metadata):")
df_row0 = pd.read_excel(meox_file, sheet_name="InitialDataset", header=None, nrows=1)
print(df_row0.to_string())

print("\nRow 1 (potential header):")
df_row1 = pd.read_excel(meox_file, sheet_name="InitialDataset", header=None, skiprows=1, nrows=1)
print(df_row1.to_string())

print("\nRow 2 (data if header=1):")
df_data = pd.read_excel(meox_file, sheet_name="InitialDataset", header=1, nrows=3)
print(df_data.to_string())

# SAPNet file
sapnet_file = RAW_DATA_DIR / "02_MODEL_SAPNet_EC50_DatasetReport.xlsx"
print(f"\n\nSAPNet file: {sapnet_file.name}")
print("\nRow 0 (metadata):")
df_row0 = pd.read_excel(sapnet_file, sheet_name="InitialDataset", header=None, nrows=1)
print(df_row0.to_string())

print("\nRow 1 (potential header):")
df_row1 = pd.read_excel(sapnet_file, sheet_name="InitialDataset", header=None, skiprows=1, nrows=1)
print(df_row1.to_string())

print("\nRow 2 (data if header=1):")
df_data = pd.read_excel(sapnet_file, sheet_name="InitialDataset", header=1, nrows=3)
print(df_data.to_string())

print("\n" + "="*80)
