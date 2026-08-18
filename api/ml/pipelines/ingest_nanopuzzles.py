"""
Ingestion script for NanoPUZZLES ISA-TAB datasets.
Parses nanopuzzles_clean.csv and inserts into material_records and toxicity_records
with strict duplicate prevention.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
import codecs
from sqlalchemy.orm import sessionmaker

sys.path.append(str(Path(__file__).parent.parent.parent))

from app.db.models import MaterialRecord, ToxicityRecord
from app.db.session import engine

if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"
INPUT_FILE = PROCESSED_DATA_DIR / "nanopuzzles_clean.csv"


def insert_nanopuzzles(df, session):
    materials_inserted = 0
    toxicities_inserted = 0
    duplicates_skipped = 0
    
    for _, row in df.iterrows():
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
            'doi': doi_val
        }
        
        # Check duplicate material
        q = session.query(MaterialRecord).filter(
            MaterialRecord.name == mat_data['name'],
            MaterialRecord.material_type == mat_data['material_type']
        )
        if mat_data['doi']:
            q = q.filter(MaterialRecord.doi == mat_data['doi'])
            
        existing_mat = q.first()
        if existing_mat:
            mat_id = existing_mat.id
        else:
            mat = MaterialRecord(**mat_data)
            session.add(mat)
            session.flush()
            mat_id = mat.id
            materials_inserted += 1
            
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
            
            q_t = session.query(ToxicityRecord).filter(ToxicityRecord.material_id == mat_id)
            if tox_data['ec50'] is not None:
                q_t = q_t.filter(ToxicityRecord.ec50 == tox_data['ec50'])
            if tox_data['ic50'] is not None:
                q_t = q_t.filter(ToxicityRecord.ic50 == tox_data['ic50'])
                
            existing_t = q_t.first()
            if existing_t:
                duplicates_skipped += 1
            else:
                tox = ToxicityRecord(**tox_data)
                session.add(tox)
                toxicities_inserted += 1
                
    session.commit()
    return materials_inserted, toxicities_inserted, duplicates_skipped


def main():
    print("="*80)
    print("NANOPUZZLES DATA INGESTION")
    print("="*80)
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    try:
        df = pd.read_csv(INPUT_FILE)
        print(f"Loaded {len(df)} records from {INPUT_FILE.name}.")
        
        m_before = session.query(MaterialRecord).count()
        t_before = session.query(ToxicityRecord).count()
        
        print(f"\nBefore Counts:")
        print(f"  material_records: {m_before}")
        print(f"  toxicity_records: {t_before}")
        
        m_ins, t_ins, dup = insert_nanopuzzles(df, session)
        
        m_after = session.query(MaterialRecord).count()
        t_after = session.query(ToxicityRecord).count()
        
        print(f"\nAfter Counts:")
        print(f"  material_records: {m_after} (Net: +{m_after - m_before}, inserted: {m_ins})")
        print(f"  toxicity_records: {t_after} (Net: +{t_after - t_before}, inserted: {t_ins})")
        print(f"  Duplicates skipped: {dup}")
        
    except Exception as e:
        session.rollback()
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()
        
    print("\n" + "="*80)
    print("NANOPUZZLES INGESTION COMPLETE")
    print("="*80)


if __name__ == '__main__':
    main()
