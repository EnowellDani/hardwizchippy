"""
TechPowerUp CPU Database Scraper for HardWizChippy
By KBitWare

This script scrapes CPU specifications from TechPowerUp and:
1. Inserts them into your MySQL database
2. Exports to JSON for offline Flutter app use

Usage:
    pip install -r requirements.txt
    python scrape_techpowerup.py
"""

import requests
from bs4 import BeautifulSoup
import mysql.connector
import json
import time
import re
from datetime import datetime
from tqdm import tqdm
import os

# Configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'kbitboy',
    'password': 'danieyl',
    'database': 'hardwizchippy'
}

BASE_URL = 'https://www.techpowerup.com'
CPU_LIST_URL = f'{BASE_URL}/cpu-specs/'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# Rate limiting - be respectful to the server
REQUEST_DELAY = 0.5  # seconds between requests


def get_soup(url):
    """Fetch a URL and return BeautifulSoup object"""
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        return BeautifulSoup(response.text, 'lxml')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None


def parse_clock_speed(text):
    """Convert clock speed text to MHz as integer"""
    if not text or text == 'N/A':
        return None
    text = text.strip()
    match = re.search(r'([\d.]+)\s*(GHz|MHz)', text, re.IGNORECASE)
    if match:
        value = float(match.group(1))
        unit = match.group(2).lower()
        if unit == 'ghz':
            return int(value * 1000)
        return int(value)
    return None


def parse_cache(text):
    """Convert cache text to KB as integer"""
    if not text or text == 'N/A':
        return None
    text = text.strip()
    # Handle "64 KB per core" -> just extract the number
    match = re.search(r'([\d.]+)\s*(KB|MB|GB)', text, re.IGNORECASE)
    if match:
        value = float(match.group(1))
        unit = match.group(2).upper()
        if unit == 'GB':
            return int(value * 1024 * 1024)
        elif unit == 'MB':
            return int(value * 1024)
        return int(value)
    return None


def parse_tdp(text):
    """Extract TDP in watts"""
    if not text or text == 'N/A':
        return None
    match = re.search(r'([\d.]+)\s*W', text, re.IGNORECASE)
    if match:
        return int(float(match.group(1)))
    return None


def parse_price(text):
    """Extract price as float"""
    if not text or text == 'N/A':
        return None
    match = re.search(r'\$?([\d,]+(?:\.\d{2})?)', text)
    if match:
        return float(match.group(1).replace(',', ''))
    return None


def parse_date(text):
    """Parse release date to YYYY-MM-DD format"""
    if not text or text == 'N/A' or text == 'Never Released':
        return None
    try:
        # Try various date formats
        for fmt in ['%B %d, %Y', '%b %d, %Y', '%Y-%m-%d', '%B %Y', '%Y']:
            try:
                dt = datetime.strptime(text.strip(), fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue
    except:
        pass
    return None


def parse_int(text):
    """Extract integer from text"""
    if not text or text == 'N/A':
        return None
    match = re.search(r'(\d+)', text.replace(',', ''))
    if match:
        return int(match.group(1))
    return None


def get_cpu_links():
    """Get all CPU detail page links from the main list"""
    print("Fetching CPU list from TechPowerUp...")
    cpu_links = []

    # TechPowerUp has multiple pages, let's get the main ones
    # First, get the full list by manufacturer
    for manufacturer in ['intel', 'amd']:
        url = f"{CPU_LIST_URL}?mfgr={manufacturer}&sort=name"
        soup = get_soup(url)
        if not soup:
            continue

        # Find all CPU links in the table
        table = soup.find('table', class_='processors')
        if table:
            for row in table.find_all('tr')[1:]:  # Skip header
                link = row.find('a')
                if link and link.get('href'):
                    href = link.get('href')
                    if href.startswith('/cpu-specs/'):
                        cpu_links.append({
                            'url': BASE_URL + href,
                            'name': link.get_text(strip=True),
                            'manufacturer': manufacturer.upper()
                        })

        time.sleep(REQUEST_DELAY)

    print(f"Found {len(cpu_links)} CPUs")
    return cpu_links


def scrape_cpu_detail(url):
    """Scrape detailed specs from a CPU's detail page"""
    soup = get_soup(url)
    if not soup:
        return None

    specs = {'techpowerup_url': url}

    # Find the specs table
    specs_section = soup.find('section', class_='details')
    if not specs_section:
        return None

    # Parse all spec rows
    for row in specs_section.find_all('tr'):
        cells = row.find_all(['th', 'td'])
        if len(cells) >= 2:
            key = cells[0].get_text(strip=True).lower()
            value = cells[1].get_text(strip=True)

            # Map TechPowerUp fields to our database fields
            if 'name' in key:
                specs['name'] = value
            elif key == 'codename':
                specs['codename'] = value
            elif key == 'generation':
                specs['generation'] = value
            elif key == 'cores':
                specs['cores'] = parse_int(value)
            elif key == 'threads':
                specs['threads'] = parse_int(value)
            elif 'base' in key and 'freq' in key:
                specs['base_clock'] = parse_clock_speed(value)
            elif ('boost' in key or 'turbo' in key) and 'freq' in key:
                specs['boost_clock'] = parse_clock_speed(value)
            elif key == 'tdp':
                specs['tdp'] = parse_tdp(value)
            elif 'l1 cache' in key:
                specs['l1_cache'] = parse_cache(value)
            elif 'l2 cache' in key:
                specs['l2_cache'] = parse_cache(value)
            elif 'l3 cache' in key:
                specs['l3_cache'] = parse_cache(value)
            elif key == 'socket':
                specs['socket_name'] = value
            elif key == 'process':
                specs['process_node'] = value
            elif 'transistors' in key:
                specs['transistors_million'] = parse_int(value)
            elif 'die size' in key:
                match = re.search(r'([\d.]+)', value)
                if match:
                    specs['die_size_mm2'] = float(match.group(1))
            elif 'memory type' in key:
                specs['memory_type'] = value
            elif 'memory bus' in key:
                if 'dual' in value.lower():
                    specs['memory_channels'] = 2
                elif 'quad' in value.lower():
                    specs['memory_channels'] = 4
                elif 'octa' in value.lower() or 'eight' in value.lower():
                    specs['memory_channels'] = 8
            elif 'max memory' in key:
                specs['max_memory_gb'] = parse_int(value)
            elif 'pci-express' in key.lower() or 'pcie' in key.lower():
                match = re.search(r'Gen\s*(\d)', value, re.IGNORECASE)
                if match:
                    specs['pcie_version'] = match.group(1)
                lanes_match = re.search(r'(\d+)\s*Lanes', value, re.IGNORECASE)
                if lanes_match:
                    specs['pcie_lanes'] = int(lanes_match.group(1))
            elif 'release date' in key or 'launch date' in key:
                specs['launch_date'] = parse_date(value)
            elif 'launch price' in key or 'msrp' in key:
                specs['launch_msrp'] = parse_price(value)
            elif key == 'integrated graphics' or 'igpu' in key:
                if value.lower() not in ['no', 'none', 'n/a', '']:
                    specs['has_integrated_gpu'] = True
                    specs['integrated_gpu_name'] = value
                else:
                    specs['has_integrated_gpu'] = False

    return specs


def get_or_create_manufacturer(cursor, name):
    """Get manufacturer ID, creating if necessary"""
    cursor.execute("SELECT id FROM manufacturers WHERE name = %s", (name,))
    result = cursor.fetchone()
    if result:
        return result[0]

    cursor.execute("INSERT INTO manufacturers (name) VALUES (%s)", (name,))
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
        launch_msrp = VALUES(launch_msrp),
        updated_at = CURRENT_TIMESTAMP
    """

    values = (
        cpu_data.get('name'),
        manufacturer_id,
        socket_id,
        cpu_data.get('codename'),
        cpu_data.get('generation'),
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
        cpu_data.get('launch_date'),
        cpu_data.get('launch_msrp'),
        cpu_data.get('techpowerup_url')
    )

    cursor.execute(sql, values)


def export_to_json(output_file='cpu_database.json'):
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

    # Convert datetime objects to strings
    for cpu in cpus:
        for key, value in cpu.items():
            if isinstance(value, datetime):
                cpu[key] = value.strftime('%Y-%m-%d')

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({'cpus': cpus, 'total': len(cpus)}, f, indent=2, default=str)

    cursor.close()
    conn.close()

    print(f"Exported {len(cpus)} CPUs to {output_file}")


def main():
    print("=" * 60)
    print("TechPowerUp CPU Scraper for HardWizChippy")
    print("By KBitWare")
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
        print("3. Run the schema.sql file first")
        return

    # Get all CPU links
    cpu_links = get_cpu_links()

    if not cpu_links:
        print("No CPUs found. Check your internet connection.")
        return

    # Limit for testing - remove this line for full scrape
    # cpu_links = cpu_links[:50]  # Uncomment to test with 50 CPUs first

    print(f"\nScraping {len(cpu_links)} CPUs...")
    print("This will take a while. Be patient!\n")

    success_count = 0
    error_count = 0

    for cpu_info in tqdm(cpu_links, desc="Scraping CPUs"):
        try:
            # Scrape detailed specs
            cpu_data = scrape_cpu_detail(cpu_info['url'])

            if cpu_data and cpu_data.get('name'):
                # Get/create manufacturer
                manufacturer_id = get_or_create_manufacturer(
                    cursor,
                    cpu_info['manufacturer']
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
            # print(f"Error processing {cpu_info['name']}: {e}")

        # Rate limiting
        time.sleep(REQUEST_DELAY)

    cursor.close()
    conn.close()

    print(f"\n{'=' * 60}")
    print(f"Scraping complete!")
    print(f"Successfully scraped: {success_count} CPUs")
    print(f"Errors: {error_count}")
    print(f"{'=' * 60}")

    # Export to JSON
    export_to_json()

    print("\nDone! Your database is now populated.")
    print("You can run your Flutter app to see the data!")


if __name__ == '__main__':
    main()
