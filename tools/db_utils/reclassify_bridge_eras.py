import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from storage.database import SessionLocal, StyleBridge, Product
from tools.analysis.compute_bridges import classify_temporal_type

db = SessionLocal()
bridges = db.query(StyleBridge).all()
updated = 0

for b in bridges:
    src = db.query(Product).get(b.source_id)
    tgt = db.query(Product).get(b.target_id)
    new_type = classify_temporal_type(src.era, tgt.era, src.decade, tgt.decade)
    if new_type != b.temporal_type:
        b.temporal_type = new_type
        updated += 1
    if updated % 500 == 0:
        db.commit()

db.commit()
print(f"Updated {updated} bridges")
db.close()
