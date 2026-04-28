"""Roteamento WebSocket do FlowForge."""

from django.urls import re_path

from flowforge import consumers

websocket_urlpatterns = [
    re_path(
        r"ws/runs/(?P<run_id>[0-9a-f-]{36})/$",
        consumers.WorkflowRunConsumer.as_asgi(),
    ),
]
