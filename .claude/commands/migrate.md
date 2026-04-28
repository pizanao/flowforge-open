---
description: Fluxo seguro de migrations — makemigrations, revisar, migrate.
---

Faça o fluxo completo de migrations:

1. Rode `uv run python manage.py makemigrations --dry-run --verbosity 2` e mostre o que seria gerado.
2. Se houver mudanças, pergunte ao usuário se posso seguir.
3. Após confirmação, rode `uv run python manage.py makemigrations`.
4. Acione o agente `migration-auditor` nas novas migrations.
5. Se o auditor aprovar, rode `uv run python manage.py migrate --plan` e mostre o plano.
6. Só então rode `uv run python manage.py migrate`.

Se em qualquer passo o usuário disser "não", pare.
