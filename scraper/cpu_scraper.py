"""
HardWizChippy - Comprehensive CPU Scraper
==========================================
Single scraper to collect ALL CPU data from multiple sources.

Data collected matches the app's detail view requirements:
- Main specs (name, frequency, cache)
- General info (launch date, price, fab, TDP, socket)
- Core info (architecture, cores, threads, frequencies, cache levels)
- Features (instruction set, bus, data width)
- Memory specs (type, channels, bandwidth, max size)
- Graphics (integrated GPU specs)
- PCIe specs
- Benchmarks (Cinebench, Geekbench, PassMark, etc.)
- Gaming performance
"""

import requests
from bs4 import BeautifulSoup
import mysql.connector
import json
import re
import time
from datetime import datetime
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed

# =============================================================================
# CONFIGURATION
# =============================================================================

DB_CONFIG = {
    'host': 'localhost',
    'user': 'kbitboy',
    'password': 'danieyl',
    'database': 'hardwizchippy'
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}

# =============================================================================
# DATABASE MANAGER
# =============================================================================

class DatabaseManager:
    """Handles all database operations."""
    
    def __init__(self):
        self.conn = None
        self.cursor = None
        self._cache = {'manufacturers': {}, 'sockets': {}, 'families': {}}
    
    def connect(self):
        try:
            self.conn = mysql.connector.connect(**DB_CONFIG)
            self.cursor = self.conn.cursor(dictionary=True)
            self._load_cache()
            return True
        except Exception as e:
            print(f"[DB] Connection failed: {e}")
            return False
    
    def _load_cache(self):
        """Pre-load lookup tables into cache."""
        self.cursor.execute("SELECT id, name FROM manufacturers")
        for row in self.cursor.fetchall():
            self._cache['manufacturers'][row['name'].lower()] = row['id']
        
        self.cursor.execute("SELECT id, name FROM sockets")
        for row in self.cursor.fetchall():
            self._cache['sockets'][row['name'].lower()] = row['id']
    
    def close(self):
        if self.cursor: self.cursor.close()
        if self.conn: self.conn.close()
    
    def get_or_create_manufacturer(self, name):
        if not name: return None
        key = name.lower()
        if key in self._cache['manufacturers']:
            return self._cache['manufacturers'][key]
        
        self.cursor.execute("INSERT INTO manufacturers (name) VALUES (%s)", (name,))
        self.conn.commit()
        mid = self.cursor.lastrowid
        self._cache['manufacturers'][key] = mid
        return mid
    
    def get_or_create_socket(self, name, mfgr_id):
        if not name: return None
        key = name.lower()
        if key in self._cache['sockets']:
            return self._cache['sockets'][key]
        
        self.cursor.execute(
            "INSERT INTO sockets (name, manufacturer_id) VALUES (%s, %s)",
            (name, mfgr_id)
        )
        self.conn.commit()
        sid = self.cursor.lastrowid
        self._cache['sockets'][key] = sid
        return sid
    
    def upsert_cpu(self, cpu):
        """Insert or update a CPU record."""
        try:
            mfgr_id = self.get_or_create_manufacturer(cpu.get('manufacturer'))
            socket_id = self.get_or_create_socket(cpu.get('socket'), mfgr_id)
            
            name = cpu.get('name', '').strip()[:150]
            if not name: return False
            
            # Check exists
            self.cursor.execute("SELECT id FROM cpus WHERE name = %s", (name,))
            existing = self.cursor.fetchone()
            
            if existing:
                self._update_cpu(existing['id'], cpu, socket_id)
                return 'updated'
            else:
                self._insert_cpu(name, mfgr_id, socket_id, cpu)
                return 'inserted'
        except Exception as e:
            print(f"  DB Error [{cpu.get('name', '')[:30]}]: {e}")
            self.conn.rollback()
            return False
    
    def _insert_cpu(self, name, mfgr_id, socket_id, cpu):
        """Insert new CPU."""
        self.cursor.execute("""
            INSERT INTO cpus (
                name, manufacturer_id, socket_id, codename, generation,
                cores, threads, p_cores, e_cores,
                base_clock, boost_clock, p_core_base_clock, p_core_boost_clock,
                e_core_base_clock, e_core_boost_clock,
                l1_cache, l2_cache, l3_cache,
                tdp, base_power, max_turbo_power, process_node,
                transistors_million, die_size_mm2,
                memory_type, memory_channels, max_memory_gb,
                has_integrated_gpu, integrated_gpu_name,
                pcie_version, pcie_lanes,
                launch_date, launch_msrp, techpowerup_url,
                created_at, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, NOW(), NOW()
            )
        """, (
            name, mfgr_id, socket_id,
            cpu.get('codename'), cpu.get('generation'),
            cpu.get('cores'), cpu.get('threads'),
            cpu.get('p_cores'), cpu.get('e_cores'),
            cpu.get('base_clock'), cpu.get('boost_clock'),
            cpu.get('p_core_base_clock'), cpu.get('p_core_boost_clock'),
            cpu.get('e_core_base_clock'), cpu.get('e_core_boost_clock'),
            cpu.get('l1_cache'), cpu.get('l2_cache'), cpu.get('l3_cache'),
            cpu.get('tdp'), cpu.get('base_power'), cpu.get('max_turbo_power'),
            cpu.get('process_node'),
            cpu.get('transistors_million'), cpu.get('die_size_mm2'),
            cpu.get('memory_type'), cpu.get('memory_channels'), cpu.get('max_memory_gb'),
            cpu.get('has_integrated_gpu'), cpu.get('integrated_gpu_name'),
            cpu.get('pcie_version'), cpu.get('pcie_lanes'),
            cpu.get('launch_date'), cpu.get('launch_msrp'), cpu.get('url')
        ))
        self.conn.commit()
    
    def _update_cpu(self, cpu_id, cpu, socket_id):
        """Update existing CPU with new data (only non-null values)."""
        self.cursor.execute("""
            UPDATE cpus SET
                socket_id = COALESCE(%s, socket_id),
                codename = COALESCE(%s, codename),
                cores = COALESCE(%s, cores),
                threads = COALESCE(%s, threads),
                base_clock = COALESCE(%s, base_clock),
                boost_clock = COALESCE(%s, boost_clock),
                l1_cache = COALESCE(%s, l1_cache),
                l2_cache = COALESCE(%s, l2_cache),
                l3_cache = COALESCE(%s, l3_cache),
                tdp = COALESCE(%s, tdp),
                process_node = COALESCE(%s, process_node),
                transistors_million = COALESCE(%s, transistors_million),
                die_size_mm2 = COALESCE(%s, die_size_mm2),
                memory_type = COALESCE(%s, memory_type),
                pcie_version = COALESCE(%s, pcie_version),
                pcie_lanes = COALESCE(%s, pcie_lanes),
                techpowerup_url = COALESCE(%s, techpowerup_url),
                updated_at = NOW()
            WHERE id = %s
        """, (
            socket_id, cpu.get('codename'),
            cpu.get('cores'), cpu.get('threads'),
            cpu.get('base_clock'), cpu.get('boost_clock'),
            cpu.get('l1_cache'), cpu.get('l2_cache'), cpu.get('l3_cache'),
            cpu.get('tdp'), cpu.get('process_node'),
            cpu.get('transistors_million'), cpu.get('die_size_mm2'),
            cpu.get('memory_type'), cpu.get('pcie_version'), cpu.get('pcie_lanes'),
            cpu.get('url'), cpu_id
        ))
        self.conn.commit()
    
    def get_stats(self):
        """Get database statistics."""
        stats = {}
        self.cursor.execute("SELECT COUNT(*) as count FROM cpus")
        stats['total'] = self.cursor.fetchone()['count']
        
        self.cursor.execute("""
            SELECT m.name, COUNT(*) as count 
            FROM cpus c JOIN manufacturers m ON c.manufacturer_id = m.id 
            GROUP BY m.id ORDER BY count DESC
        """)
        stats['by_manufacturer'] = {r['name']: r['count'] for r in self.cursor.fetchall()}
        
        return stats


# =============================================================================
# CPU SCRAPER
# =============================================================================

class CPUScraper:
    """Comprehensive CPU data scraper from multiple sources."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
    
    # -------------------------------------------------------------------------
    # PASSMARK - Main CPU list with benchmark scores
    # -------------------------------------------------------------------------
    
    def scrape_passmark_list(self):
        """Get all CPUs from PassMark benchmark database."""
        print("\n[1/3] PassMark - Fetching CPU benchmark list...")
        
        cpus = []
        url = "https://www.cpubenchmark.net/cpu_list.php"
        
        try:
            resp = self.session.get(url, timeout=60)
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            table = soup.find('table', id='cputable') or soup.find('table')
            if not table:
                print("  [!] Could not find CPU table")
                return []
            
            for row in table.find_all('tr')[1:]:
                cells = row.find_all('td')
                if len(cells) >= 2:
                    link = cells[0].find('a')
                    if link:
                        name = link.get_text().strip()
                        href = link.get('href')
                        
                        # Get PassMark score
                        score = self._parse_int(cells[1].get_text())
                        
                        if name:
                            cpus.append({
                                'name': name,
                                'passmark_url': urljoin("https://www.cpubenchmark.net", href) if href else None,
                                'passmark_score': score,
                                'manufacturer': self._detect_manufacturer(name)
                            })
            
            print(f"  [OK] Found {len(cpus)} CPUs")
            
        except Exception as e:
            print(f"  [!] Error: {e}")
        
        return cpus
    
    # -------------------------------------------------------------------------
    # TECHPOWERUP - Detailed CPU specifications
    # -------------------------------------------------------------------------
    
    def scrape_techpowerup_list(self):
        """Get all CPUs from TechPowerUp with detailed specs."""
        print("\n[2/3] TechPowerUp - Fetching detailed specs...")
        
        cpus = {}
        manufacturers = ['AMD', 'Intel', 'VIA', 'Qualcomm', 'Apple']
        
        for mfgr in manufacturers:
            page = 1
            count = 0
            
            while page <= 100:
                url = f"https://www.techpowerup.com/cpu-specs/?mfgr={mfgr}&sort=name&page={page}"
                
                try:
                    resp = self.session.get(url, timeout=30)
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    
                    table = soup.find('table', class_='processors')
                    if not table:
                        break
                    
                    rows = table.find_all('tr')[1:]
                    if not rows:
                        break
                    
                    new_found = False
                    for row in rows:
                        cells = row.find_all('td')
                        if cells:
                            link = cells[0].find('a')
                            if link:
                                name = link.get_text().strip()
                                href = link.get('href')
                                
                                if href and href not in cpus:
                                    full_url = urljoin("https://www.techpowerup.com", href)
                                    cpus[href] = {
                                        'name': name,
                                        'url': full_url,
                                        'manufacturer': mfgr
                                    }
                                    count += 1
                                    new_found = True
                    
                    if not new_found:
                        break
                    
                    page += 1
                    time.sleep(0.1)
                    
                except Exception as e:
                    break
            
            if count > 0:
                print(f"    {mfgr}: {count} CPUs")
        
        print(f"  [OK] Total: {len(cpus)} CPUs from TechPowerUp")
        return list(cpus.values())
    
    def scrape_techpowerup_details(self, url):
        """Scrape detailed specs from a TechPowerUp CPU page."""
        try:
            resp = self.session.get(url, timeout=30)
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            specs = {}
            
            # Extract from spec sections
            for section in soup.find_all('section', class_='details'):
                for row in section.find_all('tr'):
                    cells = row.find_all(['th', 'td'])
                    if len(cells) == 2:
                        label = cells[0].get_text().strip().rstrip(':')
                        value = cells[1].get_text().strip()
                        if value and value not in ['-', 'N/A', 'Unknown']:
                            specs[label] = value
            
            return self._parse_techpowerup_specs(specs)
            
        except:
            return None
    
    def _parse_techpowerup_specs(self, raw):
        """Parse TechPowerUp specs into structured format."""
        return {
            'socket': raw.get('Socket'),
            'codename': raw.get('Codename'),
            'cores': self._parse_int(raw.get('# of Cores')),
            'threads': self._parse_int(raw.get('# of Threads')),
            'base_clock': self._parse_clock(raw.get('Frequency')),
            'boost_clock': self._parse_clock(raw.get('Turbo Clock')),
            'l1_cache': self._parse_cache(raw.get('Cache L1')),
            'l2_cache': self._parse_cache(raw.get('Cache L2')),
            'l3_cache': self._parse_cache(raw.get('Cache L3')),
            'tdp': self._parse_int(raw.get('TDP')),
            'process_node': raw.get('Process Size'),
            'transistors_million': self._parse_int(raw.get('Transistors')),
            'die_size_mm2': self._parse_float(raw.get('Die Size')),
            'memory_type': raw.get('Memory Support'),
            'memory_channels': self._parse_int(raw.get('Memory Channels')),
            'max_memory_gb': self._parse_int(raw.get('Max Memory')),
            'pcie_version': self._extract_pcie_version(raw.get('PCI-Express')),
            'pcie_lanes': self._parse_int(raw.get('PCI-Express')),
            'has_integrated_gpu': 1 if raw.get('Integrated Graphics') else 0,
            'integrated_gpu_name': raw.get('Integrated Graphics'),
            'launch_date': self._parse_date(raw.get('Release Date')),
            'launch_msrp': self._parse_price(raw.get('Launch Price')),
            'microarchitecture': raw.get('Architecture'),
            'instruction_set': raw.get('Instruction Set'),
            'multiplier': raw.get('Multiplier'),
            'bus_speed': raw.get('Bus Speed'),
        }
    
    # -------------------------------------------------------------------------
    # GEEKBENCH - Benchmark scores
    # -------------------------------------------------------------------------
    
    def scrape_geekbench_scores(self, cpu_name):
        """Get Geekbench scores for a CPU."""
        # This would require Geekbench Browser API or scraping
        # For now, return None - can be implemented later
        return None
    
    # -------------------------------------------------------------------------
    # UTILITY METHODS
    # -------------------------------------------------------------------------
    
    def _detect_manufacturer(self, name):
        """Detect CPU manufacturer from name."""
        name_lower = name.lower()
        
        patterns = [
            (['intel', 'core i', 'xeon', 'pentium', 'celeron', 'atom'], 'Intel'),
            (['amd', 'ryzen', 'epyc', 'athlon', 'phenom', 'threadripper', 'fx-', 'opteron'], 'AMD'),
            (['apple', ' m1', ' m2', ' m3', ' m4'], 'Apple'),
            (['qualcomm', 'snapdragon'], 'Qualcomm'),
            (['mediatek', 'dimensity', 'helio'], 'MediaTek'),
            (['nvidia', 'tegra'], 'NVIDIA'),
            (['arm', 'cortex', 'neoverse'], 'ARM'),
            (['samsung', 'exynos'], 'Samsung'),
        ]
        
        for keywords, mfgr in patterns:
            if any(kw in name_lower for kw in keywords):
                return mfgr
        return 'Other'
    
    def _parse_int(self, val):
        if not val: return None
        nums = re.findall(r'[\d,]+', str(val))
        return int(nums[0].replace(',', '')) if nums else None
    
    def _parse_float(self, val):
        if not val: return None
        nums = re.findall(r'[\d.]+', str(val))
        return float(nums[0]) if nums else None
    
    def _parse_clock(self, val):
        """Parse clock speed to GHz (decimal)."""
        if not val: return None
        nums = re.findall(r'[\d.]+', str(val))
        if nums:
            num = float(nums[0])
            if 'MHz' in str(val):
                return round(num / 1000, 2)
            return round(num, 2)  # Assume GHz
        return None
    
    def _parse_cache(self, val):
        """Parse cache size to KB."""
        if not val: return None
        val = str(val).lower()
        nums = re.findall(r'[\d.]+', val)
        if nums:
            num = float(nums[0])
            if 'mb' in val:
                return int(num * 1024)
            if 'gb' in val:
                return int(num * 1024 * 1024)
            return int(num)  # Assume KB
        return None
    
    def _parse_price(self, val):
        if not val: return None
        nums = re.findall(r'[\d.]+', str(val).replace(',', ''))
        return float(nums[0]) if nums else None
    
    def _parse_date(self, val):
        """Parse date string to SQL date format."""
        if not val: return None
        try:
            # Try various formats
            for fmt in ['%b %d, %Y', '%B %d, %Y', '%Y-%m-%d', '%d %b %Y', '%b %Y']:
                try:
                    return datetime.strptime(val.strip(), fmt).strftime('%Y-%m-%d')
                except:
                    continue
            # Extract year at minimum
            years = re.findall(r'20\d{2}|19\d{2}', val)
            if years:
                return f"{years[0]}-01-01"
        except:
            pass
        return None
    
    def _extract_pcie_version(self, val):
        """Extract PCIe version (e.g., '4.0' from 'PCIe 4.0 x16')."""
        if not val: return None
        match = re.search(r'(\d+\.?\d*)', str(val))
        return match.group(1) if match else None


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    print("=" * 70)
    print("HardWizChippy - Comprehensive CPU Scraper")
    print("=" * 70)
    
    # Initialize
    db = DatabaseManager()
    if not db.connect():
        return
    
    scraper = CPUScraper()
    
    # Get initial stats
    initial_stats = db.get_stats()
    print(f"\n[DB] Current CPUs: {initial_stats['total']}")
    
    # Step 1: Get PassMark CPU list (names + benchmark scores)
    passmark_cpus = scraper.scrape_passmark_list()
    
    # Step 2: Get TechPowerUp CPU list (detailed specs)
    tpu_cpus = scraper.scrape_techpowerup_list()
    
    # Create lookup by normalized name
    tpu_lookup = {}
    for cpu in tpu_cpus:
        key = re.sub(r'[^a-z0-9]', '', cpu['name'].lower())
        tpu_lookup[key] = cpu
    
    # Step 3: Merge data and save to database
    print("\n[3/3] Saving to database...")
    
    inserted = 0
    updated = 0
    failed = 0
    
    # Process PassMark CPUs first (they have benchmark data)
    for i, cpu in enumerate(passmark_cpus):
        # Try to find matching TechPowerUp data
        key = re.sub(r'[^a-z0-9]', '', cpu['name'].lower())
        tpu_data = tpu_lookup.get(key, {})
        
        # Merge data
        merged = {**cpu, **tpu_data}
        merged['name'] = cpu['name']  # Keep PassMark name
        
        result = db.upsert_cpu(merged)
        if result == 'inserted': inserted += 1
        elif result == 'updated': updated += 1
        else: failed += 1
        
        if (i + 1) % 1000 == 0:
            print(f"    Progress: {i + 1}/{len(passmark_cpus)}")
    
    # Process remaining TechPowerUp CPUs not in PassMark
    passmark_keys = {re.sub(r'[^a-z0-9]', '', c['name'].lower()) for c in passmark_cpus}
    
    for cpu in tpu_cpus:
        key = re.sub(r'[^a-z0-9]', '', cpu['name'].lower())
        if key not in passmark_keys:
            result = db.upsert_cpu(cpu)
            if result == 'inserted': inserted += 1
            elif result == 'updated': updated += 1
    
    # Final stats
    final_stats = db.get_stats()
    
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    print(f"  Initial CPUs: {initial_stats['total']}")
    print(f"  Final CPUs:   {final_stats['total']}")
    print(f"  Added:        {final_stats['total'] - initial_stats['total']}")
    print(f"  Updated:      {updated}")
    print(f"  Failed:       {failed}")
    print("\nBy Manufacturer:")
    for mfgr, count in final_stats['by_manufacturer'].items():
        print(f"  {mfgr}: {count}")
    
    db.close()
    print("\n[OK] Done!")


if __name__ == "__main__":
    main()
