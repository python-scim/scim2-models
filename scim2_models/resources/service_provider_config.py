from enum import Enum
from typing import Annotated
from typing import Any

from pydantic import Field

from ..annotations import Mutability
from ..annotations import Required
from ..annotations import Returned
from ..annotations import Uniqueness
from ..attributes import ComplexAttribute
from ..path import URN
from ..reference import External
from ..reference import Reference
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


class AuthenticationScheme(ComplexAttribute):
    class Type(str, Enum):
        oauth = "oauth"
        oauth2 = "oauth2"
        oauthbearertoken = "oauthbearertoken"
        httpbasic = "httpbasic"
        httpdigest = "httpdigest"

    type: Annotated[Type | None, Mutability.read_only, Required.true] = Field(
        None,
        examples=["oauth", "oauth2", "oauthbearertoken", "httpbasic", "httpdigest"],
    )
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
