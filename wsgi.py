"""
WSGI Application entry point for Argus API.
Suitable for Waitress, Gunicorn, uWSGI, or AWS/GCP serverless environments.
"""
from app import create_app
from app.core.cache import cache

app = create_app()

# Warm up baseline cache on startup for instant zero-latency responses
cache.warm_cache()

if __name__ == "__main__":
    app.run()
