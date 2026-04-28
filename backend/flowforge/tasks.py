"""
Tasks Celery do FlowForge.

Execução assíncrona de workflows via Celery workers.
"""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, acks_late=True)
def execute_workflow(self, run_id: str) -> dict:
    """
    Executa um workflow de forma assíncrona.

    Args:
        run_id: UUID da Run a executar.

    Returns:
        Resultado da execução.
    """
    from flowforge.engine.executor import WorkflowExecutor
    from flowforge.models import Run

    try:
        run = Run.objects.select_related("workflow").get(id=run_id)
    except Run.DoesNotExist:
        logger.error("Run %s não encontrada", run_id)
        return {"error": "Run não encontrada"}

    executor = WorkflowExecutor(run)
    result = executor.execute()

    logger.info(
        "Workflow '%s' executado: status=%s, duration=%dms",
        run.workflow.name,
        run.status,
        run.duration_ms,
    )

    return {
        "run_id": str(run.id),
        "status": run.status,
        "duration_ms": run.duration_ms,
        "output": result,
    }


@shared_task(bind=True, max_retries=1, acks_late=True)
def trigger_daily_briefing(self) -> dict:
    """
    Dispara o workflow 'Daily Briefing' automaticamente.
    Chamado pelo Celery Beat todo dia às 09:00 (America/Sao_Paulo).
    """
    from flowforge.models import Run, Workflow

    try:
        workflow = Workflow.objects.get(name="Daily Briefing")
    except Workflow.DoesNotExist:
        logger.error("Workflow 'Daily Briefing' não encontrado. Execute: python manage.py seed_daily_briefing")
        return {"error": "Workflow não encontrado"}

    from django.utils import timezone
    now = timezone.localtime()

    run = Run.objects.create(
        workflow=workflow,
        trigger_type="schedule",
        input_data={
            "source": "celery_beat",
            "date": now.strftime("%d/%m/%Y"),
            "weekday": ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"][now.weekday()],
            "time": now.strftime("%H:%M"),
        },
        nodes_total=workflow.nodes.count(),
    )

    execute_workflow.delay(str(run.id))
    logger.info("Daily Briefing disparado: run_id=%s", run.id)
    return {"run_id": str(run.id), "status": "triggered"}
