from enum import Enum
from inspect import isclass
from typing import Annotated
from typing import Any
from typing import Generic
from typing import Optional
from typing import TypeVar
from typing import Union

from pydantic import Field
from pydantic import ValidationInfo
from pydantic import field_validator
from pydantic import model_validator
from typing_extensions import Self

from ..annotations import Mutability
from ..annotations import Required
from ..attributes import ComplexAttribute
from ..base import BaseModel
from ..context import Context
from ..resources.resource import Resource
from ..urn import _resolve_path_to_target
from ..utils import _extract_field_name
from ..utils import _find_field_name
from ..utils import _get_path_parts
from ..utils import _validate_scim_path_syntax
from .error import Error
from .message import Message
from .message import _get_resource_class

T = TypeVar("T", bound=Resource[Any])


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
            raise ValueError(Error.make_mutability_error().detail)

        # RFC 7643 Section 7: "Attributes with mutability 'immutable' SHALL NOT be updated"
        if mutability == Mutability.immutable and self.op == PatchOperation.Op.replace_:
            raise ValueError(Error.make_mutability_error().detail)

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
            raise ValueError(Error.make_invalid_value_error().detail)

    @model_validator(mode="after")
    def validate_operation_requirements(self, info: ValidationInfo) -> Self:
        """Validate operation requirements according to RFC 7644."""
        # Only validate in PATCH request context
        scim_ctx = info.context.get("scim") if info.context else None
        if scim_ctx != Context.RESOURCE_PATCH_REQUEST:
            return self

        # RFC 7644 Section 3.5.2: "Path syntax validation according to ABNF grammar"
        if self.path is not None and not _validate_scim_path_syntax(self.path):
            raise ValueError(Error.make_invalid_path_error().detail)

        # RFC 7644 Section 3.5.2.3: "Path is required for remove operations"
        if self.path is None and self.op == PatchOperation.Op.remove:
            raise ValueError(Error.make_invalid_path_error().detail)

        # RFC 7644 Section 3.5.2.1: "Value is required for add operations"
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


class PatchOp(Message, Generic[T]):
    """Patch Operation as defined in :rfc:`RFC7644 §3.5.2 <7644#section-3.5.2>`.

    Type parameter T is required and must be a concrete Resource subclass.
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
        cls, typevar_values: Union[type[Resource[Any]], tuple[type[Resource[Any]], ...]]
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

    schemas: Annotated[list[str], Required.true] = [
        "urn:ietf:params:scim:api:messages:2.0:PatchOp"
    ]

    operations: Annotated[Optional[list[PatchOperation]], Required.true] = Field(
        None, serialization_alias="Operations", min_length=1
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
            raise ValueError(Error.make_invalid_value_error().detail)

        resource_class = _get_resource_class(self)
        if resource_class is None or not self.operations:
            return self

        # RFC 7644 Section 3.5.2: "Validate each operation against schema constraints"
        for operation in self.operations:
            if operation.path is None:
                continue

            field_name = _extract_field_name(operation.path)
            operation._validate_mutability(resource_class, field_name)  # type: ignore[arg-type]
            operation._validate_required_attribute(resource_class, field_name)  # type: ignore[arg-type]

        return self

    def patch(self, resource: T) -> bool:
        """Apply all PATCH operations to the given SCIM resource in sequence.

        The resource is modified in-place.

        Each operation in the PatchOp is applied in order, modifying the resource in-place
        according to :rfc:`RFC7644 §3.5.2 <7644#section-3.5.2>`. Supported operations are
        "add", "replace", and "remove". If any operation modifies the resource, the method
        returns True; otherwise, False.

        :param resource: The SCIM resource to patch. This object is modified in-place.
        :type resource: T
        :return: True if the resource was modified by any operation, False otherwise.
        :raises ValueError: If an operation is invalid (e.g., invalid path, forbidden mutation).
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
        self, resource: Resource[Any], operation: PatchOperation
    ) -> bool:
        """Apply a single patch operation to a resource.

        :return: :data:`True` if the resource was modified, else :data:`False`.
        """
        if operation.op in (PatchOperation.Op.add, PatchOperation.Op.replace_):
            return self._apply_add_replace(resource, operation)
        if operation.op == PatchOperation.Op.remove:
            return self._apply_remove(resource, operation)

        raise ValueError(Error.make_invalid_value_error().detail)

    def _apply_add_replace(
        self, resource: Resource[Any], operation: PatchOperation
    ) -> bool:
        """Apply an add or replace operation."""
        # RFC 7644 Section 3.5.2.1: "If path is specified, add/replace at that path"
        if operation.path is not None:
            return self._set_value_at_path(
                resource,
                operation.path,
                operation.value,
                is_add=operation.op == PatchOperation.Op.add,
            )

        # RFC 7644 Section 3.5.2.1: "If no path specified, add/replace at root level"
        return self._apply_root_attributes(resource, operation.value)

    def _apply_remove(self, resource: Resource[Any], operation: PatchOperation) -> bool:
        """Apply a remove operation."""
        # RFC 7644 Section 3.5.2.3: "Path is required for remove operations"
        if operation.path is None:
            raise ValueError(Error.make_invalid_path_error().detail)

        # RFC 7644 Section 3.5.2.3: "If a value is specified, remove only that value"
        if operation.value is not None:
            return self._remove_specific_value(
                resource, operation.path, operation.value
            )

        return self._remove_value_at_path(resource, operation.path)

    @classmethod
    def _apply_root_attributes(cls, resource: BaseModel, value: Any) -> bool:
        """Apply attributes to the resource root."""
        if not isinstance(value, dict):
            return False

        modified = False
        for attr_name, val in value.items():
            field_name = _find_field_name(type(resource), attr_name)
            if not field_name:
                continue

            old_value = getattr(resource, field_name)
            if old_value != val:
                setattr(resource, field_name, val)
                modified = True

        return modified

    @classmethod
    def _set_value_at_path(
        cls, resource: Resource[Any], path: str, value: Any, is_add: bool
    ) -> bool:
        """Set a value at a specific path."""
        target, attr_path = _resolve_path_to_target(resource, path)

        if not target:
            raise ValueError(Error.make_invalid_path_error().detail)

        if not attr_path:
            if not isinstance(value, dict):
                raise ValueError(Error.make_invalid_path_error().detail)

            updated_data = {**target.model_dump(), **value}
            updated_target = type(target).model_validate(updated_data)
            target.__dict__.update(updated_target.__dict__)
            return True

        path_parts = _get_path_parts(attr_path)
        if len(path_parts) == 1:
            return cls._set_simple_attribute(target, path_parts[0], value, is_add)

        return cls._set_complex_attribute(target, path_parts, value, is_add)

    @classmethod
    def _set_simple_attribute(
        cls, resource: BaseModel, attr_name: str, value: Any, is_add: bool
    ) -> bool:
        """Set a value on a simple (non-nested) attribute."""
        field_name = _find_field_name(type(resource), attr_name)
        if not field_name:
            raise ValueError(Error.make_no_target_error().detail)

        # RFC 7644 Section 3.5.2.1: "For multi-valued attributes, add operation appends values"
        if is_add and cls._is_multivalued_field(resource, field_name):
            return cls._handle_multivalued_add(resource, field_name, value)

        old_value = getattr(resource, field_name)
        if old_value == value:
            return False

        setattr(resource, field_name, value)
        return True

    @classmethod
    def _set_complex_attribute(
        cls, resource: BaseModel, path_parts: list[str], value: Any, is_add: bool
    ) -> bool:
        """Set a value on a complex (nested) attribute."""
        parent_attr = path_parts[0]
        sub_path = ".".join(path_parts[1:])

        parent_field_name = _find_field_name(type(resource), parent_attr)
        if not parent_field_name:
            raise ValueError(Error.make_no_target_error().detail)

        parent_obj = getattr(resource, parent_field_name)
        if parent_obj is None:
            parent_obj = cls._create_parent_object(resource, parent_field_name)
            if parent_obj is None:
                return False

        return cls._set_value_at_path(parent_obj, sub_path, value, is_add)

    @classmethod
    def _is_multivalued_field(cls, resource: BaseModel, field_name: str) -> bool:
        """Check if a field is multi-valued."""
        return hasattr(resource, field_name) and type(resource).get_field_multiplicity(
            field_name
        )

    @classmethod
    def _handle_multivalued_add(
        cls, resource: BaseModel, field_name: str, value: Any
    ) -> bool:
        """Handle adding values to a multi-valued attribute."""
        current_list = getattr(resource, field_name) or []

        # RFC 7644 Section 3.5.2.1: "Add operation appends values to multi-valued attributes"
        if isinstance(value, list):
            return cls._add_multiple_values(resource, field_name, current_list, value)

        return cls._add_single_value(resource, field_name, current_list, value)

    @classmethod
    def _add_multiple_values(
        cls,
        resource: BaseModel,
        field_name: str,
        current_list: list[Any],
        values: list[Any],
    ) -> bool:
        """Add multiple values to a multi-valued attribute."""
        new_values = []
        # RFC 7644 Section 3.5.2.1: "Do not add duplicate values"
        for new_val in values:
            if not cls._value_exists_in_list(current_list, new_val):
                new_values.append(new_val)

        if not new_values:
            return False

        setattr(resource, field_name, current_list + new_values)
        return True

    @classmethod
    def _add_single_value(
        cls, resource: BaseModel, field_name: str, current_list: list[Any], value: Any
    ) -> bool:
        """Add a single value to a multi-valued attribute."""
        # RFC 7644 Section 3.5.2.1: "Do not add duplicate values"
        if cls._value_exists_in_list(current_list, value):
            return False

        current_list.append(value)
        setattr(resource, field_name, current_list)
        return True

    @classmethod
    def _value_exists_in_list(cls, current_list: list[Any], new_value: Any) -> bool:
        """Check if a value already exists in a list."""
        return any(cls._values_match(item, new_value) for item in current_list)

    @classmethod
    def _create_parent_object(cls, resource: BaseModel, parent_field_name: str) -> Any:
        """Create a parent object if it doesn't exist."""
        parent_class = type(resource).get_field_root_type(parent_field_name)
        if not parent_class or not isclass(parent_class):
            return None

        parent_obj = parent_class()
        setattr(resource, parent_field_name, parent_obj)
        return parent_obj

    @classmethod
    def _remove_value_at_path(cls, resource: Resource[Any], path: str) -> bool:
        """Remove a value at a specific path."""
        target, attr_path = _resolve_path_to_target(resource, path)

        # RFC 7644 Section 3.5.2.3: "Path must resolve to a valid attribute"
        if not attr_path or not target:
            raise ValueError(Error.make_invalid_path_error().detail)

        parent_attr, *path_parts = _get_path_parts(attr_path)
        field_name = _find_field_name(type(target), parent_attr)
        if not field_name:
            raise ValueError(Error.make_no_target_error().detail)
        parent_obj = getattr(target, field_name)

        if parent_obj is None:
            return False

        # RFC 7644 Section 3.5.2.3: "Remove entire attribute if no sub-path"
        if not path_parts:
            setattr(target, field_name, None)
            return True

        sub_path = ".".join(path_parts)
        return cls._remove_value_at_path(parent_obj, sub_path)

    @classmethod
    def _remove_specific_value(
        cls, resource: Resource[Any], path: str, value_to_remove: Any
    ) -> bool:
        """Remove a specific value from a multi-valued attribute."""
        target, attr_path = _resolve_path_to_target(resource, path)

        # RFC 7644 Section 3.5.2.3: "Path must resolve to a valid attribute"
        if not attr_path or not target:
            raise ValueError(Error.make_invalid_path_error().detail)

        field_name = _find_field_name(type(target), attr_path)
        if not field_name:
            raise ValueError(Error.make_no_target_error().detail)

        current_list = getattr(target, field_name)
        if not isinstance(current_list, list):
            return False

        new_list = []
        modified = False
        # RFC 7644 Section 3.5.2.3: "Remove matching values from multi-valued attributes"
        for item in current_list:
            if not cls._values_match(item, value_to_remove):
                new_list.append(item)
            else:
                modified = True

        if modified:
            setattr(target, field_name, new_list if new_list else None)
            return True

        return False

    @classmethod
    def _values_match(cls, value1: Any, value2: Any) -> bool:
        """Check if two values match, converting BaseModel to dict for comparison."""

        def to_dict(value: Any) -> dict[str, Any]:
            return value.model_dump() if isinstance(value, BaseModel) else value

        return to_dict(value1) == to_dict(value2)
