"""
Tests for security headers and HTTPS protection.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch

from core.config import AppSettings
from core.security_middleware import (
    SecurityHeadersMiddleware,
    HTTPSRedirectMiddleware,
    CSRFMiddleware,
    add_security_middleware,
)
from core.cors_config import CORSConfig


class TestSecurityHeaders:
    """Test security headers middleware."""

    @pytest.fixture
    def settings(self):
        return AppSettings(
            security_headers_enabled=True,
            https_enabled=True,
            csrf_protection_enabled=True,
            app_env="production",
        )

    @pytest.fixture
    def app_with_headers(self, settings):
        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware, settings=settings)

        @app.get("/test")
        def test_endpoint():
            return {"message": "ok"}

        return app

    def test_hsts_header_present(self, app_with_headers):
        """Test HSTS header is added."""
        client = TestClient(app_with_headers)
        response = client.get("/test")

        assert "Strict-Transport-Security" in response.headers
        assert "max-age=31536000" in response.headers["Strict-Transport-Security"]

    def test_hsts_include_subdomains(self, app_with_headers):
        """Test HSTS includes subdomains."""
        client = TestClient(app_with_headers)
        response = client.get("/test")

        assert "includeSubDomains" in response.headers["Strict-Transport-Security"]

    def test_csp_header_present(self, app_with_headers):
        """Test CSP header is set."""
        client = TestClient(app_with_headers)
        response = client.get("/test")

        assert "Content-Security-Policy" in response.headers
        assert "default-src 'self'" in response.headers["Content-Security-Policy"]

    def test_x_frame_options_header(self, app_with_headers):
        """Test X-Frame-Options header."""
        client = TestClient(app_with_headers)
        response = client.get("/test")

        assert response.headers["X-Frame-Options"] == "SAMEORIGIN"

    def test_x_content_type_options_header(self, app_with_headers):
        """Test X-Content-Type-Options header."""
        client = TestClient(app_with_headers)
        response = client.get("/test")

        assert response.headers["X-Content-Type-Options"] == "nosniff"

    def test_x_xss_protection_header(self, app_with_headers):
        """Test X-XSS-Protection header."""
        client = TestClient(app_with_headers)
        response = client.get("/test")

        assert response.headers["X-XSS-Protection"] == "1; mode=block"

    def test_referrer_policy_header(self, app_with_headers):
        """Test Referrer-Policy header."""
        client = TestClient(app_with_headers)
        response = client.get("/test")

        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

    def test_permissions_policy_header(self, app_with_headers):
        """Test Permissions-Policy header."""
        client = TestClient(app_with_headers)
        response = client.get("/test")

        assert "Permissions-Policy" in response.headers
        assert "camera=()" in response.headers["Permissions-Policy"]

    def test_headers_disabled(self, settings):
        """Test headers not added when disabled."""
        settings.security_headers_enabled = False
        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware, settings=settings)

        @app.get("/test")
        def test_endpoint():
            return {"message": "ok"}

        client = TestClient(app)
        response = client.get("/test")

        # Headers should not be present
        assert "Strict-Transport-Security" not in response.headers


class TestHTTPSRedirect:
    """Test HTTPS redirect middleware."""

    @pytest.fixture
    def settings_https(self):
        return AppSettings(
            https_enabled=True,
            https_redirect=True,
            app_env="production",
        )

    @pytest.fixture
    def settings_dev(self):
        return AppSettings(
            https_enabled=True,
            https_redirect=True,
            app_env="dev",
        )

    def test_http_to_https_redirect(self, settings_https):
        """Test HTTP requests are redirected to HTTPS."""
        app = FastAPI()
        app.add_middleware(HTTPSRedirectMiddleware, settings=settings_https)

        @app.get("/test")
        def test_endpoint():
            return {"message": "ok"}

        client = TestClient(app)
        response = client.get("/test", follow_redirects=False)

        # Should be redirected with 301 (Moved Permanently)
        assert response.status_code == 301

    def test_health_check_no_redirect(self, settings_https):
        """Test health checks are not redirected."""
        app = FastAPI()
        app.add_middleware(HTTPSRedirectMiddleware, settings=settings_https)

        @app.get("/health")
        def health():
            return {"status": "ok"}

        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_no_redirect_in_dev(self, settings_dev):
        """Test no redirect in development."""
        app = FastAPI()
        app.add_middleware(HTTPSRedirectMiddleware, settings=settings_dev)

        @app.get("/test")
        def test_endpoint():
            return {"message": "ok"}

        client = TestClient(app)
        response = client.get("/test")

        assert response.status_code == 200

    def test_redirect_disabled(self, settings_https):
        """Test redirect can be disabled."""
        settings_https.https_redirect = False
        app = FastAPI()
        app.add_middleware(HTTPSRedirectMiddleware, settings=settings_https)

        @app.get("/test")
        def test_endpoint():
            return {"message": "ok"}

        client = TestClient(app)
        response = client.get("/test")

        assert response.status_code == 200


class TestCSRFMiddleware:
    """Test CSRF protection middleware."""

    @pytest.fixture
    def settings_csrf(self):
        return AppSettings(
            csrf_protection_enabled=True,
            csrf_trusted_origins="http://localhost:3000,https://example.com",
        )

    @pytest.fixture
    def app_csrf(self, settings_csrf):
        app = FastAPI()
        app.add_middleware(CSRFMiddleware, settings=settings_csrf)

        @app.get("/test")
        def test_get():
            return {"message": "ok"}

        @app.post("/test")
        def test_post():
            return {"message": "created"}

        return app

    def test_csrf_token_on_get(self, app_csrf):
        """Test CSRF token is set on GET request."""
        client = TestClient(app_csrf)
        response = client.get("/test")

        assert "csrf_token" in response.cookies
        assert len(response.cookies["csrf_token"]) > 0

    def test_csrf_token_in_header(self, app_csrf):
        """Test CSRF validation with header token."""
        client = TestClient(app_csrf)

        # First GET to get token
        get_response = client.get("/test")
        token = get_response.cookies.get("csrf_token")

        # POST with matching token
        post_response = client.post(
            "/test",
            headers={"X-CSRF-Token": token},
            cookies={"csrf_token": token},
        )

        assert post_response.status_code == 200

    def test_csrf_token_mismatch(self, app_csrf):
        """Test CSRF token mismatch rejection."""
        client = TestClient(app_csrf)

        # GET to get token
        get_response = client.get("/test")

        # POST with wrong token
        post_response = client.post(
            "/test",
            headers={"X-CSRF-Token": "wrong_token"},
            cookies={"csrf_token": "correct_token"},
        )

        # Should be rejected with 403
        assert post_response.status_code == 403

    def test_trusted_origin_bypass(self, app_csrf):
        """Test trusted origins bypass CSRF check."""
        client = TestClient(
            app_csrf,
            headers={"Origin": "http://localhost:3000"},
        )

        # POST without tokens but from trusted origin
        post_response = client.post("/test")

        # Should succeed
        assert post_response.status_code == 200

    def test_csrf_disabled(self):
        """Test CSRF can be disabled."""
        settings = AppSettings(csrf_protection_enabled=False)
        app = FastAPI()
        app.add_middleware(CSRFMiddleware, settings=settings)

        @app.post("/test")
        def test_post():
            return {"message": "created"}

        client = TestClient(app)
        response = client.post("/test")

        assert response.status_code == 200


class TestCORSConfig:
    """Test CORS configuration."""

    @pytest.fixture
    def settings(self):
        return AppSettings(
            cors_origins="http://localhost:3000,https://example.com",
        )

    def test_cors_origins_list(self, settings):
        """Test CORS origins are parsed correctly."""
        config = CORSConfig(settings)

        assert "http://localhost:3000" in config.allowed_origins
        assert "https://example.com" in config.allowed_origins

    def test_cors_allow_credentials(self, settings):
        """Test credentials are allowed."""
        config = CORSConfig(settings)

        assert config.allow_credentials is True

    def test_cors_allowed_methods(self, settings):
        """Test allowed methods are set."""
        config = CORSConfig(settings)

        assert "GET" in config.allow_methods
        assert "POST" in config.allow_methods
        assert "DELETE" in config.allow_methods

    def test_cors_allowed_headers(self, settings):
        """Test allowed headers include security headers."""
        config = CORSConfig(settings)

        assert "X-CSRF-Token" in config.allow_headers
        assert "X-Request-ID" in config.allow_headers
        assert "Authorization" in config.allow_headers

    def test_cors_exposed_headers(self, settings):
        """Test exposed headers are set."""
        config = CORSConfig(settings)

        assert "X-CSRF-Token" in config.expose_headers
        assert "X-Request-ID" in config.expose_headers

    def test_cors_max_age(self, settings):
        """Test preflight cache max age."""
        config = CORSConfig(settings)

        assert config.max_age == 3600

    def test_cors_validate_origin(self, settings):
        """Test origin validation."""
        config = CORSConfig(settings)

        assert config.validate_origin("http://localhost:3000") is True
        assert config.validate_origin("https://example.com") is True
        assert config.validate_origin("https://evil.com") is False


class TestAddSecurityMiddleware:
    """Test adding all security middleware."""

    def test_add_all_middleware(self):
        """Test that all middleware are added."""
        app = FastAPI()
        settings = AppSettings(
            security_headers_enabled=True,
            https_enabled=True,
            csrf_protection_enabled=True,
        )

        add_security_middleware(app, settings)

        # Check that middleware were added
        # We can't directly check middleware, but we can verify the app doesn't error
        assert app is not None

        @app.get("/test")
        def test_endpoint():
            return {"message": "ok"}

        client = TestClient(app)
        response = client.get("/test")

        # Should have security headers
        assert "Strict-Transport-Security" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "Content-Security-Policy" in response.headers


class TestIntegration:
    """Integration tests for all security features."""

    def test_full_security_stack(self):
        """Test full security stack integration."""
        app = FastAPI()
        settings = AppSettings(
            security_headers_enabled=True,
            https_enabled=True,
            csrf_protection_enabled=True,
            cors_origins="http://localhost:3000",
        )

        add_security_middleware(app, settings)

        from fastapi.middleware.cors import CORSMiddleware
        cors_config = CORSConfig(settings)
        app.add_middleware(CORSMiddleware, **cors_config.get_cors_config_dict())

        @app.get("/api/test")
        def get_test():
            return {"method": "get"}

        @app.post("/api/test")
        def post_test():
            return {"method": "post"}

        client = TestClient(app)

        # Test GET request
        get_response = client.get("/api/test")
        assert get_response.status_code == 200
        assert "Strict-Transport-Security" in get_response.headers
        assert "csrf_token" in get_response.cookies

        # Test POST with CSRF token
        token = get_response.cookies.get("csrf_token")
        post_response = client.post(
            "/api/test",
            headers={"X-CSRF-Token": token},
            cookies={"csrf_token": token},
        )
        assert post_response.status_code == 200

    def test_health_endpoint_unaffected(self):
        """Test health endpoint is not affected by security."""
        app = FastAPI()
        settings = AppSettings(
            https_enabled=True,
            https_redirect=True,
            app_env="production",
        )

        add_security_middleware(app, settings)

        @app.get("/health")
        def health():
            return {"status": "ok"}

        client = TestClient(app)
        response = client.get("/health")

        # Should not be redirected (health checks are important)
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
