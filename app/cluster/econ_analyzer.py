"""
EconAnalyzer: Economic analysis component inside Data Management Cluster.
Analyzes GDP growth, CPI inflation, wage benchmarks, and labor market resilience.
"""
from typing import Dict, Any, List, Optional
from app.cluster.dataset import Dataset

class EconAnalyzer:
    """
    EconAnalyzer component of the Data Management Cluster.
    Computes macroeconomic and regional comparative economic metrics.
    """
    def analyze_regional_parity(self, census_data: List[Dict[str, Any]], bls_data: List[Dict[str, Any]], bea_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Synthesizes Census, BLS, and BEA datasets across cities into economic health indices.
        """
        cities = {}
        # Merge by city
        for item in census_data:
            c = item.get("city")
            if c:
                cities.setdefault(c, {})["population"] = item.get("population", 0)
                cities[c]["median_income"] = item.get("median_household_income", 0)

        for item in bls_data:
            c = item.get("city")
            if c:
                cities.setdefault(c, {})["unemployment_rate_pct"] = item.get("unemployment_rate_pct", 0)
                cities[c]["avg_hourly_wage"] = item.get("avg_hourly_wage", 0)

        for item in bea_data:
            c = item.get("city")
            if c:
                cities.setdefault(c, {})["metro_gdp_billions"] = item.get("metro_gdp_billions", 0)
                cities[c]["real_gdp_growth_pct"] = item.get("real_gdp_growth_pct", 0)

        benchmarks = {}
        for city, metrics in cities.items():
            income = metrics.get("median_income", 50000)
            unemployment = metrics.get("unemployment_rate_pct", 5.0)
            gdp_growth = metrics.get("real_gdp_growth_pct", 2.0)

            # Economic vitality index: (income/1000) * (gdp_growth/unemployment)
            vitality_score = round((income / 1000.0) * (gdp_growth / max(unemployment, 0.5)), 2)
            benchmarks[city] = {
                **metrics,
                "economic_vitality_index": vitality_score
            }

        return {
            "cities_analyzed": list(cities.keys()),
            "benchmarks": benchmarks,
            "top_economic_performer": max(benchmarks.items(), key=lambda x: x[1]["economic_vitality_index"])[0] if benchmarks else None
        }

    def compute_inflation_impact(self, bls_dataset: Dataset) -> Dict[str, Any]:
        inflation_map = {}
        for r in bls_dataset.records:
            city = r.get("city")
            cpi = r.get("cpi_annual_change_pct")
            if city and cpi:
                inflation_map[city] = {
                    "cpi_annual_change_pct": cpi,
                    "purchasing_power_risk": "High" if cpi > 3.2 else "Moderate"
                }
        return inflation_map
