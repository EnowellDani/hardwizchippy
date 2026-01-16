"""
TechPowerUp CPU Specs Scraper - Enhanced with Playwright
Extracts comprehensive CPU specifications from detail pages.
"""
import re
from typing import Dict, List, Optional, Any, Generator
from bs4 import BeautifulSoup
import logging
import sys
sys.path.insert(0, "..")
from core.base_scraper import BaseScraper

# Try Playwright for better scraping
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class TechPowerUpScraper(BaseScraper):
    BASE_URL = "https://www.techpowerup.com"
    CPU_LIST_URL = f"{BASE_URL}/cpu-specs/"

    def __init__(self, use_playwright: bool = True):
        super().__init__("techpowerup")
        self.logger = logging.getLogger("scraper.techpowerup")
        self.use_playwright = use_playwright and PLAYWRIGHT_AVAILABLE
        self._browser = None
        self._context = None
        self._page = None

    def scrape_list(self) -> Generator[Dict[str, Any], None, None]:
        """Scrape all CPUs using Playwright for better results."""
        if self.use_playwright:
            yield from self._scrape_with_playwright()
        else:
            yield from self._scrape_with_requests()

    def _scrape_with_playwright(self) -> Generator[Dict[str, Any], None, None]:
        """Use Playwright to scrape the full CPU list."""
        seen = set()

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = context.new_page()

            self.logger.info("Loading TechPowerUp CPU list with Playwright...")
            page.goto(self.CPU_LIST_URL, wait_until="networkidle", timeout=60000)

            # Find all CPU links in the table
            cpu_links = page.query_selector_all("table.items-desktop-table tr a[href*='/cpu-specs/']")
            self.logger.info(f"Found {len(cpu_links)} CPU links")

            for link in cpu_links:
                try:
                    href = link.get_attribute("href")
                    name = link.text_content().strip()

                    if not href or not name:
                        continue

                    cpu_url = href if href.startswith("http") else self.BASE_URL + href

                    if cpu_url in seen:
                        continue

                    seen.add(cpu_url)
                    yield {"name": name, "url": cpu_url}

                except Exception as e:
                    self.logger.warning(f"Error parsing CPU link: {e}")

            browser.close()

        self.logger.info(f"Total unique CPUs found: {len(seen)}")

    def _scrape_with_requests(self) -> Generator[Dict[str, Any], None, None]:
        """Fallback to requests-based scraping."""
        seen = set()

        self.logger.info("Scraping TechPowerUp with requests...")
        soup = self.get_soup(self.CPU_LIST_URL)

        if not soup:
            self.logger.error("Failed to get TechPowerUp page")
            return

        # Find CPU table
        table = soup.find("table", class_="items-desktop-table")
        if not table:
            self.logger.warning("No CPU table found")
            return

        for row in table.find_all("tr")[1:]:
            cells = row.find_all("td")
            if len(cells) < 2:
                continue

            link = cells[0].find("a")
            if not link:
                continue

            cpu_url = link.get("href", "")
            if not cpu_url.startswith("http"):
                cpu_url = self.BASE_URL + cpu_url

            if cpu_url in seen:
                continue

            seen.add(cpu_url)
            yield {"name": link.get_text(strip=True), "url": cpu_url}

    def _init_playwright(self):
        """Initialize Playwright browser for detail page scraping."""
        if not PLAYWRIGHT_AVAILABLE:
            return False
        if self._browser is None:
            from playwright.sync_api import sync_playwright
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=True)
            self._context = self._browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            self._page = self._context.new_page()
        return True

    def _close_playwright(self):
        """Close Playwright browser."""
        if self._browser:
            self._browser.close()
            self._playwright.stop()
            self._browser = None
            self._page = None

    def scrape_detail(self, url: str) -> Optional[Dict[str, Any]]:
        """Scrape detailed CPU specifications using Playwright for JS rendering."""
        data = {"techpowerup_url": url}

        # Use Playwright for detail pages (they need JS rendering)
        if self.use_playwright and self._init_playwright():
            try:
                self._page.goto(url, wait_until="networkidle", timeout=60000)
                html = self._page.content()
                soup = BeautifulSoup(html, "html.parser")
            except Exception as e:
                self.logger.warning(f"Playwright failed for {url}: {e}")
                soup = self.get_soup(url)
                if not soup:
                    return None
        else:
            soup = self.get_soup(url)
            if not soup:
                return None

        # Get CPU name from page title
        title = soup.select_one("h1.cpuname")
        if title:
            data["name"] = title.get_text(strip=True)

        # Parse ALL section.details tables (this is the key fix!)
        sections = soup.select("section.details")
        for section in sections:
            table = section.find("table")
            if table:
                data.update(self._parse_spec_table(table))

        # Try to get image
        img = soup.select_one("div.chip-image img, img.chip-image, .gpudb-large-image img")
        if img:
            src = img.get("src", "")
            if src:
                data["image_url"] = src if src.startswith("http") else self.BASE_URL + src

        return data

    def _parse_spec_table(self, table) -> Dict[str, Any]:
        """Parse a specifications table from any section."""
        data = {}

        for row in table.find_all("tr"):
            cells = row.find_all(["th", "td"])
            if len(cells) != 2:
                continue

            # Clean label: lowercase and remove trailing colon
            label = cells[0].get_text(strip=True).lower().rstrip(':')
            value = cells[1].get_text(strip=True)

            if not value or value in ["-", "Unknown"]:
                continue

            self._map_field(data, label, value)

        return data

    def _map_field(self, data: Dict, label: str, value: str):
        """Map spec fields to database columns based on TechPowerUp's actual labels."""

        # === CORE CONFIG SECTION ===
        if label == "# of cores":
            data["cores"] = self._parse_int(value)
        elif label == "# of threads":
            data["threads"] = self._parse_int(value)
        elif label == "integrated graphics":
            if value and value != "N/A":
                data["integrated_gpu_name"] = value
                data["has_integrated_gpu"] = True
            else:
                data["has_integrated_gpu"] = False

        # === PERFORMANCE SECTION ===
        elif label == "frequency":
            data["base_clock"] = self._parse_clock(value)
        elif label == "turbo clock":
            data["boost_clock"] = self._parse_clock(value)
        elif label == "tdp":
            data["tdp"] = self._parse_power(value)

        # === PHYSICAL SECTION ===
        elif label == "socket":
            data["socket_name"] = value
        elif label == "process size":
            data["process_node"] = value
        elif label == "foundry":
            data["fab_processor"] = value
        elif label == "transistors":
            data["transistors_million"] = self._parse_transistors(value)
        elif label == "die size":
            data["die_size_mm2"] = self._parse_die_size(value)

        # === CACHE SECTION ===
        elif label == "cache l1":
            data["l1_cache"] = self._parse_cache_per_core(value)
        elif label == "cache l2":
            data["l2_cache"] = self._parse_cache_per_core(value)
        elif label == "cache l3":
            data["l3_cache"] = self._parse_cache(value)

        # === ARCHITECTURE SECTION ===
        elif label == "codename":
            data["codename"] = value
        elif label == "generation":
            data["microarchitecture"] = value
        elif label == "memory support":
            data["memory_type"] = value
        elif label == "memory bus":
            data["memory_channels"] = self._parse_memory_channels(value)
        elif label == "max memory" or label == "max memory size":
            data["max_memory_gb"] = self._parse_memory_size(value)
        elif label == "pci-express":
            # Parse both version and lanes from "Gen 4, 20 Lanes(CPU only)"
            pcie_data = self._parse_pcie(value)
            data.update(pcie_data)

        # === PROCESSOR SECTION ===
        elif label == "release date":
            data["launch_date_raw"] = value
        elif label == "launch price":
            data["launch_msrp"] = self._parse_price(value)
        elif label == "market":
            data["market_segment"] = value

        # === LEGACY FALLBACKS (for older page formats) ===
        elif "cores" in label and "thread" not in label:
            if "cores" not in data:
                data["cores"] = self._parse_int(value)
        elif "threads" in label:
            if "threads" not in data:
                data["threads"] = self._parse_int(value)
        elif "base" in label and "clock" in label:
            if "base_clock" not in data:
                data["base_clock"] = self._parse_clock(value)
        elif "boost" in label or ("turbo" in label and "clock" not in label):
            if "boost_clock" not in data:
                data["boost_clock"] = self._parse_clock(value)
        elif "l1 cache" in label or "l1cache" in label:
            if "l1_cache" not in data:
                data["l1_cache"] = self._parse_cache(value)
        elif "l2 cache" in label or "l2cache" in label:
            if "l2_cache" not in data:
                data["l2_cache"] = self._parse_cache(value)
        elif "l3 cache" in label or "l3cache" in label:
            if "l3_cache" not in data:
                data["l3_cache"] = self._parse_cache(value)

    def _parse_int(self, text: str) -> Optional[int]:
        match = re.search(r"([\d,]+)", text)
        return int(match.group(1).replace(",", "")) if match else None

    def _parse_clock(self, text: str) -> Optional[int]:
        """Parse clock speed to MHz."""
        match = re.search(r"([\d.]+)\s*(GHz|MHz)", text, re.I)
        if match:
            value = float(match.group(1))
            unit = match.group(2).upper()
            return int(value * 1000) if unit == "GHZ" else int(value)
        return None

    def _parse_cache(self, text: str) -> Optional[int]:
        """Parse cache size to KB."""
        match = re.search(r"([\d.]+)\s*(GB|MB|KB)", text, re.I)
        if match:
            value = float(match.group(1))
            unit = match.group(2).upper()
            if unit == "GB":
                return int(value * 1024 * 1024)
            elif unit == "MB":
                return int(value * 1024)
            return int(value)
        return None

    def _parse_power(self, text: str) -> Optional[int]:
        match = re.search(r"(\d+)\s*W", text, re.I)
        return int(match.group(1)) if match else None

    def _parse_price(self, text: str) -> Optional[float]:
        match = re.search(r"\$?([\d,]+(?:\.\d{2})?)", text)
        return float(match.group(1).replace(",", "")) if match else None

    def _parse_memory_size(self, text: str) -> Optional[int]:
        """Parse memory size to GB."""
        match = re.search(r"(\d+)\s*(TB|GB)", text, re.I)
        if match:
            value = int(match.group(1))
            unit = match.group(2).upper()
            return value * 1024 if unit == "TB" else value
        return None

    def _parse_transistors(self, text: str) -> Optional[int]:
        """Parse transistor count to millions. E.g., '4,150 million' -> 4150"""
        match = re.search(r"([\d,]+(?:\.\d+)?)\s*(billion|million)", text, re.I)
        if match:
            # Remove commas and convert to float
            value = float(match.group(1).replace(",", ""))
            unit = match.group(2).lower()
            return int(value * 1000) if unit == "billion" else int(value)
        return None

    def _parse_die_size(self, text: str) -> Optional[float]:
        match = re.search(r"([\d.]+)\s*mm", text, re.I)
        return float(match.group(1)) if match else None

    def _parse_cache_per_core(self, text: str) -> Optional[int]:
        """Parse cache like '64 KB (per core)' or '512 KB (per core)' to total KB."""
        # First try to get the value
        match = re.search(r"([\d.]+)\s*(GB|MB|KB)", text, re.I)
        if match:
            value = float(match.group(1))
            unit = match.group(2).upper()
            if unit == "GB":
                return int(value * 1024 * 1024)
            elif unit == "MB":
                return int(value * 1024)
            return int(value)
        return None

    def _parse_memory_channels(self, text: str) -> Optional[int]:
        """Parse memory bus like 'Dual-channel', 'Quad-channel' to number."""
        text_lower = text.lower()
        if "single" in text_lower:
            return 1
        elif "dual" in text_lower:
            return 2
        elif "triple" in text_lower:
            return 3
        elif "quad" in text_lower:
            return 4
        elif "hexa" in text_lower or "six" in text_lower:
            return 6
        elif "octa" in text_lower or "eight" in text_lower:
            return 8
        # Try to extract a number directly
        match = re.search(r"(\d+)", text)
        return int(match.group(1)) if match else None

    def _parse_pcie(self, text: str) -> Dict[str, Any]:
        """Parse PCIe like 'Gen 4, 20 Lanes(CPU only)' to version and lanes."""
        result = {}

        # Parse version (Gen 3, Gen 4, Gen 5, etc.)
        version_match = re.search(r"Gen\s*(\d+)", text, re.I)
        if version_match:
            result["pcie_version"] = f"PCIe {version_match.group(1)}.0"

        # Parse lanes
        lanes_match = re.search(r"(\d+)\s*Lanes?", text, re.I)
        if lanes_match:
            result["pcie_lanes"] = int(lanes_match.group(1))

        return result


def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    scraper = TechPowerUpScraper(use_playwright=True)
    result = scraper.run(limit=10)
    print(f"Scraped {len(result)} CPUs")
    if result:
        print(f"Sample: {result[0]}")


if __name__ == "__main__":
    main()
