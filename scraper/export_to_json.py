"""
=============================================================================
HardWizChippy - JSON Exporter Utility
=============================================================================
Standalone script to export MySQL database to cpu_database.json for Flutter.

Usage:
    python export_to_json.py                    # Default export
    python export_to_json.py --output custom.json
    python export_to_json.py --modern-only     # Only 2020+ CPUs
    python export_to_json.py --minify          # Minified JSON

Author: KBitWare Project
Date: January 2026
=============================================================================
"""

import json
import argparse
import logging
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List

import mysql.connector
from mysql.connector import Error as MySQLError

# =============================================================================
# CONFIGURATION
# =============================================================================

DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'kbitboy',
    'password': 'danieyl',
    'database': 'hardwizchippy',
    'charset': 'utf8mb4'
}

DEFAULT_OUTPUT = '../assets/data/cpu_database.json'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s'
)
logger = logging.getLogger('JsonExporter')

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def json_serializer(obj: Any) -> Any:
    """Custom JSON serializer for non-standard types."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, bytes):
        return obj.decode('utf-8')
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def clean_dict(d: Dict) -> Dict:
    """Remove None values and clean up dict for JSON export."""
    cleaned = {}
    for key, value in d.items():
        if value is None:
            continue
        if isinstance(value, dict):
            value = clean_dict(value)
            if not value:
                continue
        if isinstance(value, list):
            value = [clean_dict(v) if isinstance(v, dict) else v for v in value]
            value = [v for v in value if v]
            if not value:
                continue
        cleaned[key] = value
    return cleaned


# =============================================================================
# EXPORTER CLASS
# =============================================================================

class CpuDatabaseExporter:
    """Export CPU database to JSON for Flutter integration."""
    
    def __init__(self, config: Dict = None):
        self.config = config or DB_CONFIG
        self.conn = None
        self.cursor = None
        
    def connect(self) -> bool:
        """Establish database connection."""
        try:
            self.conn = mysql.connector.connect(**self.config)
            self.cursor = self.conn.cursor(dictionary=True)
            logger.info("✅ Connected to database")
            return True
        except MySQLError as e:
            logger.error(f"❌ Database connection failed: {e}")
            return False
    
    def close(self):
        """Close database connection."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
    
    def get_cpus(self, modern_only: bool = False) -> List[Dict]:
        """Fetch all CPUs with full data."""
        
        # Main CPU query
        cpu_query = """
            SELECT 
                c.id,
                c.name,
                c.name_normalized,
                
                -- Main View / Nerd Specs
                c.max_frequency_ghz as max_frequency,
                c.total_cache_mb as total_cache,
                c.transistors_million,
                c.die_size_mm2,
                c.is_mcm,
                c.mcm_chiplet_count,
                c.mcm_config,
                c.voltage_range,
                
                -- General Info
                c.launch_date,
                c.launch_quarter,
                c.launch_msrp,
                c.current_price,
                c.status,
                c.product_code,
                
                -- Core Info
                c.microarchitecture,
                c.codename,
                c.generation,
                c.market_segment,
                c.cores_total as cores,
                c.threads_total as threads,
                c.p_cores,
                c.e_cores,
                c.base_clock_ghz as base_clock,
                c.boost_clock_ghz as boost_clock,
                c.p_core_base_ghz as p_core_base_clock,
                c.p_core_boost_ghz as p_core_boost_clock,
                c.e_core_base_ghz as e_core_base_clock,
                c.e_core_boost_ghz as e_core_boost_clock,
                c.is_unlocked as unlocked_multiplier,
                
                -- Cache
                c.l1_cache_kb as l1_cache,
                c.l2_cache_kb as l2_cache,
                c.l3_cache_mb as l3_cache,
                
                -- Memory
                c.memory_type,
                c.memory_channels,
                c.max_memory_gb,
                c.max_memory_bandwidth_gbs as memory_bandwidth,
                c.ecc_support as ecc_supported,
                
                -- Graphics
                c.has_igpu as has_integrated_gpu,
                c.igpu_name as integrated_gpu_name,
                c.igpu_base_mhz as graphics_base_freq,
                c.igpu_boost_mhz as graphics_turbo_freq,
                
                -- PCIe
                c.pcie_version,
                c.pcie_lanes_total as pcie_lanes,
                c.pcie_config,
                
                -- Power
                c.tdp_watts as tdp,
                c.base_power_watts as base_power,
                c.max_power_watts as max_turbo_power,
                
                -- Process
                c.process_node,
                c.foundry as fab_processor,
                
                -- URLs
                c.techpowerup_url,
                c.nanoreview_url,
                c.intel_ark_url,
                c.image_url,
                
                -- Status
                c.is_released,
                c.is_discontinued,
                
                -- Manufacturer info (joined)
                m.name as manufacturer_name,
                m.logo_url as manufacturer_logo,
                
                -- Socket info (joined)
                s.name as socket_name,
                s.release_year as socket_release_year,
                
                -- Family info (joined)
                f.name as family_name,
                f.codename as family_codename
                
            FROM cpus c
            LEFT JOIN manufacturers m ON c.manufacturer_id = m.id
            LEFT JOIN sockets s ON c.socket_id = s.id
            LEFT JOIN cpu_families f ON c.family_id = f.id
        """
        
        if modern_only:
            cpu_query += " WHERE c.launch_date >= '2020-01-01' OR c.launch_date IS NULL"
        
        cpu_query += " ORDER BY c.id"
        
        self.cursor.execute(cpu_query)
        cpus = self.cursor.fetchall()
        
        # Fetch benchmarks
        self.cursor.execute("""
            SELECT 
                cpu_id,
                cinebench_r23_single,
                cinebench_r23_multi,
                cinebench_r24_single,
                cinebench_r24_multi,
                geekbench6_single,
                geekbench6_multi,
                passmark_single,
                passmark_multi,
                _3dmark_timespy_cpu as timespy_cpu,
                handbrake_h264_1080p_sec as handbrake_h264,
                handbrake_h265_4k_sec as handbrake_h265,
                blender_classroom_sec as blender_classroom,
                _7zip_compress_mips as zip_compress,
                _7zip_decompress_mips as zip_decompress
            FROM cpu_benchmarks
        """)
        benchmarks_map = {row['cpu_id']: row for row in self.cursor.fetchall()}
        
        # Fetch gaming data
        self.cursor.execute("""
            SELECT 
                cpu_id,
                test_resolution,
                test_gpu,
                avg_fps,
                fps_1_percent,
                fps_01_percent,
                gaming_score
            FROM cpu_gaming_aggregate
        """)
        gaming_map = {}
        for row in self.cursor.fetchall():
            cpu_id = row['cpu_id']
            if cpu_id not in gaming_map:
                gaming_map[cpu_id] = []
            gaming_map[cpu_id].append(row)
        
        # Merge data
        result = []
        for cpu in cpus:
            cpu_id = cpu['id']
            
            # Add benchmarks
            if cpu_id in benchmarks_map:
                bench = benchmarks_map[cpu_id]
                cpu['structured_benchmarks'] = {
                    'cinebench_r23': {
                        'single': bench.get('cinebench_r23_single'),
                        'multi': bench.get('cinebench_r23_multi')
                    },
                    'cinebench_r24': {
                        'single': bench.get('cinebench_r24_single'),
                        'multi': bench.get('cinebench_r24_multi')
                    },
                    'geekbench6': {
                        'single': bench.get('geekbench6_single'),
                        'multi': bench.get('geekbench6_multi')
                    },
                    'passmark': {
                        'single': bench.get('passmark_single'),
                        'multi': bench.get('passmark_multi')
                    },
                    '3dmark': {
                        'timespy_cpu': bench.get('timespy_cpu')
                    },
                    'content_creation': {
                        'handbrake_h264': bench.get('handbrake_h264'),
                        'handbrake_h265': bench.get('handbrake_h265'),
                        'blender_classroom': bench.get('blender_classroom')
                    },
                    'productivity': {
                        'zip_compress': bench.get('zip_compress'),
                        'zip_decompress': bench.get('zip_decompress')
                    }
                }
            
            # Add gaming
            if cpu_id in gaming_map:
                cpu['gaming_benchmarks'] = []
                for g in gaming_map[cpu_id]:
                    cpu['gaming_benchmarks'].append({
                        'resolution': g.get('test_resolution'),
                        'gpu_used': g.get('test_gpu'),
                        'avg_fps': g.get('avg_fps'),
                        'fps_1_percent': g.get('fps_1_percent'),
                        'fps_01_percent': g.get('fps_01_percent'),
                        'gaming_score': g.get('gaming_score')
                    })
            
            # Clean up internal fields
            del cpu['cpu_id'] if 'cpu_id' in cpu else None
            
            result.append(clean_dict(cpu))
        
        return result
    
    def get_stats(self) -> Dict:
        """Get database statistics."""
        stats = {}
        
        self.cursor.execute("SELECT COUNT(*) as cnt FROM cpus")
        stats['total_cpus'] = self.cursor.fetchone()['cnt']
        
        self.cursor.execute("SELECT COUNT(*) as cnt FROM cpus WHERE launch_date >= '2020-01-01'")
        stats['modern_cpus'] = self.cursor.fetchone()['cnt']
        
        self.cursor.execute("SELECT COUNT(*) as cnt FROM cpus WHERE transistors_million IS NOT NULL")
        stats['with_transistors'] = self.cursor.fetchone()['cnt']
        
        self.cursor.execute("SELECT COUNT(*) as cnt FROM cpus WHERE die_size_mm2 IS NOT NULL")
        stats['with_die_size'] = self.cursor.fetchone()['cnt']
        
        self.cursor.execute("SELECT COUNT(*) as cnt FROM cpu_benchmarks WHERE cinebench_r23_multi IS NOT NULL")
        stats['with_benchmarks'] = self.cursor.fetchone()['cnt']
        
        self.cursor.execute("SELECT COUNT(*) as cnt FROM cpu_gaming_aggregate")
        stats['with_gaming'] = self.cursor.fetchone()['cnt']
        
        return stats
    
    def export(self, output_path: str, modern_only: bool = False, minify: bool = False) -> bool:
        """Export database to JSON file."""
        
        logger.info(f"📤 Exporting to {output_path}...")
        
        try:
            cpus = self.get_cpus(modern_only=modern_only)
            stats = self.get_stats()
            
            output = {
                'schema_version': '5.0',
                'pipeline': 'triple_threat_merge',
                'generated_at': datetime.now().isoformat(),
                'stats': stats,
                'cpus': cpus
            }
            
            # Ensure output directory exists
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Write JSON
            indent = None if minify else 2
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output, f, indent=indent, ensure_ascii=False, default=json_serializer)
            
            # Get file size
            size_kb = output_file.stat().st_size / 1024
            size_mb = size_kb / 1024
            
            logger.info(f"✅ Export complete!")
            logger.info(f"   📊 CPUs exported: {len(cpus)}")
            logger.info(f"   📁 File size: {size_mb:.2f} MB ({size_kb:.0f} KB)")
            logger.info(f"   📍 Location: {output_file.absolute()}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Export failed: {e}")
            return False


# =============================================================================
# CLI ENTRY POINT
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description='Export HardWizChippy database to JSON')
    parser.add_argument('--output', '-o', default=DEFAULT_OUTPUT, help='Output JSON file path')
    parser.add_argument('--modern-only', action='store_true', help='Export only 2020+ CPUs')
    parser.add_argument('--minify', action='store_true', help='Minify JSON output')
    parser.add_argument('--stats', action='store_true', help='Show stats only, no export')
    
    args = parser.parse_args()
    
    exporter = CpuDatabaseExporter()
    
    if not exporter.connect():
        return 1
    
    try:
        if args.stats:
            stats = exporter.get_stats()
            print("\n📊 Database Statistics:")
            print("-" * 30)
            for key, value in stats.items():
                print(f"  {key}: {value}")
            return 0
        
        success = exporter.export(
            output_path=args.output,
            modern_only=args.modern_only,
            minify=args.minify
        )
        
        return 0 if success else 1
        
    finally:
        exporter.close()


if __name__ == '__main__':
    exit(main())
