# PROMPT.md — FlowForge (#6)

> Workflow visual no-code com drag-and-drop, DAG engine (Kahn's algorithm) e 8 node types.
> Subdomínio: `flowforge.pizani.ia.br`
> Portas: PG:5432 | Redis:6406 | API:8006 | UI:5106

---

## Contexto do Projeto

FlowForge é um construtor visual de workflows no-code. O usuário monta pipelines
arrastando blocos (nodes) num canvas, conecta com edges, e executa o DAG resultante.
O backend valida a topologia (ciclos, dependências), resolve a ordem de execução via
Kahn's Algorithm, e processa cada node com Celery workers.

**Propósito no portfólio:** demonstrar domínio de algoritmos de grafos (DAG/topological sort),
arquitetura event-driven (Celery), UX interativa avançada (drag-and-drop com React Flow),
e capacidade de construir ferramentas no-code — skill altamente valorizado no mercado.

---

## Stack & Convenções

- **Backend:** Django 5.1 + DRF + Celery + PostgreSQL 16 + Redis 7
- **Frontend:** React 18 + TypeScript + React Flow (@xyflow/react) + Recharts
- **Design System:** Sora + Source Code Pro | Accent: `#a855f7` (violet) | Dark theme
- **Padrões:** docstrings PT-BR, type hints, CLAUDE.md, docker-compose.yml
- **Testes:** pytest (backend) + Vitest (frontend), mínimo 80% coverage nas models/services

---

## Modelo de Dados

```
Workflow
├── id: UUID (pk)
├── name: str (max 100)
├── description: text (optional)
├── owner: FK → User
├── is_active: bool (default True)
├── created_at / updated_at: datetime
└── Meta: unique_together(owner, name)

Node
├── id: UUID (pk)
├── workflow: FK → Workflow (cascade)
├── node_type: str (choices: 8 tipos abaixo)
├── label: str (max 80)
├── config: JSONField (default={}) — parâmetros específicos por tipo
├── position_x: float
├── position_y: float
├── created_at: datetime
└── Meta: index on (workflow, node_type)

Edge
├── id: UUID (pk)
├── workflow: FK → Workflow (cascade)
├── source_node: FK → Node (cascade)
├── target_node: FK → Node (cascade)
├── source_handle: str (default "output")
├── target_handle: str (default "input")
├── created_at: datetime
└── Meta: unique_together(source_node, target_node, source_handle, target_handle)

WorkflowRun
├── id: UUID (pk)
├── workflow: FK → Workflow (cascade)
├── status: str (choices: pending/running/completed/failed/cancelled)
├── started_at / finished_at: datetime (nullable)
├── execution_order: JSONField — lista de UUIDs na ordem topológica
├── error_message: text (nullable)
├── created_at: datetime
└── Meta: ordering = ['-created_at']

NodeExecution
├── id: UUID (pk)
├── run: FK → WorkflowRun (cascade)
├── node: FK → Node (cascade)
├── status: str (choices: pending/running/completed/failed/skipped)
├── input_data: JSONField (default={})
├── output_data: JSONField (default={})
├── started_at / finished_at: datetime (nullable)
├── error_message: text (nullable)
├── duration_ms: int (nullable)
└── Meta: unique_together(run, node), ordering = ['started_at']
```

---

## 8 Node Types

| Tipo | Descrição | Config esperada |
|------|-----------|-----------------|
| `trigger` | Ponto de entrada do workflow (1 por workflow) | `{"mode": "manual" \| "schedule", "cron": "..."}` |
| `http_request` | Faz request HTTP externo | `{"method": "GET\|POST\|PUT\|DELETE", "url": "...", "headers": {}, "body": {}}` |
| `transform` | Transforma dados com JSONPath/template | `{"expression": "...", "template": "..."}` |
| `condition` | Branch condicional (if/else com 2 outputs) | `{"field": "...", "operator": "eq\|neq\|gt\|lt\|contains", "value": "..."}` |
| `delay` | Espera N segundos | `{"seconds": 5}` |
| `llm_call` | Chama LLM (Ollama local) | `{"model": "qwen2.5:3b", "prompt_template": "...", "max_tokens": 500}` |
| `database` | Query SQL (read-only no PostgreSQL) | `{"query": "SELECT ...", "connection": "default"}` |
| `output` | Node final — persiste resultado | `{"format": "json\|text\|table"}` |

---

## Sprints de Desenvolvimento

### Sprint 1 — Foundation (Backend Core + Canvas Básico)
**Objetivo:** CRUD de workflows com canvas drag-and-drop funcional.

**Backend:**
1. Django app `workflows` com models: Workflow, Node, Edge
2. Serializers DRF com validação:
   - Edge não pode apontar pro mesmo node (source ≠ target)
   - Máximo 1 node tipo `trigger` por workflow
3. ViewSets: WorkflowViewSet (CRUD), NodeViewSet (nested under workflow), EdgeViewSet (nested)
4. URL pattern: `/api/v1/workflows/`, `/api/v1/workflows/{id}/nodes/`, `/api/v1/workflows/{id}/edges/`
5. Admin registrado com list_display útil

**Frontend:**
1. Setup React Flow com canvas dark theme (violet accent)
2. Sidebar com os 8 node types arrastáveis (drag from sidebar → drop on canvas)
3. Cada node type tem ícone e cor distinta
4. Conectar nodes com edges (validação: não permitir self-loop no frontend)
5. Salvar posições (position_x, position_y) no backend ao mover nodes
6. Toolbar: salvar workflow, limpar canvas, toggle minimap
7. Auto-save com debounce (2s após última alteração)

**Critério de done:** Criar workflow, arrastar nodes, conectar edges, salvar, recarregar e ver o estado persistido.

---

### Sprint 2 — DAG Engine + Execução
**Objetivo:** Validar topologia e executar workflows com Celery.

**Backend:**
1. Service `dag_engine.py`:
   - `validate_dag(workflow_id)` → detecta ciclos (DFS com cores: white/gray/black)
   - `topological_sort(workflow_id)` → Kahn's Algorithm → retorna lista ordenada de node IDs
   - `find_unreachable_nodes(workflow_id)` → nodes desconectados do trigger
2. Models: WorkflowRun, NodeExecution
3. Celery task `execute_workflow(workflow_id)`:
   - Valida DAG → cria WorkflowRun → executa nodes na ordem topológica
   - Cada node: cria NodeExecution, executa, salva output_data
   - Output de um node vira input do próximo (passagem de dados via edges)
   - Se node falha → marca run como `failed`, registra error_message
4. Node executors (strategy pattern):
   - `BaseNodeExecutor` (abstract) com método `execute(node, input_data) → output_data`
   - Um executor por node_type (8 classes)
   - Registrar no `NODE_EXECUTOR_REGISTRY: dict[str, Type[BaseNodeExecutor]]`
5. API endpoints: `POST /api/v1/workflows/{id}/run/`, `GET /api/v1/workflows/{id}/runs/`
6. Endpoint de validação: `POST /api/v1/workflows/{id}/validate/` → retorna erros de topologia

**Frontend:**
1. Botão "Validate" → chama endpoint, mostra erros inline nos nodes problemáticos
2. Botão "Run" → dispara execução, mostra toast de confirmação
3. Painel lateral "Run History" com lista de execuções (status + duração)

**Critério de done:** Montar workflow com 4+ nodes, validar, executar, ver resultado no run history.

---

### Sprint 3 — Real-time Execution Feedback
**Objetivo:** Visualizar execução em tempo real no canvas.

**Backend:**
1. Django Channels WebSocket consumer: `WorkflowRunConsumer`
   - Room: `workflow_run_{run_id}`
   - Eventos: `node_started`, `node_completed`, `node_failed`, `run_completed`, `run_failed`
   - Payload: `{node_id, status, output_data, duration_ms, error_message}`
2. Celery task atualizada: emite eventos via channel_layer a cada node executado
3. Redis como channel layer (CHANNEL_LAYERS config)

**Frontend:**
1. Conectar WebSocket ao iniciar execução
2. Animação nos nodes durante execução:
   - `pending` → cinza com borda pontilhada
   - `running` → pulse animation com borda violet
   - `completed` → verde com check icon
   - `failed` → vermelho com X icon
3. Edge animation: "flow dots" percorrendo a conexão durante execução
4. Drawer de detalhes ao clicar num NodeExecution: input/output JSON viewer
5. Progress bar geral da run (nodes completados / total)

**Critério de done:** Executar workflow e ver os nodes mudando de status em tempo real no canvas.

---

### Sprint 4 — Node Configuration Panels
**Objetivo:** UI de configuração específica para cada tipo de node.

**Frontend:**
1. Ao clicar/double-click num node → abre painel lateral de configuração
2. Cada node_type tem form específico:
   - **trigger:** toggle manual/schedule + cron input com preview ("Next run: ...")
   - **http_request:** method dropdown + URL input + headers key-value editor + body JSON editor
   - **transform:** expression builder com preview de output
   - **condition:** field selector + operator dropdown + value input + preview das branches
   - **delay:** slider de segundos (1-300) com display
   - **llm_call:** model selector + prompt template textarea com variáveis `{{input.field}}`
   - **database:** SQL editor com syntax highlight (CodeMirror ou similar simples) + dry-run
   - **output:** format selector + preview do output final
3. Validação inline nos forms (campos obrigatórios, URL válida, JSON válido, etc.)
4. Preview mode: mostrar dados mock passando pelo node
5. Salvar config no `config` JSONField via API

**Backend:**
1. Validação de config por node_type no serializer (schema validation)
2. Endpoint dry-run: `POST /api/v1/nodes/{id}/dry-run/` → executa isolado com dados mock

**Critério de done:** Configurar todos os 8 tipos de node com validação, salvar, e usar dry-run.

---

### Sprint 5 — Dashboard + Templates + Polish
**Objetivo:** Dashboard de workflows, templates pré-prontos, e polimento final.

**Backend:**
1. Endpoint de stats: `GET /api/v1/workflows/stats/` → total runs, success rate, avg duration
2. Workflow templates (fixtures):
   - "Data Pipeline" — trigger → http_request → transform → output
   - "Smart Classifier" — trigger → llm_call → condition → output (2 branches)
   - "Scheduled Report" — trigger(schedule) → database → transform → output
3. Endpoint: `POST /api/v1/workflows/from-template/{template_slug}/`

**Frontend:**
1. Dashboard home:
   - Cards de workflows (nome, nodes count, last run status, created_at)
   - Stats cards: total workflows, runs today, success rate
   - Mini chart (Recharts): runs por dia nos últimos 7 dias
2. Template gallery: cards visuais dos 3 templates → click to create
3. Workflow list com search, sort (name, created, last_run), e status filter
4. Empty states com ilustrações e CTAs
5. Responsive: sidebar collapsa em mobile, canvas com pinch-to-zoom
6. Keyboard shortcuts: Ctrl+S (save), Delete (remove selected), Ctrl+Z (undo)
7. Undo/Redo stack (últimas 20 ações no canvas)

**Critério de done:** Dashboard funcional, criar workflow via template, UX polida e responsiva.

---

### Sprint 6 — Testing, Docs & Deploy
**Objetivo:** Cobertura de testes, documentação, e deploy no VPS.

**Backend:**
1. pytest: models, serializers, DAG engine (100% no dag_engine.py), API endpoints
2. Fixtures de teste: workflow válido, workflow com ciclo, workflow desconectado
3. Testar Celery tasks com `CELERY_ALWAYS_EAGER=True`
4. Testar WebSocket consumers com `WebsocketCommunicator`

**Frontend:**
1. Vitest: node executors, DAG validation (frontend mirror), custom hooks
2. Testar React Flow interactions com Testing Library

**Docs & Deploy:**
1. README.md completo: screenshots, setup local, arquitetura, tech decisions
2. CLAUDE.md atualizado com estado final do projeto
3. docker-compose.yml: web, celery_worker, celery_beat, redis, postgres, channels (daphne)
4. Nginx config ou Cloudflare Tunnel apontando para `flowforge.pizani.ia.br:8006`
5. CI: GitHub Actions (lint + test) — mesmo padrão dos outros projetos

**Critério de done:** Testes passando, README com screenshots, rodando em `flowforge.pizani.ia.br`.

---

## Regras de Implementação

1. **Não usar `any` no TypeScript** — tipar tudo, inclusive configs de nodes
2. **JSONField configs validadas no backend** — nunca confiar só no frontend
3. **Celery tasks idempotentes** — re-run seguro sem side-effects duplicados
4. **Logs estruturados** — `structlog` com workflow_id e run_id em todo log
5. **Rate limiting** — max 5 runs simultâneas por usuário
6. **Soft delete em workflows** — `is_active=False`, nunca DELETE real
7. **Edge validation server-side** — source_handle e target_handle devem existir no node_type schema
8. **Nenhum secret hardcoded** — tudo via .env (já coberto pelo .claudeignore + settings.json)
