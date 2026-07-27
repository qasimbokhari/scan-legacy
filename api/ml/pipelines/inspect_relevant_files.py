"""
Targeted inspection of relevant toxicity/material data files.
Focuses on files that contain material properties and toxicity outcomes.
"""

import os
import pandas as pd
from pathlib import Path
import sys

# Set UTF-8 encoding for output
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

# Define paths
BASE_DIR = Path(__file__).parent.parent.parent.parent
RAW_DATA_DIR = BASE_DIR / "data" / "raw"

# Files to inspect (based on initial scan)
RELEVANT_FILES = {
    "nanopharos": [
        "MeOx_EC50_full.csv",
        "Metal_Oxide_cytotoxicity.xlsx",
        "Metal_oxide_facet_cytotoxicity.xlsx",
        "NanoPharos_HepaRG.xlsx",
        "ICNP_CellViability.csv",
        "Copper_nanoparticles_toxicity.csv",
        "Photo-induced_cytotoxicity_data.csv",
        "dataset_ecotoxicity.xlsx",
    ],
    "zenodo_toxicity": [
        "02_MODEL_SAPNet_EC50_DatasetReport.xlsx",
        "04_MODEL_Hydro-diameter_MeOx_DMEM_ Dataset Report.xlsx",
        "05_MODEL_MeOxDMEM_tox_DatasetReport.xlsx",
    ],
    "zenodo_nanomaterials": [
        "Supplementary-materials-Trinh-and-Kim-Nanomaterials-2021.xlsx",
    ],
    "cananolab": [
        "GC File Manifest 2026-05-24 10-59-23.csv",
    ],
}


def inspect_file(file_path):
    """Inspect a single file and return metadata."""
    try:
        if file_path.suffix in [".csv", ".CSV"]:
            df = pd.read_csv(file_path)
        elif file_path.suffix in [".xlsx", ".xls"]:
            df = pd.read_excel(file_path)
        else:
            return {
                "error": f"Unsupported file type: {file_path.suffix}",
                "columns": [],
                "row_count": 0,
                "sample": []
            }
        
        return {
            "columns": list(df.columns),
            "row_count": len(df),
            "sample": df.head(5).to_dict(orient="records") if len(df) > 0 else []
        }
    except Exception as e:
        return {
            "error": str(e),
            "columns": [],
            "row_count": 0,
            "sample": []
        }


def main():
    """Run inspection on relevant files only."""
    print("="*80)
    print("TARGETED DATASET INSPECTION - RELEVANT FILES ONLY")
    print("="*80)
    
    for dataset_name, file_list in RELEVANT_FILES.items():
        dataset_path = RAW_DATA_DIR / dataset_name
        print(f"\n{'='*80}")
        print(f"DATASET: {dataset_name}")
        print(f"{'='*80}\n")
        
        for filename in file_list:
            file_path = dataset_path / filename
            print(f"\n{'-'*80}")
            print(f"FILE: {filename}")
            print(f"Path: {file_path}")
            print(f"{'-'*80}")
            
            if not file_path.exists():
                print(f"ERROR: File does not exist")
                continue
            
            result = inspect_file(file_path)
            
            if "error" in result:
                print(f"ERROR: {result['error']}")
            else:
                print(f"\nColumns ({len(result['columns'])}):")
                for i, col in enumerate(result['columns'], 1):
                    print(f"  {i}. {col}")
                
                print(f"\nRow count: {result['row_count']}")
                
                if result['sample']:
                    print(f"\nSample rows (first 5):")
                    for i, row in enumerate(result['sample'], 1):
                        print(f"  Row {i}:")
                        for key, value in row.items():
                            print(f"    {key}: {value}")
                else:
                    print("\nNo sample rows available (empty file)")
    
    print(f"\n{'='*80}")
    print("INSPECTION COMPLETE")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
