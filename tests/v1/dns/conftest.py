import os

# 32+ bytes to avoid PyJWT's short-key warning.
HS256_SECRET = "test-secret-test-secret-test-secret"

# Base settings must exist before `app.main` is imported. AUTH_ENABLED + AUTH_HS256_SECRET
# turn on the global AuthMiddleware, so these route tests send a valid bearer.
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
    "AUTH_ENABLED": "true",
    "AUTH_HS256_SECRET": HS256_SECRET,
}
for _k, _v in _BASE_ENV.items():
    os.environ.setdefault(_k, _v)

from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient

from tashtiot_apis_library import AWX
from tashtiot_apis_library.schemas import MetadataRequest

from app.v1.dns.schemas import (
    DNSRecordCreate,
    DNSRecordCreateSpec,
    DNSRecordDelete,
    DNSRecordDeleteSpec,
)


@pytest.fixture
def client(monkeypatch):
    # Mock the AWX connector so DNS create/delete/status don't hit the network.
    async def fake_launch_job(self, **kwargs):
        return {"status": "successful", "job_id": 1}

    async def fake_get_job_status(self, **kwargs):
        return {"status": "successful", "job_id": kwargs.get("job_id", 1)}

    monkeypatch.setattr(AWX, "launch_job", fake_launch_job)
    monkeypatch.setattr(AWX, "get_job_status", fake_get_job_status)

    from app.main import create_app

    return TestClient(create_app())


@pytest.fixture
def authenticated_headers():
    token = jwt.encode(
        {"sub": "dns-test", "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
        HS256_SECRET,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def metadata_request():
    return MetadataRequest(
        project="test", network="net", region="kirya", space="net", environment="test"
    )


@pytest.fixture
def create_spec():
    return DNSRecordCreateSpec(
        record_name="aln-aln-aln-1", ip="190.50.50.160", record_type="a", dns_zone="net.com"
    )


@pytest.fixture
def delete_spec():
    return DNSRecordDeleteSpec(record_name="aln-aln-aln-1", record_type="a", dns_zone="net.com")


@pytest.fixture
def valid_create_dns_record(metadata_request, create_spec):
    return DNSRecordCreate(spec=create_spec, metadata=metadata_request)


@pytest.fixture
def valid_delete_dns_record(metadata_request, delete_spec):
    return DNSRecordDelete(spec=delete_spec, metadata=metadata_request)


@pytest.fixture
def invalid_create_dns_record(metadata_request):
    # record_name exceeds the 15-char limit -> a validation error (422), never reaching AWX.
    return {
        "spec": {
            "record_name": "its-more-then-15",
            "ip": "190.50.50.160",
            "record_type": "a",
            "dns_zone": "net.com",
        },
        "metadata": metadata_request,
    }


@pytest.fixture
def invalid_delete_dns_record(metadata_request):
    return {
        "spec": {
            "record_name": "its-more-then-15",
            "record_type": "a",
            "dns_zone": "net.com",
        },
        "metadata": metadata_request,
    }
