"""
HardWizChippy Scraper Core Package
"""
from .data_source import (
    CPUSpecification,
    Manufacturer,
    DataSourcePriority,
    DataSourceBase,
    DataSourceRegistry
)
from .data_merger import DataMerger, MergeConfig, CPUNameMatcher, QualityScorer

__all__ = [
    'CPUSpecification',
    'Manufacturer',
    'DataSourcePriority',
    'DataSourceBase',
    'DataSourceRegistry',
    'DataMerger',
    'MergeConfig',
    'CPUNameMatcher',
    'QualityScorer',
]
