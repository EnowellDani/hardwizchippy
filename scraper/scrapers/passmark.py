"""
PassMark CPU Benchmark Scraper - Enhanced with Playwright
"""
import re
import logging
from typing import Dict, List, Optional, Any

from core.base_scraper import BaseScraper
from core.cpu_matcher import CpuMatcher
from exporters.database import get_db

# Try Playwright for JS-rendered content
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class PassMarkScraper(BaseScraper):
    """Scrapes CPU benchmark scores from PassMark/cpubenchmark.net."""

    SOURCE_NAME = 'passmark'
    BASE_URL = 'https://www.cpubenchmark.net'

    def __init__(self, use_playwright: bool = True):
        super().__init__(self.SOURCE_NAME)
        self.matcher = CpuMatcher()
        self.db = get_db()
        self._cpu_names: List[str] = []
        self.use_playwright = use_playwright and PLAYWRIGHT_AVAILABLE

    def scrape_list(self) -> List[Dict[str, Any]]:
        """Scrape CPU benchmark charts."""
        if self.use_playwright:
            return self._scrape_with_playwright()
        else:
            return self._scrape_with_requests()

    def _scrape_with_playwright(self) -> List[Dict[str, Any]]:
        """Use Playwright to scrape PassMark charts."""
        cpus = {}

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()

            # Scrape multi-core chart from cpu_list.php (uses table#cputable)
            self.logger.info("Scraping PassMark multi-core chart...")
            page.goto(f"{self.BASE_URL}/cpu_list.php", wait_until="domcontentloaded", timeout=90000)
            page.wait_for_timeout(5000)  # Wait for JS to render table

            # Parse the HTML with BeautifulSoup for more reliable extraction
            from bs4 import BeautifulSoup
            html = page.content()
            soup = BeautifulSoup(html, 'lxml')

            table = soup.find('table', id='cputable')
            if table:
                tbody = table.find('tbody')
                if tbody:
                    rows = tbody.find_all('tr')
                    self.logger.info(f"Found {len(rows)} rows in multi-core table")

                    for row in rows:
                        try:
                            cells = row.find_all('td')
                            if len(cells) >= 2:
                                name_cell = cells[0]
                                score_cell = cells[1]

                                link = name_cell.find('a')
                                if link:
                                    name = link.get_text(strip=True)
                                    score_text = score_cell.get_text(strip=True)
                                    score = self._parse_score(score_text)

                                    if name and score:
                                        if name not in cpus:
                                            cpus[name] = {'name': name, 'source': 'passmark'}
                                        cpus[name]['passmark_multi'] = score
                        except Exception as e:
                            continue
            else:
                self.logger.warning("Could not find cputable on multi-core page")

            self.logger.info(f"Multi-core entries: {len(cpus)}")

            # Scrape single-core chart from singleThread.html (uses ul.chartlist)
            self.logger.info("Scraping PassMark single-core chart...")
            page.goto(f"{self.BASE_URL}/singleThread.html", wait_until="domcontentloaded", timeout=90000)
            page.wait_for_timeout(5000)

            html = page.content()
            soup = BeautifulSoup(html, 'lxml')

            chartlist = soup.select('ul.chartlist li')
            self.logger.info(f"Found {len(chartlist)} items in single-core chart")

            single_count = 0
            for item in chartlist:
                try:
                    name_elem = item.select_one('span.prdname')
                    score_elem = item.select_one('span.count')

                    if name_elem and score_elem:
                        name = name_elem.get_text(strip=True)
                        score_text = score_elem.get_text(strip=True)
                        score = self._parse_score(score_text)

                        if name and score:
                            if name not in cpus:
                                cpus[name] = {'name': name, 'source': 'passmark'}
                            cpus[name]['passmark_single'] = score
                            single_count += 1
                except Exception as e:
                    continue

            self.logger.info(f"Single-core entries added: {single_count}")
            browser.close()

        self.logger.info(f"Total unique CPUs scraped from PassMark: {len(cpus)}")
        return list(cpus.values())

    def _scrape_with_requests(self) -> List[Dict[str, Any]]:
        """Fallback to requests-based scraping."""
        cpus = []

        charts = [
            ('cpu_list.php', 'multi'),
            ('singleThread.html', 'single'),
        ]

        for chart_url, score_type in charts:
            url = f'{self.BASE_URL}/{chart_url}'
            soup = self.get_soup(url)

            if not soup:
                self.logger.warning(f'Failed to fetch {chart_url}')
                continue

            # Try multiple selectors
            chart_items = (
                soup.select('ul.chartlist li') or
                soup.select('table#cputable tbody tr') or
                soup.select('div.chart_body li')
            )

            for item in chart_items:
                try:
                    cpu_data = self._parse_chart_item(item, score_type)
                    if cpu_data:
                        existing = next(
                            (c for c in cpus if c['name'] == cpu_data['name']),
                            None
                        )
                        if existing:
                            existing.update(cpu_data)
                        else:
                            cpus.append(cpu_data)
                except Exception as e:
                    self.logger.warning(f'Error parsing chart item: {e}')

        return cpus

    def _parse_chart_item(self, item, score_type: str) -> Optional[Dict[str, Any]]:
        """Parse a chart list item."""
        try:
            name_elem = (
                item.select_one('span.prdname') or
                item.select_one('td:first-child a') or
                item.select_one('a.name')
            )
            if not name_elem:
                return None

            name = name_elem.get_text(strip=True)

            score_elem = (
                item.select_one('span.count') or
                item.select_one('td:nth-child(2)') or
                item.select_one('span.score')
            )
            score = None
            if score_elem:
                score_text = score_elem.get_text(strip=True)
                score = self._parse_score(score_text)

            if not score:
                return None

            result = {'name': name, 'source': 'passmark'}
            if score_type == 'multi':
                result['passmark_multi'] = score
            else:
                result['passmark_single'] = score

            return result
        except Exception as e:
            return None

    def _parse_score(self, score_text: str) -> Optional[int]:
        """Parse score string to integer."""
        if not score_text:
            return None

        clean = re.sub(r'[^\d]', '', score_text)
        try:
            return int(clean) if clean else None
        except ValueError:
            return None

    def scrape_detail(self, url: str) -> Optional[Dict[str, Any]]:
        """Scrape detailed CPU info from PassMark."""
        soup = self.get_soup(url)
        if not soup:
            return None

        result = {}
        score_tables = soup.select('table.desc')
        for table in score_tables:
            rows = table.select('tr')
            for row in rows:
                cells = row.select('td')
                if len(cells) >= 2:
                    label = cells[0].get_text(strip=True).lower()
                    value = cells[1].get_text(strip=True)

                    if 'single thread' in label:
                        result['passmark_single'] = self._parse_score(value)
                    elif 'cpu mark' in label or 'overall' in label:
                        result['passmark_multi'] = self._parse_score(value)

        return result

    def run(self) -> Dict[str, Any]:
        """Run PassMark scraper and update database."""
        self.logger.info('Starting PassMark benchmark scrape')

        self._cpu_names = self.db.get_all_cpu_names()
        self.logger.info(f'Loaded {len(self._cpu_names)} CPU names')

        benchmarks = self.scrape_list()
        self.logger.info(f'Found {len(benchmarks)} benchmark entries')

        matched = 0
        updated = 0

        for bench in benchmarks:
            match_result = self.matcher.match(
                bench['name'],
                self._cpu_names,
                threshold=0.85
            )

            if match_result:
                matched_name, confidence = match_result
                cpu = self.db.get_cpu_by_name(matched_name)

                if cpu:
                    matched += 1
                    if bench.get('passmark_single'):
                        self.db.insert_benchmark_score(
                            cpu['id'],
                            'PassMark Single',
                            bench['passmark_single'],
                            'passmark'
                        )
                        updated += 1
                    if bench.get('passmark_multi'):
                        self.db.insert_benchmark_score(
                            cpu['id'],
                            'PassMark Multi',
                            bench['passmark_multi'],
                            'passmark'
                        )
                        updated += 1

        stats = {
            'source': self.SOURCE_NAME,
            'benchmarks_found': len(benchmarks),
            'matched': matched,
            'scores_updated': updated
        }

        self.logger.info(f'PassMark scrape complete: {stats}')
        return stats


def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    scraper = PassMarkScraper(use_playwright=True)
    result = scraper.run()
    print(f'Result: {result}')


if __name__ == '__main__':
    main()
