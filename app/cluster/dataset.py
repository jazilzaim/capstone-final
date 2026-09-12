"""
Dataset: In-memory structured dataset component of the Data Management Cluster.
"""
from typing import Dict, Any, List, Optional, Callable

class Dataset:
    """
    Dataset component of the Data Management Cluster.
    Wraps standardized government and municipal data with schema inspection, filtering, and projections.
    """
    def __init__(self, name: str, records: Optional[List[Dict[str, Any]]] = None, metadata: Optional[Dict[str, Any]] = None):
        self.name = name
        self.records: List[Dict[str, Any]] = records or []
        self.metadata: Dict[str, Any] = metadata or {}

    def filter(self, predicate: Callable[[Dict[str, Any]], bool]) -> 'Dataset':
        """Return a new Dataset containing only records that satisfy the predicate."""
        filtered = [r for r in self.records if predicate(r)]
        return Dataset(f"{self.name}_filtered", filtered, self.metadata)

    def select(self, fields: List[str]) -> 'Dataset':
        """Project records down to specific fields."""
        projected = [{k: r.get(k) for k in fields if k in r} for r in self.records]
        return Dataset(f"{self.name}_projected", projected, self.metadata)

    def group_by(self, key_field: str) -> Dict[str, List[Dict[str, Any]]]:
        """Group records by a given field key."""
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for r in self.records:
            k = str(r.get(key_field, "unknown"))
            if k not in grouped:
                grouped[k] = []
            grouped[k].append(r)
        return grouped

    def count(self) -> int:
        return len(self.records)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "count": len(self.records),
            "metadata": self.metadata,
            "records": self.records
        }
