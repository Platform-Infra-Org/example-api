"""Rollback must restore the secret's original key/values, at the path create/delete use."""

import asyncio

import pytest
from tashtiot_apis_library.connectors.vault.models import VaultSecret

from app.v1.haproxy.operations import delete_haproxy_operation, update_haproxy_operation
from app.v1.haproxy.schemas import HaProxyIdentifier, HaProxySpec

ORIGINAL = {"sheker_secret": "original-value"}
SECRET_PATH = "/perimeter/haproxy/dev/team-ns/edge"  # .../{cluster}/{namespace}/{name}


class FakeVault:
    def __init__(self, fail_write=False):
        self.fail_write = fail_write
        self.writes = []

    async def read_secret(self, path):
        assert path == SECRET_PATH
        # Same shape the real connector returns: values on .data, KV metadata alongside.
        return VaultSecret(data=dict(ORIGINAL), metadata={"version": 3})

    async def write_secret(self, path, data):
        if self.fail_write and not self.writes:
            self.writes.append(("failed", path, data))
            raise RuntimeError("vault write failed")
        self.writes.append(("ok", path, data))

    async def delete_secret(self, path):
        pass


class FakeGit:
    async def get_file_content(self, path):
        return "backends: []\n"

    async def modify_file(self, *args, **kwargs):
        pass

    async def delete_file(self, *args, **kwargs):
        pass

    async def add_file(self, *args, **kwargs):
        pass


class FailingArgo:
    async def wait_for_app_deletion(self, app_name):
        raise RuntimeError("argo timed out")


def _spec():
    return HaProxySpec.model_validate(
        {
            "metadata": {
                "cluster": "dev",
                "namespace": "team-ns",
                "name": "edge",
                "version": "1.0.0",
                "paasLabels": {
                    "operational_purpose": "test",
                    "operational": True,
                    "critical": False,
                },
            },
            "values": {"backends": ["b1"]},
            "secrets": {"sheker_secret": "new-value"},
        }
    )


async def test_update_rollback_restores_original_secret_values():
    vault = FakeVault(fail_write=True)

    with pytest.raises(RuntimeError):
        await update_haproxy_operation(git=FakeGit(), vault=vault, argocd=None, payload=_spec())

    _, path, restored = vault.writes[-1]
    assert path == SECRET_PATH
    assert restored == ORIGINAL  # the plain key/values, not {"data": ..., "metadata": ...}


async def test_delete_rollback_restores_original_secret_values():
    vault = FakeVault()
    params = HaProxyIdentifier(cluster="dev", namespace="team-ns", name="edge")

    await delete_haproxy_operation(git=FakeGit(), vault=vault, argocd=FailingArgo(), params=params)
    for _ in range(5):  # let the fire-and-forget background rollback run
        await asyncio.sleep(0)

    assert vault.writes == [("ok", SECRET_PATH, ORIGINAL)]
