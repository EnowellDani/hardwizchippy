#!/usr/bin/env python3
"""
HardWizChippy Scraper - Main Orchestrator
Runs all scrapers and exports data for the Flutter app
"""
import argparse
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import LOG_CONFIG, DATA_DIR
from scrapers.techpowerup import TechPowerUpScraper
from scrapers.pcpartpicker import PCPartPickerScraper
from scrapers.passmark import PassMarkScraper
from scrapers.geekbench import GeekbenchScraper
from scrapers.cinebench import CinebenchScraper
from scrapers.tomshardware import TomsHardwareScraper
from exporters.json_exporter import JsonExporter
from exporters.database import get_db


def setup_logging():
    """Configure logging for the scraper."""
    logging.basicConfig(
        level=LOG_CONFIG["level"],
        format=LOG_CONFIG["format"],
        datefmt=LOG_CONFIG["date_format"],
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(LOG_CONFIG["file"])
        ]
    )


def run_specs_scraper(logger, limit: int = None) -> List[Dict[str, Any]]:
    """Run TechPowerUp scraper for CPU specifications."""
    logger.info("=" * 40)
    logger.info("Running TechPowerUp Specs Scraper")
    logger.info("=" * 40)

    scraper = TechPowerUpScraper()
    cpus = scraper.run(limit=limit)
    logger.info(f"Scraped {len(cpus)} CPUs from TechPowerUp")
    return cpus


def run_price_scraper(logger) -> Dict[str, Any]:
    """Run PCPartPicker price scraper."""
    logger.info("=" * 40)
    logger.info("Running PCPartPicker Price Scraper")
    logger.info("=" * 40)

    try:
        scraper = PCPartPickerScraper()
        result = scraper.run()
        logger.info(f"Price scrape result: {result}")
        return result
    except Exception as e:
        logger.error(f"Price scraper failed: {e}")
        return {'error': str(e)}


def run_benchmark_scrapers(logger) -> List[Dict[str, Any]]:
    """Run all benchmark scrapers."""
    results = []

    scrapers = [
        ("PassMark", PassMarkScraper),
        ("Geekbench", GeekbenchScraper),
        ("Cinebench", CinebenchScraper),
    ]

    for name, scraper_class in scrapers:
        logger.info("=" * 40)
        logger.info(f"Running {name} Benchmark Scraper")
        logger.info("=" * 40)

        try:
            scraper = scraper_class()
            result = scraper.run()
            results.append({'source': name, **result})
            logger.info(f"{name} result: {result}")
        except Exception as e:
            logger.error(f"{name} scraper failed: {e}")
            results.append({'source': name, 'error': str(e)})

    return results


def run_gaming_scraper(logger, use_playwright: bool = True) -> Dict[str, Any]:
    """Run Tom's Hardware gaming benchmark scraper."""
    logger.info("=" * 40)
    logger.info("Running Tom's Hardware Gaming Scraper")
    logger.info("=" * 40)

    try:
        scraper = TomsHardwareScraper(use_playwright=use_playwright)
        result = scraper.run()
        logger.info(f"Gaming scrape result: {result}")
        return result
    except Exception as e:
        logger.error(f"Gaming scraper failed: {e}")
        return {'error': str(e)}


def export_to_flutter(logger, cpus: List[Dict[str, Any]]) -> Path:
    """Export data to JSON for Flutter app."""
    logger.info("=" * 40)
    logger.info("Exporting to JSON for Flutter")
    logger.info("=" * 40)

    exporter = JsonExporter()
    output_file = exporter.export_cpus(cpus)

    # Copy to Flutter assets
    flutter_assets = Path(__file__).parent.parent / "assets" / "data"
    flutter_assets.mkdir(parents=True, exist_ok=True)

    import shutil
    dest_file = flutter_assets / "cpu_database.json"
    shutil.copy(output_file, dest_file)
    logger.info(f"Exported to: {dest_file}")

    return dest_file


def main():
    """Main entry point for the scraper."""
    parser = argparse.ArgumentParser(
        description='HardWizChippy CPU Data Scraper'
    )
    parser.add_argument(
        '--specs-only',
        action='store_true',
        help='Only run specs scraper (TechPowerUp)'
    )
    parser.add_argument(
        '--prices-only',
        action='store_true',
        help='Only run price scraper (PCPartPicker)'
    )
    parser.add_argument(
        '--benchmarks-only',
        action='store_true',
        help='Only run benchmark scrapers'
    )
    parser.add_argument(
        '--gaming-only',
        action='store_true',
        help='Only run gaming benchmark scraper'
    )
    parser.add_argument(
        '--no-playwright',
        action='store_true',
        help='Disable Playwright for gaming scraper'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Limit number of CPUs to scrape (for testing)'
    )
    parser.add_argument(
        '--export-only',
        action='store_true',
        help='Only export existing database to JSON'
    )

    args = parser.parse_args()

    setup_logging()
    logger = logging.getLogger("main")

    logger.info("=" * 60)
    logger.info("HardWizChippy Scraper Starting")
    logger.info(f"Time: {datetime.now().isoformat()}")
    logger.info("=" * 60)

    results = {
        'start_time': datetime.now().isoformat(),
        'specs': None,
        'prices': None,
        'benchmarks': None,
        'gaming': None,
        'export': None
    }

    try:
        cpus = []

        # Determine which scrapers to run
        run_all = not any([
            args.specs_only,
            args.prices_only,
            args.benchmarks_only,
            args.gaming_only,
            args.export_only
        ])

        # Run specs scraper
        if run_all or args.specs_only:
            cpus = run_specs_scraper(logger, limit=args.limit)
            results['specs'] = {'cpus_scraped': len(cpus)}

        # Run price scraper
        if run_all or args.prices_only:
            results['prices'] = run_price_scraper(logger)

        # Run benchmark scrapers
        if run_all or args.benchmarks_only:
            results['benchmarks'] = run_benchmark_scrapers(logger)

        # Run gaming scraper
        if run_all or args.gaming_only:
            results['gaming'] = run_gaming_scraper(
                logger,
                use_playwright=not args.no_playwright
            )

        # Export to JSON
        if run_all or args.export_only:
            # If export-only, load from database
            if args.export_only or not cpus:
                db = get_db()
                cpus = db.get_all_cpus()
                logger.info(f"Loaded {len(cpus)} CPUs from database")

            if cpus:
                export_path = export_to_flutter(logger, cpus)
                results['export'] = {'file': str(export_path), 'cpus': len(cpus)}

        results['end_time'] = datetime.now().isoformat()

        logger.info("=" * 60)
        logger.info("Scraper Completed Successfully!")
        logger.info(f"Results: {results}")
        logger.info("=" * 60)

    except KeyboardInterrupt:
        logger.warning("Scraper interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Scraper failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
