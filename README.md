# Argus API — Municipal Open Data Platform

[![Python](https://img.shields.io/badge/Python-3.13-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.1-black.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A unified Flask API product and developer platform that standardizes and serves municipal open government data across four major US cities:
- **Las Vegas, NV** (ArcGIS REST FeatureServers — Clark County / City of Las Vegas)
- **Los Angeles, CA** (Socrata SODA REST API — DataLA)
- **Seattle, WA** (Socrata SODA REST API — Seattle Open Data)
- **Phoenix, AZ** (CKAN Datastore REST API — Phoenix Open Data)

---

## Key Features

1. **Normalized Data Schemas**: Eliminates schema discrepancies between Socrata, CKAN, and ArcGIS portals. All endpoints output standardized JSON envelopes for:
   - **Public Safety & Emergency Incidents** (`/api/v1/incidents`)
   - **Building & Construction Permits** (`/api/v1/permits`)
   - **Commercial Registrations & Business Licenses** (`/api/v1/businesses`)
   - **Cross-City Analytics & Benchmarking** (`/api/v1/analytics/summary`)
2. **Interactive Developer Web Portal**:
   - Live API Playground with real-time JSON syntax highlighting.
   - 1-click code snippet generators for cURL, Python `requests`, and JavaScript `fetch`.
   - Live System Status monitor with ping latency tracking to all 4 municipal data portals.
   - Self-service API Key generation and verification.
3. **Enterprise API Gateway Features**:
   - **Authentication**: Key-based (`X-API-Key`) with tiered permissions (`Free`, `Developer`, `Enterprise`).
   - **Sliding-Window Rate Limiting**: Injects standard RFC rate limit headers (`X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`).
   - **In-Memory TTL Caching**: Sub-20ms response times for repeated queries with cache hit/miss metrics.
   - **High-Availability Fallback**: Automatic resilience fallback if an upstream city portal undergoes downtime.

---

## Quick Start

### 1. Environment Setup

```powershell
# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Run Application

#### Development Server:
```powershell
python run.py
```

#### Production Multi-Threaded WSGI Server (Waitress):
```powershell
python run_prod.py
```
Waitress launches with 8 worker threads, socket backlog of 500, baseline cache warming on startup, and atomic rate limiting.

Visit the Stripe-Inspired Platform & Dashboard at:
- **Stripe Landing Platform**: [http://127.0.0.1:5000/](http://127.0.0.1:5000/) (Radiant gradient mesh, split-screen code console)
- **Stripe Developer Dashboard**: [http://127.0.0.1:5000/dashboard](http://127.0.0.1:5000/dashboard) (Overview, KPIs, live activity stream)
- **Stripe Request Inspector (Logs)**: [http://127.0.0.1:5000/dashboard/logs](http://127.0.0.1:5000/dashboard/logs) (Click-to-inspect drawer for headers & JSON)
- **Stripe Workbench / Shell**: [http://127.0.0.1:5000/dashboard/workbench](http://127.0.0.1:5000/dashboard/workbench) (Live interactive query runner)
- **Stripe API Keys & Quota Center**: [http://127.0.0.1:5000/dashboard/keys](http://127.0.0.1:5000/dashboard/keys) (Token reveal/hide, quota consumption meters)
- **Stripe 3-Column API Reference & Auto-Docs**: [http://127.0.0.1:5000/docs](http://127.0.0.1:5000/docs) (Sticky navigation, real-time authenticated key injection)
- **City Connectors Health Matrix**: [http://127.0.0.1:5000/status](http://127.0.0.1:5000/status) (Real-time latency monitor)

### 3. User Authentication & Developer Credentials

The platform includes full user account authentication (integrated with **Supabase Auth** and local password hashing):
- **Sign In**: [http://127.0.0.1:5000/login](http://127.0.0.1:5000/login)
- **Sign Up**: [http://127.0.0.1:5000/signup](http://127.0.0.1:5000/signup) (automatically issues an `argus_` sandbox API key)
- **Auto-Generated Personalized Documentation**: When signed in, `/docs` dynamically injects the user's live API key and personalized code snippets.
- **Pre-Configured Demo Developer Account**:
  - **Email**: `developer@argus.dev` (or legacy `developer@civicpulse.dev`)
  - **Password**: `Password123!`
  - Includes a 1-click **⚡ Fill Demo** button on the sign-in page.

### 4. Pre-Configured Demo API Keys

For direct machine-to-machine testing via cURL or SDKs, the following sandbox keys are pre-seeded:
- Free Tier (30 req/min): `argus_demo_free_key_2026` / `civic_demo_free_key_2026`
- Developer Pro (120 req/min): `argus_demo_pro_key_2026` / `civic_demo_pro_key_2026`
- Enterprise (600 req/min): `argus_demo_enterprise_key_2026` / `civic_demo_enterprise_key_2026`

---

## API Endpoints Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/incidents` | Public safety and emergency calls across cities or single city |
| `GET` | `/api/v1/permits` | Commercial & residential building permits |
| `GET` | `/api/v1/businesses` | Active business licenses and NAICS categories |
| `GET` | `/api/v1/cities` | Supported municipal portals, connector health & latencies |
| `GET` | `/api/v1/cities/<city_id>` | Detailed metadata for a single municipality |
| `GET` | `/api/v1/analytics/summary` | Cross-city aggregates and comparative metrics |
| `GET` | `/api/v1/jobs` | List state machine pipeline jobs |
| `POST` | `/api/v1/jobs` | Create multi-city asynchronous data pipeline job |
| `GET` | `/api/v1/jobs/<id>` | Inspect state machine audit trail and result payload |
| `POST` | `/api/v1/jobs/<id>/submit` | Submit job for validation and worker execution |
| `POST` | `/api/v1/jobs/<id>/cancel` | Cancel job and transition to terminal FinalState |
| `GET` | `/api/v1/gov/connectors` | List all 6 GovApiConnectors (Census, BLS, BEA, Treasury, FEC, USAspending) |
| `GET` | `/api/v1/gov/<connector>` | Query specific GovApiConnector data and regional indicators |
| `GET` | `/api/v1/gov/analytics/econ` | Data Management Cluster: EconAnalyzer parity benchmarks |
| `GET` | `/api/v1/gov/analytics/policy`| Data Management Cluster: PolicyAnalyzer federal funding density |
| `GET` | `/api/v1/gov/charts/economic`| Downstream VisualizationService Chart.js payloads |
| `POST` | `/api/v1/keys` | Self-service API Key generation |
| `POST` | `/api/v1/keys/generate` | API Key generation alias |
| `GET` | `/api/v1/keys/verify` | Inspect key tier and quota status |
| `GET` | `/api/v1/health` | System health check and cache hit-ratio telemetry |

---

## Example Requests

### Single-City Query (Las Vegas):
```bash
curl -X GET "http://127.0.0.1:5000/api/v1/incidents?city=las_vegas&limit=5" \
  -H "X-API-Key: argus_demo_free_key_2026"
```

### Multi-City Concurrent Query (All 4 Cities):
```bash
curl -X GET "http://127.0.0.1:5000/api/v1/incidents?city=all&category=Property+Crime&limit=10" \
  -H "X-API-Key: argus_demo_free_key_2026"
```

### Python SDK Example:
```python
import requests

url = "http://127.0.0.1:5000/api/v1/incidents"
headers = {
    "X-API-Key": "argus_demo_free_key_2026"
}
params = {
    "city": "seattle",
    "category": "Property Crime",
    "limit": 5
}

response = requests.get(url, headers=headers, params=params)
print(response.json())
```

---

## Automated Testing Suite

The repository features comprehensive automated test coverage (31 passing tests):

```powershell
# Run the entire test suite
.venv\Scripts\python -m pytest tests/ -v

# Run performance benchmarks only
.venv\Scripts\python -m pytest tests/test_performance.py -v -s

# Run end-to-end user journey test only
.venv\Scripts\python -m pytest tests/test_user_journey.py -v -s
```

### Performance Benchmark Highlights:
- **Cache Hit Latency**: ~1.53 ms average response time.
- **Parallel Multi-City Aggregation**: Concurrently fetches Las Vegas, LA, Seattle, and Phoenix in ~1.5 seconds without sequential compounding latency.
- **Atomic Rate Limiting**: Over 1,000 atomic token checks in ~14 ms.
- **High Concurrency**: 100% 200 OK across high multi-threaded concurrent requests with thread-safe LRU eviction.
