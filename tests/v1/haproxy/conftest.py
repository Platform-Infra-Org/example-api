import os

# The haproxy settings singletons are built at import time, so the required values must be in the
# environment before app.v1.haproxy is imported.
_BASE_ENV = {
    "ARGOCD_URL": "https://argo.test",
    "ARGOCD_TOKEN": "x",
    "VAULT_URL": "https://vault.test",
    "VAULT_TOKEN": "x",
    "TEAM_NAME": "test-team",
    "CLUSTERS": '["dev"]',
    "HAPROXY_VALUES_REPO_URL": "https://git.test",
    "HAPROXY_VALUES_REPO_ACCESS_TOKEN": "x",
    "HAPROXY_VALUES_REPO_EMAIL": "svc@test",
    "HAPROXY_REPO_PROJECT_KEY": "dev",
    "HAPROXY_VALUES_REPO_SLUG": "haproxy-values",
    "HAPROXY_VALUES_REPO_SSH_KEY_PATH": "/tmp/key",
}
for _k, _v in _BASE_ENV.items():
    os.environ.setdefault(_k, _v)
