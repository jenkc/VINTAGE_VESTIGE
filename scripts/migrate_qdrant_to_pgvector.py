"""
One-time migration: read embeddings from local Qdrant,
write them to pgvector columns in Supabase PostgreSQL.
"""

import os
import sys

sys.path.insert(0, 
os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv()

from qdrant_client import QdrantClient
from storage.database import SessionLocal, Product
from sqlalchemy import text

# Connect to local Qdrant (still running)
qdrant = QdrantClient(
    host=os.getenv('QDRANT_HOST', 'localhost'),
    port=int(os.getenv('QDRANT_PORT', 6333))
)

db = SessionLocal()  # Now pointing at Supabase

def migrate_collection(collection_name, column_name):
    """Write vectors in Qdrant to pgvector column in Supabase."""
    print(f"\nMigrating {collection_name} → {column_name} ... ")
    migrated = 0
    offset = None

    while True:
        points, offset = qdrant.scroll(
            collection_name=collection_name,
            limit=100,
            offset=offset,
            with_vectors=True,
            with_payload=False,
        )

        for point in points:
            vec_str = str(point.vector)  # pgvector accepts format [0.1, 0.2, ...]
            db.execute(
                text(f"UPDATE products SET {column_name} = :vec WHERE id = :id"),
                {"vec": vec_str, "id": point.id}
            )
            migrated += 1

        db.commit()
        print(f"   Migrated {migrated} embeddings so far ...")

        if offset is None:
            break
    
    print(f"  Done: {migrated} total")
    return migrated

# Migrate both collections
text_count = migrate_collection('vintage_text', 'text_embedding')
image_count = migrate_collection('vintage_images', 'image_embedding')

db.close()

print(f"\nMigration complete!")
print(f"  Text embeddings migrated: {text_count}")
print(f"  Image embeddings migrated: {image_count}")
