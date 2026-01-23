"""
Analyze data quality from recent scraping batches.
"""
import pymysql

conn = pymysql.connect(host='localhost', user='kbitboy', password='danieyl', database='hardwizchippy')
cursor = conn.cursor()

print('📊 DATA QUALITY ANALYSIS')
print('=' * 80)

# Recent scrapes performance
cursor.execute('''
    SELECT 
        source,
        COUNT(*) as total_attempts,
        SUM(success) as successful,
        ROUND(AVG(success) * 100, 1) as success_rate,
        COUNT(DISTINCT cpu_id) as unique_cpus,
        ROUND(AVG(raw_data_count), 1) as avg_data_points
    FROM cpu_source_data
    WHERE id > (SELECT MAX(id) - 180 FROM cpu_source_data)
    GROUP BY source
    ORDER BY success_rate DESC
''')

print('\n🎯 SOURCE PERFORMANCE (Last 180 records):')
print(f"{'Source':<20} {'Attempts':<10} {'Success':<10} {'Rate':<10} {'CPUs':<10} {'Avg Data'}")
print('-' * 80)
for row in cursor.fetchall():
    source, total, successful, rate, cpus, avg_data = row
    print(f"{source:<20} {total:<10} {successful:<10} {rate}%{'':<7} {cpus:<10} {avg_data}")

# Transistor extraction by manufacturer
cursor.execute('''
    SELECT 
        m.name as manufacturer,
        COUNT(DISTINCT c.id) as total_cpus,
        SUM(CASE WHEN c.transistors_million IS NOT NULL THEN 1 ELSE 0 END) as with_transistors,
        ROUND(AVG(CASE WHEN c.transistors_million IS NOT NULL THEN 1 ELSE 0 END) * 100, 1) as transistor_rate
    FROM cpus c
    JOIN manufacturers m ON c.manufacturer_id = m.id
    WHERE c.id IN (SELECT DISTINCT cpu_id FROM cpu_source_data WHERE id > (SELECT MAX(id) - 180 FROM cpu_source_data))
    GROUP BY m.name
''')

print('\n🔬 TRANSISTOR DATA EXTRACTION:')
print(f"{'Manufacturer':<15} {'Total CPUs':<12} {'With Data':<12} {'Rate'}")
print('-' * 60)
for row in cursor.fetchall():
    manuf, total, with_data, rate = row
    print(f"{manuf:<15} {total:<12} {with_data:<12} {rate}%")

# Benchmark coverage
cursor.execute('''
    SELECT 
        c.name,
        c.cores,
        c.transistors_million,
        (SELECT COUNT(DISTINCT source) FROM cpu_source_data WHERE cpu_id = c.id AND success = 1) as sources_count
    FROM cpus c
    WHERE c.id IN (SELECT DISTINCT cpu_id FROM cpu_source_data WHERE id > (SELECT MAX(id) - 180 FROM cpu_source_data))
    ORDER BY sources_count DESC
    LIMIT 5
''')

print('\n🏆 TOP 5 CPUs BY SOURCE COVERAGE:')
print(f"{'CPU Name':<35} {'Sources':<10} {'Cores':<8} {'Transistors'}")
print('-' * 80)
for row in cursor.fetchall():
    name, cores, trans, sources = row
    trans_str = f"{trans}M" if trans else "N/A"
    cores_str = str(cores) if cores else "N/A"
    print(f"{name[:34]:<35} {sources}/5{'':<6} {cores_str:<8} {trans_str}")

# Data completeness
cursor.execute('''
    SELECT 
        COUNT(DISTINCT c.id) as total_cpus,
        SUM(CASE WHEN c.cores IS NOT NULL THEN 1 ELSE 0 END) as with_cores,
        SUM(CASE WHEN c.boost_clock IS NOT NULL THEN 1 ELSE 0 END) as with_boost,
        SUM(CASE WHEN c.tdp IS NOT NULL THEN 1 ELSE 0 END) as with_tdp,
        SUM(CASE WHEN c.process_node IS NOT NULL THEN 1 ELSE 0 END) as with_process
    FROM cpus c
    WHERE c.id IN (SELECT DISTINCT cpu_id FROM cpu_source_data WHERE id > (SELECT MAX(id) - 180 FROM cpu_source_data))
''')

row = cursor.fetchone()
total = row[0]
print('\n📈 DATA COMPLETENESS (Recent Batch):')
print(f"Total CPUs: {total}")
print(f"Cores: {row[1]}/{total} ({round(row[1]/total*100, 1)}%)")
print(f"Boost Clock: {row[2]}/{total} ({round(row[2]/total*100, 1)}%)")
print(f"TDP: {row[3]}/{total} ({round(row[3]/total*100, 1)}%)")
print(f"Process Node: {row[4]}/{total} ({round(row[4]/total*100, 1)}%)")

# Most problematic CPUs
cursor.execute('''
    SELECT 
        c.name,
        COUNT(*) as total_sources,
        SUM(success) as successful_sources
    FROM cpus c
    JOIN cpu_source_data csd ON c.id = csd.cpu_id
    WHERE c.id IN (SELECT DISTINCT cpu_id FROM cpu_source_data WHERE id > (SELECT MAX(id) - 180 FROM cpu_source_data))
    GROUP BY c.id, c.name
    HAVING successful_sources < 2
    ORDER BY successful_sources ASC
    LIMIT 5
''')

print('\n⚠️ MOST PROBLEMATIC CPUs (< 2 sources successful):')
print(f"{'CPU Name':<35} {'Attempts':<12} {'Successful'}")
print('-' * 60)
for row in cursor.fetchall():
    name, attempts, successful = row
    print(f"{name[:34]:<35} {attempts:<12} {successful}")

conn.close()
print('\n✅ Analysis complete!')
