"""
Intelligent Data Merger
=======================
Combines CPU specifications from multiple data sources into a unified,
high-quality dataset.

Features:
- Fuzzy name matching for cross-source CPU identification
- Priority-based field selection (official sources preferred)
- Conflict resolution with configurable strategies
- Gap filling from secondary sources
- Data validation and quality scoring

Author: KBitWare
Architecture: Senior Developer Level
"""

import re
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict
from difflib import SequenceMatcher
import logging

from core.data_source import (
    CPUSpecification,
    Manufacturer,
    DataSourcePriority
)


@dataclass
class MergeConfig:
    """Configuration for the merge process."""

    # Minimum similarity score for name matching (0.0 to 1.0)
    name_match_threshold: float = 0.85

    # Whether to prefer official sources over all others
    prefer_official_sources: bool = True

    # Fields that should never be overwritten by lower-priority sources
    protected_fields: Set[str] = field(default_factory=lambda: {
        'name', 'manufacturer', 'source', 'source_id'
    })

    # Fields where higher values are preferred (e.g., benchmarks)
    prefer_higher_fields: Set[str] = field(default_factory=lambda: {
        'geekbench_single', 'geekbench_multi',
        'passmark_single', 'passmark_multi',
        'cinebench_single', 'cinebench_multi'
    })

    # Fields where the most recent data is preferred
    prefer_recent_fields: Set[str] = field(default_factory=lambda: {
        'current_price', 'is_discontinued'
    })


class CPUNameMatcher:
    """
    Intelligent CPU name matching across different sources.

    Handles variations like:
    - "Intel Core i9-14900K" vs "Core i9-14900K"
    - "AMD Ryzen 9 7950X" vs "Ryzen 9 7950X"
    - "AMD Ryzen™ 9 7950X Processor" vs "Ryzen 9 7950X"
    """

    # Patterns to strip for matching
    STRIP_PATTERNS = [
        r'^(intel|amd)\s+',           # Manufacturer prefix
        r'\s+processor$',              # "Processor" suffix
        r'[®™©]',                      # Trademark symbols
        r'\s+\([^)]+\)$',              # Trailing parenthetical
        r'\s+w/\s+.*$',                # "w/ Radeon Graphics" etc
        r'\s+with\s+.*$',              # "with Radeon Graphics" etc
    ]

    # Model number extraction pattern
    MODEL_PATTERN = re.compile(
        r'(core\s+)?(i[3579]|ultra\s+[579]|ryzen\s+[3579]|threadripper|athlon|epyc|xeon)'
        r'[\s-]*'
        r'(\d{3,5}[a-z]*)',
        re.IGNORECASE
    )

    def __init__(self):
        self.logger = logging.getLogger("merger.matcher")
        self._canonical_cache: Dict[str, str] = {}

    def get_canonical_name(self, name: str) -> str:
        """
        Convert a CPU name to its canonical form for matching.

        Examples:
            "Intel® Core™ i9-14900K Processor" -> "core i9 14900k"
            "AMD Ryzen™ 9 7950X" -> "ryzen 9 7950x"
        """
        if name in self._canonical_cache:
            return self._canonical_cache[name]

        canonical = name.lower()

        # Apply strip patterns
        for pattern in self.STRIP_PATTERNS:
            canonical = re.sub(pattern, '', canonical, flags=re.IGNORECASE)

        # Normalize whitespace and dashes
        canonical = re.sub(r'[-_]+', ' ', canonical)
        canonical = ' '.join(canonical.split())

        self._canonical_cache[name] = canonical
        return canonical

    def extract_model_key(self, name: str) -> Optional[str]:
        """
        Extract the essential model identifier for fast matching.

        Returns the core model number that uniquely identifies the CPU.
        """
        canonical = self.get_canonical_name(name)
        match = self.MODEL_PATTERN.search(canonical)

        if match:
            # Combine family and model number
            family = (match.group(1) or "") + (match.group(2) or "")
            model = match.group(3) or ""
            return f"{family.strip()} {model}".strip().lower()

        return None

    def calculate_similarity(self, name1: str, name2: str) -> float:
        """
        Calculate similarity score between two CPU names.

        Returns a value between 0.0 (no match) and 1.0 (perfect match).
        """
        # First try exact model key matching
        key1 = self.extract_model_key(name1)
        key2 = self.extract_model_key(name2)

        if key1 and key2:
            if key1 == key2:
                return 1.0
            # Compare model keys
            return SequenceMatcher(None, key1, key2).ratio()

        # Fall back to canonical name comparison
        canonical1 = self.get_canonical_name(name1)
        canonical2 = self.get_canonical_name(name2)

        if canonical1 == canonical2:
            return 1.0

        return SequenceMatcher(None, canonical1, canonical2).ratio()

    def find_best_match(
        self,
        target: str,
        candidates: List[str],
        threshold: float = 0.85
    ) -> Optional[Tuple[str, float]]:
        """
        Find the best matching name from a list of candidates.

        Returns:
            Tuple of (matched_name, similarity_score) or None if no match
        """
        best_match = None
        best_score = 0.0

        for candidate in candidates:
            score = self.calculate_similarity(target, candidate)
            if score > best_score and score >= threshold:
                best_score = score
                best_match = candidate

        return (best_match, best_score) if best_match else None


class DataMerger:
    """
    Merges CPU specifications from multiple data sources.

    Implements intelligent conflict resolution and gap filling
    to produce a high-quality unified dataset.
    """

    def __init__(self, config: Optional[MergeConfig] = None):
        self.config = config or MergeConfig()
        self.matcher = CPUNameMatcher()
        self.logger = logging.getLogger("merger")

        # Stats tracking
        self.stats = {
            'total_input': 0,
            'merged': 0,
            'conflicts_resolved': 0,
            'gaps_filled': 0
        }

    def merge(
        self,
        spec_lists: List[Tuple[str, DataSourcePriority, List[CPUSpecification]]]
    ) -> List[CPUSpecification]:
        """
        Merge CPU specifications from multiple sources.

        Args:
            spec_lists: List of (source_name, priority, specs) tuples

        Returns:
            Unified list of merged CPUSpecification objects
        """
        self.logger.info("Starting data merge...")
        self.stats = {'total_input': 0, 'merged': 0, 'conflicts_resolved': 0, 'gaps_filled': 0}

        # Sort by priority (lower = higher priority)
        spec_lists = sorted(spec_lists, key=lambda x: x[1].value)

        # Group specs by canonical name
        groups: Dict[str, List[CPUSpecification]] = defaultdict(list)

        for source_name, priority, specs in spec_lists:
            self.stats['total_input'] += len(specs)

            for spec in specs:
                canonical = self.matcher.get_canonical_name(spec.name)
                model_key = self.matcher.extract_model_key(spec.name) or canonical
                groups[model_key].append(spec)

        # Merge each group
        merged_results = []

        for key, group in groups.items():
            if len(group) == 1:
                merged_results.append(group[0])
            else:
                merged = self._merge_group(group)
                merged_results.append(merged)
                self.stats['merged'] += 1

        self.logger.info(
            f"Merge complete: {len(merged_results)} unique CPUs from "
            f"{self.stats['total_input']} inputs, "
            f"{self.stats['merged']} merged, "
            f"{self.stats['gaps_filled']} gaps filled"
        )

        return merged_results

    def _merge_group(self, group: List[CPUSpecification]) -> CPUSpecification:
        """
        Merge a group of specifications for the same CPU.

        Uses priority-based field selection with conflict resolution.
        """
        # Sort by source priority (official sources first)
        group = sorted(group, key=lambda s: self._get_source_priority(s))

        # Start with the highest priority spec as base
        base = group[0]
        result_dict = base.to_dict()

        # Merge in fields from lower-priority sources
        for spec in group[1:]:
            spec_dict = spec.to_dict()

            for field, value in spec_dict.items():
                if field in self.config.protected_fields:
                    continue

                if value is None:
                    continue

                current_value = result_dict.get(field)

                # Gap filling: fill in missing values
                if current_value is None:
                    result_dict[field] = value
                    self.stats['gaps_filled'] += 1
                    continue

                # Conflict resolution
                if current_value != value:
                    resolved = self._resolve_conflict(field, current_value, value, base, spec)
                    if resolved != current_value:
                        result_dict[field] = resolved
                        self.stats['conflicts_resolved'] += 1

        # Create merged specification
        merged = CPUSpecification(
            name=result_dict['name'],
            manufacturer=Manufacturer(result_dict['manufacturer']) if result_dict.get('manufacturer') else base.manufacturer,
            source=f"merged({','.join(s.source for s in group)})"
        )

        # Copy all fields
        for field, value in result_dict.items():
            if hasattr(merged, field) and field not in ['name', 'manufacturer', 'source']:
                setattr(merged, field, value)

        return merged

    def _get_source_priority(self, spec: CPUSpecification) -> int:
        """Get numeric priority for a specification's source."""
        source_priorities = {
            'intel_ark': 1,
            'amd_specs': 1,
            'techpowerup': 2,
            'geekbench': 3,
            'passmark': 3,
        }
        return source_priorities.get(spec.source, 10)

    def _resolve_conflict(
        self,
        field: str,
        value1: Any,
        value2: Any,
        spec1: CPUSpecification,
        spec2: CPUSpecification
    ) -> Any:
        """
        Resolve a conflict between two values for the same field.

        Uses field-specific strategies for intelligent resolution.
        """
        # For benchmark fields, prefer higher values
        if field in self.config.prefer_higher_fields:
            if isinstance(value1, (int, float)) and isinstance(value2, (int, float)):
                return max(value1, value2)

        # For boolean fields, prefer True if either is True
        if isinstance(value1, bool) and isinstance(value2, bool):
            if field == 'is_discontinued':
                return value1 or value2  # If any source says discontinued, it is
            if field == 'has_integrated_gpu':
                return value1 or value2

        # For numeric fields with significant difference, prefer official source
        if isinstance(value1, (int, float)) and isinstance(value2, (int, float)):
            # If values differ by more than 10%, log warning
            if value1 > 0 and abs(value1 - value2) / value1 > 0.1:
                self.logger.debug(
                    f"Significant conflict for {field}: {value1} vs {value2} "
                    f"(keeping {value1} from {spec1.source})"
                )

        # Default: prefer first (higher priority) source
        return value1

    def fill_gaps(
        self,
        primary: List[CPUSpecification],
        secondary: List[CPUSpecification]
    ) -> List[CPUSpecification]:
        """
        Fill gaps in primary dataset using secondary data.

        Only fills None fields, never overwrites existing data.
        """
        # Build index of secondary specs by model key
        secondary_index: Dict[str, CPUSpecification] = {}
        for spec in secondary:
            key = self.matcher.extract_model_key(spec.name)
            if key:
                secondary_index[key] = spec

        filled = []
        for spec in primary:
            key = self.matcher.extract_model_key(spec.name)
            secondary_spec = secondary_index.get(key) if key else None

            if secondary_spec:
                spec = self._fill_spec_gaps(spec, secondary_spec)

            filled.append(spec)

        return filled

    def _fill_spec_gaps(
        self,
        primary: CPUSpecification,
        secondary: CPUSpecification
    ) -> CPUSpecification:
        """Fill None fields in primary from secondary."""
        primary_dict = primary.to_dict()
        secondary_dict = secondary.to_dict()

        for field, value in secondary_dict.items():
            if field in self.config.protected_fields:
                continue
            if primary_dict.get(field) is None and value is not None:
                primary_dict[field] = value
                self.stats['gaps_filled'] += 1

        # Reconstruct spec
        result = CPUSpecification(
            name=primary.name,
            manufacturer=primary.manufacturer,
            source=primary.source
        )
        for field, value in primary_dict.items():
            if hasattr(result, field) and field not in ['name', 'manufacturer', 'source']:
                setattr(result, field, value)

        return result


class QualityScorer:
    """
    Calculates data quality scores for CPU specifications.

    Useful for identifying incomplete records and prioritizing
    data enrichment efforts.
    """

    # Fields and their weights for quality scoring
    FIELD_WEIGHTS = {
        # Essential fields (high weight)
        'name': 10,
        'manufacturer': 10,
        'cores': 8,
        'threads': 8,
        'base_clock': 8,
        'boost_clock': 7,
        'tdp': 7,

        # Important fields (medium weight)
        'l2_cache': 5,
        'l3_cache': 5,
        'socket_name': 5,
        'process_node': 5,
        'memory_type': 4,
        'launch_date': 4,

        # Nice to have (low weight)
        'launch_msrp': 3,
        'pcie_version': 3,
        'pcie_lanes': 2,
        'transistors_million': 2,
        'die_size_mm2': 2,

        # Benchmarks (optional)
        'geekbench_single': 2,
        'geekbench_multi': 2,
        'passmark_single': 2,
        'passmark_multi': 2,
    }

    def calculate_score(self, spec: CPUSpecification) -> float:
        """
        Calculate quality score for a specification.

        Returns:
            Score between 0.0 (no data) and 1.0 (complete data)
        """
        total_weight = sum(self.FIELD_WEIGHTS.values())
        achieved_weight = 0

        spec_dict = spec.to_dict()

        for field, weight in self.FIELD_WEIGHTS.items():
            value = spec_dict.get(field)
            if value is not None:
                achieved_weight += weight

        return achieved_weight / total_weight

    def get_missing_fields(self, spec: CPUSpecification) -> List[str]:
        """Get list of important missing fields."""
        missing = []
        spec_dict = spec.to_dict()

        for field in self.FIELD_WEIGHTS:
            if spec_dict.get(field) is None:
                missing.append(field)

        return sorted(missing, key=lambda f: -self.FIELD_WEIGHTS.get(f, 0))
