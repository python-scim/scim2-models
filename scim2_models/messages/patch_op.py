from enum import Enum
from inspect import isclass
from typing import Annotated
from typing import Any
from typing import Generic
from typing import TypeVar

from pydantic import BaseModel as PydanticBaseModel
from pydantic import Field
from pydantic import ValidationInfo
from pydantic import field_validator
from pydantic import model_validator
from typing_extensions import Self

from ..annotations import Mutability
from ..annotations import Required
from ..attributes import ComplexAttribute
from ..context import Context
from ..exceptions import InvalidValueException
from ..exceptions import MutabilityException
from ..exceptions import NoTargetException
from ..path import URN
from ..path import Path
from ..resources.resource import Resource
from .message import Message
from .message import _get_resource_class

ResourceT = TypeVar("ResourceT", bound=Resource[Any])


class PatchOperation(ComplexAttribute, Generic[ResourceT]):
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

    path: Path[ResourceT] | None = None
    """The "path" attribute value is a String containing an attribute path
    describing the target of the operation."""

    def _validate_mutability(
        self, resource_class: type[Resource[Any]], field_name: str
    ) -> None:
        """Validate mutability constraints."""
        # RFC 7644 Section 3.5.2: "Servers should be tolerant of schema extensions"
        if field_name not in resource_class.model_fields:
            return

        mutability = resource_class.get_field_annotation(field_name, Mutability)

        # RFC 7643 Section 7: "Attributes with mutability 'readOnly' SHALL NOT be modified"
        if mutability == Mutability.read_only and self.op in (
            PatchOperation.Op.add,
            PatchOperation.Op.replace_,
        ):
            raise MutabilityException(
                attribute=field_name, mutability="readOnly", operation=self.op.value
            ).as_pydantic_error()

        # RFC 7643 Section 7: "Attributes with mutability 'immutable' SHALL NOT be updated"
        if mutability == Mutability.immutable and self.op == PatchOperation.Op.replace_:
            raise MutabilityException(
                attribute=field_name, mutability="immutable", operation=self.op.value
            ).as_pydantic_error()

    def _validate_required_attribute(
        self, resource_class: type[Resource[Any]], field_name: str
    ) -> None:
        """Validate required attribute constraints for remove operations."""
        # RFC 7644 Section 3.5.2.3: Only validate for remove operations
        if self.op != PatchOperation.Op.remove:
            return

        # RFC 7644 Section 3.5.2: "Servers should be tolerant of schema extensions"
        if field_name not in resource_class.model_fields:
            return

        required = resource_class.get_field_annotation(field_name, Required)

        # RFC 7643 Section 7: "Required attributes SHALL NOT be removed"
        if required == Required.true:
            raise InvalidValueException(
                detail="required attribute cannot be removed", attribute=field_name
            ).as_pydantic_error()

    @model_validator(mode="after")
    def validate_operation_requirements(self, info: ValidationInfo) -> Self:
        """Validate operation requirements according to RFC 7644."""
        # Only validate in PATCH request context
        scim_ctx = info.context.get("scim") if info.context else None
        if scim_ctx != Context.RESOURCE_PATCH_REQUEST:
            return self

        # RFC 7644 Section 3.5.2.2: "If 'path' is unspecified, the operation
        # fails with HTTP status code 400 and a 'scimType' error of 'noTarget'"
        if self.path is None and self.op == PatchOperation.Op.remove:
            raise NoTargetException(
                detail="Remove operation requires a path"
            ).as_pydantic_error()

        # RFC 7644 Section 3.5.2.1: "Value is required for add operations"
        if self.op == PatchOperation.Op.add and self.value is None:
            raise InvalidValueException(
                detail="value is required for add operations"
            ).as_pydantic_error()

        return self

    value: Any | None = None

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


class PatchOp(Message, Generic[ResourceT]):
    """Patch Operation as defined in :rfc:`RFC7644 §3.5.2 <7644#section-3.5.2>`.

    Type parameter ResourceT is required and must be a concrete Resource subclass.
    Usage: PatchOp[User], PatchOp[Group], etc.

    .. note::
        - Always use with a specific type parameter, e.g., PatchOp[User]
        - PatchOp[Resource] is not allowed - use a concrete subclass instead
        - Union types are not supported - use a specific resource type
        - Using PatchOp without a type parameter raises TypeError
    """

    def __new__(cls, *args: Any, **kwargs: Any) -> Self:
        """Create new PatchOp instance with type parameter validation.

        Only handles the case of direct instantiation without type parameter (PatchOp()).
        All type parameter validation is handled by __class_getitem__.
        """
        if (
            cls.__name__ == "PatchOp"
            and not hasattr(cls, "__origin__")
            and not hasattr(cls, "__args__")
        ):
            raise TypeError(
                "PatchOp requires a type parameter. "
                "Use PatchOp[YourResourceType] instead of PatchOp. "
                "Example: PatchOp[User], PatchOp[Group], etc."
            )

        return super().__new__(cls)

    def __class_getitem__(
        cls, typevar_values: type[Resource[Any]] | tuple[type[Resource[Any]], ...]
    ) -> Any:
        """Validate type parameter when creating parameterized type.

        Ensures the type parameter is a concrete Resource subclass (not Resource itself)
        or a TypeVar bound to Resource. Rejects invalid types (str, int, etc.) and Union types.
        """
        if isinstance(typevar_values, TypeVar):
            # Check if TypeVar is bound to Resource or its subclass
            if typevar_values.__bound__ is not None and (
                typevar_values.__bound__ is Resource
                or (
                    isclass(typevar_values.__bound__)
                    and issubclass(typevar_values.__bound__, Resource)
                )
            ):
                return super().__class_getitem__(typevar_values)
            else:
                raise TypeError(
                    f"PatchOp TypeVar must be bound to Resource or its subclass, got {typevar_values}. "
                    "Example: T = TypeVar('T', bound=Resource)"
                )

        # Check if type parameter is a concrete Resource subclass (not Resource itself)
        if typevar_values is Resource:
            raise TypeError(
                "PatchOp requires a concrete Resource subclass, not Resource itself. "
                "Use PatchOp[User], PatchOp[Group], etc. instead of PatchOp[Resource]."
            )

        if not (
            isclass(typevar_values)
            and issubclass(typevar_values, Resource)
            and typevar_values is not Resource
        ):
            raise TypeError(
                f"PatchOp type parameter must be a concrete Resource subclass or TypeVar, got {typevar_values}. "
                "Use PatchOp[User], PatchOp[Group], etc."
            )

        return super().__class_getitem__(typevar_values)

    __schema__ = URN("urn:ietf:params:scim:api:messages:2.0:PatchOp")

    operations: Annotated[list[PatchOperation[ResourceT]] | None, Required.true] = (
        Field(None, serialization_alias="Operations", min_length=1)
    )
    """The body of an HTTP PATCH request MUST contain the attribute
    "Operations", whose value is an array of one or more PATCH operations."""

    @model_validator(mode="after")
    def validate_operations(self, info: ValidationInfo) -> Self:
        """Validate operations against resource type metadata if available.

        When PatchOp is used with a specific resource type (e.g., PatchOp[User]),
        this validator will automatically check mutability and required constraints.
        """
        # RFC 7644: The body of an HTTP PATCH request MUST contain the attribute "Operations"
        scim_ctx = info.context.get("scim") if info.context else None
        if scim_ctx == Context.RESOURCE_PATCH_REQUEST and self.operations is None:
            raise InvalidValueException(
                detail="operations attribute is required"
            ).as_pydantic_error()

        resource_class = _get_resource_class(self)
        if resource_class is None or not self.operations:
            return self

        # RFC 7644 Section 3.5.2: "Validate each operation against schema constraints"
        for operation in self.operations:
            if operation.path is None:
                continue

            field_name = operation.path.parts[0] if operation.path.parts else None
            operation._validate_mutability(resource_class, field_name)  # type: ignore[arg-type]
            operation._validate_required_attribute(resource_class, field_name)  # type: ignore[arg-type]

        return self

    def patch(self, resource: ResourceT) -> bool:
        """Apply all PATCH operations to the given SCIM resource in sequence.

        The resource is modified in-place.

        Each operation in the PatchOp is applied in order, modifying the resource in-place
        according to :rfc:`RFC7644 §3.5.2 <7644#section-3.5.2>`. Supported operations are
        "add", "replace", and "remove". If any operation modifies the resource, the method
        returns True; otherwise, False.

        Per :rfc:`RFC 7644 §3.5.2 <7644#section-3.5.2>`, when an operation sets a value's
        ``primary`` sub-attribute to ``True``, any other values in the same multi-valued
        attribute will have their ``primary`` set to ``False`` automatically.

        :param resource: The SCIM resource to patch. This object is modified in-place.
        :return: True if the resource was modified by any operation, False otherwise.
        :raises InvalidValueException: If multiple values are marked as primary in a single
            operation, or if multiple primary values already exist before the patch.
        """
        if not self.operations:
            return False

        modified = False
        # RFC 7644 Section 3.5.2: "Apply each operation in sequence"
        for operation in self.operations:
            if self._apply_operation(resource, operation):
                modified = True

        return modified

    def _apply_operation(
        self, resource: Resource[Any], operation: PatchOperation[ResourceT]
    ) -> bool:
        """Apply a single patch operation to a resource.

        :return: :data:`True` if the resource was modified, else :data:`False`.
        """
        if operation.op in (PatchOperation.Op.add, PatchOperation.Op.replace_):
            return self._apply_add_replace(resource, operation)
        if operation.op == PatchOperation.Op.remove:
            return self._apply_remove(resource, operation)

        raise InvalidValueException(detail=f"unsupported operation: {operation.op}")

    def _apply_add_replace(
        self, resource: Resource[Any], operation: PatchOperation[ResourceT]
    ) -> bool:
        """Apply an add or replace operation."""
        before_state = self._capture_primary_state(resource)

        path = operation.path if operation.path is not None else Path("")
        modified = path.set(
            resource,  # type: ignore[arg-type]
            operation.value,
            is_add=operation.op == PatchOperation.Op.add,
        )

        if modified:
            self._normalize_primary_after_patch(resource, before_state)

        return modified

    def _capture_primary_state(self, resource: Resource[Any]) -> dict[str, set[int]]:
        """Capture indices of elements with primary=True for each multi-valued attribute."""
        state: dict[str, set[int]] = {}
        for field_name in type(resource).model_fields:
            if not resource.get_field_multiplicity(field_name):
                continue

            field_value = getattr(resource, field_name, None)
            if not field_value:
                continue

            element_type = resource.get_field_root_type(field_name)
            if (
                not element_type
                or not isclass(element_type)
                or not issubclass(element_type, PydanticBaseModel)
                or "primary" not in element_type.model_fields
            ):
                continue

            primary_indices = {
                i
                for i, item in enumerate(field_value)
                if getattr(item, "primary", None) is True
            }
            state[field_name] = primary_indices

        return state

    def _normalize_primary_after_patch(
        self, resource: Resource[Any], before_state: dict[str, set[int]]
    ) -> None:
        """Normalize primary attributes after a patch operation.

        Per :rfc:`RFC 7644 §3.5.2 <7644#section-3.5.2>`: a PATCH operation that
        sets a value's "primary" sub-attribute to "true" SHALL cause the server
        to automatically set "primary" to "false" for any other values.
        """
        for field_name in type(resource).model_fields:
            if not resource.get_field_multiplicity(field_name):
                continue

            field_value = getattr(resource, field_name, None)
            if not field_value:
                continue

            element_type = resource.get_field_root_type(field_name)
            if (
                not element_type
                or not isclass(element_type)
                or not issubclass(element_type, PydanticBaseModel)
                or "primary" not in element_type.model_fields
            ):
                continue

            current_primary_indices = {
                i
                for i, item in enumerate(field_value)
                if getattr(item, "primary", None) is True
            }

            if len(current_primary_indices) <= 1:
                continue

            before_primaries = before_state.get(field_name, set())
            new_primaries = current_primary_indices - before_primaries

            if len(new_primaries) > 1:
                raise InvalidValueException(
                    detail=f"Multiple values marked as primary in field '{field_name}'"
                )

            if not new_primaries:
                raise InvalidValueException(
                    detail=f"Multiple primary values already exist in field '{field_name}'"
                )

            keep_index = next(iter(new_primaries))
            for i in current_primary_indices:
                if i != keep_index:
                    field_value[i].primary = False

    def _apply_remove(
        self, resource: Resource[Any], operation: PatchOperation[ResourceT]
    ) -> bool:
        """Apply a remove operation."""
        if operation.path is None:
            raise NoTargetException(detail="Remove operation requires a path")

        return operation.path.delete(resource, operation.value)  # type: ignore[arg-type]
