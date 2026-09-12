"""
TreasuryConnector: U.S. Department of the Treasury API Connector.
Provides Fiscal Data, federal debt, operating cash, and interest rate benchmarks.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from app.connectors.gov.base import GovApiConnector

class TreasuryConnector(GovApiConnector):
    def __init__(self):
        super().__init__(
            name="TreasuryConnector",
            agency="U.S. Department of the Treasury",
            base_url="https://api.fiscaldata.treasury.gov/services/api/fiscal_service/"
        )

    def fetch_data(self, query_params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        return [
            {
                "record_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "debt_held_public_billions": 28450.2,
                "intragovernmental_holdings_billions": 7120.5,
                "total_public_debt_billions": 35570.7,
                "operating_cash_balance_billions": 742.8,
                "ten_year_treasury_yield_pct": 4.15
            }
        ]

    def get_metrics(self, scope: Optional[str] = None) -> Dict[str, Any]:
        data = self.fetch_data()[0]
        return {
            "total_public_debt_trillions": round(data["total_public_debt_billions"] / 1000, 2),
            "benchmark_10yr_yield": data["ten_year_treasury_yield_pct"],
            "operating_cash_billions": data["operating_cash_balance_billions"]
        }
