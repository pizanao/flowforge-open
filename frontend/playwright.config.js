import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,  // sequencial — evita conflitos de estado no backend
  globalSetup: "./e2e/global-setup.js",
  retries: 1,
  timeout: 60_000,       // testes normais: 60s (Celery pode demorar)
  reporter: [["html", { open: "never", outputFolder: "playwright-report" }], ["list"]],

  use: {
    baseURL: "http://localhost:5106",
    storageState: "./e2e/auth-state.json",
    video: "on",                    // grava .webm de cada teste para demo/portfólio
    trace: "on",                    // gera trace interativo (playwright show-trace)
    screenshot: "only-on-failure",
  },

  projects: [
    {
      name: "chrome",
      use: { ...devices["Desktop Chrome"] },
    },
    {
      name: "firefox",
      use: { ...devices["Desktop Firefox"] },
    },
  ],
});
