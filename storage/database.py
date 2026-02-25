from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Product(Base):
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String, unique=True, index=True)  # Depop/Etsy product ID
    platform = Column(String, index=True)  # 'depop', 'etsy', etc.
    
    # Basic info
    title = Column(String)
    description = Column(Text)
    price = Column(Float)
    currency = Column(String, default='USD')
    
    # Images
    primary_image = Column(String)  # URL to main image
    image_urls = Column(Text)  # JSON array of all images
    
    # Seller info
    seller_name = Column(String)
    seller_url = Column(String)
    
    # Product URL
    url = Column(String)
    
    # Original dataset fields
    color = Column(String, nullable=True)
    season = Column(String, nullable=True)
    year = Column(Float, nullable=True)

    # Structured metadata (from source APIs or enrichment)
    era = Column(String, nullable=True)  # Broad era: 'Victorian', 'Art Deco', 'Regency', etc.
    decade = Column(String, nullable=True)  # Specific decade: '1870s', '1920s', etc.
    category = Column(String, nullable=True)  # 'dress', 'jacket', etc.
    style_tags = Column(Text, nullable=True)  # JSON array
    material = Column(String, nullable=True)  # 'silk', 'cotton', 'wool', etc.
    pattern = Column(String, nullable=True)  # 'plaid', 'floral', 'solid', etc.
    garment_type = Column(String, nullable=True)  # 'evening dress', 'coat', etc.
    culture = Column(String, nullable=True)  # 'American', 'French', etc.
    period = Column(String, nullable=True)  # 'Victorian', 'Art Deco', etc.
    object_date = Column(String, nullable=True)  # Raw date string from source (e.g. "ca. 1865")

    # AI enrichment (filled later)
    colors = Column(Text, nullable=True)  # JSON array from enrichment
    vibe = Column(String, nullable=True)
    fit_style = Column(String, nullable=True)
    occasion = Column(String, nullable=True)
    ai_description = Column(Text, nullable=True)
    enriched_text = Column(Text, nullable=True)  # Rich text used for embedding

    # Fashionpedia taxonomy fields (structured, from enrichment)
    fp_category = Column(String, nullable=True)       # Fashionpedia main category: "dress", "jacket", etc.
    silhouette = Column(String, nullable=True)         # "a-line", "fit and flare", "pencil", etc.
    neckline = Column(String, nullable=True)           # "v-neck", "sweetheart", "boat neck", etc.
    waistline = Column(String, nullable=True)          # "empire waistline", "high waist", etc.
    length = Column(String, nullable=True)             # "floor length", "midi", "knee length", etc.
    sleeve_length = Column(String, nullable=True)      # "sleeveless", "three quarter", "wrist-length", etc.
    opening_type = Column(String, nullable=True)       # "single breasted", "zip-up", "wrapping", etc.
    textile_pattern = Column(String, nullable=True)    # "floral", "stripe", "check", "paisley", etc.
    textile_finishing = Column(Text, nullable=True)    # JSON array: ["pleated", "ruched", "cutout"]
    nickname = Column(String, nullable=True)           # Fashionpedia nickname: "blazer", "wrap dress", etc.
    garment_parts = Column(Text, nullable=True)        # JSON array: ["collar", "sleeve", "pocket"]
    decorations = Column(Text, nullable=True)          # JSON array: ["bow", "ruffle", "sequin"]
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    embedded_at = Column(DateTime, nullable=True)
    enriched_at = Column(DateTime, nullable=True)

class StyleBridge(Base):
    __tablename__ = 'style_bridges'

    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey('products.id', ondelete='CASCADE'),
                       nullable=False, index=True)
    target_id = Column(Integer, ForeignKey('products.id', ondelete='CASCADE'),
                       nullable=False, index=True)

    text_similarity = Column(Float, nullable=False)
    image_similarity = Column(Float, nullable=True)
    structural_score = Column(Float, nullable=False)
    bridge_score = Column(Float, nullable=False)

    shared_attributes = Column(Text, nullable=True)  # JSON string
    bridge_type = Column(String, nullable=True)
    bridge_narrative = Column(Text, nullable=True)

    # IIT 4.0 future-proofing (nullable — populated post-MVP)
    phi_score = Column(Float, nullable=True)
    cnn_structural_score = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('source_id', 'target_id', name='uq_bridge_pair'),
    )

def init_db():
    """Create all tables"""
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created!")

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

if __name__ == '__main__':
    init_db()