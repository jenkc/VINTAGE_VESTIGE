from abc import ABC, abstractmethod
from typing import List, Dict
import time

class BaseScraper(ABC):
    """Base class for all scrapers"""
    
    def __init__(self):
        self.session = None
    
    @abstractmethod
    def scrape_search_page(self, query: str, page: int = 1) -> List[Dict]:
        """
        Scrape a search results page
        Returns list of product dictionaries
        """
        pass
    
    def rate_limit(self, seconds: float = 1.0):
        """Be nice to the servers"""
        time.sleep(seconds)