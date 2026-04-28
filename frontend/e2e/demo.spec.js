/**
 * Demo FlowForge — Luna Workflow do zero
 *
 * Cria um workflow completo de agente de comunicação:
 *   Webhook → LLM (Luna/Ollama) → HTTP (Waha/Telegram) → Output
 *
 * Parâmetros lidos de variáveis de ambiente (definidas pelo flowforge.sh na
 * primeira execução ou via .demo.env):
 *   DEMO_WORKFLOW_NAME, DEMO_OLLAMA_URL, DEMO_LUNA_MODEL,
 *   DEMO_LUNA_PROMPT, DEMO_WAHA_URL, DEMO_WAHA_SESSION
 *
 * Uso:
 *   ./flowforge.sh demo
 *   → test-results/demo-chrome/video.webm
 */

import { test, expect } from "@playwright/test";

// ── Config via env (preenchida pelo flowforge.sh na first-run) ────────────────
const CFG = {
  workflowName:  process.env.DEMO_WORKFLOW_NAME || "Luna — Agente de Comunicação",
  ollamaUrl:     process.env.DEMO_OLLAMA_URL    || "http://host.docker.internal:11434",
  lunaModel:     process.env.DEMO_LUNA_MODEL    || "llama3.2",
  lunaPrompt:    process.env.DEMO_LUNA_PROMPT   ||
    "Você é Luna, assistente especializada em comunicação.\n\nMensagem recebida: {{data.message}}\nDe: {{data.from}}\n\nResponda de forma clara e empática.",
  wahaUrl:       process.env.DEMO_WAHA_URL      || "http://host.docker.internal:3000",
  wahaSession:   process.env.DEMO_WAHA_SESSION  || "default",
  hqApiUrl:      process.env.HQ_API_URL         || "http://localhost:8000",
  hqApiToken:    process.env.HQ_API_TOKEN       || "",
};

test.use({
  launchOptions: { slowMo: 400 },
  viewport: { width: 1280, height: 800 },
});

// Demo é lento por design (slowMo + pausas visuais) — timeout generoso
// slowMo aplica delay em cada CDP command interno (mouseMove, mouseDown, etc.)
// 4 drags × ~15 comandos × 400ms = ~24s só de drag; total ~3min é seguro
test.setTimeout(240_000);

// Mapa de tipo → label exibido no palete
const NODE_LABELS = {
  trigger:   "Trigger",
  http:      "HTTP",
  transform: "Transform",
  condition: "Condição",
  llm:       "LLM Agent",
  email:     "Email",
  delay:     "Delay",
  output:    "Output",
};

// ── Helper: arrasta nó do palete ao canvas via dragAndDrop nativo ────────────
async function addNode(page, nodeType, x, y) {
  const label = NODE_LABELS[nodeType] || nodeType;

  // Palete: div draggable com o texto do label
  const source = page.locator(`[draggable="true"]`).filter({ hasText: label }).first();
  const canvas = page.locator('[style*="radial-gradient"]').first();

  const canvasBox = await canvas.boundingBox();
  if (!canvasBox) throw new Error(`Canvas não encontrado ao adicionar nó ${nodeType}`);

  await source.dragTo(canvas, {
    targetPosition: { x: Math.round(x), y: Math.round(y) },
  });

  await page.waitForTimeout(500);
}

// ── Helper: clica em nó pelo tipo e aguarda o drawer ────────────────────────
async function openNode(page, labelText) {
  await page.locator("[style*='position: absolute'][style*='border-radius: 8px']")
    .filter({ hasText: labelText })
    .first()
    .click();
  await expect(page.getByRole("button", { name: "Configurar" })).toBeVisible({ timeout: 4000 });
  await page.waitForTimeout(300);
}

// ── Helper: fecha o drawer (clica no botão ✕) ───────────────────────────────
async function closeDrawer(page) {
  await page.locator("button").filter({ hasText: "✕" }).click();
  await page.waitForTimeout(400);
}

// ── Helper: chamada autenticada ao proxy HQ ─────────────────────────────────
async function hqFetch(page, path, options = {}) {
  if (!CFG.hqApiToken) return null;
  const url = `${CFG.hqApiUrl}/api/forge/${path}`;
  return page.evaluate(
    async ({ url, token, opts }) => {
      const resp = await fetch(url, {
        ...opts,
        headers: { "X-HQ-Token": token, "Content-Type": "application/json", ...(opts.headers || {}) },
      });
      return { status: resp.status, data: await resp.json().catch(() => null) };
    },
    { url, token: CFG.hqApiToken, opts: options },
  );
}

// ════════════════════════════════════════════════════════════════════════════
test("Demo — Luna Workflow do zero", async ({ page }) => {
  // ── 0. Verifica autenticação HQ ──────────────────────────────────────────
  if (CFG.hqApiToken) {
    const auth = await page.evaluate(
      async ({ url, token }) => {
        const r = await fetch(`${url}/api/forge/workflows/`, {
          headers: { "X-HQ-Token": token },
        });
        return r.status;
      },
      { url: CFG.hqApiUrl, token: CFG.hqApiToken },
    );
    expect(auth, "HQ proxy deve responder 200 com token válido").toBe(200);
  }

  // ── 1. Página inicial ────────────────────────────────────────────────────
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "FlowForge" })).toBeVisible({ timeout: 10_000 });
  await page.waitForTimeout(1500);
  await page.screenshot({ path: "test-results/screenshots/demo-01-lista.png", fullPage: true });

  // ── 2. Cria novo workflow ────────────────────────────────────────────────
  await page.getByText("+ Novo Workflow").click();
  await expect(page.getByText("← Voltar")).toBeVisible({ timeout: 10_000 });
  await page.waitForTimeout(1200);
  await page.screenshot({ path: "test-results/screenshots/demo-02-canvas-vazio.png", fullPage: true });

  // ── 3. Adiciona nós ao canvas ────────────────────────────────────────────
  // Trigger (Webhook)
  await addNode(page, "trigger", 80, 160);
  await page.waitForTimeout(600);
  await page.screenshot({ path: "test-results/screenshots/demo-03a-trigger.png" });

  // LLM Agent (Luna)
  await addNode(page, "llm", 280, 160);
  await page.waitForTimeout(600);

  // HTTP (resposta para Waha/Telegram)
  await addNode(page, "http", 480, 160);
  await page.waitForTimeout(600);

  // Output
  await addNode(page, "output", 680, 160);
  await page.waitForTimeout(600);
  await page.screenshot({ path: "test-results/screenshots/demo-03b-nos-adicionados.png" });

  // ── 4. Configura Trigger como Webhook ────────────────────────────────────
  await openNode(page, "Trigger");
  await page.getByLabel(/tipo de disparo/i).selectOption("webhook");
  await page.waitForTimeout(800);
  await page.screenshot({ path: "test-results/screenshots/demo-04-trigger-webhook.png", fullPage: true });
  await closeDrawer(page);

  // ── 5. Configura LLM com Luna (Ollama) ───────────────────────────────────
  await openNode(page, "LLM Agent");
  // Campo Modelo
  const modelInput = page.getByLabel(/modelo/i).first();
  await modelInput.clear();
  await modelInput.fill(CFG.lunaModel);
  await page.waitForTimeout(400);
  // Campo Prompt
  const promptArea = page.getByLabel(/template do prompt/i).first();
  await promptArea.clear();
  await promptArea.fill(CFG.lunaPrompt);
  await page.waitForTimeout(800);
  await page.screenshot({ path: "test-results/screenshots/demo-05-luna-config.png", fullPage: true });
  await closeDrawer(page);

  // ── 6. Configura HTTP para responder via Waha ─────────────────────────────
  await openNode(page, "HTTP");
  await page.getByLabel(/método/i).first().selectOption("POST");
  await page.getByLabel(/url/i).first().fill(
    `${CFG.wahaUrl}/api/sendText`
  );
  await page.waitForTimeout(800);
  await page.screenshot({ path: "test-results/screenshots/demo-06-http-waha.png", fullPage: true });
  await closeDrawer(page);

  // ── 7. Salva e valida o DAG ───────────────────────────────────────────────
  // Auto-save (debounce 2s) já salvou após configurar os nós — aguarda confirmação
  await expect(page.getByText("✓ Salvo")).toBeVisible({ timeout: 10_000 });
  await page.waitForTimeout(600);
  await page.screenshot({ path: "test-results/screenshots/demo-07-salvo.png", fullPage: true });

  await page.getByRole("button", { name: /validar/i }).click();
  await page.waitForTimeout(1500);
  await page.screenshot({ path: "test-results/screenshots/demo-08-validado.png", fullPage: true });

  // ── 8. Executa o workflow ─────────────────────────────────────────────────
  await page.getByRole("button", { name: /executar/i }).click();
  // Pausa visual — a execução pode ser muito rápida (sem Ollama real)
  await page.waitForTimeout(2500);
  await page.screenshot({ path: "test-results/screenshots/demo-09-executando.png", fullPage: true });

  // Aguarda conclusão: botão volta a "▶ Executar" (não está mais disabled)
  await expect(page.getByRole("button", { name: "▶ Executar" })).toBeEnabled({ timeout: 30_000 });
  await page.waitForTimeout(1500);
  await page.screenshot({ path: "test-results/screenshots/demo-10-concluido.png", fullPage: true });

  // ── 9. Histórico de execuções ─────────────────────────────────────────────
  // Clica na aba "Execuções" (tab no workflow editor)
  await page.getByRole("button", { name: /execuções/i }).first().click();
  await page.waitForTimeout(1200);
  await page.screenshot({ path: "test-results/screenshots/demo-11-historico.png", fullPage: true });
});
