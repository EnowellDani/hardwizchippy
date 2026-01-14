"""
Base Scraper - Abstract base class for all scrapers
Provides session management, rate limiting, caching, and error handling
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Generator
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
import random
import time
import logging
import hashlib
from datetime import datetime

from config.settings import (
    USER_AGENTS, DEFAULT_HEADERS, TIMEOUTS, 
    RETRY_CONFIG, RATE_LIMITS
)
from core.rate_limiter import RateLimiter
from core.cache_manager import CacheManager


class BaseScraper(ABC):
    """
    Abstract base class providing:
    - Session management with retry logic
    - Rate limiting (configurable per source)
    - Progress tracking for resumability
    - Caching mechanism
    - Error handling and logging
    """
    
    def __init__(self, source_name: str, use_cache: bool = True):
        self.source_name = source_name
        self.logger = logging.getLogger(f"scraper.{source_name}")
        
        # Initialize components
        self.session = self._create_session()
        self.rate_limiter = RateLimiter(RATE_LIMITS.get(source_name, RATE_LIMITS["default"]))
        self.cache = CacheManager(source_name) if use_cache else None
        
        # Statistics
        self.stats = {
            "requests": 0,
            "cache_hits": 0,
            "errors": 0,
            "items_processed": 0,
            "start_time": None,
            "last_item": None
        }
    
    def _create_session(self) -> requests.Session:
        """Create a requests session with retry logic"""
        session = requests.Session()
        
        # Configure retries
        retry_strategy = Retry(
            total=RETRY_CONFIG["max_retries"],
            backoff_factor=RETRY_CONFIG["backoff_factor"],
            status_forcelist=RETRY_CONFIG["retry_on_status"],
            allowed_methods=["GET", "HEAD"]
        )
        
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=20
        )
        
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set default headers
        session.headers.update(DEFAULT_HEADERS)
        
        return session
    
    def _get_random_user_agent(self) -> str:
        """Get a random user agent for request rotation"""
        return random.choice(USER_AGENTS)
    
    def _make_request(self, url: str, use_cache: bool = True) -> Optional[str]:
        """
        Make an HTTP request with rate limiting and caching
        Returns HTML content or None on failure
        """
        # Check cache first
        if use_cache and self.cache:
            cached = self.cache.get(url)
            if cached:
                self.stats["cache_hits"] += 1
                return cached
        
        # Rate limit
        self.rate_limiter.wait()
        
        try:
            # Rotate user agent
            headers = {"User-Agent": self._get_random_user_agent()}
            
            response = self.session.get(
                url,
                headers=headers,
                timeout=(TIMEOUTS["connect"], TIMEOUTS["read"])
            )
            response.raise_for_status()
            
            self.stats["requests"] += 1
            content = response.text
            
            # Cache the response
            if use_cache and self.cache:
                self.cache.set(url, content)
            
            return content
            
        except requests.RequestException as e:
            self.stats["errors"] += 1
            self.logger.error(f"Request failed for {url}: {e}")
            return None
    
    def get_soup(self, url: str, use_cache: bool = True) -> Optional[BeautifulSoup]:
        """Fetch URL and return BeautifulSoup object"""
        html = self._make_request(url, use_cache)
        if html:
            return BeautifulSoup(html, "lxml")
        return None
    
    @abstractmethod
    def scrape_list(self) -> Generator[Dict[str, Any], None, None]:
        """
        Scrape list of items (e.g., CPU list page)
        Yields dictionaries with basic item info
        """
        pass
    
    @abstractmethod
    def scrape_detail(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Scrape detailed information from item page
        Returns dictionary with all available specs
        """
        pass
    
    def run(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Main entry point - runs the scraper
        Optionally limit number of items to scrape
        """
        self.stats["start_time"] = datetime.now()
        self.logger.info(f"Starting {self.source_name} scraper")
        
        results = []
        count = 0
        
        try:
            for item in self.scrape_list():
                if limit and count >= limit:
                    break
                
                # Get detailed info if URL available
                if "url" in item:
                    detail = self.scrape_detail(item["url"])
                    if detail:
                        item.update(detail)
                
                results.append(item)
                self.stats["items_processed"] += 1
                self.stats["last_item"] = item.get("name", "unknown")
                count += 1
                
                if count % 50 == 0:
                    self.logger.info(f"Processed {count} items")
        
        except KeyboardInterrupt:
            self.logger.warning("Scraping interrupted by user")
        
        finally:
            elapsed = (datetime.now() - self.stats["start_time"]).total_seconds()
            self.logger.info(
                f"Completed: {self.stats["items_processed"]} items, "
                f"{self.stats["requests"]} requests, "
                f"{self.stats["cache_hits"]} cache hits, "
                f"{self.stats["errors"]} errors, "
                f"{elapsed:.1f}s elapsed"
            )
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Return scraper statistics"""
        return self.stats.copy()
