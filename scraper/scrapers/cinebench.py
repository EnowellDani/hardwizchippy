"""
Cinebench CPU Benchmark Scraper
Aggregates from multiple sources since Maxon doesn't publish official charts
"""
import re
import logging
from typing import Dict, List, Optional, Any

from core.base_scraper import BaseScraper
from core.cpu_matcher import CpuMatcher
from exporters.database import get_db


class CinebenchScraper(BaseScraper):
    """Scrapes Cinebench R23/R24 scores from aggregator sites."""

    SOURCE_NAME = 'cinebench'

    # Multiple sources for Cinebench scores
    SOURCES = [
        {
            'name': 'cgdirector',
            'url': 'https://www.cgdirector.com/cinebench-r23-scores/',
            'version': 'r23'
        },
        {
            'name': 'cpu-monkey',
            'url': 'https://www.cpu-monkey.com/en/cpu_benchmark-cinebench_r23_single_core-20',
            'version': 'r23',
            'type': 'single'
        },
        {
            'name': 'cpu-monkey',
            'url': 'https://www.cpu-monkey.com/en/cpu_benchmark-cinebench_r23_multi_core-19',
            'version': 'r23',
            'type': 'multi'
        },
    ]

    def __init__(self):
        super().__init__(self.SOURCE_NAME)
        self.matcher = CpuMatcher()
        self.db = get_db()
        self._cpu_names: List[str] = []

    def scrape_list(self) -> List[Dict[str, Any]]:
        """Scrape Cinebench scores from all sources."""
        all_scores = {}

        for source in self.SOURCES:
            self.logger.info(f"Scraping {source['name']} for {source['version']}")

            try:
                if source['name'] == 'cgdirector':
                    scores = self._scrape_cgdirector(source['url'])
                elif source['name'] == 'cpu-monkey':
                    scores = self._scrape_cpu_monkey(
                        source['url'],
                        source['version'],
                        source.get('type', 'multi')
                    )
                else:
                    continue

                # Merge scores
                for cpu_name, cpu_scores in scores.items():
                    if cpu_name not in all_scores:
                        all_scores[cpu_name] = {'name': cpu_name, 'source': 'cinebench'}
                    all_scores[cpu_name].update(cpu_scores)

            except Exception as e:
                self.logger.warning(f"Error scraping {source['name']}: {e}")

        return list(all_scores.values())

    def _scrape_cgdirector(self, url: str) -> Dict[str, Dict[str, int]]:
        """Scrape CGDirector Cinebench chart."""
        scores = {}
        soup = self.get_soup(url)

        if not soup:
            return scores

        # Find benchmark tables
        tables = soup.select('table')

        for table in tables:
            rows = table.select('tr')

            for row in rows:
                cells = row.select('td')
                if len(cells) < 3:
                    continue

                try:
                    name = cells[0].get_text(strip=True)
                    single = self._parse_score(cells[1].get_text(strip=True))
                    multi = self._parse_score(cells[2].get_text(strip=True))

                    if name and (single or multi):
                        scores[name] = {}
                        if single:
                            scores[name]['cinebench_r23_single'] = single
                        if multi:
                            scores[name]['cinebench_r23_multi'] = multi
                except Exception:
                    continue

        return scores

    def _scrape_cpu_monkey(self, url: str, version: str, score_type: str) -> Dict[str, Dict[str, int]]:
        """Scrape CPU-Monkey benchmark chart."""
        scores = {}
        soup = self.get_soup(url)

        if not soup:
            return scores

        # Find benchmark list
        bench_list = soup.select('div.bench-list-item, tr.bench-row')

        for item in bench_list:
            try:
                name_elem = item.select_one('a.cpu-name, td.name a')
                score_elem = item.select_one('span.score, td.score')

                if not name_elem or not score_elem:
                    continue

                name = name_elem.get_text(strip=True)
                score = self._parse_score(score_elem.get_text(strip=True))

                if name and score:
                    key = f'cinebench_{version}_{score_type}'
                    scores[name] = {key: score}
            except Exception:
                continue

        return scores

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
        """Not used for Cinebench - scores come from list pages."""
        return None

    def run(self) -> Dict[str, Any]:
        """Run Cinebench scraper and update database."""
        self.logger.info('Starting Cinebench benchmark scrape')

        # Load CPU names
        self._cpu_names = self.db.get_all_cpu_names()
        self.logger.info(f'Loaded {len(self._cpu_names)} CPU names')

        # Scrape benchmarks
        benchmarks = self.scrape_list()
        self.logger.info(f'Found {len(benchmarks)} benchmark entries')

        matched = 0
        updated = 0

        benchmark_mappings = [
            ('cinebench_r23_single', 'Cinebench R23 Single'),
            ('cinebench_r23_multi', 'Cinebench R23 Multi'),
            ('cinebench_r24_single', 'Cinebench R24 Single'),
            ('cinebench_r24_multi', 'Cinebench R24 Multi'),
        ]

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
                    for key, bench_name in benchmark_mappings:
                        if bench.get(key):
                            self.db.insert_benchmark_score(
                                cpu['id'],
                                bench_name,
                                bench[key],
                                'cinebench'
                            )
                            updated += 1

        stats = {
            'source': self.SOURCE_NAME,
            'benchmarks_found': len(benchmarks),
            'matched': matched,
            'scores_updated': updated
        }

        self.logger.info(f'Cinebench scrape complete: {stats}')
        return stats


def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    scraper = CinebenchScraper()
    result = scraper.run()
    print(f'Result: {result}')


if __name__ == '__main__':
    main()
