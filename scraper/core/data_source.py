"""
Abstract Data Source Interface
==============================
Defines the contract for all CPU data sources in the HardWizChippy scraper system.

This module implements the Strategy Pattern, allowing different data sources
(Intel ARK, AMD, TechPowerUp, etc.) to be used interchangeably while maintaining
a consistent interface.

Author: KBitWare
Architecture: Senior Developer Level
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Generator
from enum import Enum
from datetime import datetime
import logging


class Manufacturer(Enum):
    """Supported CPU manufacturers."""
    INTEL = "Intel"
    AMD = "AMD"
    OTHER = "Other"


class DataSourcePriority(Enum):
    """
    Priority levels for data sources.
    Higher priority sources are preferred when merging data.
    """
    OFFICIAL = 1      # Official manufacturer APIs (Intel ARK, AMD)
    PRIMARY = 2       # High-quality third-party (TechPowerUp)
    SECONDARY = 3     # Supplementary sources (GitHub datasets)
    BENCHMARK = 4     # Benchmark-only sources (Geekbench, PassMark)


@dataclass
class CPUSpecification:
    """
    Unified CPU specification data model.

    All data sources normalize their data to this format,
    enabling consistent merging and storage.
    """
    # === Identification ===
    name: str
    manufacturer: Manufacturer
    source: str  # Which data source provided this
    source_url: Optional[str] = None
    source_id: Optional[str] = None  # Unique ID from source (ARK ID, etc.)

    # === Core Configuration ===
    cores: Optional[int] = None
    threads: Optional[int] = None
    p_cores: Optional[int] = None  # Performance cores (Intel hybrid)
    e_cores: Optional[int] = None  # Efficiency cores (Intel hybrid)

    # === Clock Speeds (MHz) ===
    base_clock: Optional[int] = None
    boost_clock: Optional[int] = None
    p_core_base_clock: Optional[int] = None
    p_core_boost_clock: Optional[int] = None
    e_core_base_clock: Optional[int] = None
    e_core_boost_clock: Optional[int] = None

    # === Cache (KB) ===
    l1_cache: Optional[int] = None
    l2_cache: Optional[int] = None
    l3_cache: Optional[int] = None

    # === Power (Watts) ===
    tdp: Optional[int] = None
    base_power: Optional[int] = None
    max_turbo_power: Optional[int] = None

    # === Architecture ===
    codename: Optional[str] = None
    microarchitecture: Optional[str] = None
    generation: Optional[str] = None
    socket_name: Optional[str] = None
    process_node: Optional[str] = None

    # === Physical ===
    transistors_million: Optional[int] = None
    die_size_mm2: Optional[float] = None

    # === Memory ===
    memory_type: Optional[str] = None
    memory_channels: Optional[int] = None
    max_memory_gb: Optional[int] = None
    memory_speed: Optional[str] = None

    # === Graphics ===
    has_integrated_gpu: Optional[bool] = None
    integrated_gpu_name: Optional[str] = None

    # === PCIe ===
    pcie_version: Optional[str] = None
    pcie_lanes: Optional[int] = None

    # === Launch Info ===
    launch_date: Optional[str] = None
    launch_msrp: Optional[float] = None

    # === Status ===
    is_released: Optional[bool] = None
    is_discontinued: Optional[bool] = None

    # === Benchmarks ===
    geekbench_single: Optional[int] = None
    geekbench_multi: Optional[int] = None
    passmark_single: Optional[int] = None
    passmark_multi: Optional[int] = None
    cinebench_single: Optional[int] = None
    cinebench_multi: Optional[int] = None

    # === Media ===
    image_url: Optional[str] = None

    # === Metadata ===
    scraped_at: datetime = field(default_factory=datetime.now)
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database insertion."""
        result = {}
        for key, value in self.__dict__.items():
            if key == 'manufacturer':
                result[key] = value.value if value else None
            elif key == 'scraped_at':
                result[key] = value.isoformat() if value else None
            elif key == 'raw_data':
                continue  # Skip raw data for DB
            else:
                result[key] = value
        return result

    def get_canonical_name(self) -> str:
        """Get a standardized name for matching across sources."""
        name = self.name.lower()
        # Remove common prefixes
        for prefix in ['intel ', 'amd ', 'processor ']:
            if name.startswith(prefix):
                name = name[len(prefix):]
        # Normalize spacing and special chars
        name = ' '.join(name.split())
        return name


class DataSourceBase(ABC):
    """
    Abstract base class for all CPU data sources.

    Implements Template Method pattern for common scraping workflow
    while allowing subclasses to customize specific steps.
    """

    def __init__(
        self,
        name: str,
        priority: DataSourcePriority,
        manufacturer: Optional[Manufacturer] = None
    ):
        self.name = name
        self.priority = priority
        self.manufacturer = manufacturer
        self.logger = logging.getLogger(f"scraper.{name}")
        self._cache: Dict[str, CPUSpecification] = {}

    @property
    @abstractmethod
    def source_url(self) -> str:
        """Base URL for this data source."""
        pass

    @abstractmethod
    def fetch_cpu_list(self) -> Generator[Dict[str, Any], None, None]:
        """
        Fetch list of available CPUs from the source.

        Yields:
            Dict with at minimum 'name' and 'url' or 'id' keys
        """
        pass

    @abstractmethod
    def fetch_cpu_details(self, cpu_ref: Dict[str, Any]) -> Optional[CPUSpecification]:
        """
        Fetch detailed specifications for a single CPU.

        Args:
            cpu_ref: Reference dict from fetch_cpu_list()

        Returns:
            CPUSpecification object or None if fetch failed
        """
        pass

    @abstractmethod
    def normalize_data(self, raw_data: Dict[str, Any]) -> CPUSpecification:
        """
        Normalize raw data from source to unified CPUSpecification format.

        Args:
            raw_data: Raw data dict from the source

        Returns:
            Normalized CPUSpecification object
        """
        pass

    def scrape_all(
        self,
        limit: Optional[int] = None,
        filter_fn: Optional[callable] = None
    ) -> List[CPUSpecification]:
        """
        Scrape all CPUs from this source.

        Args:
            limit: Maximum number of CPUs to scrape (None for all)
            filter_fn: Optional filter function for CPU references

        Returns:
            List of CPUSpecification objects
        """
        results = []
        count = 0

        self.logger.info(f"Starting scrape from {self.name}")

        for cpu_ref in self.fetch_cpu_list():
            if limit and count >= limit:
                break

            if filter_fn and not filter_fn(cpu_ref):
                continue

            try:
                spec = self.fetch_cpu_details(cpu_ref)
                if spec:
                    results.append(spec)
                    count += 1
                    self.logger.debug(f"Scraped: {spec.name}")
            except Exception as e:
                self.logger.warning(f"Failed to scrape {cpu_ref.get('name', 'unknown')}: {e}")

        self.logger.info(f"Completed scrape: {len(results)} CPUs from {self.name}")
        return results

    def get_cached(self, key: str) -> Optional[CPUSpecification]:
        """Get cached specification by key."""
        return self._cache.get(key)

    def set_cached(self, key: str, spec: CPUSpecification):
        """Cache a specification."""
        self._cache[key] = spec


class DataSourceRegistry:
    """
    Registry for managing multiple data sources.

    Implements Singleton pattern to ensure consistent source management
    across the application.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._sources: Dict[str, DataSourceBase] = {}
        return cls._instance

    def register(self, source: DataSourceBase):
        """Register a data source."""
        self._sources[source.name] = source

    def get(self, name: str) -> Optional[DataSourceBase]:
        """Get a registered source by name."""
        return self._sources.get(name)

    def get_all(self) -> List[DataSourceBase]:
        """Get all registered sources sorted by priority."""
        return sorted(
            self._sources.values(),
            key=lambda s: s.priority.value
        )

    def get_by_manufacturer(self, manufacturer: Manufacturer) -> List[DataSourceBase]:
        """Get sources that provide data for a specific manufacturer."""
        return [
            s for s in self.get_all()
            if s.manufacturer is None or s.manufacturer == manufacturer
        ]
