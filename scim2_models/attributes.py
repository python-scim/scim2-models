from typing import List
from typing import Optional
from typing import Tuple
from typing import Type


def validate_model_attribute(model: Type, attribute_base: str) -> None:
    """Validate that an attribute name or a sub-attribute path exist for a
    given model."""

    from scim2_models.base import BaseModel

    attribute_name, *sub_attribute_blocks = attribute_base.split(".")
    sub_attribute_base = ".".join(sub_attribute_blocks)

    aliases = {field.alias for field in model.model_fields.values()}

    if attribute_name not in aliases:
        raise ValueError(
            f"Model '{model.__name__}' has no attribute named '{attribute_name}'"
        )

    if sub_attribute_base:
        attribute_type = model.get_field_root_type(attribute_name)

        if not issubclass(attribute_type, BaseModel):
            raise ValueError(
                f"Attribute '{attribute_name}' is not a complex attribute, and cannot have a '{sub_attribute_base}' sub-attribute"
            )

        validate_model_attribute(attribute_type, sub_attribute_base)


def extract_schema_and_attribut_base(attribute_urn: str) -> Tuple[str, str]:
    # Extract the schema urn part and the attribute name part from attribute
    # name, as defined in :rfc:`RFC7644 §3.10 <7644#section-3.10>`.

    *urn_blocks, attribute_base = attribute_urn.split(":")
    schema = ":".join(urn_blocks)
    return schema, attribute_base


def validate_attribute_urn(
    attribute_name: str,
    default_resource: Optional[Type] = None,
    resource_types: Optional[List[Type]] = None,
) -> str:
    """Validate that an attribute urn is valid or not.

    :parm attribute_name: The attribute urn to check.
    :default_resource: The default resource if `attribute_name` is not an absolute urn.
    :resource_types: The available resources in which to look for the attribute.
    :return: The normalized attribute URN.
    """

    from scim2_models.rfc7643.resource import Resource

    if not resource_types:
        resource_types = []

    if default_resource and default_resource not in resource_types:
        resource_types.append(default_resource)

    default_schema = (
        default_resource.model_fields["schemas"].default[0]
        if default_resource
        else None
    )

    schema, attribute_base = extract_schema_and_attribut_base(attribute_name)
    if not schema:
        schema = default_schema

    if not schema:
        raise ValueError("No default schema and relative URN")

    resource = Resource.get_by_schema(resource_types, schema)
    if not resource:
        raise ValueError(f"No resource matching schema '{schema}'")

    validate_model_attribute(resource, attribute_base)

    return f"{schema}:{attribute_base}"


def contains_attribute_or_subattributes(attribute_urns: List[str], attribute_urn):
    return attribute_urn in attribute_urns or any(
        item.startswith(f"{attribute_urn}.") for item in attribute_urns
    )
