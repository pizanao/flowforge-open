import http from "node:http";
import https from "node:https";
import path from "node:path";
import { fileURLToPath } from "node:url";

const DEFAULT_BACKEND_URL = "http://localhost:8006";
const DEFAULT_HEALTH_PATH = "/api/workflows/";
const DEFAULT_TIMEOUT_MS = 2000;
const DEFAULT_RETRIES = 15;
const DEFAULT_RETRY_DELAY_MS = 2000;

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function normalizeUrl(baseUrl, healthPath) {
  const url = new URL(baseUrl || DEFAULT_BACKEND_URL);
  url.pathname = healthPath || DEFAULT_HEALTH_PATH;
  url.search = "";
  url.hash = "";
  return url;
}

function requestOnce(url, timeoutMs) {
  const client = url.protocol === "https:" ? https : http;

  return new Promise((resolve, reject) => {
    const request = client.request(
      url,
      {
        method: "GET",
        timeout: timeoutMs,
        headers: {
          Accept: "application/json",
          "User-Agent": "flowforge-frontend-startup-check",
        },
      },
      (response) => {
        response.resume();
        response.on("end", () => {
          if (response.statusCode >= 500) {
            reject(new Error(`Backend respondeu HTTP ${response.statusCode}`));
            return;
          }
          resolve(response.statusCode);
        });
      },
    );

    request.on("timeout", () => {
      request.destroy(new Error(`Timeout ao conectar no backend após ${timeoutMs}ms`));
    });
    request.on("error", reject);
    request.end();
  });
}

export async function validateBackendConnectivity(options = {}) {
  const backendUrl = options.backendUrl ?? process.env.BACKEND_URL ?? DEFAULT_BACKEND_URL;
  const healthPath = options.healthPath ?? process.env.BACKEND_CONNECTIVITY_PATH ?? DEFAULT_HEALTH_PATH;
  const timeoutMs = Number(options.timeoutMs ?? process.env.BACKEND_CONNECTIVITY_TIMEOUT_MS ?? DEFAULT_TIMEOUT_MS);
  const retries = Number(options.retries ?? process.env.BACKEND_CONNECTIVITY_RETRIES ?? DEFAULT_RETRIES);
  const retryDelayMs = Number(
    options.retryDelayMs ?? process.env.BACKEND_CONNECTIVITY_RETRY_DELAY_MS ?? DEFAULT_RETRY_DELAY_MS,
  );
  const url = normalizeUrl(backendUrl, healthPath);

  let lastError = null;
  for (let attempt = 1; attempt <= retries; attempt += 1) {
    try {
      const statusCode = await requestOnce(url, timeoutMs);
      console.log(`[startup] Backend acessivel em ${url.toString()} (HTTP ${statusCode})`);
      return { ok: true, statusCode, url: url.toString() };
    } catch (error) {
      lastError = error;
      console.error(
        `[startup] Falha ao validar backend (${attempt}/${retries}) em ${url.toString()}: ${error.message}`,
      );
      if (attempt < retries) {
        await sleep(retryDelayMs);
      }
    }
  }

  throw new Error(
    `Frontend nao pode iniciar: backend inacessivel em ${url.toString()}. Ultimo erro: ${lastError?.message}`,
  );
}

if (fileURLToPath(import.meta.url) === path.resolve(process.argv[1])) {
  validateBackendConnectivity().catch((error) => {
    console.error(error.stack || error.message);
    process.exit(1);
  });
}
