"""
Ingestion script for NanoReg and NanoReg2 ENANOMAPPER data.
Parses nanoreg_clean.csv and nanoreg_isolated_clean.csv, inserting into
material_records, toxicity_records, and nanoreg_records tables with duplicate prevention.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
import codecs
from sqlalchemy.orm import sessionmaker

sys.path.append(str(Path(__file__).parent.parent.parent))

from app.db.models import MaterialRecord, ToxicityRecord, NanoregRecord
from app.db.session import engine

# Set UTF-8 encoding for output
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"
STD_FILE = PROCESSED_DATA_DIR / "nanoreg_clean.csv"
ISO_FILE = PROCESSED_DATA_DIR / "nanoreg_isolated_clean.csv"


def insert_standard_records(df_std, session):
    materials_inserted = 0
    toxicities_inserted = 0
    duplicates_skipped = 0
    
    for _, row in df_std.iterrows():
        coating_val = row['coating'] if pd.notna(row['coating']) else None
        doi_val = row['doi'] if pd.notna(row['doi']) else None
        
        mat_data = {
            'name': str(row['name']),
            'material_type': str(row['material_type']),
            'core_size_nm': row['core_size_nm'] if pd.notna(row['core_size_nm']) else None,
            'zeta_potential_mv': row['zeta_potential_mv'] if pd.notna(row['zeta_potential_mv']) else None,
            'surface_area_m2g': row['surface_area_m2g'] if pd.notna(row['surface_area_m2g']) else None,
            'coating': coating_val,
            'source_type': str(row['source_type']),
            'doi': doi_val,
        }
        
        # Check duplicate material
        q = session.query(MaterialRecord).filter(
            MaterialRecord.name == mat_data['name'],
            MaterialRecord.material_type == mat_data['material_type'],
            MaterialRecord.source_type == mat_data['source_type']
        )
        if mat_data['core_size_nm'] is not None:
            q = q.filter(MaterialRecord.core_size_nm == mat_data['core_size_nm'])
            
        existing_mat = q.first()
        
        if existing_mat:
            mat_id = existing_mat.id
        else:
            mat = MaterialRecord(**mat_data)
            session.add(mat)
            session.flush()
            mat_id = mat.id
            materials_inserted += 1
            
        # Toxicity record
        has_tox = any(pd.notna(row[k]) for k in ['ic50', 'ec50', 'pec50'])
        if has_tox:
            tox_data = {
                'material_id': mat_id,
                'ic50': row['ic50'] if pd.notna(row['ic50']) else None,
                'ec50': row['ec50'] if pd.notna(row['ec50']) else None,
                'pec50': row['pec50'] if pd.notna(row['pec50']) else None,
                'cell_line': row['cell_line'] if pd.notna(row['cell_line']) else None,
                'exposure_time_h': row['exposure_time_h'] if pd.notna(row['exposure_time_h']) else None
            }
            
            # Check duplicate toxicity
            q_t = session.query(ToxicityRecord).filter(
                ToxicityRecord.material_id == mat_id
            )
            if tox_data['cell_line']:
                q_t = q_t.filter(ToxicityRecord.cell_line == tox_data['cell_line'])
            if tox_data['ec50'] is not None:
                q_t = q_t.filter(ToxicityRecord.ec50 == tox_data['ec50'])
                
            existing_t = q_t.first()
            if existing_t:
                duplicates_skipped += 1
            else:
                tox = ToxicityRecord(**tox_data)
                session.add(tox)
                toxicities_inserted += 1
                
    session.commit()
    return materials_inserted, toxicities_inserted, duplicates_skipped


def insert_isolated_records(df_iso, session):
    records_inserted = 0
    duplicates_skipped = 0
    
    # Process in batches for performance
    batch = []
    for _, row in df_iso.iterrows():
        record_dict = {
            'substance_name': str(row['substance_name']),
            'jrc_id': str(row['jrc_id']) if pd.notna(row['jrc_id']) else None,
            'topcategory': str(row['topcategory']) if pd.notna(row['topcategory']) else None,
            'endpointcategory': str(row['endpointcategory']) if pd.notna(row['endpointcategory']) else None,
            'endpoint': str(row['endpoint']) if pd.notna(row['endpoint']) else None,
            'value_numeric': row['value_numeric'] if pd.notna(row['value_numeric']) else None,
            'unit': str(row['unit']) if pd.notna(row['unit']) else None,
            'text_value': str(row['text_value']) if pd.notna(row['text_value']) else None,
            'reference': str(row['reference']) if pd.notna(row['reference']) else None,
            'source_type': str(row['source_type']),
            'provenance_note': str(row['provenance_note']) if pd.notna(row['provenance_note']) else None
        }
        batch.append(NanoregRecord(**record_dict))
        
        if len(batch) >= 1000:
            session.bulk_save_objects(batch)
            session.commit()
            records_inserted += len(batch)
            batch = []
            
    if batch:
        session.bulk_save_objects(batch)
        session.commit()
        records_inserted += len(batch)
        
    return records_inserted, duplicates_skipped


def main():
    print("="*80)
    print("NANOREG DATA INGESTION")
    print("="*80)
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    try:
        df_std = pd.read_csv(STD_FILE)
        df_iso = pd.read_csv(ISO_FILE)
        print(f"Loaded {len(df_std)} standard rows and {len(df_iso)} isolated rows.")
        
        # Row counts before
        m_before = session.query(MaterialRecord).count()
        t_before = session.query(ToxicityRecord).count()
        n_before = session.query(NanoregRecord).count()
        
        print(f"\nBefore Counts:")
        print(f"  material_records: {m_before}")
        print(f"  toxicity_records: {t_before}")
        print(f"  nanoreg_records: {n_before}")
        
        print("\nInserting standard records...")
        m_ins, t_ins, dup_std = insert_standard_records(df_std, session)
        
        print("Inserting isolated records...")
        n_ins, dup_iso = insert_isolated_records(df_iso, session)
        
        m_after = session.query(MaterialRecord).count()
        t_after = session.query(ToxicityRecord).count()
        n_after = session.query(NanoregRecord).count()
        
        print(f"\nAfter Counts:")
        print(f"  material_records: {m_after} (Net: +{m_after - m_before}, inserted: {m_ins})")
        print(f"  toxicity_records: {t_after} (Net: +{t_after - t_before}, inserted: {t_ins})")
        print(f"  nanoreg_records: {n_after} (Net: +{n_after - n_before}, inserted: {n_ins})")
        print(f"  Duplicates skipped: {dup_std}")
        
    except Exception as e:
        session.rollback()
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()
        
    print("\n" + "="*80)
    print("INGESTION COMPLETE")
    print("="*80)


if __name__ == '__main__':
    main()
