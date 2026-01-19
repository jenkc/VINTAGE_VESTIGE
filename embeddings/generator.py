from embeddings.models import models
from storage.database import SessionLocal, Product
import numpy as np
from datetime import datetime
import base64
from io import BytesIO
from PIL import Image
from storage.vector_db import VectorDB

def decode_data_url(data_url):
    """Convert data URL back to PIL Image"""
    if not data_url or not data_url.startswith('data:image'):
        return None
    
    # Extract base64 data
    header, encoded = data_url.split(',', 1)
    image_data = base64.b64decode(encoded)
    
    # Convert to PIL Image
    image = Image.open(BytesIO(image_data))
    return image
  
class EmbeddingGenerator:
  """Generate embeddings for products"""
  
  def __init__(self):
    self.models = models
  
  def generate_product_embeddings(self, product_data):
    """
    Generate embeddings for a product
    
    Args:
      product_data: dict with 'primary_image', 'title', 'description'
        
    Returns:
      dict with 'image_embedding', 'text_embedding'
    """
    embeddings = {}

    # Image embedding
    if product_data.get('primary_image'):
      try:
        image_input = product_data['primary_image']
        
        # If it's a data URL, decode it first
        if isinstance(image_input, str) and image_input.startswith('data:image'):
          image_input = decode_data_url(image_input)
          
        image_emb = self.models.encode_image(image_input)
        embeddings['image_embedding'] = image_emb
      
      except Exception as e:
        print(f"  ⚠️  Image embedding failed: {e}")
        embeddings['image_embedding'] = None
        
    # Text embedding
    text_parts = []
    if product_data.get('title'):
      text_parts.append(product_data['title'])
    if product_data.get('description'):
      text_parts.append(product_data['description'])
      
    text = " ".join(text_parts)
    
    if text:
      text_emb = self.models.encode_text(text)
      embeddings['text_embedding'] = text_emb
      
    return embeddings
  
  def generate_text_embedding(self, text):
    """Generate embedding for search query text"""
    return self.models.encode_text(text)
  
  def generate_image_embedding(self, image_input):
    """Generate embedding for search query image"""
    return self.models.encode_image(image_input)
  
def generate_embeddings_for_database(limit=None):
  """
  Generate embeddings for all products in database
  
  Args:
    limit: Optional limit on number of products to process
  """
  db = SessionLocal()
  generator = EmbeddingGenerator()
  
  # Get products without embeddings
  query = db.query(Product).filter(Product.embedded_at == None)
  if limit:
    query = query.limit(limit)
    
  products = query.all()
  total = len(products)
  
  print(f"📊 Generating embeddings for {total} products...\n")
  
  embeddings_data = []
  
  for i, product in enumerate(products):
    try:
      print(f"[{i+1}/{total}] Processing: {product.title[:50]}...")
      
      # Generate embeddings
      product_data = {
        'primary_image': product.primary_image,
        'title': product.title,
        'description': product.description
      }
      
      embeddings = generator.generate_product_embeddings(product_data)
      
      # Store for later insertion into Qdrant
      embeddings_data.append({
        'product_id': str(product.id),
        'image_embedding': embeddings.get('image_embedding'),
        'text_embedding': embeddings.get('text_embedding'),
        'metadata': {
          'title': product.title,
          'price': product.price,
          'platform': product.platform,
          'url': product.url,
          'primary_image': product.primary_image,
          'description': product.description
        }
      })
      
      # Mark as embedded
      product.embedded_at = datetime.utcnow()
      
      if (i + 1) % 10 == 0:
        db.commit()
        print(f"   ✅ Checkpoint: {i+1} products processed\n")
        
    except Exception as e:
      print(f"  ❌ Error: {e}\n")
      continue
  
  db.commit()
  db.close()
  
  print(f"\n✅ Generated embeddings for {len(embeddings_data)} products!")
  print(f"💾 Ready to store in Qdrant\n")
  
  # Store in Qdrant
  from storage.vector_db import VectorDB
  vector_db = VectorDB()
  
  print(f"💾 Storing in Qdrant...")
  for item in embeddings_data:
    vector_db.upsert_product(
      product_id=item['product_id'],
      embeddings={
        'image_embedding': item['image_embedding'],
        'text_embedding': item['text_embedding']
      },
      metadata=item['metadata']
    )
  print(f"✅ Stored {len(embeddings_data)} products in Qdrant!\n")

  return embeddings_data

if __name__ == "__main__":
  # Test embedding generation with 5 products
  embeddings_data = generate_embeddings_for_database(limit=100)
  
  print(f"📊 Sample embedding data:")
  if embeddings_data:
    sample = embeddings_data[0]
    print(f"   Product ID: {sample['product_id']}")
    print(f"   Title: {sample['metadata']['title']}")
    if sample['image_embedding'] is not None:
        print(f"   Image embedding shape: {sample['image_embedding'].shape}")
    if sample['text_embedding'] is not None:
        print(f"   Text embedding shape: {sample['text_embedding'].shape}")