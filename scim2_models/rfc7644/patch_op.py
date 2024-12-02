from enum import Enum
from typing import Annotated
from typing import Any
from typing import Optional

from pydantic import Field
from pydantic import field_validator

from ..base import ComplexAttribute
from ..base import Required
from .message import Message


class PatchOperation(ComplexAttribute):
    class Op(str, Enum):
        replace_ = "replace"
        remove = "remove"
        add = "add"

    op: Optional[Optional[Op]] = None
    """Each PATCH operation object MUST have exactly one "op" member, whose
    value indicates the operation to perform and MAY be one of "add", "remove",
    or "replace".

    .. note::

        For the sake of compatibility with Microsoft Entra,
        despite :rfc:`RFC7644 §3.5.2 <7644#section-3.5.2>`, op is case-insensitive.
    """

    path: Optional[str] = None
    """The "path" attribute value is a String containing an attribute path
    describing the target of the operation."""

    value: Optional[Any] = None

    @field_validator("op", mode="before")
    @classmethod
    def normalize_op(cls, v):
        """Ignorecase for op.

        This brings
        `compatibility with Microsoft Entra <https://learn.microsoft.com/en-us/entra/identity/app-provisioning/use-scim-to-provision-users-and-groups#general>`_:

        Don't require a case-sensitive match on structural elements in SCIM,
        in particular PATCH op operation values, as defined in section 3.5.2.
        Microsoft Entra ID emits the values of op as Add, Replace, and Remove.
        """
        if isinstance(v, str):
            return v.lower()
        return v


class PatchOp(Message):
    """Patch Operation as defined in :rfc:`RFC7644 §3.5.2 <7644#section-3.5.2>`.

    .. todo::

        The models for Patch operations are defined, but their behavior is not implemented nor tested yet.
    """

    schemas: Annotated[list[str], Required.true] = [
        "urn:ietf:params:scim:api:messages:2.0:PatchOp"
    ]

    operations: Optional[list[PatchOperation]] = Field(
        None, serialization_alias="Operations"
    )
    """The body of an HTTP PATCH request MUST contain the attribute
    "Operations", whose value is an array of one or more PATCH operations."""
