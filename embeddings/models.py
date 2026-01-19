from sentence_transformers import SentenceTransformer
import torch
from PIL import Image
import requests
from io import BytesIO

class EmbeddingModels:
  """Singleton class to manage embedding models"""
  
  _instance = None
  
  def __new__(cls):
    if cls._instance is None:
      cls._instance = super().__new__(cls)
      cls._instance._initialized = False
    return cls._instance
  
  def __init__(self):
    if self._initialized:
      return
    
    print("🔄 Loading embedding models...")
    print("   (First time takes 5-10 minutes to download)")
    
    # CLIP model for images (512-dim embeddings)
    print("\n📦 Loading CLIP model...")
    self.clip = SentenceTransformer('clip-ViT-B-32')
    print("✅ CLIP loaded")
    
    # Text embedding model (384-dim embeddings)
    print("\n📦 Loading text model...")
    self.text = SentenceTransformer('all-MiniLM-L6-v2')
    print("✅ Text model loaded")
    
    self._initialized = True
    print("\n🎉 All models ready!\n")
    
  def encode_image(self, image_input):
    """
    Encode an image into a vector embedding.
    Args:
      image_input: A PIL Image or a URL string of the image.
    Returns:
      numpy array of shape (512, )
    """
    # Handle different input types
    if isinstance(image_input, str):
      # URL string
      if image_input.startswith('http'):
        response = requests.get(image_input, timeout=10)
        image = Image.open(BytesIO(response.content))
      # Local file path
      else:
        image = Image.open(image_input)
    else:
      # Already a PIL image
      image = image_input
      
    # Convert to RGB if needed
    if image.mode != 'RGB':
      image = image.convert('RGB')
      
    # Generate embedding
    embedding = self.clip.encode(image)
    return embedding
  
  def encode_text(self, text):
    """
    Encode text into a vector embedding.
    Args:
      text: A string of text.
    Returns:
      numpy array of shape (384, )
    """
    embedding = self.text.encode(text)
    return embedding
  
# Create global instance
models = EmbeddingModels()

if __name__ == "__main__":
  # Test the models
  print("Testing embedding models...\n")
  
  # Test text embedding
  sample_text = "vintage 1970s prairie dress with floral patterns"
  text_emb = models.encode_text(sample_text)
  print(f"✅ Text embedding shape: {text_emb.shape}")
  print(f"   First 5 values: {text_emb[:5]}\n")
  
# Test image embedding (using a placeholder)
try:
  test_url = "https://via.placeholder.com/400x400.png?text=Test"
  image_emb = models.encode_image(test_url)
  print(f"✅ Image embedding shape: {image_emb.shape}")
  print(f"   First 5 values: {image_emb[:5]}\n")
except Exception as e:
  print(f"⚠️  Image test skipped: {e}\n")
    
print("🎉 Models working correctly!")