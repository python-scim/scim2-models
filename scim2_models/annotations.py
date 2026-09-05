from enum import Enum


class Mutability(str, Enum):
    """A single keyword indicating the circumstances under which the value of the attribute can be (re)defined."""

    read_only = "readOnly"
    """The attribute SHALL NOT be modified.

    It is left out of a creation or a replacement request, and dropped from one
    that carries it anyway, rather than making the payload invalid. A PATCH
    operation targeting it is rejected.
    """

    read_write = "readWrite"
    """The attribute MAY be updated and read at any time.

    This is the implicit value of any attribute, per
    :rfc:`RFC7643 §2.2 <7643#section-2.2>`, and the only one carrying no
    constraint.
    """

    immutable = "immutable"
    """The attribute MAY be defined at resource creation (e.g., POST) or at
    record replacement via a request (e.g., a PUT).

    The attribute SHALL NOT be updated, so :meth:`~scim2_models.Resource.replace`
    and :meth:`~scim2_models.PatchOp.patch` raise a
    :class:`~scim2_models.MutabilityException` when an operation would change the
    value it already holds. Adding a value where there was none, asserting the
    current one, and removing an unset one are the operations left. The check
    happens as the change is applied, since it takes the current value, where a
    payload can only be read against the schema.
    """

    write_only = "writeOnly"
    """The attribute MAY be updated at any time.

    Attribute values SHALL NOT be returned (e.g., because the value is a
    stored hash).  Note: An attribute with a mutability of "writeOnly"
    usually also has a returned setting of "never".

    Unlike :attr:`read_only`, a query or a search request naming it is
    rejected rather than cleaned up, as a client cannot be reading a value it
    is not allowed to read.
    """

    _default = read_write


class Returned(str, Enum):
    """A single keyword that indicates when an attribute and associated values are returned in response to a GET request or in response to a PUT, POST, or PATCH request."""

    always = "always"  # cannot be excluded
    """The attribute is always returned, regardless of the contents of the
    "attributes" parameter.

    For example, "id" is always returned to identify a SCIM resource. It
    survives :attr:`ResponseParameters.excluded_attributes <scim2_models.ResponseParameters.excluded_attributes>`, and a response
    missing it is invalid.
    """

    never = "never"  # always excluded
    """The attribute is never returned, regardless of the contents of the
    "attributes" parameter.

    It is dropped from every response, and a response carrying it is invalid.
    """

    default = "default"  # included by default but can be excluded
    """The attribute is returned by default in all SCIM operation responses
    where attribute values are returned, unless it is explicitly excluded.

    This is the implicit value of any attribute, per
    :rfc:`RFC7643 §2.2 <7643#section-2.2>`. Both
    :attr:`ResponseParameters.attributes <scim2_models.ResponseParameters.attributes>` and
    :attr:`ResponseParameters.excluded_attributes <scim2_models.ResponseParameters.excluded_attributes>` bear on it.
    """

    request = "request"  # excluded by default but can be included
    """The attribute is returned in response to any PUT, POST, or PATCH
    operations if specified in the "attributes" parameter.

    Asking for it takes an exact match: an attribute requested through its
    parent complex attribute stays out.
    """

    _default = default


class Uniqueness(str, Enum):
    """A single keyword value that specifies how the service provider enforces uniqueness of attribute values.

    Unlike the other attribute characteristics, this one carries no validation:
    checking it takes the values a store already holds, which a model cannot
    know. It is a declaration, published by
    :meth:`~scim2_models.Resource.to_schema` and read back by
    :meth:`~scim2_models.Resource.from_schema`, that a service provider
    honours and whose violation it reports with
    :class:`~scim2_models.UniquenessException`.
    """

    none = "none"
    """The values are not intended to be unique in any way.

    This is the implicit value of any attribute, per
    :rfc:`RFC7643 §2.2 <7643#section-2.2>`.
    """

    server = "server"
    """The value SHOULD be unique within the context of the current SCIM
    endpoint (or tenancy) and MAY be globally unique (e.g., a "username", email
    address, or other server-generated key or counter).

    No two resources on the same server SHOULD possess the same value. This is
    what :attr:`User.user_name <scim2_models.User.user_name>` carries.
    """

    global_ = "global"
    """The value SHOULD be globally unique (e.g., an email address, a GUID, or
    other value).

    No two resources on any server SHOULD possess the same value. This is what
    :attr:`Resource.id <scim2_models.Resource.id>` carries, an identifier a
    client may store alongside resources coming from several servers.
    """

    _default = none


class Required(Enum):
    """A Boolean value that specifies whether the attribute is required or not.

    Missing required attributes raise a :class:`~pydantic_core.ValidationError` on :attr:`~scim2_models.Context.RESOURCE_CREATION_REQUEST` and :attr:`~scim2_models.Context.RESOURCE_REPLACEMENT_REQUEST` validations.
    """

    true = True
    """The attribute must carry a value in a creation or a replacement request.

    A PATCH operation that removes it is rejected too, as
    :rfc:`RFC7644 §3.5.2.2 <7644#section-3.5.2.2>` has a server answer
    ``mutability`` when a required attribute becomes unassigned.
    """

    false = False
    """The attribute may be absent.

    This is the implicit value of any attribute, per
    :rfc:`RFC7643 §2.2 <7643#section-2.2>`.
    """

    _default = false

    def __bool__(self) -> bool:
        return self.value


class CaseExact(Enum):
    """A Boolean value that specifies whether a string attribute is case-sensitive or not."""

    true = True
    """Values of the attribute are compared with their case.

    ``binary`` and ``reference`` attributes are case-exact whatever their schema
    says, per :rfc:`RFC7643 §2.3.6 <7643#section-2.3.6>` and
    :rfc:`§2.3.7 <7643#section-2.3.7>`. Comparing is up to the service provider;
    what this library does with the annotation is publish it in
    :meth:`~scim2_models.Resource.to_schema`.
    """

    false = False
    """Values of the attribute are compared without their case.

    This is the implicit value of any other attribute, per
    :rfc:`RFC7643 §2.2 <7643#section-2.2>`. Values are kept as they were
    submitted either way.
    """

    _default = false

    def __bool__(self) -> bool:
        return self.value
