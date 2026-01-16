"""
Deep analysis of website structures for scraper debugging.
This script captures actual HTML to understand the DOM structure.
"""
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import json
import re

def analyze_geekbench_deeply():
    """Deep analysis of Geekbench page structure."""
    print("=" * 70)
    print("DEEP ANALYSIS: Geekbench")
    print("=" * 70)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto("https://browser.geekbench.com/processor-benchmarks",
                  wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2000)

        # Get the HTML content
        html = page.content()
        soup = BeautifulSoup(html, 'lxml')

        # Find all tables
        tables = soup.find_all('table')
        print(f"\nFound {len(tables)} tables")

        for i, table in enumerate(tables):
            print(f"\n--- Table {i} ---")
            # Get table class
            table_class = table.get('class', ['no-class'])
            print(f"Class: {table_class}")

            # Get parent/header context
            parent = table.find_parent(['div', 'section'])
            if parent:
                parent_id = parent.get('id', 'no-id')
                parent_class = parent.get('class', ['no-class'])
                print(f"Parent: id={parent_id}, class={parent_class}")

            # Find preceding header
            prev_header = table.find_previous(['h1', 'h2', 'h3', 'h4'])
            if prev_header:
                print(f"Preceding header: {prev_header.get_text(strip=True)[:50]}")

            # Analyze rows
            rows = table.find_all('tr')
            print(f"Total rows: {len(rows)}")

            # Sample first 3 rows
            for j, row in enumerate(rows[:3]):
                print(f"\n  Row {j}:")
                cells = row.find_all(['td', 'th'])
                print(f"    Cells: {len(cells)}")

                for k, cell in enumerate(cells[:4]):
                    cell_text = cell.get_text(strip=True)[:40]
                    cell_class = cell.get('class', [])
                    links = cell.find_all('a')
                    print(f"      Cell {k}: class={cell_class}, text='{cell_text}', links={len(links)}")

                    if links:
                        for link in links[:2]:
                            href = link.get('href', '')[:50]
                            link_text = link.get_text(strip=True)[:30]
                            print(f"        Link: href='{href}', text='{link_text}'")

        browser.close()


def analyze_passmark_deeply():
    """Deep analysis of PassMark page structure."""
    print("\n" + "=" * 70)
    print("DEEP ANALYSIS: PassMark")
    print("=" * 70)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print("Loading PassMark (this may take a while)...")

        try:
            # Use domcontentloaded instead of networkidle for faster load
            page.goto("https://www.cpubenchmark.net/cpu_list.php",
                      wait_until="domcontentloaded", timeout=120000)

            # Wait for the table to appear
            page.wait_for_selector("table, #cputable, .chart", timeout=30000)
            page.wait_for_timeout(3000)

            html = page.content()
            soup = BeautifulSoup(html, 'lxml')

            # Find tables
            tables = soup.find_all('table')
            print(f"\nFound {len(tables)} tables")

            for i, table in enumerate(tables[:3]):
                table_id = table.get('id', 'no-id')
                table_class = table.get('class', ['no-class'])
                print(f"\nTable {i}: id={table_id}, class={table_class}")

                rows = table.find_all('tr')
                print(f"Rows: {len(rows)}")

                # Sample rows
                for j, row in enumerate(rows[:3]):
                    cells = row.find_all(['td', 'th'])
                    print(f"  Row {j}: {len(cells)} cells")
                    for k, cell in enumerate(cells[:3]):
                        text = cell.get_text(strip=True)[:30]
                        print(f"    Cell {k}: '{text}'")

            # Also look for chart lists
            chart_lists = soup.select('ul.chartlist, div.chart_body, #mark')
            print(f"\nChart lists found: {len(chart_lists)}")

        except Exception as e:
            print(f"Error: {e}")

        browser.close()


def analyze_pcpartpicker_deeply():
    """Deep analysis of PCPartPicker with anti-bot measures."""
    print("\n" + "=" * 70)
    print("DEEP ANALYSIS: PCPartPicker")
    print("=" * 70)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Non-headless for testing

        # Create context with realistic browser profile
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='en-US',
            timezone_id='America/New_York',
        )

        page = context.new_page()

        # Add stealth scripts to avoid detection
        page.add_init_script("""
            // Override webdriver detection
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });

            // Override plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });

            // Override languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
        """)

        try:
            print("Loading PCPartPicker...")
            page.goto("https://pcpartpicker.com/products/cpu/",
                      wait_until="domcontentloaded", timeout=60000)

            # Wait for content
            page.wait_for_timeout(5000)

            # Check for Cloudflare challenge
            html = page.content()
            if "challenge" in html.lower() or "cloudflare" in html.lower():
                print("Cloudflare challenge detected!")
                print("Waiting for challenge to complete...")
                page.wait_for_timeout(10000)
                html = page.content()

            soup = BeautifulSoup(html, 'lxml')

            # Look for product table
            tables = soup.find_all('table')
            print(f"\nFound {len(tables)} tables")

            # Look for product rows
            product_rows = soup.select('tr.tr__product, tr[data-part], div.product')
            print(f"Product rows found: {len(product_rows)}")

            if product_rows:
                for row in product_rows[:3]:
                    name_elem = row.select_one('td.td__name a, a.td__nameWrapper__name')
                    price_elem = row.select_one('td.td__price, span.price')
                    if name_elem:
                        print(f"  Product: {name_elem.get_text(strip=True)[:40]}")
                    if price_elem:
                        print(f"  Price: {price_elem.get_text(strip=True)}")

        except Exception as e:
            print(f"Error: {e}")

        browser.close()


if __name__ == "__main__":
    analyze_geekbench_deeply()
    analyze_passmark_deeply()
    # analyze_pcpartpicker_deeply()  # Commented out as it needs non-headless
