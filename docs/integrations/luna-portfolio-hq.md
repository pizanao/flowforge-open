# Integração Luna × FlowForge

**Projeto:** [portfolio-hq](https://github.com/pizanao/portfolio-hq)
**Propósito:** Automatizar fluxos de conversa da Luna (agente de comunicação) via FlowForge como motor de orquestração.

---

## Arquitetura

```
Telegram / WhatsApp (Waha)
        │
        │  POST /api/workflows/{id}/webhook/
        ▼
  FlowForge (Webhook Trigger)
        │
        ▼
  LLM Node  →  Ollama (Luna / llama3.2)
        │
        ▼
  HTTP Node  →  POST /api/sendText  →  Waha
        │
        ▼
  Output Node (log da resposta)
```

---

## Configuração do Workflow no FlowForge

### 1. Trigger — Webhook

| Campo | Valor |
|-------|-------|
| Tipo de disparo | `webhook` |
| URL gerada | `http://localhost:8006/api/workflows/{id}/webhook/` |

O Waha e o bot do Telegram devem configurar o webhook apontando para essa URL.

**Payload esperado:**
```json
{
  "message": "Olá Luna!",
  "from": "5511999999999",
  "chat_id": "5511999999999@c.us",
  "platform": "whatsapp"
}
```

### 2. LLM Node — Luna (Ollama)

| Campo | Valor |
|-------|-------|
| Modelo | `llama3.2` (ou o modelo configurado no Ollama) |
| Prompt template | ver abaixo |

```
Você é Luna, uma assistente especializada em comunicação clara e empática.

Mensagem recebida: {{data.message}}
De: {{data.from}}
Plataforma: {{data.platform}}

Responda de forma natural, direta e no mesmo idioma da mensagem.
```

### 3. HTTP Node — Envio via Waha

| Campo | Valor |
|-------|-------|
| Método | `POST` |
| URL | `http://localhost:3000/api/sendText` |
| Body | `{"chatId": "{{trigger.chat_id}}", "text": "{{llm.response}}", "session": "default"}` |

---

## Como testar o fluxo completo

```bash
# 1. Sobe o FlowForge
./flowforge.sh start

# 2. Roda a demo que cria o workflow automaticamente
./flowforge.sh demo

# 3. Dispara o webhook manualmente
curl -X POST http://localhost:8006/api/workflows/{id}/webhook/ \
  -H "Content-Type: application/json" \
  -d '{"message": "Olá Luna!", "from": "5511999999999", "chat_id": "5511999999999@c.us"}'

# 4. Acompanha a execução em tempo real no canvas
# → Abra http://localhost:5106/ e clique no workflow criado
```

---

## Variáveis de ambiente (`.demo.env`)

```bash
DEMO_WORKFLOW_NAME="Luna — Agente de Comunicação"
DEMO_OLLAMA_URL="http://localhost:11434"
DEMO_LUNA_MODEL="llama3.2"
DEMO_WAHA_URL="http://localhost:3000"
DEMO_WAHA_SESSION="default"
```

Configure via `./flowforge.sh demo` (pergunta na primeira execução) ou edite `.demo.env` manualmente.

---

## Referências

- FlowForge: `http://localhost:5106`
- API FlowForge: `http://localhost:8006/api/`
- Waha (fork): `https://github.com/pizanao/portfolio-hq`
- Ollama: `http://localhost:11434`
