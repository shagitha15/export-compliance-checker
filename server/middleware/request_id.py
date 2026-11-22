"""
Request ID Tracking ASGI Middleware.
"""

import uuid
from starlette.types import ASGIApp, Scope, Receive, Send


class RequestIdMiddleware:
    """
    Pure ASGI middleware for attaching and propagating X-Request-ID.
    """

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        req_id = headers.get(b"x-request-id", None)
        if req_id:
            request_id = req_id.decode("latin1")
        else:
            request_id = f"req_{uuid.uuid4().hex[:12]}"

        # Store in ASGI scope state
        if "state" not in scope:
            scope["state"] = {}
        scope["state"]["request_id"] = request_id

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                resp_headers = list(message.get("headers", []))
                resp_headers.append((b"x-request-id", request_id.encode("latin1")))
                message["headers"] = resp_headers
            await send(message)

        await self.app(scope, receive, send_wrapper)
