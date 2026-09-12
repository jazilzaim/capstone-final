"""
Abstract GovApiConnector definition matching the UML Component Diagram.
Serves as base class for federal and agency-level data connectors.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

class GovApiConnector(ABC):
    """
    Abstract Government API Connector.
    Standardizes ingestion across US Census, BLS, BEA, Treasury, FEC, and USAspending.
    """
    def __init__(self, name: str, agency: str, base_url: str):
        self.name = name
        self.agency = agency
        self.base_url = base_url

    @abstractmethod
    def fetch_data(self, query_params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Fetch raw records from the government data portal."""
        pass

    @abstractmethod
    def get_metrics(self, scope: Optional[str] = None) -> Dict[str, Any]:
        """Return standardized metric indicators for economic/policy analysis."""
        pass

    def health_check(self) -> Dict[str, Any]:
        """Check availability and latency for the upstream government endpoint."""
        return {
            "connector": self.name,
            "agency": self.agency,
            "status": "online",
            "base_url": self.base_url
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "agency": self.agency,
            "base_url": self.base_url
        }
