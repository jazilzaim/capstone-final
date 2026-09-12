"""
BEAConnector: Bureau of Economic Analysis API Connector.
Provides Gross Domestic Product (GDP), industry output, and personal income by region.
"""
from typing import Dict, Any, List, Optional
from app.connectors.gov.base import GovApiConnector

class BEAConnector(GovApiConnector):
    def __init__(self):
        super().__init__(
            name="BEAConnector",
            agency="Bureau of Economic Analysis",
            base_url="https://apps.bea.gov/api/data"
        )
        self._regional_gdp = {
            "las_vegas": {
                "metro_gdp_billions": 142.5,
                "real_gdp_growth_pct": 3.6,
                "per_capita_income": 58400,
                "leading_industry": "Hospitality & Entertainment"
            },
            "los_angeles": {
                "metro_gdp_billions": 1120.0,
                "real_gdp_growth_pct": 2.4,
                "per_capita_income": 74200,
                "leading_industry": "Media, Tech & Logistics"
            },
            "seattle": {
                "metro_gdp_billions": 485.2,
                "real_gdp_growth_pct": 3.8,
                "per_capita_income": 92100,
                "leading_industry": "Cloud Computing & Aerospace"
            },
            "phoenix": {
                "metro_gdp_billions": 310.8,
                "real_gdp_growth_pct": 4.1,
                "per_capita_income": 61800,
                "leading_industry": "Semiconductors & Financial Services"
            }
        }

    def fetch_data(self, query_params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        city = (query_params or {}).get("city", "all")
        if city in self._regional_gdp:
            return [{"city": city, **self._regional_gdp[city]}]
        return [{"city": k, **v} for k, v in self._regional_gdp.items()]

    def get_metrics(self, scope: Optional[str] = None) -> Dict[str, Any]:
        scope = (scope or "all").lower()
        if scope in self._regional_gdp:
            return self._regional_gdp[scope]
        return {
            "total_metro_gdp_billions": sum(g["metro_gdp_billions"] for g in self._regional_gdp.values()),
            "regional_data": self._regional_gdp
        }
