[//]: # ( [MermaidChart: 0b0a13f5-51ec-4c7d-bcb3-241fd06a70e2]
# CLAUDE.md — FlowForge

## Visão Geral

Plataforma visual no-code para criar e executar workflows automatizados.
Editor de canvas com drag-and-drop + motor de execução baseado em DAG com feedback em tempo real via WebSocket.

## Como Rodar

```bash
source .venv/bin/activate

python backend/manage.py migrate
python backend/manage.py collectstatic --no-input
python backend/manage.py seed_workflows   # dados iniciais

docker compose up -d
# API/WS: http://localhost:8006/api/  ws://localhost:8006/ws/
# UI:     http://localhost:5106/
```

## Arquitetura

```
Portfolio HQ (Auth Gateway) → FlowForge API (Service Token) → Celery (Execução) → Node Handlers → PostgreSQL (Logs)
        ↕ OAuth (GitHub/LinkedIn)          ↕ WebSocket (Django Channels/Daphne)
React Canvas Editor (servido via HQ /forge/) ─── API calls via proxy /api/forge/... ───→ FlowForge Backend
```

### Fluxo de execução:
1. Usuário monta workflow no canvas (drag de nós do palete + desenho de edges)
2. Auto-save com debounce 2s → `PUT /api/workflows/{id}/save_graph/`
3. Ao executar → Celery task → resolve ordem topológica (Kahn's Algorithm)
4. Executor percorre nós na ordem, chama handler de cada tipo
5. A cada mudança de estado: emite evento via `channel_layer` → WebSocket → frontend
6. Canvas atualiza em tempo real: pulse (running) → verde (success) / vermelho (failed)
7. NodeExecution + Run persistidos com input/output/duration

### Tipos de nó e handlers:
- `trigger` — ponto de entrada (recebe payload); suporta manual, webhook, schedule (cron)
- `http` — request HTTP real via `httpx` (GET/POST/PUT/PATCH/DELETE, headers, body, redirects)
- `transform` — pick, merge, rename nos dados
- `condition` — avalia expressão e escolhe branch (true/false)
- `llm` — envia prompt template para Ollama via `ollama.Client.chat()` (modelo configurável)
- `email` — envia email via SMTP (simulado)
- `delay` — aguarda N segundos
- `output` — nó terminal, retorna resultado final
- `telegram` — envia mensagem via Telegram Bot API (`httpx`, lê token/chat_id do settings)

## Convenções de Código

### Backend (Python/Django)
- Type hints em todas as funções públicas
- Docstrings em português com formato Google style
- Imports organizados: stdlib → third-party → local
- Models herdam de TimeStampedModel (created_at, updated_at)
- Serializers: versão List (compacta) e Detail (completa) quando necessário
- Views: usar ViewSets com @action para endpoints customizados
- Tasks Celery: bind=True, max_retries=2, acks_late=True

### Frontend (React)
- Componentes funcionais com hooks
- CSS-in-JS inline (sem CSS modules)
- Design system: var(--bg), var(--surface), var(--border), var(--fg), var(--muted), var(--accent)
- Fonts: Sora (body) + Cascadia Code (code/data)
- Canvas: SVG para conexões + divs posicionadas para nós
- Drag-and-drop: mousedown/mousemove/mouseup nativos (sem biblioteca)

### Geral
- Commits semânticos: feat:, fix:, refactor:, docs:, test:
- Sem comentários óbvios — o código deve ser autoexplicativo

## Testes

Ao escrever testes pytest (arquivos `test_*.py`), **delegar para subagente com `model: "haiku"`** para economizar tokens:

```
Agent({
  subagent_type: "general-purpose",
  model: "haiku",
  description: "Escrever testes pytest para ...",
  prompt: "..."  // inclua: arquivos a ler, convenções do projeto, o que testar
})
```

Use Haiku para: serializers, handlers, models, templates (estrutura repetitiva).
Use Sonnet para: testes de integração complexos (executor, DAG, WebSocket) que exigem análise profunda do codebase.

## Status das Sprints

### ✅ Sprint 1 — Foundation (COMPLETO)
- CRUD Workflow/Node/Edge + Admin Django
- Validações: self-loop em edges, max 1 trigger por workflow
- Canvas interativo: drag do palete ao canvas, desenho de edges, auto-save 2s
- Toolbar: salvar / limpar canvas

### ✅ Sprint 2 — DAG Engine + Execução (COMPLETO)
- WorkflowExecutor com Kahn's Algorithm
- 8 handlers com strategy pattern
- Celery task execute_workflow
- `engine/dag_engine.py` — `validate_dag()` DFS white/gray/black + `find_unreachable_nodes()`
- `POST /api/workflows/{id}/validate/` → `{valid, errors: [{node_id, message}]}`
- `POST /api/workflows/{id}/webhook/` — trigger via HTTP externo
- Frontend: botão "✦ Validar", highlight de nós com erro (borda vermelha + badge "!")

### ✅ Sprint 3 — Real-time Feedback (COMPLETO)
- Django Channels + Daphne
- WorkflowRunConsumer (WebSocket) com snapshot ao conectar
- Animações no canvas em tempo real (pulse/success/failed/pending)
- Edge "flow dots" com animateMotion
- NodeDetailDrawer com JSON de output
- Progress bar de execução

### ✅ Sprint 4 — Node Configuration Panels (COMPLETO)
- `NodeConfigPanels.jsx` — 9 painéis específicos por tipo de nó (inclui Telegram)
- `POST /api/nodes/{id}/dry_run/` — testa nó isolado sem persistir (URL com underscore)
- `validate_node_config()` no serializer — validação por tipo

### ✅ E2E — Playwright (COMPLETO)
- Chrome + Firefox, vídeo on, trace on
- `demo.spec.js` — Luna workflow do zero em ~33s (slowMo 400ms)
- `flowforge.sh demo` — grava .webm para portfólio

### ✅ Sprint 5 — Dashboard + Templates (COMPLETO)
- `GET /api/workflows/stats/` — total_workflows, total_runs, success_rate, avg_duration_ms, node_type_counts
- `WorkflowTemplate` model com slug, nodes_data, edges_data
- `GET /api/workflows/templates/` — galeria (slug, name, description, category, tags)
- `POST /api/workflows/from-template/{slug}/` — instancia template como workflow real
- `python manage.py seed_templates` — 3 templates: luna, monitor-http, etl-simples
- Dashboard: MetricBox row com stats (success_rate, avg_duration), galeria de templates
- Undo/Redo stack (20 ações) via undoStackRef/redoStackRef + botões ↩/↪
- Keyboard shortcuts: Ctrl+S (salvar), Delete (remover nó), Ctrl+Z (desfazer), Ctrl+Y (refazer)

### ✅ Daily Briefing — Telegram + Ollama (COMPLETO E TESTADO)
- Pipeline end-to-end: Trigger (cron 09:00) → HTTP (FlowForge stats) → LLM → Telegram → Output
- Handlers reais: `httpx` para HTTP, `ollama.Client.chat()` para LLM, Telegram Bot API
- `celerybeat` service no docker-compose; `seed_daily_briefing` management command
- Modelo padrão: `llama3.1:8b` (local); OLLAMA_BASE_URL via `host.docker.internal`
- `parse_mode` omitido quando vazio para evitar erro 400 do Telegram

### ✅ Sprint 6 — Testes & Deploy (COMPLETO)
- `backend/tests/` — 76 testes, 57% cobertura (models/serializers/dag_engine/API/tasks: 86–100%)
- `backend/pytest.ini` + `backend/requirements-dev.txt` (pytest-django, pytest-mock, pytest-cov)
- `.github/workflows/ci.yml` — backend (postgres+redis services) + frontend build + E2E (push main)
- `docker-compose.prod.yml` — Postgres + Redis + Backend + Celery + Celerybeat + Frontend + Nginx
- `nginx/nginx.conf` — proxy para API, WebSocket upgrade, static files, gzip
- `frontend/Dockerfile.prod` — multi-stage build (node:20 → serve estático na porta 5106)

### ✅ Melhorias Pós-Sprint 6
- **Fix dry_run URL**: frontend corrigido de `/dry-run/` para `/dry_run/` (DRF usa underscore)
- **Botão "Excluir fluxo"**: confirmação via `window.confirm` → `DELETE` → volta à lista
- **Botão "Salvar como"**: `window.prompt` com nome → `duplicate/` + `PATCH` do nome → volta à lista

### ✅ Controle de Acesso via Portfolio HQ (COMPLETO)
- **Service Token**: `IsServiceAuthenticated` permission class valida header `X-Service-Token` (shared secret)
- **Proxy autenticado no HQ**: `forge_views.py` → proxy genérico catch-all com `IsAuthenticated` + service token
  - `re_path(r"^forge/(?P<path>.*)$", forge_proxy)` — qualquer endpoint do FlowForge via HQ
  - Envia `X-Forwarded-User` e `X-Forwarded-User-Id` nos headers
- **Endpoints protegidos**: todos os ViewSets usam `IsServiceAuthenticated`; webhook permanece `AllowAny`
- **Frontend via HQ**: API base configurável (`VITE_API_BASE`), auth check via `/api/auth/me/`, redirect para login OAuth
- **WebSocket configurável**: `VITE_WS_BASE` para conectar direto ao FlowForge backend
- **Vite base path**: `VITE_BASE_PATH=/forge/` para servir como sub-rota do HQ
- **76 testes** (4 novos: token aceito, token rejeitado, token inválido, webhook público)
- **Env vars**: `PORTFOLIO_HQ_SERVICE_TOKEN` (FlowForge) / `FLOWFORGE_SERVICE_TOKEN` (HQ) — mesmo valor
