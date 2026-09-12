"""
Comprehensive tests for the Argus UML State Machine and Data Pipeline Jobs.
Validates all states, happy path, failure recovery loops, cancellation flows, and API endpoints.
"""
import pytest
from app import create_app
from app.models.storage import db
from app.core.state_machine import JobStateMachine, JobState, JobEvent
from app.core.exceptions import InvalidStateTransitionError
from app.services.job_worker import (
    run_job_pipeline_step_by_step,
    cancel_pipeline_job,
    retry_failed_job,
    archive_completed_job
)

@pytest.fixture
def app():
    test_app = create_app()
    test_app.config["TESTING"] = True
    return test_app

@pytest.fixture
def client(app):
    return app.test_client()

# =====================================================================
# 1. State Machine Unit Transitions (Exact UML Diagram Matrix)
# =====================================================================

def test_state_machine_happy_path_lifecycle():
    """
    Test the full happy path:
    Initial -> Draft -> submit() -> Submitted -> validationOk -> Queued
    -> workerStarts() -> Fetching -> success -> Analyzing -> success
    -> Completed -> archivePolicy -> Archived (Terminal)
    """
    sm = JobStateMachine()
    assert sm.state == JobState.DRAFT

    # submit() -> Submitted
    assert sm.submit({"user": "dev@argus.dev"}) == JobState.SUBMITTED
    assert sm.state == JobState.SUBMITTED

    # validationOk -> Queued
    assert sm.validation_ok({"valid": True}) == JobState.QUEUED
    assert sm.state == JobState.QUEUED

    # workerStarts() -> Fetching
    assert sm.worker_starts({"worker": "worker-1"}) == JobState.FETCHING
    assert sm.state == JobState.FETCHING

    # success -> Analyzing
    assert sm.success({"records": 100}) == JobState.ANALYZING
    assert sm.state == JobState.ANALYZING

    # success -> Completed
    assert sm.success({"metrics_computed": True}) == JobState.COMPLETED
    assert sm.state == JobState.COMPLETED
    assert not sm.is_terminal()

    # archivePolicy -> Archived (Terminal)
    assert sm.archive_policy({"ttl_expired": True}) == JobState.ARCHIVED
    assert sm.state == JobState.ARCHIVED
    assert sm.is_terminal()

def test_state_machine_validation_failure_and_recovery():
    """
    Test validation failure path:
    Draft -> submit() -> Submitted -> validationError -> FailedValidation
    -> Error -> Draft (recovery loop)
    """
    sm = JobStateMachine()
    sm.submit()
    assert sm.state == JobState.SUBMITTED

    # validationError -> FailedValidation
    sm.validation_error("Invalid city: atlantis")
    assert sm.state == JobState.FAILED_VALIDATION

    # Error -> Draft (returns to Draft for correction)
    sm.error({"correction": "updated parameters"})
    assert sm.state == JobState.DRAFT

def test_state_machine_fetching_failure_and_recovery():
    """
    Test fetching failure path:
    Draft -> submit -> validationOk -> workerStarts -> Fetching
    -> failure -> FailedExecution -> failure -> Draft (recovery loop)
    """
    sm = JobStateMachine()
    sm.submit()
    sm.validation_ok()
    sm.worker_starts()
    assert sm.state == JobState.FETCHING

    # failure -> FailedExecution
    sm.failure("Upstream timeout on Las Vegas connector")
    assert sm.state == JobState.FAILED_EXECUTION

    # failure -> Draft (recovery loop)
    sm.failure("Recovering to draft for parameter adjustment")
    assert sm.state == JobState.DRAFT

def test_state_machine_analyzing_failure_and_recovery():
    """
    Test analyzing failure path:
    Draft -> submit -> validationOk -> workerStarts -> Fetching
    -> success -> Analyzing -> failure -> FailedExecution -> failure -> Draft
    """
    sm = JobStateMachine()
    sm.submit()
    sm.validation_ok()
    sm.worker_starts()
    sm.success()
    assert sm.state == JobState.ANALYZING

    # failure -> FailedExecution
    sm.failure("Data format error during analysis")
    assert sm.state == JobState.FAILED_EXECUTION

    # failure -> Draft
    sm.failure("Retry to draft")
    assert sm.state == JobState.DRAFT

def test_state_machine_cancellation_paths():
    """
    Test all cancellation paths from diagram:
    - Draft -> cancel() -> Cancelled -> notifyUser -> FinalState
    - Queued -> cancel() -> Cancelled
    - Fetching -> delete() -> Cancelled
    - Analyzing -> delete() -> Cancelled
    """
    # 1. From Draft
    sm1 = JobStateMachine()
    sm1.cancel("User changed mind")
    assert sm1.state == JobState.CANCELLED
    sm1.notify_user()
    assert sm1.state == JobState.FINAL_STATE
    assert sm1.is_terminal()

    # 2. From Queued
    sm2 = JobStateMachine()
    sm2.submit()
    sm2.validation_ok()
    assert sm2.state == JobState.QUEUED
    sm2.cancel()
    assert sm2.state == JobState.CANCELLED

    # 3. From Fetching (via delete)
    sm3 = JobStateMachine()
    sm3.submit()
    sm3.validation_ok()
    sm3.worker_starts()
    assert sm3.state == JobState.FETCHING
    sm3.delete("Aborted during fetch")
    assert sm3.state == JobState.CANCELLED

    # 4. From Analyzing (via delete)
    sm4 = JobStateMachine()
    sm4.submit()
    sm4.validation_ok()
    sm4.worker_starts()
    sm4.success()
    assert sm4.state == JobState.ANALYZING
    sm4.delete("Aborted during analysis")
    assert sm4.state == JobState.CANCELLED

def test_state_machine_illegal_transitions_rejected():
    """
    Test that invalid/illegal transitions raise InvalidStateTransitionError.
    """
    sm = JobStateMachine()
    # Cannot jump directly from Draft to Completed
    with pytest.raises(InvalidStateTransitionError) as exc:
        sm.trigger(JobEvent.SUCCESS)
    assert exc.value.status_code == 409

    # Cannot archive from Draft
    with pytest.raises(InvalidStateTransitionError):
        sm.archive_policy()

    # Move to Submitted
    sm.submit()
    # Cannot call workerStarts directly without validationOk
    with pytest.raises(InvalidStateTransitionError):
        sm.worker_starts()

# =====================================================================
# 2. Worker Pipeline Execution & Multi-City Fetch
# =====================================================================

def test_pipeline_job_end_to_end_execution():
    """
    Tests creating a pipeline job, executing step-by-step through the state machine,
    verifying multi-city data aggregation across Las Vegas, LA, Seattle, Phoenix.
    """
    job = db.create_pipeline_job(
        user_email="tester@argus.dev",
        name="Automated Test Multi-City Pipeline",
        cities=["las_vegas", "los_angeles", "seattle", "phoenix"],
        datasets=["incidents", "permits"],
        query_params={"limit": 3},
        initial_status="Draft"
    )
    job_id = job["job_id"]
    assert job["status"] == "Draft"

    # Execute step-by-step pipeline
    completed_job = run_job_pipeline_step_by_step(job_id)
    assert completed_job["status"] == "Completed"
    assert completed_job["result"] is not None

    # Check metrics by city
    metrics = completed_job["result"]["metrics_by_city"]
    for city in ["las_vegas", "los_angeles", "seattle", "phoenix"]:
        assert city in metrics
        assert "incidents_count" in metrics[city]
        assert "permits_count" in metrics[city]

    # Test archive policy
    archived_job = archive_completed_job(job_id)
    assert archived_job["status"] == "Archived"

# =====================================================================
# 3. REST API Endpoints for State Machine Jobs
# =====================================================================

def test_jobs_api_lifecycle(client):
    """
    Test /api/v1/jobs endpoints:
    - POST /api/v1/jobs
    - GET /api/v1/jobs/<id>
    - POST /api/v1/jobs/<id>/submit
    - POST /api/v1/jobs/<id>/cancel
    - POST /api/v1/jobs/<id>/transition
    """
    demo_key = "argus_demo_free_key_2026"
    headers = {"X-API-Key": demo_key}

    # 1. Create Job
    res = client.post("/api/v1/jobs", json={
        "name": "API Test Pipeline",
        "cities": ["las_vegas", "seattle"],
        "datasets": ["incidents"],
        "query_params": {"limit": 2}
    }, headers=headers)
    assert res.status_code == 201
    job_data = res.get_json()["data"]
    job_id = job_data["job_id"]
    assert job_data["status"] == "Draft"

    # 2. Get Job Details & State Machine Metadata
    res_get = client.get(f"/api/v1/jobs/{job_id}", headers=headers)
    assert res_get.status_code == 200
    info = res_get.get_json()["data"]
    assert "state_machine_info" in info
    assert info["state_machine_info"]["current_state"] == "Draft"
    assert "submit" in info["state_machine_info"]["allowed_events"]
    assert "cancel" in info["state_machine_info"]["allowed_events"]

    # 3. Manual Transition Trigger
    res_trans = client.post(f"/api/v1/jobs/{job_id}/transition", json={
        "event": "submit",
        "metadata": {"source": "manual_test"}
    }, headers=headers)
    assert res_trans.status_code == 200
    assert res_trans.get_json()["data"]["status"] == "Submitted"

    # 4. Cancel Job
    res_cancel = client.post(f"/api/v1/jobs/{job_id}/cancel", json={
        "reason": "Test cancel"
    }, headers=headers)
    assert res_cancel.status_code == 200
    # Following notifyUser, status reaches FinalState
    assert res_cancel.get_json()["data"]["status"] in ["Cancelled", "FinalState"]
