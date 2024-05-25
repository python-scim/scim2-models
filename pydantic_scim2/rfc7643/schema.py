from enum import Enum
from typing import List
from typing import Optional

from ..base import SCIM2Model
from .resource import Meta


class Mutability(str, Enum):
    read_only = "readOnly"
    read_write = "readWrite"
    immutable = "immutable"
    write_only = "writeOnly"


class Returned(str, Enum):
    always = "always"
    never = "never"
    default = "default"
    request = "request"


class Uniqueness(str, Enum):
    none = "none"
    server = "server"
    global_ = "global"


class Attribute(SCIM2Model):
    class Type(str, Enum):
        string = "string"
        boolean = "boolean"
        decimal = "decimal"
        integer = "integer"
        date_time = "dateTime"
        reference = "reference"
        binary = "binary"
        complex = "complex"

    name: str
    """The attribute's name."""

    type: Type
    """The attribute's data type."""

    sub_attributes: Optional[List["Attribute"]] = None
    """When an attribute is of type "complex", "subAttributes" defines a set of
    sub-attributes."""

    multi_valued: bool
    """A Boolean value indicating the attribute's plurality."""

    description: str
    """The attribute's human-readable description."""

    required: bool
    """A Boolean value that specifies whether or not the attribute is
    required."""

    canonical_values: Optional[List[str]] = None
    """A collection of suggested canonical values that MAY be used (e.g.,
    "work" and "home")."""

    case_exact: bool = True
    """A Boolean value that specifies whether or not a string attribute is case
    sensitive."""

    mutability: Mutability = Mutability.read_write
    """A single keyword indicating the circumstances under which the value of
    the attribute can be (re)defined."""

    returned: Returned = Returned.default
    """A single keyword that indicates when an attribute and associated values
    are returned in response to a GET request or in response to a PUT, POST, or
    PATCH request."""

    uniqueness: Uniqueness = Uniqueness.none
    """A single keyword value that specifies how the service provider enforces
    uniqueness of attribute values."""

    reference_types: Optional[List[str]] = None
    """A multi-valued array of JSON strings that indicate the SCIM resource
    types that may be referenced."""


class Schema(SCIM2Model):
    schemas: List[str] = ["urn:ietf:params:scim:schemas:core:2.0:Schema"]

    id: str
    """The unique URI of the schema."""

    name: Optional[str] = None
    """The schema's human-readable name."""

    description: Optional[str] = None
    """The schema's human-readable description."""

    attributes: List[Attribute]
    """A complex type that defines service provider attributes and their
    qualities via the following set of sub-attributes."""

    meta: Optional[Meta] = None
    """A complex attribute containing resource metadata."""
