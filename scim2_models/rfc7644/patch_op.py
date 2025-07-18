from enum import Enum
from typing import Annotated
from typing import Any
from typing import Generic
from typing import Optional

from pydantic import Field
from pydantic import field_validator
from pydantic import model_validator
from typing_extensions import Self

from ..annotations import Mutability
from ..annotations import Required
from ..attributes import ComplexAttribute
from ..base import BaseModel
from ..rfc7643.resource import AnyResource
from ..utils import extract_field_name
from ..utils import validate_scim_path_syntax
from .error import Error
from .message import Message
from .message import get_resource_class


class PatchOperation(ComplexAttribute):
    class Op(str, Enum):
        replace_ = "replace"
        remove = "remove"
        add = "add"

    op: Op
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

    @field_validator("path")
    @classmethod
    def validate_path_syntax(cls, v: Optional[str]) -> Optional[str]:
        """Validate path syntax according to RFC 7644 ABNF grammar (simplified)."""
        if v is None:
            return v

        # RFC 7644 Section 3.5.2: Path syntax validation according to ABNF grammar
        if not validate_scim_path_syntax(v):
            raise ValueError(Error.make_invalid_path_error().detail)

        return v

    def _validate_mutability(
        self, resource_class: type[BaseModel], field_name: str
    ) -> None:
        """Validate mutability constraints."""
        # RFC 7644 Section 3.5.2: Servers should be tolerant of schema extensions
        if field_name not in resource_class.model_fields:
            return

        mutability = resource_class.get_field_annotation(field_name, Mutability)

        # RFC 7643 Section 7: Attributes with mutability "readOnly" SHALL NOT be modified
        if mutability == Mutability.read_only:
            if self.op in (PatchOperation.Op.add, PatchOperation.Op.replace_):
                raise ValueError(Error.make_mutability_error().detail)

        # RFC 7643 Section 7: Attributes with mutability "immutable" SHALL NOT be updated
        elif mutability == Mutability.immutable:
            if self.op == PatchOperation.Op.replace_:
                raise ValueError(Error.make_mutability_error().detail)

    def _validate_required_attribute(
        self, resource_class: type[BaseModel], field_name: str
    ) -> None:
        """Validate required attribute constraints for remove operations."""
        # RFC 7644 Section 3.5.2.3: Only validate for remove operations
        if self.op != PatchOperation.Op.remove:
            return

        # RFC 7644 Section 3.5.2: Servers should be tolerant of schema extensions
        if field_name not in resource_class.model_fields:
            return

        required = resource_class.get_field_annotation(field_name, Required)

        # RFC 7643 Section 7: Required attributes SHALL NOT be removed
        if required == Required.true:
            raise ValueError(Error.make_invalid_value_error().detail)

    @model_validator(mode="after")
    def validate_operation_requirements(self) -> Self:
        """Validate operation requirements according to RFC 7644."""
        # RFC 7644 Section 3.5.2.3: Path is required for remove operations
        if self.path is None and self.op == PatchOperation.Op.remove:
            raise ValueError(Error.make_invalid_value_error().detail)

        # RFC 7644 Section 3.5.2.1: Value is required for "add" operations
        if self.op == PatchOperation.Op.add and self.value is None:
            raise ValueError(Error.make_invalid_value_error().detail)

        return self

    value: Optional[Any] = None

    @field_validator("op", mode="before")
    @classmethod
    def normalize_op(cls, v: Any) -> Any:
        """Ignore case for op.

        This brings
        `compatibility with Microsoft Entra <https://learn.microsoft.com/en-us/entra/identity/app-provisioning/use-scim-to-provision-users-and-groups#general>`_:

        Don't require a case-sensitive match on structural elements in SCIM,
        in particular PATCH op operation values, as defined in section 3.5.2.
        Microsoft Entra ID emits the values of op as Add, Replace, and Remove.
        """
        if isinstance(v, str):
            return v.lower()
        return v


class PatchOp(Message, Generic[AnyResource]):
    """Patch Operation as defined in :rfc:`RFC7644 §3.5.2 <7644#section-3.5.2>`."""

    schemas: Annotated[list[str], Required.true] = [
        "urn:ietf:params:scim:api:messages:2.0:PatchOp"
    ]

    operations: Annotated[Optional[list[PatchOperation]], Required.true] = Field(
        None, serialization_alias="Operations", min_length=1
    )
    """The body of an HTTP PATCH request MUST contain the attribute
    "Operations", whose value is an array of one or more PATCH operations."""

    @model_validator(mode="after")
    def validate_operations(self) -> Self:
        """Validate operations against resource type metadata if available.

        When PatchOp is used with a specific resource type (e.g., PatchOp[User]),
        this validator will automatically check mutability and required constraints.
        """
        resource_class = get_resource_class(self)
        if resource_class is None or not self.operations:
            return self

        for operation in self.operations:
            if operation.path is None:
                continue

            field_name = extract_field_name(operation.path)
            if field_name is None:
                continue

            operation._validate_mutability(resource_class, field_name)
            operation._validate_required_attribute(resource_class, field_name)

        return self
