---
description: Varredura de qualidade + segurança.
---

Rode em sequência:

1. `uv run ruff check .` — reporte problemas.
2. `uv run ruff format --check .` — reporte arquivos não formatados.
3. Acione o agente `security-auditor`.
4. Acione o agente `django-reviewer` nos arquivos modificados em relação a `main` (`git diff main --name-only`).
5. Gere um relatório consolidado ordenado por severidade.
