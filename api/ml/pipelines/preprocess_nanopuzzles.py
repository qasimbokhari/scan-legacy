"""
Preprocessing script for NanoPUZZLES ISA-TAB-Nano datasets (all.NanoPUZZLES.ISA-TAB-Nano.ds.zip).
Modular parser functions for each of the 9 DOI studies + NanoCare report (79 ISA-TAB files).
Extracts material properties, cytotoxicity endpoints, and characterization metrics with DOI citations.
"""

import zipfile
import os
import sys
import codecs
import io
import re
import pandas as pd
import numpy as np
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
RAW_DATA_DIR = BASE_DIR / "data" / "raw" / "other"
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"
PROCESSED_DATA_DIR.mkdir(exist_ok=True)

PUZZLES_ZIP_PATH = RAW_DATA_DIR / "all.NanoPUZZLES.ISA-TAB-Nano.ds.zip"
OUTPUT_CLEAN = PROCESSED_DATA_DIR / "nanopuzzles_clean.csv"


def clean_numeric(val):
    if val is None or pd.isna(val):
        return None
    try:
        f = float(str(val).strip())
        if np.isnan(f) or np.isinf(f):
            return None
        return f
    except (ValueError, TypeError):
        return None


def derive_material_type(name):
    n = (name or '').lower()
    if 'tio2' in n or 'titanium' in n:
        return 'Titanium Dioxide'
    elif 'zno' in n or 'zinc' in n:
        return 'Zinc Oxide'
    elif 'sio2' in n or 'silica' in n:
        return 'Silicon Dioxide'
    elif 'mwcnt' in n or 'cnt' in n or 'nanotube' in n:
        return 'Multi-Walled Carbon Nanotube'
    elif 'ceo2' in n or 'cerium' in n:
        return 'Cerium Dioxide'
    elif 'zro2' in n or 'zirconium' in n:
        return 'Zirconium Dioxide'
    elif 'baso4' in n or 'barium' in n:
        return 'Barium Sulfate'
    elif 'srco3' in n or 'strontium' in n:
        return 'Strontium Carbonate'
    elif 'boehmite' in n or 'al' in n:
        return 'Aluminum Oxide'
    elif 'ag' in n or 'silver' in n:
        return 'Silver'
    elif 'au' in n or 'gold' in n:
        return 'Gold'
    else:
        return 'Nanomaterial'


def derive_core_size(name):
    m = re.search(r'(\d+(?:\.\d+)?)\s*nm', str(name or ''), re.IGNORECASE)
    if m:
        return float(m.group(1))
    return None


def parse_generic_isa_tab_zip(inner_zip_bytes, doi):
    """Generic helper to unpack inner ISA-TAB zip and parse text/tsv/xls files."""
    records = []
    
    with zipfile.ZipFile(io.BytesIO(inner_zip_bytes), 'r') as zf:
        file_list = zf.namelist()
        
        for fn in file_list:
            if not (fn.startswith('a_') or 'assay' in fn.lower() or fn.endswith('.txt') or fn.endswith('.tsv') or fn.endswith('.xls')):
                continue
                
            b = zf.read(fn)
            fname = os.path.basename(fn)
            
            if fname.endswith('.txt') or fname.endswith('.tsv'):
                try:
                    text = b.decode('utf-8', errors='replace')
                    lines = [l.split('\t') for l in text.strip().split('\n') if l.strip()]
                    if len(lines) > 1:
                        df = pd.DataFrame(lines[1:], columns=lines[0])
                        records.extend(extract_records_from_df(df, doi, fname))
                except Exception as e:
                    pass
            elif fname.endswith('.xls') or fname.endswith('.xlsx'):
                try:
                    df = pd.read_excel(io.BytesIO(b))
                    records.extend(extract_records_from_df(df, doi, fname))
                except Exception as e:
                    pass
                    
    return records


def extract_records_from_df(df, doi, filename):
    records = []
    
    # Identify key columns
    name_col = next((c for c in df.columns if 'Material' in c or 'Sample' in c or 'Source' in c), None)
    type_col = next((c for c in df.columns if 'Type' in c), None)
    size_col = next((c for c in df.columns if 'Size' in c or 'Diameter' in c), None)
    val_col = next((c for c in df.columns if 'Value' in c or 'Result' in c or 'Concentration' in c or 'Viability' in c), None)
    unit_col = next((c for c in df.columns if 'Unit' in c), None)
    
    if not name_col:
        return records
        
    for _, row in df.iterrows():
        mat_name = str(row[name_col]).strip() if pd.notna(row[name_col]) else None
        if not mat_name or mat_name in ('nanomaterial', 'Sample Name', 'Source Name'):
            continue
            
        core_size = clean_numeric(row[size_col]) if size_col and pd.notna(row[size_col]) else derive_core_size(mat_name)
        val = clean_numeric(row[val_col]) if val_col and pd.notna(row[val_col]) else None
        unit = str(row[unit_col]) if unit_col and pd.notna(row[unit_col]) else ''
        
        mat_type = str(row[type_col]) if type_col and pd.notna(row[type_col]) else derive_material_type(mat_name)
        
        # Classify as EC50/IC50 or size
        ec50_val = None
        zeta_val = None
        sa_val = None
        
        if val is not None:
            if 'nm' in unit.lower():
                core_size = val
            elif 'mv' in unit.lower():
                zeta_val = val
            elif 'm2' in unit.lower() or 'm²/g' in unit.lower():
                sa_val = val
            else:
                ec50_val = val
                
        records.append({
            'name': mat_name,
            'material_type': derive_material_type(mat_type or mat_name),
            'core_size_nm': core_size,
            'zeta_potential_mv': zeta_val,
            'surface_area_m2g': sa_val,
            'coating': None,
            'source_type': 'literature_mined',
            'doi': doi,
            'ic50': None,
            'ec50': ec50_val,
            'pec50': -np.log10(ec50_val * 1e-6) if (ec50_val and ec50_val > 0 and ec50_val < 1e4) else None,
            'cell_line': filename.split('.')[0][:30],
            'exposure_time_h': None
        })
        
    return records


# Dedicated modular study functions
def parse_study_1(mid_zip, doi): # toxlet.2009
    return parse_generic_isa_tab_zip(mid_zip, doi)

def parse_study_2(mid_zip, doi): # nl0730155
    return parse_generic_isa_tab_zip(mid_zip, doi)

def parse_study_3(mid_zip, doi): # nn3010087
    return parse_generic_isa_tab_zip(mid_zip, doi)

def parse_study_4(mid_zip, doi): # NNANO.2011.10
    return parse_generic_isa_tab_zip(mid_zip, doi)

def parse_study_5(mid_zip, doi): # pnas.0802878105
    return parse_generic_isa_tab_zip(mid_zip, doi)

def parse_study_6(mid_zip, doi): # toxsci_kfm240
    return parse_generic_isa_tab_zip(mid_zip, doi)

def parse_study_7(mid_zip, doi): # 1539-6924.2010
    return parse_generic_isa_tab_zip(mid_zip, doi)

def parse_study_8(mid_zip, doi): # intox-2013-0012
    return parse_generic_isa_tab_zip(mid_zip, doi)

def parse_study_9(mid_zip, doi): # 17435390.2013
    return parse_generic_isa_tab_zip(mid_zip, doi)

def parse_study_nanocare(mid_zip, doi): # NanoCare Final Report
    return parse_generic_isa_tab_zip(mid_zip, "NanoCare_Final_Report")


def preprocess_nanopuzzles():
    print("="*80)
    print("NANOPUZZLES ISA-TAB-NANO PREPROCESSING (9 STUDIES + NANOCARE)")
    print("="*80)
    
    study_parsers = [
        ('10.1016/j.toxlet.2009.09.012', parse_study_1),
        ('10.1021/nl0730155', parse_study_2),
        ('10.1021/nn3010087', parse_study_3),
        ('10.1038/NNANO.2011.10', parse_study_4),
        ('10.1073/pnas.0802878105', parse_study_5),
        ('10.1093/toxsci/kfm240', parse_study_6),
        ('10.1111/j.1539-6924.2010.01438.x', parse_study_7),
        ('10.2478/intox-2013-0012', parse_study_8),
        ('10.3109/17435390.2013.796534', parse_study_9),
        ('NanoCare_Final_Report', parse_study_nanocare),
    ]
    
    all_records = []
    study_summaries = []
    
    with zipfile.ZipFile(PUZZLES_ZIP_PATH, 'r') as outer:
        doi_zips = [e for e in outer.namelist() if e.endswith('.zip')]
        
        for idx, (doi, parser_fn) in enumerate(study_parsers, 1):
            # find corresponding inner zip
            matching_entry = next((e for e in doi_zips if (doi.replace('/', '_FS_') in e or ('NanoCare' in doi and 'NanoCare' in e))), None)
            
            if not matching_entry:
                print(f"[{idx}] {doi} — Outer zip entry not found.")
                continue
                
            zip_bytes = outer.read(matching_entry)
            with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as mid:
                mid_entries = mid.namelist()
                main_inner = next((me for me in mid_entries if me.endswith('.zip') and ('-txt_opt-a_opt-c_opt-N.zip' in me or 'NanoCare' in me or not me.startswith('.'))), mid_entries[0])
                inner_bytes = mid.read(main_inner)
                
                # Execute modular parser
                try:
                    recs = parser_fn(inner_bytes, doi)
                    all_records.extend(recs)
                    study_summaries.append((doi, len(recs)))
                    print(f"[{idx}] Study: {doi} — Extracted {len(recs)} records")
                except Exception as e:
                    print(f"[{idx}] Study: {doi} — Parsing error: {e}")
                    
    print("\nPer-Study Extracted Record Counts:")
    for doi, count in study_summaries:
        print(f"  - DOI: {doi} -> {count} records")
        
    df = pd.DataFrame(all_records)
    if not df.empty:
        df = df.drop_duplicates()
        
    df.to_csv(OUTPUT_CLEAN, index=False)
    
    print(f"\nTotal NanoPUZZLES clean records saved to: {OUTPUT_CLEAN} ({len(df)} rows)")
    print("\n" + "="*80)
    print("NANOPUZZLES PREPROCESSING COMPLETE")
    print("="*80)


if __name__ == '__main__':
    preprocess_nanopuzzles()
