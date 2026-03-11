import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from storage.database import SessionLocal, Product

db = SessionLocal()

print("📊 VINTAGE VESTIGE DATABASE")
print("=" * 50)

# Count
count = db.query(Product).count()
print(f"\n📦 Total Products: {count}\n")

# # Show all products
# products = db.query(Product).all()

# for p in products:
#     print(f"ID: {p.id}")
#     print(f"Title: {p.title}")
#     print(f"Price: ${p.price}")
#     print(f"Platform: {p.platform}")
#     print(f"URL: {p.url}")
#     print("-" * 50)

# db.close()