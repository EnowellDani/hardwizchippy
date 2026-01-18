"""
=============================================================================
HardWizChippy - Smoke Test Script
"The 5-CPU Sanity Check"
=============================================================================

A lightweight test script to verify fuzzy matching and data integrity
for the most important "Main View Point" specs.

Target CPUs:
  1. Intel Core Ultra 9 285K
  2. AMD Ryzen 9 9950X3D
  3. Intel Core i9-14900K
  4. AMD Ryzen 7 7800X3D
  5. Intel Core Ultra 7 265K

Run: python smoke_test.py

Author: KBitWare Project
Date: January 2026
=============================================================================
"""

import asyncio
import json
import re
import random
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# Third-party imports
try:
    from thefuzz import fuzz
    from playwright.async_api import async_playwright, Browser, Page
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import print as rprint
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Run: pip install thefuzz playwright rich")
    exit(1)

# =============================================================================
# CONFIGURATION
# =============================================================================

# The 5 Test CPUs
TEST_CPUS = [
    {
        'name': 'Intel Core Ultra 9 285K',
        'expected_manufacturer': 'Intel',
        'expected_socket': 'LGA 1851',
    },
    {
        'name': 'AMD Ryzen 9 9950X3D',
        'expected_manufacturer': 'AMD',
        'expected_socket': 'AM5',
    },
    {
        'name': 'Intel Core i9-14900K',
        'expected_manufacturer': 'Intel',
        'expected_socket': 'LGA 1700',
    },
    {
        'name': 'AMD Ryzen 7 7800X3D',
        'expected_manufacturer': 'AMD',
        'expected_socket': 'AM5',
    },
    {
        'name': 'Intel Core Ultra 7 265K',
        'expected_manufacturer': 'Intel',
        'expected_socket': 'LGA 1851',
    },
]

# Randomized User-Agents (Anti-bot measure)
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
]

SOURCES = {
    'nanoreview': 'https://nanoreview.net',
    'techpowerup': 'https://www.techpowerup.com',
}

console = Console()

# =============================================================================
# LOGGING SETUP - merger_debug.log
# =============================================================================

# Main logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('SmokeTest')

# Debug logger for fuzzy match failures
debug_logger = logging.getLogger('FuzzyDebug')
debug_handler = logging.FileHandler('merger_debug.log', mode='w', encoding='utf-8')
debug_handler.setFormatter(logging.Formatter('%(asctime)s | %(message)s'))
debug_logger.addHandler(debug_handler)
debug_logger.setLevel(logging.DEBUG)


# =============================================================================
# ENHANCED NAME MATCHER (The Fix for "Intel Core Ultra 9 285K" == "Core Ultra 9 285K")
# =============================================================================

class NameMatcher:
    """
    Intelligent CPU name matching using TheFuzz.
    
    KEY FIX: "Intel Core Ultra 9 285K" and "Core Ultra 9 285K" are 100% match.
    """
    
    # Canonical manufacturer prefixes to strip for matching
    MANUFACTURER_PREFIXES = [
        r'^intel\s+',
        r'^amd\s+',
        r'^apple\s+',
        r'^qualcomm\s+',
        r'^nvidia\s+',
    ]
    
    # Common suffixes to normalize
    SUFFIX_PATTERNS = [
        r'\s+processor$',
        r'\s+cpu$',
        r'\s+with\s+.*$',  # "with Radeon Graphics"
        r'\s+boxed$',
        r'\s+tray$',
        r'\s+oem$',
    ]
    
    # Model number patterns (the MOST important part for matching)
    MODEL_PATTERNS = [
        # Intel Core Ultra: "285K", "265K", "245K"
        r'(ultra\s*[579])\s*(\d{3}[A-Z]*)',
        # Intel Core iX: "14900K", "13900KS"
        r'(i[3579])[- ]?(\d{4,5}[A-Z]*)',
        # AMD Ryzen: "9950X3D", "7800X3D", "9900X"
        r'(ryzen\s*[3579])\s*(\d{4}[A-Z0-9]*)',
        # AMD EPYC: "9654", "9754"
        r'(epyc)\s*(\d{4}[A-Z]*)',
    ]
    
    @staticmethod
    def normalize(name: str) -> str:
        """
        Normalize CPU name for matching.
        
        CRITICAL: This removes manufacturer prefixes so that
        "Intel Core Ultra 9 285K" normalizes to the same thing as "Core Ultra 9 285K"
        """
        if not name:
            return ''
        
        normalized = name.lower().strip()
        
        # Step 1: Remove manufacturer prefixes
        for pattern in NameMatcher.MANUFACTURER_PREFIXES:
            normalized = re.sub(pattern, '', normalized, flags=re.IGNORECASE)
        
        # Step 2: Remove common suffixes
        for pattern in NameMatcher.SUFFIX_PATTERNS:
            normalized = re.sub(pattern, '', normalized, flags=re.IGNORECASE)
        
        # Step 3: Normalize whitespace
        normalized = ' '.join(normalized.split())
        
        # Step 4: Normalize common variations
        normalized = normalized.replace('(r)', '')
        normalized = normalized.replace('(tm)', '')
        normalized = re.sub(r'\s*-\s*', '-', normalized)  # Normalize dashes
        
        return normalized.strip()
    
    @staticmethod
    def extract_model_number(name: str) -> Optional[str]:
        """
        Extract the core model identifier.
        
        Examples:
            "Intel Core Ultra 9 285K" -> "ultra9285k"
            "Core Ultra 9 285K" -> "ultra9285k"
            "AMD Ryzen 9 9950X3D" -> "ryzen99950x3d"
            "Core i9-14900K" -> "i914900k"
        """
        name_lower = name.lower()
        
        # Intel Core Ultra
        match = re.search(r'ultra\s*([579])\s*(\d{3}[a-z]*)', name_lower)
        if match:
            return f"ultra{match.group(1)}{match.group(2)}"
        
        # Intel Core iX
        match = re.search(r'(i[3579])[- ]?(\d{4,5}[a-z]*)', name_lower)
        if match:
            return f"{match.group(1)}{match.group(2)}"
        
        # AMD Ryzen
        match = re.search(r'ryzen\s*([3579])\s*(\d{4}[a-z0-9]*)', name_lower)
        if match:
            return f"ryzen{match.group(1)}{match.group(2)}"
        
        # Generic fallback: extract any number sequence
        match = re.search(r'(\d{3,5}[a-z0-9]*)', name_lower)
        if match:
            return match.group(1)
        
        return None
    
    @staticmethod
    def match_score(query: str, candidate: str) -> int:
        """
        Calculate match score between two CPU names.
        
        Returns score 0-100, where 100 is perfect match.
        
        KEY ALGORITHM:
        1. If model numbers are identical -> automatic 100
        2. Otherwise use fuzzy matching on normalized names
        """
        # Extract model numbers
        query_model = NameMatcher.extract_model_number(query)
        candidate_model = NameMatcher.extract_model_number(candidate)
        
        # If model numbers exist and match exactly -> 100%
        if query_model and candidate_model:
            if query_model == candidate_model:
                return 100
        
        # Normalize both names
        query_norm = NameMatcher.normalize(query)
        candidate_norm = NameMatcher.normalize(candidate)
        
        # If normalized names are identical -> 100%
        if query_norm == candidate_norm:
            return 100
        
        # Use multiple fuzzy strategies
        scores = [
            fuzz.ratio(query_norm, candidate_norm),
            fuzz.token_sort_ratio(query_norm, candidate_norm),
            fuzz.token_set_ratio(query_norm, candidate_norm),
        ]
        
        # Weighted average
        base_score = (scores[0] * 0.3 + scores[1] * 0.4 + scores[2] * 0.3)
        
        # Bonus for matching model numbers (even if not exact)
        if query_model and candidate_model:
            model_similarity = fuzz.ratio(query_model, candidate_model)
            if model_similarity >= 90:
                base_score = min(100, base_score + 15)
            elif model_similarity >= 80:
                base_score = min(100, base_score + 10)
        
        return int(base_score)
    
    @staticmethod
    def find_best_match(query: str, candidates: List[str], threshold: int = 85) -> Tuple[Optional[str], int]:
        """
        Find the best matching CPU name from candidates.
        
        Returns: (best_match, score) or (None, 0)
        """
        if not query or not candidates:
            return None, 0
        
        best_match = None
        best_score = 0
        
        for candidate in candidates:
            score = NameMatcher.match_score(query, candidate)
            
            if score > best_score:
                best_score = score
                best_match = candidate
        
        # Log low-confidence matches for manual review
        if 0 < best_score < threshold:
            debug_logger.warning(
                f"LOW CONFIDENCE MATCH ({best_score}%): "
                f"'{query}' -> '{best_match}' | "
                f"Query normalized: '{NameMatcher.normalize(query)}' | "
                f"Candidate normalized: '{NameMatcher.normalize(best_match)}'"
            )
        
        if best_score >= threshold:
            return best_match, best_score
        
        return None, best_score


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class SmokeTestResult:
    """Result of a smoke test for one CPU."""
    cpu_name: str
    
    # NanoReview results
    nanoreview_found: bool = False
    nanoreview_url: str = ''
    benchmarks_extracted: bool = False
    cinebench_r23_single: Optional[int] = None
    cinebench_r23_multi: Optional[int] = None
    geekbench6_single: Optional[int] = None
    geekbench6_multi: Optional[int] = None
    gaming_score: Optional[int] = None
    
    # TechPowerUp results
    techpowerup_found: bool = False
    techpowerup_url: str = ''
    fuzzy_match_score: int = 0
    fuzzy_matched_name: str = ''
    
    # Nerd specs (The Big Part!)
    die_size_mm2: Optional[float] = None
    transistors_million: Optional[int] = None
    is_mcm: bool = False
    mcm_config: str = ''
    voltage_range: str = ''
    process_node: str = ''
    
    # Status
    success: bool = False
    error_message: str = ''


# =============================================================================
# ANTI-BOT UTILITIES
# =============================================================================

def get_random_user_agent() -> str:
    """Get a random user agent to avoid detection."""
    return random.choice(USER_AGENTS)


async def anti_bot_delay(min_sec: float = 3.0, max_sec: float = 7.0):
    """Random delay between requests to avoid bot detection."""
    delay = random.uniform(min_sec, max_sec)
    console.print(f"   [dim]⏳ Anti-bot delay: {delay:.1f}s...[/dim]")
    await asyncio.sleep(delay)


# =============================================================================
# SCRAPERS (Lightweight versions for smoke test)
# =============================================================================

class SmokeTestScraper:
    """Lightweight scraper for smoke testing."""
    
    def __init__(self, browser: Browser):
        self.browser = browser
        self.results: List[SmokeTestResult] = []
    
    async def scrape_nanoreview(self, cpu_name: str) -> Tuple[bool, Dict]:
        """Search NanoReview for a CPU and extract benchmarks."""
        console.print(f"\n   🔍 Searching NanoReview for [cyan]{cpu_name}[/cyan]...")
        
        page = await self.browser.new_page(user_agent=get_random_user_agent())
        result = {'found': False, 'url': '', 'benchmarks': {}, 'gaming': {}}
        
        try:
            # Search on NanoReview
            search_query = cpu_name.replace(' ', '+')
            search_url = f"https://nanoreview.net/en/search?q={search_query}"
            
            await page.goto(search_url, timeout=30000)
            await asyncio.sleep(2)
            
            # Look for first CPU result
            cpu_link = await page.query_selector('a[href*="/en/cpu/"]')
            
            if cpu_link:
                href = await cpu_link.get_attribute('href')
                result['url'] = f"https://nanoreview.net{href}" if href.startswith('/') else href
                result['found'] = True
                
                # Navigate to CPU page
                await page.goto(result['url'], timeout=30000)
                await asyncio.sleep(2)
                
                content = await page.content()
                
                # Extract Cinebench R23
                cb23_match = re.search(r'cinebench\s*r23.*?single[^0-9]*(\d[\d,]*)', content, re.IGNORECASE | re.DOTALL)
                if cb23_match:
                    result['benchmarks']['cinebench_r23_single'] = int(cb23_match.group(1).replace(',', ''))
                
                cb23_multi = re.search(r'cinebench\s*r23.*?multi[^0-9]*(\d[\d,]*)', content, re.IGNORECASE | re.DOTALL)
                if cb23_multi:
                    result['benchmarks']['cinebench_r23_multi'] = int(cb23_multi.group(1).replace(',', ''))
                
                # Extract Geekbench 6
                gb6_single = re.search(r'geekbench\s*6.*?single[^0-9]*(\d[\d,]*)', content, re.IGNORECASE | re.DOTALL)
                if gb6_single:
                    result['benchmarks']['geekbench6_single'] = int(gb6_single.group(1).replace(',', ''))
                
                gb6_multi = re.search(r'geekbench\s*6.*?multi[^0-9]*(\d[\d,]*)', content, re.IGNORECASE | re.DOTALL)
                if gb6_multi:
                    result['benchmarks']['geekbench6_multi'] = int(gb6_multi.group(1).replace(',', ''))
                
                # Extract Gaming Score
                gaming_match = re.search(r'gaming\s*score[^0-9]*(\d+)', content, re.IGNORECASE)
                if gaming_match:
                    result['gaming']['score'] = int(gaming_match.group(1))
                
                console.print(f"   ✅ Found [green]{cpu_name}[/green] on NanoReview... Benchmarks extracted.")
            else:
                console.print(f"   ⚠️ [yellow]Not found on NanoReview[/yellow]")
                debug_logger.warning(f"NOT FOUND ON NANOREVIEW: '{cpu_name}'")
                
        except Exception as e:
            console.print(f"   ❌ [red]NanoReview error: {e}[/red]")
            debug_logger.error(f"NANOREVIEW ERROR for '{cpu_name}': {e}")
        finally:
            await page.close()
        
        return result['found'], result
    
    async def scrape_techpowerup(self, cpu_name: str, existing_names: List[str] = None) -> Tuple[bool, Dict, int]:
        """Search TechPowerUp for a CPU and extract nerd specs."""
        console.print(f"\n   🔍 Attempting Fuzzy Match on TechPowerUp for [cyan]{cpu_name}[/cyan]...")
        
        page = await self.browser.new_page(user_agent=get_random_user_agent())
        result = {'found': False, 'url': '', 'matched_name': '', 'specs': {}}
        match_score = 0
        
        try:
            # Go to TechPowerUp CPU specs
            await page.goto('https://www.techpowerup.com/cpu-specs/', timeout=30000)
            await asyncio.sleep(2)
            
            # Use their search
            search_box = await page.query_selector('input[name="s"], input.search-input, #search')
            if search_box:
                # Simplify search query
                simple_query = re.sub(r'^(Intel|AMD)\s+', '', cpu_name)
                await search_box.fill(simple_query)
                await search_box.press('Enter')
                await asyncio.sleep(3)
            
            # Get all CPU links from results
            links = await page.query_selector_all('table.processors td a, .cpuname a')
            
            if links:
                # Build candidate list
                candidates = []
                href_map = {}
                
                for link in links[:20]:  # Check first 20 results
                    try:
                        text = await link.inner_text()
                        href = await link.get_attribute('href')
                        if text and href and 'cpu-specs' in href:
                            candidates.append(text.strip())
                            href_map[text.strip()] = href
                    except:
                        continue
                
                if candidates:
                    # Find best fuzzy match
                    best_match, match_score = NameMatcher.find_best_match(cpu_name, candidates)
                    
                    console.print(f"   📊 Fuzzy match result: [cyan]{best_match}[/cyan] (Score: {match_score}%)")
                    
                    if best_match and match_score >= 85:
                        result['found'] = True
                        result['matched_name'] = best_match
                        result['url'] = f"https://www.techpowerup.com{href_map[best_match]}"
                        
                        # Navigate to spec page
                        await page.goto(result['url'], timeout=30000)
                        await asyncio.sleep(2)
                        
                        content = await page.content()
                        
                        # Extract Die Size
                        die_match = re.search(r'die\s*size[:\s]*(\d+(?:\.\d+)?)\s*mm', content, re.IGNORECASE)
                        if die_match:
                            result['specs']['die_size_mm2'] = float(die_match.group(1))
                        
                        # Extract Transistors
                        trans_match = re.search(r'transistors?[:\s]*(\d[\d,.]*)\s*(million|billion|M|B)?', content, re.IGNORECASE)
                        if trans_match:
                            value = float(trans_match.group(1).replace(',', ''))
                            unit = trans_match.group(2) or ''
                            if 'billion' in unit.lower() or unit.upper() == 'B':
                                value *= 1000
                            result['specs']['transistors_million'] = int(value)
                        
                        # Extract MCM info
                        if re.search(r'multi.?chip|MCM|chiplet|CCD|IOD', content, re.IGNORECASE):
                            result['specs']['is_mcm'] = True
                            mcm_match = re.search(r'(\d+\s*(?:CCD|chiplet|die)[^<\n]*)', content, re.IGNORECASE)
                            if mcm_match:
                                result['specs']['mcm_config'] = mcm_match.group(1).strip()
                        
                        # Extract Process Node
                        process_match = re.search(r'process[:\s]*(Intel\s*\d+|TSMC\s*N?\d+|\d+\s*nm)', content, re.IGNORECASE)
                        if process_match:
                            result['specs']['process_node'] = process_match.group(1).strip()
                        
                        # Extract Voltage Range
                        voltage_match = re.search(r'voltage[:\s]*(\d+\.?\d*)\s*[-–]\s*(\d+\.?\d*)\s*V', content, re.IGNORECASE)
                        if voltage_match:
                            result['specs']['voltage_range'] = f"{voltage_match.group(1)}V - {voltage_match.group(2)}V"
                        
                        # Print success message
                        die_size = result['specs'].get('die_size_mm2', 'N/A')
                        transistors = result['specs'].get('transistors_million', 'N/A')
                        console.print(f"   ✅ [green]SUCCESS: Merged Die Size: {die_size}mm² and Transistors: {transistors}M[/green]")
                    else:
                        console.print(f"   ⚠️ [yellow]Match score too low ({match_score}% < 85%)[/yellow]")
            else:
                console.print(f"   ⚠️ [yellow]No search results on TechPowerUp[/yellow]")
                debug_logger.warning(f"NO TECHPOWERUP RESULTS: '{cpu_name}'")
                
        except Exception as e:
            console.print(f"   ❌ [red]TechPowerUp error: {e}[/red]")
            debug_logger.error(f"TECHPOWERUP ERROR for '{cpu_name}': {e}")
        finally:
            await page.close()
        
        return result['found'], result, match_score
    
    async def run_smoke_test(self) -> List[SmokeTestResult]:
        """Run the full smoke test on all 5 CPUs."""
        
        console.print(Panel.fit(
            "[bold cyan]🧪 SMOKE TEST - The 5-CPU Sanity Check[/bold cyan]\n"
            "Testing fuzzy matching and data integrity",
            border_style="cyan"
        ))
        
        for i, cpu_info in enumerate(TEST_CPUS, 1):
            cpu_name = cpu_info['name']
            
            console.print(f"\n{'='*60}")
            console.print(f"[bold]CPU {i}/5: {cpu_name}[/bold]")
            console.print(f"{'='*60}")
            
            result = SmokeTestResult(cpu_name=cpu_name)
            
            try:
                # Step 1: NanoReview
                nano_found, nano_data = await self.scrape_nanoreview(cpu_name)
                result.nanoreview_found = nano_found
                result.nanoreview_url = nano_data.get('url', '')
                
                if nano_data.get('benchmarks'):
                    result.benchmarks_extracted = True
                    result.cinebench_r23_single = nano_data['benchmarks'].get('cinebench_r23_single')
                    result.cinebench_r23_multi = nano_data['benchmarks'].get('cinebench_r23_multi')
                    result.geekbench6_single = nano_data['benchmarks'].get('geekbench6_single')
                    result.geekbench6_multi = nano_data['benchmarks'].get('geekbench6_multi')
                
                if nano_data.get('gaming'):
                    result.gaming_score = nano_data['gaming'].get('score')
                
                # Anti-bot delay
                await anti_bot_delay()
                
                # Step 2: TechPowerUp
                tpu_found, tpu_data, match_score = await self.scrape_techpowerup(cpu_name)
                result.techpowerup_found = tpu_found
                result.techpowerup_url = tpu_data.get('url', '')
                result.fuzzy_match_score = match_score
                result.fuzzy_matched_name = tpu_data.get('matched_name', '')
                
                if tpu_data.get('specs'):
                    result.die_size_mm2 = tpu_data['specs'].get('die_size_mm2')
                    result.transistors_million = tpu_data['specs'].get('transistors_million')
                    result.is_mcm = tpu_data['specs'].get('is_mcm', False)
                    result.mcm_config = tpu_data['specs'].get('mcm_config', '')
                    result.voltage_range = tpu_data['specs'].get('voltage_range', '')
                    result.process_node = tpu_data['specs'].get('process_node', '')
                
                result.success = result.nanoreview_found or result.techpowerup_found
                
                # Anti-bot delay before next CPU
                if i < len(TEST_CPUS):
                    await anti_bot_delay()
                    
            except Exception as e:
                result.error_message = str(e)
                console.print(f"   ❌ [red]Error: {e}[/red]")
            
            self.results.append(result)
        
        return self.results
    
    def print_summary(self):
        """Print a summary table of all results."""
        console.print("\n")
        console.print(Panel.fit(
            "[bold green]📊 SMOKE TEST SUMMARY[/bold green]",
            border_style="green"
        ))
        
        # Results table
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("CPU", style="cyan")
        table.add_column("NanoReview", justify="center")
        table.add_column("TechPowerUp", justify="center")
        table.add_column("Fuzzy Score", justify="center")
        table.add_column("Die Size", justify="right")
        table.add_column("Transistors", justify="right")
        table.add_column("MCM", justify="center")
        
        for r in self.results:
            nano_status = "✅" if r.nanoreview_found else "❌"
            tpu_status = "✅" if r.techpowerup_found else "❌"
            fuzzy = f"{r.fuzzy_match_score}%" if r.fuzzy_match_score > 0 else "N/A"
            die_size = f"{r.die_size_mm2}mm²" if r.die_size_mm2 else "N/A"
            transistors = f"{r.transistors_million}M" if r.transistors_million else "N/A"
            mcm = "Yes" if r.is_mcm else "No"
            
            table.add_row(
                r.cpu_name[:25] + "..." if len(r.cpu_name) > 25 else r.cpu_name,
                nano_status,
                tpu_status,
                fuzzy,
                die_size,
                transistors,
                mcm
            )
        
        console.print(table)
        
        # Benchmark summary
        console.print("\n[bold]Benchmark Data Extracted:[/bold]")
        for r in self.results:
            if r.benchmarks_extracted:
                console.print(f"  {r.cpu_name}:")
                console.print(f"    CB R23: {r.cinebench_r23_single or 'N/A'} (ST) / {r.cinebench_r23_multi or 'N/A'} (MT)")
                console.print(f"    GB6:    {r.geekbench6_single or 'N/A'} (ST) / {r.geekbench6_multi or 'N/A'} (MT)")
                console.print(f"    Gaming: {r.gaming_score or 'N/A'}")
        
        # Statistics
        total = len(self.results)
        nano_found = sum(1 for r in self.results if r.nanoreview_found)
        tpu_found = sum(1 for r in self.results if r.techpowerup_found)
        has_die = sum(1 for r in self.results if r.die_size_mm2)
        has_trans = sum(1 for r in self.results if r.transistors_million)
        
        console.print(f"\n[bold]Statistics:[/bold]")
        console.print(f"  NanoReview found:    {nano_found}/{total} ({nano_found/total*100:.0f}%)")
        console.print(f"  TechPowerUp found:   {tpu_found}/{total} ({tpu_found/total*100:.0f}%)")
        console.print(f"  Has Die Size:        {has_die}/{total} ({has_die/total*100:.0f}%)")
        console.print(f"  Has Transistors:     {has_trans}/{total} ({has_trans/total*100:.0f}%)")
        
        # Check debug log
        console.print(f"\n📋 Check [cyan]merger_debug.log[/cyan] for low-confidence matches and errors")


# =============================================================================
# MAIN
# =============================================================================

async def main():
    """Run the smoke test."""
    
    console.print("\n[bold]🚀 Starting Smoke Test...[/bold]\n")
    
    # Initialize debug log
    debug_logger.info("=" * 60)
    debug_logger.info("SMOKE TEST STARTED")
    debug_logger.info(f"Timestamp: {datetime.now().isoformat()}")
    debug_logger.info("=" * 60)
    
    # First, test the NameMatcher
    console.print("[bold]📐 Testing NameMatcher Logic:[/bold]")
    test_cases = [
        ("Intel Core Ultra 9 285K", "Core Ultra 9 285K"),
        ("AMD Ryzen 9 9950X3D", "Ryzen 9 9950X3D"),
        ("Intel Core i9-14900K", "Core i9 14900K"),
        ("Intel Core Ultra 7 265K", "Core Ultra 7 265K Processor"),
    ]
    
    for query, candidate in test_cases:
        score = NameMatcher.match_score(query, candidate)
        status = "✅" if score >= 85 else "⚠️"
        console.print(f"  {status} '{query}' vs '{candidate}' = {score}%")
    
    console.print("")
    
    # Launch browser and run tests
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        try:
            scraper = SmokeTestScraper(browser)
            await scraper.run_smoke_test()
            scraper.print_summary()
            
            # Save results to JSON
            results_json = []
            for r in scraper.results:
                results_json.append({
                    'cpu_name': r.cpu_name,
                    'nanoreview_found': r.nanoreview_found,
                    'techpowerup_found': r.techpowerup_found,
                    'fuzzy_match_score': r.fuzzy_match_score,
                    'die_size_mm2': r.die_size_mm2,
                    'transistors_million': r.transistors_million,
                    'is_mcm': r.is_mcm,
                    'process_node': r.process_node,
                    'cinebench_r23_single': r.cinebench_r23_single,
                    'cinebench_r23_multi': r.cinebench_r23_multi,
                })
            
            with open('smoke_test_results.json', 'w') as f:
                json.dump(results_json, f, indent=2)
            
            console.print(f"\n📁 Results saved to [cyan]smoke_test_results.json[/cyan]")
            
        finally:
            await browser.close()
    
    debug_logger.info("SMOKE TEST COMPLETED")
    console.print("\n[bold green]✅ Smoke test complete![/bold green]\n")


if __name__ == '__main__':
    asyncio.run(main())
