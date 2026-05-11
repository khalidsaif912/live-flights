# ✈️ Muscat Airport Flights Manager

Automated system for fetching and managing departure flights from Muscat International Airport (MCT).

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt

# Optional but recommended (improves success rate)
pip install playwright
playwright install chromium
```

### 2. Run Setup

```bash
python setup.py
```

### 3. Start Collecting Data

```bash
# One-time run
python flight_manager.py

# Continuous auto-update (every 30 minutes)
python auto_update.py
```

## 📂 Output Files

After running, you'll get:

```
flight_data/
├── live_flights.json          # Flights departing in next 24 hours
├── archive_flights.json       # Complete historical archive
├── live_flights.xlsx          # Excel format (live)
├── archive_flights.xlsx       # Excel format (archive)
└── metadata.json             # Last update info
```

## 🔑 Key Features

### 1. **Two-File System**

- **Live Flights** (`live_flights.json`): Only flights departing in the next 24 hours
  - Completely replaced on each update
  - Perfect for real-time monitoring

- **Archive** (`archive_flights.json`): All flights ever collected
  - Smart merge: updates existing, adds new, keeps history
  - No duplicates
  - Preserves `firstSeen` timestamp
  - Updates `lastUpdated` timestamp

### 2. **Smart Deduplication**

Flights are identified by: `Flight Code + Date + Destination + Scheduled Time`

```
Example:
WY101 | 9MAY | LHR | 2026-05-09T14:15  ← Unique key

If this flight appears again with status change:
Old: status="Scheduled"
New: status="Boarding"
→ Archive updates the record, preserves firstSeen
```

### 3. **Multi-Format Export**

- JSON (machine-readable)
- Excel (human-readable, formatted)

## 📊 Data Structure

```json
{
  "code": "WY101",              // Flight number
  "date": "9MAY",               // Date in short format
  "airline": "Oman Air",        // Carrier
  "destination": "LHR",         // IATA code
  "sourceDestination": "London Heathrow",  // Full name
  "stdEtd": "1415/1430",       // Scheduled/Estimated time
  "status": "Boarding",         // Current status
  "scheduledAt": "2026-05-09T14:15:00+04:00",  // ISO format
  "estimatedAt": "2026-05-09T14:30:00+04:00",
  "gate": "B12",
  "terminal": "1",
  "firstSeen": "2026-05-01T08:00:00Z",      // Never changes
  "lastUpdated": "2026-05-09T12:30:00Z"     // Updates each run
}
```

## ⏰ Scheduling

### Linux/macOS (Cron)

```bash
chmod +x setup_cron.sh
./setup_cron.sh
```

Or manually:
```bash
crontab -e
# Add: */30 * * * * cd /path/to/project && python3 flight_manager.py
```

### Windows (Task Scheduler)

Run PowerShell as Administrator:
```powershell
.\setup_windows_task.ps1
```

Or use GUI: `taskschd.msc`

## 📈 Analytics

```bash
# Full analysis report
python analyze_flights.py

# Filter by destination
python analyze_flights.py --destination LHR

# Filter by airline
python analyze_flights.py --airline "Oman Air"

# Export to CSV
python analyze_flights.py --export-csv
```

## 🔧 Configuration

Edit `config.ini` to customize:
- Update intervals
- File paths
- Time filters
- Destination aliases
- And more...

## 🛠️ Troubleshooting

### No flights fetched?

1. Install Playwright:
   ```bash
   pip install playwright
   playwright install chromium
   ```

2. Check internet connection

3. Try manual run to see errors:
   ```bash
   python flight_manager.py
   ```

### Excel not created?

```bash
pip install openpyxl
```

## 📝 Example Use Cases

### 1. Track Specific Destination

```python
import json

with open("flight_data/archive_flights.json") as f:
    flights = json.load(f)

london_flights = [f for f in flights if f["destination"] == "LHR"]
print(f"Total flights to London: {len(london_flights)}")
```

### 2. Analyze Delays

```python
from datetime import datetime

delays = []
for f in flights:
    if f["scheduledAt"] and f["estimatedAt"]:
        sched = datetime.fromisoformat(f["scheduledAt"])
        estim = datetime.fromisoformat(f["estimatedAt"])
        delay = (estim - sched).total_seconds() / 60
        delays.append(delay)

avg_delay = sum(delays) / len(delays)
print(f"Average delay: {avg_delay:.1f} minutes")
```

### 3. Export to CSV with Pandas

```python
import pandas as pd

df = pd.read_json("flight_data/archive_flights.json")
df.to_csv("flight_data/flights.csv", index=False)
```

## 🔐 Privacy & Security

- ✅ All data is public from official airport website
- ✅ No personal data collected
- ✅ No login/API keys required
- ✅ Data stored locally only

## 📚 File Descriptions

| File | Purpose | Update Method |
|------|---------|---------------|
| `live_flights.json` | Current flights (24h) | Complete replacement |
| `archive_flights.json` | All historical flights | Smart merge |
| `*.xlsx` | Excel formatted data | Regenerated each run |
| `metadata.json` | Update status info | Overwritten |

## 🎯 System Architecture

```
┌─────────────────────────────────────┐
│  Muscat Airport Website             │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│  Fetch Strategies:                  │
│  1. CloudScraper (bypass CF)        │
│  2. Standard Requests               │
│  3. Playwright (real browser)       │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│  Parse HTML → Extract Flights       │
└─────────────────────────────────────┘
              ↓
        ┌─────┴─────┐
        ↓           ↓
┌─────────────┐  ┌──────────────────┐
│ Filter 24h  │  │  All Flights     │
└─────────────┘  └──────────────────┘
        ↓                 ↓
┌─────────────┐  ┌──────────────────┐
│live_flights │  │ Merge Archive    │
│   .json     │  │ (smart update)   │
└─────────────┘  └──────────────────┘
        ↓                 ↓
┌─────────────┐  ┌──────────────────┐
│live_flights │  │archive_flights   │
│   .xlsx     │  │     .json        │
└─────────────┘  └──────────────────┘
                          ↓
                 ┌──────────────────┐
                 │archive_flights   │
                 │     .xlsx        │
                 └──────────────────┘
```

## 📄 License

For personal and educational use.

## 🆘 Support

1. Check the troubleshooting section
2. Review log files in `logs/`
3. Ensure all dependencies are installed

---

**Happy Flight Tracking! ✈️**
