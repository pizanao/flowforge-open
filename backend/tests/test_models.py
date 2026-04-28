"""Testes dos modelos do FlowForge."""

import pytest
from django.db import IntegrityError

from flowforge.models import Edge, Node, NodeExecution, Run, Workflow, WorkflowTemplate


@pytest.mark.django_db
class TestWorkflow:
    def test_criacao_defaults(self):
        wf = Workflow.objects.create(name="Meu Workflow")
        assert wf.status == "draft"
        assert wf.version == 1
        assert wf.tags == []
        assert wf.canvas_state == {}
        assert str(wf) == "Meu Workflow (v1)"

    def test_status_choices(self):
        for status in ("draft", "active", "paused", "archived"):
            wf = Workflow.objects.create(name=f"WF {status}", status=status)
            assert wf.status == status

    def test_uuid_primary_key(self):
        wf = Workflow.objects.create(name="UUID Test")
        assert len(str(wf.id)) == 36  # formato UUID

    def test_timestamps_preenchidos(self):
        wf = Workflow.objects.create(name="Timestamps")
        assert wf.created_at is not None
        assert wf.updated_at is not None

    def test_ordenacao_por_updated_at(self):
        wf1 = Workflow.objects.create(name="Primeiro")
        wf2 = Workflow.objects.create(name="Segundo")
        # Mais recente aparece primeiro
        workflows = list(Workflow.objects.all())
        assert workflows[0].id == wf2.id


@pytest.mark.django_db
class TestNode:
    def test_criacao_basica(self, workflow):
        node = Node.objects.create(
            workflow=workflow,
            node_type="trigger",
            label="Start",
            config={"trigger_type": "manual"},
        )
        assert node.node_type == "trigger"
        assert node.label == "Start"
        assert node.position_x == 0
        assert node.position_y == 0
        assert str(node) == "[trigger] Start"

    def test_todos_tipos_validos(self, workflow):
        tipos = ["trigger", "http", "transform", "condition", "llm",
                 "email", "delay", "output", "telegram"]
        for tipo in tipos:
            node = Node.objects.create(workflow=workflow, node_type=tipo, label=tipo)
            assert node.node_type == tipo

    def test_config_jsonfield(self, workflow):
        config = {"method": "POST", "url": "http://example.com", "headers": {"X-Key": "val"}}
        node = Node.objects.create(workflow=workflow, node_type="http", label="HTTP", config=config)
        node.refresh_from_db()
        assert node.config["method"] == "POST"
        assert node.config["headers"]["X-Key"] == "val"

    def test_cascade_delete_com_workflow(self, workflow):
        Node.objects.create(workflow=workflow, node_type="output", label="Out")
        assert Node.objects.filter(workflow=workflow).count() == 1
        workflow.delete()
        assert Node.objects.count() == 0


@pytest.mark.django_db
class TestEdge:
    def test_criacao_basica(self, workflow):
        src = Node.objects.create(workflow=workflow, node_type="trigger", label="A")
        tgt = Node.objects.create(workflow=workflow, node_type="output", label="B")
        edge = Edge.objects.create(workflow=workflow, source_node=src, target_node=tgt)
        assert str(edge) == "A → B"
        assert edge.source_handle == "default"

    def test_unique_together(self, workflow):
        src = Node.objects.create(workflow=workflow, node_type="trigger", label="S")
        tgt = Node.objects.create(workflow=workflow, node_type="output", label="T")
        Edge.objects.create(workflow=workflow, source_node=src, target_node=tgt)
        with pytest.raises(IntegrityError):
            Edge.objects.create(workflow=workflow, source_node=src, target_node=tgt)

    def test_source_handle_condition(self, workflow):
        src = Node.objects.create(workflow=workflow, node_type="condition", label="Cond")
        t = Node.objects.create(workflow=workflow, node_type="output", label="True")
        f = Node.objects.create(workflow=workflow, node_type="output", label="False")
        e1 = Edge.objects.create(workflow=workflow, source_node=src, target_node=t, source_handle="true")
        e2 = Edge.objects.create(workflow=workflow, source_node=src, target_node=f, source_handle="false")
        assert e1.source_handle == "true"
        assert e2.source_handle == "false"


@pytest.mark.django_db
class TestRun:
    def test_criacao_defaults(self, workflow):
        run = Run.objects.create(workflow=workflow, nodes_total=3)
        assert run.status == "pending"
        assert run.trigger_type == "manual"
        assert run.duration_ms == 0
        assert run.nodes_completed == 0

    def test_str(self, workflow):
        run = Run.objects.create(workflow=workflow)
        assert "pending" in str(run)

    def test_status_transitions(self, workflow):
        run = Run.objects.create(workflow=workflow, status="running")
        run.status = "success"
        run.save()
        run.refresh_from_db()
        assert run.status == "success"


@pytest.mark.django_db
class TestWorkflowTemplate:
    def test_criacao(self):
        t = WorkflowTemplate.objects.create(
            slug="my-template",
            name="My Template",
            nodes_data=[],
            edges_data=[],
        )
        assert t.slug == "my-template"
        assert str(t) == "[template] My Template"

    def test_slug_unico(self):
        WorkflowTemplate.objects.create(slug="unico", name="T1")
        with pytest.raises(IntegrityError):
            WorkflowTemplate.objects.create(slug="unico", name="T2")
