"""
Motor de execução do FlowForge.

Resolve a ordem topológica do grafo (DAG) e executa
cada nó na sequência correta, passando outputs como inputs.
"""

import logging
import time
from collections import defaultdict, deque
from typing import Any

from asgiref.sync import async_to_sync
from django.utils import timezone

logger = logging.getLogger(__name__)


class WorkflowExecutor:
    """Executa um workflow resolvendo o DAG e chamando handlers."""

    def __init__(self, run):
        self.run = run
        self.workflow = run.workflow
        self.node_outputs: dict[str, Any] = {}

    def execute(self) -> dict[str, Any]:
        """
        Executa o workflow completo.

        Returns:
            Resultado final do workflow.
        """
        from flowforge.models import NodeExecution, Run

        self.run.status = Run.Status.RUNNING
        self.run.started_at = timezone.now()
        self.run.save(update_fields=["status", "started_at"])

        try:
            # Resolve ordem topológica
            execution_order = self._topological_sort()

            # Registra total de nós antes de executar
            self.run.nodes_total = len(execution_order)
            self.run.nodes_completed = 0
            self.run.save(update_fields=["nodes_total", "nodes_completed"])

            # Cria NodeExecution para cada nó
            node_executions = {}
            for i, node in enumerate(execution_order):
                ne = NodeExecution.objects.create(
                    run=self.run,
                    node=node,
                    execution_order=i,
                )
                node_executions[str(node.id)] = ne

            # Executa cada nó na ordem
            for node in execution_order:
                ne = node_executions[str(node.id)]
                self._execute_node(node, ne)

                if ne.status == "failed":
                    raise RuntimeError(
                        f"Nó '{node.label}' falhou: {ne.error_message}"
                    )

                self.run.nodes_completed += 1
                self.run.save(update_fields=["nodes_completed"])

            # Sucesso
            output = self._get_final_output(execution_order)
            self.run.status = Run.Status.SUCCESS
            self.run.output_data = output
            self.run.finished_at = timezone.now()
            self.run.duration_ms = int(
                (self.run.finished_at - self.run.started_at).total_seconds() * 1000
            )
            self.run.save()

            self._emit(
                "run_completed",
                {
                    "run_id": str(self.run.id),
                    "status": "success",
                    "nodes_completed": self.run.nodes_completed,
                    "nodes_total": self.run.nodes_total,
                    "duration_ms": self.run.duration_ms,
                    "output_data": output,
                    "timestamp": timezone.now().isoformat(),
                },
            )

            return output

        except Exception as e:
            logger.exception("Workflow execution falhou: %s", e)
            self.run.status = Run.Status.FAILED
            self.run.error_message = str(e)
            self.run.finished_at = timezone.now()
            self.run.duration_ms = int(
                (self.run.finished_at - self.run.started_at).total_seconds() * 1000
            )
            self.run.save()

            self._emit(
                "run_failed",
                {
                    "run_id": str(self.run.id),
                    "status": "failed",
                    "error_message": str(e),
                    "nodes_completed": self.run.nodes_completed,
                    "nodes_total": self.run.nodes_total,
                    "duration_ms": self.run.duration_ms,
                    "timestamp": timezone.now().isoformat(),
                },
            )

            return {"error": str(e)}

    def _topological_sort(self) -> list:
        """
        Resolve a ordem topológica do DAG usando Kahn's algorithm.

        Returns:
            Lista de nós na ordem de execução.

        Raises:
            ValueError: Se o grafo contém ciclos.
        """
        nodes = list(self.workflow.nodes.all())
        edges = list(self.workflow.edges.all())

        # Monta grafo de adjacência e in-degree
        in_degree = defaultdict(int)
        adjacency = defaultdict(list)
        node_map = {str(n.id): n for n in nodes}

        for node in nodes:
            in_degree[str(node.id)] = 0

        for edge in edges:
            src = str(edge.source_node_id)
            tgt = str(edge.target_node_id)
            adjacency[src].append(tgt)
            in_degree[tgt] += 1

        # Inicia com nós sem dependências (in_degree == 0)
        queue = deque([nid for nid, deg in in_degree.items() if deg == 0])
        result = []

        while queue:
            nid = queue.popleft()
            result.append(node_map[nid])

            for neighbor in adjacency[nid]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(result) != len(nodes):
            raise ValueError("O workflow contém ciclos — não é um DAG válido.")

        return result

    def _execute_node(self, node, node_execution) -> None:
        """Executa um nó individual chamando o handler apropriado."""
        from flowforge.engine.handlers import get_handler
        from flowforge.models import NodeExecution

        node_execution.status = NodeExecution.Status.RUNNING
        node_execution.started_at = timezone.now()
        node_execution.save(update_fields=["status", "started_at"])

        self._emit(
            "node_started",
            {
                "node_id": str(node.id),
                "node_label": node.label,
                "node_type": node.node_type,
                "execution_order": node_execution.execution_order,
                "timestamp": timezone.now().isoformat(),
            },
        )

        start = time.time()

        try:
            # Coleta inputs dos nós anteriores
            input_data = self._collect_inputs(node)
            node_execution.input_data = input_data

            # Chama handler
            handler = get_handler(node.node_type)
            output = handler(node, input_data, self.run)

            # Salva output
            self.node_outputs[str(node.id)] = output
            node_execution.output_data = output
            node_execution.status = NodeExecution.Status.SUCCESS

        except Exception as e:
            node_execution.status = NodeExecution.Status.FAILED
            node_execution.error_message = str(e)
            logger.error("Nó %s falhou: %s", node.label, e)

        finally:
            node_execution.finished_at = timezone.now()
            node_execution.duration_ms = int((time.time() - start) * 1000)
            node_execution.save()

        if node_execution.status == NodeExecution.Status.SUCCESS:
            self._emit(
                "node_completed",
                {
                    "node_id": str(node.id),
                    "node_label": node.label,
                    "node_type": node.node_type,
                    "status": "success",
                    "output_data": node_execution.output_data,
                    "duration_ms": node_execution.duration_ms,
                    "execution_order": node_execution.execution_order,
                    "timestamp": timezone.now().isoformat(),
                },
            )
        else:
            self._emit(
                "node_failed",
                {
                    "node_id": str(node.id),
                    "node_label": node.label,
                    "node_type": node.node_type,
                    "status": "failed",
                    "error_message": node_execution.error_message,
                    "duration_ms": node_execution.duration_ms,
                    "execution_order": node_execution.execution_order,
                    "timestamp": timezone.now().isoformat(),
                },
            )

    def _collect_inputs(self, node) -> dict:
        """Coleta outputs dos nós conectados como input deste nó."""
        edges = self.workflow.edges.filter(target_node=node)
        inputs = {}

        for edge in edges:
            src_id = str(edge.source_node_id)
            if src_id in self.node_outputs:
                key = edge.source_handle or "default"
                inputs[key] = self.node_outputs[src_id]

        # Se é trigger, usa input_data do run
        if node.node_type == "trigger":
            inputs["trigger"] = self.run.input_data

        return inputs

    def _get_final_output(self, execution_order: list) -> dict:
        """Retorna output do último nó (ou do nó output)."""
        for node in reversed(execution_order):
            if node.node_type == "output":
                return self.node_outputs.get(str(node.id), {})

        if execution_order:
            last = execution_order[-1]
            return self.node_outputs.get(str(last.id), {})

        return {}

    def _emit(self, event_type: str, payload: dict) -> None:
        """
        Emite evento para o grupo WebSocket da run.

        Usa async_to_sync para enviar do contexto síncrono do Celery.
        Nunca propaga exceções — falhas no WebSocket não devem derrubar a execução.

        Args:
            event_type: Tipo do evento (ex: "node_started").
            payload: Dados do evento.
        """
        try:
            from channels.layers import get_channel_layer

            channel_layer = get_channel_layer()
            if channel_layer is None:
                return

            group_name = f"workflow_run_{self.run.id}"
            async_to_sync(channel_layer.group_send)(
                group_name,
                {"type": event_type, **payload},
            )
        except Exception:
            logger.warning("Falha ao emitir evento WebSocket: %s", event_type, exc_info=True)
