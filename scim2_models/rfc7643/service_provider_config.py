from enum import Enum
from typing import Annotated
from typing import Optional

from pydantic import Field

from ..base import ComplexAttribute
from ..base import ExternalReference
from ..base import Mutability
from ..base import Reference
from ..base import Required
from ..base import Returned
from ..base import Uniqueness
from .resource import Resource


class Patch(ComplexAttribute):
    supported: Annotated[Optional[bool], Mutability.read_only, Required.true] = None
    """A Boolean value specifying whether or not the operation is supported."""


class Bulk(ComplexAttribute):
    supported: Annotated[Optional[bool], Mutability.read_only, Required.true] = None
    """A Boolean value specifying whether or not the operation is supported."""

    max_operations: Annotated[Optional[int], Mutability.read_only, Required.true] = None
    """An integer value specifying the maximum number of operations."""

    max_payload_size: Annotated[Optional[int], Mutability.read_only, Required.true] = (
        None
    )
    """An integer value specifying the maximum payload size in bytes."""


class Filter(ComplexAttribute):
    supported: Annotated[Optional[bool], Mutability.read_only, Required.true] = None
    """A Boolean value specifying whether or not the operation is supported."""

    max_results: Annotated[Optional[int], Mutability.read_only, Required.true] = None
    """A Boolean value specifying whether or not the operation is supported."""


class ChangePassword(ComplexAttribute):
    supported: Annotated[Optional[bool], Mutability.read_only, Required.true] = None
    """A Boolean value specifying whether or not the operation is supported."""


class Sort(ComplexAttribute):
    supported: Annotated[Optional[bool], Mutability.read_only, Required.true] = None
    """A Boolean value specifying whether or not the operation is supported."""


class ETag(ComplexAttribute):
    supported: Annotated[Optional[bool], Mutability.read_only, Required.true] = None
    """A Boolean value specifying whether or not the operation is supported."""


class AuthenticationScheme(ComplexAttribute):
    class Type(str, Enum):
        oauth = "oauth"
        oauth2 = "oauth2"
        oauthbearertoken = "oauthbearertoken"
        httpbasic = "httpbasic"
        httpdigest = "httpdigest"

    type: Annotated[Optional[Type], Mutability.read_only, Required.true] = Field(
        None,
        examples=["oauth", "oauth2", "oauthbreakertoken", "httpbasic", "httpdigest"],
    )
    """The authentication scheme."""

    name: Annotated[Optional[str], Mutability.read_only, Required.true] = None
    """The common authentication scheme name, e.g., HTTP Basic."""

    description: Annotated[Optional[str], Mutability.read_only, Required.true] = None
    """A description of the authentication scheme."""

    spec_uri: Annotated[
        Optional[Reference[ExternalReference]], Mutability.read_only
    ] = None
    """An HTTP-addressable URL pointing to the authentication scheme's
    specification."""

    documentation_uri: Annotated[
        Optional[Reference[ExternalReference]], Mutability.read_only
    ] = None
    """An HTTP-addressable URL pointing to the authentication scheme's usage
    documentation."""

    primary: Annotated[Optional[bool], Mutability.read_only] = None
    """A Boolean value indicating the 'primary' or preferred attribute value
    for this attribute, e.g., the preferred mailing address or primary email
    address."""


class ServiceProviderConfig(Resource):
    schemas: Annotated[list[str], Required.true] = [
        "urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig"
    ]

    id: Annotated[
        Optional[str], Mutability.read_only, Returned.default, Uniqueness.global_
    ] = None
    """A unique identifier for a SCIM resource as defined by the service
    provider."""
    # RFC7643 §5
    #     Unlike other core
    #     resources, the "id" attribute is not required for the service
    #     provider configuration resource

    documentation_uri: Annotated[
        Optional[Reference[ExternalReference]], Mutability.read_only
    ] = None
    """An HTTP-addressable URL pointing to the service provider's human-
    consumable help documentation."""

    patch: Annotated[Optional[Patch], Mutability.read_only, Required.true] = None
    """A complex type that specifies PATCH configuration options."""

    bulk: Annotated[Optional[Bulk], Mutability.read_only, Required.true] = None
    """A complex type that specifies bulk configuration options."""

    filter: Annotated[Optional[Filter], Mutability.read_only, Required.true] = None
    """A complex type that specifies FILTER options."""

    change_password: Annotated[
        Optional[ChangePassword], Mutability.read_only, Required.true
    ] = None
    """A complex type that specifies configuration options related to changing
    a password."""

    sort: Annotated[Optional[Sort], Mutability.read_only, Required.true] = None
    """A complex type that specifies sort result options."""

    etag: Annotated[Optional[ETag], Mutability.read_only, Required.true] = None
    """A complex type that specifies ETag configuration options."""

    authentication_schemes: Annotated[
        Optional[list[AuthenticationScheme]], Mutability.read_only, Required.true
    ] = None
    """A complex type that specifies supported authentication scheme
    properties."""
