"""Fixtures compartilhadas entre os testes do FlowForge."""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from flowforge.models import Edge, Node, Run, Workflow, WorkflowTemplate

SERVICE_TOKEN = "test-service-token-for-flowforge"


@pytest.fixture(autouse=True)
def _set_service_token(settings):
    """Garante que o service token está configurado em todos os testes."""
    settings.PORTFOLIO_HQ_SERVICE_TOKEN = SERVICE_TOKEN


@pytest.fixture
def api_client():
    """APIClient com service token — compatibilidade com testes do main."""
    client = APIClient()
    client.defaults["HTTP_X_SERVICE_TOKEN"] = SERVICE_TOKEN
    return client


@pytest.fixture
def anon_client():
    """APIClient sem autenticação."""
    return APIClient()


@pytest.fixture
def user(db):
    """Usuário padrão autenticado para testes de API."""
    user_model = get_user_model()
    return user_model.objects.create_user(
        username="flowforge-admin",
        email="admin@flowforge.local",
        password="admin123",
    )


@pytest.fixture
def api(user):
    """Cliente DRF autenticado."""
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def anon_api():
    """Cliente DRF sem autenticação."""
    return APIClient()


@pytest.fixture
def workflow(db):
    return Workflow.objects.create(name="Workflow Teste", status="active")


@pytest.fixture
def trigger_node(workflow):
    return Node.objects.create(
        workflow=workflow,
        node_type="trigger",
        label="Início",
        config={"trigger_type": "manual"},
        position_x=100,
        position_y=100,
    )


@pytest.fixture
def output_node(workflow):
    return Node.objects.create(
        workflow=workflow,
        node_type="output",
        label="Fim",
        config={},
        position_x=400,
        position_y=100,
    )


@pytest.fixture
def edge(workflow, trigger_node, output_node):
    return Edge.objects.create(
        workflow=workflow,
        source_node=trigger_node,
        target_node=output_node,
        source_handle="default",
    )


@pytest.fixture
def run(workflow, trigger_node, output_node, edge):
    return Run.objects.create(
        workflow=workflow,
        trigger_type="manual",
        input_data={"msg": "olá"},
        nodes_total=2,
    )


@pytest.fixture
def mock_node():
    """Nó mock leve para testes de handlers sem banco."""
    from types import SimpleNamespace
    return SimpleNamespace(config={}, id=__import__("uuid").uuid4())


@pytest.fixture
def mock_run(workflow):
    """Run mock mínima para testes de handlers."""
    from types import SimpleNamespace
    return SimpleNamespace(id=__import__("uuid").uuid4(), trigger_type="manual")


@pytest.fixture
def workflow_with_nodes(db):
    """Workflow completo com trigger → http → output (usado pelos testes do main)."""
    wf = Workflow.objects.create(name="Workflow Completo", status="active")
    trigger = Node.objects.create(
        workflow=wf, node_type="trigger", label="Início",
        config={"trigger_type": "manual"}, position_x=100, position_y=200,
    )
    http_node = Node.objects.create(
        workflow=wf, node_type="http", label="Buscar dados",
        config={"method": "GET", "url": "http://example.com/api"},
        position_x=300, position_y=200,
    )
    output_node = Node.objects.create(
        workflow=wf, node_type="output", label="Resultado",
        config={"format": "raw"}, position_x=500, position_y=200,
    )
    Edge.objects.create(workflow=wf, source_node=trigger, target_node=http_node)
    Edge.objects.create(workflow=wf, source_node=http_node, target_node=output_node)
    return wf


@pytest.fixture
def template(db):
    """WorkflowTemplate mínimo para testes de templates."""
    return WorkflowTemplate.objects.create(
        slug="test-template",
        name="Template Teste",
        description="Template para testes",
        category="test",
        tags=["test"],
        nodes_data=[
            {"_ref": "n1", "node_type": "trigger", "label": "Start",
             "config": {"trigger_type": "manual"}, "position_x": 0, "position_y": 0},
            {"_ref": "n2", "node_type": "output", "label": "End",
             "config": {"format": "raw"}, "position_x": 200, "position_y": 0},
        ],
        edges_data=[
            {"source_ref": "n1", "target_ref": "n2", "source_handle": "default"},
        ],
    )
