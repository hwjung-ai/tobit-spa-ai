"""
Advanced CORS configuration with environment-specific settings.
"""

from __future__ import annotations

from typing import List

from core.config import AppSettings


class CORSConfig:
    """CORS configuration manager."""

    def __init__(self, settings: AppSettings):
        self.settings = settings

    @property
    def allowed_origins(self) -> List[str]:
        """Get list of allowed origins."""
        if (
            not self.settings.cors_allowed_origins
            or self.settings.cors_allowed_origins == ["*"]
        ):
            return ["*"]
        return self.settings.cors_allowed_origins

    @property
    def allow_credentials(self) -> bool:
        """Always allow credentials for API use."""
        return True

    @property
    def allow_methods(self) -> List[str]:
        """Allowed HTTP methods."""
        return ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]

    @property
    def allow_headers(self) -> List[str]:
        """Allowed HTTP headers."""
        return [
            "Accept",
            "Accept-Encoding",
            "Accept-Language",
            "Authorization",
            "Content-Type",
            "Origin",
            "User-Agent",
            "X-CSRF-Token",
            "X-Requested-With",
            "X-Request-ID",
            "X-Parent-Request-ID",
            "X-Trace-ID",
        ]

    @property
    def expose_headers(self) -> List[str]:
        """Headers exposed to the browser."""
        return [
            "Content-Length",
            "Content-Type",
            "Date",
            "X-CSRF-Token",
            "X-Request-ID",
            "X-Trace-ID",
        ]

    @property
    def max_age(self) -> int:
        """Max age for preflight cache (in seconds)."""
        return 3600  # 1 hour

    def validate_origin(self, origin: str) -> bool:
        """Validate if origin is in allowed list."""
        return origin in self.allowed_origins

    def get_cors_config_dict(self) -> dict:
        """Get CORS configuration as dictionary for middleware."""
        return {
            "allow_origins": self.allowed_origins,
            "allow_credentials": self.allow_credentials,
            "allow_methods": self.allow_methods,
            "allow_headers": self.allow_headers,
            "expose_headers": self.expose_headers,
            "max_age": self.max_age,
        }
