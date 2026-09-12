"""
PolicyAnalyzer: Policy and civic investment analysis component inside Data Management Cluster.
Evaluates federal award allocations, campaign finance, and municipal infrastructure metrics.
"""
from typing import Dict, Any, List, Optional
from app.cluster.dataset import Dataset

class PolicyAnalyzer:
    """
    PolicyAnalyzer component of the Data Management Cluster.
    Analyzes federal grant distributions (USAspending), campaign finance (FEC), and municipal permit investments.
    """
    def evaluate_federal_investment_density(
        self,
        census_records: List[Dict[str, Any]],
        usaspending_records: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculates per-capita federal funding and award concentration across target cities.
        """
        pop_map = {r.get("city"): r.get("population", 1) for r in census_records if r.get("city")}
        policy_eval = {}

        for item in usaspending_records:
            city = item.get("city")
            if not city or city not in pop_map:
                continue

            funding_millions = float(item.get("total_federal_funding_millions", 0))
            pop = pop_map[city]
            funding_per_capita = round((funding_millions * 1_000_000) / pop, 2)

            policy_eval[city] = {
                "total_federal_funding_millions": funding_millions,
                "population": pop,
                "funding_per_capita_usd": funding_per_capita,
                "top_agency": item.get("top_awarding_agency"),
                "investment_tier": "High" if funding_per_capita > 2500 else "Standard"
            }

        return {
            "cities_evaluated": list(policy_eval.keys()),
            "evaluations": policy_eval,
            "highest_funding_per_capita": max(policy_eval.items(), key=lambda x: x[1]["funding_per_capita_usd"])[0] if policy_eval else None
        }

    def evaluate_civic_campaign_finance(self, fec_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        analysis = {}
        for r in fec_records:
            city = r.get("city")
            if city:
                receipts = r.get("total_receipts_millions", 0)
                individual_pct = r.get("individual_contributions_pct", 0)
                analysis[city] = {
                    "total_receipts_millions": receipts,
                    "grassroots_index_pct": individual_pct,
                    "engagement_level": "Elevated" if individual_pct > 70 else "Normal"
                }
        return analysis
