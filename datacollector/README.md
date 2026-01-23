# CPU Data Management

Tools for downloading, merging, and importing CPU data from curated datasets into HardWizChippy (Spec-I).

## 📊 Current Database

- **Total CPUs:** 10,306
- **Manufacturers:** Intel (4,755), AMD (3,935)
- **Benchmark Coverage:** 5,037 CPUs (49%)
- **Benchmarks:** PassMark, Cinebench R23, Geekbench 6

## 🚀 Quick Start

### Initial Setup (One-time)

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Set up Kaggle API** (if not done):
   - Visit https://www.kaggle.com/settings
   - Create API token
   - Place credentials in `~/.kaggle/kaggle.json`

### Download & Import Data

```bash
# Download datasets (auto + manual instructions)
python download_datasets.py

# Manually download Kaggle files when prompted, then:
python merge_datasets_v2.py
```

This will:
- Download GitHub CPU specs
- Guide you to download Kaggle datasets
- Merge all sources
- Import 7,500+ CPUs to MySQL
- Takes ~5 minutes total

## 📁 Files

### Active Tools
- **merge_datasets_v2.py** - Main merger (downloads + imports)
- **download_datasets.py** - Downloads GitHub JSON
- **download_kaggle_manual.py** - Manual download instructions
- **import_to_mysql.py** - Direct MySQL importer (if needed)
- **analyze_quality.py** - Database quality analyzer

### Data Files
- **data_sources/** - Downloaded datasets
- **merged_cpu_data.csv** - Final merged dataset (7,499 CPUs)

### Documentation
- **DATASET_MERGE_REPORT.md** - Complete project report

## 📦 Data Sources

1. **Kaggle CPU Benchmarks** - PassMark scores (3,825 CPUs)
2. **Kaggle Cinebench R23** - R23 scores (215 CPUs)
3. **Kaggle AMD Specs** - AMD specifications (582 CPUs)
4. **Kaggle Intel Specs** - Intel specifications (2,880 CPUs)
5. **GitHub CPU-Specs** - Community specs (1,045 CPUs)

All datasets are publicly available under CC0-1.0 or MIT licenses.

## 🔄 Updating Data

To refresh the database with new data:

```bash
# Re-download datasets
python download_datasets.py

# Re-run merger (will update existing CPUs)
python merge_datasets_v2.py
```

## 🛠️ Database Schema

The merger works with the existing HardWizChip schema:

```sql
cpus (name, manufacturer_id, cores, threads, tdp, base_clock, boost_clock)
cpu_benchmarks (cpu_id, benchmark_id, score)
benchmarks (id, name)
```

Benchmark IDs:
- 1: Cinebench R23 Single
- 2: Cinebench R23 Multi
- 3: Geekbench 6 Single
- 4: Geekbench 6 Multi
- 5: PassMark Single
- 6: PassMark Multi

## 📈 Quality Metrics

Run analysis:
```bash
python analyze_quality.py
```

Current coverage:
- Cores: 77.2%
- TDP: 45.5%
- Threads: 10.9%
- Clock speeds: 15.4% (base), 10.5% (boost)

## 🎯 For Production (Spec-I)

The database is ready for your Flutter app. All data is imported and validated with zero errors.

To use in Flutter:
1. Ensure MySQL is running (Laragon)
2. Connect using existing database configuration
3. Query `cpus` and `cpu_benchmarks` tables

---

**Project:** HardWizChippy (Spec-I for Play Store)  
**Last Updated:** January 23, 2026  
**Database Status:** ✅ Production Ready
