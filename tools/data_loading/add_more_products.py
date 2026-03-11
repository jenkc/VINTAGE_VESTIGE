from datasets import load_dataset
from storage.database import SessionLocal, Product
from embeddings.generator import generate_embeddings_for_database
import json
import random
from io import BytesIO
from storage.image_storage import upload_product_image

def upload_pil_image(pil_image, storage_key):
    """Save PIL Image to Supabase Storage, return public URL."""
    buf = BytesIO()
    pil_image.save(buf, format="JPEG", quality=80)
    return upload_product_image(storage_key, buf.getvalue())

def add_more_products(num_to_add=450):
    """Add random products from Hugging Face dataset"""

    print("=" * 60)
    print("🚀 ADDING MORE PRODUCTS TO VINTAGE VESTIGE")
    print("=" * 60)
    print(f"\n📊 Adding up to {num_to_add} random products\n")

    # Check current database state
    db = SessionLocal()
    current_count = db.query(Product).count()
    print(f"📦 Current products in database: {current_count}\n")

    print("📦 Loading fashion dataset from Hugging Face...")
    print("   (This may take a moment)\n")

    try:
        dataset = load_dataset("ashraq/fashion-product-images-small", split="train")
        print(f"✅ Dataset loaded: {len(dataset)} total products available\n")
    except Exception as e:
        print(f"❌ Error loading dataset: {e}")
        db.close()
        return

    # Generate random indices from the full dataset
    all_indices = list(range(len(dataset)))
    random.shuffle(all_indices)

    print(f"💾 Loading {num_to_add} random products...\n")

    stored_count = 0
    skipped_count = 0
    checked_count = 0

    for i in all_indices:
        if stored_count >= num_to_add:
            break

        try:
            item = dataset[i]
            external_id = f'fashion_{item.get("id", i)}'

            # Check if already exists
            existing = db.query(Product).filter(Product.external_id == external_id).first()
            if existing:
                skipped_count += 1
                continue

            # Extract fields
            title = item.get('productDisplayName', f'Fashion Item {i}')
            article_type = item.get('articleType', 'clothing')
            color = item.get('baseColour', '')
            season = item.get('season', '')
            gender = item.get('gender', '')

            # Build description
            desc_parts = [article_type]
            if color:
                desc_parts.append(color)
            if season:
                desc_parts.append(f"{season} season")
            if gender:
                desc_parts.append(f"for {gender}")

            description = " - ".join(desc_parts)

            # Get image
            pil_image = item.get('image')
            image_data_url = upload_pil_image(pil_image, external_id) if pil_image else None

            # Random price
            price = round(random.uniform(20, 150), 2)

            product_data = {
                'external_id': external_id,
                'platform': 'huggingface_dataset',
                'title': title[:255],
                'description': description[:500],
                'price': price,
                'currency': 'USD',
                'primary_image': image_data_url,
                'image_urls': json.dumps([image_data_url] if image_data_url else []),
                'seller_name': 'fashion_dataset',
                'seller_url': 'https://huggingface.co/datasets',
                'url': f'https://example.com/product/{item.get("id", i)}',
                'category': article_type,
                'style_tags': json.dumps([color, season]) if color or season else None,
            }

            product = Product(**product_data)
            db.add(product)
            stored_count += 1

            if stored_count % 50 == 0:
                db.commit()
                print(f"  ✅ Added {stored_count} products...")

        except Exception as e:
            print(f"  ⚠️  Error on item {i}: {e}")
            continue

        checked_count += 1
        if checked_count % 100 == 0 and stored_count < num_to_add:
            print(f"  📊 Checked {checked_count} items, added {stored_count} so far...")

    db.commit()

    new_total = db.query(Product).count()
    unembedded = db.query(Product).filter(Product.embedded_at == None).count()

    print(f"\n" + "=" * 60)
    print(f"✅ PRODUCTS LOADED!")
    print(f"=" * 60)
    print(f"\n📊 Results:")
    print(f"   Checked: {checked_count} random items")
    print(f"   Added: {stored_count} new products")
    print(f"   Skipped (duplicates): {skipped_count}")
    print(f"   Total in database: {new_total}")
    print(f"   Awaiting embeddings: {unembedded}")

    db.close()

    return stored_count

def generate_new_embeddings():
    """Generate embeddings for products that don't have them yet"""
    print("\n" + "=" * 60)
    print("🧠 GENERATING EMBEDDINGS FOR NEW PRODUCTS")
    print("=" * 60 + "\n")

    generate_embeddings_for_database()

if __name__ == '__main__':
    # Step 1: Add 450 random products
    added = add_more_products(num_to_add=500)

    if added and added > 0:
        # Step 2: Generate embeddings for new products
        print("\n" + "=" * 60)
        print("📝 STEP 2: GENERATING EMBEDDINGS")
        print("=" * 60)
        generate_new_embeddings()

    print("\n🎉 Done! You now have 500 products with embeddings.")
