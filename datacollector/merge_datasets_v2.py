"""
Simplified CPU dataset merger - v2
"""
import pandas as pd
import json
import pymysql
from fuzzywuzzy import fuzz
import re

def normalize_cpu_name(name):
    """Normalize CPU names for matching."""
    if not name or pd.isna(name):
        return ""
    name = str(name).lower().strip()
    name = re.sub(r'\s+', ' ', name)
    name = name.replace('processor', '').replace('cpu', '')
    name = name.replace('(tm)', '').replace('™', '')
    name = name.strip()
    return name

def main():
    print("=" * 80)
    print("🔄 CPU DATASET MERGER v2")
    print("=" * 80)
    
    # Load PassMark benchmarks
    print("\n📖 Loading PassMark benchmarks...")
    df_passmark = pd.read_csv('data_sources/CPU_benchmark_v4.csv')
    df_passmark = df_passmark[['cpuName', 'cpuMark', 'threadMark', 'TDP', 'cores', 'socket']].copy()
    df_passmark.columns = ['name', 'passmark_multi', 'passmark_single', 'tdp', 'cores', 'socket']
    print(f"✅ {len(df_passmark)} CPUs")
    
    # Load Cinebench R23
    print("\n📖 Loading Cinebench R23...")
    df_cinebench = pd.read_csv('data_sources/CPU_r23_v2.csv')
    df_cinebench = df_cinebench[['cpuName', 'singleScore', 'multiScore', 'cores']].copy()
    df_cinebench.columns = ['name', 'cinebench_single', 'cinebench_multi', 'cores']
    print(f"✅ {len(df_cinebench)} CPUs")
    
    # Load AMD specs
    print("\n📖 Loading AMD specs...")
    df_amd = pd.read_csv('data_sources/AMDfullspecs_adjusted.csv')
    print(f"   Columns: {list(df_amd.columns)[:5]}...")
    # Find name column
    name_col = None
    for col in df_amd.columns:
        if 'model' in col.lower() or 'name' in col.lower():
            name_col = col
            break
    if name_col:
        df_amd = df_amd.rename(columns={name_col: 'name'})
        df_amd['manufacturer'] = 'AMD'
        print(f"✅ {len(df_amd)} AMD CPUs")
    else:
        print(f"⚠️ No name column found")
        df_amd = pd.DataFrame()
    
    # Load Intel specs
    print("\n📖 Loading Intel specs...")
    df_intel = pd.read_csv('data_sources/INTELpartialspecs_adjusted.csv')
    print(f"   Columns: {list(df_intel.columns)[:5]}...")
    name_col = None
    for col in df_intel.columns:
        if 'model' in col.lower() or 'name' in col.lower() or 'product' in col.lower():
            name_col = col
            break
    if name_col:
        df_intel = df_intel.rename(columns={name_col: 'name'})
        df_intel['manufacturer'] = 'Intel'
        print(f"✅ {len(df_intel)} Intel CPUs")
    else:
        print(f"⚠️ No name column found")
        df_intel = pd.DataFrame()
    
    # Merge benchmarks first
    print("\n🔗 Merging benchmarks...")
    df = df_passmark.merge(df_cinebench[['name', 'cinebench_single', 'cinebench_multi']], 
                          on='name', how='outer')
    print(f"✅ {len(df)} CPUs with benchmarks")
    
    # Add AMD specs
    if not df_amd.empty:
        print("\n🔗 Adding AMD specs...")
        # Keep only common columns (exclude socket)
        amd_cols = ['name', 'manufacturer'] + [col for col in df_amd.columns 
                                                if col in ['cores', 'threads', 'tdp']]
        df_amd_clean = df_amd[amd_cols].copy()
        df = df.merge(df_amd_clean, on='name', how='outer', suffixes=('', '_amd'))
        print(f"✅ {len(df)} total CPUs")
    
    # Add Intel specs
    if not df_intel.empty:
        print("\n🔗 Adding Intel specs...")
        intel_cols = ['name', 'manufacturer'] + [col for col in df_intel.columns 
                                                  if col in ['cores', 'threads', 'tdp']]
        df_intel_clean = df_intel[intel_cols].copy()
        df = df.merge(df_intel_clean, on='name', how='outer', suffixes=('', '_intel'))
        print(f"✅ {len(df)} total CPUs")
    
    # Resolve duplicate columns (e.g., cores, cores_amd, cores_intel)
    for col_base in ['cores', 'threads', 'tdp', 'manufacturer']:
        if f'{col_base}_amd' in df.columns or f'{col_base}_intel' in df.columns:
            # Combine the columns
            if col_base in df.columns:
                base_col = df[col_base]
            else:
                base_col = pd.Series([None] * len(df))
            
            if f'{col_base}_amd' in df.columns:
                base_col = base_col.fillna(df[f'{col_base}_amd'])
                df = df.drop(columns=[f'{col_base}_amd'])
            
            if f'{col_base}_intel' in df.columns:
                base_col = base_col.fillna(df[f'{col_base}_intel'])
                df = df.drop(columns=[f'{col_base}_intel'])
            
            df[col_base] = base_col
    
    # Drop socket column as database uses socket_id
    if 'socket' in df.columns:
        df = df.drop(columns=['socket'])
    
    # Save merged data
    print("\n💾 Saving merged dataset...")
    df.to_csv('data_sources/merged_cpu_data.csv', index=False)
    print(f"✅ Saved {len(df)} CPUs to merged_cpu_data.csv")
    
    # Import to MySQL
    print("\n📤 Importing to MySQL...")
    try:
        conn = pymysql.connect(
            host='localhost',
            user='kbitboy',
            password='danieyl',
            database='hardwizchippy',
            charset='utf8mb4'
        )
        cursor = conn.cursor()
        
        imported = 0
        updated = 0
        errors = 0
        batch_size = 100
        
        for idx, row in df.iterrows():
            try:
                # Determine manufacturer
                manufacturer_id = 1  # Default Intel
                if pd.notna(row.get('manufacturer')):
                    if 'amd' in str(row['manufacturer']).lower():
                        manufacturer_id = 2
                elif pd.notna(row.get('name')):
                    name_lower = str(row['name']).lower()
                    if 'ryzen' in name_lower or 'threadripper' in name_lower or 'epyc' in name_lower:
                        manufacturer_id = 2
                
                # Insert/update CPU
                cursor.execute("""
                    INSERT INTO cpus (name, manufacturer_id, cores, threads, tdp)
                    VALUES (%s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        cores = COALESCE(VALUES(cores), cores),
                        threads = COALESCE(VALUES(threads), threads),
                        tdp = COALESCE(VALUES(tdp), tdp),
                        id = LAST_INSERT_ID(id)
                """, (
                    str(row['name'])[:150] if pd.notna(row.get('name')) else None,
                    manufacturer_id,
                    int(row['cores']) if pd.notna(row.get('cores')) else None,
                    int(row['threads']) if pd.notna(row.get('threads')) else None,
                    int(row['tdp']) if pd.notna(row.get('tdp')) else None
                ))
                
                cpu_id = cursor.lastrowid
                if cpu_id == 0:
                    cursor.execute("SELECT id FROM cpus WHERE name = %s", (row['name'],))
                    result = cursor.fetchone()
                    if result:
                        cpu_id = result[0]
                        updated += 1
                    else:
                        continue
                else:
                    imported += 1
                
                # Insert PassMark (benchmark_id: 6=Multi, 5=Single)
                if pd.notna(row.get('passmark_multi')):
                    cursor.execute("""
                        INSERT INTO cpu_benchmarks (cpu_id, benchmark_id, score, source)
                        VALUES (%s, 6, %s, 'kaggle')
                        ON DUPLICATE KEY UPDATE score = VALUES(score)
                    """, (cpu_id, float(row['passmark_multi'])))
                
                if pd.notna(row.get('passmark_single')):
                    cursor.execute("""
                        INSERT INTO cpu_benchmarks (cpu_id, benchmark_id, score, source)
                        VALUES (%s, 5, %s, 'kaggle')
                        ON DUPLICATE KEY UPDATE score = VALUES(score)
                    """, (cpu_id, float(row['passmark_single'])))
                
                # Insert Cinebench R23 (benchmark_id: 2=Multi, 1=Single)
                if pd.notna(row.get('cinebench_multi')):
                    cursor.execute("""
                        INSERT INTO cpu_benchmarks (cpu_id, benchmark_id, score, source)
                        VALUES (%s, 2, %s, 'kaggle')
                        ON DUPLICATE KEY UPDATE score = VALUES(score)
                    """, (cpu_id, float(row['cinebench_multi'])))
                
                if pd.notna(row.get('cinebench_single')):
                    cursor.execute("""
                        INSERT INTO cpu_benchmarks (cpu_id, benchmark_id, score, source)
                        VALUES (%s, 1, %s, 'kaggle')
                        ON DUPLICATE KEY UPDATE score = VALUES(score)
                    """, (cpu_id, float(row['cinebench_single'])))
                
                # Commit in batches for better performance
                if (idx + 1) % batch_size == 0:
                    conn.commit()
                    print(f"  ✅ Imported {idx + 1}/{len(df)} CPUs...")
                    
            except Exception as e:
                errors += 1
                if errors <= 5:  # Only show first 5 errors
                    print(f"  ⚠️ Error on row {idx}: {str(e)[:100]}")
        
        conn.commit()
        conn.close()
        
        print(f"\n✅ Import complete!")
        print(f"   New CPUs: {imported}")
        print(f"   Updated: {updated}")
        print(f"   Errors: {errors}")
        
    except Exception as e:
        print(f"❌ MySQL error: {e}")
        import traceback
        traceback.print_exc()
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 FINAL SUMMARY")
    print("=" * 80)
    print(f"Total CPUs: {len(df)}")
    print(f"With PassMark: {df['passmark_multi'].notna().sum()}")
    print(f"With Cinebench: {df['cinebench_multi'].notna().sum()}")
    print(f"With cores: {df['cores'].notna().sum()}")
    print(f"With TDP: {df['tdp'].notna().sum()}")
    print("=" * 80)

if __name__ == '__main__':
    main()
