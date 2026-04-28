"""
Cria o workflow "FlowForge Demo" para gravação de portfólio.

Pipeline:
  Trigger (manual)
      → LLM (Ollama — gera 1 frase de sucesso)
      → WhatsApp (Waha — envia para o telefone configurado)
      → Output

Uso:
  python manage.py seed_whatsapp_demo
  python manage.py seed_whatsapp_demo --phone 5567933001234
"""

import os

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Cria o workflow FlowForge Demo com envio real via WhatsApp (Waha)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--phone",
            default=os.getenv("DEMO_WHATSAPP_PHONE", "5567933001234"),
            help="Número WhatsApp destino (DDI+DDD+número, sem @c.us)",
        )

    def handle(self, *args, **options):
        phone = options["phone"]
        self._create_workflow(phone)
        self.stdout.write(self.style.SUCCESS(
            f"\n✓ Workflow 'FlowForge Demo' criado.\n"
            f"  WhatsApp destino: {phone}\n\n"
            "Abra o FlowForge e clique em 'FlowForge Demo' para gravar a demo:\n"
            "  ./flowforge.sh demo"
        ))

    def _create_workflow(self, phone: str) -> None:
        from flowforge.models import Edge, Node, Workflow

        wf, _ = Workflow.objects.update_or_create(
            name="FlowForge Demo",
            defaults={
                "description": "Demo de portfólio — executa LLM + envia WhatsApp em tempo real.",
                "status": "active",
                "tags": ["demo", "whatsapp", "llm", "portfolio"],
            },
        )
        wf.nodes.all().delete()
        wf.edges.all().delete()

        whatsapp_text = (
            "🎬 *FlowForge Demo executada!*\n\n"
            "✅ Workflow visual no-code rodando em tempo real.\n\n"
            "📅 {{date}} às {{time}}\n"
            "🔗 http://localhost:5106"
        )

        n1 = Node.objects.create(
            workflow=wf, node_type="trigger", label="Iniciar Demo",
            position_x=80, position_y=200,
            config={"trigger_type": "manual"},
        )
        n2 = Node.objects.create(
            workflow=wf, node_type="transform", label="Formatar Dados",
            position_x=300, position_y=200,
            config={"operation": "passthrough"},
        )
        n3 = Node.objects.create(
            workflow=wf, node_type="whatsapp", label="Enviar WhatsApp",
            position_x=520, position_y=200,
            config={
                "phone": phone,
                "text": whatsapp_text,
                "session": "default",
            },
        )
        n4 = Node.objects.create(
            workflow=wf, node_type="output", label="Concluído",
            position_x=740, position_y=200,
            config={"format": "summary"},
        )

        Edge.objects.create(workflow=wf, source_node=n1, target_node=n2)
        Edge.objects.create(workflow=wf, source_node=n2, target_node=n3)
        Edge.objects.create(workflow=wf, source_node=n3, target_node=n4)

        self.stdout.write(f"  Workflow '{wf.name}' criado: 4 nós, 3 edges.")
