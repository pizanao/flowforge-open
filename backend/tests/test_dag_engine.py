"""Testes do DAG engine — validação de ciclos e alcançabilidade."""

import pytest

from flowforge.engine.dag_engine import find_unreachable_nodes, validate_dag
from flowforge.models import Edge, Node, Workflow


@pytest.mark.django_db
class TestValidateDag:
    def test_workflow_inexistente(self):
        result = validate_dag("00000000-0000-0000-0000-000000000000")
        assert result["valid"] is False
        assert result["errors"][0]["node_id"] is None

    def test_workflow_sem_nos(self, db):
        wf = Workflow.objects.create(name="Vazio")
        result = validate_dag(str(wf.id))
        assert result["valid"] is False
        assert any("não possui nós" in e["message"] for e in result["errors"])

    def test_workflow_sem_trigger(self, db):
        wf = Workflow.objects.create(name="Sem Trigger")
        Node.objects.create(workflow=wf, node_type="output", label="Out")
        result = validate_dag(str(wf.id))
        assert result["valid"] is False
        assert any("trigger" in e["message"].lower() for e in result["errors"])

    def test_dag_valido_simples(self, workflow_with_nodes):
        result = validate_dag(str(workflow_with_nodes.id))
        assert result["valid"] is True
        assert result["errors"] == []

    def test_trigger_duplicado(self, db):
        wf = Workflow.objects.create(name="Dois Triggers")
        t1 = Node.objects.create(workflow=wf, node_type="trigger", label="T1")
        t2 = Node.objects.create(workflow=wf, node_type="trigger", label="T2")
        out = Node.objects.create(workflow=wf, node_type="output", label="Out")
        Edge.objects.create(workflow=wf, source_node=t1, target_node=out)
        Edge.objects.create(workflow=wf, source_node=t2, target_node=out, source_handle="true")
        result = validate_dag(str(wf.id))
        assert result["valid"] is False
        assert any("trigger duplicado" in e["message"].lower() for e in result["errors"])

    def test_ciclo_detectado(self, db):
        wf = Workflow.objects.create(name="Com Ciclo")
        trigger = Node.objects.create(workflow=wf, node_type="trigger", label="Start")
        n1 = Node.objects.create(workflow=wf, node_type="http", label="A")
        n2 = Node.objects.create(workflow=wf, node_type="http", label="B")
        Edge.objects.create(workflow=wf, source_node=trigger, target_node=n1)
        Edge.objects.create(workflow=wf, source_node=n1, target_node=n2)
        Edge.objects.create(workflow=wf, source_node=n2, target_node=n1, source_handle="true")
        result = validate_dag(str(wf.id))
        assert result["valid"] is False
        assert any("ciclo" in e["message"].lower() for e in result["errors"])

    def test_no_nao_alcancavel(self, db):
        wf = Workflow.objects.create(name="Com Ilha")
        trigger = Node.objects.create(workflow=wf, node_type="trigger", label="Start")
        out = Node.objects.create(workflow=wf, node_type="output", label="Out")
        orphan = Node.objects.create(workflow=wf, node_type="http", label="Órfão")
        Edge.objects.create(workflow=wf, source_node=trigger, target_node=out)
        # orphan não tem edge — não alcançável
        result = validate_dag(str(wf.id))
        assert result["valid"] is False
        assert any(str(orphan.id) == e["node_id"] for e in result["errors"])
        assert any("alcançável" in e["message"].lower() for e in result["errors"])

    def test_dag_linear_longo(self, db):
        """Pipeline com 5 nós em sequência deve ser válido."""
        wf = Workflow.objects.create(name="Pipeline Longo")
        tipos = ["trigger", "http", "transform", "llm", "output"]
        nodes = [Node.objects.create(workflow=wf, node_type=t, label=t) for t in tipos]
        for i in range(len(nodes) - 1):
            Edge.objects.create(workflow=wf, source_node=nodes[i], target_node=nodes[i + 1])
        result = validate_dag(str(wf.id))
        assert result["valid"] is True


@pytest.mark.django_db
class TestFindUnreachableNodes:
    def test_sem_trigger_retorna_todos(self, db):
        wf = Workflow.objects.create(name="SemTrigger")
        n = Node.objects.create(workflow=wf, node_type="output", label="Out")
        unreachable = find_unreachable_nodes(str(wf.id))
        assert str(n.id) in unreachable

    def test_todos_alcancaveis(self, workflow_with_nodes):
        unreachable = find_unreachable_nodes(str(workflow_with_nodes.id))
        assert unreachable == []

    def test_workflow_inexistente_retorna_lista_vazia(self):
        result = find_unreachable_nodes("00000000-0000-0000-0000-000000000000")
        assert result == []
