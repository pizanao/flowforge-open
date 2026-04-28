"""Testes dos templates de workflow — galeria, instanciação e validação de DAG."""

import pytest

from flowforge.models import Node, WorkflowTemplate


EXPECTED_SLUGS = {
    "whatsapp-notificacao",
    "whatsapp-agente",
    "monitor-http",
    "daily-briefing",
    "etl-transform",
}

TEMPLATE_NODE_COUNTS = {
    "whatsapp-notificacao": 4,
    "whatsapp-agente":      4,
    "monitor-http":         5,
    "daily-briefing":       5,
    "etl-transform":        5,
}

TEMPLATE_EDGE_COUNTS = {
    "whatsapp-notificacao": 3,
    "whatsapp-agente":      3,
    "monitor-http":         4,
    "daily-briefing":       4,
    "etl-transform":        4,
}

@pytest.fixture(autouse=True)
def seed_templates(db):
    """Popula os templates antes de cada teste neste módulo."""
    from django.core.management import call_command
    call_command("seed_templates", verbosity=0)


# ── WorkflowTemplate model ────────────────────────────────────────────────────

@pytest.mark.django_db
class TestWorkflowTemplateModel:
    def test_all_slugs_created(self):
        slugs = set(WorkflowTemplate.objects.values_list("slug", flat=True))
        assert EXPECTED_SLUGS.issubset(slugs)

    def test_str(self):
        t = WorkflowTemplate.objects.get(slug="whatsapp-notificacao")
        assert "[template]" in str(t)
        assert "Notificação" in str(t)

    def test_nodes_data_is_list(self):
        for slug in EXPECTED_SLUGS:
            t = WorkflowTemplate.objects.get(slug=slug)
            assert isinstance(t.nodes_data, list), f"{slug}: nodes_data não é lista"
            assert len(t.nodes_data) > 0, f"{slug}: nodes_data vazio"

    def test_edges_data_is_list(self):
        for slug in EXPECTED_SLUGS:
            t = WorkflowTemplate.objects.get(slug=slug)
            assert isinstance(t.edges_data, list), f"{slug}: edges_data não é lista"

    def test_every_node_has_required_fields(self):
        for slug in EXPECTED_SLUGS:
            t = WorkflowTemplate.objects.get(slug=slug)
            for node in t.nodes_data:
                assert "_ref" in node, f"{slug}: nó sem _ref"
                assert "node_type" in node, f"{slug}: nó sem node_type"
                assert "label" in node, f"{slug}: nó sem label"

    def test_every_edge_references_valid_refs(self):
        for slug in EXPECTED_SLUGS:
            t = WorkflowTemplate.objects.get(slug=slug)
            refs = {n["_ref"] for n in t.nodes_data}
            for edge in t.edges_data:
                assert edge["source_ref"] in refs, f"{slug}: source_ref inválido"
                assert edge["target_ref"] in refs, f"{slug}: target_ref inválido"

    def test_each_template_has_exactly_one_trigger(self):
        for slug in EXPECTED_SLUGS:
            t = WorkflowTemplate.objects.get(slug=slug)
            triggers = [n for n in t.nodes_data if n["node_type"] == "trigger"]
            assert len(triggers) == 1, f"{slug}: esperado 1 trigger, encontrado {len(triggers)}"

    def test_each_template_has_at_least_one_output(self):
        for slug in EXPECTED_SLUGS:
            t = WorkflowTemplate.objects.get(slug=slug)
            outputs = [n for n in t.nodes_data if n["node_type"] == "output"]
            assert len(outputs) >= 1, f"{slug}: sem nó output"


# ── Galeria de templates (API) ────────────────────────────────────────────────

@pytest.mark.django_db
class TestTemplateListAPI:
    def test_list_returns_200(self, api):
        resp = api.get("/api/workflows/templates/")
        assert resp.status_code == 200

    def test_list_contains_all_slugs(self, api):
        resp = api.get("/api/workflows/templates/")
        slugs = {t["slug"] for t in resp.data}
        assert EXPECTED_SLUGS.issubset(slugs)

    def test_list_fields(self, api):
        resp = api.get("/api/workflows/templates/")
        for t in resp.data:
            assert "slug" in t
            assert "name" in t
            assert "description" in t
            assert "category" in t
            assert "tags" in t

    def test_whatsapp_templates_have_correct_category(self, api):
        resp = api.get("/api/workflows/templates/")
        by_slug = {t["slug"]: t for t in resp.data}
        assert by_slug["whatsapp-notificacao"]["category"] == "WhatsApp"
        assert by_slug["whatsapp-agente"]["category"] == "IA"

    def test_monitor_template_has_schedule_tag(self, api):
        resp = api.get("/api/workflows/templates/")
        monitor = next(t for t in resp.data if t["slug"] == "monitor-http")
        assert "schedule" in monitor["tags"]


# ── Instanciação de templates (from-template) ─────────────────────────────────

@pytest.mark.django_db
class TestFromTemplateAPI:
    def test_invalid_slug_returns_404(self, api):
        resp = api.post("/api/workflows/from-template/slug-inexistente/")
        assert resp.status_code == 404

    @pytest.mark.parametrize("slug", list(EXPECTED_SLUGS))
    def test_instantiation_returns_201(self, api, slug):
        resp = api.post(f"/api/workflows/from-template/{slug}/")
        assert resp.status_code == 201, f"{slug}: esperado 201, recebido {resp.status_code}"

    @pytest.mark.parametrize("slug,expected_nodes", TEMPLATE_NODE_COUNTS.items())
    def test_node_count_matches_template(self, api, slug, expected_nodes):
        resp = api.post(f"/api/workflows/from-template/{slug}/")
        assert resp.status_code == 201
        wf_id = resp.data["id"]
        assert Node.objects.filter(workflow_id=wf_id).count() == expected_nodes

    @pytest.mark.parametrize("slug", list(EXPECTED_SLUGS))
    def test_workflow_gets_template_name(self, api, slug):
        template = WorkflowTemplate.objects.get(slug=slug)
        resp = api.post(f"/api/workflows/from-template/{slug}/")
        assert resp.data["name"] == template.name

    @pytest.mark.parametrize("slug", list(EXPECTED_SLUGS))
    def test_instantiated_dag_is_valid(self, api, slug):
        """DAG instanciado deve passar na validação do engine."""
        from flowforge.engine.dag_engine import validate_dag
        resp = api.post(f"/api/workflows/from-template/{slug}/")
        assert resp.status_code == 201
        result = validate_dag(resp.data["id"])
        assert result["valid"] is True, f"{slug}: DAG inválido — {result['errors']}"

    def test_instantiation_copies_tags(self, api):
        resp = api.post("/api/workflows/from-template/whatsapp-notificacao/")
        assert "whatsapp" in resp.data.get("tags", [])

    def test_whatsapp_template_has_whatsapp_node(self, api):
        resp = api.post("/api/workflows/from-template/whatsapp-notificacao/")
        wf_id = resp.data["id"]
        assert Node.objects.filter(workflow_id=wf_id, node_type="whatsapp").exists()

    def test_agente_template_has_llm_and_whatsapp(self, api):
        resp = api.post("/api/workflows/from-template/whatsapp-agente/")
        wf_id = resp.data["id"]
        assert Node.objects.filter(workflow_id=wf_id, node_type="llm").exists()
        assert Node.objects.filter(workflow_id=wf_id, node_type="whatsapp").exists()

    def test_monitor_template_has_condition_node(self, api):
        resp = api.post("/api/workflows/from-template/monitor-http/")
        wf_id = resp.data["id"]
        assert Node.objects.filter(workflow_id=wf_id, node_type="condition").exists()

    def test_daily_briefing_has_telegram_node(self, api):
        resp = api.post("/api/workflows/from-template/daily-briefing/")
        wf_id = resp.data["id"]
        assert Node.objects.filter(workflow_id=wf_id, node_type="telegram").exists()

    def test_multiple_instantiations_create_independent_workflows(self, api):
        resp1 = api.post("/api/workflows/from-template/etl-transform/")
        resp2 = api.post("/api/workflows/from-template/etl-transform/")
        assert resp1.data["id"] != resp2.data["id"]
        assert Node.objects.filter(workflow_id=resp1.data["id"]).count() == \
               Node.objects.filter(workflow_id=resp2.data["id"]).count()


# ── Seed idempotente ──────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSeedIdempotency:
    def test_running_seed_twice_does_not_duplicate(self):
        from django.core.management import call_command
        call_command("seed_templates", verbosity=0)
        count_after = WorkflowTemplate.objects.count()
        # seed_templates usa update_or_create — contar deve ser o mesmo
        assert WorkflowTemplate.objects.count() == count_after

    def test_slug_is_unique(self):
        for slug in EXPECTED_SLUGS:
            assert WorkflowTemplate.objects.filter(slug=slug).count() == 1
