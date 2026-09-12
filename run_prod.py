"""
Argus Production Server Launcher.
Runs the application on the multi-threaded Waitress WSGI server with production configuration.
"""
import os
import sys
import logging
from waitress import serve
from wsgi import app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("argus.production")

def run_production_server():
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", 5000))
    threads = int(os.environ.get("WEB_CONCURRENCY", 8))

    print("=" * 72)
    print("  ARGUS MUNICIPAL OPEN DATA PLATFORM — PRODUCTION WSGI SERVER")
    print(f"  * Host: {host}  |  Port: {port}  |  Worker Threads: {threads}")
    print("  * Municipalities: Las Vegas (NV), Los Angeles (CA), Seattle (WA), Phoenix (AZ)")
    print("  * Server Engine: Waitress Production Server")
    print("  * Parallel Orchestration: Active ThreadPoolExecutor (max_workers=8)")
    print("  * Caching & Concurrency: Thread-Safe LRU, Atomic Rate Limiting")
    print("=" * 72)

    serve(
        app,
        host=host,
        port=port,
        threads=threads,
        connection_limit=500,
        channel_timeout=30,
        cleanup_interval=30
    )

if __name__ == "__main__":
    run_production_server()
