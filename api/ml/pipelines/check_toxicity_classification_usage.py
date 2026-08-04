"""
Check if toxicity_classification column is used by any dataset.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from sqlalchemy.orm import sessionmaker
from sqlalchemy import func
from api.app.db.models import MaterialRecord, ToxicityRecord
from api.app.db.session import engine

# Set UTF-8 encoding for output
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')


def main():
    """Check toxicity_classification usage."""
    print("="*80)
    print("TOXICITY_CLASSIFICATION COLUMN USAGE CHECK")
    print("="*80)
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    try:
        # Count records with toxicity_classification set
        with_classification = session.query(func.count(ToxicityRecord.id)).filter(
            ToxicityRecord.toxicity_classification.isnot(None)
        ).scalar()
        
        total_toxicity = session.query(func.count(ToxicityRecord.id)).scalar()
        
        print(f"\nTotal ToxicityRecord rows: {total_toxicity}")
        print(f"Rows with toxicity_classification set: {with_classification}")
        
        if with_classification > 0:
            print(f"\nSample records with toxicity_classification:")
            records = session.query(ToxicityRecord).filter(
                ToxicityRecord.toxicity_classification.isnot(None)
            ).limit(5).all()
            
            for i, tox in enumerate(records, 1):
                print(f"  {i}. material_id={tox.material_id}, classification={tox.toxicity_classification}")
        else:
            print(f"\n✓ No records use toxicity_classification column")
        
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
