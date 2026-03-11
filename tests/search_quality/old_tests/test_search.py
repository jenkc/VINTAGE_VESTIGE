from embeddings.generator import EmbeddingGenerator
from tools.migration.vector_db import VectorDB
from storage.database import SessionLocal, Product

def test_text_search():
  """Test text-based similarity search"""
  print("\n" + "=" * 60)
  print("🔍 TEXT SEARCH TEST")
  print("=" * 60)
  print()
  
  generator = EmbeddingGenerator()
  vector_db = VectorDB()
  
  # Test queries
  queries = [
    "black dress",
    "leather jacket",
    "blue denim",
    "white shirt",
    "casual wear"
  ]
  
  for query in queries:
    print(f"🔎 Query: '{query}'")
    print("-" * 40)
    
    # Generate query embedding
    query_vector = generator.generate_text_embedding(query)
    
    # Search in vector DB
    results = vector_db.search_similar(
      collection='vintage_text',
      query_vector=query_vector,
      limit=5 
    )
    
    # Show results
    for i, result in enumerate(results):
      print(f"  {i+1}. {result['title'][:60]}")
      print(f"     Score: {result['score']:.3f} | Price: ${result['price']}")
      
    print()
  
def test_product_similarity():
  """Find similar products to existing ones"""
  print("\n" + "=" * 60)
  print("🔄 PRODUCT SIMILARITY TEST")
  print("=" * 60)
  print()

  db = SessionLocal()
  generator = EmbeddingGenerator()
  vector_db = VectorDB()
  
  # Pick a random product
  product = db.query(Product).filter(Product.embedded_at != None).first()
  
  print(f"Source Product: {product.title}")
  print(f"Category: {product.category}")
  print("-" * 40)
  
  # Generate embedding from its text
  text = f"{product.title} {product.description}"
  query_vector = generator.generate_text_embedding(text)
  
  # Find similar products
  results = vector_db.search_similar(
    collection='vintage_text',
    query_vector=query_vector,
    limit=6
  )
  print(f"DEBUG: Got {len(results)} results")
  
  # Show results (skip first which is the source product itself)
  print("Similar products:")
  shown = 0
  for result in results:
    if result.get('product_id') == str(product.id):
      continue # skip source product
    shown += 1
    print(f"  {shown}. {result['title'][:60]}")
    print(f"     Score: {result['score']:.3f} | Price: ${result['price']}")
    
  print()
  db.close()
  
def test_database_verification():
  """Verify database state"""
  print("\n" + "=" * 60)
  print("📊 DATABASE VERIFICATION")
  print("=" * 60)
  print()
  
  db = SessionLocal()
  
  total = db.query(Product).count()
  embedded = db.query(Product).filter(Product.embedded_at != None).count()
  
  print(f"Total products: {total}")
  print(f"Products with embeddings: {embedded}")
  print(f"Coverage: {(embedded/total*100):.1f}%")
  print()
  
  # Show sample
  print("Sample embedded products:")
  products = db.query(Product).filter(Product.embedded_at != None).limit(5).all()
  for p in products:
    print(f"  • {p.title[:50]}")
    
  print()
  db.close()

if __name__ == "__main__":
  print("\n🧪 VINTAGE VESTIGE - SEARCH TESTING")
  
  # Run tests
  test_database_verification()
  test_text_search()
  test_product_similarity()
  
  print("=" * 60)
  print("✅ SEARCH TESTS COMPLETE!")
  print("=" * 60)
  print()