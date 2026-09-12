import time
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from app.models.schemas import PublicSafetyIncident, BuildingPermit, CommercialBusiness, CityInfo

logger = logging.getLogger(__name__)

class BaseCityConnector(ABC):
    """Abstract Base Class for Municipal Open Data Adapters."""

    def __init__(self, city_id: str, city_name: str, state: str, portal_type: str, portal_url: str):
        self.city_id = city_id
        self.city_name = city_name
        self.state = state
        self.portal_type = portal_type
        self.portal_url = portal_url
        self.last_health_status = "unknown"
        self.last_latency_ms = 0.0

    @abstractmethod
    def fetch_incidents(self, limit: int = 50, offset: int = 0, query: Optional[str] = None, category: Optional[str] = None) -> List[PublicSafetyIncident]:
        """Fetch and normalize public safety / emergency incident records."""
        pass

    @abstractmethod
    def fetch_permits(self, limit: int = 50, offset: int = 0, query: Optional[str] = None) -> List[BuildingPermit]:
        """Fetch and normalize building/construction permits."""
        pass

    @abstractmethod
    def fetch_businesses(self, limit: int = 50, offset: int = 0, query: Optional[str] = None) -> List[CommercialBusiness]:
        """Fetch and normalize registered commercial entities."""
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Test connectivity to the municipal portal and return latency and status."""
        pass

    def get_info(self) -> CityInfo:
        health = self.health_check()
        return CityInfo(
            city_id=self.city_id,
            name=self.city_name,
            state=self.state,
            timezone="America/Los_Angeles" if self.city_id != "phoenix" else "America/Phoenix",
            portal_type=self.portal_type,
            portal_url=self.portal_url,
            documentation_url=self.portal_url,
            supported_endpoints=["/incidents", "/permits", "/businesses"],
            status=health.get("status", "online"),
            latency_ms=health.get("latency_ms", 25.0),
            record_count_estimate=health.get("record_count_estimate", "100,000+"),
            last_synced_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        )

    @staticmethod
    def categorize_crime(raw_desc: str) -> str:
        """Helper to map municipal incident descriptions into standardized categories."""
        desc = (raw_desc or "").upper()
        if any(w in desc for w in ["ASSAULT", "BATTERY", "ROBBERY", "HOMICIDE", "SHOOTING", "WEAPON", "THREAT", "DOMESTIC"]):
            return "Violent Crime"
        if any(w in desc for w in ["BURGLARY", "THEFT", "LARCENY", "STOLEN", "VANDALISM", "VEHICLE", "PROPERTY", "TRESPASS"]):
            return "Property Crime"
        if any(w in desc for w in ["TRAFFIC", "COLLISION", "ACCIDENT", "DUI", "SPEEDING"]):
            return "Traffic"
        if any(w in desc for w in ["DISTURBANCE", "NOISE", "DRUGS", "NARCOTICS", "INTOXICATION", "LOITERING"]):
            return "Public Order"
        if any(w in desc for w in ["FIRE", "ALARM", "EMS", "MEDICAL", "RESCUE", "HAZARD"]):
            return "Emergency Services"
        return "General Service"
