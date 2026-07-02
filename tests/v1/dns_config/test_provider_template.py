"""DNS template-id resolution from the Remote Config provider (with fallback).

Unit-level: the operation only reads `dns_record.metadata` + `dns_record.spec` and calls
`awx_client.launch_job`, so we duck-type both and assert which template id is used.
"""
import types

from app.v1.dns.conf import config
from app.v1.dns.operation_dns import create_dns, delete_dns


class FakeAWX:
    def __init__(self):
        self.kwargs = None

    async def launch_job(self, **kwargs):
        self.kwargs = kwargs
        return {"job_id": 1}


class FakeProvider:
    def __init__(self, cfg):
        self._cfg = cfg

    async def resolve_infra_config(self, metadata):
        return self._cfg


def _record():
    return types.SimpleNamespace(
        metadata=types.SimpleNamespace(
            space=None, network=None, region=None, island=None, environment="prod", project="p"
        ),
        spec=types.SimpleNamespace(record_type="A", record_name="x", ip="1.2.3.4", dns_zone="z"),
    )


async def test_create_uses_provider_template_id():
    awx = FakeAWX()
    await create_dns(_record(), awx, FakeProvider({"awx_create_dns_template_id": 9999}))
    assert awx.kwargs["job_template_id"] == 9999


async def test_delete_uses_provider_template_id():
    awx = FakeAWX()
    await delete_dns(_record(), awx, FakeProvider({"awx_delete_dns_template_id": 8888}))
    assert awx.kwargs["job_template_id"] == 8888


async def test_falls_back_to_conf_when_provider_disabled():
    awx = FakeAWX()
    await create_dns(_record(), awx, None)
    assert awx.kwargs["job_template_id"] == config.AWX_CREATE_DNS_TEMPLATE_ID


async def test_falls_back_to_conf_when_key_absent():
    awx = FakeAWX()
    await create_dns(_record(), awx, FakeProvider({}))
    assert awx.kwargs["job_template_id"] == config.AWX_CREATE_DNS_TEMPLATE_ID
