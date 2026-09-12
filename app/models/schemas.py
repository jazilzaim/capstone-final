from dataclasses import dataclass, asdict, field
from typing import Optional, Dict, Any, List

@dataclass
class Location:
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    neighborhood_or_district: Optional[str] = None
    zip_code: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class PublicSafetyIncident:
    """Normalized incident model across all 4 cities."""
    id: str
    city: str                          # los_angeles, seattle, las_vegas, phoenix
    city_name: str                     # e.g. "Los Angeles, CA"
    source_system: str                 # e.g. "DataLA SODA"
    incident_type: str                 # e.g. "BURGLARY", "THEFT", "ASSAULT"
    category: str                      # Standardized: Violent Crime, Property Crime, Traffic, Disorder, Service Call
    description: str                   # Detailed narrative or offense description
    occurred_at: Optional[str]         # ISO 8601 string e.g. "2026-03-01T14:30:00Z"
    location: Location
    status: Optional[str] = "Reported" # e.g. "Active", "Closed", "Report Filed"
    raw_id: Optional[str] = None       # Original municipal ID (e.g. dr_no, Event_Number)
    extra_attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["location"] = self.location.to_dict()
        return d

@dataclass
class BuildingPermit:
    """Normalized building & construction permit model."""
    id: str
    city: str
    city_name: str
    source_system: str
    permit_number: str
    permit_type: str                   # e.g. "Commercial Alteration", "New Construction", "Demolition"
    description: str
    status: str                        # e.g. "Issued", "In Review", "Expired", "Completed"
    applied_date: Optional[str] = None
    issued_date: Optional[str] = None
    valuation_usd: Optional[float] = None
    housing_units: Optional[int] = None
    contractor_or_applicant: Optional[str] = None
    location: Optional[Location] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if self.location:
            d["location"] = self.location.to_dict()
        return d

@dataclass
class CommercialBusiness:
    """Normalized commercial entity & business license model."""
    id: str
    city: str
    city_name: str
    business_name: str
    primary_category: str              # e.g. "Food Services", "Retail Trade", "Professional Services"
    naics_code: Optional[str] = None
    license_number: Optional[str] = None
    status: str = "Active"             # "Active", "Pending", "Expired"
    start_date: Optional[str] = None
    location: Optional[Location] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if self.location:
            d["location"] = self.location.to_dict()
        return d

@dataclass
class CityInfo:
    """Metadata and operational status for a municipal connector."""
    city_id: str
    name: str
    state: str
    timezone: str
    portal_type: str
    portal_url: str
    documentation_url: str
    supported_endpoints: List[str]
    status: str                        # "online", "degraded", "offline"
    latency_ms: float
    record_count_estimate: str
    last_synced_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
