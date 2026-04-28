"""Serializers do FlowForge."""

from rest_framework import serializers

from flowforge.models import Edge, Node, NodeExecution, Run, Workflow, WorkflowTemplate


def validate_node_config(node_type: str, config: dict) -> list[str]:
    """
    Valida o config de um nó conforme seu tipo.

    Args:
        node_type: Tipo do nó (ex: "http", "condition").
        config: Dict de configuração a validar.

    Returns:
        Lista de mensagens de erro. Vazia significa config válida.
    """
    errors: list[str] = []
    if node_type == "http":
        if not config.get("url"):
            errors.append("Campo 'url' é obrigatório para nós HTTP.")
    elif node_type == "condition":
        if not config.get("field"):
            errors.append("Campo 'field' é obrigatório para nós Condition.")
        if not config.get("operator"):
            errors.append("Campo 'operator' é obrigatório para nós Condition.")
        if config.get("value") is None:
            errors.append("Campo 'value' é obrigatório para nós Condition.")
    elif node_type == "delay":
        seconds = config.get("seconds")
        if seconds is not None:
            if not isinstance(seconds, int) or seconds < 1:
                errors.append("Campo 'seconds' deve ser um inteiro >= 1 para nós Delay.")
    elif node_type == "email":
        if not config.get("to"):
            errors.append("Campo 'to' é obrigatório para nós Email.")
    return errors


# ── Node & Edge ─────────────────────────────────────────

class NodeSerializer(serializers.ModelSerializer):
    """Serializer de nó com posição e config."""

    class Meta:
        model = Node
        fields = [
            "id", "workflow", "node_type", "label", "config",
            "position_x", "position_y", "created_at",
        ]
        read_only_fields = ["created_at"]

    def validate(self, data: dict) -> dict:
        """Impede mais de um nó trigger por workflow e valida config por tipo."""
        node_type = data.get("node_type") or getattr(self.instance, "node_type", None)

        if node_type == "trigger":
            workflow = data.get("workflow") or getattr(self.instance, "workflow", None)
            if workflow:
                qs = Node.objects.filter(workflow=workflow, node_type="trigger")
                if self.instance:
                    qs = qs.exclude(pk=self.instance.pk)
                if qs.exists():
                    raise serializers.ValidationError(
                        {"node_type": "Já existe um nó trigger neste workflow."}
                    )

        config = data.get("config") or getattr(self.instance, "config", {}) or {}
        if node_type and config:
            config_errors = validate_node_config(node_type, config)
            if config_errors:
                raise serializers.ValidationError({"config": config_errors})

        return data


class EdgeSerializer(serializers.ModelSerializer):
    """Serializer de conexão entre nós."""

    class Meta:
        model = Edge
        fields = [
            "id", "workflow", "source_node", "target_node",
            "source_handle", "label", "created_at",
        ]
        read_only_fields = ["created_at"]

    def validate(self, data: dict) -> dict:
        """Impede self-loop (source == target)."""
        source = data.get("source_node") or getattr(self.instance, "source_node", None)
        target = data.get("target_node") or getattr(self.instance, "target_node", None)
        if source and target and source == target:
            raise serializers.ValidationError(
                "source_node e target_node não podem ser o mesmo nó."
            )
        return data


# ── Workflow ────────────────────────────────────────────

class WorkflowListSerializer(serializers.ModelSerializer):
    """Versão compacta para listagens."""

    node_count = serializers.IntegerField(read_only=True, default=0)
    run_count = serializers.IntegerField(read_only=True, default=0)
    last_run_status = serializers.CharField(read_only=True, default="")

    class Meta:
        model = Workflow
        fields = [
            "id", "name", "description", "status", "version",
            "tags", "node_count", "run_count", "last_run_status",
            "created_at", "updated_at",
        ]


class WorkflowDetailSerializer(serializers.ModelSerializer):
    """Versão completa com nós e conexões para o editor."""

    nodes = NodeSerializer(many=True, read_only=True)
    edges = EdgeSerializer(many=True, read_only=True)
    recent_runs = serializers.SerializerMethodField()

    class Meta:
        model = Workflow
        fields = "__all__"

    def get_recent_runs(self, obj: Workflow) -> list:
        runs = obj.runs.all()[:5]
        return RunListSerializer(runs, many=True).data


# ── Run ─────────────────────────────────────────────────

class RunListSerializer(serializers.ModelSerializer):
    """Versão compacta de execuções."""

    workflow_name = serializers.CharField(
        source="workflow.name", read_only=True,
    )

    class Meta:
        model = Run
        fields = [
            "id", "workflow", "workflow_name", "status",
            "trigger_type", "duration_ms", "nodes_total",
            "nodes_completed", "started_at", "finished_at",
            "created_at",
        ]


class NodeExecutionSerializer(serializers.ModelSerializer):
    """Execução de nó individual."""

    node_label = serializers.CharField(source="node.label", read_only=True)
    node_type = serializers.CharField(source="node.node_type", read_only=True)

    class Meta:
        model = NodeExecution
        fields = [
            "id", "node", "node_label", "node_type", "status",
            "input_data", "output_data", "duration_ms",
            "error_message", "execution_order", "started_at",
            "finished_at",
        ]


class RunDetailSerializer(serializers.ModelSerializer):
    """Versão completa com execuções por nó."""

    workflow_name = serializers.CharField(
        source="workflow.name", read_only=True,
    )
    node_executions = NodeExecutionSerializer(many=True, read_only=True)

    class Meta:
        model = Run
        fields = "__all__"


class WorkflowTemplateSerializer(serializers.ModelSerializer):
    """Serializer de template de workflow para a galeria."""

    class Meta:
        model = WorkflowTemplate
        fields = ["slug", "name", "description", "category", "tags"]
