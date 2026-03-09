"""Upload images to Supabase Storage."""
import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = create_client(
            os.getenv('SUPABASE_URL'),
            os.getenv('SUPABASE_SERVICE_KEY')
        )
    return _client


def upload_product_image(product_id, image_bytes, content_type="image/jpeg"):
    """
    Upload image bytes to Supabase Storage.
    Returns the public URL.
    """
    bucket = os.getenv('SUPABASE_STORAGE_BUCKET', 'product-images')
    ext = 'jpg' if 'jpeg' in content_type else content_type.split('/')[1]
    path = f"{product_id}.{ext}"

    client = _get_client()
    client.storage.from_(bucket).upload(path, image_bytes, {"content-type": content_type})

    return f"{os.getenv('SUPABASE_URL')}/storage/v1/object/public/{bucket}/{path}"
