# CLAUDE.md — flowforge_open

Contexto operacional para o Claude Code neste repositório. Leia antes de qualquer mudança.

## Stack

- **Framework:** Django 5.x
- **Python:** 3.12
- **Banco:** postgresql
- **API:** Django REST Framework + drf-spectacular
- **Gerenciador:** uv


## Idioma e tom

- Respostas em **português do Brasil**.
- Direto ao ponto. Sem preâmbulo, sem "Aqui está...", sem "Espero ter ajudado".
- Quando houver tradeoff, diga qual você recomenda e por quê — em uma frase.
- Se não souber, fale que não sabe. Não invente APIs, campos ou flags.

## Comandos frequentes

```bash
# Setup
uv sync
cp .env.example .env

# Server
uv run python manage.py runserver

# Migrations (SEMPRE revise o arquivo gerado antes de aplicar)
uv run python manage.py makemigrations
uv run python manage.py migrate

# Testes
uv run pytest
uv run pytest --cov=apps --cov-report=term-missing

# Lint + format
uv run ruff check . --fix
uv run ruff format .

# Shell turbinado
uv run python manage.py shell_plus
```

## Convenções de código

- Apps em `apps/<nome>/`, **nunca** na raiz.
- Settings divididos em `flowforge_open/settings/{base,dev,prod}.py`.
- **Fat models, thin views.** Lógica de negócio em métodos do model ou em `apps/<app>/services.py`.
- Queries complexas em `managers.py` ou `querysets.py`.
- Um teste por comportamento público. Use `pytest-django`, não `TestCase`.
- DRF: `serializers.py`, `views.py`, `urls.py` em cada app. Uma `ViewSet` por recurso.
- `logging` em vez de `print`. Nunca `print` em código de produção.
- Strings de usuário sempre em `gettext_lazy` (i18n).

## Guardrails

- **Nunca** apague ou reescreva migrations existentes sem confirmação explícita. Gere uma nova.
- **Nunca** commit de `.env`, dumps, ou chaves em plain text.
- Antes de abrir PR: `ruff check .`, `ruff format .`, `pytest` — nessa ordem. Se qualquer um falhar, pare.
- Mudanças em `settings/prod.py` exigem revisão humana. Peça confirmação.
- Mudanças em `models.py` exigem migration + teste. Sem exceção.
- `ForeignKey` sempre com `on_delete=` explícito. Prefira `PROTECT` a `CASCADE` quando em dúvida.
- `ModelSerializer` com `fields = "__all__"` é proibido — liste campos explicitamente.

## Onde procurar o quê

| Preciso de... | Vai em... |
|---|---|
| Entrypoint | `manage.py` |
| Rotas globais | `flowforge_open/urls.py` |
| Config | `flowforge_open/settings/` |
| Apps | `apps/<app>/` |
| Fixtures | `apps/<app>/fixtures/` |
| Templates HTML | `templates/` |
| Estáticos | `static/` |
| Testes | `apps/<app>/tests/` |

## Agentes

Invoque com `@nome` ou deixe o Claude escolher:

- `django-reviewer` — revisa código Django contra as convenções do projeto.
- `test-engineer` — escreve/expande testes com pytest-django.
- `migration-auditor` — audita migrations antes de aplicar.
- `security-auditor` — varredura de settings, secrets, auth, CSRF, CORS.
- `api-designer` — projeta endpoints DRF, serializers e permissions.

## Comandos slash

- `/migrate` — fluxo completo de makemigrations → revisar → migrate.
- `/new-app` — cria um app Django com a estrutura padrão do projeto.
- `/test-cov` — roda a suite com cobertura e lista gaps.
- `/audit` — varredura de segurança + qualidade.
- `/seed` — popula o DB de desenvolvimento.
