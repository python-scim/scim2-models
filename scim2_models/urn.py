from typing import TYPE_CHECKING
from typing import Any
from typing import Optional

from .base import BaseModel
from .utils import _normalize_attribute_name

if TYPE_CHECKING:
    from .base import BaseModel
    from .resources.resource import Resource


def _get_or_create_extension_instance(
    model: "Resource", extension_class: type
) -> "BaseModel":
    """Get existing extension instance or create a new one."""
    extension_instance = model[extension_class]
    if extension_instance is None:
        extension_instance = extension_class()
        model[extension_class] = extension_instance
    return extension_instance


def _normalize_path(model: Optional[type["BaseModel"]], path: str) -> tuple[str, str]:
    """Resolve a path to (schema_urn, attribute_path)."""
    from .resources.resource import Resource

    # Absolute URN
    if ":" in path:
        parts = path.rsplit(":", 1)
        return parts[0], parts[1]

    # Relative URN with a schema
    elif model and issubclass(model, Resource) and hasattr(model, "model_fields"):
        schemas_field = model.model_fields.get("schemas")
        return schemas_field.default[0], path  # type: ignore

    return "", path


def _validate_model_attribute(model: type["BaseModel"], attribute_base: str) -> None:
    """Validate that an attribute name or a sub-attribute path exist for a given model."""
    attribute_name, *sub_attribute_blocks = attribute_base.split(".")
    sub_attribute_base = ".".join(sub_attribute_blocks)

    aliases = {field.validation_alias for field in model.model_fields.values()}

    if _normalize_attribute_name(attribute_name) not in aliases:
        raise ValueError(
            f"Model '{model.__name__}' has no attribute named '{attribute_name}'"
        )

    if sub_attribute_base:
        attribute_type = model.get_field_root_type(attribute_name)

        if not attribute_type or not issubclass(attribute_type, BaseModel):
            raise ValueError(
                f"Attribute '{attribute_name}' is not a complex attribute, and cannot have a '{sub_attribute_base}' sub-attribute"
            )

        _validate_model_attribute(attribute_type, sub_attribute_base)


def _validate_attribute_urn(
    attribute_name: str, resource: type["Resource"]
) -> Optional[str]:
    """Validate that an attribute urn is valid or not.

    :param attribute_name: The attribute urn to check.
    :return: The normalized attribute URN.
    """
    from .resources.resource import Resource

    schema: Optional[Any]
    schema, attribute_base = _normalize_path(resource, attribute_name)

    validated_resource = Resource.get_by_schema([resource], schema)
    if not validated_resource:
        return None

    try:
        _validate_model_attribute(validated_resource, attribute_base)
    except ValueError:
        return None

    return f"{schema}:{attribute_base}"


def _resolve_path_to_target(
    resource: "Resource", path: str
) -> tuple[Optional["BaseModel"], str]:
    """Resolve a path to a target and an attribute_path.

    The target can be the resource itself, or an extension object.
    """
    schema_urn, attr_path = _normalize_path(type(resource), path)

    if not schema_urn:
        return resource, attr_path

    if schema_urn in resource.schemas:
        return resource, attr_path

    extension_class = resource.get_extension_model(schema_urn)
    if not extension_class:
        return (None, "")

    extension_instance = _get_or_create_extension_instance(resource, extension_class)
    return extension_instance, attr_path
