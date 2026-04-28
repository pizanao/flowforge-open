"""Permissões customizadas do FlowForge."""

from django.conf import settings
from django.utils.crypto import constant_time_compare
from rest_framework.permissions import BasePermission


class IsServiceAuthenticated(BasePermission):
    """Valida service token do Portfolio HQ no header X-Service-Token."""

    def has_permission(self, request, view) -> bool:
        expected = getattr(settings, "PORTFOLIO_HQ_SERVICE_TOKEN", "")
        if not expected:
            return True
        token = request.META.get("HTTP_X_SERVICE_TOKEN", "")
        return constant_time_compare(token, expected)


class IsAuthenticatedOrServiceToken(BasePermission):
    """Aceita JWT (acesso direto) ou service token do HQ (produção via proxy)."""

    def has_permission(self, request, view) -> bool:
        expected = getattr(settings, "PORTFOLIO_HQ_SERVICE_TOKEN", "")
        if expected:
            token = request.META.get("HTTP_X_SERVICE_TOKEN", "")
            if constant_time_compare(token, expected):
                return True
        return bool(request.user and request.user.is_authenticated)
