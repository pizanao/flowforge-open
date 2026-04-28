"""
Handlers de nós do FlowForge.

Cada tipo de nó tem um handler que recebe (node, input_data, run)
e retorna um dicionário com o output.
"""

import json
import logging
import re
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)

_HANDLERS: dict[str, Callable] = {}


def register_handler(node_type: str):
    """Decorator para registrar um handler de nó."""
    def decorator(fn):
        _HANDLERS[node_type] = fn
        return fn
    return decorator


def get_handler(node_type: str) -> Callable:
    """Retorna o handler registrado para o tipo de nó."""
    handler = _HANDLERS.get(node_type)
    if not handler:
        raise ValueError(f"Handler não encontrado para tipo: {node_type}")
    return handler


def _interpolate(template: str, data: dict) -> str:
    """Substitui {{chave}} e {{chave.subcampo}} nos templates."""
    if not isinstance(template, str):
        return str(template)

    def replace(match):
        path = match.group(1).strip()
        parts = path.split(".")
        val = data
        for p in parts:
            if isinstance(val, dict):
                val = val.get(p)
            else:
                return match.group(0)
        return str(val) if val is not None else match.group(0)

    result = re.sub(r"\{\{([^}]+)\}\}", replace, template)
    # Fallback: injeta o dict completo como {{data}}
    if "{{data}}" in result:
        result = result.replace("{{data}}", json.dumps(data, ensure_ascii=False, indent=2))
    return result


@register_handler("trigger")
def handle_trigger(node, input_data: dict, run) -> dict:
    """Ponto de entrada — repassa o payload do run."""
    from django.utils import timezone
    now = timezone.localtime()
    return {
        "payload": input_data.get("trigger", {}),
        "trigger_type": run.trigger_type,
        "timestamp": now.isoformat(),
        "date": now.strftime("%d/%m/%Y"),
        "time": now.strftime("%H:%M"),
        "weekday": ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"][now.weekday()],
    }


@register_handler("http")
def handle_http(node, input_data: dict, run) -> dict:
    """
    Nó HTTP — faz requisição HTTP real via httpx.

    Config:
        method: GET|POST|PUT|PATCH|DELETE
        url: string (suporta {{variavel}})
        headers: dict
        body: dict ou string
        timeout: int (default 30s)
    """
    import httpx

    config = node.config
    method = config.get("method", "GET").upper()
    url = _interpolate(config.get("url", ""), input_data.get("default", input_data))
    headers = config.get("headers", {})
    body = config.get("body")
    timeout = config.get("timeout", 30)

    if not url:
        raise ValueError("URL não configurada no nó HTTP.")

    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            kwargs: dict[str, Any] = {"headers": headers}
            if method in ("POST", "PUT", "PATCH") and body:
                if isinstance(body, dict):
                    kwargs["json"] = body
                else:
                    kwargs["content"] = str(body)
                    kwargs["headers"] = {**headers, "Content-Type": "application/json"}

            response = getattr(client, method.lower())(url, **kwargs)

        try:
            resp_body = response.json()
        except Exception:
            resp_body = response.text

        return {
            "status_code": response.status_code,
            "ok": response.is_success,
            "url": str(response.url),
            "method": method,
            "body": resp_body,
        }
    except httpx.RequestError as e:
        raise RuntimeError(f"Falha na requisição HTTP para {url}: {e}") from e


@register_handler("transform")
def handle_transform(node, input_data: dict, run) -> dict:
    """Manipula dados: pick, rename, merge, map, flatten, passthrough."""
    config = node.config
    operation = config.get("operation", "passthrough")
    params = config.get("params", {})
    data = input_data.get("default", input_data)

    if operation == "pick":
        keys = params.get("keys", [])
        if isinstance(data, dict):
            return {k: data[k] for k in keys if k in data}

    elif operation == "merge":
        result: dict = {}
        for val in input_data.values():
            if isinstance(val, dict):
                result.update(val)
        return result

    elif operation == "rename":
        mapping = params.get("mapping", {})
        if isinstance(data, dict):
            return {mapping.get(k, k): v for k, v in data.items()}

    return data if isinstance(data, dict) else {"data": data}


@register_handler("condition")
def handle_condition(node, input_data: dict, run) -> dict:
    """Avalia condição e retorna branch true/false."""
    config = node.config
    field = config.get("field", "")
    operator = config.get("operator", "eq")
    compare_value = config.get("value", "")

    data = input_data.get("default", input_data)
    actual_value = data.get(field) if isinstance(data, dict) else None

    result = False
    if operator == "eq":
        result = str(actual_value) == str(compare_value)
    elif operator == "neq":
        result = str(actual_value) != str(compare_value)
    elif operator == "gt":
        result = float(actual_value or 0) > float(compare_value)
    elif operator == "lt":
        result = float(actual_value or 0) < float(compare_value)
    elif operator == "gte":
        result = float(actual_value or 0) >= float(compare_value)
    elif operator == "lte":
        result = float(actual_value or 0) <= float(compare_value)
    elif operator == "contains":
        result = str(compare_value) in str(actual_value or "")
    elif operator == "exists":
        result = actual_value is not None

    return {
        "branch": "true" if result else "false",
        "condition": f"{field} {operator} {compare_value}",
        "actual_value": actual_value,
        "result": result,
        "data": data,
    }


@register_handler("llm")
def handle_llm(node, input_data: dict, run) -> dict:
    """
    Nó LLM — chama Ollama com o prompt gerado a partir do template.

    Config:
        model: string (default: qwen2.5:3b)
        prompt_template: string com {{variáveis}}
    """
    import ollama
    from django.conf import settings

    config = node.config
    model = config.get("model") or getattr(settings, "OLLAMA_MODEL", "qwen2.5:3b")
    template = config.get("prompt_template", "Analise os dados: {{data}}")

    flat_data: dict = {}
    for val in input_data.values():
        if isinstance(val, dict):
            flat_data.update(val)
    flat_data.update(input_data)

    prompt = _interpolate(template, flat_data)

    base_url = getattr(settings, "OLLAMA_BASE_URL", "http://host.docker.internal:11434")
    client = ollama.Client(host=base_url)

    logger.info("LLM call → %s @ %s | prompt[:%d]...", model, base_url, 120)

    try:
        response = client.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.7},
        )
    except Exception as e:
        raise RuntimeError(f"Ollama indisponível em {base_url}: {e}") from e

    text = response["message"]["content"]
    return {
        "response": text,
        "model": model,
        "tokens_used": response.get("eval_count", 0),
        "prompt_length": len(prompt),
    }


@register_handler("email")
def handle_email(node, input_data: dict, run) -> dict:
    """Envia email via SMTP (simulado nesta versão)."""
    config = node.config
    to = config.get("to", "user@example.com")
    subject = config.get("subject", "Notificação FlowForge")
    logger.info("Email (simulado) → %s: %s", to, subject)
    return {
        "sent": True,
        "to": to,
        "subject": subject,
        "message_id": f"sim-{run.id.hex[:8]}",
    }


@register_handler("delay")
def handle_delay(node, input_data: dict, run) -> dict:
    """Aguarda N segundos."""
    config = node.config
    seconds = min(config.get("seconds", 1), 300)
    actual_wait = min(seconds, 2)
    time.sleep(actual_wait)
    return {
        "waited_seconds": seconds,
        "actual_wait": actual_wait,
        "data": input_data.get("default", input_data),
    }


@register_handler("output")
def handle_output(node, input_data: dict, run) -> dict:
    """Consolida e retorna dados finais."""
    config = node.config
    data = input_data.get("default", input_data)
    if config.get("format") == "summary":
        return {
            "summary": True,
            "keys": list(data.keys()) if isinstance(data, dict) else [],
            "data": data,
        }
    return data if isinstance(data, dict) else {"result": data}


@register_handler("whatsapp")
def handle_whatsapp(node, input_data: dict, run) -> dict:
    """
    Envia mensagem WhatsApp via Waha API (http://waha.devlike.pro).

    Config:
        phone: número no formato 5511999999999 (sem @c.us)
        text: template da mensagem (suporta {{variavel}})
        session: sessão Waha (default: lido de WAHA_DEFAULT_SESSION)

    Lê WAHA_API_KEY e WAHA_BASE_URL do Django settings.
    """
    import httpx
    from django.conf import settings

    config = node.config
    api_key = getattr(settings, "WAHA_API_KEY", "")
    base_url = getattr(settings, "WAHA_BASE_URL", "http://127.0.0.1:3000")
    default_session = getattr(settings, "WAHA_DEFAULT_SESSION", "default")

    phone = config.get("phone", "")
    session = config.get("session") or default_session

    if not api_key:
        raise ValueError("WAHA_API_KEY não configurado em settings.")
    if not phone:
        raise ValueError("Número de telefone não configurado no nó WhatsApp.")

    chat_id = phone if phone.endswith("@c.us") else f"{phone}@c.us"

    template = config.get("text", "{{response}}")
    flat_data: dict = {}
    for val in input_data.values():
        if isinstance(val, dict):
            flat_data.update(val)
    flat_data.update(input_data)
    text = _interpolate(template, flat_data)

    url = f"{base_url}/api/sendText"
    payload = {"chatId": chat_id, "text": text, "session": session}

    with httpx.Client(timeout=15) as client:
        resp = client.post(url, json=payload, headers={"X-Api-Key": api_key})

    if not resp.is_success:
        raise RuntimeError(f"Waha API erro {resp.status_code}: {resp.text[:200]}")

    result = resp.json()
    msg_id = result.get("id", {}).get("id", "") if isinstance(result.get("id"), dict) else str(result.get("id", ""))
    logger.info("WhatsApp message sent — msg_id=%s phone=%s session=%s", msg_id, phone, session)

    return {
        "sent": True,
        "message_id": msg_id,
        "phone": phone,
        "chat_id": chat_id,
        "session": session,
        "text_length": len(text),
        "preview": text[:100],
    }


@register_handler("telegram")
def handle_telegram(node, input_data: dict, run) -> dict:
    """
    Envia mensagem via Telegram Bot API.

    Config:
        text: template da mensagem (suporta {{variavel}})
        parse_mode: MarkdownV2 | HTML | Markdown (default: Markdown)
        chat_id: sobrescreve o TELEGRAM_CHAT_ID do settings (opcional)

    Lê TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID do Django settings.
    """
    import httpx
    from django.conf import settings

    config = node.config
    bot_token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
    chat_id = config.get("chat_id") or getattr(settings, "TELEGRAM_CHAT_ID", "")
    parse_mode = config.get("parse_mode", "Markdown")

    if not bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN não configurado em settings.")
    if not chat_id:
        raise ValueError("TELEGRAM_CHAT_ID não configurado em settings ou no nó.")

    # Resolve o texto da mensagem
    template = config.get("text", "{{response}}")
    flat_data: dict = {}
    for val in input_data.values():
        if isinstance(val, dict):
            flat_data.update(val)
    flat_data.update(input_data)
    text = _interpolate(template, flat_data)

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode

    with httpx.Client(timeout=15) as client:
        resp = client.post(url, json=payload)

    if not resp.is_success:
        raise RuntimeError(f"Telegram API erro {resp.status_code}: {resp.text[:200]}")

    result = resp.json()
    msg_id = result.get("result", {}).get("message_id")
    logger.info("Telegram message sent — message_id=%s chat_id=%s", msg_id, chat_id)

    return {
        "sent": True,
        "message_id": msg_id,
        "chat_id": chat_id,
        "text_length": len(text),
        "preview": text[:100],
    }
