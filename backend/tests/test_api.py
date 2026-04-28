"""Testes dos endpoints da API REST do FlowForge."""

import pytest

from flowforge.models import Node, Workflow


@pytest.mark.django_db
class TestWorkflowEndpoints:
    def test_list_empty(self, api):
        resp = api.get("/api/workflows/")
        assert resp.status_code == 200
        assert "results" in resp.data or isinstance(resp.data, list)

    def test_create_workflow(self, api):
        resp = api.post("/api/workflows/", {"name": "Novo Workflow"}, format="json")
        assert resp.status_code == 201
        assert resp.data["name"] == "Novo Workflow"

    def test_retrieve_workflow(self, api, workflow):
        resp = api.get(f"/api/workflows/{workflow.id}/")
        assert resp.status_code == 200
        assert resp.data["name"] == "Workflow Teste"

    def test_update_workflow(self, api, workflow):
        resp = api.patch(f"/api/workflows/{workflow.id}/", {"name": "Atualizado"}, format="json")
        assert resp.status_code == 200
        assert resp.data["name"] == "Atualizado"

    def test_delete_workflow(self, api, workflow):
        resp = api.delete(f"/api/workflows/{workflow.id}/")
        assert resp.status_code == 204
        assert not Workflow.objects.filter(id=workflow.id).exists()


@pytest.mark.django_db
class TestAuthenticationRequired:
    def test_workflows_require_authentication(self, anon_api):
        resp = anon_api.get("/api/workflows/")
        assert resp.status_code == 401


@pytest.mark.django_db
class TestValidateEndpoint:
    def test_valid_dag(self, api, workflow, trigger_node, output_node, edge):
        resp = api.post(f"/api/workflows/{workflow.id}/validate/")
        assert resp.status_code == 200
        assert resp.data["valid"] is True
        assert resp.data["errors"] == []

    def test_invalid_dag_no_trigger(self, api, workflow, output_node):
        resp = api.post(f"/api/workflows/{workflow.id}/validate/")
        assert resp.status_code == 200
        assert resp.data["valid"] is False
        assert len(resp.data["errors"]) > 0


@pytest.mark.django_db
class TestStatsEndpoint:
    def test_stats_returns_expected_keys(self, api, workflow, run):
        resp = api.get("/api/workflows/stats/")
        assert resp.status_code == 200
        for key in ("total_workflows", "total_runs", "success_rate", "avg_duration_ms"):
            assert key in resp.data

    def test_stats_with_no_data(self, api):
        resp = api.get("/api/workflows/stats/")
        assert resp.status_code == 200
        assert resp.data["total_workflows"] >= 0
        assert resp.data["success_rate"] == 0


@pytest.mark.django_db
class TestTemplatesEndpoint:
    def test_templates_list(self, api):
        resp = api.get("/api/workflows/templates/")
        assert resp.status_code == 200


@pytest.mark.django_db
class TestSaveGraphEndpoint:
    def test_save_graph(self, api, workflow):
        import uuid
        node_id = str(uuid.uuid4())
        payload = {
            "nodes": [
                {
                    "id": node_id,
                    "node_type": "trigger",
                    "label": "Start",
                    "config": {},
                    "position_x": 100,
                    "position_y": 100,
                }
            ],
            "edges": [],
        }
        resp = api.put(f"/api/workflows/{workflow.id}/save_graph/", payload, format="json")
        assert resp.status_code == 200
        assert Node.objects.filter(workflow=workflow).count() == 1


@pytest.mark.django_db
class TestNodeEndpoints:
    def test_list_nodes(self, api, workflow, trigger_node):
        resp = api.get("/api/nodes/")
        assert resp.status_code == 200

    def test_dry_run_trigger_node(self, api, trigger_node):
        resp = api.post(f"/api/nodes/{trigger_node.id}/dry-run/", {}, format="json")
        assert resp.status_code in (200, 400)
