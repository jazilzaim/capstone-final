"""
Argus Pipeline Job Worker & Orchestrator.
Drives jobs through the UML State Machine lifecycle:
Draft -> Submitted -> Queued -> Fetching -> Analyzing -> Completed -> Archived
(with FailedValidation, FailedExecution, Cancelled, and FinalState error and recovery paths).
"""
import logging
import concurrent.futures
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from app.core.state_machine import JobStateMachine, JobState, JobEvent
from app.models.storage import db
from app.connectors.registry import registry

logger = logging.getLogger(__name__)

# Background executor for asynchronous job execution
job_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4, thread_name_prefix="ArgusJobWorker")

SUPPORTED_CITIES = {"las_vegas", "los_angeles", "seattle", "phoenix"}
SUPPORTED_DATASETS = {"incidents", "permits", "businesses"}

def _get_sm(job: Dict[str, Any]) -> JobStateMachine:
    return JobStateMachine(
        initial_state=JobState(job["status"]),
        history=job.get("history", [])
    )

def _save_transition(job_id: str, sm: JobStateMachine, error_message: Optional[str] = None, result_data: Optional[Dict[str, Any]] = None):
    last_entry = sm.history[-1] if sm.history else None
    return db.update_pipeline_job_state(
        job_id=job_id,
        new_status=sm.state.value,
        history_entry=last_entry,
        error_message=error_message,
        result_data=result_data
    )

def transition_job(job_id: str, event_name: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Manually apply an event to a job's state machine."""
    job = db.get_pipeline_job(job_id)
    if not job:
        raise ValueError(f"Job '{job_id}' not found.")

    sm = _get_sm(job)
    new_state = sm.trigger(event_name, metadata)
    updated = _save_transition(job_id, sm)
    return updated

def run_job_pipeline_step_by_step(job_id: str) -> Dict[str, Any]:
    """
    Executes the full pipeline for a job step-by-step through the state machine.
    """
    job = db.get_pipeline_job(job_id)
    if not job:
        raise ValueError(f"Job '{job_id}' not found.")

    sm = _get_sm(job)

    # 1. Draft -> submit() -> Submitted
    if sm.state == JobState.DRAFT:
        sm.submit({"reason": "User or pipeline submitted job"})
        _save_transition(job_id, sm)

    # 2. Submitted -> validationOk / validationError
    if sm.state == JobState.SUBMITTED:
        cities = set(c.lower().strip() for c in job.get("cities", []))
        datasets = set(d.lower().strip() for d in job.get("datasets", []))

        invalid_cities = cities - SUPPORTED_CITIES
        invalid_datasets = datasets - SUPPORTED_DATASETS

        if not cities or invalid_cities:
            err_msg = f"Invalid or unsupported cities: {list(invalid_cities) if invalid_cities else 'No cities provided'}. Supported: {list(SUPPORTED_CITIES)}"
            sm.validation_error(err_msg)
            return _save_transition(job_id, sm, error_message=err_msg)
        elif not datasets or invalid_datasets:
            err_msg = f"Invalid or unsupported datasets: {list(invalid_datasets) if invalid_datasets else 'No datasets provided'}. Supported: {list(SUPPORTED_DATASETS)}"
            sm.validation_error(err_msg)
            return _save_transition(job_id, sm, error_message=err_msg)
        else:
            sm.validation_ok({"validated_cities": list(cities), "validated_datasets": list(datasets)})
            _save_transition(job_id, sm)

    # 3. Queued -> workerStarts() -> Fetching
    if sm.state == JobState.QUEUED:
        sm.worker_starts({"worker_thread": "ArgusJobWorker", "started_at": datetime.now(timezone.utc).isoformat()})
        _save_transition(job_id, sm)

    # 4. Fetching -> success / failure
    if sm.state == JobState.FETCHING:
        fetched_data = {}
        fetch_errors = []
        cities = job.get("cities", [])
        datasets = job.get("datasets", [])
        limit = job.get("query_params", {}).get("limit", 15)

        try:
            for city in cities:
                fetched_data[city] = {}
                if "incidents" in datasets:
                    try:
                        inc_data = registry.query_incidents(city=city, limit=limit)
                        fetched_data[city]["incidents"] = [i.to_dict() if hasattr(i, "to_dict") else i for i in inc_data]
                    except Exception as e:
                        fetch_errors.append(f"{city}/incidents: {str(e)}")

                if "permits" in datasets:
                    try:
                        perm_data = registry.query_permits(city=city, limit=limit)
                        fetched_data[city]["permits"] = [p.to_dict() if hasattr(p, "to_dict") else p for p in perm_data]
                    except Exception as e:
                        fetch_errors.append(f"{city}/permits: {str(e)}")

                if "businesses" in datasets:
                    try:
                        biz_data = registry.query_businesses(city=city, limit=limit)
                        fetched_data[city]["businesses"] = [b.to_dict() if hasattr(b, "to_dict") else b for b in biz_data]
                    except Exception as e:
                        fetch_errors.append(f"{city}/businesses: {str(e)}")

            if fetch_errors and not any(len(v) > 0 for city_dict in fetched_data.values() for v in city_dict.values()):
                err_msg = f"Fetching failed across all endpoints: {'; '.join(fetch_errors)}"
                sm.failure(err_msg)
                return _save_transition(job_id, sm, error_message=err_msg)
            else:
                sm.success({"records_count": sum(len(v) for cd in fetched_data.values() for v in cd.values())})
                _save_transition(job_id, sm)
        except Exception as e:
            sm.failure(str(e))
            return _save_transition(job_id, sm, error_message=str(e))

    # 5. Analyzing -> success / failure -> Completed
    if sm.state == JobState.ANALYZING:
        try:
            # Perform multi-city comparative analytics & aggregation
            analysis_result = {
                "job_id": job_id,
                "job_name": job.get("name"),
                "cities_covered": job.get("cities"),
                "datasets_processed": job.get("datasets"),
                "metrics_by_city": {},
                "totals": {
                    "total_incidents": 0,
                    "total_permits": 0,
                    "total_businesses": 0,
                    "grand_total": 0
                }
            }

            for city, d_dict in fetched_data.items():
                inc_cnt = len(d_dict.get("incidents", []))
                perm_cnt = len(d_dict.get("permits", []))
                biz_cnt = len(d_dict.get("businesses", []))
                city_total = inc_cnt + perm_cnt + biz_cnt

                analysis_result["metrics_by_city"][city] = {
                    "incidents_count": inc_cnt,
                    "permits_count": perm_cnt,
                    "businesses_count": biz_cnt,
                    "city_total": city_total,
                    "sample_records": {k: v[:2] for k, v in d_dict.items() if v}
                }

                analysis_result["totals"]["total_incidents"] += inc_cnt
                analysis_result["totals"]["total_permits"] += perm_cnt
                analysis_result["totals"]["total_businesses"] += biz_cnt
                analysis_result["totals"]["grand_total"] += city_total

            sm.success({"analysis_completed_at": datetime.now(timezone.utc).isoformat()})
            return _save_transition(job_id, sm, result_data=analysis_result)
        except Exception as e:
            sm.failure(str(e))
            return _save_transition(job_id, sm, error_message=str(e))

    return db.get_pipeline_job(job_id)

def submit_and_dispatch_job(job_id: str, async_mode: bool = True) -> Dict[str, Any]:
    """Submits a job and queues it for execution."""
    if async_mode:
        job_executor.submit(run_job_pipeline_step_by_step, job_id)
        # Give worker a tiny slice to transition to submitted/queued
        import time
        time.sleep(0.05)
        return db.get_pipeline_job(job_id)
    else:
        return run_job_pipeline_step_by_step(job_id)

def cancel_pipeline_job(job_id: str, reason: str = "Cancelled by user") -> Dict[str, Any]:
    """
    Cancel an active job using the exact diagram semantics:
    - If Draft or Queued: triggers 'cancel()'
    - If Fetching or Analyzing: triggers 'delete()'
    - Follows up with 'notifyUser' -> FinalState
    """
    job = db.get_pipeline_job(job_id)
    if not job:
        raise ValueError(f"Job '{job_id}' not found.")

    sm = _get_sm(job)
    if sm.state == JobState.SUBMITTED:
        sm.validation_ok({"reason": "Validated before cancellation"})
        sm.cancel(reason=reason)
    elif sm.state in [JobState.DRAFT, JobState.QUEUED]:
        sm.cancel(reason=reason)
    elif sm.state in [JobState.FETCHING, JobState.ANALYZING]:
        sm.delete(reason=reason)
    elif sm.state == JobState.CANCELLED:
        pass
    else:
        raise ValueError(f"Cannot cancel job in '{sm.state.value}' state.")

    # Apply notifyUser to reach terminal FinalState as per diagram
    if sm.state == JobState.CANCELLED:
        sm.notify_user({"notification_sent_to": job.get("user_email")})

    return _save_transition(job_id, sm)

def retry_failed_job(job_id: str) -> Dict[str, Any]:
    """
    Recovers a failed job back to Draft as modeled in the diagram:
    - FailedValidation -> Error -> Draft
    - FailedExecution -> failure -> Draft
    """
    job = db.get_pipeline_job(job_id)
    if not job:
        raise ValueError(f"Job '{job_id}' not found.")

    sm = _get_sm(job)
    if sm.state == JobState.FAILED_VALIDATION:
        sm.error({"recovered_from": "FailedValidation"})
    elif sm.state == JobState.FAILED_EXECUTION:
        sm.failure(error_message="Recovering from FailedExecution to Draft")
    else:
        raise ValueError(f"Job in state '{sm.state.value}' cannot be retried (only FailedValidation or FailedExecution).")

    return _save_transition(job_id, sm)

def archive_completed_job(job_id: str) -> Dict[str, Any]:
    """
    Applies archivePolicy to transition Completed -> Archived (Terminal)
    """
    job = db.get_pipeline_job(job_id)
    if not job:
        raise ValueError(f"Job '{job_id}' not found.")

    sm = _get_sm(job)
    if sm.state != JobState.COMPLETED:
        raise ValueError(f"Only Completed jobs can be archived (current state: '{sm.state.value}').")

    sm.archive_policy({"archived_at": datetime.now(timezone.utc).isoformat()})
    return _save_transition(job_id, sm)
