"""
Clear placeholder MeOx/SAPNet rows from database.
These have names like "Unknown_MeOx" and "Unknown_SAPNet" with no real data.
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
    """Clear MeOx/SAPNet placeholder rows."""
    print("="*80)
    print("CLEAR MEOX/SAPNET PLACEHOLDER ROWS")
    print("="*80)
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    try:
        # Find placeholder materials
        placeholder_materials = session.query(MaterialRecord).filter(
            MaterialRecord.name.in_(['Unknown_MeOx', 'Unknown_SAPNet'])
        ).all()
        
        print(f"\nFound {len(placeholder_materials)} placeholder materials")
        
        if len(placeholder_materials) == 0:
            print("No placeholder materials found. Nothing to delete.")
            return
        
        # Get toxicity records
        material_ids = [m.id for m in placeholder_materials]
        toxicity_records = session.query(ToxicityRecord).filter(
            ToxicityRecord.material_id.in_(material_ids)
        ).all()
        
        print(f"Found {len(toxicity_records)} toxicity records linked to placeholders")
        
        # Delete toxicity records first
        for tox in toxicity_records:
            session.delete(tox)
        
        session.flush()
        print(f"Deleted {len(toxicity_records)} toxicity records")
        
        # Delete material records
        for mat in placeholder_materials:
            session.delete(mat)
        
        print(f"Deleted {len(placeholder_materials)} material records")
        
        session.commit()
        
        print(f"\n✓ Successfully deleted all placeholder rows")
        
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
