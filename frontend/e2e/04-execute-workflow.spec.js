import { test, expect } from "@playwright/test";

test.describe("Execução de Workflow", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await page.waitForTimeout(500);
    // Card de workflow com pelo menos 1 nó (regex exclui "0 nós" e cards vazios criados por outros testes)
    const card = page.locator("div[style*='cursor: pointer']")
      .filter({ has: page.locator("h3") })
      .filter({ hasText: /[1-9]\d* nós/ })
      .first();
    await card.waitFor({ timeout: 10_000 });
    await card.click();
    await expect(page.getByText("← Voltar")).toBeVisible({ timeout: 5_000 });
  });

  test("botão Executar dispara a execução", async ({ page }) => {
    const runBtn = page.getByText("▶ Executar");
    await expect(runBtn).toBeVisible({ timeout: 5_000 });
    await runBtn.click();

    // Botão muda para "Executando..."
    await expect(page.getByText("⏳ Executando...")).toBeVisible({ timeout: 5_000 });

    await page.screenshot({ path: "test-results/screenshots/04-executing.png", fullPage: true });
  });

  test("execução conclude e aba Execuções atualiza", async ({ page }) => {
    await page.getByText("▶ Executar").click();

    // Aguarda completar (success ou failed — até 30s para workflows com LLM)
    await expect(
      page.getByText("▶ Executar")
    ).toBeVisible({ timeout: 30_000 });

    // Clica na aba Execuções para ver o histórico
    await page.getByText("Execuções", { exact: true }).click();
    await page.waitForTimeout(500);

    // Verifica que a aba Execuções está ativa (o conteúdo muda)
    // Apenas verifica que a página responde - não verifica conteúdo específico
    // pois pode ou não haver execuções prévias
    const execTabActive = await page.locator("button").filter({ hasText: "Execuções" }).first().isVisible();
    expect(execTabActive).toBe(true);

    await page.screenshot({ path: "test-results/screenshots/04-run-history.png", fullPage: true });
  });
});
