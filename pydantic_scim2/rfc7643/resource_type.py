from typing import List
from typing import Optional

from pydantic import AnyUrl
from pydantic import Field

from ..base import SCIM2Model
from .resource import Meta
from .resource import Resource


class SchemaExtension(SCIM2Model):
    schema_: AnyUrl = Field(..., alias="schema")
    """The URI of a schema extension."""

    required: bool
    """A Boolean value that specifies whether or not the schema extension is
    required for the resource type.

    If true, a resource of this type MUST include this schema extension
    and also include any attributes declared as required in this schema
    extension. If false, a resource of this type MAY omit this schema
    extension.
    """


class ResourceType(Resource):
    schemas: List[str] = ["urn:ietf:params:scim:schemas:core:2.0:ResourceType"]

    # Each SCIM resource (Users, Groups, etc.) includes the following
    # common attributes.  With the exception of the "ServiceProviderConfig"
    # and "ResourceType" server discovery endpoints and their associated
    # resources, these attributes MUST be defined for all resources,
    # including any extended resource types.

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

    id: Optional[str] = None
    """The resource type's server unique id.

    May be the same as the 'name' attribute.
    """

    name: str
    """The resource type name.

    When applicable, service providers MUST specify the name, e.g.,
    'User'.
    """

    description: Optional[str] = None
    """The resource type's human-readable description.

    When applicable, service providers MUST specify the description.
    """

    endpoint: str
    """The resource type's HTTP-addressable endpoint relative to the Base URL,
    e.g., '/Users'."""

    schema_: AnyUrl = Field(..., alias="schema")
    """The resource type's primary/base schema URI."""

    schema_extensions: Optional[List[SchemaExtension]] = None
    """A list of URIs of the resource type's schema extensions."""
