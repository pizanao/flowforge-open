"""
Cria o workflow Daily Briefing com cron às 09:00 (America/Sao_Paulo).

Pipeline:
  Trigger (schedule 0 9 * * *)
      → LLM (Ollama qwen2.5:3b — gera o briefing)
      → Telegram (envia para o chat do usuário)
      → Output
"""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Cria o workflow Daily Briefing e o agendamento Celery Beat"

    def handle(self, *args, **options):
        self._create_workflow()
        self._create_periodic_task()
        self.stdout.write(self.style.SUCCESS(
            "Daily Briefing criado! Roda todo dia às 09:00 (America/Sao_Paulo).\n"
            "Certifique-se de que o serviço 'celerybeat' está rodando:\n"
            "  docker compose up -d celerybeat"
        ))

    def _create_workflow(self):
        from flowforge.models import Edge, Node, Workflow

        wf, _ = Workflow.objects.update_or_create(
            name="Daily Briefing",
            defaults={
                "description": "Briefing diário automático às 09:00 entregue no Telegram.",
                "status": "active",
                "tags": ["briefing", "telegram", "llm", "cron"],
            },
        )
        wf.nodes.all().delete()
        wf.edges.all().delete()

        prompt = """Você é um assistente executivo preciso e direto.
Hoje é {{weekday}}, {{date}} às {{time}}.

Com base nas informações abaixo sobre os projetos e métricas do FlowForge, gere um Daily Briefing CURTO para o usuário.

DADOS DO DIA:
- Data: {{weekday}}, {{date}}
- Workflows ativos: {{total_workflows}}
- Total de execuções: {{total_runs}}
- Taxa de sucesso: {{success_rate}}%
- Duração média: {{avg_duration_ms}}ms

REGRAS OBRIGATÓRIAS:
1. Máximo 10 linhas no total
2. Use emojis para cada seção
3. Se não há nada urgente: escreva "Dia tranquilo 😎" e pare
4. Se algo precisa de atenção: destaque com ⚠️
5. Termine com uma frase motivacional curta ou status do dia
6. NÃO invente dados — use apenas o que foi fornecido acima

FORMATO ESPERADO:
☀️ Briefing — [Dia Semana] [Data]

📊 FlowForge: [X] workflows · [Y] execuções · [Z]% sucesso
[linha de status ou alerta se necessário]

[Frase final]"""

        n1 = Node.objects.create(
            workflow=wf, node_type="trigger", label="Cron 09:00",
            position_x=80, position_y=200,
            config={"trigger_type": "schedule", "schedule": "0 9 * * *"},
        )
        n2 = Node.objects.create(
            workflow=wf, node_type="http", label="FlowForge Stats",
            position_x=280, position_y=200,
            config={
                "method": "GET",
                "url": "http://backend:8006/api/workflows/stats/",
                "timeout": 10,
            },
        )
        n3 = Node.objects.create(
            workflow=wf, node_type="llm", label="Gerar Briefing",
            position_x=480, position_y=200,
            config={
                "model": "llama3.1:8b",
                "prompt_template": prompt,
            },
        )
        n4 = Node.objects.create(
            workflow=wf, node_type="telegram", label="Enviar Telegram",
            position_x=680, position_y=200,
            config={
                "text": "{{response}}",
                "parse_mode": "",
            },
        )
        n5 = Node.objects.create(
            workflow=wf, node_type="output", label="Concluído",
            position_x=880, position_y=200,
            config={"format": "summary"},
        )

        Edge.objects.create(workflow=wf, source_node=n1, target_node=n2)
        Edge.objects.create(workflow=wf, source_node=n2, target_node=n3)
        Edge.objects.create(workflow=wf, source_node=n3, target_node=n4)
        Edge.objects.create(workflow=wf, source_node=n4, target_node=n5)

        self.stdout.write(f"  Workflow '{wf.name}' criado com 5 nós.")

    def _create_periodic_task(self):
        try:
            from django_celery_beat.models import CrontabSchedule, PeriodicTask
            import json

            schedule, _ = CrontabSchedule.objects.get_or_create(
                minute="0",
                hour="9",
                day_of_week="*",
                day_of_month="*",
                month_of_year="*",
                timezone="America/Sao_Paulo",
            )

            task, created = PeriodicTask.objects.update_or_create(
                name="Daily Briefing — 09:00",
                defaults={
                    "task": "flowforge.tasks.trigger_daily_briefing",
                    "crontab": schedule,
                    "enabled": True,
                    "kwargs": json.dumps({}),
                    "description": "Envia briefing diário via Telegram às 09:00 (BRT)",
                },
            )

            status = "criado" if created else "atualizado"
            self.stdout.write(f"  PeriodicTask '{task.name}' {status}.")

        except Exception as e:
            self.stdout.write(self.style.WARNING(
                f"  django_celery_beat não disponível: {e}\n"
                f"  Execute: python manage.py migrate para criar as tabelas."
            ))
