"""
Import scraped CPU data into MySQL database.
"""
import json
import pymysql
from datetime import datetime

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'kbitboy',
    'password': 'danieyl',
    'database': 'hardwizchippy',
    'charset': 'utf8mb4'
}

def get_manufacturer_id(cursor, cpu_name):
    """Determine manufacturer ID from CPU name."""
    if 'intel' in cpu_name.lower():
        cursor.execute("SELECT id FROM manufacturers WHERE name = 'Intel'")
        result = cursor.fetchone()
        return result[0] if result else 1  # Default to 1 for Intel
    elif 'amd' in cpu_name.lower() or 'ryzen' in cpu_name.lower():
        cursor.execute("SELECT id FROM manufacturers WHERE name = 'AMD'")
        result = cursor.fetchone()
        return result[0] if result else 2  # Default to 2 for AMD
    return 1  # Default to Intel


def create_tables(cursor):
    """Ensure necessary tables exist (using existing schema)."""
    # Tables already exist, just verify manufacturers
    cursor.execute("SELECT COUNT(*) FROM manufacturers WHERE name IN ('Intel', 'AMD')")
    count = cursor.fetchone()[0]
    
    if count < 2:
        # Add manufacturers if missing
        cursor.execute("INSERT IGNORE INTO manufacturers (name) VALUES ('Intel'), ('AMD')")
    
    print("✅ Tables verified")


def import_data(cursor, json_file='direct_scrape_results.json'):
    """Import CPU data from JSON file."""
    
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"📊 Loading {len(data['cpus'])} CPUs...")
    
    imported_count = 0
    skipped_count = 0
    
    for cpu in data['cpus']:
        cpu_name = cpu['name']
        
        try:
            manufacturer_id = get_manufacturer_id(cursor, cpu_name)
            
            # Insert CPU (or get existing) using existing schema
            cursor.execute("""
                INSERT INTO cpus (name, manufacturer_id) VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE id=LAST_INSERT_ID(id)
            """, (cpu_name, manufacturer_id))
            
            cpu_id = cursor.lastrowid
            if cpu_id == 0:
                cursor.execute("SELECT id FROM cpus WHERE name = %s", (cpu_name,))
                cpu_id = cursor.fetchone()[0]
            
            # Aggregate best data from all sources
            best_specs = {
                'transistors_million': None,
                'die_size_mm2': None,
                'cores': None,
                'threads': None,
                'base_clock': None,
                'boost_clock': None,
                'tdp': None,
                'process_node': None
            }
            
            # Process each source
            for source in cpu['sources']:
                # Insert source data (handle None values properly)
                try:
                    # Validate numeric fields to prevent corrupted data
                    def safe_float(value):
                        """Convert to float, return None if invalid."""
                        if value is None:
                            return None
                        try:
                            result = float(value)
                            # Sanity check: reject unreasonable values
                            if result < 0 or result > 100000:
                                return None
                            return result
                        except (ValueError, TypeError):
                            return None
                    
                    def safe_int(value):
                        """Convert to int, return None if invalid."""
                        if value is None:
                            return None
                        try:
                            result = int(value)
                            if result < 0 or result > 10000:
                                return None
                            return result
                        except (ValueError, TypeError):
                            return None
                    
                    def safe_string(value, max_length=500):
                        """Truncate string to max length."""
                        if value is None:
                            return None
                        str_val = str(value)
                        # Remove obviously corrupted data (contains HTML/JavaScript)
                        if any(x in str_val.lower() for x in ['<script', 'function(', '\\x', 'data-jc']):
                            return None
                        return str_val[:max_length]
                    
                    cursor.execute("""
                        INSERT INTO cpu_source_data 
                        (cpu_id, source, url, success, transistors_million, die_size_mm2, 
                         cores, threads, base_clock_ghz, boost_clock_ghz, tdp, process_node, raw_data_count)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        cpu_id,
                        source['source'],
                        source['url'],
                        source['success'],
                        safe_float(source.get('transistors_million')),
                        safe_float(source.get('die_size_mm2')),
                        safe_int(source.get('cores')),
                        safe_int(source.get('threads')),
                        safe_float(source.get('base_clock_ghz')),
                        safe_float(source.get('boost_clock_ghz')),
                        safe_int(source.get('tdp')),
                        safe_string(source.get('process_node'), 500),
                        source.get('raw_data_count', 0)
                    ))
                    
                    source_data_id = cursor.lastrowid
                    
                    # Insert raw data key-value pairs
                    if source.get('raw_data'):
                        for key, value in source['raw_data'].items():
                            try:
                                cursor.execute("""
                                    INSERT INTO cpu_raw_data (source_data_id, data_key, data_value)
                                    VALUES (%s, %s, %s)
                                """, (source_data_id, key, str(value)[:500]))  # Limit value length
                            except Exception as e:
                                # Skip problematic raw data entries
                                continue
                    
                    # Update best specs (prefer non-null values)
                    if source['success']:
                        for field in best_specs:
                            source_field = field.replace('_clock', '_clock_ghz')  # Map to source format
                            if source.get(source_field) is not None:
                                best_specs[field] = source[source_field]
                
                except Exception as e:
                    print(f"    ⚠️ Error inserting source {source['source']}: {e}")
                    continue
            
            # Update main CPUs table with aggregated specs (with validation)
            update_fields = []
            update_values = []
            
            if best_specs['transistors_million'] is not None:
                validated = safe_float(best_specs['transistors_million'])
                if validated is not None:
                    update_fields.append('transistors_million = %s')
                    update_values.append(validated)
            if best_specs['die_size_mm2'] is not None:
                validated = safe_float(best_specs['die_size_mm2'])
                if validated is not None:
                    update_fields.append('die_size_mm2 = %s')
                    update_values.append(validated)
            if best_specs['cores'] is not None:
                validated = safe_int(best_specs['cores'])
                if validated is not None:
                    update_fields.append('cores = %s')
                    update_values.append(validated)
            if best_specs['threads'] is not None:
                validated = safe_int(best_specs['threads'])
                if validated is not None:
                    update_fields.append('threads = %s')
                    update_values.append(validated)
            if best_specs['base_clock'] is not None:
                validated = safe_float(best_specs['base_clock'])
                if validated is not None:
                    update_fields.append('base_clock = %s')
                    update_values.append(validated)
            if best_specs['boost_clock'] is not None:
                validated = safe_float(best_specs['boost_clock'])
                if validated is not None:
                    update_fields.append('boost_clock = %s')
                    update_values.append(validated)
            if best_specs['tdp'] is not None:
                validated = safe_int(best_specs['tdp'])
                if validated is not None:
                    update_fields.append('tdp = %s')
                    update_values.append(validated)
            if best_specs['process_node'] is not None:
                validated = safe_string(best_specs['process_node'], 500)
                if validated is not None:
                    update_fields.append('process_node = %s')
                    update_values.append(validated)
            
            if update_fields:
                update_values.append(cpu_id)
                cursor.execute(f"""
                    UPDATE cpus SET {', '.join(update_fields)}
                    WHERE id = %s
                """, tuple(update_values))
            
            imported_count += 1
            print(f"  ✅ {cpu_name}")
            
        except Exception as e:
            print(f"  ❌ {cpu_name}: {e}")
            skipped_count += 1
    
    print(f"\n📊 Import complete:")
    print(f"  ✅ Imported: {imported_count}")
    print(f"  ❌ Skipped: {skipped_count}")


def show_stats(cursor):
    """Show database statistics."""
    cursor.execute("SELECT COUNT(*) FROM cpus")
    cpu_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM cpus WHERE cores IS NOT NULL")
    specs_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM cpu_source_data WHERE success = TRUE")
    success_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM cpu_raw_data")
    raw_count = cursor.fetchone()[0]
    
    # Show sample CPU
    cursor.execute("""
        SELECT name, cores, threads, base_clock, boost_clock, tdp, process_node
        FROM cpus 
        WHERE cores IS NOT NULL 
        LIMIT 1
    """)
    sample = cursor.fetchone()
    
    print(f"\n📊 Database Statistics:")
    print(f"  Total CPUs: {cpu_count}")
    print(f"  CPUs with specs: {specs_count}")
    print(f"  Successful scrapes: {success_count}")
    print(f"  Raw data points: {raw_count}")
    
    if sample:
        print(f"\n📋 Sample CPU: {sample[0]}")
        print(f"  Cores: {sample[1]}, Threads: {sample[2]}")
        print(f"  Base: {sample[3]} GHz, Boost: {sample[4]} GHz")
        print(f"  TDP: {sample[5]}W, Process: {sample[6]}")


def main():
    """Main import process."""
    print("🔌 Connecting to MySQL...")
    
    try:
        connection = pymysql.connect(**DB_CONFIG)
        cursor = connection.cursor()
        
        print("✅ Connected to database")
        
        # Create tables
        create_tables(cursor)
        connection.commit()
        
        # Import data
        import_data(cursor)
        connection.commit()
        
        # Show stats
        show_stats(cursor)
        
        cursor.close()
        connection.close()
        
        print("\n✅ Import completed successfully!")
        
    except pymysql.Error as e:
        print(f"❌ Database error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == '__main__':
    main()
