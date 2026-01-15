"""
PCPartPicker Price Scraper - Fetches current CPU prices
Uses Playwright with stealth mode to bypass Cloudflare protection.
"""
import re
import logging
import time
from typing import Dict, List, Optional, Any
from urllib.parse import quote_plus
from bs4 import BeautifulSoup

from core.base_scraper import BaseScraper
from core.cpu_matcher import CpuMatcher
from exporters.database import get_db

# Try Playwright for JS-rendered content with anti-bot bypass
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

# Try playwright-stealth for better anti-detection
try:
    from playwright_stealth import stealth_sync
    STEALTH_AVAILABLE = True
except ImportError:
    STEALTH_AVAILABLE = False


class PCPartPickerScraper(BaseScraper):
    """
    Scrapes current CPU prices from PCPartPicker.

    NOTE: PCPartPicker uses aggressive Cloudflare protection that blocks
    automated scraping. This scraper may return 0 results in headless mode.
    Consider using alternative pricing sources:
    - Newegg API
    - Amazon Product Advertising API
    - Manual data entry via GUI browser session
    """

    SOURCE_NAME = 'pcpartpicker'
    BASE_URL = 'https://pcpartpicker.com'

    def __init__(self, use_playwright: bool = True):
        super().__init__(self.SOURCE_NAME)
        self.matcher = CpuMatcher()
        self.db = get_db()
        self._cpu_names: List[str] = []
        self.use_playwright = use_playwright and PLAYWRIGHT_AVAILABLE

    def scrape_list(self) -> List[Dict[str, Any]]:
        """Scrape CPU listings from PCPartPicker."""
        if self.use_playwright:
            return self._scrape_with_playwright()
        else:
            return self._scrape_with_requests()

    def _scrape_with_playwright(self) -> List[Dict[str, Any]]:
        """Use Playwright with stealth mode to scrape PCPartPicker."""
        cpus = []

        with sync_playwright() as p:
            # Launch browser with stealth options
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                ]
            )

            # Create context with realistic browser profile
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                locale='en-US',
                timezone_id='America/New_York',
                color_scheme='light',
                java_script_enabled=True,
            )

            page = context.new_page()

            # Apply playwright-stealth if available
            if STEALTH_AVAILABLE:
                stealth_sync(page)
                self.logger.info("Applied playwright-stealth to page")

            page_num = 1
            max_pages = 15  # Safety limit

            while page_num <= max_pages:
                try:
                    url = f'{self.BASE_URL}/products/cpu/#page={page_num}'
                    self.logger.info(f"Loading page {page_num}: {url}")

                    page.goto(url, wait_until='domcontentloaded', timeout=60000)

                    # Wait for the page to stabilize
                    page.wait_for_timeout(3000)

                    # Check for Cloudflare challenge
                    html = page.content()
                    if 'challenge' in html.lower() and 'cloudflare' in html.lower():
                        self.logger.info("Cloudflare challenge detected, waiting...")
                        page.wait_for_timeout(10000)
                        html = page.content()

                    soup = BeautifulSoup(html, 'lxml')

                    # Find product rows
                    rows = soup.select('tr.tr__product')
                    if not rows:
                        self.logger.info(f'No products found at page {page_num}')
                        break

                    self.logger.info(f"Found {len(rows)} products on page {page_num}")

                    for row in rows:
                        try:
                            cpu_data = self._parse_product_row(row)
                            if cpu_data:
                                cpus.append(cpu_data)
                        except Exception as e:
                            self.logger.warning(f'Error parsing row: {e}')

                    # Check for next page button
                    next_btn = soup.select_one('a.pagination__next:not(.pagination__next--disabled)')
                    if not next_btn:
                        self.logger.info("No more pages available")
                        break

                    page_num += 1
                    # Add delay to avoid rate limiting
                    time.sleep(2)

                except Exception as e:
                    self.logger.error(f"Error on page {page_num}: {e}")
                    break

            browser.close()

        self.logger.info(f"Total CPUs scraped from PCPartPicker: {len(cpus)}")
        return cpus

    def _scrape_with_requests(self) -> List[Dict[str, Any]]:
        """Fallback to requests-based scraping (may be blocked)."""
        cpus = []
        page = 1
        max_pages = 20  # Safety limit

        while page <= max_pages:
            url = f'{self.BASE_URL}/products/cpu/?page={page}'
            soup = self.get_soup(url)

            if not soup:
                break

            # Find product rows
            rows = soup.select('tr.tr__product')
            if not rows:
                self.logger.info(f'No more products found at page {page}')
                break

            for row in rows:
                try:
                    cpu_data = self._parse_product_row(row)
                    if cpu_data:
                        cpus.append(cpu_data)
                except Exception as e:
                    self.logger.warning(f'Error parsing row: {e}')

            # Check for next page
            next_link = soup.select_one('a.pagination__next')
            if not next_link or 'disabled' in next_link.get('class', []):
                break

            page += 1
            self.logger.info(f'Scraped page {page-1}, found {len(cpus)} CPUs so far')

        return cpus

    def _parse_product_row(self, row) -> Optional[Dict[str, Any]]:
        """Parse a single product row from PCPartPicker listing."""
        try:
            # Get CPU name
            name_elem = row.select_one('td.td__name a.td__nameWrapper__name')
            if not name_elem:
                return None

            name = name_elem.get_text(strip=True)

            # Get price
            price_elem = row.select_one('td.td__price')
            price = None
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                price = self._parse_price(price_text)

            # Get product URL for detail page
            detail_url = name_elem.get('href', '')
            if detail_url and not detail_url.startswith('http'):
                detail_url = f'{self.BASE_URL}{detail_url}'

            return {
                'name': name,
                'price': price,
                'url': detail_url,
                'source': 'pcpartpicker'
            }
        except Exception as e:
            self.logger.warning(f'Error parsing product row: {e}')
            return None

    def _parse_price(self, price_text: str) -> Optional[float]:
        """Parse price string to float."""
        if not price_text:
            return None

        # Remove currency symbols and commas
        clean = re.sub(r'[^\d.]', '', price_text)
        try:
            return float(clean) if clean else None
        except ValueError:
            return None

    def scrape_detail(self, url: str) -> Optional[Dict[str, Any]]:
        """Scrape detailed pricing from a product page."""
        soup = self.get_soup(url)
        if not soup:
            return None

        result = {'retailers': []}

        # Find price table
        price_table = soup.select('table.xs-col-12 tr')
        for row in price_table:
            try:
                retailer_elem = row.select_one('td.td__logo img')
                price_elem = row.select_one('td.td__finalPrice a')

                if retailer_elem and price_elem:
                    retailer = retailer_elem.get('alt', 'Unknown')
                    price_text = price_elem.get_text(strip=True)
                    price = self._parse_price(price_text)

                    if price:
                        result['retailers'].append({
                            'name': retailer,
                            'price': price
                        })
            except Exception:
                continue

        # Get lowest price
        if result['retailers']:
            result['lowest_price'] = min(r['price'] for r in result['retailers'])
            result['retailer'] = next(
                r['name'] for r in result['retailers']
                if r['price'] == result['lowest_price']
            )

        return result

    def search_cpu_price(self, cpu_name: str) -> Optional[Dict[str, Any]]:
        """Search for a specific CPU and get its price."""
        search_url = f'{self.BASE_URL}/search/?q={quote_plus(cpu_name)}'
        soup = self.get_soup(search_url)

        if not soup:
            return None

        # Find first CPU result
        cpu_result = soup.select_one('ul.search-results__list li a[href*="/product/"]')
        if not cpu_result:
            return None

        result_name = cpu_result.get_text(strip=True)
        result_url = cpu_result.get('href', '')

        if result_url and not result_url.startswith('http'):
            result_url = f'{self.BASE_URL}{result_url}'

        # Get price from the listing
        price_elem = cpu_result.find_next('span', class_='search-results__price')
        price = None
        if price_elem:
            price = self._parse_price(price_elem.get_text())

        return {
            'name': result_name,
            'price': price,
            'url': result_url,
            'source': 'pcpartpicker'
        }

    def run(self) -> Dict[str, Any]:
        """Run the price scraper and update database."""
        self.logger.info('Starting PCPartPicker price scrape')

        # Load existing CPU names from database
        self._cpu_names = self.db.get_all_cpu_names()
        self.logger.info(f'Loaded {len(self._cpu_names)} CPU names from database')

        # Scrape all listings
        listings = self.scrape_list()
        self.logger.info(f'Found {len(listings)} CPU listings')

        matched = 0
        updated = 0

        for listing in listings:
            if not listing.get('price'):
                continue

            # Try to match to existing CPU
            match_result = self.matcher.match(
                listing['name'],
                self._cpu_names,
                threshold=0.85
            )

            if match_result:
                matched_name, confidence = match_result
                self.logger.debug(
                    f"Matched '{listing['name']}' -> '{matched_name}' ({confidence:.2f})"
                )

                # Get CPU ID and update price
                cpu = self.db.get_cpu_by_name(matched_name)
                if cpu:
                    self.db.insert_price(
                        cpu_id=cpu['id'],
                        price=listing['price'],
                        source='pcpartpicker',
                        retailer='PCPartPicker'
                    )
                    updated += 1
            else:
                self.logger.debug(f"No match for: {listing['name']}")

        stats = {
            'source': self.SOURCE_NAME,
            'listings_found': len(listings),
            'matched': matched,
            'prices_updated': updated
        }

        self.logger.info(f'PCPartPicker scrape complete: {stats}')
        return stats


def main():
    """Run PCPartPicker scraper standalone."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    scraper = PCPartPickerScraper()
    result = scraper.run()
    print(f'Result: {result}')


if __name__ == '__main__':
    main()
