import assert from "node:assert/strict";
import http from "node:http";
import { after, before, test } from "node:test";

import { validateBackendConnectivity } from "../scripts/validate-backend-connectivity.mjs";

let server;
let baseUrl;

before(async () => {
  server = http.createServer((request, response) => {
    if (request.url === "/api/workflows/") {
      response.writeHead(401, { "Content-Type": "application/json" });
      response.end(JSON.stringify({ detail: "Authentication credentials were not provided." }));
      return;
    }

    response.writeHead(404, { "Content-Type": "application/json" });
    response.end(JSON.stringify({ detail: "Not found." }));
  });

  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const { port } = server.address();
  baseUrl = `http://127.0.0.1:${port}`;
});

after(async () => {
  await new Promise((resolve) => server.close(resolve));
});

test("startup check accepts reachable backend responses below 500", async () => {
  const result = await validateBackendConnectivity({
    backendUrl: baseUrl,
    retries: 1,
    timeoutMs: 500,
    retryDelayMs: 1,
  });

  assert.equal(result.ok, true);
  assert.equal(result.statusCode, 401);
  assert.equal(result.url, `${baseUrl}/api/workflows/`);
});

test("startup check fails when backend host cannot be resolved", async () => {
  await assert.rejects(
    validateBackendConnectivity({
      backendUrl: "http://host.docker.internal.invalid:8006",
      retries: 1,
      timeoutMs: 500,
      retryDelayMs: 1,
    }),
    /Frontend nao pode iniciar: backend inacessivel/,
  );
});
