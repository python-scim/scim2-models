from typing import Annotated
from typing import Any

from pydantic import Field
from typing_extensions import Self

from ..annotations import CaseExact
from ..annotations import Mutability
from ..annotations import Required
from ..annotations import Returned
from ..annotations import Uniqueness
from ..attributes import ComplexAttribute
from ..path import URN
from ..reference import URI
from ..reference import Reference
from .resource import Resource


class SchemaExtension(ComplexAttribute):
    schema_: Annotated[
        Reference[URI] | None,
        Mutability.read_only,
        Required.true,
        CaseExact.true,
    ] = Field(None, alias="schema")
    """The URI of a schema extension."""

    required: Annotated[bool | None, Mutability.read_only, Required.true] = None
    """A Boolean value that specifies whether or not the schema extension is
    required for the resource type.

    If true, a resource of this type MUST include this schema extension
    and also include any attributes declared as required in this schema
    extension. If false, a resource of this type MAY omit this schema
    extension.
    """


class ResourceType(Resource[Any]):
    __schema__ = URN("urn:ietf:params:scim:schemas:core:2.0:ResourceType")

    name: Annotated[
        str | None,
        Mutability.read_only,
        Required.true,
        CaseExact.true,
        Uniqueness.server,
    ] = None
    """The resource type name.

    When applicable, service providers MUST specify the name, e.g.,
    'User'.
    """

    description: Annotated[str | None, Mutability.read_only] = None
    """The resource type's human-readable description.

    When applicable, service providers MUST specify the description.
    """

    id: Annotated[str | None, Mutability.read_only, Returned.default] = None
    """The resource type's server unique id.

    This is often the same value as the "name" attribute.
    """

    endpoint: Annotated[
        Reference[URI] | None, Mutability.read_only, Required.true, Uniqueness.server
    ] = None
    """The resource type's HTTP-addressable endpoint relative to the Base URL,
    e.g., '/Users'."""

    schema_: Annotated[
        Reference[URI] | None,
        Mutability.read_only,
        Required.true,
        CaseExact.true,
    ] = Field(None, alias="schema")
    """The resource type's primary/base schema URI."""

    schema_extensions: Annotated[
        list[SchemaExtension] | None, Mutability.read_only, Required.true
    ] = None
    """A list of URIs of the resource type's schema extensions."""

    @classmethod
    def from_resource(cls, resource_model: type[Resource[Any]]) -> Self:
        """Build a naive ResourceType from a resource model."""
        schema = resource_model.__schema__
        if schema is None:
            raise ValueError(f"{resource_model.__name__} has no __schema__ defined")
        name = schema.split(":")[-1]

        extensions = getattr(resource_model, "__scim_extension_metadata__", [])

        return cls(
            id=name,
            name=name,
            description=name,
            endpoint=Reference[URI](f"/{name}s"),
            schema_=Reference[URI](schema),
            schema_extensions=[
                SchemaExtension(
                    schema_=Reference[URI](extension.__schema__),
                    required=False,
                )
                for extension in extensions
            ],
        )
