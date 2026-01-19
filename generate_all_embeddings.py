from embeddings.generator import generate_embeddings_for_database
from storage.vector_db import VectorDB  
from storage.database import SessionLocal

def main():
  """Generate embeddings and store in Qdrant vector DB"""
  
  print("=" * 60)
  print("🚀 VINTAGE VESTIGE - EMBEDDING GENERATION")
  print("=" * 60)
  print()
  
  # Step 1: Generate embeddings
  print("STEP 1: Generating embeddings from database...\n")
  embeddings_data = generate_embeddings_for_database()
  
  if not embeddings_data:
    print("❌ No products to process!")
    return
  
  # Step 2: Store embeddings in Qdrant
  print("\nSTEP 2: Storing embeddings in Qdrant...\n")
  vector_db = VectorDB()
  
  for i, item in enumerate(embeddings_data):
    try:
      vector_db.upsert_product(
        product_id=item['product_id'],
        embeddings={
          'image_embedding': item['embeddings'].get('image_embedding'),
          'text_embedding': item['embeddings'].get('text_embedding')
        },
        metadata=item['metadata']
      )

      if (i + 1) % 10 == 0:
        print(f"  ✅ Stored {i+1}/{len(embeddings_data)} products")
        
    except Exception as e:
      print(f"  ⚠️  Error storing product {item['product_id']}: {e}")
      
  print(f"\n✅ Stored all {len(embeddings_data)} products in Qdrant!")

  # Step 3: Verify
  print("\nSTEP 3: Verifying storage...\n")
  info = vector_db.get_collection_info()
    
  print("📊 Collection Statistics:")
  for name, data in info.items():
    print(f"   {name}:")
    for key, value in data.items():
      print(f"      {key}: {value}")
    
  print("\n" + "=" * 60)
  print("🎉 EMBEDDING GENERATION COMPLETE!")
  print("=" * 60)
  print()
  print("✅ Products now searchable by:")
  print("   • Image similarity (CLIP)")
  print("   • Text similarity (semantic search)")
  print()
  print("Next: Test similarity search!")  
  
if __name__ == "__main__":
  main()