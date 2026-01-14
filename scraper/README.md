# HardWizChippy CPU Scraper

Scripts to populate your database with CPU data from TechPowerUp.

## Prerequisites

1. **Python 3.8+** installed
2. **Laragon running** with MySQL
3. **Database created** - Run the schema.sql first:
   ```sql
   mysql -u kbitboy -pdanieyl < ../database/schema.sql
   ```

## Setup

```bash
cd scraper
pip install -r requirements.txt
```

## Scripts

### Quick Scrape (Recommended First)
Fast scrape from list pages - gets basic specs for ~4000+ CPUs in ~5 minutes.

```bash
python quick_scrape.py
```

**Gets:** Name, Codename, Cores, Clock Speeds, Socket, Process, L3 Cache, TDP, Launch Date

### Full Scrape
Detailed scrape visiting each CPU's page - gets ALL specs but takes 2-3 hours.

```bash
python scrape_techpowerup.py
```

**Gets:** Everything from quick scrape PLUS L1/L2 Cache, Memory Support, PCIe, Transistors, Die Size, Launch Price, etc.

## Output

Both scripts:
1. Insert data into your MySQL database (`hardwizchippy`)
2. Export a `cpu_database.json` file for offline Flutter use

## Tips

- Run `quick_scrape.py` first to see immediate results in your app
- Run `scrape_techpowerup.py` later/overnight for complete data
- The scripts use `ON DUPLICATE KEY UPDATE` so you can run them multiple times safely

## Troubleshooting

**"Database connection failed"**
- Make sure Laragon is running
- Check your MySQL credentials in the script

**"No CPUs found"**
- Check your internet connection
- TechPowerUp might be temporarily blocking - wait and try again
