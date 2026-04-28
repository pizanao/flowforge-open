"""Rotas da API FlowForge."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from flowforge.api import auth_views
from flowforge.api.views import (
    EdgeViewSet,
    NodeViewSet,
    RunViewSet,
    WorkflowViewSet,
)

router = DefaultRouter()
router.register(r"workflows", WorkflowViewSet, basename="workflow")
router.register(r"nodes", NodeViewSet, basename="node")
router.register(r"edges", EdgeViewSet, basename="edge")
router.register(r"runs", RunViewSet, basename="run")

urlpatterns = [
    path("auth/", include([
        path("login/", auth_views.LoginView.as_view()),
        path("token/refresh/", auth_views.RefreshView.as_view()),
        path("me/", auth_views.MeView.as_view()),
        path("google/", auth_views.GoogleOAuthView.as_view()),
        path("github/", auth_views.GitHubOAuthView.as_view()),
    ])),
    path("", include(router.urls)),
]
