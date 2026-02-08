from __future__ import annotations

from starlette.responses import PlainTextResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from .deps import settings


class BodySizeLimitMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.limit = settings.BODY_SIZE_LIMIT_BYTES

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:  # type: ignore[override]
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        content_length_header = None
        for name, value in scope.get("headers", []):
            if name == b"content-length":
                content_length_header = int(value.decode("latin-1"))
                break

        if content_length_header is not None and content_length_header > self.limit:
            response = PlainTextResponse("payload too large", status_code=413)
            await response(scope, receive, send)
            return

        received = 0

        async def limited_receive() -> dict:
            nonlocal received
            message = await receive()
            if message.get("type") == "http.request":
                body = message.get("body", b"")
                received += len(body)
                if received > self.limit:
                    return {"type": "http.disconnect"}
            return message

        await self.app(scope, limited_receive, send)


