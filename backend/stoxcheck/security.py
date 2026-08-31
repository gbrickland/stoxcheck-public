"""Small HTTP hardening controls shared by every public API response."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from fastapi import Header, HTTPException


MAX_REQUEST_BYTES = 64 * 1024


def verified_firebase_user(authorization: str | None = Header(default=None)) -> dict:
    """Verify a Firebase bearer token when production authentication is enabled.

    Local tests and connection-free development remain possible with the default false setting.
    Production sets REQUIRE_FIREBASE_AUTH=true so hiding the UI cannot be bypassed by calling the
    Cloud Run URL directly.
    """
    from .config import settings
    if not settings.require_firebase_auth:
        return {"uid": "local-development"}
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "A Firebase sign-in token is required.")
    try:
        import firebase_admin
        from firebase_admin import auth
        if not firebase_admin._apps:
            firebase_admin.initialize_app(options={"projectId": settings.google_cloud_project or None})
        claims = auth.verify_id_token(authorization.removeprefix("Bearer ").strip(), check_revoked=True)
        if claims.get("stoxcheck_access") is not True:
            raise HTTPException(403, "This Firebase account is not approved for Stoxcheck.")
        return claims
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(401, "The Firebase sign-in token is invalid or expired.") from error


class SecurityMiddleware(BaseHTTPMiddleware):
    """Reject clearly oversized bodies and attach browser-facing security headers.

    Cloud Run and the application still enforce their own time and memory limits. This early bound
    prevents an ordinary manual-prediction request from allocating an unexpectedly large body.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        raw_length = request.headers.get("content-length")
        if raw_length:
            try:
                if int(raw_length) > MAX_REQUEST_BYTES:
                    return self._harden(JSONResponse(
                        status_code=413,
                        content={"detail": f"Request body exceeds {MAX_REQUEST_BYTES} bytes."},
                    ))
            except ValueError:
                return self._harden(JSONResponse(
                    status_code=400,
                    content={"detail": "Invalid Content-Length header."},
                ))

        return self._harden(await call_next(request))

    @staticmethod
    def _harden(response: Response) -> Response:
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response
