# example-api

A worked example of a FastAPI service built on the internal **`tashtiot-apis-library`**.
It exposes versioned endpoints (`/api/example/v1/...`) that orchestrate infrastructure
operations against external systems, and doubles as the **reference for building a new API**
on the library: connector injection, layered config, inbound/outbound SSO, and the Remote
Config provider are all demonstrated here with real, runnable code.

If you are standing up a new service on `tashtiot-apis-library`, read this top to bottom and
copy the patterns from the module that matches your integration (`dns`, `chat`, `haproxy`,
`auth_demo`).

---

## Quick start

```bash
# Requires a uv.toml pointing at the internal Artifactory index (see below).
uv sync                   # install deps (incl. tashtiot-apis-library) into .venv

cp .env.example .env      # then fill in the values you need
uv run python -m app.main # serves on 0.0.0.0:5000  (app factory: app/main.py:create_app)
```

### Package index (`uv.toml`)

`tashtiot-apis-library` is served from the internal Artifactory, not public PyPI, so `uv` needs to
know that index. That's configured in a **`uv.toml`** — the uv equivalent of the old `pip.ini`
(it defines the Artifactory indexes and `system-certs = true`). Place it in one of:

- **the repo root** (next to `pyproject.toml`) — applies to this project only; or
- **`~/.config/uv/uv.toml`** (`%APPDATA%\uv\uv.toml` on Windows) — shared across all your uv
  projects. A repo-root `uv.toml` wins if both exist.

The index URLs embed an Artifactory `user:token`, so **do not commit `uv.toml`** — keep it local.
It also sets `index-strategy = "unsafe-best-match"` so uv can find the pinned dev tools, which live
on the secondary index (both indexes are the same trusted Artifactory).

`uv.lock` **is** committed (pins exact versions for reproducible installs). Regenerate it with
`uv lock` in an environment with full Artifactory access whenever dependencies change.

- Swagger UI: <http://localhost:5000/docs>
- Prometheus metrics: <http://localhost:5000/metrics>

Both are provided for free by the library's `general_create_app()` — you don't wire them.

The **app version** shown in the Swagger UI comes from the `APP_VERSION` env var (default `v1.0.0`).
CI passes the release tag when building the image (the `.woodpecker` kaniko step sets
`build_args: APP_VERSION=${CI_COMMIT_TAG}`); the Dockerfile bakes it into `ENV APP_VERSION`.

```bash
# Tests (Python 3.12)
uv run pytest                       # everything under tests/
uv run pytest tests/v1/auth_demo -v # one module
```

> The old `README` documented a `uvicorn main:app` command and a `v2/`/`fqdn/`/`metadata.py`
> tree that never existed. The correct entrypoint is `python -m app.main`; the real tree is
> below.

---

## How the library is used

### 1. The application factory (`app/main.py`)

`create_app()` is the single wiring point. It:

1. calls `general_create_app()` — the library's factory that returns a `FastAPI` app already
   fitted with logging, Prometheus metrics (`/metrics`), OpenAPI docs (`/docs`), and a
   startup/shutdown lifespan that launches any registered background tasks;
2. constructs each external **connector** once (`AWX`, `Git`, `ArgoCD`, `Vault`, `BaseAPI`);
3. injects those connectors into per-module **router factories** and mounts them with
   `app.include_router(get_*_router(deps))`.

Connectors are built here, once — never per-request. To add a service, build its client and
include its router in this function.

```python
def create_app() -> FastAPI:
    app = general_create_app()
    awx_client = AWX(global_config.AWX_URL, global_config.AWX_TOKEN)
    app.include_router(get_v1_dns_router(awx_client))
    ...
    return app
```

### 2. Two-layer configuration (pydantic-settings, from `.env`)

All config is `pydantic-settings` `BaseSettings`, sourced from environment / `.env`:

- **`app/global_conf.py`** — cross-cutting settings shared by the whole app
  (`ARGOCD_*`, `VAULT_*`, `AWX_*`, `CHAT_*`, `TEAM_NAME`, `CONFIG_API_*`). Singleton
  `global_config`.
- **`app/v1/<service>/conf.py`** — one `BaseSettings` per module, including that router's
  `API_PREFIX` and `API_TAGS`. Singleton `config`.

Auth settings (`AUTH_*`, `AUTH_SSO_*`, `CONFIG_REMOTE_*`) are **not** declared in these files —
the library owns those and reads them straight from the environment. You only add app-specific
knobs.

### 3. The per-module layout (4 files)

Every service under `app/v1/<service>/` follows the same split:

| File | Responsibility |
|------|----------------|
| `conf.py` | the module's `BaseSettings` + `config` singleton (`API_PREFIX`, `API_TAGS`, …) |
| `schemas.py` | pydantic request/response models (subclass library base models where relevant) |
| `operations.py` | business logic; functions receive injected connectors as arguments |
| `routes.py` | a `get_*_router(deps) -> APIRouter` factory using `prefix=config.API_PREFIX` |

The router factory is the injection seam: connectors are captured as closure variables and
passed into the operation functions — there is no FastAPI `Depends` for connectors.

### 4. Integration patterns

- **Proxy** (`dns`, `chat`, `auth_demo`) — thin async wrappers that forward to an external
  service and return its response.
- **GitOps** (`haproxy`) — writes YAML to Git + secrets to Vault, then triggers an ArgoCD sync
  in a fire-and-forget background task; the immediate response is `InProgress` and callers poll
  `/status`. Rollback is hand-rolled in `except` blocks (no transaction) — preserve the
  rollback symmetry when editing.

---

## Authentication

### Inbound SSO — global, protecting the whole API

The app is created with `general_create_app(enable_auth=True)`, which wires the library's
**global `AuthMiddleware` over every route** (except `/docs`, `/metrics`, `/health`,
`/openapi.json`, `/static`, probes). It activates only when **both**:

1. `AUTH_ENABLED=true` (the master switch), and
2. exactly one verification material is set:

| Mode | Settings |
|------|----------|
| Symmetric HS256 | `AUTH_HS256_SECRET` |
| RS256 via JWKS | `AUTH_JWKS_URL` (or `AUTH_OIDC_ISSUER` for discovery) |
| Offline RS256 | `AUTH_PUBLIC_KEY_PEM` / `AUTH_PUBLIC_KEY_PATH` |

With `AUTH_ENABLED` off, the app boots **open** (dev mode). Turning it on with no material set
fails app creation (fail-fast). Optionally enforce `AUTH_AUDIENCE` / `AUTH_ISSUER`.

The middleware verifies the `Authorization: Bearer` token, sets the claims on
`request.state.user`, and 401s on a missing/invalid token. A route reads the verified identity
with the library's `get_current_claims` — this is all `auth_demo`'s `/whoami` does:

```python
from tashtiot_apis_library.fastapi_template.auth import get_current_claims

@router.get("/whoami")
def whoami(claims: dict = Depends(get_current_claims)):   # 401 if no verified identity
    return {"subject": claims["sub"], "claims": claims}
```

> Only need one route protected, not the whole app? Skip `enable_auth` and instead call
> `verify_token(token)` (same module) inside a per-route dependency.

### Outbound SSO — call a downstream API as a service

`GET /api/example/v1/auth_demo/downstream` calls another service using an OAuth2
`client_credentials` bearer that the library mints, caches, and refreshes for you:

```python
from tashtiot_apis_library.fastapi_template.security import sso_authenticated_api

async with sso_authenticated_api(config.DOWNSTREAM_API_URL) as client:
    response = await client.get(config.DOWNSTREAM_ENDPOINT)   # Authorization: Bearer <token> added
```

`sso_authenticated_api` returns a `BaseAPI` async client that reads the `AUTH_SSO_*` env vars
(`AUTH_SSO_TOKEN_URL`, `AUTH_SSO_CLIENT_ID`, `AUTH_SSO_CLIENT_SECRET`, plus optional
`AUTH_SSO_SCOPE` / `AUTH_SSO_AUDIENCE` / `AUTH_SSO_AUTH_STYLE`). If they're missing, building the
client raises `AuthConfigError` — the operation catches it and returns a clean `auth_failed`
result instead of a 500.

---

## Remote Config provider (consumed by DNS)

`enable_remote_config_api` wires an **authenticated, cached proxy to an upstream Config API**
(the sibling `config-api` service) that resolves hierarchical infrastructure config from a set of
**coordinates** (`space`, `network`, `region`, `island`, `environment`, `project`).

Wiring is **opt-in**: it's only enabled when `CONFIG_API_URL` is set (enabling it resolves the
outbound auth eagerly, and the default `sso` method with no credentials would otherwise crash app
creation). `create_app()` guards it and injects the returned `provider` into the DNS router:

```python
provider = None
if global_config.CONFIG_API_URL:
    try:
        provider = enable_remote_config_api(
            app,
            base_url=global_config.CONFIG_API_URL,
            remote_prefix=global_config.CONFIG_API_REMOTE_PREFIX,   # e.g. /api/v1
            coordinate_paths=[f"{dns_config.API_PREFIX}/"],
            enable_polling=False,
        )
    except AuthConfigError as exc:
        logger.warning(f"Remote Config provider not enabled: {exc}")
app.include_router(get_v1_dns_router(awx_client, provider))
```

**The existing DNS routes consume it** — no dedicated config route. A DNS create/delete request
already carries the six coordinates via `OperationRequest.metadata`, so the operation resolves the
right AWX template id per environment, falling back to the static conf default when the provider is
disabled:

```python
async def create_dns(dns_record, awx_client, provider=None):
    template_id = config.AWX_CREATE_DNS_TEMPLATE_ID
    if provider is not None:
        resolved = await provider.resolve_infra_config(dns_record.metadata)  # keyed on coordinates
        template_id = resolved.get("awx_create_dns_template_id", template_id)
    return await awx_client.launch_job(job_template_id=template_id, extra_vars=...)
```

Outbound auth to the upstream is selectable via `CONFIG_REMOTE_*` env vars —
`CONFIG_REMOTE_AUTH_METHOD` picks `sso` (OAuth2 client_credentials), `bearer` (a static token),
or `none` (use `none` for local dev). See `.env.example`.

---

## Project structure

```
app/
  main.py            # create_app(): the wiring point (connectors + routers)
  global_conf.py     # shared BaseSettings (global_config)
  helpers.py         # GitOps helpers (app-name encoding, payload parsing, secret filtering)
  v1/
    dns/             # proxy -> AWX job templates; template ids resolved from Remote Config
    chat/            # proxy -> chat API (BaseAPI client)
    haproxy/         # GitOps: Git + Vault + ArgoCD sync (background task)
    auth_demo/       # inbound SSO (/whoami) + outbound SSO client (/downstream)
tests/               # pytest; per-module suites under tests/v1/<service>/
```

Each `v1/<service>/` holds the four files described in **The per-module layout** above.

---

## Configuration reference

Copy `.env.example` to `.env`. Grouped highlights:

- **Connectors** — `ARGOCD_*`, `VAULT_*`, `AWX_*`, `CHAT_*`, `HAPROXY_*`, `TEAM_NAME`, `CLUSTERS`.
- **Inbound auth** — `AUTH_ENABLED` (master switch) plus one of `AUTH_HS256_SECRET` /
  `AUTH_JWKS_URL` / `AUTH_PUBLIC_KEY_*`, and optional `AUTH_AUDIENCE` / `AUTH_ISSUER`.
- **Outbound SSO** — `AUTH_SSO_TOKEN_URL`, `AUTH_SSO_CLIENT_ID`, `AUTH_SSO_CLIENT_SECRET`
  (+ `AUTH_SSO_SCOPE` / `AUTH_SSO_AUDIENCE` / `AUTH_SSO_AUTH_STYLE`), and the `DOWNSTREAM_*` target.
- **Remote Config** — `CONFIG_API_URL`, `CONFIG_API_REMOTE_PREFIX`, and `CONFIG_REMOTE_*` for the
  upstream auth method.

Requires `tashtiot-apis-library >= 1.1.0`.

---

## Docker

```bash
docker build -t example-api .
docker run -p 5000:5000 --env-file .env example-api
```

CI (`.woodpecker/build.yaml`) builds and pushes the image on git **tags**.
