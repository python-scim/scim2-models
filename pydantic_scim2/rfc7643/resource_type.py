from typing import Annotated
from typing import List
from typing import Optional

from pydantic import AnyUrl
from pydantic import Field

from ..base import ComplexAttribute
from ..base import Mutability
from ..base import Required
from .resource import Resource


class SchemaExtension(ComplexAttribute):
    _attribute_urn: str = (
        "urn:ietf:params:scim:schemas:core:2.0:ResourceType.schemaExtensions"
    )

    schema_: Annotated[AnyUrl, Mutability.read_only, Required.true] = Field(
        ..., alias="schema"
    )
    """The URI of a schema extension."""

    required: Annotated[bool, Mutability.read_only, Required.true]
    """A Boolean value that specifies whether or not the schema extension is
    required for the resource type.

    If true, a resource of this type MUST include this schema extension
    and also include any attributes declared as required in this schema
    extension. If false, a resource of this type MAY omit this schema
    extension.
    """


class ResourceType(Resource):
    schemas: List[str] = ["urn:ietf:params:scim:schemas:core:2.0:ResourceType"]

    id: Annotated[Optional[str], Mutability.read_only] = None
    """The resource type's server unique id.

    May be the same as the 'name' attribute.
    """

    name: Annotated[str, Mutability.read_only, Required.true]
    """The resource type name.

    When applicable, service providers MUST specify the name, e.g.,
    'User'.
    """

    description: Annotated[Optional[str], Mutability.read_only] = None
    """The resource type's human-readable description.

    When applicable, service providers MUST specify the description.
    """

    endpoint: Annotated[str, Mutability.read_only, Required.true]
    """The resource type's HTTP-addressable endpoint relative to the Base URL,
    e.g., '/Users'."""

    schema_: Annotated[AnyUrl, Mutability.read_only, Required.true] = Field(
        ..., alias="schema"
    )
    """The resource type's primary/base schema URI."""

    schema_extensions: Annotated[
        Optional[List[SchemaExtension]], Mutability.read_only, Required.true
    ] = None
    """A list of URIs of the resource type's schema extensions."""
