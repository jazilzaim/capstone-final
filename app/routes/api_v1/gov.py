"""
Gov API Routes matching the UML Component Diagram.
Exposes GovApiConnectors, Data Management Cluster Analyzers, and VisualizationService.
"""
from flask import request, jsonify
from app.routes.api_v1 import api_v1_bp
from app.services.ingestion import ingestion_service
from app.cluster import EconAnalyzer, PolicyAnalyzer, Dataset
from app.services.visualization import visualization_service
from app.core.exceptions import NotFoundError

econ_analyzer = EconAnalyzer()
policy_analyzer = PolicyAnalyzer()

@api_v1_bp.route("/gov/connectors", methods=["GET"])
def list_gov_connectors():
    """List all registered GovApiConnectors from the UML diagram."""
    connectors = ingestion_service.list_connectors()
    return jsonify({
        "status": "success",
        "count": len(connectors),
        "data": connectors
    })

@api_v1_bp.route("/gov/<connector_name>", methods=["GET"])
def query_gov_connector(connector_name: str):
    """Query data from a specific GovApiConnector."""
    connector = ingestion_service.get_connector(connector_name)
    if not connector:
        raise NotFoundError(f"Gov connector '{connector_name}' not found. Supported: Census, BLS, BEA, Treasury, FEC, USAspending.")

    city = request.args.get("city")
    data = connector.fetch_data({"city": city} if city else None)
    metrics = connector.get_metrics(city)

    return jsonify({
        "status": "success",
        "connector": connector.name,
        "agency": connector.agency,
        "metrics": metrics,
        "data": data
    })

@api_v1_bp.route("/gov/analytics/econ", methods=["GET"])
def get_econ_analytics():
    """Execute EconAnalyzer across target cities."""
    census = ingestion_service.get_connector("census").fetch_data()
    bls = ingestion_service.get_connector("bls").fetch_data()
    bea = ingestion_service.get_connector("bea").fetch_data()

    parity = econ_analyzer.analyze_regional_parity(census, bls, bea)
    bls_dataset = Dataset("bls_timeseries", bls)
    inflation = econ_analyzer.compute_inflation_impact(bls_dataset)

    return jsonify({
        "status": "success",
        "parity_benchmarks": parity,
        "inflation_impact": inflation
    })

@api_v1_bp.route("/gov/analytics/policy", methods=["GET"])
def get_policy_analytics():
    """Execute PolicyAnalyzer across target cities."""
    census = ingestion_service.get_connector("census").fetch_data()
    usaspending = ingestion_service.get_connector("usaspending").fetch_data()
    fec = ingestion_service.get_connector("fec").fetch_data()

    fed_eval = policy_analyzer.evaluate_federal_investment_density(census, usaspending)
    campaign_eval = policy_analyzer.evaluate_civic_campaign_finance(fec)

    return jsonify({
        "status": "success",
        "federal_investment_density": fed_eval,
        "civic_campaign_finance": campaign_eval
    })

@api_v1_bp.route("/gov/charts/economic", methods=["GET"])
def get_economic_charts():
    """Execute VisualizationService to format Chart.js payloads."""
    census = ingestion_service.get_connector("census").fetch_data()
    bls = ingestion_service.get_connector("bls").fetch_data()
    bea = ingestion_service.get_connector("bea").fetch_data()
    usaspending = ingestion_service.get_connector("usaspending").fetch_data()

    parity = econ_analyzer.analyze_regional_parity(census, bls, bea)
    fed_eval = policy_analyzer.evaluate_federal_investment_density(census, usaspending)

    bar_chart = visualization_service.format_city_economic_benchmark(parity["benchmarks"])
    funding_chart = visualization_service.format_federal_funding_distribution(fed_eval["evaluations"])

    return jsonify({
        "status": "success",
        "charts": {
            "economic_vitality": bar_chart,
            "federal_funding_distribution": funding_chart
        }
    })
