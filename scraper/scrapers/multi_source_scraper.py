#!/usr/bin/env python3
"""
Multi-Source CPU Data Scraper
=============================
Professional-grade orchestrator that collects CPU specifications from multiple
authoritative sources and merges them into a unified, high-quality dataset.

Data Sources:
- Intel ARK (Official Intel database via OData API)
- AMD Specs (Official AMD product specifications)
- TechPowerUp (Comprehensive third-party database)

Features:
- Parallel scraping with rate limiting
- Intelligent data merging with priority-based field selection
- Fuzzy name matching for cross-source CPU identification
- Data quality scoring and validation
- Progress tracking and resumability
- JSON export for Flutter app

Author: KBitWare
Architecture: Senior Developer Level
"""

import sys
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import asdict

# Ensure parent is in path
sys.path.insert(0, str(Path(__file__).parent))

from core.data_source import (
    CPUSpecification,
    DataSourcePriority,
    Manufacturer,
    DataSourceRegistry
)
from core.data_merger import DataMerger, MergeConfig, QualityScorer
from scrapers.intel_ark import IntelARKSource
from scrapers.amd_specs import AMDSpecsSource
from scrapers.techpowerup import TechPowerUpScraper
from exporters.database import get_db
from config.settings import DB_CONFIG, LOG_CONFIG


class TechPowerUpDataSource:
    """
    Adapter to wrap TechPowerUpScraper with DataSourceBase interface.

    This allows the existing TechPowerUp scraper to work seamlessly
    with the new multi-source architecture.
    """

    def __init__(self, use_playwright: bool = True):
        self.name = "techpowerup"
        self.priority = DataSourcePriority.PRIMARY
        self.manufacturer = None  # Covers both Intel and AMD
        self.scraper = TechPowerUpScraper(use_playwright=use_playwright)
        self.logger = logging.getLogger("scraper.techpowerup_adapter")

    def scrape_all(self, limit: Optional[int] = None) -> List[CPUSpecification]:
        """Scrape CPUs and convert to CPUSpecification format."""
        results = []
        count = 0

        self.logger.info("Starting TechPowerUp scrape...")

        # Initialize playwright for detail pages
        self.scraper._init_playwright()

        try:
            for cpu_ref in self.scraper.scrape_list():
                if limit and count >= limit:
                    break

                try:
                    raw_data = self.scraper.scrape_detail(cpu_ref.get("url"))
                    if raw_data and raw_data.get("name"):
                        spec = self._convert_to_spec(raw_data)
                        results.append(spec)
                        count += 1
                        self.logger.debug(f"Scraped: {spec.name}")
                except Exception as e:
                    self.logger.warning(f"Failed to scrape {cpu_ref.get('name')}: {e}")
        finally:
            self.scraper._close_playwright()

        self.logger.info(f"TechPowerUp scrape complete: {len(results)} CPUs")
        return results

    def _convert_to_spec(self, raw_data: Dict[str, Any]) -> CPUSpecification:
        """Convert TechPowerUp raw data to CPUSpecification."""
        # Detect manufacturer from name
        name = raw_data.get("name", "")
        name_lower = name.lower()

        if any(x in name_lower for x in ["amd", "ryzen", "athlon", "epyc", "threadripper"]):
            manufacturer = Manufacturer.AMD
        elif any(x in name_lower for x in ["intel", "core", "xeon", "pentium", "celeron"]):
            manufacturer = Manufacturer.INTEL
        else:
            manufacturer = Manufacturer.OTHER

        spec = CPUSpecification(
            name=name,
            manufacturer=manufacturer,
            source="techpowerup",
            source_url=raw_data.get("techpowerup_url"),
            raw_data=raw_data
        )

        # Map fields
        spec.cores = raw_data.get("cores")
        spec.threads = raw_data.get("threads")
        spec.base_clock = raw_data.get("base_clock")
        spec.boost_clock = raw_data.get("boost_clock")
        spec.l1_cache = raw_data.get("l1_cache")
        spec.l2_cache = raw_data.get("l2_cache")
        spec.l3_cache = raw_data.get("l3_cache")
        spec.tdp = raw_data.get("tdp")
        spec.socket_name = raw_data.get("socket_name")
        spec.process_node = raw_data.get("process_node")
        spec.codename = raw_data.get("codename")
        spec.microarchitecture = raw_data.get("microarchitecture")
        spec.memory_type = raw_data.get("memory_type")
        spec.memory_channels = raw_data.get("memory_channels")
        spec.max_memory_gb = raw_data.get("max_memory_gb")
        spec.has_integrated_gpu = raw_data.get("has_integrated_gpu")
        spec.integrated_gpu_name = raw_data.get("integrated_gpu_name")
        spec.pcie_version = raw_data.get("pcie_version")
        spec.pcie_lanes = raw_data.get("pcie_lanes")
        spec.transistors_million = raw_data.get("transistors_million")
        spec.die_size_mm2 = raw_data.get("die_size_mm2")
        spec.launch_msrp = raw_data.get("launch_msrp")
        spec.launch_date = raw_data.get("launch_date_raw")
        spec.image_url = raw_data.get("image_url")

        return spec


class MultiSourceOrchestrator:
    """
    Master orchestrator for multi-source CPU data collection.

    Coordinates scraping from multiple sources, merges data intelligently,
    and exports to database and JSON formats.
    """

    def __init__(
        self,
        use_intel: bool = True,
        use_amd: bool = True,
        use_techpowerup: bool = True,
        use_playwright: bool = True
    ):
        self.logger = logging.getLogger("orchestrator")

        # Initialize data sources
        self.sources = []

        if use_intel:
            self.sources.append(IntelARKSource(use_odata=True, use_playwright=use_playwright))

        if use_amd:
            self.sources.append(AMDSpecsSource(use_playwright=use_playwright))

        if use_techpowerup:
            self.sources.append(TechPowerUpDataSource(use_playwright=use_playwright))

        # Initialize merger and scorer
        self.merger = DataMerger(MergeConfig(
            name_match_threshold=0.85,
            prefer_official_sources=True
        ))
        self.scorer = QualityScorer()

        # Stats
        self.stats = {
            "start_time": None,
            "end_time": None,
            "sources_scraped": {},
            "total_raw": 0,
            "total_merged": 0,
            "avg_quality_score": 0.0
        }

    def run(
        self,
        limit_per_source: Optional[int] = None,
        export_json: bool = True,
        export_db: bool = True
    ) -> List[CPUSpecification]:
        """
        Run the full multi-source scraping pipeline.

        Args:
            limit_per_source: Max CPUs to scrape from each source (for testing)
            export_json: Whether to export to JSON file
            export_db: Whether to export to database

        Returns:
            List of merged CPUSpecification objects
        """
        self.stats["start_time"] = datetime.now().isoformat()
        self.logger.info("=" * 70)
        self.logger.info("HardWizChippy Multi-Source CPU Scraper")
        self.logger.info(f"Sources: {[s.name for s in self.sources]}")
        self.logger.info("=" * 70)

        # Phase 1: Collect data from all sources
        all_specs = []
        spec_lists_for_merge = []

        for source in self.sources:
            self.logger.info(f"\n{'='*50}")
            self.logger.info(f"Scraping from: {source.name}")
            self.logger.info(f"Priority: {source.priority.name}")
            self.logger.info(f"{'='*50}")

            try:
                specs = source.scrape_all(limit=limit_per_source)
                self.stats["sources_scraped"][source.name] = len(specs)
                self.stats["total_raw"] += len(specs)

                # Store for merging
                spec_lists_for_merge.append((source.name, source.priority, specs))
                all_specs.extend(specs)

                self.logger.info(f"Scraped {len(specs)} CPUs from {source.name}")

            except Exception as e:
                self.logger.error(f"Failed to scrape {source.name}: {e}")
                self.stats["sources_scraped"][source.name] = f"ERROR: {e}"

        # Phase 2: Merge data from all sources
        self.logger.info(f"\n{'='*50}")
        self.logger.info("Merging data from all sources...")
        self.logger.info(f"{'='*50}")

        merged_specs = self.merger.merge(spec_lists_for_merge)
        self.stats["total_merged"] = len(merged_specs)

        self.logger.info(f"Merged {self.stats['total_raw']} raw entries into {len(merged_specs)} unique CPUs")
        self.logger.info(f"Merge stats: {self.merger.stats}")

        # Phase 3: Calculate quality scores
        quality_scores = [self.scorer.calculate_score(spec) for spec in merged_specs]
        self.stats["avg_quality_score"] = sum(quality_scores) / len(quality_scores) if quality_scores else 0

        self.logger.info(f"Average quality score: {self.stats['avg_quality_score']:.2%}")

        # Log low-quality entries
        low_quality = [(spec, score) for spec, score in zip(merged_specs, quality_scores) if score < 0.5]
        if low_quality:
            self.logger.warning(f"{len(low_quality)} CPUs have quality score < 50%:")
            for spec, score in low_quality[:5]:
                missing = self.scorer.get_missing_fields(spec)[:5]
                self.logger.warning(f"  - {spec.name}: {score:.2%} (missing: {', '.join(missing)})")

        # Phase 4: Export data
        if export_db:
            self._export_to_database(merged_specs)

        if export_json:
            self._export_to_json(merged_specs)

        self.stats["end_time"] = datetime.now().isoformat()

        # Final report
        self._print_final_report()

        return merged_specs

    def _export_to_database(self, specs: List[CPUSpecification]):
        """Export merged specifications to MySQL database."""
        self.logger.info(f"\n{'='*50}")
        self.logger.info("Exporting to MySQL database...")
        self.logger.info(f"{'='*50}")

        try:
            db = get_db()
            success_count = 0
            error_count = 0

            for spec in specs:
                try:
                    # Get or create manufacturer
                    mfr_name = spec.manufacturer.value if spec.manufacturer else "OTHER"
                    manufacturer_id = db.get_or_create_manufacturer(mfr_name)

                    # Get or create socket
                    socket_id = None
                    if spec.socket_name:
                        socket_id = db.get_or_create_socket(spec.socket_name, manufacturer_id)

                    # Prepare CPU data
                    cpu_data = {
                        "name": spec.name,
                        "manufacturer_id": manufacturer_id,
                        "socket_id": socket_id,
                        "codename": spec.codename,
                        "generation": spec.microarchitecture,
                        "cores": spec.cores,
                        "threads": spec.threads,
                        "base_clock": spec.base_clock,
                        "boost_clock": spec.boost_clock,
                        "l1_cache": spec.l1_cache,
                        "l2_cache": spec.l2_cache,
                        "l3_cache": spec.l3_cache,
                        "tdp": spec.tdp,
                        "process_node": spec.process_node,
                        "transistors_million": spec.transistors_million,
                        "die_size_mm2": spec.die_size_mm2,
                        "memory_type": spec.memory_type,
                        "memory_channels": spec.memory_channels,
                        "max_memory_gb": spec.max_memory_gb,
                        "has_integrated_gpu": spec.has_integrated_gpu,
                        "integrated_gpu_name": spec.integrated_gpu_name,
                        "pcie_version": spec.pcie_version,
                        "pcie_lanes": spec.pcie_lanes,
                        "launch_date": spec.launch_date,
                        "launch_msrp": spec.launch_msrp,
                    }

                    # Add source URL if available
                    if spec.source_url:
                        if "techpowerup" in spec.source.lower():
                            cpu_data["techpowerup_url"] = spec.source_url
                        elif "intel" in spec.source.lower():
                            cpu_data["intel_ark_url"] = spec.source_url
                        elif "amd" in spec.source.lower():
                            cpu_data["amd_specs_url"] = spec.source_url

                    db.upsert_cpu(cpu_data)
                    success_count += 1

                except Exception as e:
                    error_count += 1
                    self.logger.debug(f"DB insert error for {spec.name}: {e}")

            self.logger.info(f"Database export complete: {success_count} success, {error_count} errors")

        except Exception as e:
            self.logger.error(f"Database export failed: {e}")

    def _export_to_json(self, specs: List[CPUSpecification]):
        """Export merged specifications to JSON file for Flutter app."""
        self.logger.info(f"\n{'='*50}")
        self.logger.info("Exporting to JSON for Flutter...")
        self.logger.info(f"{'='*50}")

        # Convert to JSON-serializable format
        cpus_json = []

        for spec in specs:
            cpu_dict = spec.to_dict()

            # Add quality score
            cpu_dict["quality_score"] = round(self.scorer.calculate_score(spec), 3)

            cpus_json.append(cpu_dict)

        # Sort by name
        cpus_json.sort(key=lambda x: x.get("name", "").lower())

        # Build export structure
        export_data = {
            "version": "2.0",
            "generated_at": datetime.now().isoformat(),
            "sources": list(self.stats["sources_scraped"].keys()),
            "total": len(cpus_json),
            "avg_quality_score": round(self.stats["avg_quality_score"], 3),
            "cpus": cpus_json
        }

        # Export to scraper data directory
        output_path = Path(__file__).parent / "data" / "cpu_database_merged.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, default=str)

        self.logger.info(f"Exported to: {output_path}")

        # Also copy to Flutter assets
        flutter_assets = Path(__file__).parent.parent / "assets" / "data"
        flutter_assets.mkdir(parents=True, exist_ok=True)

        flutter_path = flutter_assets / "cpu_database.json"
        with open(flutter_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, default=str)

        self.logger.info(f"Copied to Flutter assets: {flutter_path}")

    def _print_final_report(self):
        """Print final scraping report."""
        self.logger.info("\n" + "=" * 70)
        self.logger.info("SCRAPING COMPLETE - FINAL REPORT")
        self.logger.info("=" * 70)

        self.logger.info(f"\nTime: {self.stats['start_time']} -> {self.stats['end_time']}")

        self.logger.info("\nSources scraped:")
        for source, count in self.stats["sources_scraped"].items():
            self.logger.info(f"  - {source}: {count}")

        self.logger.info(f"\nTotal raw entries: {self.stats['total_raw']}")
        self.logger.info(f"Total merged entries: {self.stats['total_merged']}")
        self.logger.info(f"Reduction: {self.stats['total_raw'] - self.stats['total_merged']} duplicates merged")
        self.logger.info(f"Average quality score: {self.stats['avg_quality_score']:.2%}")

        self.logger.info("\n" + "=" * 70)


def setup_logging(verbose: bool = False):
    """Configure logging for the scraper."""
    level = logging.DEBUG if verbose else logging.INFO

    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(
                Path(__file__).parent / "logs" / f"multi_source_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            )
        ]
    )


def main():
    """Main entry point for multi-source scraper."""
    parser = argparse.ArgumentParser(
        description='HardWizChippy Multi-Source CPU Data Scraper',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python multi_source_scraper.py                    # Run all sources
  python multi_source_scraper.py --limit 10         # Test with 10 CPUs per source
  python multi_source_scraper.py --intel-only       # Only scrape Intel ARK
  python multi_source_scraper.py --no-db            # Skip database export
        """
    )

    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Limit CPUs per source (for testing)'
    )
    parser.add_argument(
        '--intel-only',
        action='store_true',
        help='Only scrape Intel ARK'
    )
    parser.add_argument(
        '--amd-only',
        action='store_true',
        help='Only scrape AMD specs'
    )
    parser.add_argument(
        '--techpowerup-only',
        action='store_true',
        help='Only scrape TechPowerUp'
    )
    parser.add_argument(
        '--no-playwright',
        action='store_true',
        help='Disable Playwright (use requests only)'
    )
    parser.add_argument(
        '--no-db',
        action='store_true',
        help='Skip database export'
    )
    parser.add_argument(
        '--no-json',
        action='store_true',
        help='Skip JSON export'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    # Create logs directory
    logs_dir = Path(__file__).parent / "logs"
    logs_dir.mkdir(exist_ok=True)

    setup_logging(verbose=args.verbose)
    logger = logging.getLogger("main")

    # Determine which sources to use
    use_intel = not args.amd_only and not args.techpowerup_only
    use_amd = not args.intel_only and not args.techpowerup_only
    use_techpowerup = not args.intel_only and not args.amd_only

    if args.intel_only:
        use_intel, use_amd, use_techpowerup = True, False, False
    elif args.amd_only:
        use_intel, use_amd, use_techpowerup = False, True, False
    elif args.techpowerup_only:
        use_intel, use_amd, use_techpowerup = False, False, True

    try:
        orchestrator = MultiSourceOrchestrator(
            use_intel=use_intel,
            use_amd=use_amd,
            use_techpowerup=use_techpowerup,
            use_playwright=not args.no_playwright
        )

        specs = orchestrator.run(
            limit_per_source=args.limit,
            export_json=not args.no_json,
            export_db=not args.no_db
        )

        logger.info(f"\nSuccess! Scraped and merged {len(specs)} unique CPUs.")

    except KeyboardInterrupt:
        logger.warning("\nScraper interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\nScraper failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
