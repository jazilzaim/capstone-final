"""
DataIngestionService & IngestionJob matching the UML Component Diagram.
Coordinates GovApiConnectors and transitions through the JobStateMachine into the Data Management Cluster.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from app.core.state_machine import JobStateMachine, JobState
from app.connectors.gov import (
    GovApiConnector,
    CensusConnector,
    BLSConnector,
    BEAConnector,
    TreasuryConnector,
    FECConnector,
    USAspendingConnector
)

logger = logging.getLogger(__name__)

class IngestionJob:
    """
    IngestionJob matching UML diagram.
    Manages the lifecycle of an ingestion run via the deterministic JobStateMachine.
    """
    def __init__(self, job_id: str, name: str, sources: List[str], parameters: Optional[Dict[str, Any]] = None):
        self.job_id = job_id
        self.name = name
        self.sources = sources
        self.parameters = parameters or {}
        self.state_machine = JobStateMachine(JobState.DRAFT)
        self.collected_records: List[Dict[str, Any]] = []
        self.created_at = datetime.now(timezone.utc).isoformat()

    @property
    def status(self) -> str:
        return self.state_machine.state.value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "name": self.name,
            "status": self.status,
            "sources": self.sources,
            "parameters": self.parameters,
            "records_count": len(self.collected_records),
            "state_machine": self.state_machine.to_dict(),
            "created_at": self.created_at
        }

class DataIngestionService:
    """
    DataIngestionService matching UML diagram.
    Ingests data across government connectors and outputs standardized payloads to Data Management Cluster.
    """
    def __init__(self):
        self._connectors: Dict[str, GovApiConnector] = {}
        self._register_default_connectors()

    def _register_default_connectors(self):
        self.register_connector(CensusConnector())
        self.register_connector(BLSConnector())
        self.register_connector(BEAConnector())
        self.register_connector(TreasuryConnector())
        self.register_connector(FECConnector())
        self.register_connector(USAspendingConnector())

    def register_connector(self, connector: GovApiConnector):
        self._connectors[connector.name.lower()] = connector
        # Also register alias without 'connector' suffix (e.g. 'census', 'bls')
        alias = connector.name.lower().replace("connector", "")
        self._connectors[alias] = connector

    def get_connector(self, name: str) -> Optional[GovApiConnector]:
        return self._connectors.get(name.lower().strip())

    def list_connectors(self) -> List[Dict[str, Any]]:
        seen = set()
        result = []
        for conn in self._connectors.values():
            if conn.name not in seen:
                seen.add(conn.name)
                result.append(conn.to_dict())
        return result

    def execute_ingestion_job(self, job: IngestionJob) -> IngestionJob:
        """
        Executes an IngestionJob through the state machine:
        Draft -> submit() -> validationOk -> workerStarts() -> success -> success -> Completed
        """
        sm = job.state_machine

        # 1. submit()
        sm.submit({"reason": "Ingestion job submitted"})

        # 2. validation
        unknown_sources = [s for s in job.sources if s.lower() not in self._connectors]
        if unknown_sources:
            sm.validation_error(f"Unknown connectors: {unknown_sources}")
            return job

        sm.validation_ok({"valid_sources": job.sources})

        # 3. workerStarts() -> Fetching
        sm.worker_starts({"worker": "DataIngestionServiceWorker"})

        # 4. Fetch data from each connector
        try:
            records = []
            for source_name in job.sources:
                connector = self.get_connector(source_name)
                if connector:
                    source_records = connector.fetch_data(job.parameters)
                    for rec in source_records:
                        records.append({
                            "source": connector.name,
                            "agency": connector.agency,
                            "payload": rec
                        })

            job.collected_records = records
            sm.success({"records_count": len(records)})
        except Exception as e:
            sm.failure(str(e))
            return job

        # 5. Analyzing -> Completed
        sm.success({"analyzed_at": datetime.now(timezone.utc).isoformat()})
        return job

# Global Ingestion Service instance
ingestion_service = DataIngestionService()
