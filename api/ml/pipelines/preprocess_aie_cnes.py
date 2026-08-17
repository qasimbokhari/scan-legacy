"""
Preprocessing script for AIE_CNES_Dataset.csv.
Cleans and validates the graphene/CNT sensor data for ingestion.
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

INPUT_FILE = "AIE_CNES_Dataset.csv"
OUTPUT_FILE = "aie_cnes_clean.csv"


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


def preprocess_aie_cnes():
    """Preprocess AIE_CNES dataset."""
    print("="*80)
    print("AIE-CNES DATA PREPROCESSING")
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
    
    # Basic validation - check for realistic ranges
    print(f"\nRange validation:")
    print(f"  Graphene_Ratio: {df['Graphene_Ratio (%)'].min():.2f}% - {df['Graphene_Ratio (%)'].max():.2f}%")
    print(f"  CNT_Ratio: {df['CNT_Ratio (%)'].min():.2f}% - {df['CNT_Ratio (%)'].max():.2f}%")
    print(f"  Temperature: {df['Temperature (C)'].min():.2f}°C - {df['Temperature (C)'].max():.2f}°C")
    print(f"  pH: {df['pH_Level'].min():.2f} - {df['pH_Level'].max():.2f}")
    
    # Check composition sums (graphene + CNT should roughly equal 100%)
    df['composition_sum'] = df['Graphene_Ratio (%)'] + df['CNT_Ratio (%)']
    print(f"  Composition sum (Graphene + CNT): {df['composition_sum'].min():.2f}% - {df['composition_sum'].max():.2f}%")
    
    # Remove the temporary column
    df = df.drop(columns=['composition_sum'])
    
    # Rename columns to match database schema
    column_mapping = {
        'Graphene_Ratio (%)': 'graphene_ratio_pct',
        'CNT_Ratio (%)': 'cnt_ratio_pct',
        'Electrode_Surface_Area (cm2)': 'electrode_surface_area_cm2',
        'Conductivity (S/m)': 'conductivity_s_m',
        'pH_Level': 'ph_level',
        'Temperature (C)': 'temperature_c',
        'Potential (V)': 'potential_v',
        'Current (uA)': 'current_ua',
        'Scan_Rate (mV/s)': 'scan_rate_mv_s',
        'Pulse_Amplitude (mV)': 'pulse_amplitude_mv',
        'Peak_Current (uA)': 'peak_current_ua',
        'Peak_Potential (V)': 'peak_potential_v',
        'SNR': 'snr',
        'Interference_Level (%)': 'interference_level_pct',
        'Pollutant_Type': 'pollutant_type',
        'Pollutant_Concentration (ppm)': 'pollutant_concentration_ppm',
        'Detection_Status': 'detection_status',
    }
    
    df_clean = df.rename(columns=column_mapping)
    
    # Convert detection status to integer
    df_clean['detection_status'] = df_clean['detection_status'].astype(int)
    
    # Add provenance fields
    df_clean['source_type'] = 'aie_cnes_unverified'
    df_clean['provenance_note'] = (
        "Provenance unverified. No cited source paper or laboratory. "
        "Structural indicators suggest possible synthetic origin: "
        "perfect data quality (0 missing values), tightly bounded numeric ranges, "
        "binary classification labels. Use only as plausibility-range reference, "
        "not as literature-grade or experimentally validated data."
    )
    
    # Save processed data
    output_path = PROCESSED_DATA_DIR / OUTPUT_FILE
    df_clean.to_csv(output_path, index=False)
    
    print(f"\nProcessed data saved to: {output_path}")
    print(f"Final row count: {len(df_clean)}")
    print(f"Final columns: {list(df_clean.columns)}")
    
    print("\n" + "="*80)
    print("PREPROCESSING COMPLETE")
    print("="*80)


if __name__ == "__main__":
    preprocess_aie_cnes()
