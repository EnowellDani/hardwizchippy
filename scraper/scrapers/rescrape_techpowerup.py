"""
TechPowerUp CPU Rescraper - Uses improved scraper with full field extraction
By KBitWare

This script re-scrapes CPU specifications from TechPowerUp using the improved
scraper that extracts ALL fields (threads, L1/L2 cache, memory, PCIe, etc.)
"""

import mysql.connector
import json
import time
from datetime import datetime
from tqdm import tqdm
import logging
from scrapers.techpowerup import TechPowerUpScraper

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'kbitboy',
    'password': 'danieyl',
    'database': 'hardwizchippy'
}

# Rate limiting
REQUEST_DELAY = 0.3  # seconds between requests


def get_or_create_manufacturer(cursor, name):
    """Get manufacturer ID, creating if necessary"""
    # Detect manufacturer from CPU name
    name_lower = name.lower() if name else ""
    if "amd" in name_lower or "ryzen" in name_lower or "athlon" in name_lower or "epyc" in name_lower:
        mfr_name = "AMD"
    elif "intel" in name_lower or "core" in name_lower or "xeon" in name_lower or "pentium" in name_lower or "celeron" in name_lower:
        mfr_name = "INTEL"
    else:
        mfr_name = "OTHER"

    cursor.execute("SELECT id FROM manufacturers WHERE name = %s", (mfr_name,))
    result = cursor.fetchone()
    if result:
        return result[0]

    cursor.execute("INSERT INTO manufacturers (name) VALUES (%s)", (mfr_name,))
    return cursor.lastrowid


def get_or_create_socket(cursor, name, manufacturer_id):
    """Get socket ID, creating if necessary"""
    if not name:
        return None
    cursor.execute("SELECT id FROM sockets WHERE name = %s", (name,))
    result = cursor.fetchone()
    if result:
        return result[0]

    cursor.execute(
        "INSERT INTO sockets (name, manufacturer_id) VALUES (%s, %s)",
        (name, manufacturer_id)
    )
    return cursor.lastrowid


def parse_date(text):
    """Parse release date to YYYY-MM-DD format"""
    if not text:
        return None
    try:
        # Try various date formats
        for fmt in ['%b %dth, %Y', '%b %dst, %Y', '%b %dnd, %Y', '%b %drd, %Y',
                    '%B %d, %Y', '%b %d, %Y', '%Y-%m-%d', '%B %Y', '%Y']:
            try:
                # Remove ordinal suffixes
                clean_text = text.replace('st,', ',').replace('nd,', ',').replace('rd,', ',').replace('th,', ',')
                dt = datetime.strptime(clean_text.strip(), fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue
    except:
        pass
    return None


def insert_cpu(cursor, cpu_data, manufacturer_id, socket_id):
    """Insert or update a CPU in the database"""
    sql = """
    INSERT INTO cpus (
        name, manufacturer_id, socket_id, codename, generation,
        cores, threads, base_clock, boost_clock,
        l1_cache, l2_cache, l3_cache, tdp,
        process_node, transistors_million, die_size_mm2,
        memory_type, memory_channels, max_memory_gb,
        has_integrated_gpu, integrated_gpu_name,
        pcie_version, pcie_lanes,
        launch_date, launch_msrp, techpowerup_url
    ) VALUES (
        %s, %s, %s, %s, %s,
        %s, %s, %s, %s,
        %s, %s, %s, %s,
        %s, %s, %s,
        %s, %s, %s,
        %s, %s,
        %s, %s,
        %s, %s, %s
    ) ON DUPLICATE KEY UPDATE
        codename = VALUES(codename),
        generation = VALUES(generation),
        cores = VALUES(cores),
        threads = VALUES(threads),
        base_clock = VALUES(base_clock),
        boost_clock = VALUES(boost_clock),
        l1_cache = VALUES(l1_cache),
        l2_cache = VALUES(l2_cache),
        l3_cache = VALUES(l3_cache),
        tdp = VALUES(tdp),
        process_node = VALUES(process_node),
        transistors_million = VALUES(transistors_million),
        die_size_mm2 = VALUES(die_size_mm2),
        memory_type = VALUES(memory_type),
        memory_channels = VALUES(memory_channels),
        max_memory_gb = VALUES(max_memory_gb),
        has_integrated_gpu = VALUES(has_integrated_gpu),
        integrated_gpu_name = VALUES(integrated_gpu_name),
        pcie_version = VALUES(pcie_version),
        pcie_lanes = VALUES(pcie_lanes),
        launch_msrp = VALUES(launch_msrp),
        updated_at = CURRENT_TIMESTAMP
    """

    launch_date = parse_date(cpu_data.get('launch_date_raw'))

    values = (
        cpu_data.get('name'),
        manufacturer_id,
        socket_id,
        cpu_data.get('codename'),
        cpu_data.get('microarchitecture'),  # generation field
        cpu_data.get('cores'),
        cpu_data.get('threads'),
        cpu_data.get('base_clock'),
        cpu_data.get('boost_clock'),
        cpu_data.get('l1_cache'),
        cpu_data.get('l2_cache'),
        cpu_data.get('l3_cache'),
        cpu_data.get('tdp'),
        cpu_data.get('process_node'),
        cpu_data.get('transistors_million'),
        cpu_data.get('die_size_mm2'),
        cpu_data.get('memory_type'),
        cpu_data.get('memory_channels'),
        cpu_data.get('max_memory_gb'),
        cpu_data.get('has_integrated_gpu', False),
        cpu_data.get('integrated_gpu_name'),
        cpu_data.get('pcie_version'),
        cpu_data.get('pcie_lanes'),
        launch_date,
        cpu_data.get('launch_msrp'),
        cpu_data.get('techpowerup_url')
    )

    cursor.execute(sql, values)


def export_to_json(output_file='../assets/cpu_database.json'):
    """Export database to JSON for Flutter offline use"""
    print(f"\nExporting to {output_file}...")

    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            c.*,
            m.name as manufacturer_name,
            s.name as socket_name
        FROM cpus c
        LEFT JOIN manufacturers m ON c.manufacturer_id = m.id
        LEFT JOIN sockets s ON c.socket_id = s.id
        ORDER BY c.name
    """)

    cpus = cursor.fetchall()

    # Convert datetime objects to strings and clean up data
    for cpu in cpus:
        for key, value in cpu.items():
            if isinstance(value, datetime):
                cpu[key] = value.strftime('%Y-%m-%d')
            elif value is None:
                cpu[key] = None

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({'cpus': cpus, 'total': len(cpus)}, f, indent=2, default=str)

    cursor.close()
    conn.close()

    print(f"Exported {len(cpus)} CPUs to {output_file}")


def main():
    print("=" * 60)
    print("TechPowerUp CPU Re-Scraper (Improved)")
    print("Extracts ALL CPU specifications")
    print("=" * 60)

    # Connect to database
    print("\nConnecting to MySQL database...")
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        print("Connected successfully!")
    except Exception as e:
        print(f"Database connection failed: {e}")
        print("\nMake sure:")
        print("1. Laragon is running with MySQL")
        print("2. The database 'hardwizchippy' exists")
        return

    # Initialize scraper with Playwright
    print("\nInitializing TechPowerUp scraper with Playwright...")
    scraper = TechPowerUpScraper(use_playwright=True)

    # Get all CPU links
    print("Fetching CPU list...")
    cpu_links = list(scraper.scrape_list())
    print(f"Found {len(cpu_links)} CPUs")

    if not cpu_links:
        print("No CPUs found. Check your internet connection.")
        return

    # Limit for testing (uncomment for testing):
    # cpu_links = cpu_links[:20]

    print(f"\nScraping {len(cpu_links)} CPUs with full field extraction...")
    print("This will take a while. Be patient!\n")

    success_count = 0
    error_count = 0

    for cpu_info in tqdm(cpu_links, desc="Scraping CPUs"):
        try:
            url = cpu_info.get('url')
            if not url:
                continue

            # Scrape detailed specs using improved scraper
            cpu_data = scraper.scrape_detail(url)

            if cpu_data and cpu_data.get('name'):
                # Get/create manufacturer
                manufacturer_id = get_or_create_manufacturer(
                    cursor,
                    cpu_data.get('name')
                )

                # Get/create socket
                socket_id = get_or_create_socket(
                    cursor,
                    cpu_data.get('socket_name'),
                    manufacturer_id
                )

                # Insert CPU
                insert_cpu(cursor, cpu_data, manufacturer_id, socket_id)
                conn.commit()
                success_count += 1
            else:
                error_count += 1

        except Exception as e:
            error_count += 1
            logger.debug(f"Error processing {cpu_info.get('name')}: {e}")

        # Rate limiting
        time.sleep(REQUEST_DELAY)

    # Cleanup
    scraper._close_playwright()
    cursor.close()
    conn.close()

    print(f"\n{'=' * 60}")
    print(f"Scraping complete!")
    print(f"Successfully scraped: {success_count} CPUs")
    print(f"Errors: {error_count}")
    print(f"{'=' * 60}")

    # Export to JSON
    export_to_json()

    print("\nDone! Your database is now populated with complete specs.")


if __name__ == '__main__':
    main()
