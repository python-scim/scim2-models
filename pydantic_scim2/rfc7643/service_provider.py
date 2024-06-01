from enum import Enum
from typing import Annotated
from typing import List
from typing import Optional

from pydantic import AnyUrl

from ..base import ComplexAttribute
from ..base import Mutability
from ..base import Required
from .resource import Resource


class Patch(ComplexAttribute):
    supported: Annotated[bool, Mutability.read_only, Required.true]
    """A Boolean value specifying whether or not the operation is supported."""


class Bulk(ComplexAttribute):
    supported: Annotated[bool, Mutability.read_only, Required.true]
    """A Boolean value specifying whether or not the operation is supported."""

    max_operations: Annotated[int, Mutability.read_only, Required.true]
    """An integer value specifying the maximum number of operations."""

    max_payload_size: Annotated[int, Mutability.read_only, Required.true]
    """An integer value specifying the maximum payload size in bytes."""


class Filter(ComplexAttribute):
    supported: Annotated[bool, Mutability.read_only, Required.true]
    """A Boolean value specifying whether or not the operation is supported."""

    max_results: Annotated[Optional[int], Mutability.read_only, Required.true] = None
    """A Boolean value specifying whether or not the operation is supported."""


class ChangePassword(ComplexAttribute):
    supported: Annotated[bool, Mutability.read_only, Required.true]
    """A Boolean value specifying whether or not the operation is supported."""


class Sort(ComplexAttribute):
    supported: Annotated[bool, Mutability.read_only, Required.true]
    """A Boolean value specifying whether or not the operation is supported."""


class ETag(ComplexAttribute):
    supported: Annotated[bool, Mutability.read_only]
    """A Boolean value specifying whether or not the operation is supported."""


class AuthenticationScheme(ComplexAttribute):
    class Type(str, Enum):
        oauth = "oauth"
        oauth2 = "oauth2"
        oauthbearertoken = "oauthbearertoken"
        httpbasic = "httpbasic"
        httpdigest = "httpdigest"

    type: Annotated[Type, Mutability.read_only]
    """The authentication scheme."""

    name: Annotated[str, Mutability.read_only, Required.true]
    """The common authentication scheme name, e.g., HTTP Basic."""

    description: Annotated[str, Mutability.read_only, Required.true]
    """A description of the authentication scheme."""

    spec_uri: Annotated[Optional[AnyUrl], Mutability.read_only]
    """An HTTP-addressable URL pointing to the authentication scheme's
    specification."""

    documentation_uri: Annotated[Optional[AnyUrl], Mutability.read_only] = None
    """An HTTP-addressable URL pointing to the authentication scheme's usage
    documentation."""

    primary: Annotated[Optional[bool], Mutability.read_only] = None
    """A Boolean value indicating the 'primary' or preferred attribute value
    for this attribute, e.g., the preferred mailing address or primary email
    address."""


class ServiceProviderConfiguration(Resource):
    schemas: List[str] = ["urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig"]

    documentation_uri: Annotated[Optional[AnyUrl], Mutability.read_only] = None
    """An HTTP-addressable URL pointing to the service provider's human-
    consumable help documentation."""

    patch: Annotated[Patch, Mutability.read_only, Required.true]
    """A complex type that specifies PATCH configuration options."""

    bulk: Annotated[Bulk, Mutability.read_only, Required.true]
    """A complex type that specifies bulk configuration options."""

    filter: Annotated[Filter, Mutability.read_only, Required.true]
    """A complex type that specifies FILTER options."""

    change_password: Annotated[ChangePassword, Mutability.read_only, Required.true]
    """A complex type that specifies configuration options related to changing
    a password."""

    sort: Annotated[Sort, Mutability.read_only, Required.true]
    """A complex type that specifies sort result options."""

    etag: Annotated[ETag, Mutability.read_only]
    """A complex type that specifies ETag configuration options."""

    authentication_schemes: Annotated[
        List[AuthenticationScheme], Mutability.read_only, Required.true
    ]
    """A complex type that specifies supported authentication scheme
    properties."""
