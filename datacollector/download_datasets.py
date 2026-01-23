"""
Download CPU datasets from various sources.
Run this first to fetch all data sources.
"""
import urllib.request
import os
import json

# Create data directory
os.makedirs('data_sources', exist_ok=True)

print("=" * 80)
print("📥 CPU DATASET DOWNLOADER")
print("=" * 80)

# Download GitHub CPU Specs JSON
print("\n1️⃣ Downloading GitHub CPU Specs JSON...")
github_url = "https://raw.githubusercontent.com/LiamOsler/CPU-Specs-Website/master/data/specs/combined.json"
try:
    urllib.request.urlretrieve(github_url, 'data_sources/github_cpu_specs.json')
    print("✅ Downloaded: github_cpu_specs.json")
    
    # Check file
    with open('data_sources/github_cpu_specs.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        print(f"   📊 Contains {len(data)} CPUs")
except Exception as e:
    print(f"❌ Error downloading GitHub data: {e}")

print("\n" + "=" * 80)
print("📝 MANUAL DOWNLOADS REQUIRED (Kaggle)")
print("=" * 80)
print("""
Kaggle requires authentication. Please download these files manually:

2️⃣ CPU Benchmarks Dataset:
   URL: https://www.kaggle.com/datasets/alanjo/cpu-benchmarks
   Files to download:
   - CPU_benchmark_v4.csv
   - CPU_r23_v2.csv
   
   Save to: data_sources/

3️⃣ Intel & AMD Processor Specs:
   URL: https://www.kaggle.com/datasets/alanjo/amd-processor-specifications
   Files to download:
   - AMDfullspecs_adjusted.csv
   - INTELpartialspecs_adjusted.csv
   
   Save to: data_sources/

Instructions:
1. Go to each URL above
2. Click "Download" button (or download individual files)
3. Save CSV files to the 'data_sources' folder
4. Run this script again to verify

Or use Kaggle API:
   pip install kaggle
   kaggle datasets download -d alanjo/cpu-benchmarks -p data_sources --unzip
   kaggle datasets download -d alanjo/amd-processor-specifications -p data_sources --unzip
""")

# Check if files exist
print("\n" + "=" * 80)
print("🔍 CHECKING DOWNLOADED FILES")
print("=" * 80)

required_files = [
    'data_sources/github_cpu_specs.json',
    'data_sources/CPU_benchmark_v4.csv',
    'data_sources/CPU_r23_v2.csv',
    'data_sources/AMDfullspecs_adjusted.csv',
    'data_sources/INTELpartialspecs_adjusted.csv'
]

all_present = True
for file in required_files:
    exists = os.path.exists(file)
    status = "✅" if exists else "❌"
    size = f"({os.path.getsize(file) / 1024:.1f} KB)" if exists else ""
    print(f"{status} {file} {size}")
    if not exists:
        all_present = False

if all_present:
    print("\n🎉 All files downloaded! Ready to run merge_datasets.py")
else:
    print("\n⚠️ Some files missing. Please download manually from Kaggle.")

print("=" * 80)
