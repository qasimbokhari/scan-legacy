"""
Check current state of Trinh ToxicityRecord rows in the database.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from sqlalchemy.orm import sessionmaker
from api.app.db.models import MaterialRecord, ToxicityRecord
from api.app.db.session import engine

# Set UTF-8 encoding for output
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')


def main():
    """Check Trinh ToxicityRecord state."""
    print("="*80)
    print("CURRENT STATE OF TRINH TOXICITYRECORD ROWS")
    print("="*80)
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    try:
        # Find all materials with material_type='Mixture' (Trinh data)
        trinh_materials = session.query(MaterialRecord).filter(
            MaterialRecord.material_type == 'Mixture'
        ).all()
        
        print(f"\nFound {len(trinh_materials)} Trinh materials (material_type='Mixture')")
        
        # Get all toxicity records linked to these materials
        trinh_material_ids = [m.id for m in trinh_materials]
        trinh_toxicity_records = session.query(ToxicityRecord).filter(
            ToxicityRecord.material_id.in_(trinh_material_ids)
        ).all()
        
        print(f"Found {len(trinh_toxicity_records)} toxicity records linked to Trinh materials")
        
        # Analyze the state of these records
        print(f"\nANALYSIS OF {len(trinh_toxicity_records)} TRINH TOXICITY RECORDS:")
        
        with_classification = sum(1 for t in trinh_toxicity_records if t.toxicity_classification is not None)
        without_classification = sum(1 for t in trinh_toxicity_records if t.toxicity_classification is None)
        
        with_ic50 = sum(1 for t in trinh_toxicity_records if t.ic50 is not None)
        without_ic50 = sum(1 for t in trinh_toxicity_records if t.ic50 is None)
        
        with_ec50 = sum(1 for t in trinh_toxicity_records if t.ec50 is not None)
        without_ec50 = sum(1 for t in trinh_toxicity_records if t.ec50 is None)
        
        with_pec50 = sum(1 for t in trinh_toxicity_records if t.pec50 is not None)
        without_pec50 = sum(1 for t in trinh_toxicity_records if t.pec50 is None)
        
        print(f"\n  toxicity_classification:")
        print(f"    With value: {with_classification}")
        print(f"    Null: {without_classification}")
        
        print(f"\n  ic50:")
        print(f"    With value: {with_ic50}")
        print(f"    Null: {without_ic50}")
        
        print(f"\n  ec50:")
        print(f"    With value: {with_ec50}")
        print(f"    Null: {without_ec50}")
        
        print(f"\n  pec50:")
        print(f"    With value: {with_pec50}")
        print(f"    Null: {without_pec50}")
        
        # Show sample records
        print(f"\nSAMPLE RECORDS (first 5):")
        for i, tox in enumerate(trinh_toxicity_records[:5], 1):
            print(f"\n  Record {i}:")
            print(f"    material_id: {tox.material_id}")
            print(f"    toxicity_classification: {tox.toxicity_classification}")
            print(f"    ic50: {tox.ic50}")
            print(f"    ec50: {tox.ec50}")
            print(f"    pec50: {tox.pec50}")
            print(f"    cell_line: {tox.cell_line}")
            print(f"    exposure_time_h: {tox.exposure_time_h}")
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()
    
    print("\n" + "="*80)
    print("CHECK COMPLETE")
    print("="*80)


if __name__ == "__main__":
    main()
