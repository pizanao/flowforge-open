"""Testes dos handlers de nós do FlowForge."""

import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import httpx
import pytest
import respx

from flowforge.engine.handlers import (
    _interpolate,
    handle_condition,
    handle_delay,
    handle_email,
    handle_http,
    handle_llm,
    handle_output,
    handle_telegram,
    handle_transform,
    handle_trigger,
    handle_whatsapp,
)


def make_node(config: dict) -> SimpleNamespace:
    return SimpleNamespace(config=config, id=uuid.uuid4())


def make_run(trigger_type: str = "manual") -> SimpleNamespace:
    return SimpleNamespace(id=uuid.uuid4(), trigger_type=trigger_type)


# ── _interpolate ─────────────────────────────────────────────────────────────

class TestInterpolate:
    def test_simple_key(self):
        assert _interpolate("Olá {{nome}}", {"nome": "mundo"}) == "Olá mundo"

    def test_nested_key(self):
        assert _interpolate("{{a.b}}", {"a": {"b": "ok"}}) == "ok"

    def test_missing_key_keeps_placeholder(self):
        result = _interpolate("{{missing}}", {})
        assert result == "{{missing}}"

    def test_data_fallback(self):
        result = _interpolate("{{data}}", {"x": 1})
        assert '"x": 1' in result

    def test_non_string_input(self):
        assert _interpolate(42, {}) == "42"


# ── Trigger ──────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestHandleTrigger:
    def test_returns_payload_and_timestamp(self):
        node = make_node({"trigger_type": "manual"})
        run = make_run("manual")
        result = handle_trigger(node, {"trigger": {"key": "val"}}, run)
        assert result["payload"] == {"key": "val"}
        assert result["trigger_type"] == "manual"
        assert "timestamp" in result
        assert "date" in result
        assert "weekday" in result


# ── HTTP ─────────────────────────────────────────────────────────────────────

class TestHandleHttp:
    @respx.mock
    def test_get_success(self):
        respx.get("https://api.example.com/data").mock(
            return_value=httpx.Response(200, json={"items": [1, 2, 3]})
        )
        node = make_node({"method": "GET", "url": "https://api.example.com/data"})
        result = handle_http(node, {}, make_run())
        assert result["status_code"] == 200
        assert result["ok"] is True
        assert result["body"] == {"items": [1, 2, 3]}
        assert result["method"] == "GET"

    @respx.mock
    def test_post_with_json_body(self):
        respx.post("https://api.example.com/create").mock(
            return_value=httpx.Response(201, json={"id": 99})
        )
        node = make_node({
            "method": "POST",
            "url": "https://api.example.com/create",
            "body": {"name": "test"},
        })
        result = handle_http(node, {}, make_run())
        assert result["status_code"] == 201
        assert result["body"]["id"] == 99

    @respx.mock
    def test_url_interpolation(self):
        respx.get("https://api.example.com/users/42").mock(
            return_value=httpx.Response(200, json={"user": "ok"})
        )
        node = make_node({"method": "GET", "url": "https://api.example.com/users/{{id}}"})
        result = handle_http(node, {"default": {"id": "42"}}, make_run())
        assert result["status_code"] == 200

    def test_missing_url_raises(self):
        node = make_node({"method": "GET", "url": ""})
        with pytest.raises(ValueError, match="URL não configurada"):
            handle_http(node, {}, make_run())

    @respx.mock
    def test_connection_error_raises_runtime(self):
        respx.get("https://unreachable.invalid/").mock(side_effect=httpx.ConnectError("fail"))
        node = make_node({"method": "GET", "url": "https://unreachable.invalid/"})
        with pytest.raises(RuntimeError, match="Falha na requisição"):
            handle_http(node, {}, make_run())


# ── Transform ────────────────────────────────────────────────────────────────

class TestHandleTransform:
    def test_pick(self):
        node = make_node({"operation": "pick", "params": {"keys": ["a", "c"]}})
        result = handle_transform(node, {"default": {"a": 1, "b": 2, "c": 3}}, make_run())
        assert result == {"a": 1, "c": 3}

    def test_merge(self):
        node = make_node({"operation": "merge"})
        result = handle_transform(node, {"x": {"a": 1}, "y": {"b": 2}}, make_run())
        assert result == {"a": 1, "b": 2}

    def test_rename(self):
        node = make_node({"operation": "rename", "params": {"mapping": {"old": "new"}}})
        result = handle_transform(node, {"default": {"old": "value"}}, make_run())
        assert "new" in result
        assert "old" not in result

    def test_passthrough(self):
        node = make_node({"operation": "passthrough"})
        result = handle_transform(node, {"default": {"x": 42}}, make_run())
        assert result == {"x": 42}


# ── Condition ────────────────────────────────────────────────────────────────

class TestHandleCondition:
    def _run(self, field, operator, value, data):
        node = make_node({"field": field, "operator": operator, "value": value})
        return handle_condition(node, {"default": data}, make_run())

    def test_eq_true(self):
        r = self._run("status", "eq", "active", {"status": "active"})
        assert r["branch"] == "true"
        assert r["result"] is True

    def test_eq_false(self):
        r = self._run("status", "eq", "active", {"status": "inactive"})
        assert r["branch"] == "false"

    def test_gt(self):
        r = self._run("score", "gt", "5", {"score": 10})
        assert r["branch"] == "true"

    def test_lt(self):
        r = self._run("score", "lt", "5", {"score": 3})
        assert r["branch"] == "true"

    def test_contains(self):
        r = self._run("text", "contains", "hello", {"text": "say hello world"})
        assert r["branch"] == "true"

    def test_exists_true(self):
        r = self._run("key", "exists", "", {"key": "val"})
        assert r["branch"] == "true"

    def test_exists_false(self):
        r = self._run("missing", "exists", "", {"other": "val"})
        assert r["branch"] == "false"


# ── LLM ──────────────────────────────────────────────────────────────────────

class TestHandleLlm:
    @patch("ollama.Client")
    def test_success(self, mock_client_cls, settings):
        settings.OLLAMA_BASE_URL = "http://127.0.0.1:11434"
        settings.OLLAMA_MODEL = "qwen2.5:3b"

        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.chat.return_value = {
            "message": {"content": "Resposta do LLM"},
            "eval_count": 42,
        }

        node = make_node({"prompt_template": "Analise: {{data}}"})
        result = handle_llm(node, {"default": {"x": 1}}, make_run())

        assert result["response"] == "Resposta do LLM"
        assert result["tokens_used"] == 42
        assert result["model"] == "qwen2.5:3b"

    @patch("ollama.Client")
    def test_connection_error_raises_runtime(self, mock_client_cls, settings):
        settings.OLLAMA_BASE_URL = "http://127.0.0.1:11434"
        settings.OLLAMA_MODEL = "qwen2.5:3b"

        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.chat.side_effect = ConnectionError("refused")

        node = make_node({"prompt_template": "Teste"})
        with pytest.raises(RuntimeError, match="Ollama indisponível"):
            handle_llm(node, {}, make_run())

    @patch("ollama.Client")
    def test_uses_model_from_config(self, mock_client_cls, settings):
        settings.OLLAMA_BASE_URL = "http://127.0.0.1:11434"
        settings.OLLAMA_MODEL = "qwen2.5:3b"

        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.chat.return_value = {"message": {"content": "ok"}, "eval_count": 1}

        node = make_node({"model": "llama3.1:8b", "prompt_template": "Teste"})
        result = handle_llm(node, {}, make_run())
        assert result["model"] == "llama3.1:8b"

        call_kwargs = mock_client.chat.call_args
        assert call_kwargs[1]["model"] == "llama3.1:8b"


# ── Email ────────────────────────────────────────────────────────────────────

class TestHandleEmail:
    def test_simulated_send(self):
        node = make_node({"to": "test@example.com", "subject": "Teste"})
        run = make_run()
        result = handle_email(node, {}, run)
        assert result["sent"] is True
        assert result["to"] == "test@example.com"
        assert "message_id" in result


# ── Delay ────────────────────────────────────────────────────────────────────

class TestHandleDelay:
    @patch("time.sleep")
    def test_waits_and_returns(self, mock_sleep):
        node = make_node({"seconds": 5})
        result = handle_delay(node, {"default": {"x": 1}}, make_run())
        assert result["waited_seconds"] == 5
        mock_sleep.assert_called_once()

    @patch("time.sleep")
    def test_caps_at_2s_actual_wait(self, mock_sleep):
        node = make_node({"seconds": 60})
        result = handle_delay(node, {}, make_run())
        assert result["actual_wait"] == 2


# ── Telegram ─────────────────────────────────────────────────────────────────

class TestHandleTelegram:
    @respx.mock
    def test_send_success(self, settings):
        settings.TELEGRAM_BOT_TOKEN = "123:TEST"
        settings.TELEGRAM_CHAT_ID = "99999"

        respx.post("https://api.telegram.org/bot123:TEST/sendMessage").mock(
            return_value=httpx.Response(200, json={"ok": True, "result": {"message_id": 77}})
        )

        node = make_node({"text": "Olá {{nome}}", "parse_mode": "Markdown"})
        result = handle_telegram(node, {"default": {"nome": "Mundo"}}, make_run())

        assert result["sent"] is True
        assert result["message_id"] == 77
        assert "Olá Mundo" in result["preview"]

    def test_missing_token_raises(self, settings):
        settings.TELEGRAM_BOT_TOKEN = ""
        settings.TELEGRAM_CHAT_ID = "99999"
        node = make_node({"text": "Teste"})
        with pytest.raises(ValueError, match="TELEGRAM_BOT_TOKEN"):
            handle_telegram(node, {}, make_run())

    @respx.mock
    def test_api_error_raises_runtime(self, settings):
        settings.TELEGRAM_BOT_TOKEN = "123:TEST"
        settings.TELEGRAM_CHAT_ID = "99999"

        respx.post("https://api.telegram.org/bot123:TEST/sendMessage").mock(
            return_value=httpx.Response(400, json={"description": "Bad Request"})
        )

        node = make_node({"text": "Erro"})
        with pytest.raises(RuntimeError, match="Telegram API erro 400"):
            handle_telegram(node, {}, make_run())


# ── WhatsApp (Waha) ───────────────────────────────────────────────────────────

class TestHandleWhatsapp:
    @respx.mock
    def test_send_success(self, settings):
        settings.WAHA_API_KEY = "test-key"
        settings.WAHA_BASE_URL = "http://127.0.0.1:3000"
        settings.WAHA_DEFAULT_SESSION = "default"

        respx.post("http://127.0.0.1:3000/api/sendText").mock(
            return_value=httpx.Response(201, json={
                "id": {"id": "3EB0ABC123", "fromMe": True},
                "body": "Olá Mundo",
            })
        )

        node = make_node({
            "phone": "5511999999999",
            "text": "Olá {{nome}}",
            "session": "default",
        })
        result = handle_whatsapp(node, {"default": {"nome": "Mundo"}}, make_run())

        assert result["sent"] is True
        assert result["phone"] == "5511999999999"
        assert result["chat_id"] == "5511999999999@c.us"
        assert "Olá Mundo" in result["preview"]

    def test_missing_phone_raises(self, settings):
        settings.WAHA_API_KEY = "test-key"
        settings.WAHA_BASE_URL = "http://127.0.0.1:3000"
        settings.WAHA_DEFAULT_SESSION = "default"
        node = make_node({"text": "Teste"})
        with pytest.raises(ValueError, match="telefone"):
            handle_whatsapp(node, {}, make_run())

    def test_missing_api_key_raises(self, settings):
        settings.WAHA_API_KEY = ""
        settings.WAHA_BASE_URL = "http://127.0.0.1:3000"
        settings.WAHA_DEFAULT_SESSION = "default"
        node = make_node({"phone": "5511999999999", "text": "Teste"})
        with pytest.raises(ValueError, match="WAHA_API_KEY"):
            handle_whatsapp(node, {}, make_run())

    @respx.mock
    def test_phone_already_has_suffix(self, settings):
        settings.WAHA_API_KEY = "test-key"
        settings.WAHA_BASE_URL = "http://127.0.0.1:3000"
        settings.WAHA_DEFAULT_SESSION = "default"

        respx.post("http://127.0.0.1:3000/api/sendText").mock(
            return_value=httpx.Response(201, json={"id": {"id": "AAA"}, "body": "ok"})
        )

        node = make_node({"phone": "5511999999999@c.us", "text": "Teste"})
        result = handle_whatsapp(node, {}, make_run())
        assert result["chat_id"] == "5511999999999@c.us"

    @respx.mock
    def test_api_error_raises_runtime(self, settings):
        settings.WAHA_API_KEY = "test-key"
        settings.WAHA_BASE_URL = "http://127.0.0.1:3000"
        settings.WAHA_DEFAULT_SESSION = "default"

        respx.post("http://127.0.0.1:3000/api/sendText").mock(
            return_value=httpx.Response(401, json={"message": "Unauthorized"})
        )

        node = make_node({"phone": "5511999999999", "text": "Teste"})
        with pytest.raises(RuntimeError, match="Waha API erro 401"):
            handle_whatsapp(node, {}, make_run())


# ── Output ───────────────────────────────────────────────────────────────────

class TestHandleOutput:
    def test_passthrough(self):
        node = make_node({})
        result = handle_output(node, {"default": {"result": "final"}}, make_run())
        assert result == {"result": "final"}

    def test_summary_format(self):
        node = make_node({"format": "summary"})
        result = handle_output(node, {"default": {"a": 1, "b": 2}}, make_run())
        assert result["summary"] is True
        assert set(result["keys"]) == {"a", "b"}
