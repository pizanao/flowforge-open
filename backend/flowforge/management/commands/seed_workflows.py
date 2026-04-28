"""Seed de workflows demo para o FlowForge."""

from django.core.management.base import BaseCommand

from flowforge.models import Edge, Node, Run, NodeExecution, Workflow


class Command(BaseCommand):
    help = "Cria workflows demo para demonstração do editor"

    def handle(self, *args, **options):
        self._create_data_pipeline()
        self._create_notification_flow()
        self._create_llm_analysis()
        self.stdout.write(self.style.SUCCESS("3 workflows demo criados."))

    def _create_data_pipeline(self):
        """Workflow: API → Transform → Condition → Output."""
        wf, _ = Workflow.objects.update_or_create(
            name="Data Pipeline",
            defaults={
                "description": "Coleta dados de API, transforma e filtra por condição.",
                "status": "active",
                "tags": ["demo", "data", "api"],
            },
        )
        wf.nodes.all().delete()
        wf.edges.all().delete()

        n1 = Node.objects.create(workflow=wf, node_type="trigger", label="Start", position_x=80, position_y=200, config={"trigger": "manual"})
        n2 = Node.objects.create(workflow=wf, node_type="http", label="Fetch API", position_x=280, position_y=200, config={"method": "GET", "url": "https://api.example.com/data"})
        n3 = Node.objects.create(workflow=wf, node_type="transform", label="Clean Data", position_x=480, position_y=200, config={"operation": "pick", "params": {"keys": ["id", "name", "value"]}})
        n4 = Node.objects.create(workflow=wf, node_type="condition", label="Value > 100?", position_x=680, position_y=200, config={"field": "value", "operator": "gt", "value": "100"})
        n5 = Node.objects.create(workflow=wf, node_type="output", label="Result", position_x=880, position_y=200, config={"format": "summary"})

        Edge.objects.create(workflow=wf, source_node=n1, target_node=n2)
        Edge.objects.create(workflow=wf, source_node=n2, target_node=n3)
        Edge.objects.create(workflow=wf, source_node=n3, target_node=n4)
        Edge.objects.create(workflow=wf, source_node=n4, target_node=n5, source_handle="true")

        # Cria run demo
        run = Run.objects.create(workflow=wf, status="success", trigger_type="manual", duration_ms=1240, nodes_total=5, nodes_completed=5, output_data={"summary": True, "data": {"id": 42, "name": "Teste", "value": 150}})
        for i, node in enumerate([n1, n2, n3, n4, n5]):
            NodeExecution.objects.create(run=run, node=node, status="success", execution_order=i, duration_ms=[10, 520, 15, 5, 3][i])

    def _create_notification_flow(self):
        """Workflow: Trigger → HTTP → Delay → Email."""
        wf, _ = Workflow.objects.update_or_create(
            name="Notification Flow",
            defaults={
                "description": "Recebe webhook, aguarda e envia email de notificação.",
                "status": "active",
                "tags": ["demo", "notification", "email"],
            },
        )
        wf.nodes.all().delete()
        wf.edges.all().delete()

        n1 = Node.objects.create(workflow=wf, node_type="trigger", label="Webhook", position_x=80, position_y=180, config={"trigger": "webhook"})
        n2 = Node.objects.create(workflow=wf, node_type="http", label="Get Details", position_x=300, position_y=180, config={"method": "GET", "url": "https://api.example.com/details/{{id}}"})
        n3 = Node.objects.create(workflow=wf, node_type="delay", label="Wait 5s", position_x=520, position_y=180, config={"seconds": 5})
        n4 = Node.objects.create(workflow=wf, node_type="email", label="Send Alert", position_x=740, position_y=180, config={"to": "admin@example.com", "subject": "Alerta: {{name}}"})

        Edge.objects.create(workflow=wf, source_node=n1, target_node=n2)
        Edge.objects.create(workflow=wf, source_node=n2, target_node=n3)
        Edge.objects.create(workflow=wf, source_node=n3, target_node=n4)

    def _create_llm_analysis(self):
        """Workflow: Trigger → HTTP → LLM → Condition → Email/Output."""
        wf, _ = Workflow.objects.update_or_create(
            name="LLM Analysis Pipeline",
            defaults={
                "description": "Coleta dados, analisa com Claude e decide se notifica.",
                "status": "draft",
                "tags": ["demo", "llm", "analysis"],
            },
        )
        wf.nodes.all().delete()
        wf.edges.all().delete()

        n1 = Node.objects.create(workflow=wf, node_type="trigger", label="Cron Diário", position_x=80, position_y=220, config={"trigger": "cron", "schedule": "0 8 * * *"})
        n2 = Node.objects.create(workflow=wf, node_type="http", label="Fetch Metrics", position_x=300, position_y=220, config={"method": "GET", "url": "https://api.example.com/metrics"})
        n3 = Node.objects.create(workflow=wf, node_type="llm", label="Analyze", position_x=520, position_y=220, config={"prompt_template": "Analise estas métricas e diga se há anomalias: {{data}}", "model": "claude-sonnet-4-20250514"})
        n4 = Node.objects.create(workflow=wf, node_type="condition", label="Anomalia?", position_x=740, position_y=220, config={"field": "anomaly_detected", "operator": "eq", "value": "true"})
        n5 = Node.objects.create(workflow=wf, node_type="email", label="Alert Team", position_x=940, position_y=140, config={"to": "team@example.com", "subject": "Anomalia detectada"})
        n6 = Node.objects.create(workflow=wf, node_type="output", label="All Clear", position_x=940, position_y=300, config={"format": "summary"})

        Edge.objects.create(workflow=wf, source_node=n1, target_node=n2)
        Edge.objects.create(workflow=wf, source_node=n2, target_node=n3)
        Edge.objects.create(workflow=wf, source_node=n3, target_node=n4)
        Edge.objects.create(workflow=wf, source_node=n4, target_node=n5, source_handle="true", label="Sim")
        Edge.objects.create(workflow=wf, source_node=n4, target_node=n6, source_handle="false", label="Não")
