"""
Manual Kaggle dataset downloader using direct URLs.
"""
import urllib.request
import os
import zipfile

def download_file(url, filename):
    """Download a file with progress."""
    print(f"📥 Downloading {filename}...")
    try:
        # Set headers to mimic browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        req = urllib.request.Request(url, headers=headers)
        
        with urllib.request.urlopen(req) as response:
            content = response.read()
            
        with open(filename, 'wb') as f:
            f.write(content)
        
        size = len(content) / (1024 * 1024)
        print(f"✅ Downloaded {filename} ({size:.1f} MB)")
        return True
    except Exception as e:
        print(f"❌ Failed to download {filename}: {e}")
        return False

def main():
    os.makedirs('data_sources', exist_ok=True)
    
    print("=" * 80)
    print("📥 KAGGLE DATASET MANUAL DOWNLOADER")
    print("=" * 80)
    print("\n⚠️  Kaggle requires authentication for dataset downloads.")
    print("Please download these files manually:\n")
    
    print("1️⃣ CPU Benchmarks:")
    print("   Visit: https://www.kaggle.com/datasets/alanjo/cpu-benchmarks")
    print("   Click the 'Download' button (requires Kaggle login)")
    print("   Extract these files to data_sources/:")
    print("   - CPU_benchmark_v4.csv")
    print("   - CPU_r23_v2.csv\n")
    
    print("2️⃣ AMD/Intel Specs:")
    print("   Visit: https://www.kaggle.com/datasets/alanjo/amd-processor-specifications")
    print("   Click the 'Download' button (requires Kaggle login)")
    print("   Extract these files to data_sources/:")
    print("   - AMDfullspecs_adjusted.csv")
    print("   - INTELpartialspecs_adjusted.csv\n")
    
    print("=" * 80)
    print("\n📂 Once downloaded, place all CSV files in:")
    print(f"   {os.path.abspath('data_sources')}")
    print("\nThen run: python merge_datasets.py")
    print("=" * 80)
    
    # Check what we have
    print("\n🔍 Checking current files...")
    required = [
        'data_sources/github_cpu_specs.json',
        'data_sources/CPU_benchmark_v4.csv',
        'data_sources/CPU_r23_v2.csv',
        'data_sources/AMDfullspecs_adjusted.csv',
        'data_sources/INTELpartialspecs_adjusted.csv'
    ]
    
    missing = []
    for f in required:
        if os.path.exists(f):
            size = os.path.getsize(f) / 1024
            print(f"✅ {f} ({size:.1f} KB)")
        else:
            print(f"❌ {f}")
            missing.append(f)
    
    if not missing:
        print("\n🎉 All files ready! Run: python merge_datasets.py")
    else:
        print(f"\n⚠️  {len(missing)} file(s) missing. Please download manually.")

if __name__ == '__main__':
    main()
