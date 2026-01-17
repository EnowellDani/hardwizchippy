# HardWizChippy - Triple Threat Data Pipeline
## 2-Week Implementation Timeline

---

## 🎯 Project Overview

**Goal:** Build a multi-source data pipeline to populate Laragon MySQL with comprehensive CPU data from:
- **Source A:** TechPowerUp (Nerd Specs: Transistors, Die Size, MCM, Voltage)
- **Source B:** NanoReview (Benchmarks & Gaming FPS)
- **Source C:** Intel ARK / AMD (General Info: Launch Price, Memory Type)

**Focus:** Modern CPUs (2020-2026) first, legacy CPUs skip benchmarks if not found.

---

## 📅 Week 1: Days 1-7 - Data Ingestion & Cleaning

### Days 1-2: Environment Setup & Schema
| Task | Status | Details |
|------|--------|---------|
| ✅ Create v5 Triple-Threat SQL schema | Done | `database/schema_v5_triple_threat.sql` |
| ✅ Create mega_merger.py pipeline | Done | `scraper/mega_merger.py` |
| ✅ Update requirements.txt | Done | Added TheFuzz, Playwright deps |
| ⬜ Set up Laragon MySQL | TODO | Import schema, create user |
| ⬜ Install Python dependencies | TODO | `pip install -r requirements.txt` |
| ⬜ Install Playwright browsers | TODO | `playwright install chromium` |

#### Setup Commands:
```powershell
# Navigate to scraper folder
cd e:\ProgrammingFolder\HardWizChip\hardwizchippy\scraper

# Create virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Import schema to Laragon MySQL
mysql -u root -p < ..\database\schema_v5_triple_threat.sql
```

---

### Days 3-4: NanoReview Scraping (Source B)
| Task | Status | Priority |
|------|--------|----------|
| ⬜ Test NanoReview list scraper | TODO | HIGH |
| ⬜ Test NanoReview detail scraper | TODO | HIGH |
| ⬜ Validate benchmark data extraction | TODO | HIGH |
| ⬜ Validate gaming FPS extraction | TODO | HIGH |
| ⬜ Run initial scrape (200 CPUs) | TODO | HIGH |

#### Commands:
```powershell
# Test run with limited CPUs
python mega_merger.py --max-cpus 10 --verbose

# Full NanoReview scrape
python mega_merger.py --source nanoreview --max-cpus 200
```

---

### Days 5-6: TechPowerUp Matching (Source A)
| Task | Status | Priority |
|------|--------|----------|
| ⬜ Test TechPowerUp search functionality | TODO | HIGH |
| ⬜ Validate fuzzy matching accuracy | TODO | HIGH |
| ⬜ Test nerd specs extraction | TODO | HIGH |
| ⬜ Run TechPowerUp merge pass | TODO | MEDIUM |
| ⬜ Review match scores (>85 threshold) | TODO | MEDIUM |

#### Fuzzy Match Testing:
```python
# Test fuzzy matching in Python REPL
from thefuzz import fuzz, process

query = "Intel Core Ultra 9 285K"
candidates = ["Core Ultra 9 285K", "Intel Core i9-14900K", "AMD Ryzen 9 9950X"]

# Should match "Core Ultra 9 285K" with high score
result = process.extractOne(query, candidates)
print(f"Best match: {result}")
```

---

### Day 7: Intel ARK / AMD Integration (Source C)
| Task | Status | Priority |
|------|--------|----------|
| ⬜ Test Intel ARK scraper | TODO | MEDIUM |
| ⬜ Validate MSRP extraction | TODO | MEDIUM |
| ⬜ Validate memory specs extraction | TODO | MEDIUM |
| ⬜ Add AMD official source (if needed) | TODO | LOW |

---

## 📅 Week 1 Checkpoint (End of Day 7)

### Success Criteria:
- [ ] 200+ modern CPUs in database
- [ ] 80%+ have benchmark data (NanoReview)
- [ ] 60%+ have nerd specs (TechPowerUp)
- [ ] 40%+ Intel CPUs have ARK data
- [ ] No critical errors in scraper logs

### Verification Query:
```sql
-- Check data completeness
SELECT 
    COUNT(*) as total_cpus,
    SUM(CASE WHEN transistors_million IS NOT NULL THEN 1 ELSE 0 END) as has_transistors,
    SUM(CASE WHEN die_size_mm2 IS NOT NULL THEN 1 ELSE 0 END) as has_die_size,
    (SELECT COUNT(*) FROM cpu_benchmarks WHERE cinebench_r23_multi IS NOT NULL) as has_cb23,
    (SELECT COUNT(*) FROM cpu_gaming_aggregate WHERE avg_fps IS NOT NULL) as has_gaming
FROM cpus
WHERE launch_date >= '2020-01-01' OR launch_date IS NULL;
```

---

## 📅 Week 2: Days 8-14 - Cleaning, Export & Flutter Integration

### Days 8-9: Data Cleaning
| Task | Status | Priority |
|------|--------|----------|
| ⬜ Remove duplicate CPUs | TODO | HIGH |
| ⬜ Fix NULL inconsistencies | TODO | HIGH |
| ⬜ Normalize manufacturer names | TODO | MEDIUM |
| ⬜ Validate data ranges (no negative values) | TODO | MEDIUM |
| ⬜ Review fuzzy match cache for errors | TODO | LOW |

#### Cleaning Queries:
```sql
-- Find potential duplicates
SELECT name_normalized, COUNT(*) as cnt 
FROM cpus 
GROUP BY name_normalized 
HAVING cnt > 1;

-- Find suspicious data
SELECT name, transistors_million, die_size_mm2
FROM cpus
WHERE transistors_million < 100 OR transistors_million > 500000
   OR die_size_mm2 < 10 OR die_size_mm2 > 1000;

-- Remove orphan benchmarks
DELETE FROM cpu_benchmarks WHERE cpu_id NOT IN (SELECT id FROM cpus);
```

---

### Days 10-11: JSON Export & Flutter Integration
| Task | Status | Priority |
|------|--------|----------|
| ⬜ Run JSON export | TODO | HIGH |
| ⬜ Validate JSON structure | TODO | HIGH |
| ⬜ Update Flutter cpu.dart model | TODO | HIGH |
| ⬜ Update cpu_list_screen.dart | TODO | HIGH |
| ⬜ Test data loading in app | TODO | HIGH |

#### Export Command:
```powershell
python mega_merger.py --export
# Output: assets/data/cpu_database.json
```

#### Flutter Model Updates Needed:
1. Add new fields to `Cpu` class in `lib/models/cpu.dart`
2. Update `fromJson()` to handle new benchmark structure
3. Add gaming benchmark display to detail screen

---

### Days 12-13: UI Polish
| Task | Status | Priority |
|------|--------|----------|
| ⬜ Add benchmark section to CPU detail | TODO | HIGH |
| ⬜ Add gaming FPS display | TODO | HIGH |
| ⬜ Show/hide sections based on data availability | TODO | HIGH |
| ⬜ Add "Nerd Specs" card (transistors, die size) | TODO | MEDIUM |
| ⬜ Update search to include new fields | TODO | MEDIUM |

#### NULL Fallback Strategy:
```dart
// In cpu_detail_screen.dart
Widget _buildBenchmarkSection(Cpu cpu) {
  // If no benchmarks, hide entire section
  if (cpu.structuredBenchmarks == null || 
      cpu.structuredBenchmarks!.isEmpty) {
    return const SizedBox.shrink();
  }
  
  return BenchmarkCard(benchmarks: cpu.structuredBenchmarks!);
}
```

---

### Day 14: Final Testing & Documentation
| Task | Status | Priority |
|------|--------|----------|
| ⬜ Full end-to-end test | TODO | HIGH |
| ⬜ Performance test (load time) | TODO | MEDIUM |
| ⬜ Document scraper usage | TODO | MEDIUM |
| ⬜ Create backup of database | TODO | LOW |
| ⬜ Plan incremental update strategy | TODO | LOW |

---

## 🛠️ Quick Reference Commands

### Scraper Operations
```powershell
# Full pipeline (scrape + export)
python mega_merger.py --max-cpus 200

# Export only (no scraping)
python mega_merger.py --export

# Verbose mode for debugging
python mega_merger.py --max-cpus 10 --verbose

# View logs
Get-Content mega_merger.log -Tail 50
```

### Database Operations
```sql
-- Quick stats
SELECT 'Total CPUs' as metric, COUNT(*) as value FROM cpus
UNION ALL
SELECT 'With Benchmarks', COUNT(*) FROM cpu_benchmarks
UNION ALL
SELECT 'With Gaming', COUNT(*) FROM cpu_gaming_aggregate;

-- Reset scraper state
UPDATE scraper_state SET status = 'idle', total_cpus_scraped = 0;
```

### Flutter Operations
```powershell
# Rebuild Flutter after JSON update
cd e:\ProgrammingFolder\HardWizChip\hardwizchippy
flutter clean
flutter pub get
flutter run
```

---

## ⚠️ Known Issues & Solutions

| Issue | Solution |
|-------|----------|
| NanoReview blocks scraper | Add longer delays, rotate user agents |
| TechPowerUp fuzzy match fails | Lower threshold to 80, check logs |
| Intel ARK requires login | Skip for now, use cached data |
| JSON too large for Flutter | Paginate or split by manufacturer |

---

## 📊 Success Metrics

| Metric | Target | Actual |
|--------|--------|--------|
| Total Modern CPUs | 200+ | ⬜ |
| Benchmark Coverage | 80%+ | ⬜ |
| Nerd Specs Coverage | 60%+ | ⬜ |
| Gaming FPS Coverage | 50%+ | ⬜ |
| App Load Time | <3s | ⬜ |

---

## 📁 File Structure

```
hardwizchippy/
├── database/
│   ├── schema.sql                    # Original schema
│   └── schema_v5_triple_threat.sql   # NEW: Enhanced schema
├── scraper/
│   ├── cpu_scraper.py               # Original scraper
│   ├── mega_merger.py               # NEW: Triple-threat pipeline
│   ├── requirements.txt             # Updated dependencies
│   └── mega_merger.log              # Pipeline logs
├── assets/
│   └── data/
│       └── cpu_database.json        # Exported data for Flutter
└── lib/
    ├── models/
    │   └── cpu.dart                 # CPU model (needs update)
    └── screens/
        └── cpu_detail_screen.dart   # Detail view (needs update)
```

---

*Last Updated: January 17, 2026*
