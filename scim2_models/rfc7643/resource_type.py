from typing import Annotated
from typing import List
from typing import Optional

from pydantic import Field

from ..base import CaseExact
from ..base import ComplexAttribute
from ..base import Mutability
from ..base import Reference
from ..base import Required
from ..base import Returned
from ..base import Uniqueness
from .resource import Resource


class SchemaExtension(ComplexAttribute):
    schema_: Annotated[
        Reference, Mutability.read_only, Required.true, CaseExact.true
    ] = Field(None, alias="schema")
    """The URI of a schema extension."""

    required: Annotated[bool, Mutability.read_only, Required.true] = None
    """A Boolean value that specifies whether or not the schema extension is
    required for the resource type.

    If true, a resource of this type MUST include this schema extension
    and also include any attributes declared as required in this schema
    extension. If false, a resource of this type MAY omit this schema
    extension.
    """


class ResourceType(Resource):
    schemas: List[str] = ["urn:ietf:params:scim:schemas:core:2.0:ResourceType"]

    id: Annotated[
        Optional[str], Mutability.read_only, Returned.default, Uniqueness.global_
    ] = None
    """The resource type's server unique id.

    This is often the same value as the "name" attribute.
    """

    name: Annotated[str, Mutability.read_only, Required.true] = None
    """The resource type name.

    When applicable, service providers MUST specify the name, e.g.,
    'User'.
    """

    description: Annotated[Optional[str], Mutability.read_only] = None
    """The resource type's human-readable description.

    When applicable, service providers MUST specify the description.
    """

    endpoint: Annotated[str, Mutability.read_only, Required.true] = None
    """The resource type's HTTP-addressable endpoint relative to the Base URL,
    e.g., '/Users'."""

    schema_: Annotated[
        Reference, Mutability.read_only, Required.true, CaseExact.true
    ] = Field(None, alias="schema")
    """The resource type's primary/base schema URI."""

    schema_extensions: Annotated[
        Optional[List[SchemaExtension]], Mutability.read_only, Required.true
    ] = None
    """A list of URIs of the resource type's schema extensions."""
