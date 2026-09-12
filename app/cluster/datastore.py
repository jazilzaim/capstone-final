"""
DataStore: Storage layer inside the Data Management Cluster.
Manages persistent records, datasets, and storage access.
"""
from typing import Dict, Any, List, Optional
import json
from datetime import datetime, timezone
from app.models.storage import db

class DataStore:
    """
    DataStore component of the Data Management Cluster.
    Provides persistence and retrieval for datasets and ingested government records.
    """
    def __init__(self):
        self._memory_store: Dict[str, List[Dict[str, Any]]] = {}

    def save_records(self, collection_name: str, records: List[Dict[str, Any]]) -> int:
        if collection_name not in self._memory_store:
            self._memory_store[collection_name] = []
        self._memory_store[collection_name].extend(records)
        return len(records)

    def get_records(self, collection_name: str, limit: int = 100) -> List[Dict[str, Any]]:
        return self._memory_store.get(collection_name, [])[:limit]

    def clear(self, collection_name: Optional[str] = None):
        if collection_name:
            self._memory_store.pop(collection_name, None)
        else:
            self._memory_store.clear()

    def count(self, collection_name: str) -> int:
        return len(self._memory_store.get(collection_name, []))
