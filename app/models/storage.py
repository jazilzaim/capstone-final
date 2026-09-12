import sqlite3
import secrets
import json
import time
import logging
import threading
import concurrent.futures
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple
from werkzeug.security import generate_password_hash, check_password_hash
from app.config import Config

logger = logging.getLogger(__name__)

class Storage:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or Config.DB_PATH
        self.supabase_client = None
        self._key_cache: Dict[str, Tuple[Dict[str, Any], float]] = {}
        self._key_cache_lock = threading.Lock()
        self._bg_pool = concurrent.futures.ThreadPoolExecutor(max_workers=4, thread_name_prefix="ArgusStorageBg")
        self._disabled_supabase_tables = set()
        self._init_supabase()
        self._init_db()

    def _init_supabase(self):
        """Initialize Supabase client if credentials are configured in .env."""
        if Config.SUPABASE_URL and Config.SUPABASE_KEY:
            try:
                from supabase import create_client
                self.supabase_client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
                logger.info("Connected to Supabase PostgreSQL cloud database.")
            except Exception as e:
                logger.warning(f"Could not connect to Supabase: {e}. Falling back to SQLite.")
                self.supabase_client = None

    def is_supabase_active(self) -> bool:
        return self.supabase_client is not None

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    name TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key_hash TEXT UNIQUE NOT NULL,
                    key_prefix TEXT NOT NULL,
                    name TEXT NOT NULL,
                    email TEXT,
                    tier TEXT NOT NULL DEFAULT 'free',
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_requests INTEGER DEFAULT 0,
                    last_used_at TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS usage_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id TEXT,
                    method TEXT DEFAULT 'GET',
                    key_prefix TEXT,
                    endpoint TEXT NOT NULL,
                    city TEXT,
                    query_params TEXT,
                    status_code INTEGER NOT NULL,
                    latency_ms REAL NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pipeline_jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT UNIQUE NOT NULL,
                    user_email TEXT NOT NULL,
                    name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    cities_json TEXT NOT NULL,
                    datasets_json TEXT NOT NULL,
                    query_params_json TEXT DEFAULT '{}',
                    result_json TEXT,
                    error_message TEXT,
                    history_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

            # Seed demo user
            self._seed_demo_user(cursor, conn)
            # Seed demo keys if not present
            self._seed_demo_keys(cursor, conn)
            # Seed initial sample request logs if table is empty
            self._seed_initial_logs(cursor, conn)

    def _seed_demo_user(self, cursor, conn):
        demo_users = [
            ("developer@argus.dev", "Demo Developer"),
            ("developer@civicpulse.dev", "Demo Developer")
        ]
        for demo_email, name in demo_users:
            cursor.execute("SELECT id FROM users WHERE email = ?", (demo_email,))
            if not cursor.fetchone():
                hashed = generate_password_hash("Password123!")
                cursor.execute(
                    "INSERT INTO users (email, password_hash, name) VALUES (?, ?, ?)",
                    (demo_email, hashed, name)
                )
        conn.commit()

    def _seed_initial_logs(self, cursor, conn):
        cursor.execute("SELECT COUNT(*) as cnt FROM usage_logs")
        if cursor.fetchone()["cnt"] == 0:
            sample_logs = [
                ("req_01HV789A", "GET", "argus_demo_free", "/api/v1/incidents", "las_vegas", "city=las_vegas&limit=10", 200, 14.2),
                ("req_01HV789B", "GET", "argus_demo_pro", "/api/v1/incidents", "los_angeles", "city=los_angeles&category=Property+Crime", 200, 18.6),
                ("req_01HV789C", "GET", "argus_demo_free", "/api/v1/permits", "seattle", "city=seattle&limit=5", 200, 22.4),
                ("req_01HV789D", "GET", "argus_demo_ent", "/api/v1/analytics/summary", None, "", 200, 31.8),
                ("req_01HV789E", "GET", "argus_demo_free", "/api/v1/incidents", "phoenix", "city=phoenix&limit=15", 200, 16.9),
                ("req_01HV789F", "GET", None, "/api/v1/incidents", "seattle", "city=seattle", 401, 1.2),
                ("req_01HV789G", "GET", "argus_demo_free", "/api/v1/businesses", "los_angeles", "city=los_angeles&limit=8", 200, 19.5),
                ("req_01HV789H", "GET", "argus_demo_pro", "/api/v1/cities", None, "", 200, 24.1),
            ]
            for rid, method, prefix, ep, city, qp, code, lat in sample_logs:
                cursor.execute("""
                    INSERT INTO usage_logs (request_id, method, key_prefix, endpoint, city, query_params, status_code, latency_ms)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (rid, method, prefix, ep, city, qp, code, lat))
            conn.commit()

    def _seed_demo_keys(self, cursor, conn):
        demo_keys = [
            ("argus_demo_free_key_2026", "argus_demo_free", "Free Explorer Demo", "developer@argus.dev", "free"),
            ("argus_demo_pro_key_2026", "argus_demo_pro", "Professional Developer Demo", "developer@argus.dev", "developer"),
            ("argus_demo_enterprise_key_2026", "argus_demo_ent", "Enterprise Demo", "enterprise@argus.dev", "enterprise"),
            ("civic_demo_free_key_2026", "civic_demo_free", "Free Explorer Demo", "developer@civicpulse.dev", "free"),
            ("civic_demo_pro_key_2026", "civic_demo_pro", "Professional Developer Demo", "developer@civicpulse.dev", "developer"),
            ("civic_demo_enterprise_key_2026", "civic_demo_ent", "Enterprise Demo", "enterprise@civicpulse.dev", "enterprise")
        ]
        for full_key, prefix, name, email, tier in demo_keys:
            cursor.execute("""
                INSERT OR IGNORE INTO api_keys (key_hash, key_prefix, name, email, tier)
                VALUES (?, ?, ?, ?, ?)
            """, (full_key, prefix, name, email, tier))
        conn.commit()

    def create_api_key(self, name: str, email: str, tier: str = "free") -> Dict[str, Any]:
        """Generate a new API key with argus_ prefix."""
        token = secrets.token_urlsafe(24)
        full_key = f"argus_{tier}_{token}"
        prefix = full_key[:16]

        # 1. Write to local SQLite for immediate consistency and instant queries
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO api_keys (key_hash, key_prefix, name, email, tier)
                VALUES (?, ?, ?, ?, ?)
            """, (full_key, prefix, name, email, tier))
            conn.commit()

        now_iso = datetime.now(timezone.utc).isoformat()
        key_record = {
            "key_hash": full_key,
            "key_prefix": prefix,
            "name": name,
            "email": email,
            "tier": tier,
            "is_active": 1,
            "total_requests": 0,
            "created_at": now_iso
        }

        # Cache immediately in memory
        with self._key_cache_lock:
            self._key_cache[full_key] = (key_record, time.time() + 300.0)

        # 2. Asynchronously sync to Supabase in background
        if self.supabase_client and "api_keys" not in self._disabled_supabase_tables:
            def _async_insert_key():
                try:
                    data = {
                        "key_hash": full_key,
                        "key_prefix": prefix,
                        "name": name,
                        "email": email,
                        "tier": tier,
                        "is_active": True,
                        "total_requests": 0
                    }
                    self.supabase_client.table("api_keys").insert(data).execute()
                except Exception as e:
                    err_str = str(e)
                    if "PGRST205" in err_str or "schema cache" in err_str:
                        self._disabled_supabase_tables.add("api_keys")
                    logger.warning(f"Supabase key insert notice: {e}")
            self._bg_pool.submit(_async_insert_key)

        return {
            "api_key": full_key,
            "prefix": prefix,
            "name": name,
            "email": email,
            "tier": tier,
            "rate_limit_per_min": Config.TIER_LIMITS.get(tier, 30),
            "storage": "supabase" if self.supabase_client else "sqlite"
        }

    def get_key_info(self, api_key: str) -> Optional[Dict[str, Any]]:
        now = time.time()
        # Fast path: check in-memory cache
        with self._key_cache_lock:
            cached = self._key_cache.get(api_key)
            if cached and cached[1] > now:
                return cached[0]

        info = None
        # 1. Fast local SQLite lookup
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, key_prefix, name, email, tier, is_active, created_at, total_requests, last_used_at
                FROM api_keys
                WHERE key_hash = ? AND is_active = 1
            """, (api_key,))
            row = cursor.fetchone()
            if row:
                info = dict(row)

        # 2. Fallback to Supabase if not found in SQLite
        if not info and self.supabase_client and "api_keys" not in self._disabled_supabase_tables:
            try:
                resp = self.supabase_client.table("api_keys") \
                    .select("*") \
                    .eq("key_hash", api_key) \
                    .eq("is_active", True) \
                    .limit(1) \
                    .execute()
                if resp.data and len(resp.data) > 0:
                    info = resp.data[0]
            except Exception as e:
                err_str = str(e)
                if "PGRST205" in err_str or "schema cache" in err_str:
                    self._disabled_supabase_tables.add("api_keys")
                logger.warning(f"Supabase get_key_info notice: {e}")

        if info:
            with self._key_cache_lock:
                self._key_cache[api_key] = (info, now + 120.0)  # cache for 2 minutes
        return info

    def record_usage(
        self,
        key_prefix: Optional[str],
        endpoint: str,
        city: Optional[str],
        status_code: int,
        latency_ms: float,
        method: str = "GET",
        query_params: str = "",
        request_id: Optional[str] = None
    ):
        req_id = request_id or f"req_{secrets.token_hex(6)}"

        # 1. Immediate local SQLite logging
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO usage_logs (request_id, method, key_prefix, endpoint, city, query_params, status_code, latency_ms)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (req_id, method, key_prefix, endpoint, city, query_params, status_code, latency_ms))
                if key_prefix:
                    cursor.execute("""
                        UPDATE api_keys
                        SET total_requests = total_requests + 1,
                            last_used_at = CURRENT_TIMESTAMP
                        WHERE key_prefix = ?
                    """, (key_prefix,))
                conn.commit()
        except Exception:
            pass

        # 2. Asynchronous background dispatch to Supabase
        if self.supabase_client and "usage_logs" not in self._disabled_supabase_tables:
            def _async_supabase_log():
                try:
                    log_data = {
                        "request_id": req_id,
                        "method": method,
                        "key_prefix": key_prefix,
                        "endpoint": endpoint,
                        "city": city,
                        "query_params": query_params,
                        "status_code": status_code,
                        "latency_ms": latency_ms
                    }
                    self.supabase_client.table("usage_logs").insert(log_data).execute()
                except Exception as e:
                    err_str = str(e)
                    if "PGRST205" in err_str or "schema cache" in err_str:
                        self._disabled_supabase_tables.add("usage_logs")
            self._bg_pool.submit(_async_supabase_log)

    def get_recent_logs(self, limit: int = 50, city_filter: Optional[str] = None, status_filter: Optional[int] = None) -> List[Dict[str, Any]]:
        # 1. Try Supabase
        if self.supabase_client:
            try:
                q = self.supabase_client.table("usage_logs").select("*").order("id", desc=True).limit(limit)
                if city_filter:
                    q = q.eq("city", city_filter)
                if status_filter:
                    q = q.eq("status_code", status_filter)
                resp = q.execute()
                if resp.data:
                    return resp.data
            except Exception as e:
                logger.warning(f"Supabase get_recent_logs error: {e}")

        # 2. SQLite fallback
        query = "SELECT * FROM usage_logs"
        params = []
        conditions = []
        if city_filter:
            conditions.append("city = ?")
            params.append(city_filter)
        if status_filter:
            conditions.append("status_code = ?")
            params.append(status_filter)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)

        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(query, tuple(params))
            return [dict(row) for row in cursor.fetchall()]

    def get_system_stats(self) -> Dict[str, Any]:
        storage_type = "Supabase PostgreSQL" if self.supabase_client else "SQLite (Local)"
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as cnt FROM usage_logs")
            total_calls = cursor.fetchone()["cnt"]

            cursor.execute("SELECT COUNT(*) as cnt FROM api_keys")
            total_keys = cursor.fetchone()["cnt"]

            cursor.execute("SELECT AVG(latency_ms) as avg_lat FROM usage_logs WHERE timestamp >= datetime('now', '-24 hours')")
            avg_lat_row = cursor.fetchone()
            avg_latency = round(avg_lat_row["avg_lat"] or 18.5, 1)

            cursor.execute("""
                SELECT city, COUNT(*) as count
                FROM usage_logs
                WHERE city IS NOT NULL
                GROUP BY city
                ORDER BY count DESC
                LIMIT 5
            """)
            city_breakdown = {row["city"]: row["count"] for row in cursor.fetchall()}

        return {
            "total_api_calls": total_calls,
            "active_api_keys": total_keys,
            "avg_latency_ms": avg_latency,
            "calls_by_city": city_breakdown,
            "storage_backend": storage_type
        }

    def register_user(self, name: str, email: str, password: str) -> Dict[str, Any]:
        """Register a new developer user account."""
        name = name.strip()
        email = email.strip().lower()
        if not name or not email:
            raise ValueError("Name and email are required.")
        if len(password) < 6:
            raise ValueError("Password must be at least 6 characters long.")

        # Check if user exists locally
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
            if cursor.fetchone():
                raise ValueError("An account with this email address already exists.")

            # Attempt Supabase Auth registration if client is available
            if self.supabase_client:
                try:
                    self.supabase_client.auth.sign_up({
                        "email": email,
                        "password": password,
                        "options": {"data": {"name": name}}
                    })
                except Exception as e:
                    logger.warning(f"Supabase Auth signup notice: {e}")

            # Local storage registration
            password_hash = generate_password_hash(password)
            cursor.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                (name, email, password_hash)
            )
            user_id = cursor.lastrowid
            conn.commit()

        # Automatically issue an initial free API key for the new user
        key_res = self.create_api_key(name=f"{name}'s Default Key", email=email, tier="free")

        return {
            "id": user_id,
            "name": name,
            "email": email,
            "api_key": key_res["api_key"]
        }

    def authenticate_user(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user credentials against SQLite and Supabase."""
        email = email.strip().lower()

        # 1. Check local SQLite users
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, email, password_hash, name, created_at FROM users WHERE email = ?", (email,))
            row = cursor.fetchone()
            if row and check_password_hash(row["password_hash"], password):
                return {
                    "id": row["id"],
                    "email": row["email"],
                    "name": row["name"],
                    "created_at": str(row["created_at"])
                }

        # 2. Try Supabase Auth fallback if not found in SQLite
        if self.supabase_client:
            try:
                res = self.supabase_client.auth.sign_in_with_password({"email": email, "password": password})
                if res and res.user:
                    meta = getattr(res.user, "user_metadata", {}) or {}
                    name = meta.get("name") or email.split("@")[0].capitalize()
                    password_hash = generate_password_hash(password)
                    with self._get_conn() as conn:
                        cursor = conn.cursor()
                        cursor.execute(
                            "INSERT OR IGNORE INTO users (email, password_hash, name) VALUES (?, ?, ?)",
                            (email, password_hash, name)
                        )
                        conn.commit()
                    return self.get_user_by_email(email)
            except Exception as e:
                logger.warning(f"Supabase auth login check failed: {e}")

        return None

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        email = email.strip().lower()
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, email, name, created_at FROM users WHERE email = ?", (email,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, email, name, created_at FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_user_keys(self, email: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get API keys belonging to a user (or all keys if email is not specified)."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            if email:
                cursor.execute(
                    "SELECT * FROM api_keys WHERE email = ? ORDER BY id DESC",
                    (email.strip().lower(),)
                )
                user_keys = [dict(row) for row in cursor.fetchall()]
                # If user doesn't have custom keys yet, return user keys + demo keys
                if not user_keys:
                    cursor.execute("SELECT * FROM api_keys ORDER BY id ASC LIMIT 3")
                    return [dict(row) for row in cursor.fetchall()]
                return user_keys
            else:
                cursor.execute("SELECT * FROM api_keys ORDER BY id DESC LIMIT 50")
                return [dict(row) for row in cursor.fetchall()]

    # ---------------------------------------------------------
    # State Machine Pipeline Jobs
    # ---------------------------------------------------------
    def create_pipeline_job(
        self,
        user_email: str,
        name: str,
        cities: List[str],
        datasets: List[str],
        query_params: Optional[Dict[str, Any]] = None,
        initial_status: str = "Draft"
    ) -> Dict[str, Any]:
        job_id = f"job_{secrets.token_hex(6)}"
        now_iso = datetime.now(timezone.utc).isoformat()
        initial_history = [{
            "from_state": None,
            "to_state": initial_status,
            "event": "initial",
            "timestamp": now_iso,
            "metadata": {"created_by": user_email}
        }]

        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO pipeline_jobs (
                    job_id, user_email, name, status, cities_json, datasets_json, query_params_json, history_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job_id,
                user_email.strip().lower(),
                name.strip(),
                initial_status,
                json.dumps(cities),
                json.dumps(datasets),
                json.dumps(query_params or {}),
                json.dumps(initial_history),
                now_iso,
                now_iso
            ))
            conn.commit()

        return self.get_pipeline_job(job_id)

    def get_pipeline_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM pipeline_jobs WHERE job_id = ?", (job_id,))
            row = cursor.fetchone()
            if not row:
                return None
            data = dict(row)
            data["cities"] = json.loads(data["cities_json"])
            data["datasets"] = json.loads(data["datasets_json"])
            data["query_params"] = json.loads(data["query_params_json"]) if data.get("query_params_json") else {}
            data["result"] = json.loads(data["result_json"]) if data.get("result_json") else None
            data["history"] = json.loads(data["history_json"]) if data.get("history_json") else []
            return data

    def list_pipeline_jobs(self, user_email: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            if user_email:
                cursor.execute("""
                    SELECT * FROM pipeline_jobs WHERE user_email = ? ORDER BY id DESC LIMIT ?
                """, (user_email.strip().lower(), limit))
            else:
                cursor.execute("""
                    SELECT * FROM pipeline_jobs ORDER BY id DESC LIMIT ?
                """, (limit,))
            rows = cursor.fetchall()
            results = []
            for row in rows:
                data = dict(row)
                data["cities"] = json.loads(data["cities_json"])
                data["datasets"] = json.loads(data["datasets_json"])
                data["query_params"] = json.loads(data["query_params_json"]) if data.get("query_params_json") else {}
                data["result"] = json.loads(data["result_json"]) if data.get("result_json") else None
                data["history"] = json.loads(data["history_json"]) if data.get("history_json") else []
                results.append(data)
            return results

    def update_pipeline_job_state(
        self,
        job_id: str,
        new_status: str,
        history_entry: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        result_data: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        job = self.get_pipeline_job(job_id)
        if not job:
            return None

        history = job.get("history", [])
        if history_entry:
            history.append(history_entry)

        now_iso = datetime.now(timezone.utc).isoformat()
        result_json_str = json.dumps(result_data) if result_data is not None else (
            json.dumps(job["result"]) if job.get("result") is not None else None
        )

        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE pipeline_jobs
                SET status = ?,
                    history_json = ?,
                    error_message = ?,
                    result_json = ?,
                    updated_at = ?
                WHERE job_id = ?
            """, (
                new_status,
                json.dumps(history),
                error_message if error_message is not None else job.get("error_message"),
                result_json_str,
                now_iso,
                job_id
            ))
            conn.commit()

        return self.get_pipeline_job(job_id)

# Global storage instance
db = Storage()

