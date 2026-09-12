import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
# Automatically load .env if present
load_dotenv(BASE_DIR / ".env")

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "argus-secret-key-super-secure-dev")
    ENV = os.environ.get("FLASK_ENV", "development")
    DEBUG = os.environ.get("FLASK_DEBUG", "1") == "1"

    # Supabase Cloud PostgreSQL Configuration
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_KEY = os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_SERVICE_KEY")

    # Local SQLite Fallback Database
    DB_PATH = os.environ.get("ARGUS_DB_PATH") or os.environ.get("CIVICPULSE_DB_PATH") or str(BASE_DIR / "argus.db")

    # Caching configuration
    CACHE_DEFAULT_TTL_SECONDS = int(os.environ.get("CACHE_TTL", "300"))  # 5 minutes
    CACHE_MAX_ENTRIES = int(os.environ.get("CACHE_MAX_ENTRIES", "1000"))

    # Rate Limiting Tiers (requests per window)
    RATE_LIMIT_WINDOW_SECONDS = 60
    TIER_LIMITS = {
        "free": 30,         # 30 req / min
        "developer": 120,   # 120 req / min
        "enterprise": 600,  # 600 req / min
        "internal": 10000   # unlimited / system
    }

    # City Open Data Endpoints & Portal Configs
    CITIES = {
        "los_angeles": {
            "name": "Los Angeles",
            "state": "CA",
            "timezone": "America/Los_Angeles",
            "portal_type": "Socrata SODA",
            "portal_url": "https://data.lacity.org",
            "documentation_url": "https://data.lacity.org",
            "datasets": {
                "crime": "2nrs-mtv8",        # Crime Data from 2020 to Present
                "businesses": "6rrh-rzua",   # Listing of Active Businesses
                "permits": "yv23-gn4r"       # Building and Safety Permits
            },
            "enabled": True
        },
        "seattle": {
            "name": "Seattle",
            "state": "WA",
            "timezone": "America/Los_Angeles",
            "portal_type": "Socrata SODA",
            "portal_url": "https://data.seattle.gov",
            "documentation_url": "https://data.seattle.gov",
            "datasets": {
                "crime": "tazs-3rd5",        # SPD Crime Data: 2008-Present
                "fire_911": "kzjm-xkqj",     # Real Time Fire 911 Calls
                "permits": "76t5-zqzr"       # Building Permits
            },
            "enabled": True
        },
        "las_vegas": {
            "name": "Las Vegas",
            "state": "NV",
            "timezone": "America/Los_Angeles",
            "portal_type": "ArcGIS REST",
            "portal_url": "https://opendata.arcgis.com",
            "documentation_url": "https://opendata.lasvegasnevada.gov",
            "feature_servers": {
                "police_calls": "https://services1.arcgis.com/F1v0ufATbBQScMtY/arcgis/rest/services/MetroCFS_OpenData/FeatureServer/0",
                "expired_permits": "https://services1.arcgis.com/F1v0ufATbBQScMtY/arcgis/rest/services/Expired_Permits/FeatureServer/0"
            },
            "enabled": True
        },
        "phoenix": {
            "name": "Phoenix",
            "state": "AZ",
            "timezone": "America/Phoenix",
            "portal_type": "CKAN Datastore",
            "portal_url": "https://www.phoenixopendata.com",
            "documentation_url": "https://www.phoenixopendata.com",
            "packages": {
                "police_calls": "calls-for-service",
                "fire_calls": "calls-for-service-fire",
                "arrests": "arrests"
            },
            "enabled": True
        }
    }

    # Request timeout for external portals in seconds
    UPSTREAM_TIMEOUT_SECONDS = 5.0
