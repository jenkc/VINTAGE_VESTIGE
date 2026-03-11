import requests
from bs4 import BeautifulSoup
from scrapers.base import BaseScraper
from typing import List, Dict
import json
import time

class EtsyScraper(BaseScraper):
    """Scrape vintage products from Etsy"""
    
    BASE_URL = "https://www.etsy.com"
    
    def __init__(self):
      super().__init__()
      self.session = requests.Session()  # Use session instead of requests
      self.headers = {
          'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
          'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
          'Accept-Language': 'en-US,en;q=0.9',
          'Accept-Encoding': 'gzip, deflate, br',
          'DNT': '1',
          'Connection': 'keep-alive',
          'Upgrade-Insecure-Requests': '1',
          'Sec-Fetch-Dest': 'document',
          'Sec-Fetch-Mode': 'navigate',
          'Sec-Fetch-Site': 'none',
          'Cache-Control': 'max-age=0',
      }
      self.session.headers.update(self.headers)
      
    def scrape_search_page(self, query: str, page: int = 1) -> List[Dict]:
        """
        Scrape Etsy search results for vintage items
        """
        products = []
        
        # Build search URL
        search_url = f"{self.BASE_URL}/search?q={query.replace(' ', '+')}&explicit=1&page={page}"
        
        print(f"🔍 Scraping: {search_url}")
        
        try:
            response = self.session.get(search_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find product listings
            # Etsy uses data-listing-id attribute
            listings = soup.find_all('div', {'data-appears-component-name': 'search_organic_result'})
            
            if not listings:
                # Try alternative selector
                listings = soup.find_all('li', class_='wt-list-unstyled')[:10]
            
            print(f"📦 Found {len(listings)} listings")
            
            for listing in listings[:10]:  # Limit to 10
                try:
                    product_data = self._extract_product_data(listing, query)
                    if product_data:
                        products.append(product_data)
                        print(f"  ✅ {product_data['title'][:50]}...")
                except Exception as e:
                    print(f"  ⚠️  Error extracting product: {e}")
                    continue
                
                # Be nice to Etsy
                time.sleep(0.5)
            
            print(f"\n✅ Successfully scraped {len(products)} products")
            
        except Exception as e:
            print(f"❌ Error scraping Etsy: {e}")
        
        return products
    
    def _extract_product_data(self, listing, query: str) -> Dict:
        """Extract data from a single listing"""
        
        # Find the link
        link = listing.find('a', class_='listing-link')
        if not link:
            return None
        
        url = link.get('href', '')
        if not url.startswith('http'):
            url = self.BASE_URL + url
        
        # Extract listing ID from URL
        external_id = None
        if '/listing/' in url:
            external_id = url.split('/listing/')[1].split('/')[0].split('?')[0]
        
        if not external_id:
            external_id = f"etsy_{query.replace(' ', '_')}_{hash(url)}"
        
        # Title
        title_elem = listing.find('h3', class_='v2-listing-card__title')
        if not title_elem:
            title_elem = listing.find('h2')
        title = title_elem.get_text(strip=True) if title_elem else f"Vintage {query}"
        
        # Price
        price = 0.0
        price_elem = listing.find('span', class_='currency-value')
        if price_elem:
            price_text = price_elem.get_text(strip=True)
            try:
                price = float(price_text.replace(',', ''))
            except:
                price = 25.0
        
        # Image
        img = listing.find('img', class_='wt-width-full')
        if not img:
            img = listing.find('img')
        
        image_url = None
        if img:
            image_url = img.get('src') or img.get('data-src')
        
        if not image_url:
            image_url = f"https://via.placeholder.com/400x400?text={title[:20]}"
        
        # Seller (harder to get from search page, placeholder for now)
        seller_name = "etsy_seller"
        
        product = {
            'external_id': f'etsy_{external_id}',
            'platform': 'etsy',
            'title': title,
            'description': f'Vintage {query} from Etsy',
            'price': price,
            'currency': 'USD',
            'primary_image': image_url,
            'image_urls': json.dumps([image_url]),
            'seller_name': seller_name,
            'seller_url': f'{self.BASE_URL}/shop/{seller_name}',
            'url': url
        }
        
        return product


if __name__ == '__main__':
    # Test the scraper
    print("🎨 ETSY VINTAGE SCRAPER TEST\n")
    scraper = EtsyScraper()
    products = scraper.scrape_search_page("vintage dress 1970s", page=1)
    
    print(f"\n📊 RESULTS: {len(products)} products scraped\n")
    
    if products:
        print("First product:")
        print(json.dumps(products[0], indent=2))