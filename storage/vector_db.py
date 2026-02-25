from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import os
from dotenv import load_dotenv
import numpy as np

load_dotenv()

class VectorDB:
  """Manage Qdrant vector database"""
  
  def __init__(self):
    host = os.getenv('QDRANT_HOST', 'localhost')
    port = int(os.getenv('QDRANT_PORT', '6333'))
    
    print(f"🔌 Connecting to Qdrant at {host}:{port}...")
    self.client = QdrantClient(host=host, port=port)
    print("✅ Connected\n")
    
    # Collection names
    self.image_collection = 'vintage_images'
    self.text_collection = 'vintage_text'
    
    # Initialize collections
    self._init_collections()
    
  def _init_collections(self):
    """Create collections if they don't exist"""
    collections = [c.name for c in self.client.get_collections().collections]
    
    # Image collection (512-dim CLIP embeddings)
    if self.image_collection not in collections:
      print(f"📦 Creating collection: {self.image_collection}")
      self.client.create_collection(
        collection_name=self.image_collection,
        vectors_config=VectorParams(size=512, distance=Distance.COSINE)
      )
      print("✅ Created!\n")
    else:
      print(f"✅ Collection exists: {self.image_collection}\n")
      
    # Text collection (384-dim text embeddings)
    if self.text_collection not in collections:
      print(f"📦 Creating collection: {self.text_collection}")
      self.client.create_collection(
        collection_name=self.text_collection,
        vectors_config=VectorParams(size=384, distance=Distance.COSINE)
      )
      print("✅ Created!\n")
    else:
      print(f"✅ Collection exists: {self.text_collection}\n")
      
  def upsert_product(self, product_id, embeddings, metadata):
    """
    Store product embeddings in Qdrant
    
    Args:
      product_id: string ID
      embeddings: dict with 'image_embedding' and 'text_embedding'
      metadata: dict with product info
    """
    # Store image embedding
    if embeddings.get('image_embedding') is not None:
      point = PointStruct(
        id=int(product_id),
        vector=embeddings['image_embedding'].tolist(),
        payload=metadata
      )
      self.client.upsert(
        collection_name=self.image_collection,
        points=[point]
      )
    
    # Store text embedding
    if embeddings.get('text_embedding') is not None:
      point = PointStruct(
        id=int(product_id),
        vector=embeddings['text_embedding'].tolist(),
        payload=metadata
      )
      self.client.upsert(
        collection_name=self.text_collection,
        points=[point]
      )
    
  def search_similar(self, collection, query_vector, limit=10, query_filter=None):
    """
    Search for similar items in the vector DB

    Args:
      collection: 'vintage_images' or 'vintage_text'
      query_vector: numpy array of the query embedding
      limit: number of results
      query_filter: optional qdrant_client.models.Filter for pre-filtering
    Returns:
      List of dicts with 'id', 'score', and payload fields
    """
    results = self.client.search(
      collection_name=collection,
      query_vector=query_vector.tolist() if hasattr(query_vector, 'tolist') else query_vector,
      query_filter=query_filter,
      limit=limit
    )
    
    return [
      {
        'id': hit.id,
        'score': hit.score,
        **hit.payload
      }
      for hit in results
    ]
    
  def get_collection_info(self):
    """Get info about collections"""
    info = {}
    for collection in [self.image_collection, self.text_collection]:
      try:
        col_info = self.client.get_collection(collection)
        info[collection] = {
          'vectors_count': col_info.vectors_count,
          'points_count': col_info.points_count
        }
      except:
        info[collection] = {'error': 'Collection not found'}
    return info
  
if __name__ == "__main__":
  # Test Qdrant connection
  print("🧪 Testing Qdrant Connection\n")
  vector_db = VectorDB()
  
  print("📊 Collection Info:")
  info = vector_db.get_collection_info()
  for name, data in info.items():
    print(f"   {name}:")
    for key, value in data.items():
      print(f"      {key}: {value}")
      
  print("\n🎉 Qdrant is ready!")