"""
Preprocessing script for nanowiki RDF (nanowiki.cczero.6.rdf.gz).
Parses RDF/XML, extracts nanomaterial properties and cytotoxicity endpoints,
and performs deep deduplication against existing DB records (e.g. MeOx Puzyn 2011 dataset).
"""

import gzip
import xml.etree.ElementTree as ET
import pandas as pd
import numpy as np
from pathlib import Path
import sys
import codecs
import re

# Set UTF-8 encoding for output
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
RAW_DATA_DIR = BASE_DIR / "data" / "raw" / "other"
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"
PROCESSED_DATA_DIR.mkdir(exist_ok=True)

INPUT_RDF = RAW_DATA_DIR / "nanowiki.cczero.6.rdf.gz"
OUTPUT_CLEAN = PROCESSED_DATA_DIR / "nanowiki_clean.csv"


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
    if 'zno' in n or 'tio2' in n or 'cuo' in n or 'feo' in n or 'oxide' in n or 'o2' in n or 'o3' in n:
        return 'Metal Oxide'
    elif 'cnt' in n or 'nanotube' in n or 'mwcnt' in n or 'swcnt' in n:
        return 'Carbon Nanotube'
    elif 'fullerene' in n or 'c60' in n:
        return 'Fullerene'
    elif 'silica' in n or 'sio2' in n:
        return 'Silicon Dioxide'
    elif 'silver' in n or 'ag' in n:
        return 'Silver'
    elif 'gold' in n or 'au' in n:
        return 'Gold'
    else:
        return 'Nanomaterial'


def parse_nanowiki_rdf():
    print("="*80)
    print("NANOWIKI RDF PREPROCESSING")
    print("="*80)
    
    with gzip.open(INPUT_RDF, 'rt', encoding='utf-8', errors='replace') as f:
        xml_content = f.read()
        
    root = ET.fromstring(xml_content)
    
    ns = {
        'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
        'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
        'owl': 'http://www.w3.org/2002/07/owl#',
        'swivt': 'http://semantic-mediawiki.org/swivt/1.0#'
    }
    
    subjects = root.findall('.//swivt:Subject', ns)
    print(f"\n1. Extracted {len(subjects)} total swivt:Subject RDF elements.")
    
    records = []
    puzyn_skipped_count = 0
    
    for subj in subjects:
        about = subj.attrib.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about', '')
        label_elem = subj.find('./rdfs:label', ns)
        label = label_elem.text if label_elem is not None else ''
        
        # Collect properties
        props = {}
        for child in subj:
            tag = child.tag
            prop_name = tag.split('}')[-1] if '}' in tag else tag
            val = child.text
            resource = child.attrib.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource', '')
            if resource:
                val = resource.split('/')[-1]
            props[prop_name] = val
            
        # Check Puzyn 2011 MeOx cytotoxicity entries (already in DB from meox_clean.csv)
        if 'Puzyn' in label or 'Puzyn' in about or 'Cytotox2011' in label or 'Cytotox2011' in about:
            puzyn_skipped_count += 1
            continue
            
        # Material name
        mat_name = props.get('Has_Chemical_Composition') or props.get('Has_Label') or props.get('Has_alternative_Identifier') or label
        if not mat_name or mat_name in ('Main Page', 'TestNM', 'NanoMaterial', 'Cytotoxicity', 'Puzyn2011'):
            continue
            
        endpoint_val = clean_numeric(props.get('Has_Endpoint_Value') or props.get('Has_Dose'))
        units = props.get('Has_Endpoint_Value_Units') or props.get('Has_Dose_Units')
        
        # Determine if size or cytotoxicity endpoint
        core_size = None
        ec50_val = None
        ic50_val = None
        
        if units and 'nm' in str(units).lower():
            core_size = endpoint_val
        elif endpoint_val is not None:
            ec50_val = endpoint_val
            
        doi = props.get('Has_DOI')
        
        if mat_name and (core_size is not None or ec50_val is not None or endpoint_val is not None):
            records.append({
                'name': mat_name,
                'material_type': derive_material_type(mat_name),
                'core_size_nm': core_size,
                'zeta_potential_mv': None,
                'surface_area_m2g': None,
                'coating': None,
                'source_type': 'literature_mined',
                'doi': doi,
                'ic50': None,
                'ec50': ec50_val,
                'pec50': -np.log10(ec50_val * 1e-6) if (ec50_val and ec50_val > 0 and ec50_val < 1e4) else None,
                'cell_line': props.get('Has_Latin_Name'),
                'exposure_time_h': None
            })
            
    print(f"\n2. Deep Deduplication & Extraction Results:")
    print(f"   - Skipped Puzyn 2011 MeOx duplicates: {puzyn_skipped_count} RDF entries")
    print(f"   - Net-new non-duplicate records extracted: {len(records)} records")
    
    df = pd.DataFrame(records)
    if not df.empty:
        df = df.drop_duplicates()
    df.to_csv(OUTPUT_CLEAN, index=False)
    
    print(f"\n3. Saved clean net-new records to: {OUTPUT_CLEAN} ({len(df)} rows)")
    print("\n" + "="*80)
    print("NANOWIKI PREPROCESSING COMPLETE")
    print("="*80)


if __name__ == '__main__':
    parse_nanowiki_rdf()
