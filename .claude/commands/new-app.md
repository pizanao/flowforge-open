---
description: Cria um app Django novo em apps/ com a estrutura padrão do projeto.
argument-hint: <nome-do-app>
---

Crie um app Django novo chamado **$ARGUMENTS** em `apps/$ARGUMENTS/`.

Passos:

1. `uv run python manage.py startapp $ARGUMENTS apps/$ARGUMENTS` (crie a pasta antes se não existir).
2. Abra `apps/$ARGUMENTS/apps.py` e ajuste `name = "apps.$ARGUMENTS"`.
3. Crie os arquivos:
   - `apps/$ARGUMENTS/services.py` (vazio com docstring)
   - `apps/$ARGUMENTS/urls.py` (urlpatterns vazio)
   - `apps/$ARGUMENTS/tests/__init__.py`
   - `apps/$ARGUMENTS/tests/conftest.py`
4. Adicione `"apps.$ARGUMENTS"` em `INSTALLED_APPS` de `settings/base.py`.
5. Inclua `path("$ARGUMENTS/", include("apps.$ARGUMENTS.urls"))` em `{{ project_name }}/urls.py` (ou `api/$ARGUMENTS/` se for DRF).
6. Mostre a estrutura criada.

Não crie models, views ou templates — deixa pro usuário definir o domínio.
