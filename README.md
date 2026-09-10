> **DISCLAIMER:** This is an educational/student project built for learning cybersecurity concepts only. It is **not** intended for production security use. All IOC (Indicator of Compromise) data is fake/test data using RFC 5737 documentation-reserved IP ranges and synthetic examples. This tool must **never** be used to scan, monitor, or analyze real systems without explicit authorization. The author assumes no responsibility for misuse.

# SentinelAI - Offline SOC Dashboard

SentinelAI is a fully offline Security Operations Center (SOC) web application for analyzing logs, detecting threats, scanning for Indicators of Compromise (IOCs), and managing security investigations. Built for education and demonstration - no cloud services, no API keys, and no internet required at runtime.

## Features

- **Security Dashboard** - Real-time metrics, threat trend charts, severity distribution
- **Log Analyzer** - Upload or select bundled sample logs, parse and display results with alert generation
- **Rule-Based Threat Detection** - 9 detection rules (R001-R009) covering brute force, privilege escalation, suspicious processes, IOC matches, anomalous hours, and more
- **IOC Scanner** - Scan any text for IP addresses, domains, URLs, and file hashes; match against the local IOC database
- **Hash Analyzer** - Compute MD5, SHA-1, SHA-256, SHA-512 for uploaded files and check against the IOC database
- **Investigations** - Create cases, attach alerts, add evidence, write notes, and track a timeline
- **Reports** - Generate PDF, JSON, or CSV reports for investigations or individual alerts

## Offline / Privacy

- Completely offline at runtime - no API keys, no cloud services, no AI/LLM required
- All data stored locally in a single SQLite database (`backend/data/sentinel.db`)
- Binds to localhost only (127.0.0.1), no external network access
- Log files are parsed only, never executed

## Prerequisites

| Software | Version | Notes |
|----------|---------|-------|
| Python | 3.10 or newer | `python --version` to verify |
| Node.js | 18 LTS or newer | Includes `npm` - `node --version` to verify |

## Quick Start (Clone and Run)

```bash
# Clone
git clone <your-repo-url>
cd SentinelAI

# Install backend
cd backend
pip install -r requirements.txt
python seed_data.py

# Install frontend
cd ../frontend
npm install

# Run (see platform-specific instructions below)
```

## Installation

### Windows

```powershell
# Clone
git clone <your-repo-url>
cd SentinelAI

# Backend
cd backend
pip install -r requirements.txt
python seed_data.py

# Frontend
cd ..\frontend
npm install
```

### Linux / macOS

```bash
# Clone
git clone <your-repo-url>
cd SentinelAI

# Backend
cd backend
pip3 install -r requirements.txt
python3 seed_data.py

# Frontend
cd ../frontend
npm install
```

## Launch

### Windows

**Option A - Double-click launcher:**

Run `LAUNCH_SENTINELAI.bat` in the project root. It opens two terminal windows (backend + frontend) and launches the dashboard in your browser.

To stop, run `STOP_SENTINELAI.bat`.

**Option B - Manual launch:**

Open two terminal windows:

**Terminal 1 - Backend:**
```powershell
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

**Terminal 2 - Frontend:**
```powershell
cd frontend
npm run dev
```

### Linux / macOS

**Option A - Shell scripts:**

```bash
chmod +x launch_sentinelai.sh stop_sentinelai.sh
./launch_sentinelai.sh
```

To stop:
```bash
./stop_sentinelai.sh
```

**Option B - Manual launch:**

Open two terminal windows:

**Terminal 1 - Backend:**
```bash
cd backend
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

## Local URLs

| Service | URL |
|---------|-----|
| Frontend Dashboard | http://localhost:5173/dashboard |
| Frontend Home | http://localhost:5173 |
| Backend API Docs (Swagger) | http://127.0.0.1:8000/docs |
| Backend Health Check | http://127.0.0.1:8000/health |

## Supported Upload Formats

| Format | Extension | Description |
|--------|-----------|-------------|
| Plain text logs | `.log`, `.txt` | SSH, syslog, Apache, Windows, or generic formats |
| JSON logs | `.json` | One JSON object per line or array of events |
| CSV logs | `.csv` | Comma-separated with headers |

**Safety note:** Uploaded files are read and parsed in memory only. No file is executed, and no code from uploads is run.

## Bundled Sample Logs

Four sample log files are included in `backend/data/sample_logs/`:

| File | Description |
|------|-------------|
| `auth_sample.log` | SSH authentication logs with brute-force scenarios |
| `syslog_sample.log` | System logs with privilege escalation and suspicious process events |
| `web_sample.log` | Apache access logs with web scanning and attack patterns |
| `demo_rules.log` | Multi-format logs triggering rules R005 and R008 |

These can be selected directly from the Log Analyzer page without uploading.

## Architecture

```
SentinelAI/
├── backend/
│   ├── app/
│   │   ├── api/routes/     # FastAPI route handlers (dashboard, logs, IOC, hash, investigations, reports)
│   │   ├── core/           # Config, database, security utilities
│   │   ├── models/         # SQLAlchemy ORM models
│   │   ├── schemas/        # Pydantic request/response schemas
│   │   └── services/       # Analysis engine, log parser, IOC extractor, report generator
│   ├── data/               # SQLite database + sample log files
│   ├── seed_data.py        # Seeds demo IOC records (15 indicators)
│   └── requirements.txt    # Python dependencies
└── frontend/
    ├── src/
    │   ├── pages/          # React page components (Dashboard, LogAnalyzer, IOCScanner, etc.)
    │   ├── services/       # API client functions
    │   ├── styles/         # Tailwind CSS
    │   └── types/          # TypeScript interfaces
    ├── package.json        # Node.js dependencies
    └── vite.config.ts      # Vite dev server with API proxy
```

## Detection Rules

| Rule | Name | Trigger |
|------|------|---------|
| R001 | Repeated Failed Logins | 5+ failed logins from same IP within 15 minutes |
| R002 | Brute Force Attack | 10+ attempts from same IP within 5 minutes |
| R003 | Suspicious IP Login | Login from IP found in the IOC database |
| R004 | Privilege Escalation | Keywords like `sudo`, `su root`, `runas` in logs |
| R005 | Suspicious Process | Known malicious process names in logs |
| R006 | IOC Match | Any IOC value (IP, domain, hash) matched in log content |
| R007 | Anomalous Time | Activity outside business hours (before 8 AM or after 6 PM) |
| R008 | Multiple Account Access | 5+ different accounts accessed from same source within 10 minutes |
| R009 | Log Clearing | Log deletion or clearing commands detected |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/api/dashboard/stats` | Dashboard statistics |
| GET | `/api/dashboard/recent-alerts` | Recent alerts list |
| GET | `/api/dashboard/trends` | Threat trend data |
| GET | `/api/dashboard/severity-distribution` | Severity breakdown |
| GET | `/api/logs/sample` | List bundled sample logs |
| POST | `/api/logs/parse-sample/{filename}` | Parse a sample log |
| POST | `/api/logs/upload` | Upload and parse a log file |
| GET | `/api/logs/parse-result/{job_id}` | Get parse job result |
| POST | `/api/ioc/scan` | Scan text for IOCs |
| GET | `/api/ioc/database` | List IOCs in database |
| POST | `/api/ioc/database` | Add a new IOC |
| DELETE | `/api/ioc/database/{id}` | Remove an IOC |
| GET | `/api/ioc/stats` | IOC database statistics |
| POST | `/api/hash/analyze` | Analyze file hashes |
| GET | `/api/investigations` | List investigations |
| POST | `/api/investigations` | Create investigation |
| PATCH | `/api/investigations/{id}` | Update investigation |
| DELETE | `/api/investigations/{id}` | Delete investigation |
| GET | `/api/reports` | List generated reports |
| POST | `/api/reports/generate` | Generate a report |

## License

MIT License - see [LICENSE](LICENSE) for details.
