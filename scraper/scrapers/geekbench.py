"""
Geekbench 6 CPU Benchmark Scraper
"""
import re
import logging
from typing import Dict, List, Optional, Any

from core.base_scraper import BaseScraper
from core.cpu_matcher import CpuMatcher
from exporters.database import get_db


class GeekbenchScraper(BaseScraper):
    """Scrapes CPU benchmark scores from Geekbench Browser."""

    SOURCE_NAME = 'geekbench'
    BASE_URL = 'https://browser.geekbench.com'

    def __init__(self):
        super().__init__(self.SOURCE_NAME)
        self.matcher = CpuMatcher()
        self.db = get_db()
        self._cpu_names: List[str] = []

    def scrape_list(self) -> List[Dict[str, Any]]:
        """Scrape Geekbench 6 processor chart."""
        cpus = []

        # Geekbench 6 CPU charts
        charts = [
            ('processor-benchmarks', 'multi'),
            ('processor-benchmarks/single-core', 'single'),
        ]

        for chart_path, score_type in charts:
            page = 1
            max_pages = 10

            while page <= max_pages:
                url = f'{self.BASE_URL}/v6/cpu/{chart_path}?page={page}'
                soup = self.get_soup(url)

                if not soup:
                    break

                # Find benchmark table
                table = soup.select_one('table.table')
                if not table:
                    break

                rows = table.select('tbody tr')
                if not rows:
                    break

                for row in rows:
                    try:
                        cpu_data = self._parse_table_row(row, score_type)
                        if cpu_data:
                            # Merge with existing
                            existing = next(
                                (c for c in cpus if c['name'] == cpu_data['name']),
                                None
                            )
                            if existing:
                                existing.update(cpu_data)
                            else:
                                cpus.append(cpu_data)
                    except Exception as e:
                        self.logger.warning(f'Error parsing row: {e}')

                # Check for next page
                next_link = soup.select_one('a.page-link[rel="next"]')
                if not next_link:
                    break

                page += 1

        return cpus

    def _parse_table_row(self, row, score_type: str) -> Optional[Dict[str, Any]]:
        """Parse a Geekbench table row."""
        try:
            cells = row.select('td')
            if len(cells) < 3:
                return None

            # Get CPU name (usually in first cell)
            name_elem = cells[0].select_one('a')
            if not name_elem:
                return None

            name = name_elem.get_text(strip=True)

            # Score is usually in the last cell
            score_elem = cells[-1]
            score = self._parse_score(score_elem.get_text(strip=True))

            if not score:
                return None

            result = {'name': name, 'source': 'geekbench'}

            if score_type == 'multi':
                result['geekbench6_multi'] = score
            else:
                result['geekbench6_single'] = score

            return result
        except Exception as e:
            self.logger.warning(f'Error parsing table row: {e}')
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
        """Scrape detailed benchmark from a specific result page."""
        soup = self.get_soup(url)
        if not soup:
            return None

        result = {}

        # Find score cards
        score_cards = soup.select('div.score-card')
        for card in score_cards:
            label_elem = card.select_one('span.score-card-header')
            score_elem = card.select_one('span.score')

            if label_elem and score_elem:
                label = label_elem.get_text(strip=True).lower()
                score = self._parse_score(score_elem.get_text())

                if 'single' in label:
                    result['geekbench6_single'] = score
                elif 'multi' in label:
                    result['geekbench6_multi'] = score

        return result

    def run(self) -> Dict[str, Any]:
        """Run Geekbench scraper and update database."""
        self.logger.info('Starting Geekbench 6 benchmark scrape')

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
                    if bench.get('geekbench6_single'):
                        self.db.insert_benchmark_score(
                            cpu['id'],
                            'Geekbench 6 Single',
                            bench['geekbench6_single'],
                            'geekbench'
                        )
                        updated += 1
                    if bench.get('geekbench6_multi'):
                        self.db.insert_benchmark_score(
                            cpu['id'],
                            'Geekbench 6 Multi',
                            bench['geekbench6_multi'],
                            'geekbench'
                        )
                        updated += 1

        stats = {
            'source': self.SOURCE_NAME,
            'benchmarks_found': len(benchmarks),
            'matched': matched,
            'scores_updated': updated
        }

        self.logger.info(f'Geekbench scrape complete: {stats}')
        return stats


def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    scraper = GeekbenchScraper()
    result = scraper.run()
    print(f'Result: {result}')


if __name__ == '__main__':
    main()
