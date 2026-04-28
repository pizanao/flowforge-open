import { test, expect } from "@playwright/test";

test.describe("Canvas e Nodes", () => {
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

  test("clica em um nó e abre o drawer de configuração", async ({ page }) => {
    // Aguarda canvas renderizar
    await page.waitForTimeout(1000);

    // Nós no canvas são divs posicionados absolutamente — clica no primeiro
    const node = page.locator("[style*='position: absolute'][style*='border-radius: 8px']").first();
    await node.waitFor({ timeout: 5_000 });
    await node.click();

    // Drawer deve abrir com aba Configurar
    await expect(page.getByText("Configurar")).toBeVisible({ timeout: 3_000 });

    await page.screenshot({ path: "test-results/screenshots/03-node-drawer.png", fullPage: true });
  });

  test("drawer tem abas Configurar e Execução", async ({ page }) => {
    await page.waitForTimeout(1000);
    const node = page.locator("[style*='position: absolute'][style*='border-radius: 8px']").first();
    await node.waitFor({ timeout: 5_000 });
    await node.click();

    await expect(page.getByRole("button", { name: "Configurar" })).toBeVisible({ timeout: 3_000 });
    await expect(page.getByRole("button", { name: /Execução/ })).toBeVisible();
  });

  test("valida DAG do workflow via botão Validar", async ({ page }) => {
    await page.getByText("✦ Validar").click();
    // Aguarda resposta da API (válido ou erros)
    await expect(
      page.getByText("✓ DAG válido").or(page.getByText(/erro/i))
    ).toBeVisible({ timeout: 10_000 });
  });
});
