from typing import TYPE_CHECKING
from typing import Any
from typing import Optional

from .base import BaseModel
from .utils import normalize_attribute_name

if TYPE_CHECKING:
    from .base import BaseModel
    from .rfc7643.resource import Resource


def normalize_path(model: type["BaseModel"], path: str) -> tuple[str, str]:
    """Resolve a path to (schema_urn, attribute_path)."""
    # Absolute URN
    if ":" in path:
        parts = path.rsplit(":", 1)
        return parts[0], parts[1]

    schemas_field = model.model_fields.get("schemas")
    return schemas_field.default[0], path  # type: ignore


def validate_model_attribute(model: type["BaseModel"], attribute_base: str) -> None:
    """Validate that an attribute name or a sub-attribute path exist for a given model."""
    attribute_name, *sub_attribute_blocks = attribute_base.split(".")
    sub_attribute_base = ".".join(sub_attribute_blocks)

    aliases = {field.validation_alias for field in model.model_fields.values()}

    if normalize_attribute_name(attribute_name) not in aliases:
        raise ValueError(
            f"Model '{model.__name__}' has no attribute named '{attribute_name}'"
        )

    if sub_attribute_base:
        attribute_type = model.get_field_root_type(attribute_name)

        if not attribute_type or not issubclass(attribute_type, BaseModel):
            raise ValueError(
                f"Attribute '{attribute_name}' is not a complex attribute, and cannot have a '{sub_attribute_base}' sub-attribute"
            )

        validate_model_attribute(attribute_type, sub_attribute_base)


def validate_attribute_urn(
    attribute_name: str, resource: type["Resource"]
) -> Optional[str]:
    """Validate that an attribute urn is valid or not.

    :param attribute_name: The attribute urn to check.
    :return: The normalized attribute URN.
    """
    from .rfc7643.resource import Resource

    schema: Optional[Any]
    schema, attribute_base = normalize_path(resource, attribute_name)

    validated_resource = Resource.get_by_schema([resource], schema)
    if not validated_resource:
        return None

    try:
        validate_model_attribute(validated_resource, attribute_base)
    except ValueError:
        return None

    return f"{schema}:{attribute_base}"
