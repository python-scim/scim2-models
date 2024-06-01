from enum import Enum
from typing import Annotated
from typing import List
from typing import Optional

from ..base import ComplexAttribute
from ..base import Mutability
from ..base import Returned
from ..base import Uniqueness
from .resource import Meta


class Attribute(ComplexAttribute):
    _attribute_urn: str = "urn:ietf:params:scim:schemas:core:2.0:Schema.attributes"

    class Type(str, Enum):
        string = "string"
        boolean = "boolean"
        decimal = "decimal"
        integer = "integer"
        date_time = "dateTime"
        reference = "reference"
        binary = "binary"
        complex = "complex"

    name: Annotated[str, Mutability.read_only]
    """The attribute's name."""

    type: Annotated[Type, Mutability.read_only]
    """The attribute's data type."""

    sub_attributes: Annotated[Optional[List["Attribute"]], Mutability.read_only] = None
    """When an attribute is of type "complex", "subAttributes" defines a set of
    sub-attributes."""

    multi_valued: Annotated[bool, Mutability.read_only]
    """A Boolean value indicating the attribute's plurality."""

    description: Annotated[str, Mutability.read_only]
    """The attribute's human-readable description."""

    required: Annotated[bool, Mutability.read_only]
    """A Boolean value that specifies whether or not the attribute is
    required."""

    canonical_values: Annotated[Optional[List[str]], Mutability.read_only] = None
    """A collection of suggested canonical values that MAY be used (e.g.,
    "work" and "home")."""

    case_exact: Annotated[bool, Mutability.read_only] = True
    """A Boolean value that specifies whether or not a string attribute is case
    sensitive."""

    mutability: Annotated[Mutability, Mutability.read_only] = Mutability.read_write
    """A single keyword indicating the circumstances under which the value of
    the attribute can be (re)defined."""

    returned: Annotated[Returned, Mutability.read_only] = Returned.default
    """A single keyword that indicates when an attribute and associated values
    are returned in response to a GET request or in response to a PUT, POST, or
    PATCH request."""

    uniqueness: Annotated[Uniqueness, Mutability.read_only] = Uniqueness.none
    """A single keyword value that specifies how the service provider enforces
    uniqueness of attribute values."""

    reference_types: Annotated[Optional[List[str]], Mutability.read_only] = None
    """A multi-valued array of JSON strings that indicate the SCIM resource
    types that may be referenced."""


class Schema(ComplexAttribute):
    schemas: List[str] = ["urn:ietf:params:scim:schemas:core:2.0:Schema"]

    meta: Annotated[Optional[Meta], Mutability.read_only] = None
    """A complex attribute containing resource metadata."""

    id: Annotated[str, Mutability.read_only]
    """The unique URI of the schema."""

    name: Annotated[Optional[str], Mutability.read_only] = None
    """The schema's human-readable name."""

    description: Annotated[Optional[str], Mutability.read_only] = None
    """The schema's human-readable description."""

    attributes: Annotated[List[Attribute], Mutability.read_only]
    """A complex type that defines service provider attributes and their
    qualities via the following set of sub-attributes."""
