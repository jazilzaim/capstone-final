from flask import request, jsonify, g
from app.routes.api_v1 import api_v1_bp
from app.models.storage import db
from app.core.exceptions import APIError, NotFoundError
from app.core.state_machine import JobStateMachine, JobState
from app.services.job_worker import (
    submit_and_dispatch_job,
    cancel_pipeline_job,
    retry_failed_job,
    archive_completed_job,
    transition_job
)

@api_v1_bp.route("/jobs", methods=["GET"])
def list_jobs():
    """List data pipeline jobs."""
    user_email = request.args.get("email")
    if not user_email and hasattr(g, "api_key_info") and g.api_key_info:
        user_email = g.api_key_info.get("email")

    limit = request.args.get("limit", 50, type=int)
    jobs = db.list_pipeline_jobs(user_email=user_email, limit=limit)
    return jsonify({
        "status": "success",
        "count": len(jobs),
        "data": jobs
    })

@api_v1_bp.route("/jobs", methods=["POST"])
def create_job():
    """Create a new data pipeline job in Draft state."""
    data = request.get_json(silent=True) or {}
    name = data.get("name", "Multi-City Analytics Pipeline").strip()
    cities = data.get("cities", ["las_vegas", "los_angeles", "seattle", "phoenix"])
    datasets = data.get("datasets", ["incidents", "permits"])
    query_params = data.get("query_params", {"limit": 10})
    auto_submit = bool(data.get("auto_submit", False))

    user_email = data.get("email")
    if not user_email and hasattr(g, "api_key_info") and g.api_key_info:
        user_email = g.api_key_info.get("email")
    if not user_email:
        user_email = "developer@argus.dev"

    job = db.create_pipeline_job(
        user_email=user_email,
        name=name,
        cities=cities,
        datasets=datasets,
        query_params=query_params,
        initial_status="Draft"
    )

    if auto_submit:
        job = submit_and_dispatch_job(job["job_id"], async_mode=True)

    return jsonify({
        "status": "success",
        "message": f"Pipeline job '{job['job_id']}' created successfully.",
        "data": job
    }), 201

@api_v1_bp.route("/jobs/<job_id>", methods=["GET"])
def get_job(job_id: str):
    """Retrieve full details, state history, and results of a pipeline job."""
    job = db.get_pipeline_job(job_id)
    if not job:
        raise NotFoundError(f"Pipeline job '{job_id}' not found.")

    sm = JobStateMachine(initial_state=JobState(job["status"]), history=job.get("history", []))
    job["state_machine_info"] = sm.to_dict()

    return jsonify({
        "status": "success",
        "data": job
    })

@api_v1_bp.route("/jobs/<job_id>/submit", methods=["POST"])
def submit_job(job_id: str):
    """Submit a draft job for validation and worker execution."""
    job = db.get_pipeline_job(job_id)
    if not job:
        raise NotFoundError(f"Pipeline job '{job_id}' not found.")

    async_mode = request.args.get("async", "true").lower() in ["true", "1", "yes"]
    updated_job = submit_and_dispatch_job(job_id, async_mode=async_mode)
    return jsonify({
        "status": "success",
        "message": f"Job '{job_id}' submitted successfully.",
        "data": updated_job
    })

@api_v1_bp.route("/jobs/<job_id>/transition", methods=["POST"])
def trigger_transition(job_id: str):
    """Manually apply an event from the UML State Machine."""
    data = request.get_json(silent=True) or {}
    event_name = data.get("event")
    if not event_name:
        raise APIError("Field 'event' is required (e.g. submit, cancel, delete, archivePolicy, etc.).", status_code=400)

    metadata = data.get("metadata", {})
    updated_job = transition_job(job_id, event_name, metadata)
    return jsonify({
        "status": "success",
        "message": f"Transition '{event_name}' applied successfully.",
        "data": updated_job
    })

@api_v1_bp.route("/jobs/<job_id>/cancel", methods=["POST"])
def cancel_job_endpoint(job_id: str):
    """Cancel job (applies cancel/delete and notifyUser to reach terminal FinalState)."""
    data = request.get_json(silent=True) or {}
    reason = data.get("reason", "Cancelled via API")
    updated_job = cancel_pipeline_job(job_id, reason=reason)
    return jsonify({
        "status": "success",
        "message": f"Job '{job_id}' cancelled.",
        "data": updated_job
    })

@api_v1_bp.route("/jobs/<job_id>/retry", methods=["POST"])
def retry_job_endpoint(job_id: str):
    """Recover a FailedValidation or FailedExecution job back to Draft."""
    updated_job = retry_failed_job(job_id)
    return jsonify({
        "status": "success",
        "message": f"Job '{job_id}' recovered back to Draft state.",
        "data": updated_job
    })

@api_v1_bp.route("/jobs/<job_id>/archive", methods=["POST"])
def archive_job_endpoint(job_id: str):
    """Archive a Completed job to reach Archived (Terminal)."""
    updated_job = archive_completed_job(job_id)
    return jsonify({
        "status": "success",
        "message": f"Job '{job_id}' archived.",
        "data": updated_job
    })
