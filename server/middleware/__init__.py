from fastapi import FastAPI
from server.middleware.cors import setup_cors
from server.middleware.logging import RequestLoggingMiddleware
from server.middleware.request_id import RequestIdMiddleware


def setup_middlewares(app: FastAPI) -> None:
    # 1. Request ID Middleware
    app.add_middleware(RequestIdMiddleware)

    # 2. Structured Request Logging Middleware
    app.add_middleware(RequestLoggingMiddleware)

    # 3. CORS
    setup_cors(app)


__all__ = ["setup_middlewares", "RequestIdMiddleware", "RequestLoggingMiddleware", "setup_cors"]
