"""
Manually add zeta_potential_flagged column to material_records table.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from sqlalchemy import text
from api.app.db.session import engine


def main():
    """Add zeta_potential_flagged column to material_records table."""
    print("Adding zeta_potential_flagged column to material_records table...")
    
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE material_records ADD COLUMN zeta_potential_flagged INTEGER"))
            conn.commit()
            print("✓ Column added successfully")
        except Exception as e:
            print(f"Error: {e}")
            # Column might already exist, check if that's the case
            try:
                result = conn.execute(text("SELECT zeta_potential_flagged FROM material_records LIMIT 1"))
                print("Column already exists")
            except:
                print("Column does not exist and could not be added")


if __name__ == "__main__":
    main()
