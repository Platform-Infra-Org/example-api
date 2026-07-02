import sys
import os
import json
from .schemas import DNSRecordCreate, DNSRecordResponse, DNSRecordDelete
from .conf import config


async def _resolve_template_id(provider, metadata, key: str, default: int) -> int:
    """Resolve an AWX template ID from the Remote Config provider, per environment.

    The request's `metadata` carries the six coordinates (space/network/region/island/
    environment/project) the provider resolves config against, so a deployment can serve
    a different template id per environment. Falls back to the static conf default when
    the provider is disabled or the key isn't present upstream.
    """
    if provider is None:
        return default
    resolved = await provider.resolve_infra_config(metadata)
    return resolved.get(key, default)


async def create_dns(dns_record: DNSRecordCreate, awx_client, provider=None) -> DNSRecordResponse:
    template_id = await _resolve_template_id(
        provider, dns_record.metadata, "awx_create_dns_template_id", config.AWX_CREATE_DNS_TEMPLATE_ID
    )
    extra_vars_json =  {
            "RECORD_TYPE": dns_record.spec.record_type,
            "RECORD_NAME": dns_record.spec.record_name,
            "RECORD_ADDRESS": dns_record.spec.ip,
            "DNS_ZONE": dns_record.spec.dns_zone
	}
    return await awx_client.launch_job(job_template_id=template_id, extra_vars=extra_vars_json)

async def delete_dns(dns_record: DNSRecordDelete, awx_client, provider=None) -> DNSRecordResponse:
    template_id = await _resolve_template_id(
        provider, dns_record.metadata, "awx_delete_dns_template_id", config.AWX_DELETE_DNS_TEMPLATE_ID
    )
    extra_vars_json =  {
            "RECORD_TYPE": dns_record.spec.record_type,
            "RECORD_NAME": dns_record.spec.record_name,
            "DNS_ZONE": dns_record.spec.dns_zone
	}

    return await awx_client.launch_job(job_template_id=template_id, extra_vars=extra_vars_json)


def update_dns(record_name: str, ip: str) -> str:
    """Update DNS record with new IP"""
    print(f"update dns record: {record_name} with ip: {ip}")
    return "DNS record updated successfully"

def get_dns(record_name: str) -> str:
    """Get DNS record IP"""
    print(f"get dns record: {record_name}")
    return "192.168.1.1"  # Simulated IP address

async def get_dns_status(awx_job_id: int, awx_client) -> DNSRecordResponse:

    return await awx_client.get_job_status(job_id=awx_job_id)
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
        
    

