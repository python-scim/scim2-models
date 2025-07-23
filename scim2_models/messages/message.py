from typing import Annotated
from typing import Any
from typing import Callable
from typing import Optional
from typing import Union
from typing import get_args
from typing import get_origin

from pydantic import Discriminator
from pydantic import Tag
from pydantic._internal._model_construction import ModelMetaclass

from scim2_models.resources.resource import Resource

from ..base import BaseModel
from ..scim_object import ScimObject
from ..utils import UNION_TYPES


class Message(ScimObject):
    """SCIM protocol messages as defined by :rfc:`RFC7644 §3.1 <7644#section-3.1>`."""


def _create_schema_discriminator(
    resource_types_schemas: list[str],
) -> Callable[[Any], Optional[str]]:
    """Create a schema discriminator function for the given resource schemas.

    :param resource_types_schemas: List of valid resource schemas
    :return: Discriminator function for Pydantic
    """

    def get_schema_from_payload(payload: Any) -> Optional[str]:
        """Extract schema from SCIM payload for discrimination.

        :param payload: SCIM payload dict or object
        :return: First matching schema or None
        """
        if not payload:
            return None

        payload_schemas = (
            payload.get("schemas", []) if isinstance(payload, dict) else payload.schemas
        )

        common_schemas = [
            schema for schema in payload_schemas if schema in resource_types_schemas
        ]
        return common_schemas[0] if common_schemas else None

    return get_schema_from_payload


def _get_tag(resource_type: type[BaseModel]) -> Tag:
    """Create Pydantic tag from resource type schema.

    :param resource_type: SCIM resource type
    :return: Pydantic Tag for discrimination
    """
    return Tag(resource_type.model_fields["schemas"].default[0])


def _create_tagged_resource_union(resource_union: Any) -> Any:
    """Build Discriminated Unions for SCIM resources.

    Creates discriminated unions so Pydantic can determine which class to instantiate
    by inspecting the payload's schemas field.

    :param resource_union: Union type of SCIM resources
    :return: Annotated discriminated union or original type
    """
    if get_origin(resource_union) not in UNION_TYPES:
        return resource_union

    resource_types = get_args(resource_union)

    # Set up schemas for the discriminator function
    resource_types_schemas = [
        resource_type.model_fields["schemas"].default[0]
        for resource_type in resource_types
    ]

    # Create discriminator function with schemas captured in closure
    schema_discriminator = _create_schema_discriminator(resource_types_schemas)
    discriminator = Discriminator(schema_discriminator)

    tagged_resources = [
        Annotated[resource_type, _get_tag(resource_type)]
        for resource_type in resource_types
    ]
    # Dynamic union construction from tuple - MyPy can't validate this at compile time
    union = Union[tuple(tagged_resources)]  # type: ignore
    return Annotated[union, discriminator]


class _GenericMessageMetaclass(ModelMetaclass):
    """Metaclass for SCIM generic types with discriminated unions."""

    def __new__(
        cls, name: str, bases: tuple[type, ...], attrs: dict[str, Any], **kwargs: Any
    ) -> type:
        """Create class with tagged resource unions for generic parameters."""
        if kwargs.get("__pydantic_generic_metadata__") and kwargs[
            "__pydantic_generic_metadata__"
        ].get("args"):
            tagged_union = _create_tagged_resource_union(
                kwargs["__pydantic_generic_metadata__"]["args"][0]
            )
            kwargs["__pydantic_generic_metadata__"]["args"] = (tagged_union,)

        klass = super().__new__(cls, name, bases, attrs, **kwargs)
        return klass


def _get_resource_class(obj) -> Optional[type[Resource]]:
    """Extract the resource class from generic type parameter."""
    metadata = getattr(obj.__class__, "__pydantic_generic_metadata__", {"args": [None]})
    resource_class = metadata["args"][0]
    return resource_class
