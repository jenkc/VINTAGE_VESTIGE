"""
Load more clothing from the same fashion dataset you already have,
but filtered to ONLY actual clothing items (dresses, shirts, jeans, etc.)
and skipping the ones already loaded.

Uses ashraq/fashion-product-images-small which loads fast.
"""

from datasets import load_dataset
from storage.database import SessionLocal, Product
import json
import random
from io import BytesIO
from storage.image_storage import upload_product_image


def upload_pil_image(pil_image, storage_key):
    """Save PIL Image to Supabase Storage, return public URL."""
    buf = BytesIO()
    pil_image.save(buf, format="JPEG", quality=80)
    return upload_product_image(storage_key, buf.getvalue())


# Only real clothing - no watches, perfume, socks, belts, etc.
CLOTHING_TYPES = {
    'Shirts', 'Tshirts', 'Tops', 'Dresses', 'Jeans', 'Track Pants',
    'Shorts', 'Skirts', 'Jackets', 'Sweaters', 'Sweatshirts',
    'Kurtas', 'Kurtis', 'Tunics', 'Blazers', 'Coats', 'Rain Jacket',
    'Leggings', 'Trousers', 'Capris', 'Jumpsuit', 'Rompers',
    'Shrug', 'Waistcoat', 'Nehru Jackets', 'Dupatta',
    'Innerwear Vests', 'Camisoles', 'Tank Top',
}


def load_vintage_data(num_products=100):
    """Load clothing-only items from fashion dataset"""

    print("Loading fashion dataset from Hugging Face...")
    print("  (Already cached - should be fast)\n")

    dataset = load_dataset("ashraq/fashion-product-images-small", split="train")
    print(f"Dataset: {len(dataset)} total items")

    db = SessionLocal()

    # Get existing external IDs to skip duplicates
    existing_ids = set(
        row[0] for row in db.query(Product.external_id).all()
    )
    print(f"Already in DB: {len(existing_ids)} products")

    stored_count = 0
    scanned = 0

    for i in range(len(dataset)):
        if stored_count >= num_products:
            break

        item = dataset[i]
        scanned += 1

        # Filter to clothing only
        article_type = item.get('articleType', '')
        if article_type not in CLOTHING_TYPES:
            continue

        # Skip existing
        ext_id = f'fashion_{item.get("id", i)}'
        if ext_id in existing_ids:
            continue

        try:
            title = item.get('productDisplayName', f'Fashion Item {i}')
            color = item.get('baseColour', '')
            season = item.get('season', '')
            gender = item.get('gender', '')
            usage = item.get('usage', '')
            sub_category = item.get('subCategory', '')

            # Richer description
            desc_parts = [article_type]
            if color:
                desc_parts.append(color)
            if season:
                desc_parts.append(f"{season} season")
            if gender:
                desc_parts.append(f"for {gender}")
            if usage:
                desc_parts.append(f"{usage} wear")
            description = " - ".join(desc_parts)

            # Get image
            pil_image = item.get('image')
            image_data_url = upload_pil_image(pil_image, ext_id) if pil_image else None

            price = round(random.uniform(15, 120), 2)

            product = Product(
                external_id=ext_id,
                platform='vintage_dataset',
                title=title[:255],
                description=description[:500],
                price=price,
                currency='USD',
                primary_image=image_data_url,
                image_urls=json.dumps([image_data_url] if image_data_url else []),
                seller_name='fashion_dataset',
                seller_url='https://huggingface.co/datasets',
                url=f'https://example.com/product/{item.get("id", i)}',
                category=article_type,
                color=color if color else None,
                season=season if season else None,
            )

            db.add(product)
            stored_count += 1

            if stored_count % 25 == 0:
                db.commit()
                print(f"  Stored {stored_count} clothing items (scanned {scanned})...")

        except Exception as e:
            print(f"  Error on item {i}: {e}")
            continue

    db.commit()

    print(f"\nStored {stored_count} new clothing items! (scanned {scanned})")

    # Show samples
    print("\nSample new items:")
    new_items = db.query(Product).filter(
        Product.platform == 'vintage_dataset'
    ).order_by(Product.id.desc()).limit(10).all()
    for p in new_items:
        print(f"  {p.title[:55]} | {p.category} | {p.color}")

    total = db.query(Product).count()
    clothing = db.query(Product).filter(Product.platform == 'vintage_dataset').count()
    print(f"\nNew clothing items: {clothing}")
    print(f"Total in database: {total}")

    db.close()


if __name__ == '__main__':
    import sys
    num = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    load_vintage_data(num_products=num)
