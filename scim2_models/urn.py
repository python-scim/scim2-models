"""URN (Uniform Resource Name) utilities for SCIM.

This module provides centralized utilities for handling SCIM URNs including:
- Parsing and validation of URNs
- Schema-to-resource resolution
- Path normalization and attribute resolution
- Extension handling
"""

from typing import TYPE_CHECKING
from typing import Optional

# Import conditionally to avoid circular dependencies
if TYPE_CHECKING:
    from .base import BaseModel
    from .rfc7643.resource import Resource


def extract_schema_and_attribute_base(attribute_urn: str) -> tuple[str, str]:
    """Extract schema URN and attribute name from a full attribute URN.

    :param attribute_urn: Full attribute URN like "urn:ietf:params:scim:schemas:core:2.0:User:userName"
    :return: Tuple of (schema_urn, attribute_base) where schema_urn is "urn:ietf:params:scim:schemas:core:2.0:User"
             and attribute_base is "userName"

    Examples::

        >>> extract_schema_and_attribute_base("urn:ietf:params:scim:schemas:core:2.0:User:userName")
        ('urn:ietf:params:scim:schemas:core:2.0:User', 'userName')

        >>> extract_schema_and_attribute_base("userName")
        ('', 'userName')
    """
    *urn_blocks, attribute_base = attribute_urn.split(":")
    schema = ":".join(urn_blocks)
    return schema, attribute_base


def validate_attribute_urn(
    attribute_name: str,
    default_resource: Optional[type["BaseModel"]] = None,
    resource_types: Optional[list[type["BaseModel"]]] = None,
) -> str:
    """Validate that an attribute URN is valid.

    :param attribute_name: The attribute URN to check
    :param default_resource: The default resource type if attribute_name is not an absolute URN
    :param resource_types: The available resource types in which to look for the attribute
    :return: The normalized attribute URN
    :raises ValueError: If no default schema and relative URN, or if attribute not found
    """
    from .base import validate_model_attribute
    from .rfc7643.resource import Resource

    if not resource_types:
        resource_types = []

    if default_resource and default_resource not in resource_types:
        resource_types.append(default_resource)

    default_schema: Optional[str] = (
        default_resource.model_fields["schemas"].default[0]
        if default_resource
        else None
    )

    schema, attribute_base = extract_schema_and_attribute_base(attribute_name)
    final_schema = schema or default_schema

    if not final_schema:
        raise ValueError("No default schema and relative URN")

    resource = Resource.get_by_schema(resource_types, final_schema)
    if not resource:
        raise ValueError(f"No resource matching schema '{final_schema}'")

    validate_model_attribute(resource, attribute_base)

    return f"{final_schema}:{attribute_base}"


def normalize_path_to_urn(model: "BaseModel", path: str) -> str:
    """Convert any path to a canonical URN.

    :param model: The model context for relative paths
    :param path: Path that may be relative or absolute URN
    :return: Canonical URN format

    Examples::

        >>> from scim2_models.rfc7643.user import User
        >>> user = User(user_name="test")
        >>> normalize_path_to_urn(user, "userName")
        'urn:ietf:params:scim:schemas:core:2.0:User:userName'

        >>> normalize_path_to_urn(user, "urn:ietf:params:scim:schemas:core:2.0:User:userName")
        'urn:ietf:params:scim:schemas:core:2.0:User:userName'
    """
    from .rfc7643.resource import Resource

    if is_absolute_urn(path) or not isinstance(model, Resource) or not model.schemas:
        return path

    core_schema = model.schemas[0]
    return f"{core_schema}:{path}"


def parse_urn(urn_path: str) -> tuple[str, str]:
    """Parse a URN to extract schema and attribute path.

    :param urn_path: URN path to parse
    :return: Tuple of (schema_urn, attr_path)
    :raises ValueError: If URN is malformed or cannot be parsed
    """
    from .rfc7644.error import Error

    if not is_absolute_urn(urn_path):
        return "", urn_path

    try:
        schema_urn, attr_path = extract_schema_and_attribute_base(urn_path)
        return schema_urn, attr_path
    except (ValueError, IndexError) as err:
        raise ValueError(Error.make_no_target_error().detail) from err


def resolve_urn_to_target(
    model: "BaseModel", schema_urn: str, attr_path: str
) -> tuple["BaseModel", str]:
    """Resolve a schema URN and attribute path to (target, attribute_path).

    :param model: The model to resolve against
    :param schema_urn: Schema URN to resolve
    :param attr_path: Attribute path within the schema
    :return: Tuple of (target_object, resolved_attribute_path)
    :raises ValueError: If schema URN cannot be resolved to a valid target
    """
    from .rfc7643.resource import Resource
    from .rfc7644.error import Error

    if not schema_urn:
        return model, attr_path

    if isinstance(model, Resource) and schema_urn in model.schemas:
        return model, attr_path

    if not isinstance(model, Resource):
        raise ValueError(Error.make_no_target_error().detail)

    extension_class = model.get_extension_model(schema_urn)
    if not extension_class:
        raise ValueError(Error.make_no_target_error().detail)

    if not attr_path:
        return model, schema_urn

    extension_instance = _get_or_create_extension_instance(model, extension_class)
    return extension_instance, attr_path


def is_absolute_urn(path: str) -> bool:
    """Check if a path is an absolute URN.

    :param path: Path to check
    :return: True if path contains URN schema, False otherwise
    """
    return ":" in path


def build_attribute_urn(schema: str, attribute: str) -> str:
    """Build a full attribute URN from schema and attribute name.

    :param schema: Schema URN
    :param attribute: Attribute name
    :return: Full attribute URN
    """
    if not schema:
        return attribute
    return f"{schema}:{attribute}"


def _get_or_create_extension_instance(
    model: "Resource", extension_class: type
) -> "BaseModel":
    """Get existing extension instance or create a new one.

    :param model: Resource model containing the extension
    :param extension_class: Extension class to get or create
    :return: Extension instance
    """
    extension_instance = model[extension_class]
    if extension_instance is None:
        extension_instance = extension_class()
        model[extension_class] = extension_instance
    return extension_instance


def resolve_path_to_target(model: "BaseModel", path: str) -> tuple["BaseModel", str]:
    """Resolve a path to (target, attribute_path).

    This is a convenience function that combines normalization, parsing, and resolution.

    :param model: Model to resolve against
    :param path: Path to resolve (relative or absolute)
    :return: Tuple of (target_object, attribute_path)
    """
    urn_path = normalize_path_to_urn(model, path)
    schema_urn, attr_path = parse_urn(urn_path)
    target, attr_path = resolve_urn_to_target(model, schema_urn, attr_path)
    return target, attr_path
