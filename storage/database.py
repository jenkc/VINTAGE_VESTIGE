from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean
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
    
    # AI enrichment (filled later)
    era = Column(String, nullable=True)  # '1970s', '1980s', etc.
    category = Column(String, nullable=True)  # 'dress', 'jacket', etc.
    style_tags = Column(Text, nullable=True)  # JSON array
    ai_description = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    embedded_at = Column(DateTime, nullable=True)
    enriched_at = Column(DateTime, nullable=True)

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