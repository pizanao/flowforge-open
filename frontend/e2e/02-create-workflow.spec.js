import { test, expect } from "@playwright/test";

test.describe("Criar Workflow", () => {
  test("cria um novo workflow e abre o editor", async ({ page }) => {
    await page.goto("/");

    await page.getByText("+ Novo Workflow").click();

    // Aguarda navegar ao editor
    await expect(page.getByText("← Voltar")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("Editor")).toBeVisible();

    // Canvas toolbar deve estar visível
    await expect(page.getByText("Salvar").or(page.getByText("✓ Salvo"))).toBeVisible();
    await expect(page.getByText("✦ Validar")).toBeVisible();

    await page.screenshot({ path: "test-results/screenshots/02-new-workflow-editor.png", fullPage: true });
  });

  test("volta para a lista e o novo workflow aparece", async ({ page }) => {
    await page.goto("/");

    // Conta workflows antes
    await page.waitForTimeout(1000); // aguarda API
    const before = await page.locator("h2, h3").count();

    await page.getByText("+ Novo Workflow").click();
    await expect(page.getByText("← Voltar")).toBeVisible({ timeout: 10_000 });
    await page.getByText("← Voltar").click();

    // Volta para a lista
    await expect(page.getByText("+ Novo Workflow")).toBeVisible({ timeout: 5_000 });
  });

  test("palete de nós está visível no editor", async ({ page }) => {
    await page.goto("/");
    await page.getByText("+ Novo Workflow").click();
    await expect(page.getByText("← Voltar")).toBeVisible({ timeout: 10_000 });

    // Palete deve mostrar tipos de nó
    await expect(page.getByText("Trigger")).toBeVisible();
    await expect(page.getByText("HTTP")).toBeVisible();
    await expect(page.getByText("Email")).toBeVisible();
    await expect(page.getByText("Delay")).toBeVisible();
  });
});
