"""
HTTP Request & Latency Logging ASGI Middleware.
"""

import time
from starlette.types import ASGIApp, Scope, Receive, Send
from server.logging.logger import logger


class RequestLoggingMiddleware:
    """
    Pure ASGI middleware for logging request method, path, status, and duration.
    """

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start_time = time.perf_counter()
        request_id = scope.get("state", {}).get("request_id", "-")
        method = scope.get("method", "")
        path = scope.get("path", "")
        status_code = [500]

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status_code[0] = message.get("status", 500)
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.info(
                "[%s] %s %s -> %s (%.2f ms)",
                request_id,
                method,
                path,
                status_code[0],
                duration_ms,
            )
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                "[%s] %s %s FAILED in %.2f ms: %s",
                request_id,
                method,
                path,
                duration_ms,
                exc,
            )
            raise exc
