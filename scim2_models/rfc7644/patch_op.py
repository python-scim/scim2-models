from enum import Enum
from inspect import isclass
from typing import Annotated
from typing import Any
from typing import Generic
from typing import Optional

from pydantic import Field
from pydantic import ValidationInfo
from pydantic import field_validator
from pydantic import model_validator
from typing_extensions import Self

from ..base import BaseModel
from ..base import ComplexAttribute
from ..base import Context
from ..base import Mutability
from ..base import Required
from ..rfc7643.resource import AnyResource
from ..rfc7643.resource import Resource
from ..urn import resolve_path_to_target
from ..utils import find_field_name
from .error import Error
from .message import GenericMessageMetaclass
from .message import Message


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

    path: Optional[str] = None
    """The "path" attribute value is a String containing an attribute path
    describing the target of the operation."""

    @model_validator(mode="after")
    def validate_path(self, info: ValidationInfo) -> Self:
        """Validate path constraints according to RFC7644."""
        # Only validate in PATCH request context
        scim_ctx = info.context.get("scim") if info.context else None
        if scim_ctx != Context.RESOURCE_PATCH_REQUEST:
            return self

        # RFC7644 validation for empty/whitespace-only paths
        if self.path and not self.path.strip():
            raise ValueError(Error.make_invalid_path_error().detail)

        # RFC7644 validation for required path in remove operations
        if self.path is None and self.op == PatchOperation.Op.remove:
            raise ValueError("Op.path is required for remove operations")

        return self

    value: Optional[Any] = None

    @model_validator(mode="after")
    def validate_value(self, info: ValidationInfo) -> Self:
        """Validate value constraints according to RFC7644."""
        # Only validate in PATCH request context
        scim_ctx = info.context.get("scim") if info.context else None
        if scim_ctx != Context.RESOURCE_PATCH_REQUEST:
            return self

        # RFC7644 validation for required value in add operations
        if self.value is None and self.op == PatchOperation.Op.add:
            raise ValueError("Op.value is required for add operations")

        return self


class PatchOp(Message, Generic[AnyResource], metaclass=GenericMessageMetaclass):
    """Patch Operation as defined in :rfc:`RFC7644 §3.5.2 <7644#section-3.5.2>`."""

    schemas: Annotated[list[str], Required.true] = [
        "urn:ietf:params:scim:api:messages:2.0:PatchOp"
    ]

    operations: Annotated[Optional[list[PatchOperation]], Required.true] = Field(
        None, serialization_alias="Operations", min_length=1
    )
    """The body of an HTTP PATCH request MUST contain the attribute
    "Operations", whose value is an array of one or more PATCH operations."""

    def validate_mutability(self, resource: Resource) -> None:
        """Validate that operations don't target read-only or immutable fields.

        :param resource: Target resource to validate against
        :raises ValueError: If any operation targets an immutable field
        """
        if not self.operations:
            return

        for operation in self.operations:
            if operation.op == PatchOperation.Op.remove:
                continue  # Remove operations don't check mutability

            if operation.path is None:
                continue  # Root operations are handled separately

            try:
                self._validate_path_mutability(resource, operation.path)
            except ValueError:
                # Re-raise ValueError (mutability errors)
                raise
            except Exception:
                # If path resolution fails, let the patch method handle it
                pass

    def _validate_path_mutability(self, resource: Resource, path: str) -> None:
        """Validate mutability for a specific path, handling complex nested paths.

        :param resource: Target resource
        :param path: Path to validate
        :raises ValueError: If path targets immutable field
        """
        target, attr_path = self._resolve_path(resource, path)
        path_parts = attr_path.split(".")

        current_target = target
        for i, part in enumerate(path_parts):
            field_name = find_field_name(type(current_target), part)
            if not field_name:
                break

            mutability = type(current_target).get_field_annotation(
                field_name, Mutability
            )
            if mutability in [Mutability.read_only, Mutability.immutable]:
                raise ValueError(Error.make_mutability_error().detail)

            if i < len(path_parts) - 1:
                current_obj = getattr(current_target, field_name, None)
                if current_obj is None:
                    break
                current_target = current_obj

    def patch(self, resource: Resource) -> bool:
        """Create a new patched resource.

        :return: :data:`True` if the resource has been edited, else :data:`False`.
        """
        # Validate mutability constraints before applying operations
        self.validate_mutability(resource)

        if not self.operations:
            return False

        modified = False
        for operation in self.operations:
            if self._apply_operation(resource, operation):
                modified = True

        return modified

    def _apply_operation(self, resource: Resource, operation: PatchOperation) -> bool:
        """Apply a single patch operation to a resource.

        :return: :data:`True` if the resource was modified, else :data:`False`.
        """
        if operation.op in (PatchOperation.Op.add, PatchOperation.Op.replace_):
            return self._apply_add_replace(resource, operation)
        if operation.op == PatchOperation.Op.remove:
            return self._apply_remove(resource, operation)

        raise ValueError(Error.make_invalid_value_error().detail)

    def _apply_add_replace(self, resource: Resource, operation: PatchOperation) -> bool:
        """Apply an add operation."""
        if operation.path is not None:
            return self._set_value_at_path(
                resource,
                operation.path,
                operation.value,
                is_add=operation.op == PatchOperation.Op.add,
            )

        return self._apply_root_attributes(resource, operation.value)

    def _apply_remove(self, resource: Resource, operation: PatchOperation) -> bool:
        """Apply a remove operation."""
        if operation.path is None:
            raise ValueError("Op.path is required for remove operations")

        if operation.value is not None:
            return self._remove_specific_value(
                resource, operation.path, operation.value
            )

        return self._remove_value_at_path(resource, operation.path)

    def _apply_root_attributes(self, resource: BaseModel, value: Any) -> bool:
        """Apply attributes to the resource root."""
        if not isinstance(value, dict):
            return False

        modified = False
        for attr_name, val in value.items():
            field_name = find_field_name(type(resource), attr_name)
            if not field_name:
                continue

            old_value = getattr(resource, field_name)
            if old_value != val:
                setattr(resource, field_name, val)
                modified = True

        return modified

    def _set_value_at_path(
        self, resource: Resource, path: str, value: Any, is_add: bool
    ) -> bool:
        """Set a value at a specific path."""
        target, attr_path = self._resolve_path(resource, path)
        path_parts = attr_path.split(".")

        if len(path_parts) == 1:
            return self._set_simple_attribute(target, path_parts[0], value, is_add)

        return self._set_complex_attribute(target, path_parts, value, is_add)

    def _set_simple_attribute(
        self, resource: BaseModel, attr_name: str, value: Any, is_add: bool
    ) -> bool:
        """Set a value on a simple (non-nested) attribute."""
        field_name = find_field_name(type(resource), attr_name)
        if not field_name:
            raise ValueError(Error.make_no_target_error().detail)

        if is_add and self._is_multivalued_field(resource, field_name):
            return self._handle_multivalued_add(resource, field_name, value)

        old_value = getattr(resource, field_name)
        if old_value == value:
            return False

        setattr(resource, field_name, value)
        return True

    def _set_complex_attribute(
        self, resource: BaseModel, path_parts: list[str], value: Any, is_add: bool
    ) -> bool:
        """Set a value on a complex (nested) attribute."""
        parent_attr = path_parts[0]
        sub_path = ".".join(path_parts[1:])

        parent_field_name = find_field_name(type(resource), parent_attr)
        if not parent_field_name:
            raise ValueError(Error.make_no_target_error().detail)

        parent_obj = getattr(resource, parent_field_name)
        if parent_obj is None:
            parent_obj = self._create_parent_object(resource, parent_field_name)
            if parent_obj is None:
                return False

        return self._set_value_at_path(parent_obj, sub_path, value, is_add)

    def _is_multivalued_field(self, resource: BaseModel, field_name: str) -> bool:
        """Check if a field is multi-valued."""
        return hasattr(resource, field_name) and type(resource).get_field_multiplicity(
            field_name
        )

    def _handle_multivalued_add(
        self, resource: BaseModel, field_name: str, value: Any
    ) -> bool:
        """Handle adding values to a multi-valued attribute."""
        current_list = getattr(resource, field_name) or []

        if isinstance(value, list):
            return self._add_multiple_values(resource, field_name, current_list, value)

        return self._add_single_value(resource, field_name, current_list, value)

    def _add_multiple_values(
        self, resource: BaseModel, field_name: str, current_list: list, values: list
    ) -> bool:
        """Add multiple values to a multi-valued attribute."""
        new_values = []
        for new_val in values:
            if not self._value_exists_in_list(current_list, new_val):
                new_values.append(new_val)

        if not new_values:
            return False

        setattr(resource, field_name, current_list + new_values)
        return True

    def _add_single_value(
        self, resource: BaseModel, field_name: str, current_list: list, value: Any
    ) -> bool:
        """Add a single value to a multi-valued attribute."""
        if self._value_exists_in_list(current_list, value):
            return False

        current_list.append(value)
        setattr(resource, field_name, current_list)
        return True

    def _value_exists_in_list(self, current_list: list, new_value: Any) -> bool:
        """Check if a value already exists in a list."""
        return any(self._values_match(item, new_value) for item in current_list)

    def _create_parent_object(self, resource: BaseModel, parent_field_name: str) -> Any:
        """Create a parent object if it doesn't exist."""
        parent_class = type(resource).get_field_root_type(parent_field_name)
        if not parent_class or not isclass(parent_class):
            return None

        parent_obj = parent_class()
        setattr(resource, parent_field_name, parent_obj)
        return parent_obj

    def _remove_value_at_path(self, resource: Resource, path: str) -> bool:
        """Remove a value at a specific path."""
        target, attr_path = self._resolve_path(resource, path)

        if not attr_path:
            raise ValueError(Error.make_invalid_path_error().detail)

        parent_attr, *path_parts = attr_path.split(".")
        field_name = find_field_name(type(target), parent_attr)
        if not field_name:
            raise ValueError(Error.make_no_target_error().detail)
        parent_obj = getattr(target, field_name)

        if parent_obj is None:
            return False

        if not path_parts:
            setattr(target, field_name, None)
            return True

        sub_path = ".".join(path_parts)
        return self._remove_value_at_path(parent_obj, sub_path)

    def _remove_specific_value(
        self, resource: Resource, path: str, value_to_remove: Any
    ) -> bool:
        """Remove a specific value from a multi-valued attribute."""
        target, attr_path = self._resolve_path(resource, path)

        if not attr_path:
            raise ValueError(Error.make_invalid_path_error().detail)

        field_name = find_field_name(type(target), attr_path)
        if not field_name:
            raise ValueError(Error.make_no_target_error().detail)

        current_list = getattr(target, field_name)
        if not isinstance(current_list, list):
            return False

        new_list = []
        modified = False
        for item in current_list:
            if not self._values_match(item, value_to_remove):
                new_list.append(item)
            else:
                modified = True

        if modified:
            setattr(target, field_name, new_list if new_list else None)
            return True

        return False

    def _resolve_path(self, resource: Resource, path: str) -> tuple[BaseModel, str]:
        """Resolve a path to (target, attribute_path)."""
        return resolve_path_to_target(resource, path)

    def _values_match(self, value1: Any, value2: Any) -> bool:
        """Check if two values match, handling both objects and dicts."""
        if isinstance(value1, BaseModel):
            value1 = value1.model_dump()

        if isinstance(value2, BaseModel):
            value2 = value2.model_dump()

        return value1 == value2
