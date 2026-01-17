"""
=============================================================================
HardWizChippy - Mega Merger v1.0
"The Triple-Threat Merge" Data Pipeline
=============================================================================

A sophisticated multi-source CPU data scraper that merges:
  - Source A: TechPowerUp (Nerd Specs: Transistors, Die Size, MCM, Voltage)
  - Source B: NanoReview (Benchmarks & Gaming FPS)
  - Source C: Intel ARK / AMD (General Info: Launch Price, Memory Type)

Features:
  - Playwright for JavaScript-rendered pages
  - TheFuzz for intelligent name matching across sources
  - Incremental scraping with state persistence
  - NULL fallback strategy for missing data

Usage:
  python mega_merger.py                    # Full pipeline
  python mega_merger.py --source nanoreview  # Single source
  python mega_merger.py --modern-only      # Only 2020-2026 CPUs
  python mega_merger.py --export           # Export to JSON

Author: KBitWare Project
Date: January 2026
=============================================================================
"""

import asyncio
import json
import re
import logging
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from urllib.parse import urljoin, quote

# Third-party imports
import mysql.connector
from mysql.connector import Error as MySQLError
from thefuzz import fuzz, process
from playwright.async_api import async_playwright, Page, Browser, TimeoutError as PlaywrightTimeout
from tqdm import tqdm
from tenacity import retry, stop_after_attempt, wait_exponential

# =============================================================================
# CONFIGURATION
# =============================================================================

DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'kbitboy',
    'password': 'danieyl',
    'database': 'hardwizchippy',
    'charset': 'utf8mb4',
    'use_unicode': True
}

# Source URLs
SOURCES = {
    'nanoreview': {
        'base_url': 'https://nanoreview.net',
        'cpu_list': 'https://nanoreview.net/en/cpu-list/rating',
        'cpu_detail': 'https://nanoreview.net/en/cpu/{slug}'
    },
    'techpowerup': {
        'base_url': 'https://www.techpowerup.com',
        'cpu_list': 'https://www.techpowerup.com/cpu-specs/',
        'search': 'https://www.techpowerup.com/cpu-specs/?ajaxsrch={query}'
    },
    'intel_ark': {
        'base_url': 'https://ark.intel.com',
        'search': 'https://ark.intel.com/content/www/us/en/ark/search.html?_charset_=UTF-8&q={query}'
    },
    'amd': {
        'base_url': 'https://www.amd.com',
        'processors': 'https://www.amd.com/en/products/processors/consumer/ryzen.html'
    }
}

# Scraping config
SCRAPE_CONFIG = {
    'max_cpus': 200,                    # Top 200 modern CPUs focus
    'min_launch_year': 2020,            # Focus on modern CPUs
    'fuzzy_match_threshold': 85,        # Minimum match score (0-100)
    'page_timeout_ms': 30000,
    'request_delay_sec': 1.5,           # Be nice to servers
    'retry_attempts': 3
}

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    handlers=[
        logging.FileHandler('mega_merger.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('MegaMerger')

# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class CpuBasicInfo:
    """Basic CPU info from initial list scrape."""
    name: str
    url: str
    source: str
    manufacturer: str = ''
    release_year: Optional[int] = None
    
@dataclass
class CpuNerdSpecs:
    """TechPowerUp 'Nerd Specs' - The Big Part data."""
    transistors_million: Optional[int] = None
    die_size_mm2: Optional[float] = None
    is_mcm: bool = False
    mcm_chiplet_count: Optional[int] = None
    mcm_config: Optional[str] = None
    voltage_range: Optional[str] = None
    max_voltage: Optional[float] = None
    min_voltage: Optional[float] = None
    process_node: Optional[str] = None
    foundry: Optional[str] = None
    
@dataclass
class CpuBenchmarks:
    """Benchmark data from NanoReview/NotebookCheck."""
    # Cinebench R23
    cinebench_r23_single: Optional[int] = None
    cinebench_r23_multi: Optional[int] = None
    # Cinebench R24
    cinebench_r24_single: Optional[int] = None
    cinebench_r24_multi: Optional[int] = None
    # Geekbench 6
    geekbench6_single: Optional[int] = None
    geekbench6_multi: Optional[int] = None
    # PassMark
    passmark_single: Optional[int] = None
    passmark_multi: Optional[int] = None
    # 3DMark
    _3dmark_timespy_cpu: Optional[int] = None
    
@dataclass
class CpuGaming:
    """Gaming performance data from NanoReview."""
    resolution: str = '1080p'
    gpu_used: Optional[str] = None
    avg_fps: Optional[float] = None
    fps_1_percent: Optional[float] = None
    fps_01_percent: Optional[float] = None
    gaming_score: Optional[int] = None

@dataclass
class CpuGeneralInfo:
    """General info from Intel ARK / AMD."""
    launch_date: Optional[str] = None
    launch_quarter: Optional[str] = None
    launch_msrp: Optional[float] = None
    memory_type: Optional[str] = None
    memory_channels: Optional[int] = None
    max_memory_gb: Optional[int] = None
    product_code: Optional[str] = None
    
@dataclass 
class MergedCpu:
    """Complete merged CPU data from all sources."""
    name: str
    name_normalized: str
    manufacturer: str = ''
    
    # Core specs
    cores_total: Optional[int] = None
    threads_total: Optional[int] = None
    base_clock_ghz: Optional[float] = None
    boost_clock_ghz: Optional[float] = None
    
    # Nerd specs (TechPowerUp)
    nerd_specs: CpuNerdSpecs = field(default_factory=CpuNerdSpecs)
    
    # Benchmarks (NanoReview)
    benchmarks: CpuBenchmarks = field(default_factory=CpuBenchmarks)
    
    # Gaming (NanoReview)
    gaming: CpuGaming = field(default_factory=CpuGaming)
    
    # General (Intel ARK / AMD)
    general: CpuGeneralInfo = field(default_factory=CpuGeneralInfo)
    
    # Source URLs
    techpowerup_url: Optional[str] = None
    nanoreview_url: Optional[str] = None
    ark_url: Optional[str] = None
    
    # Match scores
    tpu_match_score: int = 0
    ark_match_score: int = 0


# =============================================================================
# NAME NORMALIZATION & FUZZY MATCHING
# =============================================================================

class NameMatcher:
    """Intelligent CPU name matching using TheFuzz."""
    
    # Common prefixes/suffixes to strip for better matching
    STRIP_PATTERNS = [
        r'^intel\s+',
        r'^amd\s+',
        r'^apple\s+',
        r'\s+processor$',
        r'\s+cpu$',
        r'\s+with\s+.*$',  # Remove "with Radeon Graphics" etc.
    ]
    
    # Canonical name mappings
    NAME_FIXES = {
        'core ultra 9': 'intel core ultra 9',
        'core ultra 7': 'intel core ultra 7',
        'core ultra 5': 'intel core ultra 5',
        'ryzen 9 9': 'amd ryzen 9 9',
        'ryzen 7 9': 'amd ryzen 7 9',
        'ryzen 5 9': 'amd ryzen 5 9',
    }
    
    @staticmethod
    def normalize(name: str) -> str:
        """Normalize CPU name for matching."""
        if not name:
            return ''
        
        normalized = name.lower().strip()
        
        # Apply strip patterns
        for pattern in NameMatcher.STRIP_PATTERNS:
            normalized = re.sub(pattern, '', normalized, flags=re.IGNORECASE)
        
        # Remove extra whitespace
        normalized = ' '.join(normalized.split())
        
        # Remove special characters but keep alphanumeric
        normalized = re.sub(r'[^\w\s]', '', normalized)
        
        return normalized.strip()
    
    @staticmethod
    def extract_key_parts(name: str) -> Dict[str, Any]:
        """Extract key identifying parts from CPU name."""
        name_lower = name.lower()
        
        parts = {
            'manufacturer': None,
            'family': None,
            'tier': None,
            'model_number': None,
            'suffix': None
        }
        
        # Detect manufacturer
        if 'intel' in name_lower or 'core' in name_lower:
            parts['manufacturer'] = 'Intel'
        elif 'amd' in name_lower or 'ryzen' in name_lower or 'epyc' in name_lower:
            parts['manufacturer'] = 'AMD'
        elif 'apple' in name_lower or 'm1' in name_lower or 'm2' in name_lower or 'm3' in name_lower or 'm4' in name_lower:
            parts['manufacturer'] = 'Apple'
            
        # Extract model number (e.g., 9950X, 14900K, 285K)
        model_match = re.search(r'(\d{3,5}[A-Z]*)', name, re.IGNORECASE)
        if model_match:
            parts['model_number'] = model_match.group(1).upper()
            
        # Detect tier (i3, i5, i7, i9, Ryzen 3/5/7/9)
        tier_match = re.search(r'(i[3579]|ryzen\s*[3579]|ultra\s*[579])', name_lower)
        if tier_match:
            parts['tier'] = tier_match.group(1)
            
        return parts
    
    @staticmethod
    def match_best(query: str, candidates: List[str], threshold: int = 85) -> Tuple[Optional[str], int]:
        """
        Find best matching CPU name from candidates.
        
        Returns:
            Tuple of (best_match, score) or (None, 0) if no match found
        """
        if not query or not candidates:
            return None, 0
        
        query_normalized = NameMatcher.normalize(query)
        query_parts = NameMatcher.extract_key_parts(query)
        
        # First, try exact normalized match
        for candidate in candidates:
            if NameMatcher.normalize(candidate) == query_normalized:
                return candidate, 100
        
        # Use TheFuzz for fuzzy matching
        # Try multiple strategies and take the best
        
        best_match = None
        best_score = 0
        
        for candidate in candidates:
            candidate_normalized = NameMatcher.normalize(candidate)
            candidate_parts = NameMatcher.extract_key_parts(candidate)
            
            # Strategy 1: Token sort ratio (handles word order differences)
            score1 = fuzz.token_sort_ratio(query_normalized, candidate_normalized)
            
            # Strategy 2: Token set ratio (handles extra words)
            score2 = fuzz.token_set_ratio(query_normalized, candidate_normalized)
            
            # Strategy 3: Partial ratio (handles substring matches)
            score3 = fuzz.partial_ratio(query_normalized, candidate_normalized)
            
            # Weighted average
            score = (score1 * 0.4 + score2 * 0.4 + score3 * 0.2)
            
            # Bonus points for matching key parts
            if query_parts['model_number'] and query_parts['model_number'] == candidate_parts['model_number']:
                score += 15
            if query_parts['manufacturer'] and query_parts['manufacturer'] == candidate_parts['manufacturer']:
                score += 5
            if query_parts['tier'] and query_parts['tier'] == candidate_parts['tier']:
                score += 5
                
            # Cap at 100
            score = min(score, 100)
            
            if score > best_score:
                best_score = score
                best_match = candidate
        
        if best_score >= threshold:
            return best_match, int(best_score)
        
        return None, 0
    
    @staticmethod
    def batch_match(queries: List[str], candidates: List[str], threshold: int = 85) -> Dict[str, Tuple[str, int]]:
        """Match multiple queries against candidates."""
        results = {}
        
        for query in tqdm(queries, desc="Fuzzy matching"):
            match, score = NameMatcher.match_best(query, candidates, threshold)
            if match:
                results[query] = (match, score)
                
        return results


# =============================================================================
# DATABASE MANAGER
# =============================================================================

class DatabaseManager:
    """Handles all MySQL database operations."""
    
    def __init__(self, config: Dict = None):
        self.config = config or DB_CONFIG
        self.conn = None
        self.cursor = None
        self._manufacturer_cache = {}
        self._socket_cache = {}
        
    def connect(self) -> bool:
        """Establish database connection."""
        try:
            self.conn = mysql.connector.connect(**self.config)
            self.cursor = self.conn.cursor(dictionary=True)
            self._load_caches()
            logger.info("✅ Database connected")
            return True
        except MySQLError as e:
            logger.error(f"❌ Database connection failed: {e}")
            return False
    
    def _load_caches(self):
        """Load lookup tables into memory."""
        try:
            self.cursor.execute("SELECT id, LOWER(name) as name FROM manufacturers")
            for row in self.cursor.fetchall():
                self._manufacturer_cache[row['name']] = row['id']
                
            self.cursor.execute("SELECT id, LOWER(name) as name FROM sockets")
            for row in self.cursor.fetchall():
                self._socket_cache[row['name']] = row['id']
        except:
            pass
    
    def close(self):
        """Close database connection."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        logger.info("Database connection closed")
    
    def get_manufacturer_id(self, name: str) -> Optional[int]:
        """Get or create manufacturer ID."""
        if not name:
            return self._manufacturer_cache.get('other')
            
        key = name.lower().strip()
        
        if key in self._manufacturer_cache:
            return self._manufacturer_cache[key]
        
        try:
            self.cursor.execute(
                "INSERT INTO manufacturers (name) VALUES (%s) ON DUPLICATE KEY UPDATE id=LAST_INSERT_ID(id)",
                (name,)
            )
            self.conn.commit()
            mid = self.cursor.lastrowid
            self._manufacturer_cache[key] = mid
            return mid
        except MySQLError:
            return self._manufacturer_cache.get('other')
    
    def get_socket_id(self, name: str, manufacturer_id: int) -> Optional[int]:
        """Get or create socket ID."""
        if not name:
            return None
            
        key = name.lower().strip()
        
        if key in self._socket_cache:
            return self._socket_cache[key]
        
        try:
            self.cursor.execute(
                "INSERT INTO sockets (name, manufacturer_id) VALUES (%s, %s) ON DUPLICATE KEY UPDATE id=LAST_INSERT_ID(id)",
                (name, manufacturer_id)
            )
            self.conn.commit()
            sid = self.cursor.lastrowid
            self._socket_cache[key] = sid
            return sid
        except MySQLError:
            return None
    
    def get_all_cpu_names(self) -> List[str]:
        """Get all CPU names in database for fuzzy matching."""
        try:
            self.cursor.execute("SELECT name FROM cpus")
            return [row['name'] for row in self.cursor.fetchall()]
        except:
            return []
    
    def cpu_exists(self, name: str) -> Optional[int]:
        """Check if CPU exists, return ID if found."""
        try:
            self.cursor.execute("SELECT id FROM cpus WHERE name = %s", (name,))
            result = self.cursor.fetchone()
            return result['id'] if result else None
        except:
            return None
    
    def save_merged_cpu(self, cpu: MergedCpu) -> Tuple[str, int]:
        """
        Save or update merged CPU data.
        
        Returns:
            Tuple of (action, cpu_id) where action is 'inserted', 'updated', or 'failed'
        """
        try:
            manufacturer_id = self.get_manufacturer_id(cpu.manufacturer)
            existing_id = self.cpu_exists(cpu.name)
            
            if existing_id:
                # Update existing
                self._update_cpu(existing_id, cpu, manufacturer_id)
                return 'updated', existing_id
            else:
                # Insert new
                cpu_id = self._insert_cpu(cpu, manufacturer_id)
                return 'inserted', cpu_id
                
        except MySQLError as e:
            logger.error(f"Failed to save CPU {cpu.name}: {e}")
            self.conn.rollback()
            return 'failed', 0
    
    def _insert_cpu(self, cpu: MergedCpu, manufacturer_id: int) -> int:
        """Insert new CPU record."""
        sql = """
            INSERT INTO cpus (
                name, name_normalized, manufacturer_id,
                cores_total, threads_total, base_clock_ghz, boost_clock_ghz,
                transistors_million, die_size_mm2, is_mcm, mcm_chiplet_count, mcm_config,
                voltage_range, max_voltage, min_voltage,
                process_node, foundry,
                launch_date, launch_quarter, launch_msrp,
                memory_type, memory_channels, max_memory_gb, product_code,
                techpowerup_url, nanoreview_url, intel_ark_url,
                techpowerup_scraped_at, nanoreview_scraped_at
            ) VALUES (
                %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s,
                %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s
            )
        """
        
        now = datetime.now()
        values = (
            cpu.name, cpu.name_normalized, manufacturer_id,
            cpu.cores_total, cpu.threads_total, cpu.base_clock_ghz, cpu.boost_clock_ghz,
            cpu.nerd_specs.transistors_million, cpu.nerd_specs.die_size_mm2,
            cpu.nerd_specs.is_mcm, cpu.nerd_specs.mcm_chiplet_count, cpu.nerd_specs.mcm_config,
            cpu.nerd_specs.voltage_range, cpu.nerd_specs.max_voltage, cpu.nerd_specs.min_voltage,
            cpu.nerd_specs.process_node, cpu.nerd_specs.foundry,
            cpu.general.launch_date, cpu.general.launch_quarter, cpu.general.launch_msrp,
            cpu.general.memory_type, cpu.general.memory_channels, cpu.general.max_memory_gb, cpu.general.product_code,
            cpu.techpowerup_url, cpu.nanoreview_url, cpu.ark_url,
            now if cpu.techpowerup_url else None,
            now if cpu.nanoreview_url else None
        )
        
        self.cursor.execute(sql, values)
        self.conn.commit()
        cpu_id = self.cursor.lastrowid
        
        # Save benchmarks
        if cpu.benchmarks:
            self._save_benchmarks(cpu_id, cpu.benchmarks)
            
        # Save gaming
        if cpu.gaming and cpu.gaming.avg_fps:
            self._save_gaming(cpu_id, cpu.gaming)
            
        return cpu_id
    
    def _update_cpu(self, cpu_id: int, cpu: MergedCpu, manufacturer_id: int):
        """Update existing CPU with non-NULL values only."""
        updates = []
        values = []
        
        # Only update fields that have values
        field_map = {
            'cores_total': cpu.cores_total,
            'threads_total': cpu.threads_total,
            'base_clock_ghz': cpu.base_clock_ghz,
            'boost_clock_ghz': cpu.boost_clock_ghz,
            'transistors_million': cpu.nerd_specs.transistors_million,
            'die_size_mm2': cpu.nerd_specs.die_size_mm2,
            'is_mcm': cpu.nerd_specs.is_mcm if cpu.nerd_specs.is_mcm else None,
            'mcm_chiplet_count': cpu.nerd_specs.mcm_chiplet_count,
            'mcm_config': cpu.nerd_specs.mcm_config,
            'voltage_range': cpu.nerd_specs.voltage_range,
            'process_node': cpu.nerd_specs.process_node,
            'foundry': cpu.nerd_specs.foundry,
            'launch_msrp': cpu.general.launch_msrp,
            'memory_type': cpu.general.memory_type,
            'techpowerup_url': cpu.techpowerup_url,
            'nanoreview_url': cpu.nanoreview_url,
            'intel_ark_url': cpu.ark_url,
        }
        
        for field, value in field_map.items():
            if value is not None:
                updates.append(f"{field} = %s")
                values.append(value)
        
        if updates:
            sql = f"UPDATE cpus SET {', '.join(updates)} WHERE id = %s"
            values.append(cpu_id)
            self.cursor.execute(sql, values)
            self.conn.commit()
        
        # Update benchmarks
        if cpu.benchmarks:
            self._save_benchmarks(cpu_id, cpu.benchmarks)
            
        # Update gaming
        if cpu.gaming and cpu.gaming.avg_fps:
            self._save_gaming(cpu_id, cpu.gaming)
    
    def _save_benchmarks(self, cpu_id: int, benchmarks: CpuBenchmarks):
        """Save or update benchmark data."""
        sql = """
            INSERT INTO cpu_benchmarks (
                cpu_id,
                cinebench_r23_single, cinebench_r23_multi,
                cinebench_r24_single, cinebench_r24_multi,
                geekbench6_single, geekbench6_multi,
                passmark_single, passmark_multi,
                _3dmark_timespy_cpu,
                source, benchmark_date
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            ) ON DUPLICATE KEY UPDATE
                cinebench_r23_single = COALESCE(VALUES(cinebench_r23_single), cinebench_r23_single),
                cinebench_r23_multi = COALESCE(VALUES(cinebench_r23_multi), cinebench_r23_multi),
                cinebench_r24_single = COALESCE(VALUES(cinebench_r24_single), cinebench_r24_single),
                cinebench_r24_multi = COALESCE(VALUES(cinebench_r24_multi), cinebench_r24_multi),
                geekbench6_single = COALESCE(VALUES(geekbench6_single), geekbench6_single),
                geekbench6_multi = COALESCE(VALUES(geekbench6_multi), geekbench6_multi),
                passmark_single = COALESCE(VALUES(passmark_single), passmark_single),
                passmark_multi = COALESCE(VALUES(passmark_multi), passmark_multi),
                _3dmark_timespy_cpu = COALESCE(VALUES(_3dmark_timespy_cpu), _3dmark_timespy_cpu),
                updated_at = CURRENT_TIMESTAMP
        """
        
        values = (
            cpu_id,
            benchmarks.cinebench_r23_single, benchmarks.cinebench_r23_multi,
            benchmarks.cinebench_r24_single, benchmarks.cinebench_r24_multi,
            benchmarks.geekbench6_single, benchmarks.geekbench6_multi,
            benchmarks.passmark_single, benchmarks.passmark_multi,
            benchmarks._3dmark_timespy_cpu,
            'nanoreview', datetime.now().date()
        )
        
        self.cursor.execute(sql, values)
        self.conn.commit()
    
    def _save_gaming(self, cpu_id: int, gaming: CpuGaming):
        """Save or update gaming performance data."""
        sql = """
            INSERT INTO cpu_gaming_aggregate (
                cpu_id, test_resolution, test_gpu,
                avg_fps, fps_1_percent, fps_01_percent, gaming_score,
                source
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s
            ) ON DUPLICATE KEY UPDATE
                avg_fps = COALESCE(VALUES(avg_fps), avg_fps),
                fps_1_percent = COALESCE(VALUES(fps_1_percent), fps_1_percent),
                fps_01_percent = COALESCE(VALUES(fps_01_percent), fps_01_percent),
                gaming_score = COALESCE(VALUES(gaming_score), gaming_score),
                updated_at = CURRENT_TIMESTAMP
        """
        
        values = (
            cpu_id, gaming.resolution, gaming.gpu_used,
            gaming.avg_fps, gaming.fps_1_percent, gaming.fps_01_percent, gaming.gaming_score,
            'nanoreview'
        )
        
        self.cursor.execute(sql, values)
        self.conn.commit()
    
    def update_scraper_state(self, source: str, status: str, cpus_scraped: int = 0, error: str = None):
        """Update scraper state tracking."""
        try:
            sql = """
                UPDATE scraper_state 
                SET status = %s, total_cpus_scraped = total_cpus_scraped + %s, 
                    last_run_at = CURRENT_TIMESTAMP, error_message = %s
                WHERE source_name = %s
            """
            self.cursor.execute(sql, (status, cpus_scraped, error, source))
            self.conn.commit()
        except:
            pass
    
    def cache_fuzzy_match(self, source_name: str, source_site: str, cpu_id: int, score: int):
        """Cache a fuzzy match result for faster future lookups."""
        try:
            sql = """
                INSERT INTO fuzzy_match_cache (source_name, source_site, matched_cpu_id, match_score)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE matched_cpu_id = VALUES(matched_cpu_id), match_score = VALUES(match_score)
            """
            self.cursor.execute(sql, (source_name, source_site, cpu_id, score))
            self.conn.commit()
        except:
            pass
    
    def get_cached_match(self, source_name: str, source_site: str) -> Optional[int]:
        """Get cached fuzzy match result."""
        try:
            sql = "SELECT matched_cpu_id FROM fuzzy_match_cache WHERE source_name = %s AND source_site = %s"
            self.cursor.execute(sql, (source_name, source_site))
            result = self.cursor.fetchone()
            return result['matched_cpu_id'] if result else None
        except:
            return None


# =============================================================================
# SCRAPERS
# =============================================================================

class NanoReviewScraper:
    """Scraper for NanoReview - Benchmarks & Gaming FPS."""
    
    def __init__(self, browser: Browser):
        self.browser = browser
        self.base_url = SOURCES['nanoreview']['base_url']
        
    async def get_top_cpus(self, limit: int = 200) -> List[CpuBasicInfo]:
        """Scrape the top CPU list from NanoReview rating page."""
        logger.info(f"📋 Fetching top {limit} CPUs from NanoReview...")
        
        page = await self.browser.new_page()
        cpus = []
        
        try:
            await page.goto(SOURCES['nanoreview']['cpu_list'], timeout=SCRAPE_CONFIG['page_timeout_ms'])
            await page.wait_for_selector('.rating-table', timeout=10000)
            
            # Get all CPU rows
            rows = await page.query_selector_all('.rating-table tbody tr')
            
            for row in rows[:limit]:
                try:
                    # Get name and link
                    name_elem = await row.query_selector('td:nth-child(2) a')
                    if not name_elem:
                        continue
                    
                    name = await name_elem.inner_text()
                    href = await name_elem.get_attribute('href')
                    url = urljoin(self.base_url, href) if href else ''
                    
                    # Detect manufacturer
                    name_lower = name.lower()
                    if 'intel' in name_lower or 'core' in name_lower:
                        manufacturer = 'Intel'
                    elif 'amd' in name_lower or 'ryzen' in name_lower:
                        manufacturer = 'AMD'
                    elif 'apple' in name_lower:
                        manufacturer = 'Apple'
                    else:
                        manufacturer = 'Other'
                    
                    cpus.append(CpuBasicInfo(
                        name=name.strip(),
                        url=url,
                        source='nanoreview',
                        manufacturer=manufacturer
                    ))
                    
                except Exception as e:
                    continue
            
            logger.info(f"✅ Found {len(cpus)} CPUs on NanoReview")
            
        except PlaywrightTimeout:
            logger.warning("⚠️ NanoReview page load timed out")
        except Exception as e:
            logger.error(f"❌ NanoReview scrape error: {e}")
        finally:
            await page.close()
            
        return cpus
    
    async def get_cpu_details(self, url: str) -> Tuple[CpuBenchmarks, CpuGaming]:
        """Scrape detailed benchmarks and gaming data for a CPU."""
        benchmarks = CpuBenchmarks()
        gaming = CpuGaming()
        
        page = await self.browser.new_page()
        
        try:
            await page.goto(url, timeout=SCRAPE_CONFIG['page_timeout_ms'])
            await asyncio.sleep(1)  # Wait for dynamic content
            
            # Scrape benchmark scores
            benchmarks = await self._scrape_benchmarks(page)
            
            # Scrape gaming performance
            gaming = await self._scrape_gaming(page)
            
        except Exception as e:
            logger.debug(f"Error scraping {url}: {e}")
        finally:
            await page.close()
            
        return benchmarks, gaming
    
    async def _scrape_benchmarks(self, page: Page) -> CpuBenchmarks:
        """Extract benchmark scores from page."""
        benchmarks = CpuBenchmarks()
        
        try:
            # Look for benchmark tables/sections
            # Cinebench R23
            cb23_single = await self._find_score(page, ['cinebench r23 single', 'cb r23 single', 'cinebench 23 single'])
            cb23_multi = await self._find_score(page, ['cinebench r23 multi', 'cb r23 multi', 'cinebench 23 multi'])
            
            if cb23_single:
                benchmarks.cinebench_r23_single = int(cb23_single)
            if cb23_multi:
                benchmarks.cinebench_r23_multi = int(cb23_multi)
            
            # Cinebench R24
            cb24_single = await self._find_score(page, ['cinebench 2024 single', 'cb24 single', 'cinebench r24 single'])
            cb24_multi = await self._find_score(page, ['cinebench 2024 multi', 'cb24 multi', 'cinebench r24 multi'])
            
            if cb24_single:
                benchmarks.cinebench_r24_single = int(cb24_single)
            if cb24_multi:
                benchmarks.cinebench_r24_multi = int(cb24_multi)
            
            # Geekbench 6
            gb6_single = await self._find_score(page, ['geekbench 6 single', 'gb6 single'])
            gb6_multi = await self._find_score(page, ['geekbench 6 multi', 'gb6 multi'])
            
            if gb6_single:
                benchmarks.geekbench6_single = int(gb6_single)
            if gb6_multi:
                benchmarks.geekbench6_multi = int(gb6_multi)
            
            # PassMark
            pm_single = await self._find_score(page, ['passmark single', 'cpu mark single'])
            pm_multi = await self._find_score(page, ['passmark', 'cpu mark', 'passmark score'])
            
            if pm_single:
                benchmarks.passmark_single = int(pm_single)
            if pm_multi:
                benchmarks.passmark_multi = int(pm_multi)
                
        except Exception as e:
            logger.debug(f"Benchmark scrape error: {e}")
            
        return benchmarks
    
    async def _scrape_gaming(self, page: Page) -> CpuGaming:
        """Extract gaming performance data."""
        gaming = CpuGaming()
        
        try:
            # Look for gaming section
            gaming_section = await page.query_selector('.gaming-performance, [class*="gaming"], [id*="gaming"]')
            
            if gaming_section:
                # Try to find average FPS
                fps_elem = await gaming_section.query_selector('[class*="fps"], [class*="average"]')
                if fps_elem:
                    fps_text = await fps_elem.inner_text()
                    fps_match = re.search(r'(\d+(?:\.\d+)?)\s*fps', fps_text, re.IGNORECASE)
                    if fps_match:
                        gaming.avg_fps = float(fps_match.group(1))
            
            # Look for gaming score
            score = await self._find_score(page, ['gaming score', 'game score'])
            if score:
                gaming.gaming_score = int(score)
                
        except Exception as e:
            logger.debug(f"Gaming scrape error: {e}")
            
        return gaming
    
    async def _find_score(self, page: Page, keywords: List[str]) -> Optional[str]:
        """Find a benchmark score by searching for keywords."""
        try:
            content = await page.content()
            content_lower = content.lower()
            
            for keyword in keywords:
                # Look for pattern: keyword ... number
                pattern = rf'{re.escape(keyword)}[^0-9]*(\d[\d,]*)'
                match = re.search(pattern, content_lower)
                if match:
                    score = match.group(1).replace(',', '')
                    if score.isdigit() and int(score) > 0:
                        return score
            
            return None
        except:
            return None


class TechPowerUpScraper:
    """Scraper for TechPowerUp - Nerd Specs (Transistors, Die Size, etc.)."""
    
    def __init__(self, browser: Browser):
        self.browser = browser
        self.base_url = SOURCES['techpowerup']['base_url']
        
    async def search_cpu(self, cpu_name: str) -> Optional[str]:
        """Search for a CPU and return its detail page URL."""
        page = await self.browser.new_page()
        
        try:
            # Use TechPowerUp's CPU specs page with search
            search_url = f"{SOURCES['techpowerup']['cpu_list']}?mfgr=&sort=name&mobile=No&server=No&params="
            await page.goto(search_url, timeout=SCRAPE_CONFIG['page_timeout_ms'])
            
            # Try the search box
            search_box = await page.query_selector('input[name="s"], input[type="search"], .search-input')
            if search_box:
                await search_box.fill(cpu_name)
                await search_box.press('Enter')
                await asyncio.sleep(2)
            
            # Look for matching result
            links = await page.query_selector_all('table.processors a, .cpu-name a, td a')
            
            for link in links:
                text = await link.inner_text()
                href = await link.get_attribute('href')
                
                if href and 'cpu-specs' in href:
                    # Check if this matches our CPU
                    match, score = NameMatcher.match_best(cpu_name, [text])
                    if score >= 80:
                        return urljoin(self.base_url, href)
            
            return None
            
        except Exception as e:
            logger.debug(f"TechPowerUp search error for {cpu_name}: {e}")
            return None
        finally:
            await page.close()
    
    async def get_nerd_specs(self, url: str) -> CpuNerdSpecs:
        """Scrape the nerd specs from a CPU detail page."""
        specs = CpuNerdSpecs()
        page = await self.browser.new_page()
        
        try:
            await page.goto(url, timeout=SCRAPE_CONFIG['page_timeout_ms'])
            await asyncio.sleep(1)
            
            # Get the spec table content
            content = await page.content()
            
            # Transistors
            trans_match = re.search(r'transistors[:\s]*(\d[\d,.]*)\s*(million|billion|M|B)?', content, re.IGNORECASE)
            if trans_match:
                value = float(trans_match.group(1).replace(',', ''))
                unit = trans_match.group(2) or ''
                if 'billion' in unit.lower() or unit == 'B':
                    value *= 1000
                specs.transistors_million = int(value)
            
            # Die Size
            die_match = re.search(r'die\s*size[:\s]*(\d+(?:\.\d+)?)\s*mm', content, re.IGNORECASE)
            if die_match:
                specs.die_size_mm2 = float(die_match.group(1))
            
            # MCM / Chiplet
            if re.search(r'multi.chip|MCM|chiplet|CCD|IOD', content, re.IGNORECASE):
                specs.is_mcm = True
                chiplet_match = re.search(r'(\d+)\s*(?:CCD|chiplet|die)', content, re.IGNORECASE)
                if chiplet_match:
                    specs.mcm_chiplet_count = int(chiplet_match.group(1))
            
            # Voltage
            voltage_match = re.search(r'voltage[:\s]*(\d+\.?\d*)\s*[-–]\s*(\d+\.?\d*)\s*V', content, re.IGNORECASE)
            if voltage_match:
                specs.min_voltage = float(voltage_match.group(1))
                specs.max_voltage = float(voltage_match.group(2))
                specs.voltage_range = f"{voltage_match.group(1)}V - {voltage_match.group(2)}V"
            
            # Process Node
            process_match = re.search(r'process[:\s]*(Intel\s*\d+|TSMC\s*N?\d+|\d+\s*nm)', content, re.IGNORECASE)
            if process_match:
                specs.process_node = process_match.group(1).strip()
            
            # Foundry
            if 'TSMC' in content:
                specs.foundry = 'TSMC'
            elif 'Samsung' in content.lower():
                specs.foundry = 'Samsung'
            elif 'Intel' in specs.process_node if specs.process_node else False:
                specs.foundry = 'Intel'
            
        except Exception as e:
            logger.debug(f"TechPowerUp spec scrape error: {e}")
        finally:
            await page.close()
            
        return specs


class IntelArkScraper:
    """Scraper for Intel ARK - General Info."""
    
    def __init__(self, browser: Browser):
        self.browser = browser
        
    async def get_general_info(self, cpu_name: str) -> CpuGeneralInfo:
        """Search Intel ARK and get general CPU info."""
        info = CpuGeneralInfo()
        
        # Only process Intel CPUs
        if 'intel' not in cpu_name.lower() and 'core' not in cpu_name.lower():
            return info
        
        page = await self.browser.new_page()
        
        try:
            search_url = SOURCES['intel_ark']['search'].format(query=quote(cpu_name))
            await page.goto(search_url, timeout=SCRAPE_CONFIG['page_timeout_ms'])
            await asyncio.sleep(2)
            
            # Click first result if available
            first_result = await page.query_selector('.result-item a, .search-result a')
            if first_result:
                await first_result.click()
                await asyncio.sleep(2)
            
            content = await page.content()
            
            # Launch Date / Quarter
            launch_match = re.search(r"launch\s*date[:\s]*Q(\d)'?(\d{2,4})", content, re.IGNORECASE)
            if launch_match:
                quarter = launch_match.group(1)
                year = launch_match.group(2)
                if len(year) == 2:
                    year = '20' + year
                info.launch_quarter = f"Q{quarter}'{year}"
            
            # MSRP
            msrp_match = re.search(r'recommended.*price[:\s]*\$?([\d,]+(?:\.\d{2})?)', content, re.IGNORECASE)
            if msrp_match:
                info.launch_msrp = float(msrp_match.group(1).replace(',', ''))
            
            # Memory Type
            mem_match = re.search(r'memory\s*types?[:\s]*(DDR\d[^<\n]*)', content, re.IGNORECASE)
            if mem_match:
                info.memory_type = mem_match.group(1).strip()
            
            # Max Memory
            max_mem_match = re.search(r'max\s*memory\s*size[:\s]*(\d+)\s*GB', content, re.IGNORECASE)
            if max_mem_match:
                info.max_memory_gb = int(max_mem_match.group(1))
            
            # Memory Channels
            channels_match = re.search(r'memory\s*channels?[:\s]*(\d+)', content, re.IGNORECASE)
            if channels_match:
                info.memory_channels = int(channels_match.group(1))
            
            # Product Code
            code_match = re.search(r'processor\s*number[:\s]*([A-Z0-9-]+)', content, re.IGNORECASE)
            if code_match:
                info.product_code = code_match.group(1)
                
        except Exception as e:
            logger.debug(f"Intel ARK scrape error for {cpu_name}: {e}")
        finally:
            await page.close()
            
        return info


# =============================================================================
# MAIN PIPELINE
# =============================================================================

class MegaMerger:
    """
    The Triple-Threat Merge Pipeline.
    
    Orchestrates scraping from multiple sources and merges data into MySQL.
    """
    
    def __init__(self):
        self.db = DatabaseManager()
        self.browser = None
        self.stats = {
            'nanoreview_scraped': 0,
            'techpowerup_matched': 0,
            'ark_matched': 0,
            'inserted': 0,
            'updated': 0,
            'failed': 0
        }
        
    async def initialize(self) -> bool:
        """Initialize browser and database connections."""
        # Connect to database
        if not self.db.connect():
            return False
        
        # Launch browser
        try:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )
            logger.info("✅ Browser launched")
            return True
        except Exception as e:
            logger.error(f"❌ Browser launch failed: {e}")
            return False
    
    async def cleanup(self):
        """Clean up resources."""
        if self.browser:
            await self.browser.close()
        self.db.close()
        
    async def run_pipeline(self, max_cpus: int = 200, modern_only: bool = True):
        """
        Run the full triple-threat merge pipeline.
        
        Args:
            max_cpus: Maximum number of CPUs to process
            modern_only: Only process CPUs from 2020+
        """
        logger.info("=" * 60)
        logger.info("🚀 MEGA MERGER - Triple Threat Pipeline Started")
        logger.info("=" * 60)
        
        try:
            # Phase 1: Get CPU list from NanoReview (Source B)
            logger.info("\n📊 PHASE 1: Scraping NanoReview CPU List...")
            self.db.update_scraper_state('nanoreview', 'running')
            
            nanoreview = NanoReviewScraper(self.browser)
            cpu_list = await nanoreview.get_top_cpus(limit=max_cpus)
            self.stats['nanoreview_scraped'] = len(cpu_list)
            
            if not cpu_list:
                logger.error("❌ No CPUs found on NanoReview. Aborting.")
                return
            
            # Phase 2: For each CPU, get details and merge
            logger.info(f"\n🔄 PHASE 2: Processing {len(cpu_list)} CPUs...")
            
            techpowerup = TechPowerUpScraper(self.browser)
            intel_ark = IntelArkScraper(self.browser)
            
            existing_names = self.db.get_all_cpu_names()
            
            for i, cpu_basic in enumerate(tqdm(cpu_list, desc="Processing CPUs")):
                try:
                    # Create merged CPU object
                    merged = MergedCpu(
                        name=cpu_basic.name,
                        name_normalized=NameMatcher.normalize(cpu_basic.name),
                        manufacturer=cpu_basic.manufacturer
                    )
                    merged.nanoreview_url = cpu_basic.url
                    
                    # Get NanoReview details (benchmarks + gaming)
                    benchmarks, gaming = await nanoreview.get_cpu_details(cpu_basic.url)
                    merged.benchmarks = benchmarks
                    merged.gaming = gaming
                    
                    # Delay between requests
                    await asyncio.sleep(SCRAPE_CONFIG['request_delay_sec'])
                    
                    # Phase 2a: Search TechPowerUp for nerd specs (Source A)
                    tpu_url = await techpowerup.search_cpu(cpu_basic.name)
                    if tpu_url:
                        merged.techpowerup_url = tpu_url
                        merged.nerd_specs = await techpowerup.get_nerd_specs(tpu_url)
                        self.stats['techpowerup_matched'] += 1
                        await asyncio.sleep(SCRAPE_CONFIG['request_delay_sec'])
                    
                    # Phase 2b: Search Intel ARK for general info (Source C)
                    if cpu_basic.manufacturer == 'Intel':
                        merged.general = await intel_ark.get_general_info(cpu_basic.name)
                        if merged.general.launch_msrp:
                            self.stats['ark_matched'] += 1
                        await asyncio.sleep(SCRAPE_CONFIG['request_delay_sec'])
                    
                    # Save to database
                    action, cpu_id = self.db.save_merged_cpu(merged)
                    self.stats[action] += 1
                    
                    if action != 'failed':
                        logger.debug(f"✓ {action.upper()}: {cpu_basic.name}")
                    else:
                        logger.warning(f"✗ FAILED: {cpu_basic.name}")
                    
                    # Progress log every 25 CPUs
                    if (i + 1) % 25 == 0:
                        logger.info(f"Progress: {i + 1}/{len(cpu_list)} CPUs processed")
                        
                except Exception as e:
                    logger.error(f"Error processing {cpu_basic.name}: {e}")
                    self.stats['failed'] += 1
                    continue
            
            # Update scraper state
            self.db.update_scraper_state('nanoreview', 'completed', self.stats['nanoreview_scraped'])
            self.db.update_scraper_state('techpowerup', 'completed', self.stats['techpowerup_matched'])
            
        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            self.db.update_scraper_state('nanoreview', 'error', error=str(e))
        
        # Print summary
        self._print_summary()
    
    def _print_summary(self):
        """Print pipeline execution summary."""
        logger.info("\n" + "=" * 60)
        logger.info("📊 PIPELINE SUMMARY")
        logger.info("=" * 60)
        logger.info(f"  NanoReview CPUs found:  {self.stats['nanoreview_scraped']}")
        logger.info(f"  TechPowerUp matches:    {self.stats['techpowerup_matched']}")
        logger.info(f"  Intel ARK matches:      {self.stats['ark_matched']}")
        logger.info("-" * 40)
        logger.info(f"  Inserted:               {self.stats['inserted']}")
        logger.info(f"  Updated:                {self.stats['updated']}")
        logger.info(f"  Failed:                 {self.stats['failed']}")
        logger.info("=" * 60)


# =============================================================================
# JSON EXPORTER
# =============================================================================

class JsonExporter:
    """Export database to JSON for Flutter integration."""
    
    def __init__(self, db: DatabaseManager):
        self.db = db
        
    def export_to_json(self, output_path: str = 'assets/data/cpu_database.json'):
        """Export all CPU data to JSON file."""
        logger.info(f"📤 Exporting to {output_path}...")
        
        try:
            # Get all CPUs with full data using the view
            self.db.cursor.execute("""
                SELECT * FROM v_cpu_full
                ORDER BY 
                    CASE WHEN cinebench_r23_multi IS NOT NULL THEN 0 ELSE 1 END,
                    cinebench_r23_multi DESC,
                    launch_date DESC
            """)
            
            cpus = []
            for row in self.db.cursor.fetchall():
                # Convert to JSON-friendly format
                cpu_dict = {}
                for key, value in row.items():
                    # Handle special types
                    if isinstance(value, datetime):
                        cpu_dict[key] = value.isoformat()
                    elif isinstance(value, bytes):
                        cpu_dict[key] = value.decode('utf-8')
                    else:
                        cpu_dict[key] = value
                cpus.append(cpu_dict)
            
            # Write to file
            output = {
                'version': '5.0',
                'generated_at': datetime.now().isoformat(),
                'total_cpus': len(cpus),
                'cpus': cpus
            }
            
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"✅ Exported {len(cpus)} CPUs to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Export failed: {e}")
            return False


# =============================================================================
# CLI ENTRY POINT
# =============================================================================

async def main():
    """Main entry point for the mega merger pipeline."""
    parser = argparse.ArgumentParser(description='HardWizChippy Mega Merger - Triple Threat Data Pipeline')
    parser.add_argument('--max-cpus', type=int, default=200, help='Maximum CPUs to process')
    parser.add_argument('--modern-only', action='store_true', default=True, help='Only process 2020+ CPUs')
    parser.add_argument('--export', action='store_true', help='Export to JSON only (skip scraping)')
    parser.add_argument('--source', choices=['nanoreview', 'techpowerup', 'ark', 'all'], default='all',
                        help='Which source to scrape')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    merger = MegaMerger()
    
    if not await merger.initialize():
        logger.error("Failed to initialize. Exiting.")
        return 1
    
    try:
        if args.export:
            # Export only
            exporter = JsonExporter(merger.db)
            success = exporter.export_to_json()
            return 0 if success else 1
        else:
            # Run full pipeline
            await merger.run_pipeline(
                max_cpus=args.max_cpus,
                modern_only=args.modern_only
            )
            
            # Auto-export after scraping
            exporter = JsonExporter(merger.db)
            exporter.export_to_json()
            
            return 0
            
    finally:
        await merger.cleanup()


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    exit(exit_code)
