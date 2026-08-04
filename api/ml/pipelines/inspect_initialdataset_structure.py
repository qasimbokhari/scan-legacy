"""
Inspect the exact structure of InitialDataset sheets for MeOx and SAPNet.
"""

import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent.parent
RAW_DATA_DIR = BASE_DIR / "data" / "raw" / "zenodo_toxicity"

print("="*80)
print("INSPECT INITIALDATASET SHEET STRUCTURE")
print("="*80)

# MeOx file
meox_file = RAW_DATA_DIR / "05_MODEL_MeOxDMEM_tox_DatasetReport.xlsx"
print(f"\nMeOx file: {meox_file.name}")

# Read without header to see raw structure
df_raw = pd.read_excel(meox_file, sheet_name="InitialDataset", header=None)
print(f"\nRaw rows: {len(df_raw)}")
print("\nRow 0 (metadata):")
print(df_raw.iloc[0].to_string())
print("\nRow 1 (header candidate):")
print(df_raw.iloc[1].to_string())
print("\nRow 2 (first data row):")
print(df_raw.iloc[2].to_string())
print("\nRow 3 (second data row):")
print(df_raw.iloc[3].to_string())

# SAPNet file
sapnet_file = RAW_DATA_DIR / "02_MODEL_SAPNet_EC50_DatasetReport.xlsx"
print(f"\n\nSAPNet file: {sapnet_file.name}")

# Read without header to see raw structure
df_raw = pd.read_excel(sapnet_file, sheet_name="InitialDataset", header=None)
print(f"\nRaw rows: {len(df_raw)}")
print("\nRow 0 (metadata):")
print(df_raw.iloc[0].to_string())
print("\nRow 1 (header candidate):")
print(df_raw.iloc[1].to_string())
print("\nRow 2 (first data row):")
print(df_raw.iloc[2].to_string())
print("\nRow 3 (second data row):")
print(df_raw.iloc[3].to_string())

print("\n" + "="*80)
