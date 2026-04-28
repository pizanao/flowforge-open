"""Admin do FlowForge."""

from django.contrib import admin
from flowforge.models import Edge, Node, NodeExecution, Run, Workflow, WorkflowTemplate


@admin.register(Workflow)
class WorkflowAdmin(admin.ModelAdmin):
    list_display = ["name", "status", "version", "created_at", "updated_at"]
    list_filter = ["status"]
    search_fields = ["name"]


@admin.register(Node)
class NodeAdmin(admin.ModelAdmin):
    list_display = ["label", "node_type", "workflow", "position_x", "position_y"]
    list_filter = ["node_type"]
    raw_id_fields = ["workflow"]


@admin.register(Edge)
class EdgeAdmin(admin.ModelAdmin):
    list_display = ["source_node", "target_node", "source_handle", "workflow"]
    raw_id_fields = ["workflow", "source_node", "target_node"]


@admin.register(Run)
class RunAdmin(admin.ModelAdmin):
    list_display = ["workflow", "status", "trigger_type", "duration_ms", "created_at"]
    list_filter = ["status", "trigger_type"]
    raw_id_fields = ["workflow"]


@admin.register(WorkflowTemplate)
class WorkflowTemplateAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "category"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(NodeExecution)
class NodeExecutionAdmin(admin.ModelAdmin):
    list_display = ["node", "status", "execution_order", "duration_ms"]
    list_filter = ["status"]
    raw_id_fields = ["run", "node"]
