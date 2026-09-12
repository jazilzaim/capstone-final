"""
Automated Test Suite for the UML Component Architecture:
- ApiGateway, AuthService, RateLimiter
- GovApiConnector (Census, BLS, BEA, Treasury, FEC, USAspending)
- DataIngestionService & IngestionJob
- Data Management Cluster (DataStore, Dataset, QueryEngine, EconAnalyzer, PolicyAnalyzer)
- Downstream Query, VisualizationService, Cache
"""
import pytest
from app import create_app
from app.connectors.gov import (
    GovApiConnector,
    CensusConnector,
    BLSConnector,
    BEAConnector,
    TreasuryConnector,
    FECConnector,
    USAspendingConnector
)
from app.services.ingestion import DataIngestionService, IngestionJob, ingestion_service
from app.cluster import DataStore, Dataset, QueryEngine, EconAnalyzer, PolicyAnalyzer
from app.services.visualization import VisualizationService
from app.core.auth import AuthService
from app.core.ratelimit import RateLimiter
from app.core.cache import cache

@pytest.fixture
def app():
    test_app = create_app()
    test_app.config["TESTING"] = True
    return test_app

@pytest.fixture
def client(app):
    return app.test_client()

# =====================================================================
# 1. GovApiConnector Suite
# =====================================================================

def test_gov_connectors_fetch_and_metrics():
    # 1. CensusConnector
    census = CensusConnector()
    assert census.agency == "U.S. Census Bureau"
    data = census.fetch_data()
    assert len(data) == 4
    lv_metrics = census.get_metrics("las_vegas")
    assert lv_metrics["population"] > 500000

    # 2. BLSConnector
    bls = BLSConnector()
    assert bls.agency == "Bureau of Labor Statistics"
    bls_data = bls.fetch_data()
    assert len(bls_data) == 4
    sea_metrics = bls.get_metrics("seattle")
    assert sea_metrics["unemployment_rate_pct"] < 5.0

    # 3. BEAConnector
    bea = BEAConnector()
    assert bea.agency == "Bureau of Economic Analysis"
    bea_data = bea.fetch_data()
    assert len(bea_data) == 4
    la_metrics = bea.get_metrics("los_angeles")
    assert la_metrics["metro_gdp_billions"] > 1000

    # 4. TreasuryConnector
    treasury = TreasuryConnector()
    t_data = treasury.fetch_data()
    assert len(t_data) >= 1
    assert "total_public_debt_billions" in t_data[0]

    # 5. FECConnector
    fec = FECConnector()
    f_data = fec.fetch_data()
    assert len(f_data) == 4
    assert fec.get_metrics("phoenix")["active_committees"] > 0

    # 6. USAspendingConnector
    usaspending = USAspendingConnector()
    u_data = usaspending.fetch_data()
    assert len(u_data) == 4
    assert usaspending.get_metrics("las_vegas")["prime_contracts_millions"] > 1000

# =====================================================================
# 2. DataIngestionService & IngestionJob (State Machine Integration)
# =====================================================================

def test_data_ingestion_service_job_lifecycle():
    svc = DataIngestionService()
    job = IngestionJob(
        job_id="inj_001",
        name="Cross-Agency Regional Pull",
        sources=["census", "bls", "bea"]
    )
    assert job.status == "Draft"

    # Execute through the state machine
    finished_job = svc.execute_ingestion_job(job)
    assert finished_job.status == "Completed"
    assert len(finished_job.collected_records) > 0
    # Audit history recorded
    assert len(finished_job.state_machine.history) >= 4

# =====================================================================
# 3. Data Management Cluster Suite
# =====================================================================

def test_data_management_cluster_pipeline():
    # DataStore
    store = DataStore()
    assert store.count("raw_gov") == 0
    store.save_records("raw_gov", [{"id": 1, "val": 10}, {"id": 2, "val": 20}])
    assert store.count("raw_gov") == 2

    # Dataset
    raw_recs = [
        {"city": "las_vegas", "metric": 50, "category": "A"},
        {"city": "los_angeles", "metric": 80, "category": "B"},
        {"city": "seattle", "metric": 95, "category": "A"},
        {"city": "phoenix", "metric": 60, "category": "B"}
    ]
    ds = Dataset("test_dataset", raw_recs)
    assert ds.count() == 4
    assert ds.filter(lambda r: r["metric"] > 70).count() == 2

    # QueryEngine
    engine = QueryEngine()
    filtered = engine.execute_query(ds, filters={"category": "A"}, sort_by="metric", reverse=True)
    assert len(filtered) == 2
    assert filtered[0]["city"] == "seattle"

    # Aggregation
    agg = engine.aggregate(ds, group_by="category", agg_type="count")
    assert agg["A"] == 2
    assert agg["B"] == 2

    # EconAnalyzer
    econ = EconAnalyzer()
    census_recs = CensusConnector().fetch_data()
    bls_recs = BLSConnector().fetch_data()
    bea_recs = BEAConnector().fetch_data()
    parity = econ.analyze_regional_parity(census_recs, bls_recs, bea_recs)
    assert "benchmarks" in parity
    assert len(parity["cities_analyzed"]) == 4
    assert parity["top_economic_performer"] is not None

    # PolicyAnalyzer
    policy = PolicyAnalyzer()
    usaspending_recs = USAspendingConnector().fetch_data()
    fed_eval = policy.evaluate_federal_investment_density(census_recs, usaspending_recs)
    assert len(fed_eval["cities_evaluated"]) == 4
    assert fed_eval["highest_funding_per_capita"] is not None

# =====================================================================
# 4. Downstream Services: VisualizationService, AuthService, RateLimiter
# =====================================================================

def test_downstream_services():
    # VisualizationService
    viz = VisualizationService()
    census_recs = CensusConnector().fetch_data()
    bls_recs = BLSConnector().fetch_data()
    bea_recs = BEAConnector().fetch_data()
    parity = EconAnalyzer().analyze_regional_parity(census_recs, bls_recs, bea_recs)

    chart = viz.format_city_economic_benchmark(parity["benchmarks"])
    assert chart["type"] == "bar"
    assert len(chart["labels"]) == 4
    assert len(chart["datasets"]) == 3

    # AuthService
    key_info = AuthService.verify_api_key("argus_demo_free_key_2026")
    assert key_info is not None
    assert key_info["tier"] == "free"

    # RateLimiter
    limiter = RateLimiter()
    allowed, rem, reset = limiter.check_rate_limit("test_caller", limit=50)
    assert allowed is True
    assert rem == 49

    # Cache
    cache.set("test_cluster_key", {"status": "ok"}, ttl=60)
    assert cache.get("test_cluster_key") == {"status": "ok"}

# =====================================================================
# 5. ApiGateway REST Endpoints
# =====================================================================

def test_gov_api_endpoints(client):
    headers = {"X-API-Key": "argus_demo_free_key_2026"}

    # 1. Connectors list
    res = client.get("/api/v1/gov/connectors", headers=headers)
    assert res.status_code == 200
    connectors = res.get_json()["data"]
    connector_names = [c["name"] for c in connectors]
    assert "CensusConnector" in connector_names
    assert "BLSConnector" in connector_names
    assert "BEAConnector" in connector_names
    assert "TreasuryConnector" in connector_names
    assert "FECConnector" in connector_names
    assert "USAspendingConnector" in connector_names

    # 2. Query individual connector
    res_census = client.get("/api/v1/gov/census?city=las_vegas", headers=headers)
    assert res_census.status_code == 200
    assert res_census.get_json()["connector"] == "CensusConnector"

    # 3. Econ analytics endpoint
    res_econ = client.get("/api/v1/gov/analytics/econ", headers=headers)
    assert res_econ.status_code == 200
    assert "parity_benchmarks" in res_econ.get_json()

    # 4. Policy analytics endpoint
    res_policy = client.get("/api/v1/gov/analytics/policy", headers=headers)
    assert res_policy.status_code == 200
    assert "federal_investment_density" in res_policy.get_json()

    # 5. Chart payloads endpoint
    res_charts = client.get("/api/v1/gov/charts/economic", headers=headers)
    assert res_charts.status_code == 200
    charts = res_charts.get_json()["charts"]
    assert "economic_vitality" in charts
    assert "federal_funding_distribution" in charts
