"""Testes dos endpoints de autenticação do FlowForge."""

import pytest


@pytest.mark.django_db
class TestPasswordLogin:
    def test_login_retains_allowed_user_and_returns_tokens(self, anon_api, user, settings):
        settings.ALLOWED_EMAILS = [user.email]

        resp = anon_api.post(
            "/api/auth/login/",
            {"email": user.email, "password": "admin123"},
            format="json",
        )

        assert resp.status_code == 200
        assert "access" in resp.data
        assert "refresh" in resp.data
        assert resp.data["user"]["email"] == user.email

    def test_login_rejects_email_outside_whitelist(self, anon_api, user, settings):
        settings.ALLOWED_EMAILS = []

        resp = anon_api.post(
            "/api/auth/login/",
            {"email": user.email, "password": "admin123"},
            format="json",
        )

        assert resp.status_code == 403
        assert resp.data["detail"] == "Email não autorizado."

    def test_login_returns_401_for_invalid_password(self, anon_api, user, settings):
        settings.ALLOWED_EMAILS = [user.email]

        resp = anon_api.post(
            "/api/auth/login/",
            {"email": user.email, "password": "senha-invalida"},
            format="json",
        )

        assert resp.status_code == 401
        assert resp.data["detail"] == "Credenciais inválidas."

    def test_bootstrap_login_creates_default_user(self, anon_api, settings, monkeypatch):
        settings.ALLOWED_EMAILS = ["admin@flowforge.local"]
        monkeypatch.setenv("TEST_USER_EMAIL", "admin@flowforge.local")
        monkeypatch.setenv("TEST_USER_PASSWORD", "admin123")

        resp = anon_api.post(
            "/api/auth/login/",
            {"email": "admin@flowforge.local", "password": "admin123"},
            format="json",
        )

        assert resp.status_code == 200
        assert resp.data["user"]["email"] == "admin@flowforge.local"


@pytest.mark.django_db
class TestJwtEndpoints:
    def test_me_returns_current_user(self, anon_api, user, settings):
        settings.ALLOWED_EMAILS = [user.email]
        login = anon_api.post(
            "/api/auth/login/",
            {"email": user.email, "password": "admin123"},
            format="json",
        )

        anon_api.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        resp = anon_api.get("/api/auth/me/")

        assert resp.status_code == 200
        assert resp.data["email"] == user.email

    def test_refresh_returns_new_access_token(self, anon_api, user, settings):
        settings.ALLOWED_EMAILS = [user.email]
        login = anon_api.post(
            "/api/auth/login/",
            {"email": user.email, "password": "admin123"},
            format="json",
        )

        resp = anon_api.post(
            "/api/auth/token/refresh/",
            {"refresh": login.data["refresh"]},
            format="json",
        )

        assert resp.status_code == 200
        assert "access" in resp.data
