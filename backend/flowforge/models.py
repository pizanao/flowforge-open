"""
Modelos do FlowForge.

Estrutura: Workflow → Node/Edge (grafo visual)
           Workflow → Run → NodeExecution (execução)
"""

import uuid

from django.db import models


class TimeStampedModel(models.Model):
    """Modelo base com timestamps automáticos."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Workflow(TimeStampedModel):
    """Workflow: grafo de nós e conexões."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Rascunho"
        ACTIVE = "active", "Ativo"
        PAUSED = "paused", "Pausado"
        ARCHIVED = "archived", "Arquivado"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    version = models.PositiveIntegerField(default=1)
    tags = models.JSONField(default=list, blank=True)
    canvas_state = models.JSONField(
        default=dict,
        blank=True,
        help_text="Posição do viewport (zoom, pan) para restaurar o editor",
    )

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return f"{self.name} (v{self.version})"


class Node(TimeStampedModel):
    """Nó individual de um workflow."""

    class NodeType(models.TextChoices):
        TRIGGER = "trigger", "Trigger"
        HTTP = "http", "HTTP Request"
        TRANSFORM = "transform", "Transform"
        CONDITION = "condition", "Condição"
        LLM = "llm", "Agente LLM"
        EMAIL = "email", "Email"
        DELAY = "delay", "Delay"
        OUTPUT = "output", "Output"
        TELEGRAM = "telegram", "Telegram"
        WHATSAPP = "whatsapp", "WhatsApp"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workflow = models.ForeignKey(
        Workflow,
        on_delete=models.CASCADE,
        related_name="nodes",
    )
    node_type = models.CharField(max_length=20, choices=NodeType.choices)
    label = models.CharField(max_length=100)
    config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Configuração específica do tipo de nó",
    )
    position_x = models.FloatField(
        default=0,
        help_text="Posição X no canvas (pixels)",
    )
    position_y = models.FloatField(
        default=0,
        help_text="Posição Y no canvas (pixels)",
    )

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"[{self.node_type}] {self.label}"


class Edge(TimeStampedModel):
    """Conexão entre dois nós."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workflow = models.ForeignKey(
        Workflow,
        on_delete=models.CASCADE,
        related_name="edges",
    )
    source_node = models.ForeignKey(
        Node,
        on_delete=models.CASCADE,
        related_name="outgoing_edges",
    )
    target_node = models.ForeignKey(
        Node,
        on_delete=models.CASCADE,
        related_name="incoming_edges",
    )
    source_handle = models.CharField(
        max_length=20,
        default="default",
        help_text="Handle de saída (default, true, false para condition)",
    )
    label = models.CharField(max_length=50, blank=True, default="")

    class Meta:
        ordering = ["created_at"]
        unique_together = ["source_node", "target_node", "source_handle"]

    def __str__(self) -> str:
        return f"{self.source_node.label} → {self.target_node.label}"


class Run(TimeStampedModel):
    """Execução de um workflow."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        RUNNING = "running", "Executando"
        SUCCESS = "success", "Sucesso"
        FAILED = "failed", "Falhou"
        CANCELLED = "cancelled", "Cancelado"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workflow = models.ForeignKey(
        Workflow,
        on_delete=models.CASCADE,
        related_name="runs",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    trigger_type = models.CharField(
        max_length=20,
        default="manual",
        help_text="Como a execução foi disparada",
    )
    input_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Dados de entrada para o trigger",
    )
    output_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Resultado final do workflow",
    )
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    duration_ms = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True, default="")
    nodes_total = models.PositiveIntegerField(default=0)
    nodes_completed = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Run {self.id.hex[:8]} [{self.status}]"


class WorkflowTemplate(models.Model):
    """Template de workflow pré-configurado para a galeria."""

    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True, default="")
    category = models.CharField(max_length=50, blank=True, default="")
    tags = models.JSONField(default=list, blank=True)
    nodes_data = models.JSONField(
        default=list,
        help_text="Lista de nós: [{_ref, node_type, label, config, position_x, position_y}]",
    )
    edges_data = models.JSONField(
        default=list,
        help_text="Lista de edges: [{source_ref, target_ref, source_handle, label}]",
    )

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"[template] {self.name}"


class NodeExecution(TimeStampedModel):
    """Execução de um nó individual dentro de uma run."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        RUNNING = "running", "Executando"
        SUCCESS = "success", "Sucesso"
        FAILED = "failed", "Falhou"
        SKIPPED = "skipped", "Pulado"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    run = models.ForeignKey(
        Run,
        on_delete=models.CASCADE,
        related_name="node_executions",
    )
    node = models.ForeignKey(
        Node,
        on_delete=models.CASCADE,
        related_name="executions",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    input_data = models.JSONField(default=dict, blank=True)
    output_data = models.JSONField(default=dict, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    duration_ms = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True, default="")
    execution_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["execution_order"]

    def __str__(self) -> str:
        return f"{self.node.label} [{self.status}]"
