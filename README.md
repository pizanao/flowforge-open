<div align="center">

    ███████╗██╗      ██████╗ ██╗    ██╗███████╗ ██████╗ ██████╗  ██████╗ ███████╗
    ██╔════╝██║     ██╔═══██╗██║    ██║██╔════╝██╔═══██╗██╔══██╗██╔════╝ ██╔════╝
    █████╗  ██║     ██║   ██║██║ █╗ ██║█████╗  ██║   ██║██████╔╝██║  ███╗█████╗
    ██╔══╝  ██║     ██║   ██║██║███╗██║██╔══╝  ██║   ██║██╔══██╗██║   ██║██╔══╝
    ██║     ███████╗╚██████╔╝╚███╔███╔╝██║     ╚██████╔╝██║  ██║╚██████╔╝███████╗
    ╚═╝     ╚══════╝ ╚═════╝  ╚══╝╚══╝ ╚═╝      ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝                   

**Visual workflow builder · Real-time execution via WebSocket · LLM-powered agents**

[![Django](https://img.shields.io/badge/Django-5.x-0C4B33?style=flat-square&logo=django)](https://djangoproject.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react)](https://react.dev)
[![Celery](https://img.shields.io/badge/Celery-async-37814A?style=flat-square)](https://docs.celeryq.dev)
[![WebSocket](https://img.shields.io/badge/WebSocket-Channels-5865F2?style=flat-square)](https://channels.readthedocs.io)
[![Playwright](https://img.shields.io/badge/E2E-Playwright-45BA4B?style=flat-square&logo=playwright)](https://playwright.dev)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker)](https://docs.docker.com/compose)

</div>

---

## Demo

![FlowForge demo — Luna workflow from scratch](docs/assets/demo.gif)

> *Creating a Webhook → LLM (Luna/Ollama) → HTTP → Output pipeline from scratch, configuring each node, and executing with real-time WebSocket feedback — recorded at 2× speed.*

---

## What is FlowForge?

FlowForge is a full-stack automation platform where you build workflows visually — drag nodes onto a canvas, wire them together, and watch them execute in real time with WebSocket-driven animations.

Every node type has a dedicated configuration panel. Every run is logged with per-node input/output and duration. Every execution step pushes state to the canvas live.

Think **n8n meets a custom Python backend** — built from scratch to demonstrate full-stack engineering depth.

---

## Architecture

```mermaid
flowchart TB
    subgraph Browser["Browser"]
        Canvas["React Canvas\ndrag & drop · SVG edges · auto-save"]
        WsClient["WebSocket client\nuseWorkflowRun hook"]
    end

    subgraph Server["Django — Daphne / ASGI"]
        API["REST API\nDjango REST Framework\n\n/execute/ · /validate/ · /webhook/\n/stats/ · /templates/ · /dry-run/"]
        Consumer["WorkflowRunConsumer\nDjango Channels"]
    end

    subgraph Workers["Celery Worker"]
        Executor["WorkflowExecutor\nKahn's Algorithm\n→ topological order\n→ 8 node handlers"]
    end

    Redis[("Redis\nchannel layer\n+ broker")]
    DB[("PostgreSQL\nWorkflow · Node · Edge\nRun · NodeExecution")]

    Canvas -->|"PUT /save_graph/\nPOST /execute/"| API
    WsClient <-->|"ws:// live state"| Consumer
    API -->|"task.delay()"| Redis
    Consumer <-->|"group_send / receive"| Redis
    Redis --> Workers
    Workers --> DB
    API --> DB
```

---

## Execution Flow

```mermaid
sequenceDiagram
    actor User
    participant Canvas as React Canvas
    participant API as Django API
    participant Celery as Celery Worker
    participant WS as WebSocket Consumer

    User->>Canvas: Click ▶ Execute
    Canvas->>API: POST /api/workflows/{id}/execute/
    API->>Celery: execute_workflow.delay(run_id)
    API-->>Canvas: 202 {run_id, status: "started"}
    Canvas->>WS: connect ws://.../run/{run_id}/
    WS-->>Canvas: snapshot — all nodes pending

    loop Each node in topological order
        Celery->>WS: group_send {node_id: running}
        WS-->>Canvas: pulse violet animation
        Note over Celery: handler(node, input_data)
        Celery->>WS: group_send {node_id: success | failed}
        WS-->>Canvas: green ✓ or red ✕
    end

    Celery->>WS: run complete {status: success}
    WS-->>Canvas: final state · run_history refreshes
```

---

## Node State Machine

```mermaid
stateDiagram-v2
    direction LR
    [*] --> pending : workflow starts
    pending --> running : executor reaches node
    running --> success : handler returns output
    running --> failed : handler raises exception
    running --> skipped : condition branch not taken
    success --> [*]
    failed --> [*]
    skipped --> [*]
```

---

## Screenshots


<table>
<tr>
<td width="50%">

**Dashboard & Template Gallery**

![Dashboard](docs/assets/screenshot-dashboard.png)

</td>
<td width="50%">

**Canvas Editor**

![Canvas](docs/assets/screenshot-canvas.png)

</td>
</tr>
<tr>
<td width="50%">

**Node Configuration Panel (LLM)**

![Config](docs/assets/screenshot-config.png)

</td>
<td width="50%">

**Real-time Execution Feedback**

![Execution](docs/assets/screenshot-execution.png)

</td>
</tr>
</table>
---

## Node Types


| Icon | Type        | Function                  | Key Config                                            |
| ---- | ----------- | ------------------------- | ----------------------------------------------------- |
| ⚡   | `trigger`   | Workflow entry point      | `trigger_type`: manual \| webhook \| schedule (cron)  |
| 🌐   | `http`      | Real HTTP request (httpx) | method, url, headers (key-value editor), body         |
| ⚙️ | `transform` | Data manipulation         | operation: pick\| rename \| merge \| map \| flatten   |
| 🔀   | `condition` | If/else branch            | field, operator (8 ops), value →`true`/`false` edges |
| 🤖   | `llm`       | LLM via Ollama (real)     | model, prompt_template (with`{{data}}` interpolation) |
| 📧   | `email`     | SMTP email                | to, subject, body_template                            |
| ⏱️ | `delay`     | Pause execution           | seconds (slider 1–60 + numeric input)                |
| 📤   | `output`    | Terminal node             | format: raw\| summary                                 |
| ✈️ | `telegram`  | Telegram Bot message      | text template, parse_mode, optional chat_id override  |

Each node has a **configuration panel** with form validation and a **dry-run** button to test it in isolation — without touching the database or starting a full run.

---

## Template Gallery

Three production-ready templates, available from the dashboard:

```mermaid
flowchart LR
    subgraph Luna["🤖 Luna — Communication Agent"]
        L1([Webhook]) --> L2([LLM / Ollama]) --> L3([HTTP POST]) --> L4([Output])
    end

    subgraph Monitor["📡 HTTP Monitor"]
        M1([Schedule]) --> M2([HTTP GET]) --> M3{Condition}
        M3 -->|OK| M4([Output])
        M3 -->|Fail| M5([Email Alert])
    end

    subgraph ETL["🗄️ Simple ETL"]
        E1([Manual]) --> E2([HTTP Fetch]) --> E3([Transform]) --> E4([HTTP POST]) --> E5([Output])
    end
```

Click **"Usar template →"** on the dashboard to instantiate any template as a new editable workflow.

---

## Canvas Features


| Feature                | Detail                                                                   |
| ---------------------- |--------------------------------------------------------------------------|
| Drag & drop            | Palette items → canvas at exact drop position                            |
| Edge drawing           | Drag right handle (•) from source to target node                         |
| Auto-save              | Debounce 2s after every canvas mutation                                  |
| Validation             | DAG check: cycle detection (DFS white/gray/black) + unreachable nodes    |
| **Undo / Redo**        | 20-level history stack · ↩ ↪ buttons ·`Ctrl+Z` / `Ctrl+Y`                |
| **Keyboard shortcuts** | `Ctrl+S` save · `Delete` remove selected · `Ctrl+Z` undo · `Ctrl+Y` redo |
| Node errors            | Red border +`!` badge with message on hover                              |
| Execution state        | Violet pulse → green ✓ / red ✕ (all via WebSocket)                       |
| Flow dots              | SVG`animateMotion` dots travel along active edges                        |
| Progress bar           | Live`completed/total` counter during execution                           |
| Dry-run                | Test any node in isolation with custom input data                        |
| **Save as**            | Clone workflow with a new name via prompt                                |
| **Delete workflow**    | Permanently delete with confirmation dialog                              |

---

## Quick Start

```bash
git clone <repo> && cd flowforge
./flowforge.sh start          # Docker Compose up + health checks for backend + frontend

# Seed demo data
docker compose exec backend python manage.py seed_workflows        # 3 demo workflows
docker compose exec backend python manage.py seed_templates        # 3 gallery templates
docker compose exec backend python manage.py seed_daily_briefing   # Daily Briefing + cron 09:00 BRT

# Services:
#   UI:        http://localhost:5106
#   API:       http://localhost:8006/api/
#   Admin:     http://localhost:8006/admin/
#   WebSocket: ws://localhost:8006/ws/
```

### Trigger a workflow externally (no browser needed)

```bash
curl -X POST http://localhost:8006/api/workflows/{id}/webhook/ \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello!", "from": "5511999999999"}'
# → {"run_id": "...", "status": "execução iniciada"}
```

---

## API Reference

```
# Workflows
GET    /api/workflows/                          List all workflows
POST   /api/workflows/                          Create workflow
GET    /api/workflows/stats/                    {total_runs, success_rate, avg_duration_ms, node_type_counts}
GET    /api/workflows/templates/                Template gallery
POST   /api/workflows/from-template/{slug}/    Instantiate template as workflow
PUT    /api/workflows/{id}/save_graph/          Atomic save (nodes + edges)
POST   /api/workflows/{id}/execute/             Execute via Celery
POST   /api/workflows/{id}/validate/            {valid, errors: [{node_id, message}]}
POST   /api/workflows/{id}/webhook/             External HTTP trigger
POST   /api/workflows/{id}/duplicate/           Clone with all nodes + edges

# Nodes
GET    /api/nodes/{id}/
POST   /api/nodes/{id}/dry_run/                {output_data, error, duration_ms}

# Runs
GET    /api/runs/?workflow={id}                 List runs
GET    /api/runs/{id}/                          Full detail with per-node executions
POST   /api/runs/{id}/cancel/                   Cancel in-flight run

# WebSocket
WS     /ws/workflow/{id}/run/{run_id}/          Live execution stream (replays snapshot on connect)
```

---

## Tech Stack


| Layer       | Technology                          | Role                                              |
| ----------- | ----------------------------------- | ------------------------------------------------- |
| Backend     | Django 5.x + Django REST Framework  | ORM, serializers, ViewSets, validation            |
| Async tasks | Celery + Redis                      | Decoupled execution, retry logic                  |
| Real-time   | Django Channels + Daphne (ASGI)     | WebSocket — zero polling                         |
| Database    | PostgreSQL                          | JSONB for node config, run output                 |
| LLM         | Ollama (local)                      | Self-hosted models — no API key needed           |
| Frontend    | React 18                            | Functional components, hooks, no framework        |
| Charts      | Recharts                            | SVG-based stats charts                            |
| Styling     | CSS-in-JS inline                    | Zero build config, design tokens via`var(--*)`    |
| Unit tests  | pytest + pytest-django              | 72 tests, 57% coverage — models/API/engine/tasks |
| E2E tests   | Playwright (Chrome + Firefox)       | Video recording, trace viewer                     |
| Containers  | Docker Compose (dev) + Nginx (prod) | One-command local stack · prod-ready config      |

---

## E2E Tests & Demo Recording

```bash
./flowforge.sh test          # Headed — Chrome + Firefox (watch live)
./flowforge.sh test:ci       # Headless (CI/CD)
./flowforge.sh demo          # Records Luna workflow → test-results/*/video.webm
./flowforge.sh trace         # Opens Playwright Trace Viewer
./flowforge.sh report        # Opens HTML test report
./flowforge.sh codegen       # Record new tests by interacting with the browser
./flowforge.sh ui            # Playwright UI Mode (interactive)
```

The demo spec (`e2e/demo.spec.js`) creates a complete 4-node workflow from scratch, configures each node via its panel, validates the DAG, executes, and captures the full run history — all in ~34 seconds of real time.

---

## Project Structure

```
flowforge/
├── backend/
│   ├── config/                   # Django settings, ASGI, URLs
│   └── flowforge/
│       ├── models.py             # Workflow, Node, Edge, Run, NodeExecution, WorkflowTemplate
│       ├── engine/
│       │   ├── dag_engine.py     # validate_dag() — DFS cycle detection + unreachable nodes
│       │   ├── executor.py       # WorkflowExecutor — Kahn's Algorithm
│       │   └── handlers.py       # 9 node handlers (strategy pattern) — http/llm/telegram are real
│       ├── api/
│       │   ├── serializers.py    # validate_node_config() per node type
│       │   └── views.py          # ViewSets + @actions (execute, validate, stats, templates...)
│       ├── consumers.py          # WorkflowRunConsumer (WebSocket + snapshot replay)
│       ├── tasks.py              # execute_workflow + trigger_daily_briefing Celery tasks
│       └── management/commands/
│           ├── seed_workflows.py
│           ├── seed_templates.py
│           └── seed_daily_briefing.py  # Daily Briefing workflow + CeleryBeat PeriodicTask
├── frontend/
│   └── src/
│       ├── App.jsx               # Canvas editor + all views
│       ├── components/
│       │   ├── NodeConfigPanels.jsx    # 9 config panels (one per node type, incl. Telegram)
│       │   └── NodeDetailDrawer.jsx   # Configure / Execution tabs + inline dry-run
│       ├── hooks/
│       │   ├── useApi.js               # Generic fetch hook with loading/error state
│       │   └── useWorkflowRun.js       # WebSocket + execution state machine
│       └── utils/formatters.js         # NODE_TYPES, RUN_STATUS, WORKFLOW_STATUS
│   └── e2e/
│       ├── demo.spec.js                # Portfolio demo — full Luna workflow
│       ├── 01-workflow-list.spec.js
│       ├── 02-create-workflow.spec.js
│       ├── 03-canvas-nodes.spec.js
│       └── 04-execute-workflow.spec.js
├── backend/
│   ├── tests/
│   │   ├── conftest.py               # Shared fixtures (workflow, workflow_with_nodes, template)
│   │   ├── test_models.py            # 17 tests — Workflow, Node, Edge, Run, WorkflowTemplate
│   │   ├── test_dag_engine.py        # 11 tests — cycle detection, unreachable nodes
│   │   ├── test_serializers.py       # 17 tests — validate_node_config, NodeSerializer, EdgeSerializer
│   │   ├── test_api.py               # 23 tests — all REST endpoints + dry_run + cancel
│   │   └── test_tasks.py             #  4 tests — execute_workflow, trigger_daily_briefing
│   ├── pytest.ini                    # DJANGO_SETTINGS_MODULE + asyncio_mode
│   └── requirements-dev.txt          # pytest-django, pytest-mock, pytest-cov, pytest-asyncio
├── nginx/nginx.conf              # Reverse proxy: API + WebSocket upgrade + static files
├── docs/assets/                  # Screenshots + demo GIF
├── flowforge.sh                  # Stack control + demo recording
├── docker-compose.yml            # Development stack
└── docker-compose.prod.yml       # Production: + Postgres + Nginx + healthchecks
```

---

## Design System

```
Colors
  --bg:       #09090f    page background
  --surface:  #111119    card / panel background
  --surface2: #1a1a26    elevated elements
  --border:   #26263a    borders and dividers
  --fg:       #e6e6f0    primary text
  --muted:    #7878a0    secondary text
  --accent:   #a855f7    violet — primary action / running state
  --success:  #10b981    green — success state
  --warning:  #fbbf24    yellow — warnings / avg duration metric
  --danger:   #ef4444    red — failed state / validation errors
  --info:     #3b82f6    blue — informational metrics

Typography
  body:  Sora (system-ui fallback)
  code:  Cascadia Code → Fira Code → SF Mono → monospace
```

---

## Sprint History

```mermaid
timeline
    title FlowForge — Build History
    Sprint 1 : CRUD Workflow/Node/Edge
             : Django Admin
             : Canvas drag & drop
             : Auto-save (debounce 2s)
    Sprint 2 : DAG validation (DFS cycle detection)
             : POST /validate/ · POST /webhook/
             : Error badges on canvas nodes
    Sprint 3 : Django Channels + Daphne
             : WebSocket real-time state
             : Pulse animations · Flow dots
             : Progress bar
    Sprint 4 : 8 node config panels
             : POST /dry-run/ per node
             : validate_node_config() in serializer
    E2E      : Playwright Chrome + Firefox
             : Video recording demo
             : flowforge.sh full control
    Sprint 5 : GET /stats/ dashboard
             : Template gallery (3 templates)
             : Undo/Redo 20-level stack
             : Keyboard shortcuts
    Daily Briefing : Telegram Bot integration
                   : Real httpx + Ollama handlers
                   : Celery Beat 09:00 BRT cron
                   : seed_daily_briefing command
    Sprint 6 : 72 pytest tests (57% coverage)
             : GitHub Actions CI pipeline
             : docker-compose.prod + Nginx
             : Delete workflow (with confirm)
             : Save as (clone with new name)
```

---

<div align="center">

Built with Python + React &nbsp;·&nbsp; Dark mode only &nbsp;·&nbsp; No magic — just code

</div>
