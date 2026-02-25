from scrapers.depop import DepopScraper
from storage.database import SessionLocal, Product
import json

def test_scrape_and_store():
    """Test scraping and storing products"""
    
    # 1. Scrape products
    print("🔍 Scraping products...")
    scraper = DepopScraper()
    products_data = scraper.scrape_search_page("vintage dress", page=1)
    
    # 2. Store in database
    print("\n💾 Storing in database...")
    db = SessionLocal()
    
    for product_data in products_data:
        product = Product(**product_data)
        db.add(product)
    
    db.commit()
    print(f"✅ Stored {len(products_data)} products!")
    
    # 3. Verify they're in the database
    print("\n🔍 Verifying...")
    count = db.query(Product).count()
    print(f"✅ Total products in database: {count}")
    
    # 4. Show first product
    first_product = db.query(Product).first()
    print(f"\n📦 First product:")
    print(f"   ID: {first_product.id}")
    print(f"   Title: {first_product.title}")
    print(f"   Price: ${first_product.price}")
    print(f"   Platform: {first_product.platform}")
    
    db.close()
    print("\n🎉 Pipeline test complete!")

if __name__ == '__main__':
    test_scrape_and_store()