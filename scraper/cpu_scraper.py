"""
HardWizChippy - Comprehensive CPU Data Scraper
===============================================
Collects complete CPU specifications from multiple sources.

Sources:
- TechPowerUp: Detailed specs (cores, cache, frequencies, die info)
- PassMark: CPU benchmark scores
- CPU-Monkey: Cinebench, Geekbench scores

Run: python cpu_scraper.py
     python cpu_scraper.py --details    # Fetch detailed specs
     python cpu_scraper.py --stats      # Show stats only
"""

import requests
from bs4 import BeautifulSoup
import mysql.connector
import json
import re
import time
from datetime import datetime
from urllib.parse import urljoin, quote
from typing import Dict, List, Optional, Any

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
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Connection': 'keep-alive',
}


# =============================================================================
# DATABASE MANAGER
# =============================================================================

class Database:
    """Handles all database operations."""
    
    def __init__(self):
        self.conn = None
        self.cursor = None
        self._manufacturers = {}
        self._sockets = {}
    
    def connect(self) -> bool:
        try:
            self.conn = mysql.connector.connect(**DB_CONFIG)
            self.cursor = self.conn.cursor(dictionary=True)
            self._load_lookups()
            print("[DB] Connected to database")
            return True
        except Exception as e:
            print(f"[DB] Connection failed: {e}")
            return False
    
    def _load_lookups(self):
        """Cache manufacturer and socket IDs."""
        self.cursor.execute("SELECT id, name FROM manufacturers")
        for row in self.cursor.fetchall():
            self._manufacturers[row['name'].lower()] = row['id']
        
        self.cursor.execute("SELECT id, name FROM sockets")
        for row in self.cursor.fetchall():
            self._sockets[row['name'].lower()] = row['id']
    
    def close(self):
        if self.cursor: self.cursor.close()
        if self.conn: self.conn.close()
    
    def get_manufacturer_id(self, name: str) -> Optional[int]:
        if not name: return None
        key = name.lower()
        
        if key in self._manufacturers:
            return self._manufacturers[key]
        
        try:
            self.cursor.execute("INSERT INTO manufacturers (name) VALUES (%s)", (name,))
            self.conn.commit()
            mid = self.cursor.lastrowid
            self._manufacturers[key] = mid
            return mid
        except:
            return None
    
    def get_socket_id(self, name: str, mfgr_id: int) -> Optional[int]:
        if not name: return None
        key = name.lower()
        
        if key in self._sockets:
            return self._sockets[key]
        
        try:
            self.cursor.execute(
                "INSERT INTO sockets (name, manufacturer_id) VALUES (%s, %s)",
                (name, mfgr_id)
            )
            self.conn.commit()
            sid = self.cursor.lastrowid
            self._sockets[key] = sid
            return sid
        except:
            return None
    
    def save_cpu(self, cpu: Dict) -> str:
        """Insert or update a CPU. Returns 'inserted', 'updated', or 'failed'."""
        try:
            name = cpu.get('name', '').strip()[:150]
            if not name:
                return 'failed'
            
            mfgr_id = self.get_manufacturer_id(cpu.get('manufacturer', 'Other'))
            socket_id = self.get_socket_id(cpu.get('socket'), mfgr_id)
            
            # Check if exists
            self.cursor.execute("SELECT id FROM cpus WHERE name = %s", (name,))
            existing = self.cursor.fetchone()
            
            if existing:
                self._update_cpu(existing['id'], cpu, socket_id)
                return 'updated'
            else:
                self._insert_cpu(name, mfgr_id, socket_id, cpu)
                return 'inserted'
                
        except Exception as e:
            self.conn.rollback()
            return 'failed'
    
    def _insert_cpu(self, name: str, mfgr_id: int, socket_id: int, cpu: Dict):
        """Insert new CPU record."""
        self.cursor.execute("""
            INSERT INTO cpus (
                name, manufacturer_id, socket_id,
                max_frequency, total_cache,
                launch_date, launch_msrp, current_price,
                process_node, fab_details, transistors_million, die_size_mm2, cpu_package_size,
                tdp, base_power, max_turbo_power,
                is_mcm, mcm_chiplet_count, mcm_config,
                microarchitecture, codename, core_stepping, generation,
                cores, threads, p_cores, e_cores,
                base_clock, boost_clock,
                p_core_base_clock, p_core_boost_clock,
                e_core_base_clock, e_core_boost_clock,
                l1_cache_instruction, l1_cache_data, l1_cache, l2_cache, l2_cache_total, l3_cache,
                base_multiplier, turbo_multiplier, unlocked_multiplier,
                data_width, scalability, bus_type, bus_frequency, instruction_set, features,
                memory_type, memory_bandwidth, memory_channels, max_memory_gb, ecc_support,
                has_integrated_gpu, integrated_gpu_name, gpu_base_frequency, gpu_boost_frequency,
                gpu_execution_units, gpu_shaders, gpu_fp32_tflops,
                pcie_version, pcie_lanes, pcie_config,
                techpowerup_url,
                created_at, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, NOW(), NOW()
            )
        """, (
            name, mfgr_id, socket_id,
            cpu.get('max_frequency'), cpu.get('total_cache'),
            cpu.get('launch_date'), cpu.get('launch_msrp'), cpu.get('current_price'),
            cpu.get('process_node'), cpu.get('fab_details'), cpu.get('transistors_million'),
            cpu.get('die_size_mm2'), cpu.get('cpu_package_size'),
            cpu.get('tdp'), cpu.get('base_power'), cpu.get('max_turbo_power'),
            cpu.get('is_mcm', False), cpu.get('mcm_chiplet_count'), cpu.get('mcm_config'),
            cpu.get('microarchitecture'), cpu.get('codename'), cpu.get('core_stepping'),
            cpu.get('generation'),
            cpu.get('cores'), cpu.get('threads'), cpu.get('p_cores'), cpu.get('e_cores'),
            cpu.get('base_clock'), cpu.get('boost_clock'),
            cpu.get('p_core_base_clock'), cpu.get('p_core_boost_clock'),
            cpu.get('e_core_base_clock'), cpu.get('e_core_boost_clock'),
            cpu.get('l1_cache_instruction'), cpu.get('l1_cache_data'), cpu.get('l1_cache'),
            cpu.get('l2_cache'), cpu.get('l2_cache_total'), cpu.get('l3_cache'),
            cpu.get('base_multiplier'), cpu.get('turbo_multiplier'), cpu.get('unlocked_multiplier'),
            cpu.get('data_width'), cpu.get('scalability'), cpu.get('bus_type'),
            cpu.get('bus_frequency'), cpu.get('instruction_set'), cpu.get('features'),
            cpu.get('memory_type'), cpu.get('memory_bandwidth'), cpu.get('memory_channels'),
            cpu.get('max_memory_gb'), cpu.get('ecc_support'),
            cpu.get('has_integrated_gpu', False), cpu.get('integrated_gpu_name'),
            cpu.get('gpu_base_frequency'), cpu.get('gpu_boost_frequency'),
            cpu.get('gpu_execution_units'), cpu.get('gpu_shaders'), cpu.get('gpu_fp32_tflops'),
            cpu.get('pcie_version'), cpu.get('pcie_lanes'), cpu.get('pcie_config'),
            cpu.get('url')
        ))
        self.conn.commit()
    
    def _update_cpu(self, cpu_id: int, cpu: Dict, socket_id: int):
        """Update existing CPU with non-null values."""
        fields = []
        values = []
        
        update_map = {
            'socket_id': socket_id,
            'max_frequency': cpu.get('max_frequency'),
            'total_cache': cpu.get('total_cache'),
            'process_node': cpu.get('process_node'),
            'fab_details': cpu.get('fab_details'),
            'transistors_million': cpu.get('transistors_million'),
            'die_size_mm2': cpu.get('die_size_mm2'),
            'tdp': cpu.get('tdp'),
            'microarchitecture': cpu.get('microarchitecture'),
            'codename': cpu.get('codename'),
            'cores': cpu.get('cores'),
            'threads': cpu.get('threads'),
            'base_clock': cpu.get('base_clock'),
            'boost_clock': cpu.get('boost_clock'),
            'l1_cache': cpu.get('l1_cache'),
            'l2_cache': cpu.get('l2_cache'),
            'l3_cache': cpu.get('l3_cache'),
            'memory_type': cpu.get('memory_type'),
            'pcie_version': cpu.get('pcie_version'),
            'pcie_lanes': cpu.get('pcie_lanes'),
            'techpowerup_url': cpu.get('url'),
        }
        
        for field, value in update_map.items():
            if value is not None:
                fields.append(f"{field} = COALESCE(%s, {field})")
                values.append(value)
        
        if fields:
            fields.append("updated_at = NOW()")
            values.append(cpu_id)
            
            query = f"UPDATE cpus SET {', '.join(fields)} WHERE id = %s"
            self.cursor.execute(query, values)
            self.conn.commit()
    
    def save_benchmarks(self, cpu_name: str, benchmarks: Dict):
        """Save benchmark scores for a CPU."""
        self.cursor.execute("SELECT id FROM cpus WHERE name = %s", (cpu_name,))
        result = self.cursor.fetchone()
        if not result:
            return
        
        cpu_id = result['id']
        
        # Check if benchmark record exists
        self.cursor.execute("SELECT id FROM cpu_benchmarks WHERE cpu_id = %s", (cpu_id,))
        existing = self.cursor.fetchone()
        
        if existing:
            self.cursor.execute("""
                UPDATE cpu_benchmarks SET
                    cinebench_r23_single = COALESCE(%s, cinebench_r23_single),
                    cinebench_r23_multi = COALESCE(%s, cinebench_r23_multi),
                    cinebench_r24_single = COALESCE(%s, cinebench_r24_single),
                    cinebench_r24_multi = COALESCE(%s, cinebench_r24_multi),
                    geekbench6_single = COALESCE(%s, geekbench6_single),
                    geekbench6_multi = COALESCE(%s, geekbench6_multi),
                    passmark_single = COALESCE(%s, passmark_single),
                    passmark_multi = COALESCE(%s, passmark_multi),
                    updated_at = NOW()
                WHERE cpu_id = %s
            """, (
                benchmarks.get('cinebench_r23_single'),
                benchmarks.get('cinebench_r23_multi'),
                benchmarks.get('cinebench_r24_single'),
                benchmarks.get('cinebench_r24_multi'),
                benchmarks.get('geekbench6_single'),
                benchmarks.get('geekbench6_multi'),
                benchmarks.get('passmark_single'),
                benchmarks.get('passmark_multi'),
                cpu_id
            ))
        else:
            self.cursor.execute("""
                INSERT INTO cpu_benchmarks (
                    cpu_id, cinebench_r23_single, cinebench_r23_multi,
                    cinebench_r24_single, cinebench_r24_multi,
                    geekbench6_single, geekbench6_multi,
                    passmark_single, passmark_multi,
                    created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            """, (
                cpu_id,
                benchmarks.get('cinebench_r23_single'),
                benchmarks.get('cinebench_r23_multi'),
                benchmarks.get('cinebench_r24_single'),
                benchmarks.get('cinebench_r24_multi'),
                benchmarks.get('geekbench6_single'),
                benchmarks.get('geekbench6_multi'),
                benchmarks.get('passmark_single'),
                benchmarks.get('passmark_multi')
            ))
        
        self.conn.commit()
    
    def save_gaming_benchmark(self, cpu_name: str, game_data: Dict):
        """Save gaming performance for a CPU."""
        self.cursor.execute("SELECT id FROM cpus WHERE name = %s", (cpu_name,))
        result = self.cursor.fetchone()
        if not result:
            return
        
        cpu_id = result['id']
        
        self.cursor.execute("""
            INSERT INTO cpu_gaming_performance (
                cpu_id, game_name, resolution, graphics_preset, gpu_used,
                avg_fps, fps_1_percent, fps_01_percent, min_fps, max_fps,
                source, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            ON DUPLICATE KEY UPDATE
                avg_fps = VALUES(avg_fps),
                fps_1_percent = VALUES(fps_1_percent),
                fps_01_percent = VALUES(fps_01_percent)
        """, (
            cpu_id,
            game_data.get('game_name'),
            game_data.get('resolution', '1080p'),
            game_data.get('preset', 'Ultra'),
            game_data.get('gpu', 'RTX 4090'),
            game_data.get('avg_fps'),
            game_data.get('fps_1_percent'),
            game_data.get('fps_01_percent'),
            game_data.get('min_fps'),
            game_data.get('max_fps'),
            game_data.get('source')
        ))
        self.conn.commit()
    
    def get_stats(self) -> Dict:
        """Get database statistics."""
        stats = {}
        self.cursor.execute("SELECT COUNT(*) as c FROM cpus")
        stats['total_cpus'] = self.cursor.fetchone()['c']
        
        self.cursor.execute("""
            SELECT m.name, COUNT(*) as c 
            FROM cpus JOIN manufacturers m ON cpus.manufacturer_id = m.id 
            GROUP BY m.id ORDER BY c DESC
        """)
        stats['by_manufacturer'] = {r['name']: r['c'] for r in self.cursor.fetchall()}
        
        # Check if benchmark table exists
        try:
            self.cursor.execute("SELECT COUNT(*) as c FROM cpu_benchmarks")
            stats['benchmarks'] = self.cursor.fetchone()['c']
        except:
            stats['benchmarks'] = 0
        
        # Check if gaming table exists
        try:
            self.cursor.execute("SELECT COUNT(DISTINCT cpu_id) as c FROM cpu_gaming_performance")
            stats['gaming_data'] = self.cursor.fetchone()['c']
        except:
            stats['gaming_data'] = 0
        
        return stats


# =============================================================================
# DATA SCRAPERS
# =============================================================================

class TechPowerUpScraper:
    """Scrapes detailed CPU specs from TechPowerUp."""
    
    BASE_URL = "https://www.techpowerup.com"
    
    def __init__(self, session: requests.Session):
        self.session = session
    
    def get_cpu_list(self) -> List[Dict]:
        """Get list of all CPUs from TechPowerUp."""
        print("\n[TechPowerUp] Fetching CPU list...")
        
        all_cpus = {}
        manufacturers = ['AMD', 'Intel', 'VIA', 'Qualcomm', 'Apple', 'ARM']
        
        for mfgr in manufacturers:
            page = 1
            count = 0
            
            while page <= 100:
                url = f"{self.BASE_URL}/cpu-specs/?mfgr={mfgr}&sort=name&page={page}"
                
                try:
                    resp = self.session.get(url, timeout=30)
                    if resp.status_code != 200:
                        break
                    
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    table = soup.find('table', class_='processors')
                    
                    if not table:
                        break
                    
                    rows = table.find_all('tr')[1:]
                    if not rows:
                        break
                    
                    found_new = False
                    for row in rows:
                        cells = row.find_all('td')
                        if cells:
                            link = cells[0].find('a')
                            if link:
                                name = link.get_text().strip()
                                href = link.get('href')
                                
                                if href and href not in all_cpus:
                                    all_cpus[href] = {
                                        'name': name,
                                        'url': urljoin(self.BASE_URL, href),
                                        'manufacturer': mfgr
                                    }
                                    count += 1
                                    found_new = True
                    
                    if not found_new:
                        break
                    
                    page += 1
                    time.sleep(0.1)
                    
                except:
                    break
            
            if count > 0:
                print(f"    {mfgr}: {count}")
        
        print(f"  Total: {len(all_cpus)} CPUs")
        return list(all_cpus.values())
    
    def get_cpu_details(self, url: str) -> Optional[Dict]:
        """Scrape full details from a CPU page."""
        try:
            resp = self.session.get(url, timeout=30)
            if resp.status_code != 200:
                return None
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            raw = {}
            
            # Extract all spec rows
            for section in soup.find_all('section', class_='details'):
                for row in section.find_all('tr'):
                    cells = row.find_all(['th', 'td'])
                    if len(cells) == 2:
                        label = cells[0].get_text().strip().rstrip(':')
                        value = cells[1].get_text().strip()
                        if value and value not in ['-', 'N/A', 'Unknown', 'None']:
                            raw[label] = value
            
            return self._parse_specs(raw)
            
        except:
            return None
    
    def _parse_specs(self, raw: Dict) -> Dict:
        """Parse raw TechPowerUp specs into structured format."""
        
        # Parse cache values
        l1_total = self._parse_cache(raw.get('Cache L1'))
        l2_cache = self._parse_cache(raw.get('Cache L2'))
        l3_cache = self._parse_cache(raw.get('Cache L3'))
        
        # Parse frequencies
        base_freq = self._parse_frequency(raw.get('Frequency'))
        boost_freq = self._parse_frequency(raw.get('Turbo Clock'))
        
        # Determine if unlocked
        multiplier = raw.get('Multiplier', '')
        unlocked = 'unlocked' in multiplier.lower() or multiplier.endswith('x')
        
        return {
            # General
            'socket': raw.get('Socket'),
            'codename': raw.get('Codename'),
            'microarchitecture': raw.get('Architecture'),
            'process_node': raw.get('Process Size'),
            'fab_details': raw.get('Foundry'),
            
            # Core info
            'cores': self._parse_int(raw.get('# of Cores')),
            'threads': self._parse_int(raw.get('# of Threads')),
            'base_clock': base_freq,
            'boost_clock': boost_freq,
            'max_frequency': boost_freq or base_freq,
            
            # Cache
            'l1_cache': l1_total,
            'l2_cache': l2_cache,
            'l3_cache': l3_cache,
            'total_cache': (l1_total or 0) + (l2_cache or 0) + (l3_cache or 0),
            
            # Power
            'tdp': self._parse_int(raw.get('TDP')),
            
            # Manufacturing
            'transistors_million': self._parse_int(raw.get('Transistors')),
            'die_size_mm2': self._parse_float(raw.get('Die Size')),
            
            # MCM
            'is_mcm': 'chiplet' in str(raw).lower() or 'mcm' in str(raw).lower(),
            
            # Multiplier
            'base_multiplier': self._parse_float(multiplier.split('-')[0] if '-' in multiplier else multiplier),
            'turbo_multiplier': self._parse_float(multiplier.split('-')[1] if '-' in multiplier else None),
            'unlocked_multiplier': unlocked,
            
            # Memory
            'memory_type': raw.get('Memory Support'),
            'memory_channels': self._parse_int(raw.get('Memory Channels')),
            'max_memory_gb': self._parse_int(raw.get('Max Memory')),
            'ecc_support': 'ecc' in str(raw.get('Memory Support', '')).lower(),
            
            # PCIe
            'pcie_version': self._extract_pcie_version(raw.get('PCI-Express')),
            'pcie_lanes': self._parse_int(raw.get('PCI-Express')),
            'pcie_config': raw.get('PCI-Express'),
            
            # GPU
            'has_integrated_gpu': bool(raw.get('Integrated Graphics')),
            'integrated_gpu_name': raw.get('Integrated Graphics'),
            'gpu_base_frequency': self._parse_int(raw.get('GPU Base Clock')),
            'gpu_boost_frequency': self._parse_int(raw.get('GPU Boost Clock')),
            
            # Features
            'instruction_set': raw.get('Instruction Set'),
            'features': raw.get('Features'),
            
            # Release
            'launch_date': self._parse_date(raw.get('Release Date')),
            'launch_msrp': self._parse_price(raw.get('Launch Price')),
        }
    
    def _parse_int(self, val) -> Optional[int]:
        if not val: return None
        nums = re.findall(r'[\d,]+', str(val))
        return int(nums[0].replace(',', '')) if nums else None
    
    def _parse_float(self, val) -> Optional[float]:
        if not val: return None
        nums = re.findall(r'[\d.]+', str(val))
        return float(nums[0]) if nums else None
    
    def _parse_frequency(self, val) -> Optional[float]:
        """Parse frequency to GHz."""
        if not val: return None
        nums = re.findall(r'[\d.]+', str(val))
        if nums:
            num = float(nums[0])
            if 'MHz' in str(val):
                return round(num / 1000, 2)
            return round(num, 2)
        return None
    
    def _parse_cache(self, val) -> Optional[int]:
        """Parse cache to KB."""
        if not val: return None
        val = str(val).lower()
        nums = re.findall(r'[\d.]+', val)
        if nums:
            num = float(nums[0])
            if 'mb' in val:
                return int(num * 1024)
            if 'gb' in val:
                return int(num * 1024 * 1024)
            return int(num)
        return None
    
    def _parse_price(self, val) -> Optional[float]:
        if not val: return None
        nums = re.findall(r'[\d.]+', str(val).replace(',', ''))
        return float(nums[0]) if nums else None
    
    def _parse_date(self, val) -> Optional[str]:
        if not val: return None
        for fmt in ['%b %d, %Y', '%B %d, %Y', '%b %Y', '%B %Y', '%Y']:
            try:
                dt = datetime.strptime(val.strip(), fmt)
                return dt.strftime('%Y-%m-%d')
            except:
                continue
        years = re.findall(r'20\d{2}|19\d{2}', str(val))
        return f"{years[0]}-01-01" if years else None
    
    def _extract_pcie_version(self, val) -> Optional[str]:
        if not val: return None
        match = re.search(r'(\d+\.?\d*)', str(val))
        return match.group(1) if match else None


class PassMarkScraper:
    """Scrapes PassMark benchmark scores."""
    
    BASE_URL = "https://www.cpubenchmark.net"
    
    def __init__(self, session: requests.Session):
        self.session = session
    
    def get_all_scores(self) -> Dict[str, Dict]:
        """Get PassMark scores for all CPUs."""
        print("\n[PassMark] Fetching benchmark scores...")
        
        scores = {}
        url = f"{self.BASE_URL}/cpu_list.php"
        
        try:
            resp = self.session.get(url, timeout=60)
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            table = soup.find('table', id='cputable') or soup.find('table')
            if not table:
                return scores
            
            for row in table.find_all('tr')[1:]:
                cells = row.find_all('td')
                if len(cells) >= 2:
                    link = cells[0].find('a')
                    if link:
                        name = link.get_text().strip()
                        score_text = cells[1].get_text().strip()
                        score = int(re.sub(r'[^\d]', '', score_text)) if score_text else None
                        
                        if name and score:
                            scores[name.lower()] = {
                                'name': name,
                                'passmark_multi': score,
                                'manufacturer': self._detect_manufacturer(name)
                            }
            
            print(f"  Found {len(scores)} CPUs with scores")
            
        except Exception as e:
            print(f"  Error: {e}")
        
        return scores
    
    def _detect_manufacturer(self, name: str) -> str:
        name = name.lower()
        if any(x in name for x in ['intel', 'core i', 'xeon', 'pentium', 'celeron']):
            return 'Intel'
        elif any(x in name for x in ['amd', 'ryzen', 'epyc', 'athlon', 'threadripper']):
            return 'AMD'
        elif any(x in name for x in ['apple', ' m1', ' m2', ' m3', ' m4']):
            return 'Apple'
        return 'Other'


# =============================================================================
# MAIN SCRAPER ORCHESTRATOR
# =============================================================================

class CPUDataCollector:
    """Main orchestrator that coordinates all scrapers."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.db = Database()
        
        self.tpu = TechPowerUpScraper(self.session)
        self.passmark = PassMarkScraper(self.session)
    
    def run(self, fetch_details: bool = False, limit: int = None):
        """Run the complete data collection pipeline."""
        print("=" * 70)
        print("HardWizChippy - Comprehensive CPU Data Collector")
        print("=" * 70)
        
        if not self.db.connect():
            return
        
        # Show initial stats
        initial = self.db.get_stats()
        print(f"\n[DB] Current: {initial['total_cpus']} CPUs")
        
        # Step 1: Get PassMark scores
        passmark_data = self.passmark.get_all_scores()
        
        # Step 2: Get TechPowerUp CPU list
        tpu_list = self.tpu.get_cpu_list()
        
        if limit:
            tpu_list = tpu_list[:limit]
        
        # Step 3: Merge and save
        print("\n[Processing] Saving CPU data...")
        
        inserted = 0
        updated = 0
        
        for i, cpu in enumerate(tpu_list):
            # Merge with PassMark data
            pm_key = cpu['name'].lower()
            if pm_key in passmark_data:
                cpu['passmark_multi'] = passmark_data[pm_key].get('passmark_multi')
            
            # Get detailed specs if requested
            if fetch_details and cpu.get('url'):
                details = self.tpu.get_cpu_details(cpu['url'])
                if details:
                    cpu.update(details)
                time.sleep(0.1)
            
            result = self.db.save_cpu(cpu)
            if result == 'inserted':
                inserted += 1
            elif result == 'updated':
                updated += 1
            
            if (i + 1) % 500 == 0:
                print(f"    Progress: {i + 1}/{len(tpu_list)}")
        
        # Process remaining PassMark CPUs
        tpu_names = {c['name'].lower() for c in tpu_list}
        for name, data in passmark_data.items():
            if name not in tpu_names:
                result = self.db.save_cpu(data)
                if result == 'inserted':
                    inserted += 1
        
        # Final stats
        final = self.db.get_stats()
        
        print("\n" + "=" * 70)
        print("RESULTS")
        print("=" * 70)
        print(f"  CPUs: {initial['total_cpus']} -> {final['total_cpus']} (+{final['total_cpus'] - initial['total_cpus']})")
        print(f"  Inserted: {inserted}")
        print(f"  Updated: {updated}")
        print("\nBy Manufacturer:")
        for mfgr, count in final['by_manufacturer'].items():
            print(f"  {mfgr}: {count}")
        
        self.db.close()
        print("\n[OK] Done!")


# =============================================================================
# ENTRY POINT
# =============================================================================

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='HardWizChippy CPU Scraper')
    parser.add_argument('--details', '-d', action='store_true',
                        help='Fetch detailed specs for each CPU (slower)')
    parser.add_argument('--limit', '-l', type=int, default=None,
                        help='Limit number of CPUs to process')
    parser.add_argument('--stats', '-s', action='store_true',
                        help='Show database stats only')
    
    args = parser.parse_args()
    
    if args.stats:
        db = Database()
        if db.connect():
            stats = db.get_stats()
            print(f"\nTotal CPUs: {stats['total_cpus']}")
            print(f"Benchmarks: {stats['benchmarks']}")
            print(f"Gaming data: {stats['gaming_data']}")
            print("\nBy Manufacturer:")
            for m, c in stats['by_manufacturer'].items():
                print(f"  {m}: {c}")
            db.close()
        return
    
    collector = CPUDataCollector()
    collector.run(fetch_details=args.details, limit=args.limit)


if __name__ == "__main__":
    main()
