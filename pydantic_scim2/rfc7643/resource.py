from datetime import datetime
from typing import Any
from typing import Generic
from typing import List
from typing import Optional
from typing import TypeVar

from pydantic import ConfigDict
from pydantic import field_serializer
from pydantic import model_validator
from typing_extensions import Self

from ..base import SCIM2Model

T = TypeVar("T", SCIM2Model, Any)


class Meta(SCIM2Model):
    """All "meta" sub-attributes are assigned by the service provider (have a
    "mutability" of "readOnly"), and all of these sub-attributes have a
    "returned" characteristic of "default".

    This attribute SHALL be
    ignored when provided by clients.  "meta" contains the following
    sub-attributes:
    """

    resource_type: Optional[str] = None
    """The name of the resource type of the resource.

    This attribute has a mutability of "readOnly" and "caseExact" as
    "true".
    """

    created: Optional[datetime] = None
    """The "DateTime" that the resource was added to the service provider.

    This attribute MUST be a DateTime.
    """

    last_modified: Optional[datetime] = None
    """The most recent DateTime that the details of this resource were updated
    at the service provider.

    If this resource has never been modified since its initial creation,
    the value MUST be the same as the value of "created".
    """

    location: Optional[str] = None
    """The URI of the resource being returned.

    This value MUST be the same as the "Content-Location" HTTP response
    header (see Section 3.1.4.2 of [RFC7231]).
    """

    version: Optional[str] = None
    """The version of the resource being returned.

    This value must be the same as the entity-tag (ETag) HTTP response
    header (see Sections 2.1 and 2.3 of [RFC7232]).  This attribute has
    "caseExact" as "true".  Service provider support for this attribute
    is optional and subject to the service provider's support for
    versioning (see Section 3.14 of [RFC7644]).  If a service provider
    provides "version" (entity-tag) for a representation and the
    generation of that entity-tag does not satisfy all of the
    characteristics of a strong validator (see Section 2.1 of
    [RFC7232]), then the origin server MUST mark the "version" (entity-
    tag) as weak by prefixing its opaque value with "W/" (case
    sensitive).
    """


class Resource(SCIM2Model, Generic[T]):
    model_config = ConfigDict(extra="allow")

    schemas: List[str]
    """The "schemas" attribute is a REQUIRED attribute and is an array of
    Strings containing URIs that are used to indicate the namespaces of the
    SCIM schemas that define the attributes present in the current JSON
    structure.

    This attribute may be used by parsers to define the attributes
    present in the JSON structure that is the body to an HTTP request or
    response.  Each String value must be a unique URI.  All
    representations of SCIM schemas MUST include a non-empty array with
    value(s) of the URIs supported by that representation.  The
    "schemas" attribute for a resource MUST only contain values defined
    as "schema" and "schemaExtensions" for the resource's defined
    "resourceType".  Duplicate values MUST NOT be included.  Value order
    is not specified and MUST NOT impact behavior.
    """

    # Common attributes as defined by
    # https://www.rfc-editor.org/rfc/rfc7643#section-3.1
    id: str
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

    meta: Meta
    """A complex attribute containing resource metadata."""

    def __getitem__(self, item):
        schema = item.model_fields["schemas"].default[0]

        if not hasattr(self, schema):
            setattr(self, schema, item())

        return getattr(self, schema)

    def __setitem__(self, item: type, value: "Resource"):
        schema = item.model_fields["schemas"].default[0]
        setattr(self, schema, value)

    @model_validator(mode="after")
    def load_model_extensions(self) -> Self:
        """Instanciate schema objects if found in the payload."""

        extension_models = self.__pydantic_generic_metadata__.get("args")
        if not extension_models:
            return self

        main_schema = self.model_fields["schemas"].default[0]
        by_schema = {
            ext.model_fields["schemas"].default[0]: ext for ext in extension_models
        }
        for schema in self.schemas:
            if schema == main_schema:
                continue

            model = by_schema[schema]
            if payload := getattr(self, schema, None):
                setattr(self, schema, model.model_validate(payload))

        return self

    @field_serializer("schemas")
    def set_extension_schemas(self, schemas: List[str]):
        """Add model extensions to 'schemas'."""

        extension_models = self.__pydantic_generic_metadata__.get("args")
        extension_schemas = [
            ext.model_fields["schemas"].default[0] for ext in extension_models
        ]
        schemas = self.schemas + [
            schema for schema in extension_schemas if schema not in self.schemas
        ]
        return schemas
