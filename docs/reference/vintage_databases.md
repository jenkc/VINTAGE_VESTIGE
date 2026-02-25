**Great question!** You have two options: filter the current dataset OR add real vintage datasets.

---

## **Option 1: Filter Current Dataset for "Vintage-Looking" Items**

The fashion dataset has a `year` field. Let's filter for older items:

```python
# filter_vintage_from_dataset.py
from datasets import load_dataset
from collections import defaultdict

def analyze_years():
    """See what years are available in the dataset"""
    
    print("\n📅 ANALYZING PRODUCTION YEARS\n")
    dataset = load_dataset("ashraq/fashion-product-images-small", split="train")
    
    by_year = defaultdict(int)
    items_with_year = 0
    
    for item in dataset:
        year = item.get('year')
        if year and not pd.isna(year):
            by_year[int(year)] += 1
            items_with_year += 1
    
    print(f"Total items: {len(dataset)}")
    print(f"Items with year data: {items_with_year}\n")
    
    print("Year distribution:")
    for year in sorted(by_year.keys()):
        count = by_year[year]
        print(f"   {year}: {count} items")
    
    return dataset, by_year


def filter_vintage_items(dataset, cutoff_year=2010):
    """
    Filter for items that look more vintage
    Criteria:
    - Older production years (pre-2010 for "vintage-inspired")
    - OR specific vintage-friendly article types
    """
    
    vintage_articles = [
        'Dresses', 'Skirts', 'Jackets', 'Coats',
        'Jeans', 'Shirts', 'Blazers', 'Sweaters',
        'Accessories', 'Scarves', 'Belts', 'Bags'
    ]
    
    vintage_indices = []
    
    for idx, item in enumerate(dataset):
        year = item.get('year')
        article = item.get('articleType')
        
        # Filter by year if available
        if year and not pd.isna(year) and int(year) < cutoff_year:
            vintage_indices.append(idx)
        # Or by vintage-friendly article types
        elif article in vintage_articles:
            vintage_indices.append(idx)
    
    print(f"\n✅ Found {len(vintage_indices)} vintage-friendly items")
    return vintage_indices
```

**Problem:** This dataset is modern fashion (2011-2016), not actual vintage. It won't give you 70s prairie dresses or 90s grunge.

---

## **Option 2: Real Vintage Datasets (BETTER!)**

### **🏛️ Museum APIs - FREE, High-Quality Vintage Fashion**

Museums have THOUSANDS of real vintage clothing items with professional photos!

```python
# load_museum_vintage.py
import requests
from storage.database import SessionLocal, Product
import json
import base64
from io import BytesIO
from PIL import Image

class MetMuseumVintageScraper:
    """Get real vintage fashion from The Metropolitan Museum of Art"""
    
    BASE_URL = "https://collectionapi.metmuseum.org/public/collection/v1"
    
    def search_costume_institute(self, query="dress", limit=100):
        """Search the Met's Costume Institute collection"""
        
        print(f"\n🏛️  Searching Met Museum for: {query}")
        
        # Search for objects
        search_url = f"{self.BASE_URL}/search"
        params = {
            'q': query,
            'departmentId': 8,  # The Costume Institute
            'hasImages': 'true'
        }
        
        response = requests.get(search_url, params=params)
        data = response.json()
        
        object_ids = data.get('objectIDs', [])[:limit]
        print(f"✅ Found {len(object_ids)} objects\n")
        
        vintage_items = []
        
        for i, obj_id in enumerate(object_ids, 1):
            print(f"[{i}/{len(object_ids)}] Fetching object {obj_id}...")
            
            # Get object details
            obj_url = f"{self.BASE_URL}/objects/{obj_id}"
            obj_response = requests.get(obj_url)
            obj_data = obj_response.json()
            
            # Extract vintage item data
            item = self._parse_museum_object(obj_data)
            if item:
                vintage_items.append(item)
                print(f"  ✅ {item['title'][:50]}")
            
            # Rate limiting
            import time
            time.sleep(0.5)
        
        return vintage_items
    
    def _parse_museum_object(self, obj):
        """Parse Met Museum object into our product format"""
        
        # Must have image
        if not obj.get('primaryImage'):
            return None
        
        # Extract date (many vintage items!)
        object_date = obj.get('objectDate', '')
        period = obj.get('period', '')
        
        # Skip if too modern (we want vintage!)
        if 'century' not in object_date.lower() and period:
            # Try to extract year
            try:
                year = int(''.join(filter(str.isdigit, object_date[:4])))
                if year > 1990:  # Skip modern items
                    return None
            except:
                pass
        
        title = obj.get('title', 'Vintage Item')
        
        # Build rich description
        desc_parts = []
        if period:
            desc_parts.append(f"Period: {period}")
        if object_date:
            desc_parts.append(f"Date: {object_date}")
        if obj.get('culture'):
            desc_parts.append(f"Culture: {obj.get('culture')}")
        if obj.get('medium'):
            desc_parts.append(f"Materials: {obj.get('medium')}")
        
        description = " | ".join(desc_parts) if desc_parts else "Historical fashion item"
        
        # Download image
        try:
            img_response = requests.get(obj['primaryImage'], timeout=10)
            pil_image = Image.open(BytesIO(img_response.content))
            
            # Convert to data URL
            buffered = BytesIO()
            pil_image.save(buffered, format="JPEG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            image_data_url = f"data:image/jpeg;base64,{img_str}"
        except:
            return None
        
        # Extract era from date
        era = self._extract_era(object_date, period)
        
        return {
            'external_id': f'met_{obj.get("objectID")}',
            'platform': 'met_museum',
            'title': title[:255],
            'description': description[:500],
            'price': 0.0,  # Museum items, no price
            'currency': 'USD',
            'primary_image': image_data_url,
            'image_urls': json.dumps([image_data_url]),
            'seller_name': 'Metropolitan Museum',
            'seller_url': obj.get('objectURL', 'https://www.metmuseum.org'),
            'url': obj.get('objectURL', 'https://www.metmuseum.org'),
            'category': obj.get('objectName', 'clothing'),
            'era': era,
            'style_tags': json.dumps([period, obj.get('culture', '')])
        }
    
    def _extract_era(self, object_date, period):
        """Extract era from date string"""
        
        if '1920' in object_date:
            return '1920s'
        elif '1930' in object_date:
            return '1930s'
        elif '1940' in object_date:
            return '1940s'
        elif '1950' in object_date:
            return '1950s'
        elif '1960' in object_date:
            return '1960s'
        elif '1970' in object_date:
            return '1970s'
        elif '1980' in object_date:
            return '1980s'
        elif '19th century' in object_date.lower():
            return '1800s'
        elif period:
            return period
        
        return None


def load_met_museum_vintage(num_items=200):
    """Load vintage items from Met Museum"""
    
    print("\n" + "=" * 70)
    print("🏛️  LOADING REAL VINTAGE FROM MET MUSEUM")
    print("=" * 70)
    
    scraper = MetMuseumVintageScraper()
    
    # Search for different vintage categories
    queries = [
        'dress', 'coat', 'jacket', 'skirt', 
        'blouse', 'gown', 'suit', 'accessories'
    ]
    
    all_items = []
    items_per_query = num_items // len(queries)
    
    for query in queries:
        items = scraper.search_costume_institute(query, limit=items_per_query)
        all_items.extend(items)
    
    # Load to database
    db = SessionLocal()
    stored = 0
    
    for item in all_items:
        try:
            product = Product(**item)
            db.add(product)
            stored += 1
            
            if stored % 10 == 0:
                db.commit()
        except Exception as e:
            print(f"Error storing: {e}")
    
    db.commit()
    db.close()
    
    print(f"\n✅ Loaded {stored} REAL vintage items from Met Museum!")
    print("\n📊 These are authentic historical pieces!")


if __name__ == '__main__':
    load_met_museum_vintage(num_items=200)
```

---

## **Other Real Vintage Sources:**

### **1. Victoria & Albert Museum (V&A)**
```python
# V&A has 14,000+ fashion items
V_AND_A_API = "https://api.vam.ac.uk/v2/objects/search"
params = {
    'q': 'dress',
    'images_exist': 1,
    'page_size': 100
}
```

### **2. Europeana Fashion**
- API: https://pro.europeana.eu/page/apis
- 1M+ historical fashion items from European museums

### **3. Rijksmuseum**
- API: https://data.rijksmuseum.nl/
- Dutch historical clothing

---

## **My Recommendation:**

### **Week 1 (Tomorrow): Test with Fashion Dataset**
- Use the 500 diverse items you're pulling tomorrow
- This validates your AI pipeline works
- Cost: $10

### **Week 2: Add Real Vintage**
```python
# Hybrid approach - best of both worlds
1. Keep 500 modern fashion (AI enrichment works great)
2. Add 200 Met Museum items (REAL vintage, free!)
3. Add 300 Etsy scraped vintage (actual market prices)

Total: 1000 products
- 500 modern (good for testing AI)
- 200 museum (authentic vintage)
- 300 scraped (real marketplace)
```

### **Week 3+: Scale to 5,000**
- Museum APIs: 1,000 items (free, authentic)
- Etsy scraping: 2,000 items (real vintage market)
- Depop scraping: 2,000 items (affordable vintage)

---

**For tomorrow**, stick with your plan (500 diverse from fashion dataset). This validates your pipeline.

**Next week**, add museum APIs for REAL vintage pieces. The Met Museum API is completely free and has thousands of authentic vintage items!

Want me to write the complete Met Museum scraper for you to run next week?