from datetime import datetime
from typing import Annotated
from typing import Any
from typing import Dict
from typing import Generic
from typing import List
from typing import Optional
from typing import Type
from typing import TypeVar
from typing import Union
from typing import get_args
from typing import get_origin

from pydantic import ConfigDict
from pydantic import Discriminator
from pydantic import Tag
from pydantic import ValidationInfo
from pydantic import ValidatorFunctionWrapHandler
from pydantic import field_serializer
from pydantic import model_validator
from typing_extensions import Self

from ..base import AnyModel
from ..base import BaseModel
from ..base import ComplexAttribute
from ..base import Mutability
from ..base import Returned
from ..base import Uniqueness


class Meta(ComplexAttribute):
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


class Resource(BaseModel, Generic[AnyModel]):
    model_config = ConfigDict(extra="allow")

    schemas: List[str]
    """The "schemas" attribute is a REQUIRED attribute and is an array of
    Strings containing URIs that are used to indicate the namespaces of the
    SCIM schemas that define the attributes present in the current JSON
    structure."""

    # Common attributes as defined by
    # https://www.rfc-editor.org/rfc/rfc7643#section-3.1

    id: Annotated[
        Optional[str], Mutability.read_only, Returned.always, Uniqueness.global_
    ] = None
    """A unique identifier for a SCIM resource as defined by the service
    provider.

    id is mandatory is the resource representation, but is forbidden in
    resource creation or replacement requests.
    """

    external_id: Annotated[Optional[str], Mutability.read_write, Returned.default] = (
        None
    )
    """A String that is an identifier for the resource as defined by the
    provisioning client."""

    meta: Annotated[Optional[Meta], Mutability.read_only, Returned.default] = None
    """A complex attribute containing resource metadata."""

    def __getitem__(self, item: Any):
        if not isinstance(item, type) or not issubclass(item, Resource):
            raise KeyError(f"{item} is not a valid extension type")

        schema = item.model_fields["schemas"].default[0]
        return getattr(self, schema)

    def __setitem__(self, item: Any, value: "Resource"):
        if not isinstance(item, type) or not issubclass(item, Resource):
            raise KeyError(f"{item} is not a valid extension type")

        schema = item.model_fields["schemas"].default[0]
        setattr(self, schema, value)

    @classmethod
    def get_extension_models(cls) -> Dict[str, Type]:
        """Return extension a dict associating extension models with their
        schemas."""

        extension_models = cls.__pydantic_generic_metadata__.get("args", [])
        if len(extension_models) == 1 and get_origin(extension_models[0]) == Union:
            extension_models = get_args(extension_models[0])

        by_schema = {
            ext.model_fields["schemas"].default[0]: ext for ext in extension_models
        }
        return by_schema

    @staticmethod
    def get_by_schema(
        resource_types: List[Type], schema: str, with_extensions=True
    ) -> Optional[Type]:
        """Given a resource type list and a schema, find the matching resource
        type."""

        by_schema = {
            resource_type.model_fields["schemas"].default[0]: resource_type
            for resource_type in (resource_types or [])
        }
        if with_extensions:
            for resource_type in list(by_schema.values()):
                by_schema.update(**resource_type.get_extension_models())

        return by_schema.get(schema)

    @staticmethod
    def get_by_payload(resource_types: List[Type], payload: Dict, **kwargs):
        """Given a resource type list and a payload, find the matching resource
        type."""

        schema = payload["schemas"][0] if payload and payload.get("schemas") else None
        return Resource.get_by_schema(resource_types, schema, **kwargs)

    @model_validator(mode="after")
    def load_model_extensions(self) -> Self:
        """Instanciate schema objects if found in the payload."""

        main_schema = self.model_fields["schemas"].default[0]
        extension_models = self.get_extension_models()
        for schema in self.schemas:
            if schema == main_schema:
                continue

            try:
                model = extension_models[schema]
            except KeyError as exc:
                raise ValueError(
                    f"No extension model found for schema '{schema}'"
                ) from exc

            if payload := getattr(self, schema, None):
                setattr(self, schema, model.model_validate(payload))

        return self

    @field_serializer("schemas")
    def set_extension_schemas(self, schemas: List[str]):
        """Add model extension ids to the 'schemas' attribute."""

        extension_models = self.__pydantic_generic_metadata__.get("args")
        extension_schemas = [
            ext.model_fields["schemas"].default[0] for ext in extension_models
        ]
        schemas = self.schemas + [
            schema for schema in extension_schemas if schema not in self.schemas
        ]
        return schemas

    @model_validator(mode="wrap")
    @classmethod
    def attribute_urn_marker(
        cls, value: Any, handler: ValidatorFunctionWrapHandler, info: ValidationInfo
    ) -> Self:
        """Navigate through attributes and subattributes of type
        ComplexAttribute, and mark them with a '_schema' attribute.

        '_schema' will later be used by 'get_attribute_urn'.
        """

        obj = handler(value)
        obj.mark_with_schema()

        return obj


AnyResource = TypeVar("AnyResource", bound="Resource")


def tagged_resource_union(resource_types: Resource):
    """Build Discriminated Unions, so pydantic can get which class are needed
    to instantiate by inspecting a payload.

    https://docs.pydantic.dev/latest/concepts/unions/#discriminated-unions
    """
    if not get_origin(resource_types) == Union:
        return resource_types

    def get_schema_from_payload(payload: Any):
        try:
            return payload["schemas"][0]
        except KeyError:
            return None

    def get_tag(resource_type: Type):
        return Tag(resource_type.model_fields["schemas"].default[0])

    resource_types = get_args(resource_types)
    tagged_resources = [
        Annotated[resource_type, get_tag(resource_type)]
        for resource_type in resource_types
    ]
    return Annotated[
        Union[tuple(tagged_resources)], Discriminator(get_schema_from_payload)
    ]
