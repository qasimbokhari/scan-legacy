"""
Preprocessing script for NanoReg and NanoReg2 ENANOMAPPER MySQL dumps.
Parses nanoreg_nrfiles.sql.xz and nanoreg2.sql.xz, cleans and maps material properties,
toxicity endpoints, and complex ENANOMAPPER metrics.
"""

import lzma
import re
import pandas as pd
import numpy as np
from pathlib import Path
import sys
import codecs
import json

# Set UTF-8 encoding for output
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
RAW_DATA_DIR = BASE_DIR / "data" / "raw" / "other"
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"
PROCESSED_DATA_DIR.mkdir(exist_ok=True)

NRFILES_PATH = RAW_DATA_DIR / "nanoreg_nrfiles.sql.xz"
NR2_PATH = RAW_DATA_DIR / "nanoreg2.sql.xz"
OUTPUT_STANDARD = PROCESSED_DATA_DIR / "nanoreg_clean.csv"
OUTPUT_ISOLATED = PROCESSED_DATA_DIR / "nanoreg_isolated_clean.csv"


def clean_numeric(val):
    if val is None or pd.isna(val):
        return None
    try:
        f = float(val)
        if np.isnan(f) or np.isinf(f):
            return None
        return f
    except (ValueError, TypeError):
        return None


def parse_dump(filepath):
    """Parse substance, substance_protocolapplication, and substance_experiment from dump."""
    substances = {}  # uuid -> {name, publicname, jrc_id, format}
    proto_apps = {}  # doc_uuid -> {reference, guidance, params, reliability}
    experiments = [] # list of dicts
    
    with lzma.open(filepath, 'rt', encoding='utf-8', errors='replace') as f:
        for line in f:
            line_str = line.strip()
            
            # 1. Parse substance table
            if 'INSERT INTO `substance` VALUES' in line_str:
                # Format: (id, prefix, uuid, documentType, format, name, publicname, content, ...)
                # Match tuples
                matches = re.findall(r"\(\d+,'([^']+)','([^']+)',(?:'[^']*'|NULL),(?:'[^']*'|NULL),'([^']+)','([^']+)'", line_str)
                for prefix, uuid, name, publicname in matches:
                    substances[uuid] = {
                        'name': name,
                        'publicname': publicname,
                        'prefix': prefix
                    }
                    
            # 2. Parse substance_protocolapplication table
            if 'INSERT INTO `substance_protocolapplication` VALUES' in line_str:
                # Format: (doc_prefix, doc_uuid, topcategory, endpointcategory, endpoint, guidance, sub_prefix, sub_uuid, params, interp, criteria, reference, ref_year, ref_owner, ...)
                matches = re.findall(r"\('([^']+)','([^']+)','([^']+)','([^']+)','([^']*)','([^']*)','([^']+)','([^']+)','([^']*)',[^,]*?,[^,]*?,'([^']*)'", line_str)
                for doc_p, doc_uuid, top, ep_cat, ep, guidance, sub_p, sub_uuid, params, ref in matches:
                    proto_apps[doc_uuid] = {
                        'guidance': guidance,
                        'params': params,
                        'reference': ref,
                        'substance_uuid': sub_uuid
                    }
                    
            # 3. Parse substance_experiment table
            if 'INSERT INTO `substance_experiment` VALUES' in line_str:
                # Format: (idresult, doc_prefix, doc_uuid, topcategory, endpointcategory, endpointhash, endpoint, conditions, unit, loQual, loValue, upQual, upValue, textValue, errQual, err, sub_prefix, sub_uuid, resulttype, resultgroup)
                # Regex for fields
                # Simple extraction of string tuples
                # Splitting values logic
                values_part = line_str[line_str.find('VALUES') + 6:].rstrip(';')
                in_str = False
                escaped = False
                quote_char = None
                depth = 0
                current_val = []
                
                for c in values_part:
                    if escaped:
                        escaped = False
                    elif c == '\\':
                        escaped = True
                    elif in_str:
                        if c == quote_char:
                            in_str = False
                    elif c in ("'", '"', '`'):
                        in_str = True
                        quote_char = c
                    elif c == '(':
                        depth += 1
                        if depth == 1:
                            current_val = []
                    elif c == ')':
                        depth -= 1
                        if depth == 0:
                            # Process tuple
                            row_str = ''.join(current_val)
                            # Parse comma-separated items considering quotes
                            # Simplest: use CSV parser on line
                            import csv
                            try:
                                r = next(csv.reader([row_str], quotechar="'", escapechar='\\'))
                                if len(r) >= 18:
                                    doc_uuid = r[2]
                                    topcat = r[3]
                                    epcat = r[4]
                                    ep = r[6]
                                    unit = r[8]
                                    lo_val = clean_numeric(r[10])
                                    up_val = clean_numeric(r[12])
                                    text_val = r[13] if r[13] != 'NULL' else None
                                    sub_uuid = r[17]
                                    
                                    val = lo_val if lo_val is not None else up_val
                                    
                                    experiments.append({
                                        'doc_uuid': doc_uuid,
                                        'substance_uuid': sub_uuid,
                                        'topcategory': topcat,
                                        'endpointcategory': epcat,
                                        'endpoint': ep,
                                        'unit': unit,
                                        'val': val,
                                        'text_value': text_val
                                    })
                            except Exception:
                                pass
                    if depth > 0:
                        current_val.append(c)
                        
    return substances, proto_apps, experiments


def derive_material_type(name):
    name_l = (name or '').lower()
    if 'tio2' in name_l or 'titanium' in name_l:
        return 'Titanium Dioxide'
    elif 'zno' in name_l or 'zinc' in name_l:
        return 'Zinc Oxide'
    elif 'silica' in name_l or 'sio2' in name_l:
        return 'Silicon Dioxide'
    elif 'mwcnt' in name_l or 'cnt' in name_l or 'nanotube' in name_l:
        return 'Multi-Walled Carbon Nanotube'
    elif 'ag' in name_l or 'silver' in name_l:
        return 'Silver'
    elif 'au' in name_l or 'gold' in name_l:
        return 'Gold'
    elif 'ceo2' in name_l or 'cerium' in name_l:
        return 'Cerium Dioxide'
    elif 'baso4' in name_l or 'barium' in name_l:
        return 'Barium Sulfate'
    elif 'al2o3' in name_l or 'alumina' in name_l:
        return 'Aluminum Oxide'
    else:
        return 'Nanomaterial'


def derive_core_size(name):
    m = re.search(r'(\d+(?:\.\d+)?)\s*nm', name or '', re.IGNORECASE)
    if m:
        return float(m.group(1))
    return None


def preprocess_nanoreg():
    print("="*80)
    print("NANOREG / NANOREG2 DATA PREPROCESSING")
    print("="*80)
    
    print("\n1. Parsing nanoreg_nrfiles.sql.xz...")
    subs1, proto1, exp1 = parse_dump(NRFILES_PATH)
    print(f"   Substances: {len(subs1)}, Protocol apps: {len(proto1)}, Experiments: {len(exp1)}")
    
    print("\n2. Parsing nanoreg2.sql.xz...")
    subs2, proto2, exp2 = parse_dump(NR2_PATH)
    print(f"   Substances: {len(subs2)}, Protocol apps: {len(proto2)}, Experiments: {len(exp2)}")
    
    # Merge substances and protocol apps
    subs = {**subs2, **subs1}
    proto = {**proto2, **proto1}
    all_exp = exp1 + exp2
    
    print(f"\n3. Total experiments to process: {len(all_exp)}")
    
    standard_rows = []
    isolated_rows = []
    
    for exp in all_exp:
        sub_info = subs.get(exp['substance_uuid'], {})
        sub_name = sub_info.get('name') or sub_info.get('publicname') or 'Unknown Nanomaterial'
        proto_info = proto.get(exp['doc_uuid'], {})
        ref = proto_info.get('reference')
        
        # Determine source_type
        is_lit = False
        if ref and len(ref) > 5 and ('http' in ref.lower() or 'doi' in ref.lower() or '10.' in ref or '20' in ref or '19' in ref):
            is_lit = True
        source_type = 'literature_mined' if is_lit else 'nanoreg_mined'
        
        material_type = derive_material_type(sub_name)
        core_size = derive_core_size(sub_name)
        
        ep = (exp['endpoint'] or '').upper()
        topcat = exp['topcategory']
        epcat = exp['endpointcategory']
        val = exp['val']
        unit = exp['unit']
        
        # Map to IC50 / EC50 toxicity record if clean numeric toxicity value
        if ('IC50' in ep or 'EC50' in ep or epcat in ('EC_FISHTOX_SECTION', 'EC_DAPHNIATOX_SECTION', 'EC_ALGAETOX_SECTION')) and val is not None and val > 0:
            ec50_val = val
            pec50_val = -np.log10(val * 1e-6) if val < 1e3 else None  # approx if in M/uM
            
            # Extract cell line or target organism
            cell_line = proto_info.get('guidance') or epcat
            
            standard_rows.append({
                'name': sub_name,
                'material_type': material_type,
                'core_size_nm': core_size,
                'zeta_potential_mv': None,
                'surface_area_m2g': None,
                'coating': None,
                'source_type': source_type,
                'doi': ref if is_lit else None,
                'ic50': val if 'IC50' in ep else None,
                'ec50': ec50_val if 'EC50' in ep or 'EC_' in epcat else None,
                'pec50': pec50_val,
                'cell_line': cell_line,
                'exposure_time_h': None
            })
            
        elif epcat == 'ZETA_POTENTIAL_SECTION' and val is not None:
            standard_rows.append({
                'name': sub_name,
                'material_type': material_type,
                'core_size_nm': core_size,
                'zeta_potential_mv': val,
                'surface_area_m2g': None,
                'coating': None,
                'source_type': source_type,
                'doi': ref if is_lit else None,
                'ic50': None, 'ec50': None, 'pec50': None, 'cell_line': None, 'exposure_time_h': None
            })
            
        elif epcat == 'SPECIFIC_SURFACE_AREA_SECTION' and val is not None:
            standard_rows.append({
                'name': sub_name,
                'material_type': material_type,
                'core_size_nm': core_size,
                'zeta_potential_mv': None,
                'surface_area_m2g': val,
                'coating': None,
                'source_type': source_type,
                'doi': ref if is_lit else None,
                'ic50': None, 'ec50': None, 'pec50': None, 'cell_line': None, 'exposure_time_h': None
            })
            
        else:
            # Send to isolated table
            isolated_rows.append({
                'substance_name': sub_name,
                'jrc_id': sub_info.get('publicname'),
                'topcategory': topcat,
                'endpointcategory': epcat,
                'endpoint': exp['endpoint'],
                'value_numeric': val,
                'unit': unit,
                'text_value': exp['text_value'],
                'reference': ref,
                'source_type': source_type,
                'provenance_note': f"Ingested from ENANOMAPPER dump ({NRFILES_PATH.name}/{NR2_PATH.name})."
            })
            
    # Save processed DataFrames
    df_std = pd.DataFrame(standard_rows)
    df_iso = pd.DataFrame(isolated_rows)
    
    # Deduplicate standard rows
    df_std = df_std.drop_duplicates()
    df_iso = df_iso.drop_duplicates()
    
    df_std.to_csv(OUTPUT_STANDARD, index=False)
    df_iso.to_csv(OUTPUT_ISOLATED, index=False)
    
    print(f"\nSaved standard records to: {OUTPUT_STANDARD} ({len(df_std)} rows)")
    print(f"Saved isolated records to: {OUTPUT_ISOLATED} ({len(df_iso)} rows)")
    print("\n" + "="*80)
    print("PREPROCESSING COMPLETE")
    print("="*80)


if __name__ == '__main__':
    preprocess_nanoreg()
