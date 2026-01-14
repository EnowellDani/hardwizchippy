"""
Quick TechPowerUp CPU Scraper - Updated for 2026
Gets CPU data from the main list and individual pages
"""

import requests
from bs4 import BeautifulSoup
import mysql.connector
import json
import time
import re
from tqdm import tqdm

# Configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'kbitboy',
    'password': 'danieyl',
    'database': 'hardwizchippy'
}

BASE_URL = 'https://www.techpowerup.com'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Connection': 'keep-alive',
}


def get_soup(url):
    """Fetch a URL and return BeautifulSoup object"""
    try:
        session = requests.Session()
        response = session.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        return BeautifulSoup(response.text, 'lxml')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None


def parse_clock(text):
    """Convert clock speed to MHz"""
    if not text or text == '-':
        return None
    match = re.search(r'([\d.]+)', text)
    if match:
        val = float(match.group(1))
        if 'GHz' in text or val < 100:
            return int(val * 1000)
        return int(val)
    return None


def parse_int(text):
    """Extract integer from text"""
    if not text or text == '-':
        return None
    match = re.search(r'(\d+)', text.replace(',', ''))
    return int(match.group(1)) if match else None


def parse_cache(text):
    """Convert cache to KB"""
    if not text or text == '-':
        return None
    match = re.search(r'([\d.]+)\s*(KB|MB)', text, re.IGNORECASE)
    if match:
        val = float(match.group(1))
        if match.group(2).upper() == 'MB':
            return int(val * 1024)
        return int(val)
    return None


def scrape_main_page():
    """Scrape CPUs from the main page (top 100 popular)"""
    print("Fetching main CPU list...")
    url = f"{BASE_URL}/cpu-specs/"
    soup = get_soup(url)

    if not soup:
        return []

    cpus = []
    table = soup.find('table', class_='items-desktop-table')

    if not table:
        print("Could not find CPU table on page")
        return []

    rows = table.find_all('tr')[1:]  # Skip header

    for row in rows:
        cells = row.find_all('td')
        if len(cells) < 9:
            continue

        name_link = cells[0].find('a')
        if not name_link:
            continue

        # Determine manufacturer from name
        name = name_link.get_text(strip=True)
        if name.lower().startswith('intel') or 'core' in name.lower() or 'xeon' in name.lower() or 'pentium' in name.lower() or 'celeron' in name.lower():
            manufacturer = 'INTEL'
        elif name.lower().startswith('amd') or 'ryzen' in name.lower() or 'athlon' in name.lower() or 'epyc' in name.lower():
            manufacturer = 'AMD'
        else:
            manufacturer = 'OTHER'

        cpu = {
            'name': name,
            'url': BASE_URL + name_link.get('href', ''),
            'manufacturer': manufacturer,
            'codename': cells[1].get_text(strip=True) or None,
            'cores': parse_int(cells[2].get_text(strip=True)),
            'clock_range': cells[3].get_text(strip=True),
            'socket_name': cells[4].get_text(strip=True) or None,
            'process_node': cells[5].get_text(strip=True) or None,
            'l3_cache': parse_cache(cells[6].get_text(strip=True)),
            'tdp': parse_int(cells[7].get_text(strip=True)),
            'launch_date': cells[8].get_text(strip=True) or None,
        }

        # Parse clock range (e.g., "3.4 to 5.0 GHz")
        clock_text = cpu['clock_range']
        if clock_text and 'to' in clock_text.lower():
            parts = re.split(r'\s*to\s*', clock_text, flags=re.IGNORECASE)
            if len(parts) >= 2:
                cpu['base_clock'] = parse_clock(parts[0] + ' GHz')
                cpu['boost_clock'] = parse_clock(parts[1])
        elif clock_text:
            cpu['base_clock'] = parse_clock(clock_text)
            cpu['boost_clock'] = None

        cpus.append(cpu)

    return cpus


def search_cpus(query):
    """Search for CPUs using TechPowerUp search"""
    url = f"{BASE_URL}/cpu-specs/?q={query}"
    soup = get_soup(url)

    if not soup:
        return []

    cpus = []
    table = soup.find('table', class_='items-desktop-table')

    if not table:
        return []

    rows = table.find_all('tr')[1:]

    for row in rows:
        cells = row.find_all('td')
        if len(cells) < 9:
            continue

        name_link = cells[0].find('a')
        if not name_link:
            continue

        name = name_link.get_text(strip=True)

        # Determine manufacturer
        if 'intel' in name.lower() or 'core' in name.lower() or 'xeon' in name.lower():
            manufacturer = 'INTEL'
        elif 'amd' in name.lower() or 'ryzen' in name.lower() or 'epyc' in name.lower():
            manufacturer = 'AMD'
        else:
            manufacturer = 'OTHER'

        cpu = {
            'name': name,
            'url': BASE_URL + name_link.get('href', ''),
            'manufacturer': manufacturer,
            'codename': cells[1].get_text(strip=True) or None,
            'cores': parse_int(cells[2].get_text(strip=True)),
            'clock_range': cells[3].get_text(strip=True),
            'socket_name': cells[4].get_text(strip=True) or None,
            'process_node': cells[5].get_text(strip=True) or None,
            'l3_cache': parse_cache(cells[6].get_text(strip=True)),
            'tdp': parse_int(cells[7].get_text(strip=True)),
            'launch_date': cells[8].get_text(strip=True) or None,
        }

        clock_text = cpu['clock_range']
        if clock_text and 'to' in clock_text.lower():
            parts = re.split(r'\s*to\s*', clock_text, flags=re.IGNORECASE)
            if len(parts) >= 2:
                cpu['base_clock'] = parse_clock(parts[0] + ' GHz')
                cpu['boost_clock'] = parse_clock(parts[1])
        elif clock_text:
            cpu['base_clock'] = parse_clock(clock_text)
            cpu['boost_clock'] = None

        cpus.append(cpu)

    return cpus


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
    if not name or name == '-':
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
    """Parse release date"""
    if not text or text == '-' or text == 'Never Released':
        return None
    from datetime import datetime
    for fmt in ['%b %d, %Y', '%B %d, %Y', '%Y-%m-%d', '%b %Y', '%B %Y']:
        try:
            return datetime.strptime(text.strip(), fmt).strftime('%Y-%m-%d')
        except ValueError:
            continue
    return None


def main():
    print("=" * 60)
    print("Quick TechPowerUp CPU Scraper")
    print("=" * 60)

    # Connect to database
    print("\nConnecting to MySQL...")
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        print("Connected!")
    except Exception as e:
        print(f"Database error: {e}")
        print("\nMake sure Laragon is running and database exists!")
        return

    all_cpus = []

    # Get popular CPUs from main page
    print("\nScraping popular CPUs from main page...")
    popular_cpus = scrape_main_page()
    all_cpus.extend(popular_cpus)
    print(f"  Found {len(popular_cpus)} popular CPUs")

    # Search for more CPUs by common series
    search_terms = [
        # Intel Desktop
        'Core i9', 'Core i7', 'Core i5', 'Core i3',
        'Core Ultra 9', 'Core Ultra 7', 'Core Ultra 5',
        # Intel older
        'Core 2', 'Pentium', 'Celeron',
        # Intel Server
        'Xeon',
        # AMD Desktop
        'Ryzen 9', 'Ryzen 7', 'Ryzen 5', 'Ryzen 3',
        'Ryzen Threadripper',
        # AMD older
        'Athlon', 'Phenom', 'FX-',
        # AMD Server
        'EPYC',
    ]

    print("\nSearching for more CPUs by series...")
    seen_names = set(cpu['name'] for cpu in all_cpus)

    for term in tqdm(search_terms, desc="Searching"):
        results = search_cpus(term)
        for cpu in results:
            if cpu['name'] not in seen_names:
                all_cpus.append(cpu)
                seen_names.add(cpu['name'])
        time.sleep(0.5)  # Rate limiting

    print(f"\nTotal unique CPUs found: {len(all_cpus)}")
    print("\nInserting into database...")

    success = 0
    for cpu in tqdm(all_cpus, desc="Inserting"):
        try:
            mfg_id = get_or_create_manufacturer(cursor, cpu['manufacturer'])
            socket_id = get_or_create_socket(cursor, cpu['socket_name'], mfg_id)

            sql = """
            INSERT INTO cpus (
                name, manufacturer_id, socket_id, codename,
                cores, base_clock, boost_clock, l3_cache, tdp,
                process_node, launch_date, techpowerup_url
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                codename = VALUES(codename),
                cores = VALUES(cores),
                base_clock = VALUES(base_clock),
                boost_clock = VALUES(boost_clock),
                tdp = VALUES(tdp),
                updated_at = CURRENT_TIMESTAMP
            """

            cursor.execute(sql, (
                cpu['name'],
                mfg_id,
                socket_id,
                cpu['codename'],
                cpu['cores'],
                cpu.get('base_clock'),
                cpu.get('boost_clock'),
                cpu['l3_cache'],
                cpu['tdp'],
                cpu['process_node'],
                parse_date(cpu['launch_date']),
                cpu['url']
            ))
            conn.commit()
            success += 1
        except Exception as e:
            pass

    cursor.close()
    conn.close()

    print(f"\n{'=' * 60}")
    print(f"Done! Inserted {success} CPUs into database.")
    print("=" * 60)

    # Export to JSON
    print("\nExporting to JSON...")
    export_to_json(all_cpus)


def export_to_json(cpus):
    """Export to JSON for Flutter"""
    clean_cpus = []
    for cpu in cpus:
        clean_cpus.append({
            'name': cpu['name'],
            'manufacturer': cpu['manufacturer'],
            'codename': cpu['codename'],
            'cores': cpu['cores'],
            'base_clock': cpu.get('base_clock'),
            'boost_clock': cpu.get('boost_clock'),
            'l3_cache': cpu['l3_cache'],
            'tdp': cpu['tdp'],
            'socket': cpu['socket_name'],
            'process_node': cpu['process_node'],
            'launch_date': cpu['launch_date'],
        })

    with open('cpu_database.json', 'w', encoding='utf-8') as f:
        json.dump({'cpus': clean_cpus, 'total': len(clean_cpus)}, f, indent=2)

    print(f"Exported {len(clean_cpus)} CPUs to cpu_database.json")


if __name__ == '__main__':
    main()
