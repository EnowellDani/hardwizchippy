"""
HardWizChippy Scraper Configuration
Performance-optimized settings for multi-source scraping
"""
import os
from pathlib import Path

# Base paths
SCRAPER_ROOT = Path(__file__).parent.parent
DATA_DIR = SCRAPER_ROOT / "data"
CACHE_DIR = DATA_DIR / "cache"
OUTPUT_DIR = DATA_DIR / "output"

# Ensure directories exist
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Database configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "kbitboy"),
    "password": os.getenv("DB_PASSWORD", "danieyl"),
    "database": os.getenv("DB_NAME", "hardwizchippy"),
    "charset": "utf8mb4",
    "use_unicode": True,
    "autocommit": False,
}

# Rate limiting (seconds between requests per source)
RATE_LIMITS = {
    "techpowerup": 1.0,
    "pcpartpicker": 2.0,
    "passmark": 1.5,
    "geekbench": 1.5,
    "cinebench": 1.0,
    "tomshardware": 2.0,
    "default": 1.0
}

# Request timeouts (seconds)
TIMEOUTS = {
    "connect": 10,
    "read": 30,
    "total": 60
}

# Retry configuration
RETRY_CONFIG = {
    "max_retries": 3,
    "backoff_factor": 2.0,
    "retry_on_status": [429, 500, 502, 503, 504],
}

# Cache configuration
CACHE_CONFIG = {
    "enabled": True,
    "ttl_hours": 24,
    "max_size_mb": 500,
    "compression": True
}

# User agents rotation pool
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]

# Request headers
DEFAULT_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
    "DNT": "1",
    "Connection": "keep-alive",
}

# Batch processing
BATCH_CONFIG = {
    "cpu_batch_size": 50,
    "benchmark_batch_size": 100,
    "commit_interval": 100
}

# Logging
LOG_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    "date_format": "%Y-%m-%d %H:%M:%S",
    "file": DATA_DIR / "scraper.log",
    "max_bytes": 10 * 1024 * 1024,
    "backup_count": 5
}
