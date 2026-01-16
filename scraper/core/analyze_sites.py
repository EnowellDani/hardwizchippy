"""Analyze website structures to fix scrapers."""
from playwright.sync_api import sync_playwright
import json

def analyze_techpowerup():
    """Analyze TechPowerUp CPU specs page structure."""
    print("=" * 60)
    print("Analyzing TechPowerUp...")
    print("=" * 60)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Check main page
        page.goto("https://www.techpowerup.com/cpu-specs/", wait_until="networkidle", timeout=30000)
        content = page.content()

        # Find table classes
        tables = page.query_selector_all("table")
        print(f"Found {len(tables)} tables on main page")

        for i, table in enumerate(tables):
            class_attr = table.get_attribute("class") or "no-class"
            rows = table.query_selector_all("tr")
            print(f"  Table {i}: class='{class_attr}', rows={len(rows)}")

        # Check for pagination
        pagination = page.query_selector_all("a[href*='page=']")
        print(f"Found {len(pagination)} pagination links")

        # Check if there's a "load more" or infinite scroll
        load_more = page.query_selector("button.load-more, a.load-more, [data-load-more]")
        print(f"Load more button: {load_more is not None}")

        # Check CPU table structure
        cpu_rows = page.query_selector_all("table tr a[href*='/cpu-specs/']")
        print(f"Found {len(cpu_rows)} CPU links in table")

        # Get first few CPU links
        print("\nFirst 5 CPU links:")
        for link in cpu_rows[:5]:
            href = link.get_attribute("href")
            text = link.text_content()
            print(f"  {text}: {href}")

        browser.close()

def analyze_geekbench():
    """Analyze Geekbench page structure."""
    print("\n" + "=" * 60)
    print("Analyzing Geekbench...")
    print("=" * 60)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Try different URLs
        urls = [
            "https://browser.geekbench.com/v6/cpu",
            "https://browser.geekbench.com/processor-benchmarks",
            "https://browser.geekbench.com/v6/cpu/charts",
        ]

        for url in urls:
            print(f"\nTrying: {url}")
            try:
                page.goto(url, wait_until="networkidle", timeout=15000)
                title = page.title()
                print(f"  Title: {title}")

                # Find tables
                tables = page.query_selector_all("table")
                print(f"  Tables: {len(tables)}")

                # Find benchmark rows
                rows = page.query_selector_all("tr")
                print(f"  Table rows: {len(rows)}")

            except Exception as e:
                print(f"  Error: {e}")

        browser.close()

def analyze_passmark():
    """Analyze PassMark page structure."""
    print("\n" + "=" * 60)
    print("Analyzing PassMark...")
    print("=" * 60)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto("https://www.cpubenchmark.net/cpu_list.php", wait_until="networkidle", timeout=30000)

        # Find chart items
        chart_items = page.query_selector_all("ul.chartlist li, div.chart_body li")
        print(f"Found {len(chart_items)} chart items")

        # Try to get first few
        print("\nFirst 5 entries:")
        for item in chart_items[:5]:
            name_el = item.query_selector("span.prdname, a.name")
            score_el = item.query_selector("span.count, span.score")
            if name_el and score_el:
                print(f"  {name_el.text_content()}: {score_el.text_content()}")

        browser.close()

def analyze_tomshardware():
    """Analyze Tom's Hardware page structure."""
    print("\n" + "=" * 60)
    print("Analyzing Tom's Hardware...")
    print("=" * 60)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto("https://www.tomshardware.com/reviews/cpu-hierarchy,4312.html",
                  wait_until="networkidle", timeout=30000)

        # Wait for dynamic content
        page.wait_for_timeout(3000)

        # Find benchmark sections
        charts = page.query_selector_all("div.chart, figure, div[class*='chart'], div[class*='benchmark']")
        print(f"Found {len(charts)} chart/benchmark sections")

        # Find tables
        tables = page.query_selector_all("table")
        print(f"Found {len(tables)} tables")

        for i, table in enumerate(tables[:3]):
            rows = table.query_selector_all("tr")
            print(f"  Table {i}: {len(rows)} rows")

        browser.close()

if __name__ == "__main__":
    analyze_techpowerup()
    analyze_geekbench()
    analyze_passmark()
    analyze_tomshardware()
