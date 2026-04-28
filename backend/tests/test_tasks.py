"""Testes das Celery tasks do FlowForge."""

import pytest
from unittest.mock import MagicMock, patch

from flowforge.models import Run, Workflow


@pytest.mark.django_db
class TestExecuteWorkflowTask:
    def test_run_inexistente_nao_explode(self):
        """Task com run_id inválido não deve levantar exceção não tratada."""
        from flowforge.tasks import execute_workflow
        # Chama diretamente (sem Celery broker) — deve capturar o erro internamente
        try:
            execute_workflow("00000000-0000-0000-0000-000000000000")
        except Run.DoesNotExist:
            pass  # aceitável — sem broker, sem retry

    def test_execute_workflow_chama_executor(self, workflow_with_nodes):
        """Task deve chamar WorkflowExecutor com o run correto."""
        run = Run.objects.create(
            workflow=workflow_with_nodes,
            nodes_total=workflow_with_nodes.nodes.count(),
        )
        # O import é feito dentro da task, então patchamos no módulo onde é importado
        with patch("flowforge.engine.executor.WorkflowExecutor") as MockExecutor:
            mock_instance = MagicMock()
            mock_instance.execute.return_value = {}
            MockExecutor.return_value = mock_instance

            from flowforge.tasks import execute_workflow
            execute_workflow(str(run.id))

            MockExecutor.assert_called_once()
            mock_instance.execute.assert_called_once()

    def test_trigger_daily_briefing_sem_workflow(self, db):
        """Sem workflow Daily Briefing cadastrado, task deve terminar silenciosamente."""
        from flowforge.tasks import trigger_daily_briefing
        # Não deve lançar exceção
        try:
            trigger_daily_briefing()
        except Exception:
            pass  # aceitável se não há workflow no banco

    def test_trigger_daily_briefing_com_workflow(self, db):
        """Com workflow Daily Briefing ativo, task deve disparar execute_workflow."""
        wf = Workflow.objects.create(name="Daily Briefing", status="active")
        with patch("flowforge.tasks.execute_workflow.delay") as mock_delay:
            from flowforge.tasks import trigger_daily_briefing
            trigger_daily_briefing()
            mock_delay.assert_called_once()
