"""
Tom's Hardware Gaming Benchmark Scraper
Scrapes CPU gaming benchmarks (FPS data for popular games)

Note: Tom's Hardware uses JavaScript rendering for benchmark charts.
This scraper includes both:
1. BeautifulSoup approach for static content
2. Playwright approach for JS-rendered content (when available)
"""
import re
import json
import logging
from typing import Dict, List, Optional, Any

from core.base_scraper import BaseScraper
from core.cpu_matcher import CpuMatcher
from exporters.database import get_db

# Try to import Playwright for JS rendering
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class TomsHardwareScraper(BaseScraper):
    """Scrapes gaming benchmark data from Tom's Hardware."""

    SOURCE_NAME = 'tomshardware'
    BASE_URL = 'https://www.tomshardware.com'

    # Known gaming benchmark pages
    BENCHMARK_PAGES = [
        '/reviews/cpu-hierarchy,4312.html',
        '/reviews/best-cpus,3986.html',
    ]

    # Games to extract FPS data for
    TARGET_GAMES = [
        'Cyberpunk 2077',
        'Red Dead Redemption 2',
        'Assassins Creed Valhalla',
        'Shadow of the Tomb Raider',
        'Far Cry 6',
        'Horizon Zero Dawn',
        'Total War: Warhammer III',
        'Hitman 3',
        'F1 2022',
        'Counter-Strike 2',
    ]

    def __init__(self, use_playwright: bool = True):
        super().__init__(self.SOURCE_NAME)
        self.matcher = CpuMatcher()
        self.db = get_db()
        self._cpu_names: List[str] = []
        self.use_playwright = use_playwright and PLAYWRIGHT_AVAILABLE

        if use_playwright and not PLAYWRIGHT_AVAILABLE:
            self.logger.warning(
                'Playwright not available. Install with: pip install playwright && playwright install'
            )

    def scrape_list(self) -> List[Dict[str, Any]]:
        """Scrape gaming benchmarks from Tom's Hardware."""
        all_benchmarks = []

        for page_path in self.BENCHMARK_PAGES:
            url = f'{self.BASE_URL}{page_path}'

            if self.use_playwright:
                benchmarks = self._scrape_with_playwright(url)
            else:
                benchmarks = self._scrape_with_requests(url)

            if benchmarks:
                all_benchmarks.extend(benchmarks)

        # Deduplicate by CPU name, keeping most complete data
        deduplicated = {}
        for bench in all_benchmarks:
            name = bench['name']
            if name not in deduplicated:
                deduplicated[name] = bench
            else:
                # Merge gaming data
                existing_games = {g['game']: g for g in deduplicated[name].get('gaming', [])}
                for game in bench.get('gaming', []):
                    if game['game'] not in existing_games:
                        deduplicated[name].setdefault('gaming', []).append(game)

        return list(deduplicated.values())

    def _scrape_with_requests(self, url: str) -> List[Dict[str, Any]]:
        """Scrape using BeautifulSoup (limited - may not get all JS content)."""
        benchmarks = []
        soup = self.get_soup(url)

        if not soup:
            return benchmarks

        # Try to find benchmark tables
        tables = soup.select('table.benchmark-table, table.specs-table, div.chart-container')

        for table in tables:
            try:
                benchmarks.extend(self._parse_benchmark_table(table))
            except Exception as e:
                self.logger.warning(f'Error parsing table: {e}')

        # Try to extract from embedded JSON data
        scripts = soup.select('script[type="application/json"], script[type="application/ld+json"]')
        for script in scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and 'benchmarks' in data:
                    benchmarks.extend(self._parse_json_benchmarks(data['benchmarks']))
            except Exception:
                continue

        # Also try parsing inline chart data
        chart_scripts = soup.find_all('script', string=re.compile(r'chartData|benchmarkData'))
        for script in chart_scripts:
            try:
                benchmarks.extend(self._parse_chart_script(script.string))
            except Exception:
                continue

        return benchmarks

    def _scrape_with_playwright(self, url: str) -> List[Dict[str, Any]]:
        """Scrape using Playwright for JS-rendered content."""
        benchmarks = []

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent=self._get_random_user_agent()
                )
                page = context.new_page()

                # Navigate and wait for content
                page.goto(url, wait_until='networkidle', timeout=30000)

                # Wait for benchmark charts to load
                page.wait_for_timeout(3000)

                # Try to expand all charts
                expand_buttons = page.query_selector_all('button.expand, a.show-more')
                for button in expand_buttons:
                    try:
                        button.click()
                        page.wait_for_timeout(500)
                    except Exception:
                        continue

                # Get page content after JS rendering
                content = page.content()
                browser.close()

                # Parse with BeautifulSoup
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(content, 'lxml')

                # Find all benchmark sections
                benchmark_sections = soup.select(
                    'div.chart-container, div.benchmark-chart, '
                    'figure.chart, div[data-chart-type]'
                )

                for section in benchmark_sections:
                    try:
                        benchmarks.extend(self._parse_chart_section(section))
                    except Exception as e:
                        self.logger.warning(f'Error parsing chart section: {e}')

                # Also extract from tables
                tables = soup.select('table')
                for table in tables:
                    try:
                        benchmarks.extend(self._parse_benchmark_table(table))
                    except Exception:
                        continue

        except Exception as e:
            self.logger.error(f'Playwright scraping failed: {e}')
            # Fallback to requests
            return self._scrape_with_requests(url)

        return benchmarks

    def _parse_benchmark_table(self, table) -> List[Dict[str, Any]]:
        """Parse a benchmark table."""
        benchmarks = []
        headers = []

        # Get headers
        header_row = table.select_one('thead tr, tr:first-child')
        if header_row:
            headers = [th.get_text(strip=True).lower() for th in header_row.select('th, td')]

        # Get data rows
        rows = table.select('tbody tr, tr:not(:first-child)')

        for row in rows:
            cells = row.select('td')
            if len(cells) < 2:
                continue

            try:
                cpu_name = cells[0].get_text(strip=True)
                if not cpu_name or cpu_name.lower() in ['cpu', 'processor', '']:
                    continue

                benchmark = {
                    'name': cpu_name,
                    'source': 'tomshardware',
                    'gaming': []
                }

                # Parse FPS values from remaining cells
                for i, cell in enumerate(cells[1:], 1):
                    value = self._parse_fps(cell.get_text(strip=True))
                    if value and i < len(headers):
                        game_name = headers[i] if headers else f'Game {i}'
                        benchmark['gaming'].append({
                            'game': game_name,
                            'resolution': '1080p',  # Default, adjust if found
                            'avg_fps': value
                        })

                if benchmark['gaming']:
                    benchmarks.append(benchmark)

            except Exception:
                continue

        return benchmarks

    def _parse_chart_section(self, section) -> List[Dict[str, Any]]:
        """Parse a chart section for benchmark data."""
        benchmarks = []

        # Try to find game name from heading
        heading = section.find_previous(['h2', 'h3', 'h4'])
        game_name = heading.get_text(strip=True) if heading else 'Unknown Game'

        # Find resolution if mentioned
        resolution = '1080p'
        res_match = re.search(r'(\d{3,4}p|4K|1440p|1080p)', section.get_text())
        if res_match:
            resolution = res_match.group(1)

        # Find bar chart items
        bars = section.select('div.bar-item, div.chart-row, li.result')

        for bar in bars:
            try:
                name_elem = bar.select_one('span.name, div.label, td:first-child')
                value_elem = bar.select_one('span.value, div.score, td:last-child')

                if name_elem and value_elem:
                    cpu_name = name_elem.get_text(strip=True)
                    fps = self._parse_fps(value_elem.get_text(strip=True))

                    if cpu_name and fps:
                        benchmarks.append({
                            'name': cpu_name,
                            'source': 'tomshardware',
                            'gaming': [{
                                'game': game_name,
                                'resolution': resolution,
                                'avg_fps': fps
                            }]
                        })
            except Exception:
                continue

        return benchmarks

    def _parse_chart_script(self, script_content: str) -> List[Dict[str, Any]]:
        """Parse benchmark data from embedded JavaScript."""
        benchmarks = []

        # Try to extract JSON data from script
        json_match = re.search(r'(?:chartData|benchmarkData)\s*[=:]\s*(\[[\s\S]*?\]);', script_content)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                return self._parse_json_benchmarks(data)
            except json.JSONDecodeError:
                pass

        return benchmarks

    def _parse_json_benchmarks(self, data: List) -> List[Dict[str, Any]]:
        """Parse benchmark data from JSON format."""
        benchmarks = []

        for item in data:
            if isinstance(item, dict):
                cpu_name = item.get('name', item.get('cpu', item.get('label')))
                if not cpu_name:
                    continue

                benchmark = {
                    'name': cpu_name,
                    'source': 'tomshardware',
                    'gaming': []
                }

                # Extract FPS values
                for key, value in item.items():
                    if key.lower() in ['name', 'cpu', 'label', 'id']:
                        continue

                    fps = self._parse_fps(str(value))
                    if fps:
                        benchmark['gaming'].append({
                            'game': key,
                            'resolution': '1080p',
                            'avg_fps': fps
                        })

                if benchmark['gaming']:
                    benchmarks.append(benchmark)

        return benchmarks

    def _parse_fps(self, text: str) -> Optional[float]:
        """Parse FPS value from text."""
        if not text:
            return None

        # Extract number
        match = re.search(r'(\d+\.?\d*)', text)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass

        return None

    def _get_random_user_agent(self) -> str:
        """Get a random user agent for Playwright."""
        from config.settings import USER_AGENTS
        import random
        return random.choice(USER_AGENTS)

    def scrape_detail(self, url: str) -> Optional[Dict[str, Any]]:
        """Scrape a specific CPU review page for gaming benchmarks."""
        if self.use_playwright:
            results = self._scrape_with_playwright(url)
        else:
            results = self._scrape_with_requests(url)

        return results[0] if results else None

    def run(self) -> Dict[str, Any]:
        """Run Tom's Hardware gaming scraper."""
        self.logger.info('Starting Tom\'s Hardware gaming benchmark scrape')

        # Load CPU names
        self._cpu_names = self.db.get_all_cpu_names()
        self.logger.info(f'Loaded {len(self._cpu_names)} CPU names')

        # Scrape benchmarks
        benchmarks = self.scrape_list()
        self.logger.info(f'Found {len(benchmarks)} benchmark entries')

        matched = 0
        games_added = 0

        for bench in benchmarks:
            if not bench.get('gaming'):
                continue

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
                    for game in bench['gaming']:
                        try:
                            self.db.insert_gaming_benchmark(
                                cpu_id=cpu['id'],
                                game_name=game['game'],
                                resolution=game.get('resolution', '1080p'),
                                avg_fps=game['avg_fps'],
                                one_percent_low=game.get('1_low'),
                                point_one_percent_low=game.get('0.1_low'),
                                gpu_used=game.get('gpu'),
                                source='tomshardware'
                            )
                            games_added += 1
                        except Exception as e:
                            self.logger.warning(f'Error saving game benchmark: {e}')

        stats = {
            'source': self.SOURCE_NAME,
            'cpus_found': len(benchmarks),
            'matched': matched,
            'games_added': games_added,
            'playwright_used': self.use_playwright
        }

        self.logger.info(f'Tom\'s Hardware scrape complete: {stats}')
        return stats


def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Try with Playwright first, fallback to requests
    scraper = TomsHardwareScraper(use_playwright=PLAYWRIGHT_AVAILABLE)
    result = scraper.run()
    print(f'Result: {result}')


if __name__ == '__main__':
    main()
