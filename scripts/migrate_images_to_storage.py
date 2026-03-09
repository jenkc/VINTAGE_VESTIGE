"""
One-time migration: extract base64 images from products table,
upload to Supabase Storage, replace with public URLs.
"""
import os
import sys
import base64
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client
from storage.database import SessionLocal, Product

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET", "product-images")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
db = SessionLocal()

# Only migrate base64 images (skip products with HTTP URLs)
products = db.query(Product).filter(
    Product.primary_image.like('data:image%')
).all()

print(f"Found {len(products)} products with base64 images to migrate\n")

migrated = 0
failed = 0
batch_size = 50

for i, product in enumerate(products):
    try:
        # 1. Parse the data URL
        header, encoded = product.primary_image.split(',', 1)
        media_type = header.split(';')[0].split(':')[1]  # e.g. "image/jpg"
        ext = 'jpg' if 'jpeg' in media_type else media_type.split('/')[1]  # e.g. "jpg" or "png"

        # 2. Decode to bytes
        raw_bytes = base64.b64decode(encoded)

        # 3. Upload to Supabase Storage
        path = f"{product.id}.{ext}"
        result = supabase.storage.from_(BUCKET).upload(
            path,
            raw_bytes,
            {"content-type": media_type}
        )

        # 4. Build public URL and update product
        public_url = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET}/{path}"
        product.primary_image = public_url

        migrated += 1

        if migrated % batch_size == 0:
            db.commit()
            print(f"  [{migrated}/{len(products)}] committed batch")

    except Exception as e:
        # If file alread exists (re-run), just update the URL
        if 'Duplicate' in str(e) or 'already exists' in str(e):
            path = f"{product.id}.jpg"
            public_url = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET}/{path}"
            product.primary_image = public_url
            migrated += 1
        else:
            print(f"  FAILED product {product.id}: {e}")
            failed += 1

    # Gentle rate limiting
    if (i + 1) % 10 == 0:
        time.sleep(0.1)

db.commit()
db.close()

print(f"\nDone! Migrated: {migrated}, Failed: {failed}")