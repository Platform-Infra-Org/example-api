# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A FastAPI service exposing versioned (`/api/example/v1/...`) endpoints that orchestrate
infrastructure operations (DNS records, HAProxy deployments, chat notifications) against
external systems. It is a thin API layer over the internal `tashtiot-apis-library`, which
provides the base app and the connector clients (`Git`, `ArgoCD`, `Vault`, `AWX`, `BaseAPI`).

## Commands

The project is uv-managed (Python 3.12; see `.python-version`). Package indexes come from
`uv.toml` (the internal Artifactory; the uv equivalent of `pip.ini`).

```bash
# Install deps into .venv (requires a uv.toml with the Artifactory index — see README)
uv sync --group dev

# Run the server (app factory lives in app/main.py:create_app)
uv run python -m app.main           # serves on 0.0.0.0:5000

# Tests (Python 3.12)
uv run pytest                       # runs everything under tests/
uv run pytest tests/v1/auth_demo    # one module
uv run pytest tests/v1/auth_demo/test_auth_demo_routes.py::test_whoami_requires_token   # single test
```

Docs at `http://localhost:5000/docs`, Prometheus metrics at `/metrics` (both provided by the library's `general_create_app`).

## Architecture

**App composition (`app/main.py`).** `create_app()` is the single wiring point: it instantiates
each external connector from config, then injects them into per-module router factories via
`app.include_router(get_*_router(deps))`. Connectors are constructed once here, not per-request —
add new services by building the client and including its router here.

**Config is two-layered, all sourced from `.env`** (pydantic-settings `BaseSettings`):
- `app/global_conf.py` — shared/cross-cutting settings (`ARGOCD_*`, `VAULT_*`, `AWX_*`, `CHAT_*`, `TEAM_NAME`).
- `app/v{n}/<service>/conf.py` — per-module settings including each router's `API_PREFIX` and `API_TAGS`.

**Per-module layout** (`app/v1/<service>/`): every service follows the same four-file split:
- `conf.py` — module's `BaseSettings` (`config = ...` singleton).
- `schemas.py` — pydantic request/response models. Resource schemas subclass library base
  models (`OperationRequest`, `DefaultMetaSpec`, `ResourceSpec`, `NameNamespace`, `AWXOperationResponse`).
- `operations.py` / `operation_*.py` — business logic; functions receive injected connectors as args.
- `routes.py` — a `get_*_router(deps) -> APIRouter` factory using `prefix=config.API_PREFIX`.

**Two integration patterns coexist:**
- *Proxy services* (`dns`, `chat`) — routes are thin async wrappers that forward to an external
  service (AWX job templates by ID, or the chat API) and return its response.
- *GitOps service* (`haproxy`) — the complex one. A create/update/delete writes a values YAML
  file to a Git repo and secrets to Vault, then triggers an ArgoCD sync **in a fire-and-forget
  `asyncio.create_task` background task**. The immediate HTTP response is `status="InProgress"`;
  callers poll the `/status` endpoint. There is **no transaction** — each operation hand-rolls
  rollback (delete the git file / restore the previous secret) in `except` blocks, both inline
  and inside the background task. When editing these flows, preserve the rollback symmetry.

**Shared helpers (`app/helpers.py`).** `build_app_name`/`break_app_name` encode the ArgoCD app
naming convention (`{cluster}-{namespace}-{resource}-{name}`). `parse_payload` turns a request
payload into `(git_path, yaml, cluster, namespace, name, secrets)`. `filter_secret_payload`
strips empty values so Vault never gets blank writes. `yaml_data_equals` does order-insensitive
YAML comparison (used to skip no-op git commits on update).

## Auth & config provider

- **Inbound auth is global.** `create_app()` calls `general_create_app(enable_auth=True)`, wiring the
  library's `AuthMiddleware` over every route. It activates only when `AUTH_ENABLED=true` **and** one
  `AUTH_*` verification material is set (HS256 / JWKS / local pubkey); otherwise the app boots open.
  `auth_demo`'s `/whoami` reads the verified claims via the library's `get_current_claims`.
- **DNS consumes the Remote Config provider.** When `CONFIG_API_URL` is set, `create_app()` wires
  `enable_remote_config_api` and passes the provider into the DNS router. `create_dns`/`delete_dns`
  resolve their AWX template ids from `provider.resolve_infra_config(record.metadata)` (keyed on the
  six coordinates the request already carries), falling back to the static `dns/conf.py` ids when the
  provider is disabled or the key is absent.

## uv / packaging notes

- uv-managed, Python 3.12. `uv.lock` is committed (un-ignored); regenerate with `uv lock` in an
  environment with **full Artifactory access** — the local mirror is missing some packages
  (`aiocache`, pinned pytest versions), so `uv sync` there needs a public-PyPI fallback.
- `uv.toml` (untracked, holds the Artifactory index + creds) carries `index-strategy =
  "unsafe-best-match"` because the pinned dev tools live on the secondary index. When both a `uv.toml`
  and a `[tool.uv]` section exist, uv.toml wins — so uv settings go there, not in `pyproject.toml`.
- Known gap: `[tool.uv.sources]` points `tashtiot-apis-library` at the local `../apis-library`
  editable path (intentional for local dev; the published build lags). That path won't resolve in
  Docker/CI — those need the Artifactory-published `>=1.1.0`.
- Remaining P2 uv improvements (not yet applied): switch the Dockerfile to `COPY --from=ghcr.io/
  astral-sh/uv /uv /bin/uv`; add a `uv sync --frozen && uv run pytest` step to `.woodpecker`
  (test steps are currently commented out); keep `uv.toml` creds in `UV_INDEX_*` env, not plaintext.

## Notes

- `ExternalServiceError` from the library is the expected failure mode in routes; it is caught and
  mapped to a `502` `ArgoOperationResponse`. (Note: route handlers reference `http_status` for that
  status code but several files don't import it — verify imports when touching error paths.)
- Test suites (all `app.`-prefixed imports, `pythonpath = ["."]`): `tests/v1/auth_demo`,
  `tests/v1/dns` (route tests mock the AWX connector + send a valid bearer, since auth is global),
  and `tests/v1/dns_config` (provider template-id resolution). The old `tests/v1/fqdn` /
  `tests/v2/dns` scaffolding was removed — it tested `fqdn`/`v2` modules that never existed.
- CI (`.woodpecker/build.yaml`) only builds and pushes the image on git **tags**; tests/Sonar steps are disabled.
