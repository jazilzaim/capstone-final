"""
QueryEngine: Multi-dimensional search, filtering, and query execution engine inside Data Management Cluster.
"""
from typing import Dict, Any, List, Optional
from app.cluster.dataset import Dataset

class QueryEngine:
    """
    QueryEngine component of Data Management Cluster.
    Executes filtering, text searches, sorting, and aggregations on Datasets.
    """
    def execute_query(
        self,
        dataset: Dataset,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: Optional[str] = None,
        reverse: bool = False,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        records = dataset.records

        # Apply key-value filters
        if filters:
            for k, v in filters.items():
                if v is not None:
                    records = [r for r in records if str(r.get(k, "")).lower() == str(v).lower()]

        # Sort
        if sort_by:
            records = sorted(
                records,
                key=lambda x: (x.get(sort_by) is None, x.get(sort_by, "")),
                reverse=reverse
            )

        return records[offset:offset + limit]

    def aggregate(
        self,
        dataset: Dataset,
        group_by: str,
        metric_field: Optional[str] = None,
        agg_type: str = "count"
    ) -> Dict[str, Any]:
        groups = dataset.group_by(group_by)
        result = {}

        for group_val, recs in groups.items():
            if agg_type == "count":
                result[group_val] = len(recs)
            elif agg_type == "sum" and metric_field:
                result[group_val] = sum(float(r.get(metric_field, 0) or 0) for r in recs)
            elif agg_type == "avg" and metric_field:
                total = sum(float(r.get(metric_field, 0) or 0) for r in recs)
                result[group_val] = round(total / len(recs), 2) if recs else 0
            else:
                result[group_val] = len(recs)

        return result
