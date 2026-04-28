#!/usr/bin/env bash
# ┌─────────────────────────────────────────────────────────────┐
# │  flowforge.sh — controle de execução e gravação do FlowForge │
# └─────────────────────────────────────────────────────────────┘
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
DEMO_CONFIG="$SCRIPT_DIR/.demo.env"
HQ_DIR="$(cd "$SCRIPT_DIR/../portfolio-hq" 2>/dev/null && pwd || echo "")"
HQ_API_URL="${HQ_API_URL:-http://localhost:8000}"

# ── Cores ──────────────────────────────────────────────────────
BOLD='\033[1m'
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
MUTED='\033[0;90m'
NC='\033[0m'

# ── Helpers ────────────────────────────────────────────────────
log()     { echo -e "${BOLD}${BLUE}▶${NC} $*"; }
ok()      { echo -e "${GREEN}✓${NC} $*"; }
warn()    { echo -e "${YELLOW}⚠${NC} $*"; }
err()     { echo -e "${RED}✕${NC} $*" >&2; }
section() { echo -e "\n${BOLD}${PURPLE}── $* ──${NC}"; }

wait_for() {
  local url="$1" label="$2" timeout="${3:-60}"
  local i=0
  printf "${MUTED}  aguardando %s" "$label"
  while ! curl -sf "$url" > /dev/null 2>&1; do
    sleep 1
    printf "."
    i=$((i + 1))
    if [[ $i -ge $timeout ]]; then
      echo -e "${NC}"
      err "$label não respondeu em ${timeout}s"
      return 1
    fi
  done
  echo -e " ${GREEN}pronto${NC}"
}

load_hq_token() {
  # Já definido via env? Usa direto.
  if [[ -n "${HQ_API_TOKEN:-}" ]]; then
    return 0
  fi

  # Tenta carregar do .env do Portfolio HQ
  local hq_env="${HQ_DIR}/.env"
  if [[ -f "$hq_env" ]]; then
    HQ_API_TOKEN=$(grep -E '^HQ_API_TOKEN=' "$hq_env" | cut -d= -f2- | tr -d '"' || true)
    if [[ -n "$HQ_API_TOKEN" ]]; then
      export HQ_API_TOKEN
      ok "Token HQ carregado de portfolio-hq/.env"
      return 0
    fi
  fi

  warn "HQ_API_TOKEN não encontrado."
  warn "Defina em portfolio-hq/.env ou exporte: export HQ_API_TOKEN=<token>"
  return 1
}

check_hq_proxy() {
  local url="${HQ_API_URL}/api/forge/workflows/"
  printf "${MUTED}  verificando proxy HQ"
  local http_code
  http_code=$(curl -sf -o /dev/null -w "%{http_code}" \
    -H "X-HQ-Token: ${HQ_API_TOKEN}" \
    "$url" 2>/dev/null || echo "000")

  if [[ "$http_code" == "200" ]]; then
    echo -e " ${GREEN}✓ autenticado (HTTP $http_code)${NC}"
    return 0
  elif [[ "$http_code" == "401" ]]; then
    echo -e " ${RED}✕ token inválido (HTTP 401)${NC}"
    return 1
  elif [[ "$http_code" == "000" || "$http_code" == "503" ]]; then
    echo -e " ${YELLOW}⚠ HQ offline (HTTP $http_code) — demo usará FlowForge direto${NC}"
    return 0
  else
    echo -e " ${YELLOW}⚠ resposta inesperada (HTTP $http_code)${NC}"
    return 0
  fi
}

# ── Comandos ───────────────────────────────────────────────────

cmd_start() {
  section "Iniciando FlowForge"
  cd "$SCRIPT_DIR"

  log "Subindo containers Docker..."
  docker compose up -d

  log "Aguardando serviços ficarem prontos..."
  wait_for "http://localhost:8006/api/workflows/" "backend (porta 8006)"
  wait_for "http://localhost:5106/"               "frontend (porta 5106)"

  ok "FlowForge está no ar!"
  echo -e "  ${CYAN}API:${NC}      http://localhost:8006/api/"
  echo -e "  ${CYAN}UI:${NC}       http://localhost:5106/"
  echo -e "  ${CYAN}WebSocket:${NC} ws://localhost:8006/ws/"
}

cmd_stop() {
  section "Parando FlowForge"
  cd "$SCRIPT_DIR"
  docker compose down
  ok "Todos os containers parados."
}

cmd_restart() {
  cmd_stop
  cmd_start
}

cmd_status() {
  section "Status dos serviços"
  cd "$SCRIPT_DIR"
  docker compose ps
}

cmd_logs() {
  section "Logs (Ctrl+C para sair)"
  cd "$SCRIPT_DIR"
  docker compose logs -f "${@:-}"
}

cmd_test() {
  section "E2E Tests — Browser visível (headed)"

  # Carrega token se disponível (não bloqueia se ausente)
  load_hq_token 2>/dev/null && export HQ_API_TOKEN HQ_API_URL || true

  cd "$FRONTEND_DIR"

  local filter="${1:-}"
  if [[ -n "$filter" ]]; then
    log "Rodando testes com filtro: $filter"
    npx playwright test --headed --project=chrome "$filter"
  else
    log "Rodando todos os testes (Chrome + Firefox)..."
    npx playwright test --headed
  fi
}

cmd_test_headless() {
  section "E2E Tests — Headless (CI)"

  load_hq_token 2>/dev/null && export HQ_API_TOKEN HQ_API_URL || true

  cd "$FRONTEND_DIR"
  log "Rodando testes headless..."
  npx playwright test
  ok "Relatório: frontend/playwright-report/index.html"
}

prompt_with_default() {
  local label="$1" default="$2" varname="$3"
  echo -ne "  ${CYAN}${label}${NC} ${MUTED}[${default}]${NC}: "
  read -r input
  if [[ -z "$input" ]]; then
    eval "$varname=\"$default\""
  else
    eval "$varname=\"$input\""
  fi
}

setup_demo_config() {
  section "Configuração do Demo — Luna Workflow"
  echo -e "  ${MUTED}Pressione Enter para aceitar o valor padrão.${NC}\n"

  local name ollama_url model prompt waha_url waha_session

  prompt_with_default "Nome do workflow"          "Luna — Agente de Comunicação"    name
  prompt_with_default "URL do Ollama (Luna)"      "http://localhost:11434"           ollama_url
  prompt_with_default "Modelo da Luna"            "llama3.2"                        model
  prompt_with_default "URL do Waha/Telegram API"  "http://localhost:3000"           waha_url
  prompt_with_default "Sessão Waha"               "default"                         waha_session

  echo -ne "  ${CYAN}Prompt da Luna${NC} ${MUTED}[padrão]${NC}: "
  read -r prompt_input
  if [[ -z "$prompt_input" ]]; then
    prompt="Você é Luna, assistente especializada em comunicação.\n\nMensagem: {{data.message}}\nDe: {{data.from}}\n\nResponda de forma clara e empática."
  else
    prompt="$prompt_input"
  fi

  cat > "$DEMO_CONFIG" <<EOF
# FlowForge Demo Config — gerado em $(date)
DEMO_WORKFLOW_NAME="$name"
DEMO_OLLAMA_URL="$ollama_url"
DEMO_LUNA_MODEL="$model"
DEMO_LUNA_PROMPT="$prompt"
DEMO_WAHA_URL="$waha_url"
DEMO_WAHA_SESSION="$waha_session"
EOF

  ok "Config salva em .demo.env"
  echo
}

cmd_demo() {
  section "Demo Recording — Gravação de portfólio"

  # First-run: solicita parâmetros se config não existir
  if [[ ! -f "$DEMO_CONFIG" ]]; then
    warn "Primeira execução — configurando parâmetros do demo Luna."
    setup_demo_config
  else
    log "Usando config: .demo.env"
    echo -e "  ${MUTED}(apague .demo.env para reconfigurar)${NC}"
    echo
  fi

  # Carrega config como variáveis de ambiente
  set -a
  # shellcheck source=/dev/null
  source "$DEMO_CONFIG"
  set +a

  # Autenticação via HQ API Token
  section "Autenticação Portfolio HQ"
  if load_hq_token; then
    check_hq_proxy
    export HQ_API_TOKEN
    export HQ_API_URL
  else
    warn "Continuando sem autenticação HQ — demo acessará FlowForge direto."
  fi

  cd "$FRONTEND_DIR"
  mkdir -p test-results/screenshots

  log "Iniciando gravação em Chrome (slowMo: 700ms)..."
  log "Workflow: ${DEMO_WORKFLOW_NAME:-Luna — Agente de Comunicação}"
  if [[ -n "${HQ_API_TOKEN:-}" ]]; then
    echo -e "  ${GREEN}✓${NC} HQ Token: ${MUTED}${HQ_API_TOKEN:0:12}…${NC}"
  fi
  echo

  npx playwright test e2e/demo.spec.js \
    --headed \
    --project=chrome

  echo
  ok "Gravação concluída!"
  echo -e "  ${CYAN}Vídeo:${NC}       frontend/test-results/demo-Demo-*/video.webm"
  echo -e "  ${CYAN}Screenshots:${NC} frontend/test-results/screenshots/"
  echo -e "  ${CYAN}Trace:${NC}       ./flowforge.sh trace"

  if command -v xdg-open &> /dev/null; then
    xdg-open "$FRONTEND_DIR/test-results/" 2>/dev/null || true
  fi
}

cmd_codegen() {
  section "Playwright Codegen — Gravação interativa de testes"
  cd "$FRONTEND_DIR"

  warn "O browser vai abrir em modo de gravação."
  warn "Interaja com o FlowForge e os passos serão convertidos em código de teste."
  echo

  local output="${1:-e2e/recorded.spec.js}"
  log "Saída: $output"
  echo

  npx playwright codegen \
    --output "$output" \
    "http://localhost:5106"

  ok "Teste gravado em: $output"
}

cmd_trace() {
  section "Playwright Trace Viewer"
  cd "$FRONTEND_DIR"

  local trace_file="${1:-}"
  if [[ -z "$trace_file" ]]; then
    # Encontra o trace mais recente
    trace_file=$(find test-results -name "trace.zip" -newer playwright.config.js 2>/dev/null | head -1 || true)
  fi

  if [[ -z "$trace_file" ]]; then
    warn "Nenhum trace encontrado. Rode os testes primeiro com:"
    echo -e "    ${CYAN}./flowforge.sh test${NC}"
    exit 1
  fi

  log "Abrindo trace: $trace_file"
  npx playwright show-trace "$trace_file"
}

cmd_report() {
  section "Abrindo relatório HTML"
  cd "$FRONTEND_DIR"
  npx playwright show-report playwright-report
}

cmd_ui() {
  section "Playwright UI Mode"
  cd "$FRONTEND_DIR"
  log "Abrindo interface visual do Playwright..."
  npx playwright test --ui
}

# ── Help ───────────────────────────────────────────────────────

usage() {
  echo -e "
${BOLD}flowforge.sh${NC} — controle de execução e gravação do FlowForge

${BOLD}USO:${NC}
  ./flowforge.sh <comando> [opções]

${BOLD}STACK:${NC}
  ${CYAN}start${NC}              Sobe os containers Docker e aguarda serviços
  ${CYAN}stop${NC}               Para todos os containers
  ${CYAN}restart${NC}            Para e sobe novamente
  ${CYAN}status${NC}             Status dos containers
  ${CYAN}logs [serviço]${NC}     Tail dos logs (backend, frontend, celery, redis)

${BOLD}TESTES (browser visível):${NC}
  ${CYAN}test [filtro]${NC}      Roda testes E2E em headed mode — Chrome + Firefox
  ${CYAN}test:ci${NC}            Roda testes headless (modo CI)
  ${CYAN}ui${NC}                 Abre Playwright UI Mode (visual, interativo)

${BOLD}GRAVAÇÃO:${NC}
  ${CYAN}demo${NC}               Grava demo completa para portfólio (.webm + screenshots)
  ${CYAN}codegen [arquivo]${NC}  Grava novos testes interativamente no browser
  ${CYAN}trace [arquivo]${NC}    Abre Trace Viewer do último teste
  ${CYAN}report${NC}             Abre relatório HTML dos testes

${BOLD}AUTENTICAÇÃO:${NC}
  O demo e testes carregam automaticamente o ${CYAN}HQ_API_TOKEN${NC} de portfolio-hq/.env.
  Também aceita via variável de ambiente:
    ${MUTED}export HQ_API_TOKEN=<token>${NC}
    ${MUTED}export HQ_API_URL=http://localhost:8000${NC}   ${MUTED}(padrão)${NC}

${BOLD}EXEMPLOS:${NC}
  ./flowforge.sh start
  ./flowforge.sh test
  ./flowforge.sh test e2e/04-execute-workflow.spec.js
  ./flowforge.sh demo
  ./flowforge.sh codegen e2e/meu-teste.spec.js
  ./flowforge.sh logs backend
"
}

# ── Dispatcher ─────────────────────────────────────────────────

CMD="${1:-help}"
shift || true

case "$CMD" in
  start)        cmd_start ;;
  stop)         cmd_stop ;;
  restart)      cmd_restart ;;
  status)       cmd_status ;;
  logs)         cmd_logs "$@" ;;
  test)         cmd_test "$@" ;;
  test:ci)      cmd_test_headless ;;
  demo|record)  cmd_demo ;;
  codegen)      cmd_codegen "$@" ;;
  trace)        cmd_trace "$@" ;;
  report)       cmd_report ;;
  ui)           cmd_ui ;;
  help|--help|-h) usage ;;
  *)
    err "Comando desconhecido: $CMD"
    usage
    exit 1
    ;;
esac
