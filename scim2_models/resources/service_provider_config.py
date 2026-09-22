from typing import Annotated
from typing import Any

from pydantic import field_validator

from ..annotations import Mutability
from ..annotations import Required
from ..annotations import Returned
from ..annotations import Uniqueness
from ..attributes import ComplexAttribute
from ..attributes import ExtensibleStringEnum
from ..exceptions import SCIMException
from ..reference import External
from ..reference import Reference
from ..urn import URN
from .resource import Resource


class Patch(ComplexAttribute):
    supported: Annotated[bool | None, Mutability.read_only, Required.true] = None
    """A Boolean value specifying whether or not the operation is supported."""


class Bulk(ComplexAttribute):
    supported: Annotated[bool | None, Mutability.read_only, Required.true] = None
    """A Boolean value specifying whether or not the operation is supported."""

    max_operations: Annotated[int | None, Mutability.read_only, Required.true] = None
    """An integer value specifying the maximum number of operations."""

    max_payload_size: Annotated[int | None, Mutability.read_only, Required.true] = None
    """An integer value specifying the maximum payload size in bytes."""


class Filter(ComplexAttribute):
    supported: Annotated[bool | None, Mutability.read_only, Required.true] = None
    """A Boolean value specifying whether or not the operation is supported."""

    max_results: Annotated[int | None, Mutability.read_only, Required.true] = None
    """An integer value specifying the maximum number of resources returned in a response."""


class ChangePassword(ComplexAttribute):
    supported: Annotated[bool | None, Mutability.read_only, Required.true] = None
    """A Boolean value specifying whether or not the operation is supported."""


class Sort(ComplexAttribute):
    supported: Annotated[bool | None, Mutability.read_only, Required.true] = None
    """A Boolean value specifying whether or not the operation is supported."""


class ETag(ComplexAttribute):
    supported: Annotated[bool | None, Mutability.read_only, Required.true] = None
    """A Boolean value specifying whether or not the operation is supported."""


class Pagination(ComplexAttribute):
    class DefaultPaginationMethod(ExtensibleStringEnum):
        cursor = "cursor"
        index = "index"

    cursor: Annotated[bool | None, Mutability.read_only, Required.true] = None
    """A Boolean value specifying support of cursor-based pagination."""

    index: Annotated[bool | None, Mutability.read_only, Required.true] = None
    """A Boolean value specifying support of index-based pagination."""

    default_pagination_method: Annotated[
        DefaultPaginationMethod | None, Mutability.read_only
    ] = None
    """A string value specifying the type of pagination that the service provider defaults to when the client has not specified which method it wishes to use. Possible values are "cursor" and "index"."""

    default_page_size: Annotated[int | None, Mutability.read_only] = None
    """Positive integer value specifying the default number of results returned in a page when a count is not specified in the query."""

    max_page_size: Annotated[int | None, Mutability.read_only] = None
    """Positive integer specifying the maximum number of results returned in a page regardless of what is specified for the count in a query. The maximum number of results returned may be further restricted by other criteria."""

    cursor_timeout: Annotated[int | None, Mutability.read_only] = None
    """Positive integer specifying the minimum number of seconds that a cursor is valid between page requests. Clients waiting too long between cursor pagination requests may receive an invalid cursor error response. No value being specified may mean that there is no cursor timeout or that the cursor timeout is not a static duration."""

    @field_validator("default_page_size", "max_page_size", "cursor_timeout")
    @classmethod
    def validate_positive_integers(cls, value: int | None) -> int | None:
        if value is not None and value <= 0:
                raise SCIMException(
                    path=str(value), detail=f"{str(value)!r} is not a positive integer"
                ).as_pydantic_error()
        return value

class AuthenticationScheme(ComplexAttribute):
    class Type(ExtensibleStringEnum):
        oauth = "oauth"
        oauth2 = "oauth2"
        oauthbearertoken = "oauthbearertoken"
        httpbasic = "httpbasic"
        httpdigest = "httpdigest"

    type: Annotated[Type | None, Mutability.read_only, Required.true] = None
    """The authentication scheme."""

    name: Annotated[str | None, Mutability.read_only, Required.true] = None
    """The common authentication scheme name, e.g., HTTP Basic."""

    description: Annotated[str | None, Mutability.read_only, Required.true] = None
    """A description of the authentication scheme."""

    spec_uri: Annotated[Reference[External] | None, Mutability.read_only] = None
    """An HTTP-addressable URL pointing to the authentication scheme's
    specification."""

    documentation_uri: Annotated[Reference[External] | None, Mutability.read_only] = (
        None
    )
    """An HTTP-addressable URL pointing to the authentication scheme's usage
    documentation."""

    primary: Annotated[bool | None, Mutability.read_only] = None
    """A Boolean value indicating the 'primary' or preferred attribute value
    for this attribute, e.g., the preferred mailing address or primary email
    address."""


class ServiceProviderConfig(Resource[Any]):
    __schema__ = URN("urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig")

    id: Annotated[
        str | None, Mutability.read_only, Returned.default, Uniqueness.global_
    ] = None
    """A unique identifier for a SCIM resource as defined by the service
    provider."""
    # RFC7643 §5
    #     Unlike other core
    #     resources, the "id" attribute is not required for the service
    #     provider configuration resource

    documentation_uri: Annotated[Reference[External] | None, Mutability.read_only] = (
        None
    )
    """An HTTP-addressable URL pointing to the service provider's human-
    consumable help documentation."""

    patch: Annotated[Patch | None, Mutability.read_only, Required.true] = None
    """A complex type that specifies PATCH configuration options."""

    bulk: Annotated[Bulk | None, Mutability.read_only, Required.true] = None
    """A complex type that specifies bulk configuration options."""

    filter: Annotated[Filter | None, Mutability.read_only, Required.true] = None
    """A complex type that specifies FILTER options."""

    change_password: Annotated[
        ChangePassword | None, Mutability.read_only, Required.true
    ] = None
    """A complex type that specifies configuration options related to changing
    a password."""

    sort: Annotated[Sort | None, Mutability.read_only, Required.true] = None
    """A complex type that specifies sort result options."""

    etag: Annotated[ETag | None, Mutability.read_only, Required.true] = None
    """A complex type that specifies ETag configuration options."""

    authentication_schemes: Annotated[
        list[AuthenticationScheme] | None, Mutability.read_only, Required.true
    ] = None
    """A complex type that specifies supported authentication scheme
    properties."""

    pagination: Annotated[Pagination | None, Mutability.read_only] = None
    """A complex type that specifies pagination configuration options."""
