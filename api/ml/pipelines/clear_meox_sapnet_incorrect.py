"""
Clear incorrectly inserted MeOx/SAPNet rows from database.
These were inserted from the wrong sheet (ModelingDataset instead of InitialDataset).
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
    """Clear MeOx/SAPNet rows inserted from incorrect sheet."""
    print("="*80)
    print("CLEAR INCORRECTLY INSERTED MEOX/SAPNET ROWS")
    print("="*80)
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    try:
        # Find MeOx and SAPNet materials (they have material_type 'Metal Oxide' or 'TiO2-based')
        incorrect_materials = session.query(MaterialRecord).filter(
            MaterialRecord.material_type.in_(['Metal Oxide', 'TiO2-based'])
        ).all()
        
        print(f"\nFound {len(incorrect_materials)} materials to delete")
        
        if len(incorrect_materials) == 0:
            print("No materials found. Nothing to delete.")
            return
        
        # Get toxicity records
        material_ids = [m.id for m in incorrect_materials]
        toxicity_records = session.query(ToxicityRecord).filter(
            ToxicityRecord.material_id.in_(material_ids)
        ).all()
        
        print(f"Found {len(toxicity_records)} toxicity records linked")
        
        # Delete toxicity records first
        for tox in toxicity_records:
            session.delete(tox)
        
        session.flush()
        print(f"Deleted {len(toxicity_records)} toxicity records")
        
        # Delete material records
        for mat in incorrect_materials:
            session.delete(mat)
        
        print(f"Deleted {len(incorrect_materials)} material records")
        
        session.commit()
        
        print(f"\n✓ Successfully deleted all incorrectly inserted rows")
        
    except Exception as e:
        session.rollback()
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()
    
    print("\n" + "="*80)
    print("CLEARANCE COMPLETE")
    print("="*80)


if __name__ == "__main__":
    main()
