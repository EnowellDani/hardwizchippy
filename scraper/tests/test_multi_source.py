#!/usr/bin/env python3
"""
Multi-Source Scraper Test Suite
===============================
Tests the Intel ARK, AMD, and TechPowerUp scrapers with data validation.

Run this script to verify the scrapers are working correctly before
running a full scrape.

Usage:
    python test_multi_source.py              # Test all sources
    python test_multi_source.py --intel      # Test Intel ARK only
    python test_multi_source.py --amd        # Test AMD only
    python test_multi_source.py --tpu        # Test TechPowerUp only

Author: KBitWare
"""

import sys
import logging
from pathlib import Path
from typing import List, Dict, Any

sys.path.insert(0, str(Path(__file__).parent))

from core.data_source import CPUSpecification, DataSourcePriority
from core.data_merger import DataMerger, MergeConfig, QualityScorer, CPUNameMatcher
from scrapers.intel_ark import IntelARKSource
from scrapers.amd_specs import AMDSpecsSource
from scrapers.techpowerup import TechPowerUpScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test")


def test_intel_ark(limit: int = 3) -> List[CPUSpecification]:
    """Test Intel ARK scraper."""
    logger.info("=" * 60)
    logger.info("Testing Intel ARK Scraper")
    logger.info("=" * 60)

    scraper = IntelARKSource(use_odata=True, use_playwright=True)

    try:
        results = scraper.scrape_all(limit=limit)
        logger.info(f"Scraped {len(results)} CPUs from Intel ARK")

        for cpu in results:
            _print_cpu_summary(cpu, "Intel ARK")
            _validate_cpu(cpu)

        return results

    except Exception as e:
        logger.error(f"Intel ARK test failed: {e}")
        return []

    finally:
        scraper._close_playwright()


def test_amd_specs(limit: int = 3) -> List[CPUSpecification]:
    """Test AMD Specs scraper."""
    logger.info("=" * 60)
    logger.info("Testing AMD Specs Scraper")
    logger.info("=" * 60)

    scraper = AMDSpecsSource(use_playwright=True)

    try:
        results = scraper.scrape_all(limit=limit)
        logger.info(f"Scraped {len(results)} CPUs from AMD Specs")

        for cpu in results:
            _print_cpu_summary(cpu, "AMD Specs")
            _validate_cpu(cpu)

        return results

    except Exception as e:
        logger.error(f"AMD Specs test failed: {e}")
        return []

    finally:
        scraper._close_playwright()


def test_techpowerup(limit: int = 3) -> List[CPUSpecification]:
    """Test TechPowerUp scraper via adapter."""
    logger.info("=" * 60)
    logger.info("Testing TechPowerUp Scraper")
    logger.info("=" * 60)

    scraper = TechPowerUpScraper(use_playwright=True)
    results = []

    try:
        scraper._init_playwright()
        count = 0

        for cpu_ref in scraper.scrape_list():
            if count >= limit:
                break

            raw_data = scraper.scrape_detail(cpu_ref.get("url"))
            if raw_data and raw_data.get("name"):
                # Convert to CPUSpecification for consistency
                spec = _convert_tpu_to_spec(raw_data)
                results.append(spec)
                _print_cpu_summary(spec, "TechPowerUp")
                _validate_cpu(spec)
                count += 1

        logger.info(f"Scraped {len(results)} CPUs from TechPowerUp")
        return results

    except Exception as e:
        logger.error(f"TechPowerUp test failed: {e}")
        return []

    finally:
        scraper._close_playwright()


def _convert_tpu_to_spec(raw_data: Dict[str, Any]) -> CPUSpecification:
    """Convert TechPowerUp raw data to CPUSpecification."""
    from core.data_source import Manufacturer

    name = raw_data.get("name", "")
    name_lower = name.lower()

    if any(x in name_lower for x in ["amd", "ryzen", "athlon", "epyc"]):
        manufacturer = Manufacturer.AMD
    elif any(x in name_lower for x in ["intel", "core", "xeon"]):
        manufacturer = Manufacturer.INTEL
    else:
        manufacturer = Manufacturer.OTHER

    spec = CPUSpecification(
        name=name,
        manufacturer=manufacturer,
        source="techpowerup",
        source_url=raw_data.get("techpowerup_url")
    )

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

    return spec


def _print_cpu_summary(cpu: CPUSpecification, source: str):
    """Print a summary of CPU specs."""
    print(f"\n  [{source}] {cpu.name}")
    print(f"    Cores: {cpu.cores}, Threads: {cpu.threads}")
    print(f"    Base: {cpu.base_clock} MHz, Boost: {cpu.boost_clock} MHz")
    print(f"    TDP: {cpu.tdp}W, Cache L3: {cpu.l3_cache} KB")
    print(f"    Socket: {cpu.socket_name}, Process: {cpu.process_node}")


def _validate_cpu(cpu: CPUSpecification) -> bool:
    """Validate CPU data completeness."""
    scorer = QualityScorer()
    score = scorer.calculate_score(cpu)
    missing = scorer.get_missing_fields(cpu)

    if score < 0.5:
        logger.warning(f"  LOW QUALITY ({score:.1%}): Missing {', '.join(missing[:5])}")
        return False
    else:
        logger.info(f"  Quality score: {score:.1%}")
        return True


def test_name_matcher():
    """Test CPU name matching algorithm."""
    logger.info("=" * 60)
    logger.info("Testing CPU Name Matcher")
    logger.info("=" * 60)

    matcher = CPUNameMatcher()

    # Test cases
    test_pairs = [
        ("Intel Core i9-14900K", "Core i9-14900K"),
        ("AMD Ryzen 9 7950X", "Ryzen 9 7950X Processor"),
        ("Intel® Core™ i7-13700K Processor", "Core i7 13700K"),
        ("AMD Ryzen™ 7 5800X3D", "Ryzen 7 5800X3D"),
        ("Intel Core i5-12400", "AMD Ryzen 5 5600X"),  # Should NOT match
    ]

    for name1, name2 in test_pairs:
        similarity = matcher.calculate_similarity(name1, name2)
        key1 = matcher.extract_model_key(name1)
        key2 = matcher.extract_model_key(name2)

        print(f"\n  '{name1}' vs '{name2}'")
        print(f"    Keys: '{key1}' vs '{key2}'")
        print(f"    Similarity: {similarity:.2%}")

        if similarity >= 0.85:
            print(f"    Result: MATCH ✓")
        else:
            print(f"    Result: NO MATCH ✗")


def test_data_merger():
    """Test data merger with sample data."""
    logger.info("=" * 60)
    logger.info("Testing Data Merger")
    logger.info("=" * 60)

    from core.data_source import Manufacturer

    # Create sample specs from different sources
    intel_spec = CPUSpecification(
        name="Intel Core i9-14900K",
        manufacturer=Manufacturer.INTEL,
        source="intel_ark",
        cores=24,
        threads=32,
        base_clock=3200,
        boost_clock=6000,
        tdp=125,
        socket_name="LGA 1700"
    )

    tpu_spec = CPUSpecification(
        name="Core i9-14900K",  # Slightly different name
        manufacturer=Manufacturer.INTEL,
        source="techpowerup",
        cores=24,
        threads=32,
        base_clock=3200,
        boost_clock=6000,
        l3_cache=36864,  # Extra data from TPU
        process_node="Intel 7",
        transistors_million=8000
    )

    # Merge
    merger = DataMerger(MergeConfig())
    spec_lists = [
        ("intel_ark", DataSourcePriority.OFFICIAL, [intel_spec]),
        ("techpowerup", DataSourcePriority.PRIMARY, [tpu_spec])
    ]

    merged = merger.merge(spec_lists)

    print(f"\n  Merged {len(merged)} CPUs")
    print(f"  Merge stats: {merger.stats}")

    if merged:
        cpu = merged[0]
        print(f"\n  Merged result: {cpu.name}")
        print(f"    Source: {cpu.source}")
        print(f"    Cores: {cpu.cores}, L3 Cache: {cpu.l3_cache} KB")
        print(f"    Transistors: {cpu.transistors_million}M (gap filled from TPU)")


def main():
    """Run all tests."""
    import argparse

    parser = argparse.ArgumentParser(description="Test Multi-Source Scrapers")
    parser.add_argument("--intel", action="store_true", help="Test Intel ARK only")
    parser.add_argument("--amd", action="store_true", help="Test AMD only")
    parser.add_argument("--tpu", action="store_true", help="Test TechPowerUp only")
    parser.add_argument("--matcher", action="store_true", help="Test name matcher only")
    parser.add_argument("--merger", action="store_true", help="Test data merger only")
    parser.add_argument("--limit", type=int, default=3, help="CPUs per source (default: 3)")

    args = parser.parse_args()

    run_all = not any([args.intel, args.amd, args.tpu, args.matcher, args.merger])

    print("\n" + "=" * 70)
    print("HardWizChippy Multi-Source Scraper Test Suite")
    print("=" * 70)

    results = {}

    # Test name matcher
    if run_all or args.matcher:
        test_name_matcher()

    # Test data merger
    if run_all or args.merger:
        test_data_merger()

    # Test Intel ARK
    if run_all or args.intel:
        results["intel_ark"] = test_intel_ark(limit=args.limit)

    # Test AMD
    if run_all or args.amd:
        results["amd_specs"] = test_amd_specs(limit=args.limit)

    # Test TechPowerUp
    if run_all or args.tpu:
        results["techpowerup"] = test_techpowerup(limit=args.limit)

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    total = 0
    for source, cpus in results.items():
        print(f"  {source}: {len(cpus)} CPUs scraped")
        total += len(cpus)

    print(f"\n  Total: {total} CPUs")
    print("=" * 70)

    if total > 0:
        print("\n✓ Tests passed! Scrapers are working.")
    else:
        print("\n✗ No data scraped. Check logs for errors.")


if __name__ == "__main__":
    main()
