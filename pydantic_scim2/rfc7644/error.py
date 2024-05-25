from typing import List
from typing import Optional

from pydantic import field_serializer

from ..base import SCIM2Model


class Error(SCIM2Model):
    schemas: List[str] = ["urn:ietf:params:scim:api:messages:2.0:Error"]

    status: int
    """The HTTP status code (see Section 6 of [RFC7231]) expressed as a JSON
    string."""

    @field_serializer("status")
    def serialize_int_to_string(status: int):
        return str(status)

    scim_type: Optional[str] = None
    """A SCIM detail error keyword."""

    detail: Optional[str] = None
    """A detailed human-readable message."""

    @classmethod
    def not_found(cls, detail: str = "Not found") -> "Error":
        return cls(detail=detail, status=404)

    @classmethod
    def conflict(cls, detail: str = "Conflict") -> "Error":
        return cls(detail=detail, status=409)

    @classmethod
    def unprocessable(cls, detail: str = "Unprocessable Entity") -> "Error":
        return cls(detail=detail, status=422)
