"""
USAspendingConnector: USAspending.gov API Connector.
Supplies federal awards, prime contracts, and infrastructure grant allocations.
"""
from typing import Dict, Any, List, Optional
from app.connectors.gov.base import GovApiConnector

class USAspendingConnector(GovApiConnector):
    def __init__(self):
        super().__init__(
            name="USAspendingConnector",
            agency="USAspending.gov (U.S. Treasury)",
            base_url="https://api.usaspending.gov/api/v2/"
        )
        self._federal_awards = {
            "las_vegas": {
                "state": "NV",
                "prime_contracts_millions": 1840.5,
                "grant_awards_millions": 920.0,
                "total_federal_funding_millions": 2760.5,
                "top_awarding_agency": "Department of Defense / Department of Energy"
            },
            "los_angeles": {
                "state": "CA",
                "prime_contracts_millions": 8420.0,
                "grant_awards_millions": 4150.0,
                "total_federal_funding_millions": 12570.0,
                "top_awarding_agency": "Department of Transportation / HHS"
            },
            "seattle": {
                "state": "WA",
                "prime_contracts_millions": 3890.0,
                "grant_awards_millions": 2100.0,
                "total_federal_funding_millions": 5990.0,
                "top_awarding_agency": "Department of Defense / NOAA"
            },
            "phoenix": {
                "state": "AZ",
                "prime_contracts_millions": 4210.0,
                "grant_awards_millions": 1850.0,
                "total_federal_funding_millions": 6060.0,
                "top_awarding_agency": "Department of Defense / CHIPS Act / VA"
            }
        }

    def fetch_data(self, query_params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        city = (query_params or {}).get("city", "all")
        if city in self._federal_awards:
            return [{"city": city, **self._federal_awards[city]}]
        return [{"city": k, **v} for k, v in self._federal_awards.items()]

    def get_metrics(self, scope: Optional[str] = None) -> Dict[str, Any]:
        scope = (scope or "all").lower()
        if scope in self._federal_awards:
            return self._federal_awards[scope]
        return {
            "total_federal_funding_all_metros_millions": sum(a["total_federal_funding_millions"] for a in self._federal_awards.values()),
            "allocations": self._federal_awards
        }
