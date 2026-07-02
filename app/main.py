from fastapi import FastAPI
from loguru import logger
from .v1.dns.routes import get_v1_dns_router
from .global_conf import global_config
import uvicorn
from tashtiot_apis_library.fastapi_template.utils import BaseAPI
from tashtiot_apis_library import general_create_app, Git, ArgoCD, Vault, AWX
from tashtiot_apis_library.fastapi_template import enable_remote_config_api
from tashtiot_apis_library.fastapi_template.errors import AuthConfigError
from .v1.haproxy.conf import config as ha_proxy_config
from .v1.haproxy.routes import get_router
from .v1.chat.routes import get_v1_chat_router
from .v1.auth_demo.routes import get_v1_auth_demo_router
from .v1.dns.conf import config as dns_config

def create_app() -> FastAPI:
    # enable_auth wires the library's global AuthMiddleware, which protects every route
    # (except docs/metrics/health/probes). It only activates when AUTH_ENABLED=true and one
    # AUTH_* verification material is set; otherwise the app boots open. See README.
    app = general_create_app(enable_auth=True)
    
    # Configure external services objects
    chat_client = BaseAPI(global_config.CHAT_API_URL, headers={"x-api-token": global_config.CHAT_API_TOKEN}).client
    awx_client = AWX(global_config.AWX_URL, global_config.AWX_TOKEN)
    git = Git(base_url=ha_proxy_config.HAPROXY_VALUES_REPO_URL,token=ha_proxy_config.HAPROXY_VALUES_REPO_ACCESS_TOKEN, username_or_email=ha_proxy_config.HAPROXY_VALUES_REPO_EMAIL, project_key=ha_proxy_config.HAPROXY_REPO_PROJECT_KEY, repo_slug=ha_proxy_config.HAPROXY_VALUES_REPO_SLUG, default_ref="master", ssh_key_file_path=ha_proxy_config.HAPROXY_VALUES_REPO_SSH_KEY_PATH)
    argocd = ArgoCD(global_config.ARGOCD_URL, global_config.ARGOCD_TOKEN, global_config.APPLICATION_SET_TIMEOUT)
    vault = Vault(global_config.VAULT_URL, global_config.VAULT_TOKEN)
    
    # Remote Config provider: opt-in. Only wire it when an upstream is configured — enabling
    # it resolves outbound auth eagerly, so an unconfigured method ('sso' by default) would
    # otherwise crash app creation. When disabled, DNS falls back to its static conf template
    # ids. enable_polling=False: no coordinate query-param route remains to drive the OpenAPI
    # enum dropdowns, so the allowlist poller has nothing to refresh.
    provider = None
    if global_config.CONFIG_API_URL:
        try:
            provider = enable_remote_config_api(
                app,
                base_url=global_config.CONFIG_API_URL,
                remote_prefix=global_config.CONFIG_API_REMOTE_PREFIX,
                config_path=f"{dns_config.API_PREFIX}/",
                naming_path=f"{dns_config.API_PREFIX}/",
                enable_polling=False,
            )
        except AuthConfigError as exc:
            logger.warning(f"Remote Config provider not enabled (auth misconfigured): {exc}")

    # Add routes to app
    app.include_router(get_router(git=git, argocd=argocd, vault=vault))

    # DNS: create/delete resolve their AWX template ids from the provider (keyed on the
    # request's metadata coordinates), falling back to static conf when provider is None.
    app.include_router(get_v1_dns_router(awx_client, provider))

    app.include_router(get_v1_chat_router(chat_client))

    # Auth showcase: /whoami echoes the globally-verified caller identity; /downstream calls
    # a downstream API with an outbound SSO bearer built per-request inside the operation.
    app.include_router(get_v1_auth_demo_router())

    return app

if __name__ == "__main__":
	app = create_app()
    
	uvicorn.run(app, host="0.0.0.0", port=5000)
