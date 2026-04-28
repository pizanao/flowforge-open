import { test, expect } from "@playwright/test";

test.describe("Workflow List", () => {
  test("exibe o header e pelo menos um workflow", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByRole("heading", { name: "FlowForge", exact: true })).toBeVisible();
    await expect(page.getByText("Visual Workflow Builder")).toBeVisible();
    await expect(page.getByText("+ Novo Workflow")).toBeVisible();

    // Aguarda cards carregarem (fetch da API)
    const cards = page.locator("div").filter({ hasText: /nós|execuções/i }).first();
    await expect(cards).toBeVisible({ timeout: 10_000 });

    await page.screenshot({ path: "test-results/screenshots/01-workflow-list.png", fullPage: true });
  });

  test("exibe stats de workflows, taxa de sucesso e execuções", async ({ page }) => {
    await page.goto("/");

    // Stats cards no topo do dashboard (labels em maiúsculas via CSS)
    await expect(page.getByText("Workflows", { exact: true })).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("Taxa de Sucesso", { exact: true })).toBeVisible();
    await expect(page.getByText("Execuções", { exact: true })).toBeVisible();
    await expect(page.getByText("Duração Média", { exact: true })).toBeVisible();
  });

  test("abre o editor ao clicar em um workflow", async ({ page }) => {
    await page.goto("/");

    // cursor pointer + tem h3 isola o card do workflow (exclui logo header e templates)
    const firstCard = page.locator("div[style*='cursor: pointer']").filter({ has: page.locator("h3") }).first();
    await firstCard.waitFor({ timeout: 10_000 });
    await firstCard.click();

    // Deve aparecer botão Voltar e aba Editor
    await expect(page.getByText("← Voltar")).toBeVisible({ timeout: 5_000 });
    await expect(page.getByText("Editor")).toBeVisible();
  });
});
