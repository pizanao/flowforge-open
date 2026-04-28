"""Seed dos templates de integração do FlowForge com os projetos do portfólio.

Templates:
- dataflow-trigger   → dispara pipeline no DataFlow Agent
- infrawatch-analyze → analisa servidor no InfraWatch AI
- govsearch-crawl    → dispara crawl no GovSearch AI
"""

from django.core.management.base import BaseCommand

from flowforge.models import WorkflowTemplate


class Command(BaseCommand):
    help = "Cria os 3 templates de integração com os projetos do portfólio"

    def handle(self, *args, **options) -> None:
        self._create_dataflow_trigger()
        self._create_infrawatch_analyze()
        self._create_govsearch_crawl()
        self.stdout.write(self.style.SUCCESS("3 templates de integração criados."))

    # ── DataFlow Agent ──────────────────────────────────────────────────────

    def _create_dataflow_trigger(self) -> None:
        """Template que autentica e dispara um pipeline no DataFlow Agent."""
        WorkflowTemplate.objects.update_or_create(
            slug="dataflow-trigger",
            defaults={
                "name": "DataFlow — Processar Pipeline",
                "description": (
                    "Autentica no DataFlow Agent e dispara um pipeline de processamento "
                    "de dados. Notifica via Telegram ao final."
                ),
                "category": "Integração",
                "tags": ["dataflow", "pipeline", "etl", "integração"],
                "nodes_data": [
                    {
                        "_ref": "n1",
                        "node_type": "trigger",
                        "label": "Iniciar",
                        "config": {"trigger_type": "manual"},
                        "position_x": 80,
                        "position_y": 200,
                    },
                    {
                        "_ref": "n2",
                        "node_type": "http",
                        "label": "Autenticar DataFlow",
                        "config": {
                            "method": "POST",
                            "url": "http://localhost:8001/api/auth/token/",
                            "headers": {"Content-Type": "application/json"},
                            "body": {"username": "admin", "password": "admin"},
                        },
                        "position_x": 300,
                        "position_y": 200,
                    },
                    {
                        "_ref": "n3",
                        "node_type": "transform",
                        "label": "Extrair Token",
                        "config": {
                            "operation": "pick",
                            "params": {"keys": ["access"]},
                        },
                        "position_x": 520,
                        "position_y": 200,
                    },
                    {
                        "_ref": "n4",
                        "node_type": "http",
                        "label": "Trigger Pipeline",
                        "config": {
                            "method": "POST",
                            "url": "http://localhost:8001/api/pipelines/{{pipeline_id}}/trigger/",
                            "headers": {
                                "Content-Type": "application/json",
                                "Authorization": "Bearer {{access}}",
                            },
                            "body": {},
                        },
                        "position_x": 740,
                        "position_y": 200,
                    },
                    {
                        "_ref": "n5",
                        "node_type": "condition",
                        "label": "Sucesso?",
                        "config": {
                            "field": "status",
                            "operator": "eq",
                            "value": "queued",
                        },
                        "position_x": 960,
                        "position_y": 200,
                    },
                    {
                        "_ref": "n6",
                        "node_type": "telegram",
                        "label": "Notificar Sucesso",
                        "config": {
                            "text": "✅ *DataFlow Agent*\nPipeline `{{pipeline_id}}` disparado com sucesso!\nStatus: queued ⏳",
                            "parse_mode": "Markdown",
                        },
                        "position_x": 1180,
                        "position_y": 100,
                    },
                    {
                        "_ref": "n7",
                        "node_type": "telegram",
                        "label": "Notificar Falha",
                        "config": {
                            "text": "❌ *DataFlow Agent*\nFalha ao disparar pipeline `{{pipeline_id}}`.\nVerifique o DataFlow.",
                            "parse_mode": "Markdown",
                        },
                        "position_x": 1180,
                        "position_y": 300,
                    },
                    {
                        "_ref": "n8",
                        "node_type": "output",
                        "label": "Resultado",
                        "config": {"format": "summary"},
                        "position_x": 1400,
                        "position_y": 200,
                    },
                ],
                "edges_data": [
                    {"source_ref": "n1", "target_ref": "n2"},
                    {"source_ref": "n2", "target_ref": "n3"},
                    {"source_ref": "n3", "target_ref": "n4"},
                    {"source_ref": "n4", "target_ref": "n5"},
                    {"source_ref": "n5", "target_ref": "n6", "source_handle": "true",  "label": "OK"},
                    {"source_ref": "n5", "target_ref": "n7", "source_handle": "false", "label": "Falha"},
                    {"source_ref": "n6", "target_ref": "n8"},
                    {"source_ref": "n7", "target_ref": "n8"},
                ],
            },
        )
        self.stdout.write("  ✓ dataflow-trigger")

    # ── InfraWatch AI ───────────────────────────────────────────────────────

    def _create_infrawatch_analyze(self) -> None:
        """Template que autentica e dispara análise de anomalia no InfraWatch AI."""
        WorkflowTemplate.objects.update_or_create(
            slug="infrawatch-analyze",
            defaults={
                "name": "InfraWatch — Analisar Servidor",
                "description": (
                    "Recebe um alerta via webhook, autentica no InfraWatch AI, "
                    "dispara análise de anomalia com LLM e envia resumo via Telegram."
                ),
                "category": "Integração",
                "tags": ["infrawatch", "monitoring", "ai", "anomalia", "integração"],
                "nodes_data": [
                    {
                        "_ref": "n1",
                        "node_type": "trigger",
                        "label": "Receber Alerta",
                        "config": {"trigger_type": "webhook"},
                        "position_x": 80,
                        "position_y": 200,
                    },
                    {
                        "_ref": "n2",
                        "node_type": "http",
                        "label": "Autenticar InfraWatch",
                        "config": {
                            "method": "POST",
                            "url": "http://localhost:8005/api/auth/token/",
                            "headers": {"Content-Type": "application/json"},
                            "body": {"username": "admin", "password": "admin"},
                        },
                        "position_x": 300,
                        "position_y": 200,
                    },
                    {
                        "_ref": "n3",
                        "node_type": "transform",
                        "label": "Extrair Token",
                        "config": {
                            "operation": "pick",
                            "params": {"keys": ["access"]},
                        },
                        "position_x": 520,
                        "position_y": 200,
                    },
                    {
                        "_ref": "n4",
                        "node_type": "http",
                        "label": "Analisar Servidor",
                        "config": {
                            "method": "POST",
                            "url": "http://localhost:8005/api/servers/{{server_id}}/analyze/",
                            "headers": {
                                "Content-Type": "application/json",
                                "Authorization": "Bearer {{access}}",
                            },
                            "body": {},
                        },
                        "position_x": 740,
                        "position_y": 200,
                    },
                    {
                        "_ref": "n5",
                        "node_type": "llm",
                        "label": "Resumir Análise",
                        "config": {
                            "prompt_template": (
                                "Você é um especialista em infraestrutura. "
                                "Resuma em exatamente 2 linhas objetivas a análise abaixo:\n\n"
                                "{{data}}"
                            ),
                        },
                        "position_x": 960,
                        "position_y": 200,
                    },
                    {
                        "_ref": "n6",
                        "node_type": "telegram",
                        "label": "Alertar Pizani",
                        "config": {
                            "text": (
                                "🚨 *InfraWatch AI*\n"
                                "Servidor `{{server_id}}` analisado.\n\n"
                                "{{response}}"
                            ),
                            "parse_mode": "Markdown",
                        },
                        "position_x": 1180,
                        "position_y": 200,
                    },
                    {
                        "_ref": "n7",
                        "node_type": "output",
                        "label": "Resultado",
                        "config": {"format": "summary"},
                        "position_x": 1400,
                        "position_y": 200,
                    },
                ],
                "edges_data": [
                    {"source_ref": "n1", "target_ref": "n2"},
                    {"source_ref": "n2", "target_ref": "n3"},
                    {"source_ref": "n3", "target_ref": "n4"},
                    {"source_ref": "n4", "target_ref": "n5"},
                    {"source_ref": "n5", "target_ref": "n6"},
                    {"source_ref": "n6", "target_ref": "n7"},
                ],
            },
        )
        self.stdout.write("  ✓ infrawatch-analyze")

    # ── GovSearch AI ────────────────────────────────────────────────────────

    def _create_govsearch_crawl(self) -> None:
        """Template que autentica e dispara crawl de uma fonte no GovSearch AI."""
        WorkflowTemplate.objects.update_or_create(
            slug="govsearch-crawl",
            defaults={
                "name": "GovSearch — Crawl de Fonte",
                "description": (
                    "Autentica no GovSearch AI, dispara crawl de uma fonte governamental, "
                    "aguarda indexação e notifica via Telegram com o resultado."
                ),
                "category": "Integração",
                "tags": ["govsearch", "crawler", "rag", "gov", "integração"],
                "nodes_data": [
                    {
                        "_ref": "n1",
                        "node_type": "trigger",
                        "label": "Iniciar Crawl",
                        "config": {"trigger_type": "manual"},
                        "position_x": 80,
                        "position_y": 200,
                    },
                    {
                        "_ref": "n2",
                        "node_type": "http",
                        "label": "Autenticar GovSearch",
                        "config": {
                            "method": "POST",
                            "url": "http://localhost:8004/api/auth/token/",
                            "headers": {"Content-Type": "application/json"},
                            "body": {"username": "admin", "password": "admin"},
                        },
                        "position_x": 300,
                        "position_y": 200,
                    },
                    {
                        "_ref": "n3",
                        "node_type": "transform",
                        "label": "Extrair Token",
                        "config": {
                            "operation": "pick",
                            "params": {"keys": ["access"]},
                        },
                        "position_x": 520,
                        "position_y": 200,
                    },
                    {
                        "_ref": "n4",
                        "node_type": "http",
                        "label": "Disparar Crawl",
                        "config": {
                            "method": "POST",
                            "url": "http://localhost:8004/api/sources/{{source_id}}/crawl/",
                            "headers": {
                                "Content-Type": "application/json",
                                "Authorization": "Bearer {{access}}",
                            },
                            "body": {},
                        },
                        "position_x": 740,
                        "position_y": 200,
                    },
                    {
                        "_ref": "n5",
                        "node_type": "delay",
                        "label": "Aguardar Indexação",
                        "config": {"seconds": 5},
                        "position_x": 960,
                        "position_y": 200,
                    },
                    {
                        "_ref": "n6",
                        "node_type": "http",
                        "label": "Verificar Status",
                        "config": {
                            "method": "GET",
                            "url": "http://localhost:8004/api/sources/{{source_id}}/",
                            "headers": {"Authorization": "Bearer {{access}}"},
                        },
                        "position_x": 1180,
                        "position_y": 200,
                    },
                    {
                        "_ref": "n7",
                        "node_type": "telegram",
                        "label": "Notificar Conclusão",
                        "config": {
                            "text": (
                                "🔍 *GovSearch AI*\n"
                                "Crawl da fonte `{{source_id}}` finalizado!\n"
                                "Documentos indexados: {{document_count}}\n"
                                "Status: {{status}}"
                            ),
                            "parse_mode": "Markdown",
                        },
                        "position_x": 1400,
                        "position_y": 200,
                    },
                    {
                        "_ref": "n8",
                        "node_type": "output",
                        "label": "Resultado",
                        "config": {"format": "summary"},
                        "position_x": 1620,
                        "position_y": 200,
                    },
                ],
                "edges_data": [
                    {"source_ref": "n1", "target_ref": "n2"},
                    {"source_ref": "n2", "target_ref": "n3"},
                    {"source_ref": "n3", "target_ref": "n4"},
                    {"source_ref": "n4", "target_ref": "n5"},
                    {"source_ref": "n5", "target_ref": "n6"},
                    {"source_ref": "n6", "target_ref": "n7"},
                    {"source_ref": "n7", "target_ref": "n8"},
                ],
            },
        )
        self.stdout.write("  ✓ govsearch-crawl")
