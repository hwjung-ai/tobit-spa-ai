"""
Security middleware for HTTPS, security headers, CORS, and CSRF protection.
"""

from __future__ import annotations

import secrets
from typing import Callable
from urllib.parse import urlparse

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse

from core.config import AppSettings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses."""

    def __init__(self, app: FastAPI, settings: AppSettings):
        super().__init__(app)
        self.settings = settings

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        if not self.settings.security_headers_enabled:
            return response

        # HSTS (HTTP Strict Transport Security)
        hsts_header = f"max-age={self.settings.hsts_max_age}"
        if self.settings.hsts_include_subdomains:
            hsts_header += "; includeSubDomains"
        response.headers["Strict-Transport-Security"] = hsts_header

        # CSP (Content Security Policy)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self' https:; "
            "frame-ancestors 'self'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )

        # X-Frame-Options (clickjacking protection)
        response.headers["X-Frame-Options"] = "SAMEORIGIN"

        # X-Content-Type-Options (MIME type sniffing protection)
        response.headers["X-Content-Type-Options"] = "nosniff"

        # X-XSS-Protection (XSS protection)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer-Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions-Policy (Feature Policy)
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), "
            "ambient-light-sensor=(), "
            "autoplay=(), "
            "battery=(), "
            "camera=(), "
            "cross-origin-isolated=(), "
            "display-capture=(), "
            "document-domain=(), "
            "encrypted-media=(), "
            "execution-while-not-rendered=(), "
            "execution-while-out-of-viewport=(), "
            "fullscreen=(), "
            "geolocation=(), "
            "gyroscope=(), "
            "magnetometer=(), "
            "microphone=(), "
            "midi=(), "
            "navigation-override=(), "
            "picture-in-picture=(), "
            "publickey-credentials-get=(), "
            "sync-xhr=(), "
            "usb=(), "
            "vr=(), "
            "xr-spatial-tracking=()"
        )

        return response


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """Middleware to redirect HTTP to HTTPS."""

    def __init__(self, app: FastAPI, settings: AppSettings):
        super().__init__(app)
        self.settings = settings

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip redirect for health checks
        if request.url.path in ["/health", "/healthz"]:
            return await call_next(request)

        # Skip in development mode
        if self.settings.app_env == "dev":
            return await call_next(request)

        # Only redirect if HTTPS is enabled and we're not already on HTTPS
        if self.settings.https_enabled and self.settings.https_redirect:
            if request.url.scheme == "http":
                url = request.url.replace(scheme="https")
                return RedirectResponse(url=url, status_code=301)

        return await call_next(request)


class CSRFMiddleware(BaseHTTPMiddleware):
    """Middleware for CSRF token generation and validation."""

    def __init__(self, app: FastAPI, settings: AppSettings):
        super().__init__(app)
        self.settings = settings
        self.token_length = 32

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not self.settings.csrf_protection_enabled:
            return await call_next(request)

        # Skip CSRF protection for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)

        # Generate CSRF token for GET requests (add to response)
        if request.method == "GET":
            response = await call_next(request)
            token = secrets.token_urlsafe(self.token_length)
            response.set_cookie(
                key="csrf_token",
                value=token,
                httponly=False,  # Must be accessible by JavaScript
                secure=self.settings.https_enabled,
                samesite="strict",
                max_age=3600,  # 1 hour
            )
            return response

        # Validate CSRF token for state-changing requests
        if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
            # Get token from cookie
            cookie_token = request.cookies.get("csrf_token")

            # Get token from header or body
            header_token = request.headers.get("X-CSRF-Token")

            # Try to get from body if form data
            body_token = None
            if request.headers.get("content-type", "").startswith("application/x-www-form-urlencoded"):
                try:
                    body = await request.body()
                    if body:
                        body_str = body.decode("utf-8")
                        for param in body_str.split("&"):
                            if param.startswith("csrf_token="):
                                body_token = param.split("=", 1)[1]
                                break
                except Exception:
                    pass

            provided_token = header_token or body_token

            # Skip CSRF check for certain conditions
            origin = request.headers.get("origin", "")
            referer = request.headers.get("referer", "")

            # Check if origin/referer is trusted
            is_trusted = False
            if origin:
                parsed_origin = urlparse(origin)
                origin_base = f"{parsed_origin.scheme}://{parsed_origin.netloc}"
                is_trusted = origin_base in self.settings.csrf_trusted_origins_list
            elif referer:
                parsed_referer = urlparse(referer)
                referer_base = f"{parsed_referer.scheme}://{parsed_referer.netloc}"
                is_trusted = referer_base in self.settings.csrf_trusted_origins_list

            # Validate token if not from trusted origin
            if not is_trusted and cookie_token and provided_token:
                if cookie_token != provided_token:
                    return Response(
                        content='{"code": 403, "message": "CSRF token mismatch"}',
                        status_code=403,
                        media_type="application/json",
                    )

        return await call_next(request)


def add_security_middleware(app: FastAPI, settings: AppSettings) -> None:
    """Add all security middleware to the FastAPI app."""
    # Add in reverse order (last added = first executed)
    app.add_middleware(CSRFMiddleware, settings=settings)
    app.add_middleware(HTTPSRedirectMiddleware, settings=settings)
    app.add_middleware(SecurityHeadersMiddleware, settings=settings)
