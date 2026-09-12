from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.connectors.registry import registry
from app.models.storage import db
from app.core.cache import cache
from app.core.auth import login_required, get_current_user
from app.services.job_worker import (
    submit_and_dispatch_job,
    cancel_pipeline_job,
    retry_failed_job,
    archive_completed_job,
    transition_job
)

web_bp = Blueprint("web", __name__, template_folder="../templates")

# ---------------------------------------------------------
# Public Website & Docs
# ---------------------------------------------------------
@web_bp.route("/")
def index():
    stats = db.get_system_stats()
    cities = [c.to_dict() for c in registry.get_all_cities_info()]
    return render_template("index.html", stats=stats, cities=cities)

@web_bp.route("/playground")
def playground():
    cities = [c.to_dict() for c in registry.get_all_cities_info()]
    return render_template("playground.html", cities=cities)

@web_bp.route("/docs")
def documentation():
    cities = [c.to_dict() for c in registry.get_all_cities_info()]
    return render_template("documentation.html", cities=cities)

@web_bp.route("/status")
def status():
    cities = [c.to_dict() for c in registry.get_all_cities_info()]
    cache_stats = cache.stats()
    system_stats = db.get_system_stats()
    return render_template("status.html", cities=cities, cache_stats=cache_stats, system_stats=system_stats)

@web_bp.route("/keys")
def keys():
    return render_template("keys.html")

# ---------------------------------------------------------
# User Authentication Routes
# ---------------------------------------------------------
@web_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user"):
        return redirect(url_for("web.dashboard_overview"))

    next_url = request.args.get("next") or request.form.get("next") or url_for("web.dashboard_overview")
    # Sanitize next_url to prevent open redirect
    if not next_url.startswith("/"):
        next_url = url_for("web.dashboard_overview")

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Please enter both email and password.", "error")
            return render_template("login.html", email=email, next=next_url), 400

        user = db.authenticate_user(email, password)
        if user:
            session["user"] = user
            flash(f"Welcome back, {user['name']}!", "success")
            return redirect(next_url)
        else:
            flash("Invalid email or password. You can use the Demo Developer button below.", "error")
            return render_template("login.html", email=email, next=next_url), 401

    return render_template("login.html", next=next_url)

@web_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if session.get("user"):
        return redirect(url_for("web.dashboard_overview"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not name or not email or not password:
            flash("All fields are required to create a developer account.", "error")
            return render_template("signup.html", name=name, email=email), 400

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "error")
            return render_template("signup.html", name=name, email=email), 400

        try:
            user = db.register_user(name=name, email=email, password=password)
            session["user"] = {
                "id": user["id"],
                "name": user["name"],
                "email": user["email"]
            }
            flash("Account registered successfully! Your sandbox API key has been provisioned.", "success")
            return redirect(url_for("web.dashboard_overview"))
        except ValueError as e:
            flash(str(e), "error")
            return render_template("signup.html", name=name, email=email), 400

    return render_template("signup.html")

@web_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been signed out.", "info")
    return redirect(url_for("web.index"))

# ---------------------------------------------------------
# Stripe Developer Dashboard Routes (Protected)
# ---------------------------------------------------------
@web_bp.route("/dashboard")
@login_required
def dashboard_overview():
    stats = db.get_system_stats()
    cities = [c.to_dict() for c in registry.get_all_cities_info()]
    logs = db.get_recent_logs(limit=15)
    return render_template("dashboard/overview.html", stats=stats, cities=cities, logs=logs)

@web_bp.route("/dashboard/logs")
@login_required
def dashboard_logs():
    city_filter = request.args.get("city")
    status_filter = request.args.get("status")
    status_code = int(status_filter) if status_filter and status_filter.isdigit() else None
    logs = db.get_recent_logs(limit=50, city_filter=city_filter, status_filter=status_code)
    cities = [c.to_dict() for c in registry.get_all_cities_info()]
    return render_template("dashboard/logs.html", logs=logs, cities=cities)

@web_bp.route("/dashboard/workbench")
@login_required
def dashboard_workbench():
    cities = [c.to_dict() for c in registry.get_all_cities_info()]
    return render_template("dashboard/workbench.html", cities=cities)

@web_bp.route("/dashboard/keys")
@login_required
def dashboard_keys():
    current_u = get_current_user()
    user_email = current_u.get("email") if current_u else None
    user_keys = db.get_user_keys(user_email)
    return render_template("dashboard/keys.html", user_keys=user_keys)

@web_bp.route("/dashboard/connectors")
@login_required
def dashboard_connectors():
    return redirect("/status")

@web_bp.route("/dashboard/jobs")
@login_required
def dashboard_jobs():
    current_u = get_current_user()
    user_email = current_u.get("email") if current_u else None
    jobs = db.list_pipeline_jobs(user_email=user_email)
    cities = [c.to_dict() for c in registry.get_all_cities_info()]
    return render_template("dashboard/jobs.html", jobs=jobs, cities=cities)

@web_bp.route("/dashboard/jobs/new", methods=["POST"])
@login_required
def dashboard_jobs_new():
    current_u = get_current_user()
    user_email = current_u.get("email") if current_u else "developer@argus.dev"

    name = request.form.get("name", "Multi-City Analytics Pipeline").strip()
    selected_cities = request.form.getlist("cities")
    if not selected_cities:
        selected_cities = ["las_vegas", "los_angeles", "seattle", "phoenix"]

    selected_datasets = request.form.getlist("datasets")
    if not selected_datasets:
        selected_datasets = ["incidents", "permits"]

    limit = int(request.form.get("limit", 15))
    auto_submit = request.form.get("auto_submit") == "1"

    job = db.create_pipeline_job(
        user_email=user_email,
        name=name,
        cities=selected_cities,
        datasets=selected_datasets,
        query_params={"limit": limit},
        initial_status="Draft"
    )

    if auto_submit:
        submit_and_dispatch_job(job["job_id"], async_mode=True)
        flash(f"Job '{job['name']}' created and submitted to queue!", "success")
    else:
        flash(f"Job '{job['name']}' created in Draft state. You can review and submit whenever ready.", "info")

    return redirect(url_for("web.dashboard_jobs"))

@web_bp.route("/dashboard/jobs/<job_id>/action", methods=["POST"])
@login_required
def dashboard_jobs_action(job_id: str):
    action = request.form.get("action")
    try:
        if action == "submit":
            submit_and_dispatch_job(job_id, async_mode=True)
            flash(f"Job '{job_id}' submitted!", "success")
        elif action == "cancel":
            cancel_pipeline_job(job_id, reason="Cancelled from Dashboard")
            flash(f"Job '{job_id}' cancelled.", "warning")
        elif action == "retry":
            retry_failed_job(job_id)
            flash(f"Job '{job_id}' recovered to Draft.", "info")
        elif action == "archive":
            archive_completed_job(job_id)
            flash(f"Job '{job_id}' archived.", "success")
        elif action == "transition":
            event = request.form.get("event")
            transition_job(job_id, event)
            flash(f"Transition '{event}' applied to job.", "info")
        else:
            flash(f"Unknown action '{action}'.", "error")
    except Exception as e:
        flash(f"Action failed: {str(e)}", "error")

    return redirect(url_for("web.dashboard_jobs"))


