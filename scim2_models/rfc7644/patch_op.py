from enum import Enum
from typing import Any
from typing import List
from typing import Optional

from pydantic import Field
from pydantic import field_validator

from ..base import ComplexAttribute
from .message import Message


class PatchOperation(ComplexAttribute):
    class Op(str, Enum):
        replace = "replace"
        remove = "remove"
        add = "add"

    op: Op
    """Each PATCH operation object MUST have exactly one "op" member, whose
    value indicates the operation to perform and MAY be one of "add", "remove",
    or "replace"."""

    path: Optional[str] = None
    """The "path" attribute value is a String containing an attribute path
    describing the target of the operation."""

    value: Optional[Any] = None

    @field_validator("op", mode="before")
    @classmethod
    def normalize_op(cls, v):
        if isinstance(v, str):
            return v.lower()
        return v


class PatchOp(Message):
    """Patch Operation as defined in :rfc:`RFC7644 §3.5.2
    <7644#section-3.5.2>`.

    .. todo::

        The models for Patch operations are defined, but their behavior is not implemented nor tested yet.
    """

    schemas: List[str] = ["urn:ietf:params:scim:api:messages:2.0:PatchOp"]

    operations: List[PatchOperation] = Field(None, serialization_alias="Operations")
    """The body of an HTTP PATCH request MUST contain the attribute
    "Operations", whose value is an array of one or more PATCH operations."""
