"""
TechPowerUp CPU Specs Scraper - Enhanced with Playwright
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

    def scrape_detail(self, url: str) -> Optional[Dict[str, Any]]:
        """Scrape detailed CPU specifications."""
        soup = self.get_soup(url)
        if not soup:
            return None

        data = {"techpowerup_url": url}

        # Parse spec table
        spec_table = soup.find("table", class_="specs")
        if spec_table:
            data.update(self._parse_spec_table(spec_table))

        # Try to get image
        img = soup.select_one("div.chip-image img, img.chip-image")
        if img:
            src = img.get("src", "")
            if src:
                data["image_url"] = src if src.startswith("http") else self.BASE_URL + src

        return data

    def _parse_spec_table(self, table) -> Dict[str, Any]:
        """Parse the specifications table."""
        data = {}

        for row in table.find_all("tr"):
            cells = row.find_all(["th", "td"])
            if len(cells) != 2:
                continue

            label = cells[0].get_text(strip=True).lower()
            value = cells[1].get_text(strip=True)

            if not value or value in ["N/A", "-", "Unknown"]:
                continue

            self._map_field(data, label, value)

        return data

    def _map_field(self, data: Dict, label: str, value: str):
        """Map spec fields to database columns."""
        # Core specs
        if "cores" in label and "thread" not in label:
            data["cores"] = self._parse_int(value)
        elif "threads" in label:
            data["threads"] = self._parse_int(value)
        elif "base" in label and "clock" in label:
            data["base_clock"] = self._parse_clock(value)
        elif "boost" in label or "turbo" in label:
            data["boost_clock"] = self._parse_clock(value)

        # Socket and process
        elif "socket" in label:
            data["socket_name"] = value
        elif "process" in label and "size" in label:
            data["process_node"] = value
        elif "foundry" in label or "fab" in label:
            data["fab_processor"] = value

        # Cache
        elif "l1 cache" in label:
            if "instruction" in label:
                data["l1_cache_instruction"] = self._parse_cache(value)
            elif "data" in label:
                data["l1_cache_data"] = self._parse_cache(value)
            else:
                data["l1_cache"] = self._parse_cache(value)
        elif "l2 cache" in label:
            data["l2_cache"] = self._parse_cache(value)
        elif "l3 cache" in label:
            data["l3_cache"] = self._parse_cache(value)

        # Power
        elif "tdp" in label:
            data["tdp"] = self._parse_power(value)

        # Architecture
        elif "codename" in label:
            data["codename"] = value
        elif "microarchitecture" in label or "architecture" in label:
            data["microarchitecture"] = value

        # Launch info
        elif "launch" in label and "date" in label:
            data["launch_date_raw"] = value
        elif "launch" in label and "price" in label:
            data["launch_msrp"] = self._parse_price(value)

        # Memory
        elif "memory" in label and "type" in label:
            data["memory_type"] = value
        elif "memory" in label and "channel" in label:
            data["memory_channels"] = self._parse_int(value)
        elif "max memory" in label:
            data["max_memory_gb"] = self._parse_memory_size(value)

        # Graphics
        elif "integrated gpu" in label or "igpu" in label:
            data["integrated_gpu_name"] = value
            data["has_integrated_gpu"] = True

        # PCIe
        elif "pcie" in label or "pci express" in label:
            if "version" in label or "revision" in label:
                data["pcie_version"] = value
            elif "lane" in label:
                data["pcie_lanes"] = self._parse_int(value)

        # Transistors
        elif "transistor" in label:
            data["transistors_million"] = self._parse_transistors(value)

        # Die size
        elif "die size" in label:
            data["die_size_mm2"] = self._parse_die_size(value)

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
        """Parse transistor count to millions."""
        match = re.search(r"([\d.]+)\s*(billion|million)", text, re.I)
        if match:
            value = float(match.group(1))
            unit = match.group(2).lower()
            return int(value * 1000) if unit == "billion" else int(value)
        return None

    def _parse_die_size(self, text: str) -> Optional[float]:
        match = re.search(r"([\d.]+)\s*mm", text, re.I)
        return float(match.group(1)) if match else None


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
