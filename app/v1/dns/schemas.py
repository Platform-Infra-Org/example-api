from pydantic import BaseModel, Field, field_validator
from ipaddress import IPv4Address, AddressValueError
from tashtiot_apis_library.connectors.awx.models import AWXOperationResponse
from tashtiot_apis_library import InfraOperationRequest

class DNSRecordCreateSpec(BaseModel):
    record_name: str = Field(..., max_length=15)
    ip: str
    record_type: str
    dns_zone: str   

    @field_validator("ip")
    @classmethod
    def validate_ip(cls, v: str) -> str:
        """
        Ensure the supplied value is a valid IPv4 address.
        Returns the original string (so the field stays a plain ``str``).
        """
        try:
            IPv4Address(v)
        except (AddressValueError, ValueError) as exc:
            raise ValueError(f"'{v}' is not a valid IPv4 address") from exc
        return v

class DNSRecordCreate(InfraOperationRequest):
    spec: DNSRecordCreateSpec

class DNSRecordDeleteSpec(BaseModel):
    record_name: str = Field(..., max_length=15)
    record_type: str
    dns_zone: str

class DNSRecordDelete(InfraOperationRequest):
    spec: DNSRecordDeleteSpec


class DNSRecordResponse(AWXOperationResponse):
    pass

class DNSRecordUpdate(BaseModel):
    ip: str

    @field_validator("ip")
    @classmethod
    def validate_ip(cls, v: str) -> str:
        """
        Ensure the supplied value is a valid IPv4 address.
        Returns the original string (so the field stays a plain ``str``).
        """
        try:
            IPv4Address(v)
        except (AddressValueError, ValueError) as exc:
            raise ValueError(f"'{v}' is not a valid IPv4 address") from exc
        return v