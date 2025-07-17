"""Base SCIM object classes with schema identification."""

from typing import TYPE_CHECKING
from typing import Annotated
from typing import Any
from typing import Optional

from .annotations import Required
from .base import BaseModel
from .context import Context
from .utils import normalize_attribute_name

if TYPE_CHECKING:
    from .rfc7643.resource import Resource


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


def extract_schema_and_attribute_base(attribute_urn: str) -> tuple[str, str]:
    """Extract the schema urn part and the attribute name part from attribute name.

    As defined in :rfc:`RFC7644 §3.10 <7644#section-3.10>`.
    """
    *urn_blocks, attribute_base = attribute_urn.split(":")
    schema = ":".join(urn_blocks)
    return schema, attribute_base


def validate_attribute_urn(
    attribute_name: str,
    default_resource: Optional[type["Resource"]] = None,
    resource_types: Optional[list[type["Resource"]]] = None,
) -> str:
    """Validate that an attribute urn is valid or not.

    :param attribute_name: The attribute urn to check.
    :default_resource: The default resource if `attribute_name` is not an absolute urn.
    :resource_types: The available resources in which to look for the attribute.
    :return: The normalized attribute URN.
    """
    from .rfc7643.resource import Resource

    if not resource_types:
        resource_types = []

    if default_resource and default_resource not in resource_types:
        resource_types.append(default_resource)

    default_schema = (
        default_resource.model_fields["schemas"].default[0]
        if default_resource
        else None
    )

    schema: Optional[Any]
    schema, attribute_base = extract_schema_and_attribute_base(attribute_name)
    if not schema:
        schema = default_schema

    if not schema:
        raise ValueError("No default schema and relative URN")

    resource = Resource.get_by_schema(resource_types, schema)
    if not resource:
        raise ValueError(f"No resource matching schema '{schema}'")

    validate_model_attribute(resource, attribute_base)

    return f"{schema}:{attribute_base}"


class ScimObject(BaseModel):
    schemas: Annotated[list[str], Required.true]
    """The "schemas" attribute is a REQUIRED attribute and is an array of
    Strings containing URIs that are used to indicate the namespaces of the
    SCIM schemas that define the attributes present in the current JSON
    structure."""

    def _prepare_model_dump(
        self,
        scim_ctx: Optional[Context] = Context.DEFAULT,
        **kwargs: Any,
    ) -> dict[str, Any]:
        kwargs.setdefault("context", {}).setdefault("scim", scim_ctx)

        if scim_ctx:
            kwargs.setdefault("exclude_none", True)
            kwargs.setdefault("by_alias", True)

        return kwargs

    def model_dump(
        self,
        *args: Any,
        scim_ctx: Optional[Context] = Context.DEFAULT,
        **kwargs: Any,
    ) -> dict:
        """Create a model representation that can be included in SCIM messages by using Pydantic :code:`BaseModel.model_dump`.

        :param scim_ctx: If a SCIM context is passed, some default values of
            Pydantic :code:`BaseModel.model_dump` are tuned to generate valid SCIM
            messages. Pass :data:`None` to get the default Pydantic behavior.
        """
        dump_kwargs = self._prepare_model_dump(scim_ctx, **kwargs)
        if scim_ctx:
            dump_kwargs.setdefault("mode", "json")
        return super(BaseModel, self).model_dump(*args, **dump_kwargs)

    def model_dump_json(
        self,
        *args: Any,
        scim_ctx: Optional[Context] = Context.DEFAULT,
        **kwargs: Any,
    ) -> str:
        """Create a JSON model representation that can be included in SCIM messages by using Pydantic :code:`BaseModel.model_dump_json`.

        :param scim_ctx: If a SCIM context is passed, some default values of
            Pydantic :code:`BaseModel.model_dump` are tuned to generate valid SCIM
            messages. Pass :data:`None` to get the default Pydantic behavior.
        """
        dump_kwargs = self._prepare_model_dump(scim_ctx, **kwargs)
        return super(BaseModel, self).model_dump_json(*args, **dump_kwargs)
