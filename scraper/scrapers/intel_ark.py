"""
Intel ARK Data Source
=====================
Scrapes CPU specifications from Intel's ARK database using multiple methods:
1. Intel OData API (official, preferred)
2. Direct ARK website scraping with Playwright (fallback)

This provides comprehensive Intel processor specifications including:
- Core/thread counts, clock speeds, cache sizes
- TDP, socket, process node, memory support
- Launch dates, pricing, product status

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


class IntelARKSource(DataSourceBase):
    """
    Intel ARK data source implementation.

    Uses Intel's OData API when possible, with Playwright-based
    web scraping as a fallback for comprehensive data extraction.
    """

    # Intel OData API endpoints
    ODATA_BASE = "https://odata.intel.com/API/v1_0/Products"
    ODATA_PROCESSORS = f"{ODATA_BASE}/Processors()"

    # ARK website endpoints
    ARK_BASE = "https://ark.intel.com"
    ARK_SEARCH = f"{ARK_BASE}/content/www/us/en/ark/search.html"

    # Request configuration
    REQUEST_DELAY = 0.5  # Seconds between requests
    REQUEST_TIMEOUT = 30

    def __init__(self, use_odata: bool = True, use_playwright: bool = True):
        super().__init__(
            name="intel_ark",
            priority=DataSourcePriority.OFFICIAL,
            manufacturer=Manufacturer.INTEL
        )
        self.use_odata = use_odata
        self.use_playwright = use_playwright and PLAYWRIGHT_AVAILABLE
        self._playwright = None
        self._browser = None
        self._page = None
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json"
        })

    @property
    def source_url(self) -> str:
        return self.ARK_BASE

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
        Fetch list of Intel processors.

        First attempts OData API, falls back to web scraping.
        """
        if self.use_odata:
            yield from self._fetch_via_odata()
        else:
            yield from self._fetch_via_scraping()

    def _fetch_via_odata(self) -> Generator[Dict[str, Any], None, None]:
        """Fetch processor list via Intel OData API."""
        self.logger.info("Fetching Intel processors via OData API...")

        # OData query for desktop and mobile processors
        filters = [
            "ProcessorType eq 'Desktop'",
            "ProcessorType eq 'Mobile'",
            "ProcessorType eq 'Server'",
        ]

        for filter_query in filters:
            try:
                skip = 0
                page_size = 100

                while True:
                    url = (
                        f"{self.ODATA_PROCESSORS}?"
                        f"$filter={filter_query}&"
                        f"$skip={skip}&$top={page_size}&"
                        f"$select=ProductId,CodeNameText,ProcessorNumber,StatusCodeText,"
                        f"NumCores,NumThreads,ClockSpeed,ClockSpeedMax,Cache,TDP,"
                        f"SocketsSupported,Lithography,LaunchDate,RecommendedCustomerPrice"
                    )

                    response = self._session.get(url, timeout=self.REQUEST_TIMEOUT)

                    if response.status_code != 200:
                        self.logger.warning(f"OData API returned {response.status_code}")
                        break

                    data = response.json()
                    items = data.get("value", [])

                    if not items:
                        break

                    for item in items:
                        yield {
                            "id": item.get("ProductId"),
                            "name": item.get("ProcessorNumber", "Unknown"),
                            "raw_data": item,
                            "source": "odata"
                        }

                    skip += page_size
                    time.sleep(self.REQUEST_DELAY)

            except Exception as e:
                self.logger.error(f"OData API error: {e}")
                # Fall back to scraping
                yield from self._fetch_via_scraping()
                return

    def _fetch_via_scraping(self) -> Generator[Dict[str, Any], None, None]:
        """Fetch processor list via web scraping."""
        self.logger.info("Fetching Intel processors via web scraping...")

        if not self._init_playwright():
            self.logger.error("Playwright not available for scraping")
            return

        # Product categories to scrape
        categories = [
            "/content/www/us/en/ark/products/series/230584/intel-core-ultra-processors.html",
            "/content/www/us/en/ark/products/series/195733/13th-generation-intel-core-processors.html",
            "/content/www/us/en/ark/products/series/217839/14th-generation-intel-core-processors.html",
            "/content/www/us/en/ark/products/series/122139/intel-core-processors.html",
        ]

        seen_ids = set()

        for category in categories:
            try:
                url = f"{self.ARK_BASE}{category}"
                self._page.goto(url, wait_until="networkidle", timeout=60000)
                time.sleep(1)

                # Find all product links
                links = self._page.query_selector_all("a[href*='/ark/products/']")

                for link in links:
                    href = link.get_attribute("href")
                    if not href or "/series/" in href:
                        continue

                    # Extract product ID from URL
                    match = re.search(r'/products/(\d+)/', href)
                    if match:
                        product_id = match.group(1)
                        if product_id in seen_ids:
                            continue
                        seen_ids.add(product_id)

                        name = link.text_content().strip()
                        yield {
                            "id": product_id,
                            "name": name,
                            "url": f"{self.ARK_BASE}{href}" if href.startswith("/") else href,
                            "source": "scraping"
                        }

                time.sleep(self.REQUEST_DELAY)

            except Exception as e:
                self.logger.warning(f"Error scraping category {category}: {e}")

    def fetch_cpu_details(self, cpu_ref: Dict[str, Any]) -> Optional[CPUSpecification]:
        """Fetch detailed specifications for an Intel processor."""
        if cpu_ref.get("source") == "odata" and "raw_data" in cpu_ref:
            # Already have full data from OData
            return self.normalize_data(cpu_ref["raw_data"])

        # Need to scrape detail page
        product_id = cpu_ref.get("id")
        url = cpu_ref.get("url") or f"{self.ARK_BASE}/content/www/us/en/ark/products/{product_id}.html"

        try:
            if self.use_playwright and self._init_playwright():
                self._page.goto(url, wait_until="networkidle", timeout=60000)
                html = self._page.content()
            else:
                response = self._session.get(url, timeout=self.REQUEST_TIMEOUT)
                html = response.text

            soup = BeautifulSoup(html, "html.parser")
            raw_data = self._parse_ark_page(soup)
            raw_data["product_id"] = product_id
            raw_data["source_url"] = url

            time.sleep(self.REQUEST_DELAY)
            return self.normalize_data(raw_data)

        except Exception as e:
            self.logger.warning(f"Error fetching details for {cpu_ref.get('name')}: {e}")
            return None

    def _parse_ark_page(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Parse Intel ARK product page HTML."""
        data = {}

        # Get product name
        title = soup.select_one("h1.product-family-title-text, span.ark-accessible-color")
        if title:
            data["name"] = title.get_text(strip=True)

        # Parse specification sections
        spec_sections = soup.select("div.specs-section, section.specs-section")

        for section in spec_sections:
            rows = section.select("li.ark-tech-data, div.ark-spec-row")
            for row in rows:
                label_elem = row.select_one("span.ark-label, .label")
                value_elem = row.select_one("span.ark-value, .value, span[data-key]")

                if label_elem and value_elem:
                    label = label_elem.get_text(strip=True).lower()
                    value = value_elem.get_text(strip=True)

                    if value and value not in ["N/A", "-"]:
                        data[label] = value

        return data

    def normalize_data(self, raw_data: Dict[str, Any]) -> CPUSpecification:
        """Normalize Intel ARK data to unified format."""
        spec = CPUSpecification(
            name=raw_data.get("ProcessorNumber") or raw_data.get("name", "Unknown"),
            manufacturer=Manufacturer.INTEL,
            source="intel_ark",
            source_url=raw_data.get("source_url"),
            source_id=str(raw_data.get("ProductId") or raw_data.get("product_id")),
            raw_data=raw_data
        )

        # === Core Configuration ===
        spec.cores = self._parse_int(raw_data.get("NumCores") or raw_data.get("total cores"))
        spec.threads = self._parse_int(raw_data.get("NumThreads") or raw_data.get("total threads"))
        spec.p_cores = self._parse_int(raw_data.get("# of performance-cores"))
        spec.e_cores = self._parse_int(raw_data.get("# of efficient-cores"))

        # === Clock Speeds ===
        spec.base_clock = self._parse_clock(
            raw_data.get("ClockSpeed") or raw_data.get("processor base frequency")
        )
        spec.boost_clock = self._parse_clock(
            raw_data.get("ClockSpeedMax") or raw_data.get("max turbo frequency")
        )
        spec.p_core_base_clock = self._parse_clock(raw_data.get("performance-core base frequency"))
        spec.p_core_boost_clock = self._parse_clock(raw_data.get("performance-core max turbo frequency"))
        spec.e_core_base_clock = self._parse_clock(raw_data.get("efficient-core base frequency"))
        spec.e_core_boost_clock = self._parse_clock(raw_data.get("efficient-core max turbo frequency"))

        # === Cache ===
        cache_str = raw_data.get("Cache") or raw_data.get("cache") or ""
        spec.l3_cache = self._parse_cache(cache_str)
        spec.l2_cache = self._parse_cache(raw_data.get("l2 cache"))

        # === Power ===
        spec.tdp = self._parse_power(raw_data.get("TDP") or raw_data.get("tdp"))
        spec.base_power = self._parse_power(raw_data.get("processor base power"))
        spec.max_turbo_power = self._parse_power(raw_data.get("maximum turbo power"))

        # === Architecture ===
        spec.codename = raw_data.get("CodeNameText") or raw_data.get("code name")
        spec.socket_name = raw_data.get("SocketsSupported") or raw_data.get("sockets supported")
        spec.process_node = raw_data.get("Lithography") or raw_data.get("lithography")

        # === Memory ===
        spec.memory_type = raw_data.get("memory types")
        spec.max_memory_gb = self._parse_int(raw_data.get("max memory size"))
        spec.memory_channels = self._parse_int(raw_data.get("max # of memory channels"))

        # === Graphics ===
        gpu_name = raw_data.get("processor graphics")
        if gpu_name and gpu_name.lower() not in ["none", "n/a", "-"]:
            spec.has_integrated_gpu = True
            spec.integrated_gpu_name = gpu_name
        else:
            spec.has_integrated_gpu = False

        # === PCIe ===
        pcie_str = raw_data.get("pci express revision") or ""
        if pcie_str:
            spec.pcie_version = pcie_str
        spec.pcie_lanes = self._parse_int(raw_data.get("max # of pci express lanes"))

        # === Launch Info ===
        spec.launch_date = raw_data.get("LaunchDate") or raw_data.get("launch date")
        spec.launch_msrp = self._parse_price(
            raw_data.get("RecommendedCustomerPrice") or raw_data.get("recommended customer price")
        )

        # === Status ===
        status = (raw_data.get("StatusCodeText") or raw_data.get("status") or "").lower()
        spec.is_released = "launched" in status or "shipping" in status
        spec.is_discontinued = "discontinued" in status or "end of life" in status

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
    """Test Intel ARK scraper."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    scraper = IntelARKSource(use_odata=True, use_playwright=True)

    print("Testing Intel ARK scraper...")
    print("=" * 60)

    # Test with limit
    results = scraper.scrape_all(limit=5)

    for cpu in results:
        print(f"\n{cpu.name}")
        print(f"  Cores: {cpu.cores}, Threads: {cpu.threads}")
        print(f"  Base: {cpu.base_clock} MHz, Boost: {cpu.boost_clock} MHz")
        print(f"  TDP: {cpu.tdp}W, Cache: {cpu.l3_cache} KB")
        print(f"  Socket: {cpu.socket_name}, Process: {cpu.process_node}")

    scraper._close_playwright()
    print(f"\n\nTotal scraped: {len(results)}")


if __name__ == "__main__":
    main()
