# Backfill Qdrant payloads with fields used by bridge filters.
# Fields: platform, fp_category (needed for cross-category filter)
from storage.database import SessionLocal, Product
from tools.migration.vector_db import VectorDB

db = SessionLocal()
vdb = VectorDB()
products = db.query(Product).filter(Product.embedded_at != None).all()

print(f"Backfilling platform + fp_category for {len(products)} products...")

for i, product in enumerate(products):
    payload_patch = {
        "platform": product.platform,
        "fp_category": product.fp_category,
    }
    for collection in [vdb.image_collection, vdb.text_collection]:
        try:
            vdb.client.set_payload(
                collection_name=collection,
                payload=payload_patch,
                points=[product.id]
            )
        except Exception:
            pass  # point may not exist in this collection

    if (i + 1) % 100 == 0:
        print(f"  {i + 1}/{len(products)} done")

print("Backfill complete!")
db.close()
