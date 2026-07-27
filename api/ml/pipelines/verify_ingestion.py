"""
Verification script for data ingestion.
Reports total counts from material_records and toxicity_records tables,
broken down by source dataset where possible.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from sqlalchemy import func
from sqlalchemy.orm import sessionmaker
from api.app.db.models import MaterialRecord, ToxicityRecord
from api.app.db.session import engine

# Set UTF-8 encoding for output
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')


def main():
    """Run verification queries."""
    print("="*80)
    print("DATA INGESTION VERIFICATION")
    print("="*80)
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    try:
        # Total counts
        total_materials = session.query(func.count(MaterialRecord.id)).scalar()
        total_toxicities = session.query(func.count(ToxicityRecord.id)).scalar()
        
        print(f"\nTOTAL COUNTS:")
        print(f"  Material records: {total_materials}")
        print(f"  Toxicity records: {total_toxicities}")
        
        # Breakdown by source_type
        print(f"\nBREAKDOWN BY SOURCE_TYPE:")
        source_counts = session.query(
            MaterialRecord.source_type,
            func.count(MaterialRecord.id)
        ).group_by(MaterialRecord.source_type).all()
        
        for source_type, count in source_counts:
            print(f"  {source_type}: {count} materials")
        
        # Breakdown by material_type
        print(f"\nBREAKDOWN BY MATERIAL_TYPE (top 10):")
        material_type_counts = session.query(
            MaterialRecord.material_type,
            func.count(MaterialRecord.id)
        ).group_by(MaterialRecord.material_type).order_by(
            func.count(MaterialRecord.id).desc()
        ).limit(10).all()
        
        for material_type, count in material_type_counts:
            print(f"  {material_type}: {count} materials")
        
        # Check for materials without toxicity data
        materials_without_tox = session.query(func.count(MaterialRecord.id)).filter(
            ~MaterialRecord.id.in_(
                session.query(ToxicityRecord.material_id)
            )
        ).scalar()
        
        print(f"\nMATERIALS WITHOUT TOXICITY DATA:")
        print(f"  {materials_without_tox} materials have no linked toxicity records")
        
        # Check for materials with required fields
        materials_missing_name = session.query(func.count(MaterialRecord.id)).filter(
            MaterialRecord.name.is_(None)
        ).scalar()
        
        materials_missing_type = session.query(func.count(MaterialRecord.id)).filter(
            MaterialRecord.material_type.is_(None)
        ).scalar()
        
        print(f"\nDATA QUALITY CHECKS:")
        print(f"  Materials missing name: {materials_missing_name}")
        print(f"  Materials missing material_type: {materials_missing_type}")
        
        # Sample records
        print(f"\nSAMPLE MATERIAL RECORDS (first 5):")
        sample_materials = session.query(MaterialRecord).limit(5).all()
        for i, mat in enumerate(sample_materials, 1):
            print(f"  {i}. {mat.name} ({mat.material_type}) - source: {mat.source_type}")
        
        print(f"\nSAMPLE TOXICITY RECORDS (first 5):")
        sample_toxicities = session.query(ToxicityRecord).limit(5).all()
        for i, tox in enumerate(sample_toxicities, 1):
            print(f"  {i}. material_id: {tox.material_id} - ic50: {tox.ic50}, ec50: {tox.ec50}")
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()
    
    print("\n" + "="*80)
    print("VERIFICATION COMPLETE")
    print("="*80)


if __name__ == "__main__":
    main()
