---
name: crud-generator
description: Gera CRUD Django completo (Model → Migration → Admin → Serializer → ViewSet → URL → Testes) a partir de uma descrição do recurso.
---

# CRUD Generator

Use quando o usuário pedir "crie um CRUD para X" ou descrever um recurso novo.

## Entrada esperada

- Nome do recurso (singular, ex: `Product`).
- App onde vai: `apps/<app>/`.
- Campos: nome, tipo, obrigatoriedade, relacionamentos.
- Permissions: quem pode ler/criar/editar/deletar.

Se faltar info, pergunte antes.

## Saída

Gere **todos** os arquivos, nesta ordem:

1. `apps/<app>/models.py` — model com `__str__`, `Meta.ordering`, `verbose_name`, índices onde útil.
2. Migration via `makemigrations` — e acione `migration-auditor` nela.
3. `apps/<app>/admin.py` — `ModelAdmin` com `list_display`, `search_fields`, `list_filter`.
4. `apps/<app>/serializers.py` — `ListSerializer` + `DetailSerializer` (sem `__all__`).
5. `apps/<app>/views.py` — `ModelViewSet` com queryset otimizado, permissions, filters.
6. `apps/<app>/urls.py` — registra no `DefaultRouter`.
7. `apps/<app>/tests/test_<recurso>_api.py` — testes de list/create/retrieve/update/delete + permissions.

## Regras

- Nunca `fields = "__all__"` em Serializer ou ModelForm.
- Sempre `select_related`/`prefetch_related` no queryset da viewset.
- Permissions fail-closed (default: `IsAuthenticated`).
- Testes cobrindo happy path + unauthorized + invalid payload.
- Após gerar tudo, rode `uv run ruff format .` e `uv run pytest apps/<app>/`.

Pergunte antes de aplicar as migrations.
