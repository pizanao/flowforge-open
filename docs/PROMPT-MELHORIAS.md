# PROMPT.md — FlowForge Modernization Sprint

> Sessão de modernização do frontend. Projeto está **80% pronto e testado para produção**. A meta é refinar sem regressão.

---

## 🎯 Contexto

O FlowForge é o projeto #6 do meu portfólio: workflow visual no-code com React Flow, DAG engine (Kahn's Algorithm), 8 tipos de nós e Strategy Pattern para executores. Stack: Django 5.1 + Celery + PostgreSQL + React 18 + Recharts. Accent: `#a855f7` (violet). Fonts: Sora + Source Code Pro.

**Estado atual:**
- Backend estável, integração funcionando, suite de testes passando.
- Frontend funcional, mas com **dois problemas estruturais**:
  1. `frontend/src/App.jsx` passou de 1.000 linhas — virou um deus-componente.
  2. Visual genérico, com layout mal aproveitado (muito scroll vertical, paddings excessivos, largura desperdiçada).

---

## 🛡️ Princípios não-negociáveis

1. **Zero regressão funcional.** Cada sprint termina com app rodando idêntico ao anterior em comportamento. Refactor é mudança *interna*; do ponto de vista do usuário, nada quebra.
2. **Vertical slices, nunca big-bang.** Cada sprint é um commit (ou poucos commits) atômico, mergeable, revertível.
3. **Tokens antes de visual.** Criar o sistema de design *primeiro* e depois aplicar — não fazer no olho.
4. **Componentizar ≠ redesenhar.** Sprint 2 só move código de lugar. Visual só muda no Sprint 3.
5. **Cost-zero first.** Sem libs novas se um hook + CSS variables resolvem.

---

## 🗺️ Mapa dos Sprints

| Sprint | Escopo | Risco | Tempo estimado |
|--------|--------|-------|----------------|
| 1 | Theme system (auto-detect SO + tokens) | Baixo | 1 sessão |
| 2 | Componentização do `App.jsx` | Médio (regressão) | 1-2 sessões |
| 3 | Layout fluido + densidade visual | Médio | 1-2 sessões |
| 4 | Polish, a11y e validação final | Baixo | 1 sessão |

---

## Sprint 1 — Theme System com Auto-Detect

### Objetivo
Sistema de tema robusto que **detecta a preferência do SO** (`prefers-color-scheme`), permite override manual pelo usuário, persiste a escolha e reage em tempo real a mudanças do SO.

### Entregas

**1.1. Tokens semânticos em CSS variables**

Criar `frontend/src/styles/tokens.css` com escalas e tokens semânticos. Não usar valores hex direto nos componentes a partir daqui.

```css
:root {
  /* Brand scale (violet #a855f7) */
  --violet-50: #faf5ff;
  --violet-500: #a855f7;
  --violet-600: #9333ea;
  --violet-900: #581c87;
  /* ... 50-950 completo */

  /* Neutros — escala neutra */
  --neutral-0: #ffffff;
  --neutral-50: #fafafa;
  /* ... até --neutral-950 */
}

/* Tema light (default) */
[data-theme="light"] {
  --bg-base: var(--neutral-0);
  --bg-surface: var(--neutral-50);
  --bg-raised: var(--neutral-0);
  --bg-overlay: rgba(0,0,0,0.4);

  --fg-default: var(--neutral-900);
  --fg-muted: var(--neutral-600);
  --fg-subtle: var(--neutral-500);

  --border-default: var(--neutral-200);
  --border-strong: var(--neutral-300);

  --accent: var(--violet-600);
  --accent-hover: var(--violet-700);
  --accent-soft: var(--violet-50);
}

/* Tema dark */
[data-theme="dark"] {
  --bg-base: var(--neutral-950);
  --bg-surface: var(--neutral-900);
  /* ... */
  --accent: var(--violet-500);
  --accent-soft: rgba(168, 85, 247, 0.1);
}
```

**1.2. Hook `useTheme`**

Criar `frontend/src/hooks/useTheme.js`:

```js
// Pseudocódigo do comportamento esperado:
// - Estado: "light" | "dark" | "system"
// - Default: "system" (auto-detect via matchMedia)
// - Persistência: localStorage["flowforge-theme"]
// - Listener: matchMedia('(prefers-color-scheme: dark)')
//   reage em tempo real se modo for "system"
// - Aplica via document.documentElement.setAttribute('data-theme', resolved)
// - Retorna { theme, resolvedTheme, setTheme }
```

Tratar edge case: **flicker de tema** no carregamento. Adicionar script inline no `index.html` que aplica o tema *antes* do React montar:

```html
<script>
  (function() {
    var stored = localStorage.getItem('flowforge-theme');
    var system = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    var resolved = (!stored || stored === 'system') ? system : stored;
    document.documentElement.setAttribute('data-theme', resolved);
  })();
</script>
```

**1.3. `ThemeProvider` + toggle UI**

- Context provider envolvendo a app.
- Componente `ThemeToggle` com 3 estados (light / dark / system) acessível na topbar e sem emojs.
- Usar ícones (sun / moon / monitor) — provavelmente já tenho `lucide-react` preferencia .

### Decisões arquiteturais (rationale para entrevista)

- **Por que `data-theme` e não classe?** Atributo é mais semântico, evita conflito com Tailwind/utilities, e dá pra dark-mode em SVG via CSS attribute selector.
- **Por que script inline anti-flicker?** Render-blocking de 200-300 bytes vale muito mais que o flash branco que assusta o usuário em dark mode. Padrão usado pela docs do Next.js e shadcn.
- **Por que três estados (light/dark/system)?** Respeitar a escolha do SO é o default certo, mas usuário consciente quer override. Dois estados forçam escolha.
- **Por que CSS vars e não styled-components/emotion?** Zero runtime, zero bundle extra, troca de tema é instantânea (sem re-render React), e funciona até com SSR estático.

### Validação Sprint 1
- [ ] Abrir o app com SO em dark → carrega em dark sem flicker.
- [ ] Trocar tema do SO com app aberto → app reage em tempo real (modo system).
- [ ] Selecionar light manual → persiste no reload.
- [ ] Selecionar system → volta a seguir SO.
- [ ] **Nenhuma cor mudou ainda nos componentes — eles ainda usam hex hardcoded.** Sprint 1 só monta a infra.

---

## Sprint 2 — Componentização do `App.jsx`

### Objetivo
Quebrar o `App.jsx` (1k+ linhas) em estrutura modular **mantendo comportamento 100% idêntico**. Refactor mecânico, não criativo.

### Etapa 0 — Mapeamento (obrigatório antes de mover qualquer linha)

Antes de criar qualquer arquivo novo, gerar um **inventário comentado do App.jsx atual**, identificando blocos:

- Imports
- Estados (useState/useReducer)
- Effects (useEffect)
- Handlers
- Subcomponentes inline
- JSX render
- Helpers/utilitários

Salvar esse mapa como comentário no topo do `App.jsx` ou num `REFACTOR_NOTES.md` temporário. Esse mapa guia a extração.

### Estrutura-alvo

```
frontend/src/
├── main.jsx
├── App.jsx                        ← fica < 100 linhas (router + providers)
├── styles/
│   ├── tokens.css
│   └── globals.css
├── contexts/
│   ├── ThemeContext.jsx
│   └── WorkflowContext.jsx        ← se houver state global de workflow
├── hooks/
│   ├── useTheme.js
│   ├── useWorkflow.js             ← lógica de DAG/execução
│   └── useNodeOperations.js
├── layout/
│   ├── AppShell.jsx               ← grid principal (sidebar/topbar/main)
│   ├── Topbar.jsx
│   ├── Sidebar.jsx
│   └── Inspector.jsx              ← painel direito de propriedades
├── pages/
│   ├── EditorPage.jsx
│   ├── WorkflowsListPage.jsx
│   └── ExecutionsPage.jsx
├── features/
│   ├── canvas/
│   │   ├── WorkflowCanvas.jsx     ← wrapper React Flow
│   │   ├── canvasConfig.js
│   │   └── edgeStyles.js
│   ├── nodes/
│   │   ├── index.js               ← registry dos 8 tipos
│   │   ├── TriggerNode.jsx
│   │   ├── HttpRequestNode.jsx
│   │   ├── TransformNode.jsx
│   │   ├── ConditionNode.jsx
│   │   ├── DelayNode.jsx
│   │   ├── LlmCallNode.jsx
│   │   ├── DatabaseNode.jsx
│   │   └── OutputNode.jsx
│   ├── palette/
│   │   └── NodePalette.jsx        ← lista drag-source de nós
│   └── inspector/
│       ├── NodeInspector.jsx
│       └── fields/                ← inputs reutilizáveis
├── components/
│   ├── ui/                        ← Button, Input, Select, Modal, etc
│   └── icons/
└── lib/
    ├── api.js                     ← cliente HTTP
    └── workflow-utils.js
```

### Regras de extração

1. **Move-then-rename**: extrair UM componente por commit. Rodar app entre cada extração.
2. **Props explícitas, não Context prematuro**: só promover a Context quando 3+ níveis de prop drilling aparecerem.
3. **Hooks customizados pra lógica, componentes pra render**: se um bloco tem lógica + render acoplados, separar `useNodeEditor()` (lógica) de `<NodeEditor />` (render).
4. **Registry pattern para nós**: criar `nodes/index.js` que exporta `nodeTypes = { trigger: TriggerNode, ... }` — assim adicionar um 9º tipo é uma linha.
5. **Não introduzir libs novas** nessa fase (sem zustand/redux/jotai). Só extração.

### Decisões arquiteturais (rationale)

- **Por que `features/` e não só `components/`?** Feature-based folders escalam melhor que type-based. Tudo de "canvas" fica junto — componente, hook, tipos, utils. Padrão usado em codebases grandes (Bulletproof React).
- **Por que `pages/` separado?** Rotas têm responsabilidade diferente: orquestram features, não renderizam UI primária.
- **Por que registry para os nós?** Strategy Pattern do backend espelhado no frontend. Adicionar tipo novo = 1 arquivo + 1 entry no registry. Acoplamento mínimo.
- **Por que sem Redux/Zustand ainda?** YAGNI. React Flow já gerencia state do grafo. Workflow metadata pode viver em Context. Se virar gargalo, aí sim avalio.

### Validação Sprint 7
- [ ] `App.jsx` tem menos de 100 linhas.
- [ ] Nenhum arquivo de feature passa de ~250 linhas.
- [ ] Todas as funcionalidades pré-refactor funcionam idênticas (criar workflow, adicionar nó, conectar, salvar, executar).
- [ ] Nenhum visual mudou. Mesmas cores, mesmos espaçamentos.
- [ ]  de produção passa sem warnings novos.
- [ ] Build de produção passa sem warnings novos.

---

## Sprint 8 — Layout Fluido e Densidade Visual

### Objetivo
Visual **linear, intuitivo, sem desperdício de espaço**. Aproveitar 100% da largura, minimizar scroll vertical, melhorar densidade de informação sem virar planilha.

### Princípios de design

1. **Full-bleed por padrão**: nada de `max-width: 1280px` centralizado. App de produtividade usa 100% da viewport.
2. **Scrolls locais, nunca global**: cada painel rola dentro de si. Topbar e sidebars são fixos. `body { overflow: hidden }`.
3. **Hierarquia por densidade, não por tamanho**: ao invés de fontes gigantes, usar peso, contraste e spacing pra criar hierarquia.
4. **Spacing escalonado em 4px**: tokens `--space-1` (4px) até `--space-12` (48px). Padding interno de cards = 12-16px, não 24-32px.
5. **Cantos sutis**: `border-radius` de 6-8px nos cards, 4px em inputs. Nada de rounded-2xl gigante.

### Layout-alvo do EditorPage

```
┌─────────────────────────────────────────────────────────┐
│  Topbar (48px)  · logo · workflow name · run · theme   │
├──────┬──────────────────────────────────────────┬───────┤
│      │                                          │       │
│  P   │                                          │   I   │
│  a   │           CANVAS (React Flow)            │   n   │
│  l   │           (fullscreen)                   │   s   │
│  e   │                                          │   p   │
│  t   │                                          │   .   │
│  t   │                                          │       │
│  e   │                                          │   ›   │
│      │                                          │       │
│ 240px│              flex: 1                     │ 320px │
└──────┴──────────────────────────────────────────┴───────┘
```

- **CSS Grid** no `AppShell`: `grid-template-columns: auto 1fr auto; grid-template-rows: 48px 1fr;`.
- **Sidebars colapsáveis** (clicar no chevron oculta, mantém ícone-only de 48px).
- **Inspector como drawer-fixo**, não modal. Aparece quando um nó é selecionado, sem cobrir o canvas.

### Componentes visuais — guia rápido

- **Botões**: altura 32px (default) / 28px (compact). Padding horizontal 12px. Sem sombra. `:hover` muda só background.
- **Inputs**: altura 32px. Border 1px sólida. Focus com `outline: 2px solid var(--accent)` e `outline-offset: 1px`.
- **Cards**: background `--bg-surface`, border 1px `--border-default`, radius 6px, padding 12-16px. Sem box-shadow por padrão.
- **Tipografia**:
  - Sora 600 / 14px → títulos de painel
  - Sora 500 / 13px → labels
  - Sora 400 / 13px → corpo
  - Source Code Pro 400 / 12px → IDs, valores técnicos, JSON preview
- **Cores funcionais** (criar tokens):
  - `--success`: verde 600/500 (light/dark)
  - `--warning`: amber 600/500
  - `--danger`: red 600/500
  - `--info`: blue 600/500

### O que muda página a página

**EditorPage**: aplicar layout-alvo acima. Remover qualquer `<div className="container mx-auto">` ou similar. Canvas ocupa todo espaço entre palette e inspector.

**WorkflowsListPage**: tabela densa ao invés de cards grandes. Linhas de 36px. Colunas: nome, última execução, status, ações. Toolbar superior com filtro + "Novo workflow". Sem padding gigante.

**ExecutionsPage**: split-view horizontal. Lista de execuções à esquerda (320px), detalhe + logs à direita (flex 1). Logs com fonte mono, fundo `--bg-base`, sem padding excessivo.

### Decisões arquiteturais (rationale)

- **Por que CSS Grid no shell e não Flexbox?** Layout 2D (linhas + colunas) é exatamente pra isso. Grid declara a estrutura inteira em 2 linhas de CSS; flex aninhado precisaria de 4 wrappers.
- **Por que sidebars colapsáveis e não fixas?** Em telas <1366px, palette + inspector + canvas largo aperta tudo. Colapso é a saída elegante; alternativa seria responsividade complexa.
- **Por que densidade alta?** Ferramenta de produtividade ≠ landing page. Linear, Notion, Figma, Retool — todos usam densidade alta. Espaço respirando demais é sinal de "site bonito"; aqui é "ferramenta produtiva".
- **Por que inspector drawer fixo e não modal?** Modal interrompe fluxo (clicar fora fecha, Esc fecha). Drawer fixo permite editar nó e ver canvas mudando ao mesmo tempo — feedback loop curto.

### Validação Sprint 3
- [ ] Em viewport 1920x1080, zero scroll vertical na EditorPage.
- [ ] Em 1366x768, ainda funcional, com sidebars colapsáveis acessíveis.
- [ ] Trocar entre light/dark mantém legibilidade e contraste em todos os componentes.
- [ ] Hierarquia visual clara: olhar um painel novo, em 2 segundos saber o que é título, o que é input, o que é ação primária.
- [ ] Nenhuma funcionalidade quebrou. Repetir teste do Sprint 2.

---

## Sprint 4 — Polish, A11y e Validação

### Entregas

1. **Acessibilidade**:
   - Foco visível em todos os elementos interativos (não usar `outline: none` sem substituto).
   - Contraste WCAG AA em ambos os temas (verificar com axe DevTools).
   - `aria-label` em botões só com ícone.
   - Navegação por teclado no canvas (já é nativo do React Flow, mas validar).
2. **Micro-interações**:
   - Transições de 150ms em hover/focus.
   - Transição de tema com `transition: background-color 200ms` no body — sem ficar piscando.
   - Drag-and-drop com cursor visual claro.
3. **Estados vazios e de erro**:
   - Empty state na lista de workflows (ilustração simples + CTA).
   - Erro de execução com mensagem útil, não stacktrace cru.
4. **Performance**:
   - Lighthouse 90+ em performance.
   - Memoização nos nós do React Flow (`React.memo` + comparação shallow).
5. **Documentação**:
   - Atualizar `CLAUDE.md` com nova estrutura de pastas.
   - `README.md` com screenshots novos.

### Validação final

- [ ] Build de produção sem warnings.
- [ ] App roda em Chrome, Firefox, Safari sem regressão visual.
- [ ] Lighthouse: performance 90+, a11y 95+.
- [ ] Smoke test completo: criar workflow, adicionar 5 nós dos 8 tipos, conectar, salvar, executar, ver resultado.
- [ ] Trocar tema 10 vezes seguidas — sem bug visual.
- [ ] Comparar bundle size com pré-refactor — não pode ter aumentado mais que 5%.

---

## 📋 Checklist meta

Antes de começar **cada sprint**, confirmar:

- [ ] Branch dedicada criada (`feat/sprint-N-descricao`).
- [ ] Suite de testes do backend rodando localmente.
- [ ] Build do frontend passando.
- [ ] Tag git no estado atual (`pre-sprint-N`) pra rollback rápido.

Antes de **fechar cada sprint**:

- [ ] Smoke test manual completo.
- [ ] Commit semântico com escopo claro.
- [ ] Atualizar este `PROMPT.md` se descobrir desvio de plano.

---

## 🎤 Notas para a entrevista (06/04/2026)

Resumo de 60 segundos do que esse sprint vai me dar:

> "O FlowForge tinha um problema clássico de greenfield: começou rápido, App.jsx virou um deus-componente de 1k linhas e o visual era genérico. Modernizei em 4 sprints disciplinados — primeiro o sistema de tema com auto-detect do SO via matchMedia, depois a componentização em arquitetura feature-based, depois o layout fluido com CSS Grid pra aproveitar 100% da viewport, e por fim polish e a11y. O ponto-chave foi vertical slicing: cada sprint termina com app rodando idêntico do ponto de vista do usuário. Refactor não pode ser big-bang em projeto que vai pra produção."

Pontos altos pra puxar se perguntarem:

- Tokens semânticos via CSS vars vs CSS-in-JS (zero runtime).
- Anti-flicker script inline antes do React montar.
- Registry pattern espelhando o Strategy Pattern do backend.
- Por que NÃO introduzi Zustand/Redux (YAGNI).
- Densidade alta como decisão consciente de UX para ferramentas de produtividade.

---

**Pronto pra começar pelo Sprint 7.** Confirma o plano e abre uma nova sessão Claude Code já no diretório `flowforge/` com este `PROMPT.md` salvo na raiz.
