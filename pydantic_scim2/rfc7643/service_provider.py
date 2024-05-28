from enum import Enum
from typing import List
from typing import Optional

from pydantic import AnyUrl

from ..base import SCIM2Model
from .resource import Resource


class Patch(SCIM2Model):
    supported: bool
    """A Boolean value specifying whether or not the operation is supported."""


class Bulk(SCIM2Model):
    supported: bool
    """A Boolean value specifying whether or not the operation is supported."""

    max_operations: int
    """An integer value specifying the maximum number of operations."""

    max_payload_size: int
    """An integer value specifying the maximum payload size in bytes."""


class Filter(SCIM2Model):
    supported: bool
    """A Boolean value specifying whether or not the operation is supported."""

    max_results: Optional[int] = None
    """A Boolean value specifying whether or not the operation is supported."""


class ChangePassword(SCIM2Model):
    supported: bool
    """A Boolean value specifying whether or not the operation is supported."""


class Sort(SCIM2Model):
    supported: bool
    """A Boolean value specifying whether or not the operation is supported."""


class ETag(SCIM2Model):
    supported: bool
    """A Boolean value specifying whether or not the operation is supported."""


class AuthenticationScheme(SCIM2Model):
    class Type(str, Enum):
        oauth = "oauth"
        oauth2 = "oauth2"
        oauthbearertoken = "oauthbearertoken"
        httpbasic = "httpbasic"
        httpdigest = "httpdigest"

    type: Type
    """The authentication scheme."""

    name: str
    """The common authentication scheme name, e.g., HTTP Basic."""

    description: str
    """A description of the authentication scheme."""

    spec_uri: Optional[AnyUrl]
    """An HTTP-addressable URL pointing to the authentication scheme's
    specification."""

    documentation_uri: Optional[AnyUrl] = None
    """An HTTP-addressable URL pointing to the authentication scheme's usage
    documentation."""

    primary: Optional[bool] = None
    """A Boolean value indicating the 'primary' or preferred attribute value
    for this attribute, e.g., the preferred mailing address or primary email
    address.

    The primary attribute value 'true' MUST appear no more than once.
    """


class ServiceProviderConfiguration(Resource):
    schemas: List[str] = ["urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig"]

    documentation_uri: Optional[AnyUrl] = None
    """An HTTP-addressable URL pointing to the service provider's human-
    consumable help documentation."""

    patch: Patch
    """A complex type that specifies PATCH configuration options."""

    bulk: Bulk
    """A complex type that specifies bulk configuration options."""

    filter: Filter
    """A complex type that specifies FILTER options."""

    change_password: ChangePassword
    """A complex type that specifies configuration options related to changing
    a password."""

    sort: Sort
    """A complex type that specifies sort result options."""

    etag: ETag
    """A complex type that specifies ETag configuration options."""

    authentication_schemes: List[AuthenticationScheme]
    """A complex type that specifies supported authentication scheme
    properties."""
