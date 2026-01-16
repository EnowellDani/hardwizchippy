"""
AMD Specifications Data Source
==============================
Scrapes CPU specifications from AMD's official product pages.

AMD provides processor specifications through their website at:
- https://www.amd.com/en/products/specifications/processors.html

This scraper extracts comprehensive Ryzen, EPYC, Athlon, and Threadripper
specifications using Playwright for JavaScript-rendered content.

Author: KBitWare
Architecture: Senior Developer Level
"""

import re
import json
import time
import requests
from typing import Dict, List, Optional, Any, Generator
from bs4 import BeautifulSoup
import logging

import sys
sys.path.insert(0, "..")

from core.data_source import (
    DataSourceBase,
    DataSourcePriority,
    CPUSpecification,
    Manufacturer
)

# Playwright for JS-heavy pages
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class AMDSpecsSource(DataSourceBase):
    """
    AMD official specifications data source.

    Scrapes processor data from AMD's product specification pages
    using Playwright for JavaScript rendering.
    """

    # AMD website endpoints
    AMD_BASE = "https://www.amd.com"
    AMD_SPECS = f"{AMD_BASE}/en/products/specifications/processors.html"

    # Product category URLs
    PRODUCT_CATEGORIES = {
        "ryzen_desktop": "/en/products/processors/desktops/ryzen.html",
        "ryzen_mobile": "/en/products/processors/laptop/ryzen.html",
        "threadripper": "/en/products/processors/desktops/ryzen-threadripper.html",
        "epyc": "/en/products/processors/server/epyc.html",
        "athlon": "/en/products/processors/desktops/athlon.html",
    }

    # Request configuration
    REQUEST_DELAY = 1.0  # AMD tends to rate limit more aggressively
    REQUEST_TIMEOUT = 30

    def __init__(self, use_playwright: bool = True):
        super().__init__(
            name="amd_specs",
            priority=DataSourcePriority.OFFICIAL,
            manufacturer=Manufacturer.AMD
        )
        self.use_playwright = use_playwright and PLAYWRIGHT_AVAILABLE
        self._playwright = None
        self._browser = None
        self._page = None
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        })

    @property
    def source_url(self) -> str:
        return self.AMD_BASE

    def _init_playwright(self) -> bool:
        """Initialize Playwright browser."""
        if not PLAYWRIGHT_AVAILABLE:
            return False
        if self._browser is None:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=True)
            context = self._browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            self._page = context.new_page()
        return True

    def _close_playwright(self):
        """Clean up Playwright resources."""
        if self._browser:
            self._browser.close()
            self._playwright.stop()
            self._browser = None
            self._page = None

    def fetch_cpu_list(self) -> Generator[Dict[str, Any], None, None]:
        """
        Fetch list of AMD processors from specifications page.

        Uses the AMD product specifications table which lists all processors.
        """
        self.logger.info("Fetching AMD processors from specifications page...")

        if not self._init_playwright():
            self.logger.error("Playwright not available, falling back to static scraping")
            yield from self._fetch_static()
            return

        try:
            # Navigate to specs page
            self._page.goto(self.AMD_SPECS, wait_until="networkidle", timeout=60000)
            time.sleep(2)  # Wait for JS to fully render

            # AMD's spec page has filters - we need to expand all
            # Try to show all products by adjusting filters
            try:
                # Click "Show All" or expand filters if available
                show_all = self._page.query_selector("button:has-text('Show All'), a:has-text('View All')")
                if show_all:
                    show_all.click()
                    time.sleep(1)
            except:
                pass

            # Parse the products table
            html = self._page.content()
            soup = BeautifulSoup(html, "html.parser")

            # Find product rows in the specifications table
            product_rows = soup.select("tr.product-row, tbody tr[data-product-id]")

            if not product_rows:
                # Try alternative selectors
                product_rows = soup.select("table tbody tr")

            seen_names = set()

            for row in product_rows:
                try:
                    # Find product link
                    link = row.select_one("a[href*='/products/']")
                    if not link:
                        continue

                    name = link.get_text(strip=True)
                    if not name or name in seen_names:
                        continue

                    href = link.get("href", "")
                    if href.startswith("/"):
                        href = self.AMD_BASE + href

                    seen_names.add(name)

                    # Extract inline specs if available
                    cells = row.select("td")
                    inline_specs = {}
                    if len(cells) >= 2:
                        inline_specs["raw_cells"] = [c.get_text(strip=True) for c in cells]

                    yield {
                        "name": name,
                        "url": href,
                        "inline_specs": inline_specs
                    }

                except Exception as e:
                    self.logger.debug(f"Error parsing row: {e}")
                    continue

            # Also scrape individual product categories for more comprehensive coverage
            yield from self._fetch_from_categories()

        except Exception as e:
            self.logger.error(f"Error fetching AMD specs page: {e}")
            yield from self._fetch_from_categories()

    def _fetch_from_categories(self) -> Generator[Dict[str, Any], None, None]:
        """Fetch processors from individual category pages."""
        self.logger.info("Fetching AMD processors from category pages...")

        if not self._init_playwright():
            return

        seen_names = set()

        for category_name, category_path in self.PRODUCT_CATEGORIES.items():
            try:
                url = f"{self.AMD_BASE}{category_path}"
                self.logger.info(f"Scraping category: {category_name}")

                self._page.goto(url, wait_until="networkidle", timeout=60000)
                time.sleep(2)

                html = self._page.content()
                soup = BeautifulSoup(html, "html.parser")

                # Find product cards/links
                product_links = soup.select(
                    "a[href*='/products/processors/'], "
                    "a[href*='/product/'], "
                    ".product-card a, "
                    ".product-tile a"
                )

                for link in product_links:
                    href = link.get("href", "")
                    name = link.get_text(strip=True)

                    # Skip if not a product page
                    if "/specifications" in href or not name:
                        continue

                    # Normalize URL
                    if href.startswith("/"):
                        href = self.AMD_BASE + href

                    if name in seen_names:
                        continue
                    seen_names.add(name)

                    yield {
                        "name": name,
                        "url": href,
                        "category": category_name
                    }

                time.sleep(self.REQUEST_DELAY)

            except Exception as e:
                self.logger.warning(f"Error scraping category {category_name}: {e}")

    def _fetch_static(self) -> Generator[Dict[str, Any], None, None]:
        """Fallback static scraping without JavaScript."""
        # This is limited but provides some data
        try:
            response = self._session.get(self.AMD_SPECS, timeout=self.REQUEST_TIMEOUT)
            soup = BeautifulSoup(response.text, "html.parser")

            for link in soup.select("a[href*='/products/processors/']"):
                name = link.get_text(strip=True)
                href = link.get("href", "")
                if name and href:
                    yield {
                        "name": name,
                        "url": href if href.startswith("http") else self.AMD_BASE + href
                    }

        except Exception as e:
            self.logger.error(f"Static scraping failed: {e}")

    def fetch_cpu_details(self, cpu_ref: Dict[str, Any]) -> Optional[CPUSpecification]:
        """Fetch detailed specifications for an AMD processor."""
        url = cpu_ref.get("url")
        if not url:
            return None

        try:
            if self.use_playwright and self._init_playwright():
                self._page.goto(url, wait_until="networkidle", timeout=60000)
                time.sleep(1)
                html = self._page.content()
            else:
                response = self._session.get(url, timeout=self.REQUEST_TIMEOUT)
                html = response.text

            soup = BeautifulSoup(html, "html.parser")
            raw_data = self._parse_product_page(soup)
            raw_data["source_url"] = url
            raw_data["name"] = raw_data.get("name") or cpu_ref.get("name")

            time.sleep(self.REQUEST_DELAY)
            return self.normalize_data(raw_data)

        except Exception as e:
            self.logger.warning(f"Error fetching details for {cpu_ref.get('name')}: {e}")
            return None

    def _parse_product_page(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Parse AMD product page HTML."""
        data = {}

        # Get product name
        title = soup.select_one("h1.product-title, h1.page-title, .product-name h1")
        if title:
            data["name"] = title.get_text(strip=True)

        # Parse specification tables
        spec_tables = soup.select("table.specs-table, .specifications table, .product-specs table")

        for table in spec_tables:
            rows = table.select("tr")
            for row in rows:
                cells = row.select("th, td")
                if len(cells) >= 2:
                    label = cells[0].get_text(strip=True).lower()
                    value = cells[1].get_text(strip=True)
                    if value and value not in ["N/A", "-", "—"]:
                        data[label] = value

        # Also try definition lists
        for dl in soup.select("dl.specs, .specifications dl"):
            dts = dl.select("dt")
            dds = dl.select("dd")
            for dt, dd in zip(dts, dds):
                label = dt.get_text(strip=True).lower()
                value = dd.get_text(strip=True)
                if value:
                    data[label] = value

        # Try key-value pairs in divs
        for item in soup.select(".spec-item, .spec-row, [class*='spec']"):
            label_elem = item.select_one(".spec-label, .label, dt, th")
            value_elem = item.select_one(".spec-value, .value, dd, td")
            if label_elem and value_elem:
                label = label_elem.get_text(strip=True).lower()
                value = value_elem.get_text(strip=True)
                if value:
                    data[label] = value

        return data

    def normalize_data(self, raw_data: Dict[str, Any]) -> CPUSpecification:
        """Normalize AMD data to unified format."""
        spec = CPUSpecification(
            name=raw_data.get("name", "Unknown AMD Processor"),
            manufacturer=Manufacturer.AMD,
            source="amd_specs",
            source_url=raw_data.get("source_url"),
            raw_data=raw_data
        )

        # === Core Configuration ===
        spec.cores = self._parse_int(
            raw_data.get("# of cpu cores") or
            raw_data.get("cpu cores") or
            raw_data.get("cores")
        )
        spec.threads = self._parse_int(
            raw_data.get("# of threads") or
            raw_data.get("threads")
        )

        # === Clock Speeds ===
        spec.base_clock = self._parse_clock(
            raw_data.get("base clock") or
            raw_data.get("base frequency") or
            raw_data.get("processor base frequency")
        )
        spec.boost_clock = self._parse_clock(
            raw_data.get("max. boost clock") or
            raw_data.get("boost clock") or
            raw_data.get("max boost frequency")
        )

        # === Cache ===
        spec.l1_cache = self._parse_cache(raw_data.get("l1 cache"))
        spec.l2_cache = self._parse_cache(
            raw_data.get("l2 cache") or
            raw_data.get("total l2 cache")
        )
        spec.l3_cache = self._parse_cache(
            raw_data.get("l3 cache") or
            raw_data.get("total l3 cache")
        )

        # === Power ===
        spec.tdp = self._parse_power(
            raw_data.get("default tdp") or
            raw_data.get("tdp") or
            raw_data.get("thermal design power")
        )

        # === Architecture ===
        spec.socket_name = raw_data.get("cpu socket") or raw_data.get("socket")
        spec.process_node = raw_data.get("processor technology") or raw_data.get("cmos")

        # === Memory ===
        spec.memory_type = raw_data.get("memory type") or raw_data.get("system memory type")
        spec.memory_channels = self._parse_int(raw_data.get("memory channels"))
        spec.max_memory_gb = self._parse_int(raw_data.get("max memory"))

        # === Graphics ===
        gpu_name = raw_data.get("graphics model") or raw_data.get("integrated graphics")
        if gpu_name and gpu_name.lower() not in ["none", "n/a", "-", "discrete"]:
            spec.has_integrated_gpu = True
            spec.integrated_gpu_name = gpu_name
        else:
            spec.has_integrated_gpu = False

        # === PCIe ===
        pcie_str = raw_data.get("pci express version") or raw_data.get("pcie version") or ""
        if pcie_str:
            match = re.search(r"(\d+\.?\d*)", pcie_str)
            if match:
                spec.pcie_version = f"PCIe {match.group(1)}"
        spec.pcie_lanes = self._parse_int(raw_data.get("pcie lanes") or raw_data.get("max pcie lanes"))

        # === Launch Info ===
        spec.launch_date = raw_data.get("launch date") or raw_data.get("release date")
        spec.launch_msrp = self._parse_price(raw_data.get("launch price") or raw_data.get("msrp"))

        return spec

    # === Parsing Helpers ===

    def _parse_int(self, value: Any) -> Optional[int]:
        """Parse integer from various formats."""
        if value is None:
            return None
        if isinstance(value, int):
            return value
        text = str(value)
        match = re.search(r"([\d,]+)", text)
        return int(match.group(1).replace(",", "")) if match else None

    def _parse_clock(self, value: Any) -> Optional[int]:
        """Parse clock speed to MHz."""
        if value is None:
            return None
        text = str(value)
        match = re.search(r"([\d.]+)\s*(GHz|MHz)", text, re.I)
        if match:
            num = float(match.group(1))
            unit = match.group(2).upper()
            return int(num * 1000) if unit == "GHZ" else int(num)
        return None

    def _parse_cache(self, value: Any) -> Optional[int]:
        """Parse cache size to KB."""
        if value is None:
            return None
        text = str(value)
        match = re.search(r"([\d.]+)\s*(GB|MB|KB)", text, re.I)
        if match:
            num = float(match.group(1))
            unit = match.group(2).upper()
            if unit == "GB":
                return int(num * 1024 * 1024)
            elif unit == "MB":
                return int(num * 1024)
            return int(num)
        return None

    def _parse_power(self, value: Any) -> Optional[int]:
        """Parse power in Watts."""
        if value is None:
            return None
        text = str(value)
        match = re.search(r"(\d+)\s*W", text, re.I)
        return int(match.group(1)) if match else None

    def _parse_price(self, value: Any) -> Optional[float]:
        """Parse price to float."""
        if value is None:
            return None
        text = str(value)
        match = re.search(r"\$?([\d,]+(?:\.\d{2})?)", text)
        return float(match.group(1).replace(",", "")) if match else None

    def __del__(self):
        """Cleanup on deletion."""
        self._close_playwright()


# === Standalone Test ===

def main():
    """Test AMD specs scraper."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    scraper = AMDSpecsSource(use_playwright=True)

    print("Testing AMD Specs scraper...")
    print("=" * 60)

    # Test with limit
    results = scraper.scrape_all(limit=5)

    for cpu in results:
        print(f"\n{cpu.name}")
        print(f"  Cores: {cpu.cores}, Threads: {cpu.threads}")
        print(f"  Base: {cpu.base_clock} MHz, Boost: {cpu.boost_clock} MHz")
        print(f"  TDP: {cpu.tdp}W")
        print(f"  Socket: {cpu.socket_name}")

    scraper._close_playwright()
    print(f"\n\nTotal scraped: {len(results)}")


if __name__ == "__main__":
    main()
