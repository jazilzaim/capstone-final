from flask import jsonify

class APIError(Exception):
    """Base API Exception for structured error payloads."""
    def __init__(self, message, status_code=400, code="BAD_REQUEST", details=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.details = details or {}

    def to_dict(self):
        rv = {
            "status": "error",
            "error": {
                "code": self.code,
                "message": self.message
            }
        }
        if self.details:
            rv["error"]["details"] = self.details
        return rv

class UnauthorizedError(APIError):
    def __init__(self, message="Invalid or missing API key. Provide via 'X-API-Key' header or '?api_key=' parameter.", details=None):
        super().__init__(message, status_code=401, code="UNAUTHORIZED", details=details)

class ForbiddenError(APIError):
    def __init__(self, message="Your API key does not have permission for this resource.", details=None):
        super().__init__(message, status_code=403, code="FORBIDDEN", details=details)

class RateLimitExceededError(APIError):
    def __init__(self, message="API rate limit exceeded for your tier.", details=None):
        super().__init__(message, status_code=429, code="RATE_LIMIT_EXCEEDED", details=details)

class NotFoundError(APIError):
    def __init__(self, message="The requested resource was not found.", details=None):
        super().__init__(message, status_code=404, code="NOT_FOUND", details=details)

class UpstreamServiceError(APIError):
    def __init__(self, message="Municipal open data service temporarily unavailable.", details=None):
        super().__init__(message, status_code=502, code="UPSTREAM_SERVICE_ERROR", details=details)

def register_error_handlers(app):
    @app.errorhandler(APIError)
    def handle_api_error(err):
        response = jsonify(err.to_dict())
        response.status_code = err.status_code
        return response

    @app.errorhandler(404)
    def handle_404(err):
        response = jsonify({
            "status": "error",
            "error": {
                "code": "ENDPOINT_NOT_FOUND",
                "message": "The requested route does not exist. Check /docs for available endpoints."
            }
        })
        response.status_code = 404
        return response

    @app.errorhandler(500)
    def handle_500(err):
        response = jsonify({
            "status": "error",
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred. Our engineering team has been notified."
            }
        })
        response.status_code = 500
        return response
