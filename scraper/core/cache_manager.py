"""
Cache Manager - Disk-based caching for scraped pages
Supports compression, TTL, and size limits
"""
import os
import json
import gzip
import hashlib
import time
from pathlib import Path
from typing import Optional
import logging

from config.settings import CACHE_DIR, CACHE_CONFIG


class CacheManager:
    """
    Disk-based page cache with:
    - URL hash-based file storage
    - Optional gzip compression
    - TTL-based expiration
    - Size limit management
    """
    
    def __init__(self, source_name: str):
        self.source_name = source_name
        self.cache_dir = CACHE_DIR / source_name
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.ttl_seconds = CACHE_CONFIG["ttl_hours"] * 3600
        self.compress = CACHE_CONFIG["compression"]
        self.max_size_bytes = CACHE_CONFIG["max_size_mb"] * 1024 * 1024
        
        self.logger = logging.getLogger(f"cache.{source_name}")
        self._index_file = self.cache_dir / "_index.json"
        self._index = self._load_index()
    
    def _url_to_filename(self, url: str) -> str:
        """Convert URL to cache filename using MD5 hash"""
        url_hash = hashlib.md5(url.encode()).hexdigest()
        ext = ".gz" if self.compress else ".html"
        return f"{url_hash}{ext}"
    
    def _load_index(self) -> dict:
        """Load cache index from disk"""
        if self._index_file.exists():
            try:
                with open(self._index_file, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {}
    
    def _save_index(self):
        """Save cache index to disk"""
        try:
            with open(self._index_file, "w") as f:
                json.dump(self._index, f)
        except IOError as e:
            self.logger.error(f"Failed to save cache index: {e}")
    
    def _is_expired(self, url: str) -> bool:
        """Check if cached item has expired"""
        if url not in self._index:
            return True
        cached_time = self._index[url].get("timestamp", 0)
        return (time.time() - cached_time) > self.ttl_seconds
    
    def get(self, url: str) -> Optional[str]:
        """
        Get cached content for URL
        Returns None if not cached or expired
        """
        if not CACHE_CONFIG["enabled"]:
            return None
        
        if self._is_expired(url):
            return None
        
        filename = self._url_to_filename(url)
        filepath = self.cache_dir / filename
        
        if not filepath.exists():
            return None
        
        try:
            if self.compress:
                with gzip.open(filepath, "rt", encoding="utf-8") as f:
                    return f.read()
            else:
                with open(filepath, "r", encoding="utf-8") as f:
                    return f.read()
        except (IOError, gzip.BadGzipFile) as e:
            self.logger.warning(f"Cache read error for {url}: {e}")
            return None
    
    def set(self, url: str, content: str):
        """Cache content for URL"""
        if not CACHE_CONFIG["enabled"]:
            return
        
        filename = self._url_to_filename(url)
        filepath = self.cache_dir / filename
        
        try:
            if self.compress:
                with gzip.open(filepath, "wt", encoding="utf-8") as f:
                    f.write(content)
            else:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
            
            # Update index
            self._index[url] = {
                "timestamp": time.time(),
                "filename": filename,
                "size": len(content)
            }
            self._save_index()
            
        except IOError as e:
            self.logger.error(f"Cache write error for {url}: {e}")
    
    def delete(self, url: str):
        """Delete cached item"""
        if url in self._index:
            filename = self._index[url].get("filename")
            if filename:
                filepath = self.cache_dir / filename
                try:
                    filepath.unlink(missing_ok=True)
                except IOError:
                    pass
            del self._index[url]
            self._save_index()
    
    def clear(self):
        """Clear all cached items for this source"""
        for url in list(self._index.keys()):
            self.delete(url)
        self._index = {}
        self._save_index()
        self.logger.info(f"Cache cleared for {self.source_name}")
    
    def cleanup_expired(self) -> int:
        """Remove expired cache entries, returns count of removed items"""
        removed = 0
        for url in list(self._index.keys()):
            if self._is_expired(url):
                self.delete(url)
                removed += 1
        return removed
    
    def get_stats(self) -> dict:
        """Get cache statistics"""
        total_size = sum(item.get("size", 0) for item in self._index.values())
        return {
            "source": self.source_name,
            "items": len(self._index),
            "total_size_mb": total_size / (1024 * 1024),
            "max_size_mb": self.max_size_bytes / (1024 * 1024),
            "ttl_hours": self.ttl_seconds / 3600
        }
