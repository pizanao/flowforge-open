"""Testes dos serializers do FlowForge."""

import pytest
from rest_framework.exceptions import ValidationError

from flowforge.api.serializers import (
    EdgeSerializer,
    NodeSerializer,
    RunDetailSerializer,
    RunListSerializer,
    WorkflowDetailSerializer,
    WorkflowListSerializer,
    WorkflowTemplateSerializer,
    validate_node_config,
)
from flowforge.models import Edge, Node, NodeExecution, Run, Workflow, WorkflowTemplate


# ── validate_node_config (função pura) ───────────────────────────────────────

class TestValidateNodeConfig:
    def test_http_without_url(self):
        errs = validate_node_config("http", {})
        assert any("url" in e for e in errs)

    def test_http_with_url_is_valid(self):
        assert validate_node_config("http", {"url": "https://api.com"}) == []

    def test_condition_missing_field(self):
        errs = validate_node_config("condition", {"operator": "eq", "value": "x"})
        assert any("field" in e for e in errs)

    def test_condition_missing_operator(self):
        errs = validate_node_config("condition", {"field": "status", "value": "ok"})
        assert any("operator" in e for e in errs)

    def test_condition_valid(self):
        assert validate_node_config("condition", {"field": "ok", "operator": "eq", "value": "True"}) == []

    def test_delay_invalid_seconds(self):
        errs = validate_node_config("delay", {"seconds": 0})
        assert any("seconds" in e for e in errs)

    def test_delay_valid(self):
        assert validate_node_config("delay", {"seconds": 5}) == []

    def test_email_missing_to(self):
        errs = validate_node_config("email", {"subject": "x"})
        assert any("to" in e for e in errs)

    def test_email_valid(self):
        assert validate_node_config("email", {"to": "a@b.com"}) == []

    def test_unknown_type_has_no_errors(self):
        assert validate_node_config("whatsapp", {"phone": "5511999"}) == []
        assert validate_node_config("output", {}) == []


# ── NodeSerializer ────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestNodeSerializer:
    def test_serialize_node(self, trigger_node):
        data = NodeSerializer(trigger_node).data
        assert data["node_type"] == "trigger"
        assert data["label"] == "Início"
        assert "config" in data
        assert "position_x" in data

    def test_duplicate_trigger_raises_validation_error(self, workflow, trigger_node):
        """Não pode adicionar segundo trigger ao mesmo workflow."""
        payload = {
            "workflow": workflow.id,
            "node_type": "trigger",
            "label": "Trigger 2",
            "config": {},
        }
        serializer = NodeSerializer(data=payload)
        assert serializer.is_valid() is False
        assert "node_type" in serializer.errors or "non_field_errors" in serializer.errors

    def test_http_without_url_raises_validation_error(self, workflow):
        # Config parcialmente preenchida (method definido, url ausente) deve falhar.
        # Config vazia ({}) é aceita — nó pode ser salvo antes de ser configurado.
        payload = {
            "workflow": workflow.id,
            "node_type": "http",
            "label": "HTTP sem URL",
            "config": {"method": "GET", "timeout": 30},
        }
        serializer = NodeSerializer(data=payload)
        assert serializer.is_valid() is False
        assert "config" in serializer.errors

    def test_whatsapp_node_has_no_config_errors(self, workflow):
        payload = {
            "workflow": workflow.id,
            "node_type": "whatsapp",
            "label": "WA",
            "config": {"phone": "5511999", "text": "oi"},
        }
        serializer = NodeSerializer(data=payload)
        assert serializer.is_valid() is True


# ── EdgeSerializer ────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestEdgeSerializer:
    def test_serialize_edge(self, edge, trigger_node, output_node):
        data = EdgeSerializer(edge).data
        assert str(data["source_node"]) == str(trigger_node.id)
        assert str(data["target_node"]) == str(output_node.id)
        assert data["source_handle"] == "default"

    def test_self_loop_raises_validation_error(self, workflow, trigger_node):
        payload = {
            "workflow": workflow.id,
            "source_node": trigger_node.id,
            "target_node": trigger_node.id,
        }
        serializer = EdgeSerializer(data=payload)
        assert serializer.is_valid() is False


# ── WorkflowListSerializer ────────────────────────────────────────────────────

@pytest.mark.django_db
class TestWorkflowListSerializer:
    def test_fields_present(self, workflow):
        data = WorkflowListSerializer(workflow).data
        for field in ("id", "name", "description", "status", "version", "tags", "created_at", "updated_at"):
            assert field in data

    def test_status_default_draft(self, db):
        wf = Workflow.objects.create(name="Rascunho")
        data = WorkflowListSerializer(wf).data
        assert data["status"] == "draft"

    def test_tags_is_list(self, workflow):
        data = WorkflowListSerializer(workflow).data
        assert isinstance(data["tags"], list)


# ── WorkflowDetailSerializer ──────────────────────────────────────────────────

@pytest.mark.django_db
class TestWorkflowDetailSerializer:
    def test_includes_nodes_and_edges(self, workflow, trigger_node, output_node, edge):
        data = WorkflowDetailSerializer(workflow).data
        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) == 2
        assert len(data["edges"]) == 1

    def test_recent_runs_field(self, workflow, run):
        data = WorkflowDetailSerializer(workflow).data
        assert "recent_runs" in data
        assert isinstance(data["recent_runs"], list)
        assert len(data["recent_runs"]) == 1

    def test_node_includes_config(self, workflow, trigger_node, output_node, edge):
        data = WorkflowDetailSerializer(workflow).data
        nodes_by_type = {n["node_type"]: n for n in data["nodes"]}
        assert "config" in nodes_by_type["trigger"]


# ── RunListSerializer ─────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestRunListSerializer:
    def test_fields_present(self, run, workflow):
        data = RunListSerializer(run).data
        for field in ("id", "workflow", "workflow_name", "status", "trigger_type", "duration_ms"):
            assert field in data

    def test_workflow_name_populated(self, run, workflow):
        data = RunListSerializer(run).data
        assert data["workflow_name"] == workflow.name

    def test_status_default_pending(self, run):
        data = RunListSerializer(run).data
        assert data["status"] == "pending"


# ── RunDetailSerializer ───────────────────────────────────────────────────────

@pytest.mark.django_db
class TestRunDetailSerializer:
    def test_includes_node_executions(self, run, trigger_node):
        NodeExecution.objects.create(run=run, node=trigger_node, execution_order=0)
        data = RunDetailSerializer(run).data
        assert "node_executions" in data
        assert len(data["node_executions"]) == 1

    def test_node_execution_includes_label_and_type(self, run, trigger_node):
        NodeExecution.objects.create(run=run, node=trigger_node, execution_order=0)
        data = RunDetailSerializer(run).data
        ne = data["node_executions"][0]
        assert ne["node_label"] == "Início"
        assert ne["node_type"] == "trigger"


# ── WorkflowTemplateSerializer ────────────────────────────────────────────────

@pytest.mark.django_db
class TestWorkflowTemplateSerializer:
    def test_fields(self, db):
        t = WorkflowTemplate.objects.create(
            slug="test-tmpl",
            name="Test",
            description="desc",
            category="IA",
            tags=["a", "b"],
            nodes_data=[],
            edges_data=[],
        )
        data = WorkflowTemplateSerializer(t).data
        for field in ("slug", "name", "description", "category", "tags"):
            assert field in data

    def test_nodes_data_not_in_serializer(self, db):
        """nodes_data e edges_data não são expostos na listagem pública."""
        t = WorkflowTemplate.objects.create(
            slug="test-tmpl2", name="T", nodes_data=[], edges_data=[],
        )
        data = WorkflowTemplateSerializer(t).data
        assert "nodes_data" not in data
        assert "edges_data" not in data
