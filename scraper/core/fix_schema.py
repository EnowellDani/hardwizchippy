"""Fix database schema - add missing columns."""
import mysql.connector
from config.settings import DB_CONFIG

def column_exists(cursor, table, column):
    cursor.execute(f"SHOW COLUMNS FROM {table} LIKE '{column}'")
    return cursor.fetchone() is not None

def table_exists(cursor, table):
    cursor.execute(f"SHOW TABLES LIKE '{table}'")
    return cursor.fetchone() is not None

def fix_schema():
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()

    print("Checking and fixing database schema...")

    # 1. Add source column to cpu_benchmarks
    if not column_exists(cursor, 'cpu_benchmarks', 'source'):
        print("Adding 'source' column to cpu_benchmarks...")
        cursor.execute("ALTER TABLE cpu_benchmarks ADD COLUMN source VARCHAR(50) DEFAULT NULL")
        conn.commit()
    else:
        print("cpu_benchmarks.source already exists")

    # 2. Create gaming_benchmarks table
    if not table_exists(cursor, 'gaming_benchmarks'):
        print("Creating gaming_benchmarks table...")
        cursor.execute("""
            CREATE TABLE gaming_benchmarks (
                id INT AUTO_INCREMENT PRIMARY KEY,
                cpu_id INT NOT NULL,
                game_name VARCHAR(100) NOT NULL,
                resolution VARCHAR(20) DEFAULT '1080p',
                settings VARCHAR(50) DEFAULT NULL,
                avg_fps DECIMAL(8,2),
                one_percent_low DECIMAL(8,2),
                point_one_percent_low DECIMAL(8,2),
                gpu_used VARCHAR(100),
                source VARCHAR(50),
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (cpu_id) REFERENCES cpus(id) ON DELETE CASCADE,
                UNIQUE KEY unique_benchmark (cpu_id, game_name, resolution, gpu_used)
            )
        """)
        conn.commit()
    else:
        print("gaming_benchmarks table already exists")

    # 3. Create price_history table
    if not table_exists(cursor, 'price_history'):
        print("Creating price_history table...")
        cursor.execute("""
            CREATE TABLE price_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                cpu_id INT NOT NULL,
                price DECIMAL(10,2) NOT NULL,
                source VARCHAR(50),
                retailer VARCHAR(100),
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (cpu_id) REFERENCES cpus(id) ON DELETE CASCADE,
                INDEX idx_cpu_date (cpu_id, scraped_at)
            )
        """)
        conn.commit()
    else:
        print("price_history table already exists")

    # 4. Create scraper_progress table
    if not table_exists(cursor, 'scraper_progress'):
        print("Creating scraper_progress table...")
        cursor.execute("""
            CREATE TABLE scraper_progress (
                id INT AUTO_INCREMENT PRIMARY KEY,
                source VARCHAR(50) NOT NULL UNIQUE,
                last_url TEXT,
                items_scraped INT DEFAULT 0,
                status VARCHAR(20) DEFAULT 'pending',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    else:
        print("scraper_progress table already exists")

    # 5. Add current_price to cpus
    if not column_exists(cursor, 'cpus', 'current_price'):
        print("Adding 'current_price' column to cpus...")
        cursor.execute("ALTER TABLE cpus ADD COLUMN current_price DECIMAL(10,2) DEFAULT NULL")
        conn.commit()
    else:
        print("cpus.current_price already exists")

    # 6. Add price_updated_at to cpus
    if not column_exists(cursor, 'cpus', 'price_updated_at'):
        print("Adding 'price_updated_at' column to cpus...")
        cursor.execute("ALTER TABLE cpus ADD COLUMN price_updated_at TIMESTAMP NULL")
        conn.commit()
    else:
        print("cpus.price_updated_at already exists")

    cursor.close()
    conn.close()
    print("\nSchema fixes complete!")

if __name__ == "__main__":
    fix_schema()
