"""
HardWizChippy Scrapers Package
"""
from .techpowerup import TechPowerUpScraper
from .pcpartpicker import PCPartPickerScraper
from .passmark import PassMarkScraper
from .geekbench import GeekbenchScraper
from .cinebench import CinebenchScraper
from .tomshardware import TomsHardwareScraper

__all__ = [
    'TechPowerUpScraper',
    'PCPartPickerScraper',
    'PassMarkScraper',
    'GeekbenchScraper',
    'CinebenchScraper',
    'TomsHardwareScraper',
]
