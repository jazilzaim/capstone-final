import logging
import concurrent.futures
from typing import Dict, List, Optional, Any
from app.config import Config
from app.connectors.base import BaseCityConnector
from app.connectors.los_angeles import LosAngelesConnector
from app.connectors.seattle import SeattleConnector
from app.connectors.las_vegas import LasVegasConnector
from app.connectors.phoenix import PhoenixConnector
from app.models.schemas import PublicSafetyIncident, BuildingPermit, CommercialBusiness, CityInfo

logger = logging.getLogger("argus.connectors.registry")

class ConnectorRegistry:
    """Central registry and high-performance parallel query orchestrator for all municipal adapters."""

    def __init__(self):
        self._connectors: Dict[str, BaseCityConnector] = {
            "los_angeles": LosAngelesConnector(),
            "seattle": SeattleConnector(),
            "las_vegas": LasVegasConnector(),
            "phoenix": PhoenixConnector()
        }
        self._pool = concurrent.futures.ThreadPoolExecutor(max_workers=8, thread_name_prefix="ArgusConnector")

    def get_connector(self, city_id: str) -> Optional[BaseCityConnector]:
        return self._connectors.get(city_id.lower())

    def list_city_ids(self) -> List[str]:
        return list(self._connectors.keys())

    def get_all_cities_info(self) -> List[CityInfo]:
        return [c.get_info() for c in self._connectors.values()]

    def query_incidents(
        self,
        city: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        query: Optional[str] = None,
        category: Optional[str] = None
    ) -> List[PublicSafetyIncident]:
        if city and city.lower() != "all":
            connector = self.get_connector(city)
            if not connector:
                return []
            return connector.fetch_incidents(limit=limit, offset=offset, query=query, category=category)

        # High-performance parallel multi-city aggregation
        results: List[PublicSafetyIncident] = []
        per_city_limit = max(5, limit // len(self._connectors))

        futures = {
            self._pool.submit(conn.fetch_incidents, limit=per_city_limit, offset=offset, query=query, category=category): cid
            for cid, conn in self._connectors.items()
        }

        done, not_done = concurrent.futures.wait(
            futures.keys(),
            timeout=Config.UPSTREAM_TIMEOUT_SECONDS,
            return_when=concurrent.futures.ALL_COMPLETED
        )

        for future in done:
            try:
                city_results = future.result()
                if city_results:
                    results.extend(city_results)
            except Exception as e:
                logger.warning(f"Parallel fetch_incidents failed for {futures[future]}: {e}")

        for future in not_done:
            cid = futures[future]
            logger.warning(f"Parallel fetch_incidents timed out for {cid}, applying resilient fallback")
            conn = self.get_connector(cid)
            if conn and hasattr(conn, "_get_fallback_incidents"):
                results.extend(conn._get_fallback_incidents(per_city_limit, query, category))

        # Sort by occurred_at desc if available
        results.sort(key=lambda x: x.occurred_at or "", reverse=True)
        return results[:limit]

    def query_permits(
        self,
        city: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        query: Optional[str] = None
    ) -> List[BuildingPermit]:
        if city and city.lower() != "all":
            connector = self.get_connector(city)
            if not connector:
                return []
            return connector.fetch_permits(limit=limit, offset=offset, query=query)

        # High-performance parallel multi-city aggregation
        results: List[BuildingPermit] = []
        per_city_limit = max(5, limit // len(self._connectors))

        futures = {
            self._pool.submit(conn.fetch_permits, limit=per_city_limit, offset=offset, query=query): cid
            for cid, conn in self._connectors.items()
        }

        done, not_done = concurrent.futures.wait(
            futures.keys(),
            timeout=Config.UPSTREAM_TIMEOUT_SECONDS,
            return_when=concurrent.futures.ALL_COMPLETED
        )

        for future in done:
            try:
                city_results = future.result()
                if city_results:
                    results.extend(city_results)
            except Exception as e:
                logger.warning(f"Parallel fetch_permits failed for {futures[future]}: {e}")

        for future in not_done:
            cid = futures[future]
            logger.warning(f"Parallel fetch_permits timed out for {cid}, applying resilient fallback")
            conn = self.get_connector(cid)
            if conn and hasattr(conn, "_get_fallback_permits"):
                results.extend(conn._get_fallback_permits(per_city_limit, query))

        return results[:limit]

    def query_businesses(
        self,
        city: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        query: Optional[str] = None
    ) -> List[CommercialBusiness]:
        if city and city.lower() != "all":
            connector = self.get_connector(city)
            if not connector:
                return []
            return connector.fetch_businesses(limit=limit, offset=offset, query=query)

        # High-performance parallel multi-city aggregation
        results: List[CommercialBusiness] = []
        per_city_limit = max(5, limit // len(self._connectors))

        futures = {
            self._pool.submit(conn.fetch_businesses, limit=per_city_limit, offset=offset, query=query): cid
            for cid, conn in self._connectors.items()
        }

        done, not_done = concurrent.futures.wait(
            futures.keys(),
            timeout=Config.UPSTREAM_TIMEOUT_SECONDS,
            return_when=concurrent.futures.ALL_COMPLETED
        )

        for future in done:
            try:
                city_results = future.result()
                if city_results:
                    results.extend(city_results)
            except Exception as e:
                logger.warning(f"Parallel fetch_businesses failed for {futures[future]}: {e}")

        for future in not_done:
            cid = futures[future]
            logger.warning(f"Parallel fetch_businesses timed out for {cid}, applying resilient fallback")
            conn = self.get_connector(cid)
            if conn and hasattr(conn, "_get_fallback_businesses"):
                results.extend(conn._get_fallback_businesses(per_city_limit, query))

        return results[:limit]

    def get_analytics_summary(self) -> Dict[str, Any]:
        """Aggregate statistical indicators across all 4 cities."""
        all_incidents = self.query_incidents(city="all", limit=120)
        category_counts: Dict[str, int] = {}
        city_counts: Dict[str, int] = {}

        for inc in all_incidents:
            cat = inc.category or "General"
            category_counts[cat] = category_counts.get(cat, 0) + 1

            cname = inc.city_name
            city_counts[cname] = city_counts.get(cname, 0) + 1

        all_permits = self.query_permits(city="all", limit=60)
        total_valuation = sum((p.valuation_usd or 0) for p in all_permits)

        return {
            "total_sampled_incidents": len(all_incidents),
            "breakdown_by_category": category_counts,
            "breakdown_by_city": city_counts,
            "construction_pipeline": {
                "active_permits_sampled": len(all_permits),
                "total_estimated_valuation_usd": round(total_valuation, 2)
            },
            "cities_monitored": len(self._connectors),
            "updated_at": "2026-09-11T19:00:00Z"
        }

registry = ConnectorRegistry()
