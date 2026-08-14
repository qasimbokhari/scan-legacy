"""
Delete Trinh-sourced records from the database.
Identifies Trinh records by material_type='Mixture' and deletes both
ToxicityRecord and MaterialRecord rows.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports (running from api/ directory)
sys.path.append(str(Path(__file__).parent.parent.parent))

from sqlalchemy.orm import sessionmaker
from app.db.models import MaterialRecord, ToxicityRecord
from app.db.session import engine

# Set UTF-8 encoding for output
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')


def main():
    """Delete Trinh records."""
    print("="*80)
    print("DELETE TRINH-SOURCED RECORDS")
    print("="*80)
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    try:
        # Find all materials with material_type='Mixture' (Trinh data)
        trinh_materials = session.query(MaterialRecord).filter(
            MaterialRecord.material_type == 'Mixture'
        ).all()
        
        print(f"\nFound {len(trinh_materials)} Trinh materials (material_type='Mixture')")
        
        if len(trinh_materials) == 0:
            print("No Trinh materials found. Nothing to delete.")
            return
        
        # Get all toxicity records linked to these materials
        trinh_material_ids = [m.id for m in trinh_materials]
        trinh_toxicity_records = session.query(ToxicityRecord).filter(
            ToxicityRecord.material_id.in_(trinh_material_ids)
        ).all()
        
        print(f"Found {len(trinh_toxicity_records)} toxicity records linked to Trinh materials")
        
        # Delete toxicity records first (foreign key constraint)
        for tox in trinh_toxicity_records:
            session.delete(tox)
        
        session.flush()  # Flush to ensure toxicity records are deleted before materials
        print(f"Deleted {len(trinh_toxicity_records)} toxicity records")
        
        # Delete material records
        for mat in trinh_materials:
            session.delete(mat)
        
        print(f"Deleted {len(trinh_materials)} material records")
        
        session.commit()
        
        print(f"\n✓ Successfully deleted all Trinh-sourced records")
        
    except Exception as e:
        session.rollback()
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()
    
    print("\n" + "="*80)
    print("DELETION COMPLETE")
    print("="*80)


if __name__ == "__main__":
    main()
