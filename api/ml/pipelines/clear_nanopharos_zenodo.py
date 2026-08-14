"""
Clear nanoPharos and Zenodo (MeOx/SAPNet) sourced rows from database.
Identifies these rows by material_type != 'Unknown' (caNanoLab has material_type='Unknown').
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
    """Clear nanoPharos and Zenodo rows."""
    print("="*80)
    print("CLEAR NANOPHAROS AND ZENODO ROWS")
    print("="*80)
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    try:
        # Find all materials with material_type != 'Unknown' (nanoPharos + Zenodo)
        nanopharos_zenodo_materials = session.query(MaterialRecord).filter(
            MaterialRecord.material_type != 'Unknown'
        ).all()
        
        print(f"\nFound {len(nanopharos_zenodo_materials)} materials with material_type != 'Unknown'")
        print("(These are nanoPharos and Zenodo-sourced rows)")
        
        if len(nanopharos_zenodo_materials) == 0:
            print("No nanoPharos/Zenodo materials found. Nothing to delete.")
            return
        
        # Get all toxicity records linked to these materials
        material_ids = [m.id for m in nanopharos_zenodo_materials]
        toxicity_records = session.query(ToxicityRecord).filter(
            ToxicityRecord.material_id.in_(material_ids)
        ).all()
        
        print(f"Found {len(toxicity_records)} toxicity records linked to these materials")
        
        # Delete toxicity records first (foreign key constraint)
        for tox in toxicity_records:
            session.delete(tox)
        
        session.flush()
        print(f"Deleted {len(toxicity_records)} toxicity records")
        
        # Delete material records
        for mat in nanopharos_zenodo_materials:
            session.delete(mat)
        
        print(f"Deleted {len(nanopharos_zenodo_materials)} material records")
        
        session.commit()
        
        print(f"\n✓ Successfully deleted all nanoPharos and Zenodo-sourced records")
        
        # Verify caNanoLab data remains
        cananolab_materials = session.query(MaterialRecord).filter(
            MaterialRecord.material_type == 'Unknown'
        ).count()
        
        print(f"\nVerification:")
        print(f"  caNanoLab materials remaining (material_type='Unknown'): {cananolab_materials}")
        
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
