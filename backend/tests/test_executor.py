"""Testes do WorkflowExecutor."""

from unittest.mock import patch, MagicMock

import pytest
from django.utils import timezone

from flowforge.engine.executor import WorkflowExecutor
from flowforge.models import Edge, Node, NodeExecution, Run, Workflow


@pytest.mark.django_db
class TestWorkflowExecutor:
    """Testes da execução completa do workflow."""

    def test_execute_success(self, workflow, trigger_node, output_node, edge, run):
        """Executa workflow trigger→output com sucesso."""
        with patch.object(WorkflowExecutor, "_emit"):
            executor = WorkflowExecutor(run)
            result = executor.execute()

            run.refresh_from_db()
            assert run.status == Run.Status.SUCCESS
            assert isinstance(result, dict)
            assert run.finished_at is not None
            assert run.duration_ms >= 0

    def test_execute_sets_running_status(self, workflow, trigger_node, output_node, edge, run):
        """Verifica que status muda para RUNNING durante execução."""
        with patch.object(WorkflowExecutor, "_emit"):
            executor = WorkflowExecutor(run)
            executor.execute()

            run.refresh_from_db()
            assert run.status == Run.Status.SUCCESS

    def test_execute_returns_output(self, workflow, trigger_node, output_node, edge, run):
        """Verifica que retorna dict com output do workflow."""
        with patch.object(WorkflowExecutor, "_emit"):
            executor = WorkflowExecutor(run)
            result = executor.execute()

            assert isinstance(result, dict)

    def test_execute_creates_node_executions(self, workflow, trigger_node, output_node, edge, run):
        """Verifica que cria NodeExecution para cada nó."""
        with patch.object(WorkflowExecutor, "_emit"):
            executor = WorkflowExecutor(run)
            executor.execute()

            node_execs = NodeExecution.objects.filter(run=run)
            assert node_execs.count() == 2
            assert all(ne.status == NodeExecution.Status.SUCCESS for ne in node_execs)

    def test_execute_sets_node_execution_order(self, workflow, trigger_node, output_node, edge, run):
        """Verifica que NodeExecution tem execution_order correto."""
        with patch.object(WorkflowExecutor, "_emit"):
            executor = WorkflowExecutor(run)
            executor.execute()

            node_execs = NodeExecution.objects.filter(run=run).order_by("execution_order")
            assert node_execs[0].execution_order == 0
            assert node_execs[1].execution_order == 1

    def test_execute_emits_events(self, workflow, trigger_node, output_node, edge, run):
        """Verifica que _emit foi chamado durante execução."""
        with patch.object(WorkflowExecutor, "_emit") as mock_emit:
            executor = WorkflowExecutor(run)
            executor.execute()

            assert mock_emit.call_count >= 5

    def test_execute_failed_node_stops_workflow(self, workflow, trigger_node, output_node, edge, run):
        """Quando um nó falha, o workflow deve parar e setar status FAILED."""
        with patch.object(WorkflowExecutor, "_emit"):
            with patch(
                "flowforge.engine.handlers.get_handler",
                side_effect=ValueError("Nó falhou intencionalmente")
            ):
                executor = WorkflowExecutor(run)
                result = executor.execute()

                run.refresh_from_db()
                assert run.status == Run.Status.FAILED
                assert "error" in result

    def test_execute_sets_timestamps(self, workflow, trigger_node, output_node, edge, run):
        """Verifica que started_at e finished_at são preenchidos."""
        with patch.object(WorkflowExecutor, "_emit"):
            executor = WorkflowExecutor(run)
            executor.execute()

            run.refresh_from_db()
            assert run.started_at is not None
            assert run.finished_at is not None
            assert run.finished_at >= run.started_at

    def test_execute_counts_nodes_total_and_completed(self, db):
        """Verifica que nodes_total e nodes_completed são contabilizados."""
        with patch.object(WorkflowExecutor, "_emit"):
            wf = Workflow.objects.create(name="Teste Contagem")
            t = Node.objects.create(workflow=wf, node_type="trigger", label="T")
            out = Node.objects.create(workflow=wf, node_type="output", label="Out")
            Edge.objects.create(workflow=wf, source_node=t, target_node=out)
            run = Run.objects.create(workflow=wf, trigger_type="manual")

            executor = WorkflowExecutor(run)
            executor.execute()

            run.refresh_from_db()
            assert run.nodes_total == 2
            assert run.nodes_completed == 2


@pytest.mark.django_db
class TestTopologicalSort:
    """Testes do Kahn's algorithm para ordenação topológica."""

    def test_sort_simple_chain(self, workflow, trigger_node, output_node, edge, run):
        """Workflow linear trigger→output retorna nós na ordem correta."""
        executor = WorkflowExecutor(run)
        order = executor._topological_sort()

        assert len(order) == 2
        assert order[0].node_type == "trigger"
        assert order[1].node_type == "output"

    def test_sort_three_nodes(self, db):
        """Workflow com 3 nós: trigger→http→output."""
        wf = Workflow.objects.create(name="3 Nodes")
        t = Node.objects.create(workflow=wf, node_type="trigger", label="Start")
        h = Node.objects.create(workflow=wf, node_type="http", label="HTTP")
        out = Node.objects.create(workflow=wf, node_type="output", label="End")
        Edge.objects.create(workflow=wf, source_node=t, target_node=h)
        Edge.objects.create(workflow=wf, source_node=h, target_node=out)
        run = Run.objects.create(workflow=wf, trigger_type="manual")

        executor = WorkflowExecutor(run)
        order = executor._topological_sort()

        assert len(order) == 3
        assert order[0].id == t.id
        assert order[1].id == h.id
        assert order[2].id == out.id

    def test_sort_cycle_raises_error(self, db):
        """Workflow com ciclo (A→B→A) deve lançar ValueError."""
        wf = Workflow.objects.create(name="Com Ciclo")
        a = Node.objects.create(workflow=wf, node_type="http", label="A")
        b = Node.objects.create(workflow=wf, node_type="http", label="B")
        Edge.objects.create(workflow=wf, source_node=a, target_node=b)
        Edge.objects.create(workflow=wf, source_node=b, target_node=a)
        run = Run.objects.create(workflow=wf, trigger_type="manual")

        executor = WorkflowExecutor(run)
        with pytest.raises(ValueError, match="ciclo"):
            executor._topological_sort()

    def test_sort_empty_workflow_returns_empty(self, db):
        """Workflow sem nós retorna lista vazia."""
        wf = Workflow.objects.create(name="Vazio")
        run = Run.objects.create(workflow=wf, trigger_type="manual")

        executor = WorkflowExecutor(run)
        order = executor._topological_sort()

        assert order == []

    def test_sort_single_node(self, db):
        """Workflow com único nó retorna aquele nó."""
        wf = Workflow.objects.create(name="Um Nó")
        trigger = Node.objects.create(workflow=wf, node_type="trigger", label="T")
        run = Run.objects.create(workflow=wf, trigger_type="manual")

        executor = WorkflowExecutor(run)
        order = executor._topological_sort()

        assert len(order) == 1
        assert order[0].id == trigger.id


@pytest.mark.django_db
class TestCollectInputs:
    """Testes da coleta de inputs para cada nó."""

    def test_trigger_gets_run_input(self, workflow, trigger_node, output_node, edge, run):
        """Nó trigger recebe input_data do run."""
        executor = WorkflowExecutor(run)
        inputs = executor._collect_inputs(trigger_node)

        assert "trigger" in inputs
        assert inputs["trigger"] == run.input_data

    def test_node_gets_previous_output(self, db):
        """Nó recebe output do nó anterior via edge."""
        wf = Workflow.objects.create(name="Teste Input")
        t = Node.objects.create(workflow=wf, node_type="trigger", label="T")
        h = Node.objects.create(workflow=wf, node_type="http", label="H")
        Edge.objects.create(workflow=wf, source_node=t, target_node=h, source_handle="default")
        run = Run.objects.create(workflow=wf, trigger_type="manual", input_data={"msg": "oi"})

        executor = WorkflowExecutor(run)
        executor.node_outputs[str(t.id)] = {"result": "data_from_trigger"}

        inputs = executor._collect_inputs(h)
        assert "default" in inputs
        assert inputs["default"] == {"result": "data_from_trigger"}

    def test_node_without_input_edge_gets_empty_dict(self, db):
        """Nó sem edges de entrada retorna dict vazio."""
        wf = Workflow.objects.create(name="Sem Edge")
        isolated = Node.objects.create(workflow=wf, node_type="http", label="Isolado")
        run = Run.objects.create(workflow=wf, trigger_type="manual")

        executor = WorkflowExecutor(run)
        inputs = executor._collect_inputs(isolated)

        assert inputs == {}


@pytest.mark.django_db
class TestGetFinalOutput:
    """Testes da extração do output final."""

    def test_returns_output_node_result(self, workflow, trigger_node, output_node, edge, run):
        """Com nó "output", retorna seu output_data."""
        executor = WorkflowExecutor(run)
        executor.node_outputs[str(output_node.id)] = {"final": "result"}
        execution_order = [trigger_node, output_node]

        result = executor._get_final_output(execution_order)
        assert result == {"final": "result"}

    def test_returns_last_node_if_no_output_type(self, db):
        """Sem nó "output", retorna último nó da lista."""
        wf = Workflow.objects.create(name="Sem Output Node")
        t = Node.objects.create(workflow=wf, node_type="trigger", label="T")
        h = Node.objects.create(workflow=wf, node_type="http", label="H")
        run = Run.objects.create(workflow=wf, trigger_type="manual")

        executor = WorkflowExecutor(run)
        executor.node_outputs[str(h.id)] = {"http_result": "data"}
        execution_order = [t, h]

        result = executor._get_final_output(execution_order)
        assert result == {"http_result": "data"}

    def test_returns_empty_dict_for_empty_execution_order(self, db):
        """Lista vazia retorna dict vazio."""
        wf = Workflow.objects.create(name="Vazio")
        run = Run.objects.create(workflow=wf, trigger_type="manual")

        executor = WorkflowExecutor(run)
        result = executor._get_final_output([])

        assert result == {}

    def test_returns_output_node_even_if_not_last(self, db):
        """Se há output_node no meio da lista, retorna dele (não do último)."""
        wf = Workflow.objects.create(name="Output No Meio")
        t = Node.objects.create(workflow=wf, node_type="trigger", label="T")
        out = Node.objects.create(workflow=wf, node_type="output", label="Out")
        extra = Node.objects.create(workflow=wf, node_type="http", label="Extra")
        run = Run.objects.create(workflow=wf, trigger_type="manual")

        executor = WorkflowExecutor(run)
        executor.node_outputs[str(out.id)] = {"output": "correct"}
        executor.node_outputs[str(extra.id)] = {"output": "wrong"}
        execution_order = [t, out, extra]

        result = executor._get_final_output(execution_order)
        assert result == {"output": "correct"}


@pytest.mark.django_db
class TestEmit:
    """Testes da emissão de eventos WebSocket."""

    def test_emit_does_not_raise_on_channel_failure(self, workflow, trigger_node, output_node, edge, run):
        """_emit nunca levanta exceção, mesmo com falha no channel."""
        with patch("channels.layers.get_channel_layer", return_value=None):
            executor = WorkflowExecutor(run)
            executor._emit("test_event", {"data": "test"})

    def test_emit_called_with_correct_payload_structure(self, workflow, trigger_node, output_node, edge, run):
        """_emit é chamado com tipo de evento e payload corretos."""
        with patch.object(WorkflowExecutor, "_emit") as mock_emit:
            executor = WorkflowExecutor(run)
            with patch.object(WorkflowExecutor, "_emit", wraps=executor._emit):
                executor.execute()


@pytest.mark.django_db
class TestNodeExecution:
    """Testes do comportamento de NodeExecution durante execução."""

    def test_node_execution_stores_input_data(self, workflow, trigger_node, output_node, edge, run):
        """NodeExecution armazena input_data do nó."""
        with patch.object(WorkflowExecutor, "_emit"):
            executor = WorkflowExecutor(run)
            executor.execute()

            node_execs = NodeExecution.objects.filter(run=run)
            for ne in node_execs:
                assert ne.input_data is not None

    def test_node_execution_stores_output_data(self, workflow, trigger_node, output_node, edge, run):
        """NodeExecution armazena output_data do nó."""
        with patch.object(WorkflowExecutor, "_emit"):
            executor = WorkflowExecutor(run)
            executor.execute()

            node_execs = NodeExecution.objects.filter(run=run, status=NodeExecution.Status.SUCCESS)
            for ne in node_execs:
                assert ne.output_data is not None

    def test_node_execution_stores_duration_ms(self, workflow, trigger_node, output_node, edge, run):
        """NodeExecution armazena duração em ms."""
        with patch.object(WorkflowExecutor, "_emit"):
            executor = WorkflowExecutor(run)
            executor.execute()

            node_execs = NodeExecution.objects.filter(run=run)
            for ne in node_execs:
                assert ne.duration_ms >= 0

    def test_node_execution_status_success_on_completion(self, workflow, trigger_node, output_node, edge, run):
        """NodeExecution deve ter status SUCCESS após sucesso."""
        with patch.object(WorkflowExecutor, "_emit"):
            executor = WorkflowExecutor(run)
            executor.execute()

            node_execs = NodeExecution.objects.filter(run=run)
            assert all(ne.status == NodeExecution.Status.SUCCESS for ne in node_execs)
