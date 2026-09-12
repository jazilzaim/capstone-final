"""
VisualizationService: Downstream visualization and charting component matching UML diagram.
Formats structured Dataset and Analyzer outputs into Chart.js compatible visual payloads.
"""
from typing import Dict, Any, List

class VisualizationService:
    """
    VisualizationService matching the UML Component Diagram.
    Transforms data from Data Management Cluster into visual chart structures.
    """
    def format_city_economic_benchmark(self, benchmarks: Dict[str, Any]) -> Dict[str, Any]:
        cities = list(benchmarks.keys())
        vitality_scores = [benchmarks[c].get("economic_vitality_index", 0) for c in cities]
        gdp_growth = [benchmarks[c].get("real_gdp_growth_pct", 0) for c in cities]
        unemployment = [benchmarks[c].get("unemployment_rate_pct", 0) for c in cities]

        return {
            "type": "bar",
            "labels": [c.replace("_", " ").title() for c in cities],
            "datasets": [
                {
                    "label": "Economic Vitality Score",
                    "data": vitality_scores,
                    "backgroundColor": "#635bff"
                },
                {
                    "label": "Real GDP Growth (%)",
                    "data": gdp_growth,
                    "backgroundColor": "#00d4ff"
                },
                {
                    "label": "Unemployment Rate (%)",
                    "data": unemployment,
                    "backgroundColor": "#f59e0b"
                }
            ]
        }

    def format_federal_funding_distribution(self, evaluations: Dict[str, Any]) -> Dict[str, Any]:
        cities = list(evaluations.keys())
        funding_millions = [evaluations[c].get("total_federal_funding_millions", 0) for c in cities]
        funding_per_capita = [evaluations[c].get("funding_per_capita_usd", 0) for c in cities]

        return {
            "type": "pie",
            "labels": [c.replace("_", " ").title() for c in cities],
            "datasets": [
                {
                    "label": "Total Federal Funding ($M)",
                    "data": funding_millions,
                    "backgroundColor": ["#635bff", "#00d4ff", "#10b981", "#f59e0b"]
                }
            ],
            "per_capita_benchmarks": dict(zip(cities, funding_per_capita))
        }

# Global VisualizationService instance
visualization_service = VisualizationService()
