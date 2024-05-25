from enum import Enum
from typing import List
from typing import Optional

from pydantic import AnyUrl

from .base import SCIM2Model
from .resource import Meta
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
    # Each SCIM resource (Users, Groups, etc.) includes the following
    # common attributes.  With the exception of the "ServiceProviderConfig"
    # and "ResourceType" server discovery endpoints and their associated
    # resources, these attributes MUST be defined for all resources,
    # including any extended resource types.

    schemas: List[str] = ["urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig"]

    id: Optional[str] = None
    """A unique identifier for a SCIM resource as defined by the service
    provider.

    Each representation of the resource MUST include a non-empty "id"
    value.  This identifier MUST be unique across the SCIM service
    provider's entire set of resources.  It MUST be a stable, non-
    reassignable identifier that does not change when the same resource
    is returned in subsequent requests.  The value of the "id" attribute
    is always issued by the service provider and MUST NOT be specified
    by the client.  The string "bulkId" is a reserved keyword and MUST
    NOT be used within any unique identifier value.  The attribute
    characteristics are "caseExact" as "true", a mutability of
    "readOnly", and a "returned" characteristic of "always".  See
    Section 9 for additional considerations regarding privacy.
    """

    external_id: Optional[str] = None
    """A String that is an identifier for the resource as defined by the
    provisioning client.

    The "externalId" may simplify identification of a resource between
    the provisioning client and the service provider by allowing the
    client to use a filter to locate the resource with an identifier
    from the provisioning domain, obviating the need to store a local
    mapping between the provisioning domain's identifier of the resource
    and the identifier used by the service provider.  Each resource MAY
    include a non-empty "externalId" value.  The value of the
    "externalId" attribute is always issued by the provisioning client
    and MUST NOT be specified by the service provider.  The service
    provider MUST always interpret the externalId as scoped to the
    provisioning domain.  While the server does not enforce uniqueness,
    it is assumed that the value's uniqueness is controlled by the
    client setting the value.  See Section 9 for additional
    considerations regarding privacy.  This attribute has "caseExact" as
    "true" and a mutability of "readWrite".  This attribute is OPTIONAL.
    """

    meta: Optional[Meta] = None
    """A complex attribute containing resource metadata."""

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
