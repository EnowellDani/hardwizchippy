"""
PassMark CPU Benchmark Scraper
"""
import re
import logging
from typing import Dict, List, Optional, Any

from core.base_scraper import BaseScraper
from core.cpu_matcher import CpuMatcher
from exporters.database import get_db


class PassMarkScraper(BaseScraper):
    """Scrapes CPU benchmark scores from PassMark/cpubenchmark.net."""

    SOURCE_NAME = 'passmark'
    BASE_URL = 'https://www.cpubenchmark.net'

    def __init__(self):
        super().__init__(self.SOURCE_NAME)
        self.matcher = CpuMatcher()
        self.db = get_db()
        self._cpu_names: List[str] = []

    def scrape_list(self) -> List[Dict[str, Any]]:
        """Scrape CPU benchmark charts."""
        cpus = []

        # Scrape the main CPU chart
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

            # Find chart rows
            chart_list = soup.select('ul.chartlist li')

            for item in chart_list:
                try:
                    cpu_data = self._parse_chart_item(item, score_type)
                    if cpu_data:
                        # Merge with existing if already scraped
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
            # Get CPU name
            name_elem = item.select_one('span.prdname')
            if not name_elem:
                return None

            name = name_elem.get_text(strip=True)

            # Get score
            score_elem = item.select_one('span.count')
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
            self.logger.warning(f'Error parsing chart item: {e}')
            return None

    def _parse_score(self, score_text: str) -> Optional[int]:
        """Parse score string to integer."""
        if not score_text:
            return None

        # Remove commas and non-numeric chars
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

        # Find score tables
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

        # Load CPU names
        self._cpu_names = self.db.get_all_cpu_names()
        self.logger.info(f'Loaded {len(self._cpu_names)} CPU names')

        # Scrape benchmarks
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
    scraper = PassMarkScraper()
    result = scraper.run()
    print(f'Result: {result}')


if __name__ == '__main__':
    main()
