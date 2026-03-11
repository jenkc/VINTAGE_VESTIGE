"""Wipe all products from PostgreSQL and clear Qdrant vectors."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from storage.database import SessionLocal, Product
from tools.migration.vector_db import VectorDB
from sqlalchemy import text


def wipe_database():
    db = SessionLocal()
    count = db.query(Product).count()
    db.execute(text('DELETE FROM products'))
    db.commit()
    db.close()
    print(f"Deleted {count} products from PostgreSQL")

    try:
        vdb = VectorDB()
        for col in ['vintage_images', 'vintage_text']:
            vdb.client.delete_collection(col)
        vdb._init_collections()
        print("Cleared and recreated Qdrant collections")
    except Exception as e:
        print(f"Qdrant cleanup note: {e}")

    print("Database wiped.")


if __name__ == '__main__':
    confirm = input("Delete ALL products and vectors? (yes/no): ")
    if confirm.lower() == 'yes':
        wipe_database()
    else:
        print("Cancelled.")
