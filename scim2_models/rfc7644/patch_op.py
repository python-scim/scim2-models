from enum import Enum
from typing import Any
from typing import List
from typing import Optional

from pydantic import Field

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


class PatchOp(Message):
    schemas: List[str] = ["urn:ietf:params:scim:api:messages:2.0:PatchOp"]

    operations: List[PatchOperation] = Field(None, alias="Operations")
    """The body of an HTTP PATCH request MUST contain the attribute
    "Operations", whose value is an array of one or more PATCH operations."""
