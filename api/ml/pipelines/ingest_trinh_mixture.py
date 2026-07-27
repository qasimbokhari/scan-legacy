"""
Trinh Mixture Dataset — Reference File Confirmation Script.

WHY THIS SCRIPT DOES NOT INSERT INTO THE DATABASE
==================================================
The Trinh et al. (2021) dataset ("Supplementary-materials-Trinh-and-Kim-Nanomaterials-2021.xlsx")
is a **literature-review metadata catalog**, not experimental outcome data.

Specifically, this dataset contains:
  - Citations to published studies (Article column)
  - Study methodology labels (in vivo / in vitro)
  - Test organism names (not mammalian cell lines)
  - Qualitative toxicology category labels ("toxic", "non-toxic")

It does NOT contain:
  - Measured IC50 or EC50 values
  - Measured EC50 values
  - Material property measurements (no core_size_nm, zeta_potential_mv, or surface_area_m2g)

Ingesting this data as ToxicityRecord rows would create records with ALL numeric fields
NULL (ic50, ec50, pec50), populating only a classification label derived from a
literature survey — not from a primary experiment. This is not suitable as toxicity
outcome data for training or querying in SCAN.

WHAT THIS SCRIPT DOES
=====================
This script simply confirms that data/processed/trinh_clean.csv exists as a cleaned
reference file (citations, study metadata) and prints a summary for audit purposes.
No database rows are inserted or modified.

If you need Trinh data for literature-survey analysis, read trinh_clean.csv directly.
"""

import sys
import pandas as pd
from pathlib import Path

# Set UTF-8 encoding for output on Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

# Paths
BASE_DIR = Path(__file__).parent.parent.parent.parent
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"
TRINH_CLEAN_CSV = PROCESSED_DATA_DIR / "trinh_clean.csv"


def main():
    """Confirm trinh_clean.csv exists as a reference file. No DB insertion."""
    print("=" * 80)
    print("TRINH MIXTURE DATASET — REFERENCE FILE CONFIRMATION")
    print("=" * 80)
    print()
    print("NOTE: This dataset is a literature-review metadata catalog.")
    print("      It is NOT ingested into material_records or toxicity_records.")
    print("      See module docstring for full rationale.")
    print()

    # Confirm the processed CSV exists
    if not TRINH_CLEAN_CSV.exists():
        print(f"WARNING: Reference file not found: {TRINH_CLEAN_CSV}")
        print("  The file should exist as a cleaned reference catalog.")
        print("  It was generated from the original Trinh Excel supplementary file.")
        print("  No action needed — this file is for reference only, not DB ingestion.")
        return

    # Load and summarise
    df = pd.read_csv(TRINH_CLEAN_CSV)
    print(f"✓ Reference file found: {TRINH_CLEAN_CSV}")
    print(f"  Rows (literature survey entries): {len(df)}")
    print(f"  Columns: {list(df.columns)}")
    print()

    # Show classification breakdown from the literature survey labels
    if 'raw_classification' in df.columns:
        breakdown = df['raw_classification'].value_counts(dropna=False)
        print("Literature survey classification labels (NOT experimental outcomes):")
        for label, count in breakdown.items():
            print(f"  {label!r}: {count}")
        print()

    # Confirm no material property data is present
    prop_cols = ['core_size_nm', 'zeta_potential_mv', 'surface_area_m2g']
    missing_props = [c for c in prop_cols if c not in df.columns or df[c].isna().all()]
    if missing_props:
        print(f"✓ Confirmed: No material property values in reference file")
        print(f"  Missing/empty columns: {missing_props}")
    print()

    print("No database rows were inserted or modified.")
    print("=" * 80)
    print("REFERENCE CHECK COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
