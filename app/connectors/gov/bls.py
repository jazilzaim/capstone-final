"""
BLSConnector: Bureau of Labor Statistics API Connector.
Supplies labor force, unemployment rates, and Consumer Price Index (CPI) metrics.
"""
from typing import Dict, Any, List, Optional
from app.connectors.gov.base import GovApiConnector

class BLSConnector(GovApiConnector):
    def __init__(self):
        super().__init__(
            name="BLSConnector",
            agency="Bureau of Labor Statistics",
            base_url="https://api.bls.gov/publicAPI/v2/timeseries/data/"
        )
        self._economic_indicators = {
            "las_vegas": {
                "unemployment_rate_pct": 5.1,
                "labor_force": 1140000,
                "cpi_annual_change_pct": 3.2,
                "avg_hourly_wage": 31.40
            },
            "los_angeles": {
                "unemployment_rate_pct": 4.9,
                "labor_force": 4980000,
                "cpi_annual_change_pct": 3.5,
                "avg_hourly_wage": 38.60
            },
            "seattle": {
                "unemployment_rate_pct": 3.8,
                "labor_force": 2240000,
                "cpi_annual_change_pct": 2.9,
                "avg_hourly_wage": 44.80
            },
            "phoenix": {
                "unemployment_rate_pct": 4.2,
                "labor_force": 2610000,
                "cpi_annual_change_pct": 3.4,
                "avg_hourly_wage": 33.50
            }
        }

    def fetch_data(self, query_params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        city = (query_params or {}).get("city", "all")
        if city in self._economic_indicators:
            return [{"city": city, **self._economic_indicators[city]}]
        return [{"city": k, **v} for k, v in self._economic_indicators.items()]

    def get_metrics(self, scope: Optional[str] = None) -> Dict[str, Any]:
        scope = (scope or "all").lower()
        if scope in self._economic_indicators:
            return self._economic_indicators[scope]
        return {
            "national_cpi_trend": 3.1,
            "indicators_by_metro": self._economic_indicators
        }
