"""Seed dos templates de workflow para a galeria do FlowForge."""

from django.core.management.base import BaseCommand

from flowforge.models import WorkflowTemplate


class Command(BaseCommand):
    help = "Cria os 5 templates padrão para a galeria de workflows"

    def handle(self, *args, **options):
        self._create_whatsapp_notificacao()
        self._create_whatsapp_agente()
        self._create_monitor_http()
        self._create_daily_briefing()
        self._create_etl_transform()
        self.stdout.write(self.style.SUCCESS("5 templates criados/atualizados."))

    def _create_whatsapp_notificacao(self):
        """Notificação WhatsApp simples via webhook."""
        WorkflowTemplate.objects.update_or_create(
            slug="whatsapp-notificacao",
            defaults={
                "name": "Notificação WhatsApp",
                "description": "Recebe evento via webhook, formata os dados e envia uma mensagem WhatsApp via Waha.",
                "category": "WhatsApp",
                "tags": ["whatsapp", "webhook", "notificacao"],
                "nodes_data": [
                    {
                        "_ref": "n1", "node_type": "trigger", "label": "Webhook",
                        "config": {"trigger_type": "webhook"},
                        "position_x": 80, "position_y": 200,
                    },
                    {
                        "_ref": "n2", "node_type": "transform", "label": "Formatar Dados",
                        "config": {"operation": "pick", "params": {"keys": ["message", "from", "timestamp"]}},
                        "position_x": 300, "position_y": 200,
                    },
                    {
                        "_ref": "n3", "node_type": "whatsapp", "label": "Enviar WhatsApp",
                        "config": {
                            "phone": "5511999999999",
                            "text": "📩 Nova mensagem de {{from}}:\n\n{{message}}\n\n🕐 {{timestamp}}",
                            "session": "default",
                        },
                        "position_x": 520, "position_y": 200,
                    },
                    {
                        "_ref": "n4", "node_type": "output", "label": "Concluído",
                        "config": {"format": "summary"},
                        "position_x": 740, "position_y": 200,
                    },
                ],
                "edges_data": [
                    {"source_ref": "n1", "target_ref": "n2"},
                    {"source_ref": "n2", "target_ref": "n3"},
                    {"source_ref": "n3", "target_ref": "n4"},
                ],
            },
        )

    def _create_whatsapp_agente(self):
        """Agente LLM que responde via WhatsApp."""
        WorkflowTemplate.objects.update_or_create(
            slug="whatsapp-agente",
            defaults={
                "name": "Agente WhatsApp + LLM",
                "description": "Recebe mensagem via webhook, processa com Ollama e envia resposta inteligente via WhatsApp.",
                "category": "IA",
                "tags": ["llm", "whatsapp", "webhook", "agente", "ollama"],
                "nodes_data": [
                    {
                        "_ref": "n1", "node_type": "trigger", "label": "Webhook",
                        "config": {"trigger_type": "webhook"},
                        "position_x": 80, "position_y": 200,
                    },
                    {
                        "_ref": "n2", "node_type": "llm", "label": "Agente LLM",
                        "config": {
                            "prompt_template": (
                                "Você é um assistente inteligente.\n\n"
                                "Mensagem recebida: {{message}}\n"
                                "De: {{from}}\n\n"
                                "Responda de forma clara, útil e empática. Máximo 3 parágrafos."
                            ),
                        },
                        "position_x": 300, "position_y": 200,
                    },
                    {
                        "_ref": "n3", "node_type": "whatsapp", "label": "Responder via WhatsApp",
                        "config": {
                            "phone": "5511999999999",
                            "text": "🤖 {{response}}",
                            "session": "default",
                        },
                        "position_x": 520, "position_y": 200,
                    },
                    {
                        "_ref": "n4", "node_type": "output", "label": "Concluído",
                        "config": {"format": "summary"},
                        "position_x": 740, "position_y": 200,
                    },
                ],
                "edges_data": [
                    {"source_ref": "n1", "target_ref": "n2"},
                    {"source_ref": "n2", "target_ref": "n3"},
                    {"source_ref": "n3", "target_ref": "n4"},
                ],
            },
        )

    def _create_monitor_http(self):
        """Monitor de endpoint com alerta WhatsApp."""
        WorkflowTemplate.objects.update_or_create(
            slug="monitor-http",
            defaults={
                "name": "Monitor HTTP + Alerta WhatsApp",
                "description": "Verifica periodicamente um endpoint HTTP e envia alerta WhatsApp se estiver fora do ar.",
                "category": "Monitoramento",
                "tags": ["monitor", "whatsapp", "schedule", "condition", "http"],
                "nodes_data": [
                    {
                        "_ref": "n1", "node_type": "trigger", "label": "Cron Horário",
                        "config": {"trigger_type": "schedule", "schedule": "0 * * * *"},
                        "position_x": 80, "position_y": 220,
                    },
                    {
                        "_ref": "n2", "node_type": "http", "label": "Check Endpoint",
                        "config": {"method": "GET", "url": "https://api.exemplo.com/health", "timeout": 10},
                        "position_x": 280, "position_y": 220,
                    },
                    {
                        "_ref": "n3", "node_type": "condition", "label": "Retornou 200?",
                        "config": {"field": "ok", "operator": "eq", "value": "True"},
                        "position_x": 480, "position_y": 220,
                    },
                    {
                        "_ref": "n4", "node_type": "whatsapp", "label": "⚠️ Alerta de Falha",
                        "config": {
                            "phone": "5511999999999",
                            "text": "⚠️ *Monitor FlowForge*\n\nEndpoint fora do ar!\n🔗 {{url}}\nStatus: {{status_code}}\n🕐 {{date}} às {{time}}",
                            "session": "default",
                        },
                        "position_x": 700, "position_y": 120,
                    },
                    {
                        "_ref": "n5", "node_type": "output", "label": "Tudo OK",
                        "config": {"format": "summary"},
                        "position_x": 700, "position_y": 320,
                    },
                ],
                "edges_data": [
                    {"source_ref": "n1", "target_ref": "n2"},
                    {"source_ref": "n2", "target_ref": "n3"},
                    {"source_ref": "n3", "target_ref": "n4", "source_handle": "false", "label": "Falha"},
                    {"source_ref": "n3", "target_ref": "n5", "source_handle": "true", "label": "OK"},
                ],
            },
        )

    def _create_daily_briefing(self):
        """Briefing diário via Telegram + LLM."""
        prompt = (
            "Você é um assistente executivo. Hoje é {{weekday}}, {{date}} às {{time}}.\n\n"
            "Gere um Daily Briefing CURTO com base nas métricas abaixo:\n\n"
            "- Workflows ativos: {{total_workflows}}\n"
            "- Execuções totais: {{total_runs}}\n"
            "- Taxa de sucesso: {{success_rate}}%\n"
            "- Duração média: {{avg_duration_ms}}ms\n\n"
            "REGRAS: Máximo 8 linhas. Use emojis. Termine com uma frase motivacional."
        )
        WorkflowTemplate.objects.update_or_create(
            slug="daily-briefing",
            defaults={
                "name": "Daily Briefing (Telegram + LLM)",
                "description": "Envia um briefing diário automático via Telegram com métricas do FlowForge geradas pelo Ollama.",
                "category": "IA",
                "tags": ["briefing", "telegram", "llm", "cron", "ollama"],
                "nodes_data": [
                    {
                        "_ref": "n1", "node_type": "trigger", "label": "Cron 09:00",
                        "config": {"trigger_type": "schedule", "schedule": "0 9 * * *"},
                        "position_x": 80, "position_y": 200,
                    },
                    {
                        "_ref": "n2", "node_type": "http", "label": "FlowForge Stats",
                        "config": {
                            "method": "GET",
                            "url": "http://backend:8006/api/workflows/stats/",
                            "timeout": 10,
                        },
                        "position_x": 280, "position_y": 200,
                    },
                    {
                        "_ref": "n3", "node_type": "llm", "label": "Gerar Briefing",
                        "config": {"prompt_template": prompt},
                        "position_x": 480, "position_y": 200,
                    },
                    {
                        "_ref": "n4", "node_type": "telegram", "label": "Enviar Telegram",
                        "config": {"text": "{{response}}", "parse_mode": ""},
                        "position_x": 680, "position_y": 200,
                    },
                    {
                        "_ref": "n5", "node_type": "output", "label": "Concluído",
                        "config": {"format": "summary"},
                        "position_x": 880, "position_y": 200,
                    },
                ],
                "edges_data": [
                    {"source_ref": "n1", "target_ref": "n2"},
                    {"source_ref": "n2", "target_ref": "n3"},
                    {"source_ref": "n3", "target_ref": "n4"},
                    {"source_ref": "n4", "target_ref": "n5"},
                ],
            },
        )

    def _create_etl_transform(self):
        """ETL com transformação de campos."""
        WorkflowTemplate.objects.update_or_create(
            slug="etl-transform",
            defaults={
                "name": "ETL com Transform",
                "description": "Busca dados de uma API, seleciona e renomeia campos, envia ao destino.",
                "category": "Dados",
                "tags": ["etl", "transform", "api", "dados"],
                "nodes_data": [
                    {
                        "_ref": "n1", "node_type": "trigger", "label": "Início",
                        "config": {"trigger_type": "manual"},
                        "position_x": 80, "position_y": 200,
                    },
                    {
                        "_ref": "n2", "node_type": "http", "label": "Buscar Dados",
                        "config": {"method": "GET", "url": "https://api.exemplo.com/registros"},
                        "position_x": 280, "position_y": 200,
                    },
                    {
                        "_ref": "n3", "node_type": "transform", "label": "Selecionar Campos",
                        "config": {"operation": "pick", "params": {"keys": ["id", "nome", "valor"]}},
                        "position_x": 480, "position_y": 200,
                    },
                    {
                        "_ref": "n4", "node_type": "http", "label": "Enviar ao Destino",
                        "config": {
                            "method": "POST",
                            "url": "https://api.destino.com/inserir",
                            "headers": {"Content-Type": "application/json"},
                        },
                        "position_x": 680, "position_y": 200,
                    },
                    {
                        "_ref": "n5", "node_type": "output", "label": "Resultado",
                        "config": {"format": "summary"},
                        "position_x": 880, "position_y": 200,
                    },
                ],
                "edges_data": [
                    {"source_ref": "n1", "target_ref": "n2"},
                    {"source_ref": "n2", "target_ref": "n3"},
                    {"source_ref": "n3", "target_ref": "n4"},
                    {"source_ref": "n4", "target_ref": "n5"},
                ],
            },
        )
