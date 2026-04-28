import fs from "node:fs";
import path from "node:path";

import { request } from "@playwright/test";

function loadDotenv(envPath) {
  if (!fs.existsSync(envPath)) return {};
  const out = {};
  for (const line of fs.readFileSync(envPath, "utf8").split("\n")) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const eq = trimmed.indexOf("=");
    if (eq === -1) continue;
    const key = trimmed.slice(0, eq).trim();
    let value = trimmed.slice(eq + 1).trim();
    if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
      value = value.slice(1, -1);
    }
    out[key] = value;
  }
  return out;
}

export default async function globalSetup() {
  const repoEnv = loadDotenv(path.resolve(process.cwd(), "../.env"));
  const email = process.env.TEST_USER_EMAIL || repoEnv.TEST_USER_EMAIL || "admin@flowforge.local";
  const password = process.env.TEST_USER_PASSWORD || repoEnv.TEST_USER_PASSWORD || "admin123";
  const apiBase = process.env.PLAYWRIGHT_API_BASE || repoEnv.PLAYWRIGHT_API_BASE || "http://localhost:8006";

  const context = await request.newContext();
  const response = await context.post(`${apiBase}/api/auth/login/`, {
    data: { email, password },
  });

  if (!response.ok()) {
    let body = "";
    try { body = await response.text(); } catch {}
    throw new Error(
      `Falha ao autenticar Playwright (email=${email}): HTTP ${response.status()} ${body}\n` +
      `→ Confira ALLOWED_EMAILS no .env ou exporte TEST_USER_EMAIL.`,
    );
  }

  const payload = await response.json();
  const storagePath = path.resolve(process.cwd(), "e2e/auth-state.json");
  fs.writeFileSync(
    storagePath,
    JSON.stringify({
      cookies: [],
      origins: [
        {
          origin: "http://localhost:5106",
          localStorage: [
            { name: "flowforge_token", value: payload.access },
            { name: "flowforge_refresh", value: payload.refresh },
            { name: "flowforge_user", value: JSON.stringify(payload.user) },
          ],
        },
      ],
    }),
  );

  await context.dispose();
}
