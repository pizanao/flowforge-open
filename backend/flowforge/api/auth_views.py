"""Views de autenticação do FlowForge."""

import os
from typing import Any

import httpx
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils.text import slugify
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView


def _normalize_email(email: str | None) -> str:
    """
    Normaliza um email para comparação.

    Args:
        email: Email bruto informado pelo cliente ou provider; pode ser None.

    Returns:
        Email em minúsculas e sem espaços laterais; string vazia se entrada None/vazia.
    """
    return (email or "").strip().lower()


def _assert_email_allowed(email: str) -> None:
    """
    Valida se o email está presente na whitelist.

    Args:
        email: Email a validar.

    Raises:
        PermissionDenied: Quando o email não está autorizado.
    """
    normalized = _normalize_email(email)
    print(settings.ALLOWED_EMAILS)
    print(normalized)
    if normalized not in set(settings.ALLOWED_EMAILS):
        raise PermissionDenied("Email não autorizado.")


def _split_name(full_name: str) -> tuple[str, str]:
    """
    Divide um nome completo em first_name e last_name.

    Args:
        full_name: Nome completo do usuário.

    Returns:
        Tupla com nome e sobrenome.
    """
    parts = [part for part in full_name.strip().split(" ") if part]
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])


def _user_payload(user: Any) -> dict[str, Any]:
    """
    Serializa o usuário autenticado para o frontend.

    Args:
        user: Instância do modelo de usuário.

    Returns:
        Dict com dados básicos do usuário.
    """
    display_name = user.get_full_name().strip() or user.email or user.get_username()
    return {
        "id": user.id,
        "email": user.email,
        "username": user.get_username(),
        "name": display_name,
    }


def _auth_response(user: Any) -> dict[str, Any]:
    """
    Gera access/refresh tokens para um usuário.

    Args:
        user: Instância autenticada.

    Returns:
        Dict com tokens JWT e dados do usuário.
    """
    refresh = RefreshToken.for_user(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "user": _user_payload(user),
    }


def _find_user_by_email(email: str) -> Any | None:
    """
    Busca um usuário pelo email.

    Args:
        email: Email a buscar.

    Returns:
        Usuário encontrado ou None.
    """
    user_model = get_user_model()
    return user_model.objects.filter(email__iexact=_normalize_email(email)).order_by("id").first()


def _build_unique_username(email: str) -> str:
    """
    Gera um username único a partir do email.

    Args:
        email: Email base do usuário.

    Returns:
        Username único e estável para criação do usuário.
    """
    user_model = get_user_model()
    username_field = user_model.USERNAME_FIELD
    max_length = user_model._meta.get_field(username_field).max_length or 150
    base = slugify(email.split("@", maxsplit=1)[0]) or "flowforge-user"
    base = base[:max_length]
    candidate = base
    suffix = 1

    while user_model.objects.filter(**{username_field: candidate}).exists():
        suffix_value = f"-{suffix}"
        candidate = f"{base[: max_length - len(suffix_value)]}{suffix_value}"
        suffix += 1

    return candidate


@transaction.atomic
def _get_or_create_user(email: str, full_name: str = "") -> Any:
    """
    Retorna um usuário existente ou cria um novo a partir do email.

    Args:
        email: Email do usuário.
        full_name: Nome completo opcional vindo do provider OAuth.

    Returns:
        Usuário persistido no banco.
    """
    normalized = _normalize_email(email)
    user_model = get_user_model()
    user = _find_user_by_email(normalized)
    if user:
        updates: list[str] = []
        if user.email != normalized:
            user.email = normalized
            updates.append("email")
        if full_name and hasattr(user, "first_name") and hasattr(user, "last_name"):
            first_name, last_name = _split_name(full_name)
            if first_name and user.first_name != first_name:
                user.first_name = first_name
                updates.append("first_name")
            if last_name and user.last_name != last_name:
                user.last_name = last_name
                updates.append("last_name")
        if updates:
            user.save(update_fields=updates)
        return user

    username_field = user_model.USERNAME_FIELD
    user_kwargs: dict[str, Any] = {"email": normalized}
    if username_field != "email":
        user_kwargs[username_field] = _build_unique_username(normalized)

    if hasattr(user_model, "EMAIL_FIELD") and user_model.EMAIL_FIELD != "email":
        user_kwargs[user_model.EMAIL_FIELD] = normalized

    first_name, last_name = _split_name(full_name)
    if hasattr(user_model, "first_name"):
        user_kwargs["first_name"] = first_name
    if hasattr(user_model, "last_name"):
        user_kwargs["last_name"] = last_name

    user = user_model._default_manager.create_user(**user_kwargs)
    return user


def _bootstrap_credentials() -> list[tuple[str, str]]:
    """
    Carrega credenciais locais de bootstrap via env.

    Bootstrap é uma backdoor de primeiro acesso e fica desabilitado em produção.
    Habilita apenas quando DEBUG=True ou ALLOW_BOOTSTRAP_LOGIN está setado.

    Returns:
        Lista de pares (email, senha) válidos para provisionamento inicial; vazia em produção.
    """
    if not settings.DEBUG and not os.getenv("ALLOW_BOOTSTRAP_LOGIN"):
        return []

    credentials: list[tuple[str, str]] = []
    for email_var, password_var in (
        ("TEST_USER_EMAIL", "TEST_USER_PASSWORD"),
        ("DJANGO_SUPERUSER_EMAIL", "DJANGO_SUPERUSER_PASSWORD"),
    ):
        env_email = _normalize_email(os.getenv(email_var, ""))
        env_password = os.getenv(password_var, "")
        if env_email and env_password:
            credentials.append((env_email, env_password))
    return credentials


@transaction.atomic
def _maybe_bootstrap_local_user(email: str, password: str) -> Any | None:
    """
    Provisiona o usuário local inicial quando as credenciais batem com o env.

    Args:
        email: Email informado no login.
        password: Senha informada no login.

    Returns:
        Usuário criado quando houver match exato com as credenciais de bootstrap.
    """
    normalized = _normalize_email(email)
    if _find_user_by_email(normalized):
        return None

    for allowed_email, allowed_password in _bootstrap_credentials():
        if normalized != allowed_email or password != allowed_password:
            continue

        user = _get_or_create_user(normalized)
        user.set_password(password)
        user.save(update_fields=["password"])
        return user

    return None


def _google_profile_from_code(code: str, redirect_uri: str) -> dict[str, str]:
    """
    Troca o authorization code do Google por um perfil do usuário.

    Args:
        code: Authorization code retornado pelo Google.
        redirect_uri: Redirect URI usada no passo de autorização.

    Returns:
        Dict com email e nome do usuário.
    """
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise ValidationError({"detail": "OAuth Google não configurado."})

    with httpx.Client(timeout=15.0) as client:
        token_response = client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        if token_response.status_code >= 400:
            raise AuthenticationFailed("Falha na autenticação com Google.")

        access_token = token_response.json().get("access_token", "")
        if not access_token:
            raise AuthenticationFailed("Google não retornou access token.")

        profile_response = client.get(
            "https://openidconnect.googleapis.com/v1/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if profile_response.status_code >= 400:
            raise AuthenticationFailed("Não foi possível obter o perfil do Google.")

    profile = profile_response.json()
    email = _normalize_email(profile.get("email", ""))
    if not email or not profile.get("email_verified"):
        raise AuthenticationFailed("O Google não retornou um email verificado.")

    return {
        "email": email,
        "name": profile.get("name", ""),
    }


def _github_profile_from_code(code: str, redirect_uri: str = "") -> dict[str, str]:
    """
    Troca o authorization code do GitHub por um perfil do usuário.

    Args:
        code: Authorization code retornado pelo GitHub.
        redirect_uri: Redirect URI opcional usada no fluxo de autorização.

    Returns:
        Dict com email e nome do usuário.
    """
    if not settings.GITHUB_CLIENT_ID or not settings.GITHUB_CLIENT_SECRET:
        raise ValidationError({"detail": "OAuth GitHub não configurado."})

    with httpx.Client(timeout=15.0) as client:
        payload: dict[str, str] = {
            "client_id": settings.GITHUB_CLIENT_ID,
            "client_secret": settings.GITHUB_CLIENT_SECRET,
            "code": code,
        }
        if redirect_uri:
            payload["redirect_uri"] = redirect_uri

        token_response = client.post(
            "https://github.com/login/oauth/access_token",
            data=payload,
            headers={"Accept": "application/json"},
        )
        if token_response.status_code >= 400:
            raise AuthenticationFailed("Falha na autenticação com GitHub.")

        access_token = token_response.json().get("access_token", "")
        if not access_token:
            raise AuthenticationFailed("GitHub não retornou access token.")

        user_response = client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json",
            },
        )
        email_response = client.get(
            "https://api.github.com/user/emails",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json",
            },
        )

        if user_response.status_code >= 400 or email_response.status_code >= 400:
            raise AuthenticationFailed("Não foi possível obter o perfil do GitHub.")

    emails = email_response.json()
    verified_email = next(
        (
            item.get("email", "")
            for item in emails
            if item.get("verified") and item.get("primary")
        ),
        "",
    )
    if not verified_email:
        verified_email = next(
            (item.get("email", "") for item in emails if item.get("verified")),
            "",
        )

    email = _normalize_email(verified_email)
    if not email:
        raise AuthenticationFailed("GitHub não retornou um email verificado.")

    profile = user_response.json()
    return {
        "email": email,
        "name": profile.get("name") or profile.get("login", ""),
    }


class LoginView(APIView):
    """Login por email e senha com emissão de JWT."""

    permission_classes = [AllowAny]
    throttle_scope = "auth"

    def post(self, request, *args: Any, **kwargs: Any) -> Response:
        """
        Autentica um usuário por email e senha.

        Args:
            request: Request DRF com email e password no body.

        Returns:
            Response com access, refresh e user.
        """
        email = _normalize_email(request.data.get("email", ""))
        password = request.data.get("password", "")
        if not email or not password:
            raise ValidationError({"detail": "Email e senha são obrigatórios."})

        _assert_email_allowed(email)

        user = _find_user_by_email(email)
        if user is None:
            user = _maybe_bootstrap_local_user(email, password)
        if user is None or not user.check_password(password):
            raise AuthenticationFailed("Credenciais inválidas.")

        return Response(_auth_response(user), status=status.HTTP_200_OK)


class RefreshView(TokenRefreshView):
    """Refresh do access token JWT."""

    permission_classes = [AllowAny]


class MeView(APIView):
    """Retorna dados do usuário autenticado."""

    def get(self, request, *args: Any, **kwargs: Any) -> Response:
        """
        Retorna os dados do usuário do token atual.

        Args:
            request: Request autenticada.

        Returns:
            Response com payload do usuário.
        """
        return Response(_user_payload(request.user), status=status.HTTP_200_OK)


class GoogleOAuthView(APIView):
    """Exchange do authorization code do Google para JWT interno."""

    permission_classes = [AllowAny]
    throttle_scope = "auth"

    def post(self, request, *args: Any, **kwargs: Any) -> Response:
        """
        Faz o code exchange do Google e retorna tokens internos.

        Args:
            request: Request com code e redirect_uri.

        Returns:
            Response com access, refresh e user.
        """
        code = request.data.get("code", "")
        redirect_uri = request.data.get("redirect_uri") or settings.FRONTEND_URL
        if not code:
            raise ValidationError({"detail": "Authorization code é obrigatório."})

        profile = _google_profile_from_code(code, redirect_uri)
        _assert_email_allowed(profile["email"])
        user = _get_or_create_user(profile["email"], profile.get("name", ""))
        return Response(_auth_response(user), status=status.HTTP_200_OK)


class GitHubOAuthView(APIView):
    """Exchange do authorization code do GitHub para JWT interno."""

    permission_classes = [AllowAny]
    throttle_scope = "auth"

    def post(self, request, *args: Any, **kwargs: Any) -> Response:
        """
        Faz o code exchange do GitHub e retorna tokens internos.

        Args:
            request: Request com code e redirect_uri opcional.

        Returns:
            Response com access, refresh e user.
        """
        code = request.data.get("code", "")
        redirect_uri = request.data.get("redirect_uri") or settings.FRONTEND_URL
        if not code:
            raise ValidationError({"detail": "Authorization code é obrigatório."})

        profile = _github_profile_from_code(code, redirect_uri)
        _assert_email_allowed(profile["email"])
        user = _get_or_create_user(profile["email"], profile.get("name", ""))
        return Response(_auth_response(user), status=status.HTTP_200_OK)
