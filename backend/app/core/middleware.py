import json

from starlette.types import ASGIApp, Message, Receive, Scope, Send

UPLOAD_PATHS = {"/api/v1/resumes", "/api/v1/resumes/bulk"}


class _BodyTooLarge(Exception):
    pass


class BodySizeLimitMiddleware:
    """Rejects oversized request bodies before they are fully read."""

    def __init__(self, app: ASGIApp, *, upload_limit: int, default_limit: int) -> None:
        self.app = app
        self.upload_limit = upload_limit
        self.default_limit = default_limit

    def _limit(self, scope: Scope) -> int:
        is_upload = scope["method"] == "POST" and scope["path"].rstrip("/") in UPLOAD_PATHS
        return self.upload_limit if is_upload else self.default_limit

    @staticmethod
    async def _reject(send: Send) -> None:
        body = json.dumps({"detail": "Request body too large"}).encode()
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode()),
                    (b"connection", b"close"),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        limit = self._limit(scope)
        declared = dict(scope["headers"]).get(b"content-length")
        if declared is not None and declared.isdigit() and int(declared) > limit:
            await self._reject(send)  # the client told us it is too big, so do not read anything
            return

        received = 0
        response_started = False

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:  # chunked uploads that lie or give no length
                    raise _BodyTooLarge
            return message

        async def tracking_send(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, tracking_send)
        except _BodyTooLarge:
            if not response_started:
                await self._reject(send)


class SecurityHeadersMiddleware:
    """Adds safe default headers to every response without overriding ones already set."""

    HEADERS = [
        (b"x-content-type-options", b"nosniff"),
        (b"x-frame-options", b"DENY"),
        (b"referrer-policy", b"no-referrer"),
        (b"cache-control", b"no-store"),  # responses can contain personal data
    ]

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                present = {name.lower() for name, _ in headers}
                headers.extend(h for h in self.HEADERS if h[0] not in present)
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_with_headers)