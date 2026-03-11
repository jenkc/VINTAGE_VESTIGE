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

def load_fashion_data(num_products=50):
    """Load fashion dataset from Hugging Face with real images"""
    
    print("📦 Loading fashion dataset from Hugging Face...")
    print("   (This may take a minute - loading images)\n")
    
    try:
        # Load fashion product dataset
        dataset = load_dataset("ashraq/fashion-product-images-small", split="train")
        print(f"✅ Loaded dataset with {len(dataset)} total products")
        print(f"   Using first {num_products} for testing\n")
        
    except Exception as e:
        print(f"❌ Error loading dataset: {e}")
        return
    
    db = SessionLocal()
    
    print("💾 Storing products in database (with real images!)...\n")
    
    stored_count = 0
    
    for i in range(min(num_products, len(dataset))):
        try:
            item = dataset[i]
            
            # Extract fields from dataset
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
            
            # Get the actual PIL Image!
            pil_image = item.get('image')
            
            # Convert to data URL for storage
            # (This embeds the image directly in the database)
            if pil_image:
                ex_id = f'fashion_{item.get("id", i)}'
                image_data_url = upload_pil_image(pil_image, ex_id)
            else:
                image_data_url = None
            
            # Random price between $20-$150
            price = round(random.uniform(20, 150), 2)
            
            product_data = {
                'external_id': f'fashion_{item.get("id", i)}',
                'platform': 'huggingface_dataset',
                'title': title[:255],
                'description': description[:500],
                'price': price,
                'currency': 'USD',
                'primary_image': image_data_url,  # Data URL with embedded image
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
            
            if (i + 1) % 10 == 0:
                db.commit()
                print(f"  ✅ Processed {i + 1}/{num_products} products (with images!)")
        
        except Exception as e:
            print(f"  ⚠️  Error on item {i}: {e}")
            continue
    
    db.commit()
    print(f"\n✅ Successfully stored {stored_count} products!\n")
    
    # Show samples
    print("📦 Sample products:")
    for p in db.query(Product).limit(5):
        has_image = "✅ Image" if p.primary_image and p.primary_image.startswith('data:image') else "❌ No image"
        print(f"  • {p.title[:50]}... ({has_image})")
    
    total = db.query(Product).count()
    print(f"\n📊 Total products in database: {total}")
    
    db.close()
    print("\n🎉 Database ready with REAL IMAGES!")

if __name__ == '__main__':
    load_fashion_data(num_products=50)
    
