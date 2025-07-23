from typing import Annotated
from typing import Optional

from pydantic import Field
from typing_extensions import Self

from ..annotations import CaseExact
from ..annotations import Mutability
from ..annotations import Required
from ..annotations import Returned
from ..attributes import ComplexAttribute
from ..reference import Reference
from ..reference import URIReference
from .resource import Resource


class SchemaExtension(ComplexAttribute):
    schema_: Annotated[
        Optional[Reference[URIReference]],
        Mutability.read_only,
        Required.true,
        CaseExact.true,
    ] = Field(None, alias="schema")
    """The URI of a schema extension."""

    required: Annotated[Optional[bool], Mutability.read_only, Required.true] = None
    """A Boolean value that specifies whether or not the schema extension is
    required for the resource type.

    If true, a resource of this type MUST include this schema extension
    and also include any attributes declared as required in this schema
    extension. If false, a resource of this type MAY omit this schema
    extension.
    """


class ResourceType(Resource):
    schemas: Annotated[list[str], Required.true] = [
        "urn:ietf:params:scim:schemas:core:2.0:ResourceType"
    ]

    name: Annotated[Optional[str], Mutability.read_only, Required.true] = None
    """The resource type name.

    When applicable, service providers MUST specify the name, e.g.,
    'User'.
    """

    description: Annotated[Optional[str], Mutability.read_only] = None
    """The resource type's human-readable description.

    When applicable, service providers MUST specify the description.
    """

    id: Annotated[Optional[str], Mutability.read_only, Returned.default] = None
    """The resource type's server unique id.

    This is often the same value as the "name" attribute.
    """

    endpoint: Annotated[
        Optional[Reference[URIReference]], Mutability.read_only, Required.true
    ] = None
    """The resource type's HTTP-addressable endpoint relative to the Base URL,
    e.g., '/Users'."""

    schema_: Annotated[
        Optional[Reference[URIReference]],
        Mutability.read_only,
        Required.true,
        CaseExact.true,
    ] = Field(None, alias="schema")
    """The resource type's primary/base schema URI."""

    schema_extensions: Annotated[
        Optional[list[SchemaExtension]], Mutability.read_only, Required.true
    ] = None
    """A list of URIs of the resource type's schema extensions."""

    @classmethod
    def from_resource(cls, resource_model: type[Resource]) -> Self:
        """Build a naive ResourceType from a resource model."""
        schema = resource_model.model_fields["schemas"].default[0]
        name = schema.split(":")[-1]

        # Get extensions from the metadata system
        extensions = getattr(resource_model, "__scim_extension_metadata__", [])

        return cls(
            id=name,
            name=name,
            description=name,
            endpoint=Reference[URIReference](f"/{name}s"),
            schema_=schema,
            schema_extensions=[
                SchemaExtension(
                    schema_=extension.model_fields["schemas"].default[0], required=False
                )
                for extension in extensions
            ],
        )
