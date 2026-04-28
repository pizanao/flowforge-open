---
description: Popula o banco de desenvolvimento com dados de exemplo.
---

Popule o DB de dev:

1. Verifique se há fixtures em `apps/*/fixtures/*.json`.
2. Se houver, rode `uv run python manage.py loaddata <fixture>` para cada uma.
3. Se não houver, pergunte ao usuário se quer que eu gere fixtures básicas — e para quais modelos.
4. Se o projeto tiver `apps/<app>/management/commands/seed.py`, rode `uv run python manage.py seed`.
5. Confirme que os dados foram criados (count por modelo principal).

Nunca rode `flush` sem confirmação explícita.
