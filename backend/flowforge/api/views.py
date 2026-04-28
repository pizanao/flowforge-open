"""ViewSets do FlowForge."""

import hashlib
import hmac
import time

from django.conf import settings
from django.db.models import Avg, Count, Subquery, OuterRef
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from flowforge.models import Edge, Node, NodeExecution, Run, Workflow
from flowforge.api.serializers import (
    EdgeSerializer,
    NodeSerializer,
    RunDetailSerializer,
    RunListSerializer,
    WorkflowDetailSerializer,
    WorkflowListSerializer,
    WorkflowTemplateSerializer,
)


def _webhook_signature_is_valid(request, raw_body: bytes) -> bool:
    """
    Valida assinatura HMAC SHA-256 de webhook externo.

    Args:
        request: Requisição DRF recebida.
        raw_body: Corpo original da requisição em bytes.

    Returns:
        True quando timestamp e assinatura batem com o segredo configurado.
    """
    secret = settings.WEBHOOK_SIGNING_SECRET
    if not secret:
        return False

    timestamp = request.headers.get("X-FlowForge-Timestamp", "")
    received_signature = request.headers.get("X-FlowForge-Signature", "")
    if not timestamp or not received_signature.startswith("sha256="):
        return False

    try:
        request_timestamp = int(timestamp)
    except ValueError:
        return False

    tolerance = settings.WEBHOOK_SIGNATURE_TOLERANCE_SECONDS
    if abs(int(time.time()) - request_timestamp) > tolerance:
        return False

    signed_payload = timestamp.encode() + b"." + raw_body
    digest = hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()
    expected_signature = f"sha256={digest}"
    return hmac.compare_digest(expected_signature, received_signature)


class WorkflowViewSet(viewsets.ModelViewSet):
    """CRUD de workflows com ações de execução."""

    def get_serializer_class(self):
        if self.action == "list":
            return WorkflowListSerializer
        return WorkflowDetailSerializer

    def get_queryset(self):
        qs = Workflow.objects.all()
        if self.action == "list":
            qs = qs.annotate(
                node_count=Count("nodes"),
                run_count=Count("runs"),
            )
        return qs

    @action(detail=False, methods=["get"])
    def stats(self, request):
        """Estatísticas globais: total de workflows, execuções, taxa de sucesso e duração média."""
        total_workflows = Workflow.objects.count()
        total_runs = Run.objects.count()
        success_runs = Run.objects.filter(status=Run.Status.SUCCESS).count()
        success_rate = round(success_runs / total_runs * 100) if total_runs > 0 else 0
        avg_duration = (
            Run.objects.filter(status=Run.Status.SUCCESS, duration_ms__gt=0)
            .aggregate(avg=Avg("duration_ms"))["avg"] or 0
        )
        node_type_counts = list(
            Node.objects.values("node_type")
            .annotate(count=Count("id"))
            .order_by("-count")[:6]
        )
        return Response({
            "total_workflows": total_workflows,
            "total_runs": total_runs,
            "success_rate": success_rate,
            "avg_duration_ms": int(avg_duration),
            "node_type_counts": node_type_counts,
        })

    @action(detail=False, methods=["get"], url_path="templates")
    def templates_list(self, request):
        """Lista de templates disponíveis para a galeria."""
        from flowforge.models import WorkflowTemplate
        templates = WorkflowTemplate.objects.all()
        return Response(WorkflowTemplateSerializer(templates, many=True).data)

    @action(detail=False, methods=["post"], url_path=r"from-template/(?P<slug>[-\w]+)")
    def from_template(self, request, slug=None):
        """Cria um workflow a partir de um template pelo slug."""
        from flowforge.models import WorkflowTemplate
        try:
            template = WorkflowTemplate.objects.get(slug=slug)
        except WorkflowTemplate.DoesNotExist:
            return Response({"error": "Template não encontrado."}, status=status.HTTP_404_NOT_FOUND)

        wf = Workflow.objects.create(
            name=template.name,
            description=template.description,
            tags=template.tags,
        )

        node_id_map = {}
        for n in template.nodes_data:
            node = Node.objects.create(
                workflow=wf,
                node_type=n["node_type"],
                label=n["label"],
                config=n.get("config", {}),
                position_x=n.get("position_x", 0),
                position_y=n.get("position_y", 0),
            )
            node_id_map[n["_ref"]] = node

        for e in template.edges_data:
            Edge.objects.create(
                workflow=wf,
                source_node=node_id_map[e["source_ref"]],
                target_node=node_id_map[e["target_ref"]],
                source_handle=e.get("source_handle", "default"),
                label=e.get("label", ""),
            )

        return Response(WorkflowDetailSerializer(wf).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="webhook", permission_classes=[AllowAny])
    def webhook(self, request, pk=None):
        """Recebe chamada externa e dispara o workflow com o body como input."""
        raw_body = request.body
        if not _webhook_signature_is_valid(request, raw_body):
            return Response(
                {"error": "Assinatura do webhook inválida."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        workflow = self.get_object()
        from flowforge.tasks import execute_workflow
        run = Run.objects.create(
            workflow=workflow,
            trigger_type="webhook",
            input_data=request.data or {},
            nodes_total=workflow.nodes.count(),
        )
        execute_workflow.delay(str(run.id))
        return Response(
            {"run_id": str(run.id), "status": "execução iniciada"},
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=True, methods=["post"])
    def validate(self, request, pk=None):
        """Valida o DAG do workflow: ciclos, trigger único e nós inalcançáveis."""
        workflow = self.get_object()
        from flowforge.engine.dag_engine import validate_dag
        result = validate_dag(str(workflow.id))
        return Response(result, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def execute(self, request, pk=None):
        """Dispara execução do workflow."""
        workflow = self.get_object()
        input_data = request.data.get("input", {})

        from flowforge.tasks import execute_workflow
        run = Run.objects.create(
            workflow=workflow,
            trigger_type="manual",
            input_data=input_data,
            nodes_total=workflow.nodes.count(),
        )
        execute_workflow.delay(str(run.id))

        return Response(
            {"run_id": str(run.id), "status": "execução iniciada"},
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=True, methods=["post"])
    def duplicate(self, request, pk=None):
        """Duplica o workflow com todos os nós e conexões."""
        original = self.get_object()
        new_wf = Workflow.objects.create(
            name=f"{original.name} (cópia)",
            description=original.description,
            tags=original.tags,
        )

        node_map = {}
        for node in original.nodes.all():
            old_id = node.id
            node.pk = None
            node.workflow = new_wf
            node.save()
            node_map[old_id] = node

        for edge in original.edges.all():
            edge.pk = None
            edge.workflow = new_wf
            edge.source_node = node_map[edge.source_node_id]
            edge.target_node = node_map[edge.target_node_id]
            edge.save()

        return Response(
            WorkflowDetailSerializer(new_wf).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["put"])
    def save_graph(self, request, pk=None):
        """Salva o grafo completo (nós + edges) de uma vez."""
        workflow = self.get_object()
        nodes_data = request.data.get("nodes", [])
        edges_data = request.data.get("edges", [])
        canvas_state = request.data.get("canvas_state", {})

        # Atualiza ou cria nós
        existing_node_ids = set()
        for n in nodes_data:
            node, _ = Node.objects.update_or_create(
                id=n.get("id"),
                workflow=workflow,
                defaults={
                    "node_type": n["node_type"],
                    "label": n["label"],
                    "config": n.get("config", {}),
                    "position_x": n.get("position_x", 0),
                    "position_y": n.get("position_y", 0),
                },
            )
            existing_node_ids.add(str(node.id))

        # Remove nós que não estão mais no grafo
        workflow.nodes.exclude(id__in=existing_node_ids).delete()

        # Recria edges
        workflow.edges.all().delete()
        for e in edges_data:
            Edge.objects.create(
                workflow=workflow,
                source_node_id=e["source_node"],
                target_node_id=e["target_node"],
                source_handle=e.get("source_handle", "default"),
                label=e.get("label", ""),
            )

        # Salva estado do canvas
        workflow.canvas_state = canvas_state
        workflow.version += 1
        workflow.save(update_fields=["canvas_state", "version", "updated_at"])

        return Response(WorkflowDetailSerializer(workflow).data)


class NodeViewSet(viewsets.ModelViewSet):
    """CRUD de nós."""

    serializer_class = NodeSerializer

    def get_queryset(self):
        qs = Node.objects.all()
        workflow_id = self.request.query_params.get("workflow", "")
        if workflow_id:
            qs = qs.filter(workflow_id=workflow_id)
        return qs

    @action(detail=True, methods=["post"], url_path="dry-run")
    def dry_run(self, request, pk=None):
        """Executa um nó isolado sem persistir no banco."""
        import time
        from types import SimpleNamespace
        from flowforge.engine.handlers import get_handler

        node = self.get_object()
        input_data = request.data.get("input_data", {})

        run_mock = SimpleNamespace(
            id="dry-run",
            input_data=input_data,
            workflow=node.workflow,
        )

        start = time.time()
        try:
            handler = get_handler(node.node_type)
            output = handler(node, input_data, run_mock)
            duration_ms = int((time.time() - start) * 1000)
            return Response(
                {"output_data": output, "error": None, "duration_ms": duration_ms},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            duration_ms = int((time.time() - start) * 1000)
            return Response(
                {"output_data": None, "error": str(e), "duration_ms": duration_ms},
                status=status.HTTP_200_OK,
            )


class EdgeViewSet(viewsets.ModelViewSet):
    """CRUD de conexões."""

    serializer_class = EdgeSerializer

    def get_queryset(self):
        qs = Edge.objects.all()
        workflow_id = self.request.query_params.get("workflow", "")
        if workflow_id:
            qs = qs.filter(workflow_id=workflow_id)
        return qs


class RunViewSet(viewsets.ReadOnlyModelViewSet):
    """Listagem e detalhes de execuções."""

    def get_serializer_class(self):
        if self.action == "list":
            return RunListSerializer
        return RunDetailSerializer

    def get_queryset(self):
        qs = Run.objects.select_related("workflow")
        workflow_id = self.request.query_params.get("workflow", "")
        if workflow_id:
            qs = qs.filter(workflow_id=workflow_id)
        return qs

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Cancela uma execução em andamento."""
        run = self.get_object()
        if run.status in ("pending", "running"):
            from django.utils import timezone
            run.status = Run.Status.CANCELLED
            run.finished_at = timezone.now()
            run.save(update_fields=["status", "finished_at", "updated_at"])
        return Response(RunDetailSerializer(run).data)
