import pytest
from app.connectors.los_angeles import LosAngelesConnector
from app.connectors.seattle import SeattleConnector
from app.connectors.las_vegas import LasVegasConnector
from app.connectors.phoenix import PhoenixConnector
from app.models.schemas import PublicSafetyIncident, BuildingPermit, CommercialBusiness

def test_los_angeles_connector():
    conn = LosAngelesConnector()
    incidents = conn.fetch_incidents(limit=2)
    assert len(incidents) > 0
    assert isinstance(incidents[0], PublicSafetyIncident)
    assert incidents[0].city == "los_angeles"
    assert incidents[0].location is not None

    permits = conn.fetch_permits(limit=2)
    assert len(permits) > 0
    assert isinstance(permits[0], BuildingPermit)

    businesses = conn.fetch_businesses(limit=2)
    assert len(businesses) > 0
    assert isinstance(businesses[0], CommercialBusiness)

def test_seattle_connector():
    conn = SeattleConnector()
    incidents = conn.fetch_incidents(limit=2)
    assert len(incidents) > 0
    assert isinstance(incidents[0], PublicSafetyIncident)
    assert incidents[0].city == "seattle"

    permits = conn.fetch_permits(limit=2)
    assert len(permits) > 0
    assert isinstance(permits[0], BuildingPermit)

def test_las_vegas_connector():
    conn = LasVegasConnector()
    incidents = conn.fetch_incidents(limit=2)
    assert len(incidents) > 0
    assert isinstance(incidents[0], PublicSafetyIncident)
    assert incidents[0].city == "las_vegas"

    permits = conn.fetch_permits(limit=2)
    assert len(permits) > 0
    assert isinstance(permits[0], BuildingPermit)

def test_phoenix_connector():
    conn = PhoenixConnector()
    incidents = conn.fetch_incidents(limit=2)
    assert len(incidents) > 0
    assert isinstance(incidents[0], PublicSafetyIncident)
    assert incidents[0].city == "phoenix"

    permits = conn.fetch_permits(limit=2)
    assert len(permits) > 0
    assert isinstance(permits[0], BuildingPermit)
