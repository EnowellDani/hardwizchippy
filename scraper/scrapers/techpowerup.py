
import re
from typing import Dict, List, Optional, Any, Generator
from bs4 import BeautifulSoup
import logging
import sys
sys.path.insert(0, "..")
from core.base_scraper import BaseScraper

class TechPowerUpScraper(BaseScraper):
    BASE_URL = "https://www.techpowerup.com"
    CPU_LIST_URL = f"{BASE_URL}/cpu-specs/"
    
    def __init__(self):
        super().__init__("techpowerup")
        self.logger = logging.getLogger("scraper.techpowerup")
    
    def scrape_list(self):
        search_terms = ["Ryzen 9", "Ryzen 7", "Ryzen 5", "Core i9", "Core i7", "Core i5"]
        seen = set()
        for term in search_terms:
            url = f"{self.CPU_LIST_URL}?search={term.replace(chr(32), chr(43))}"
            soup = self.get_soup(url)
            if not soup: continue
            table = soup.find("table", class_="items-desktop-table")
            if not table: continue
            for row in table.find_all("tr")[1:]:
                cells = row.find_all("td")
                if len(cells) < 2: continue
                link = cells[0].find("a")
                if not link: continue
                cpu_url = self.BASE_URL + link.get("href", "")
                if cpu_url in seen: continue
                seen.add(cpu_url)
                yield {"name": link.get_text(strip=True), "url": cpu_url}
    
    def scrape_detail(self, url):
        soup = self.get_soup(url)
        if not soup: return None
        data = {"techpowerup_url": url}
        spec_table = soup.find("table", class_="specs")
        if spec_table: data.update(self._parse_spec_table(spec_table))
        return data
    
    def _parse_spec_table(self, table):
        data = {}
        for row in table.find_all("tr"):
            cells = row.find_all(["th", "td"])
            if len(cells) != 2: continue
            label = cells[0].get_text(strip=True).lower()
            value = cells[1].get_text(strip=True)
            if not value or value == "N/A": continue
            self._map_field(data, label, value)
        return data
    
    def _map_field(self, data, label, value):
        if "cores" in label: data["cores"] = self._parse_int(value)
        elif "threads" in label: data["threads"] = self._parse_int(value)
        elif "base" in label and "clock" in label: data["base_clock"] = self._parse_clock(value)
        elif "boost" in label: data["boost_clock"] = self._parse_clock(value)
        elif "socket" in label: data["socket_name"] = value
        elif "tdp" in label: data["tdp"] = self._parse_power(value)
        elif "l3 cache" in label: data["l3_cache"] = self._parse_cache(value)
        elif "process" in label: data["process_node"] = value
        elif "codename" in label: data["codename"] = value
        elif "launch" in label and "date" in label: data["launch_date_raw"] = value
        elif "launch" in label and "price" in label: data["launch_msrp"] = self._parse_price(value)
    
    def _parse_int(self, t): 
        m = re.search(r"([\d,]+)", t)
        return int(m.group(1).replace(",","")) if m else None
    def _parse_clock(self, t):
        m = re.search(r"([\d.]+)\s*(GHz|MHz)", t, re.I)
        if m: return int(float(m.group(1))*1000) if m.group(2).lower()=="ghz" else int(float(m.group(1)))
        return None
    def _parse_cache(self, t):
        m = re.search(r"([\d.]+)\s*(GB|MB|KB)", t, re.I)
        if m:
            v, u = float(m.group(1)), m.group(2).upper()
            if u=="GB": return int(v*1024*1024)
            if u=="MB": return int(v*1024)
            return int(v)
        return None
    def _parse_power(self, t):
        m = re.search(r"([\d.]+)\s*W", t, re.I)
        return int(float(m.group(1))) if m else None
    def _parse_price(self, t):
        m = re.search(r"\$?([\d,]+(?:\.\d{2})?)", t)
        return float(m.group(1).replace(",","")) if m else None
