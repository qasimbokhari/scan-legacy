"""
One-time correction script for Trinh classification data.
Migrates existing Trinh-sourced ToxicityRecord rows from the sentinel pattern
in ic50 field to the dedicated toxicity_classification field.

This script:
1. Finds toxicity records linked to materials with material_type='Mixture' (Trinh data)
2. For records with ic50 sentinel values (1.0 or 0.0), migrates to toxicity_classification
3. Nulls out the fake ic50, ec50, and pec50 sentinel values
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
    """Run the correction migration."""
    print("="*80)
    print("TRINH CLASSIFICATION CORRECTION MIGRATION")
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
        
        # Migrate records
        migrated_count = 0
        skipped_count = 0
        
        for tox in trinh_toxicity_records:
            # Check if this record has sentinel ic50 values
            if tox.ic50 == 1.0:
                tox.toxicity_classification = 'toxic'
                tox.ic50 = None
                tox.ec50 = None
                tox.pec50 = None
                migrated_count += 1
                print(f"  Migrated: material_id={tox.material_id}, ic50 was 1.0 -> toxicity_classification='toxic'")
            elif tox.ic50 == 0.0:
                tox.toxicity_classification = 'non_toxic'
                tox.ic50 = None
                tox.ec50 = None
                tox.pec50 = None
                migrated_count += 1
                print(f"  Migrated: material_id={tox.material_id}, ic50 was 0.0 -> toxicity_classification='non_toxic'")
            else:
                # Record doesn't have sentinel values, skip
                skipped_count += 1
                print(f"  Skipped: material_id={tox.material_id}, ic50={tox.ic50} (not a sentinel value)")
        
        session.commit()
        
        print(f"\nMigration summary:")
        print(f"  Records migrated: {migrated_count}")
        print(f"  Records skipped: {skipped_count}")
        
        # Verify the migration
        print(f"\nVerification:")
        trinh_toxicity_after = session.query(ToxicityRecord).filter(
            ToxicityRecord.material_id.in_(trinh_material_ids)
        ).all()
        
        with_sentinel = sum(1 for t in trinh_toxicity_after if t.ic50 in [1.0, 0.0])
        with_classification = sum(1 for t in trinh_toxicity_after if t.toxicity_classification is not None)
        
        print(f"  Records with sentinel ic50 (1.0 or 0.0): {with_sentinel}")
        print(f"  Records with toxicity_classification set: {with_classification}")
        
        if with_sentinel == 0:
            print(f"  ✓ All sentinel values successfully removed")
        else:
            print(f"  ✗ WARNING: {with_sentinel} records still have sentinel values")
        
    except Exception as e:
        session.rollback()
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()
    
    print("\n" + "="*80)
    print("CORRECTION MIGRATION COMPLETE")
    print("="*80)


if __name__ == "__main__":
    main()
