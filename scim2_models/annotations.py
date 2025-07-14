from enum import Enum


class Mutability(str, Enum):
    """A single keyword indicating the circumstances under which the value of the attribute can be (re)defined."""

    read_only = "readOnly"
    """The attribute SHALL NOT be modified."""

    read_write = "readWrite"
    """The attribute MAY be updated and read at any time."""

    immutable = "immutable"
    """The attribute MAY be defined at resource creation (e.g., POST) or at
    record replacement via a request (e.g., a PUT).

    The attribute SHALL NOT be updated.
    """

    write_only = "writeOnly"
    """The attribute MAY be updated at any time.

    Attribute values SHALL NOT be returned (e.g., because the value is a
    stored hash).  Note: An attribute with a mutability of "writeOnly"
    usually also has a returned setting of "never".
    """

    _default = read_write


class Returned(str, Enum):
    """A single keyword that indicates when an attribute and associated values are returned in response to a GET request or in response to a PUT, POST, or PATCH request."""

    always = "always"  # cannot be excluded
    """The attribute is always returned, regardless of the contents of the
    "attributes" parameter.

    For example, "id" is always returned to identify a SCIM resource.
    """

    never = "never"  # always excluded
    """The attribute is never returned, regardless of the contents of the
    "attributes" parameter."""

    default = "default"  # included by default but can be excluded
    """The attribute is returned by default in all SCIM operation responses
    where attribute values are returned, unless it is explicitly excluded."""

    request = "request"  # excluded by default but can be included
    """The attribute is returned in response to any PUT, POST, or PATCH
    operations if specified in the "attributes" parameter."""

    _default = default


class Uniqueness(str, Enum):
    """A single keyword value that specifies how the service provider enforces uniqueness of attribute values."""

    none = "none"
    """The values are not intended to be unique in any way."""

    server = "server"
    """The value SHOULD be unique within the context of the current SCIM
    endpoint (or tenancy) and MAY be globally unique (e.g., a "username", email
    address, or other server-generated key or counter).

    No two resources on the same server SHOULD possess the same value.
    """

    global_ = "global"
    """The value SHOULD be globally unique (e.g., an email address, a GUID, or
    other value).

    No two resources on any server SHOULD possess the same value.
    """

    _default = none


class Required(Enum):
    """A Boolean value that specifies whether the attribute is required or not.

    Missing required attributes raise a :class:`~pydantic.ValidationError` on :attr:`~scim2_models.Context.RESOURCE_CREATION_REQUEST` and :attr:`~scim2_models.Context.RESOURCE_REPLACEMENT_REQUEST` validations.
    """

    true = True
    false = False

    _default = false

    def __bool__(self) -> bool:
        return self.value


class CaseExact(Enum):
    """A Boolean value that specifies whether a string attribute is case- sensitive or not."""

    true = True
    false = False

    _default = false

    def __bool__(self) -> bool:
        return self.value
