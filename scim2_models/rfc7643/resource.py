from datetime import datetime
from typing import Annotated
from typing import Any
from typing import Dict
from typing import ForwardRef
from typing import Generic
from typing import List
from typing import Optional
from typing import Type
from typing import TypeVar
from typing import Union
from typing import get_args
from typing import get_origin

from pydantic import Discriminator
from pydantic import Field
from pydantic import Tag
from pydantic import ValidationInfo
from pydantic import ValidatorFunctionWrapHandler
from pydantic import WrapSerializer
from pydantic import field_serializer
from pydantic import model_validator
from typing_extensions import Self

from ..base import AnyModel
from ..base import BaseModel
from ..base import CaseExact
from ..base import ComplexAttribute
from ..base import ExternalReference
from ..base import Mutability
from ..base import Required
from ..base import Returned
from ..base import Uniqueness
from ..base import URIReference
from ..base import is_complex_attribute
from ..utils import normalize_attribute_name


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


def extension_serializer(value: Any, handler, info) -> Dict[str, Any]:
    partial_result = handler(value, info)
    result = {
        attr_name: value
        for attr_name, value in partial_result.items()
        if attr_name not in Resource.model_fields
    }
    return result or None


class ResourceMetaclass(type(BaseModel)):
    def __new__(cls, name, bases, attrs, **kwargs):
        """Dynamically add a field for each extension."""

        if "__pydantic_generic_metadata__" in kwargs:
            extensions = kwargs["__pydantic_generic_metadata__"]["args"][0]
            extensions = (
                get_args(extensions)
                if get_origin(extensions) == Union
                else [extensions]
            )
            for extension in extensions:
                schema = extension.model_fields["schemas"].default[0]
                attrs.setdefault("__annotations__", {})[extension.__name__] = Annotated[
                    Optional[extension],
                    Returned.always,
                    WrapSerializer(extension_serializer),
                ]
                attrs[extension.__name__] = Field(
                    None,
                    serialization_alias=schema,
                    validation_alias=normalize_attribute_name(schema),
                )

        klass = super().__new__(cls, name, bases, attrs, **kwargs)
        return klass


class Resource(BaseModel, Generic[AnyModel], metaclass=ResourceMetaclass):
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

        return getattr(self, item.__name__)

    def __setitem__(self, item: Any, value: "Resource"):
        if not isinstance(item, type) or not issubclass(item, Resource):
            raise KeyError(f"{item} is not a valid extension type")

        setattr(self, item.__name__, value)

    @classmethod
    def get_extension_models(cls) -> Dict[str, Type]:
        """Return extension a dict associating extension models with their
        schemas."""

        extension_models = cls.__pydantic_generic_metadata__.get("args", [])
        extension_models = (
            get_args(extension_models[0])
            if len(extension_models) == 1 and get_origin(extension_models[0]) == Union
            else extension_models
        )

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
            resource_type.model_fields["schemas"].default[0].lower(): resource_type
            for resource_type in (resource_types or [])
        }
        if with_extensions:
            for resource_type in list(by_schema.values()):
                by_schema.update(
                    {
                        schema.lower(): extension
                        for schema, extension in resource_type.get_extension_models().items()
                    }
                )

        return by_schema.get(schema.lower())

    @staticmethod
    def get_by_payload(resource_types: List[Type], payload: Dict, **kwargs):
        """Given a resource type list and a payload, find the matching resource
        type."""

        schema = payload["schemas"][0] if payload and payload.get("schemas") else None
        return Resource.get_by_schema(resource_types, schema, **kwargs)

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
        """Navigate through attributes and sub-attributes of type
        ComplexAttribute, and mark them with a '_schema' attribute.

        '_schema' will later be used by 'get_attribute_urn'.
        """

        obj = handler(value)
        obj.mark_with_schema()

        return obj

    @classmethod
    def to_schema(cls):
        return model_to_schema(cls)


AnyResource = TypeVar("AnyResource", bound="Resource")


def is_multiple(field):
    return "list" in str(field.annotation).lower()


def dedicated_attributes(model):
    """Return attributes that are not members of parent classes."""

    def compare_field_infos(fi1, fi2):
        return (
            fi1
            and fi2
            and fi1.__slotnames__ == fi2.__slotnames__
            and all(
                getattr(fi1, attr) == getattr(fi2, attr) for attr in fi1.__slotnames__
            )
        )

    parent_field_infos = {
        field_name: field_info
        for parent in model.__bases__
        for field_name, field_info in parent.model_fields.items()
    }
    field_infos = {
        field_name: field_info
        for field_name, field_info in model.model_fields.items()
        if not compare_field_infos(field_info, parent_field_infos.get(field_name))
    }
    return field_infos


def model_to_schema(model: Type):
    from scim2_models.rfc7643.schema import Schema

    schema_urn = model.model_fields["schemas"].default[0]
    field_infos = dedicated_attributes(model)
    attributes = [
        model_attribute_to_attribute(model, attribute_name)
        for attribute_name in field_infos
        if attribute_name != "schemas"
    ]
    schema = Schema(
        name=model.__name__,
        id=schema_urn,
        description=model.__doc__ or model.__name__,
        attributes=attributes,
    )
    return schema


def get_reference_types(type):
    first_arg = get_args(type)[0]
    types = get_args(first_arg) if get_origin(first_arg) == Union else [first_arg]
    formatted_types = [
        t.__forward_arg__ if isinstance(t, ForwardRef) else t for t in types
    ]
    scim_reference_types = [
        "uri" if ref_type == URIReference else ref_type for ref_type in formatted_types
    ]
    scim_reference_types = [
        "external" if ref_type == ExternalReference else ref_type
        for ref_type in scim_reference_types
    ]
    return scim_reference_types


def model_attribute_to_attribute(model, attribute_name):
    from scim2_models.rfc7643.schema import Attribute

    field_info = model.model_fields[attribute_name]
    root_type = model.get_field_root_type(attribute_name)
    attribute_type = Attribute.Type.from_python(root_type)
    sub_attributes = (
        [
            model_attribute_to_attribute(root_type, sub_attribute_name)
            for sub_attribute_name in dedicated_attributes(root_type)
            if (
                attribute_name != "sub_attributes"
                or sub_attribute_name != "sub_attributes"
            )
        ]
        if is_complex_attribute(root_type)
        else None
    )

    return Attribute(
        name=field_info.serialization_alias or attribute_name,
        type=attribute_type,
        multi_valued=is_multiple(field_info),
        description=field_info.description,
        canonical_values=field_info.examples,
        required=model.get_field_annotation(attribute_name, Required),
        case_exact=model.get_field_annotation(attribute_name, CaseExact),
        mutability=model.get_field_annotation(attribute_name, Mutability),
        returned=model.get_field_annotation(attribute_name, Returned),
        uniqueness=model.get_field_annotation(attribute_name, Uniqueness),
        sub_attributes=sub_attributes,
        reference_types=get_reference_types(root_type)
        if attribute_type == Attribute.Type.reference
        else None,
    )


def tagged_resource_union(resource_types: Resource):
    """Build Discriminated Unions, so pydantic can get which class are needed
    to instantiate by inspecting a payload.

    https://docs.pydantic.dev/latest/concepts/unions/#discriminated-unions
    """
    if not get_origin(resource_types) == Union:
        return resource_types

    def get_schema_from_payload(payload: Any):
        if not payload:
            return None

        resource_types_schemas = [
            resource_type.model_fields["schemas"].default[0]
            for resource_type in resource_types
        ]
        common_schemas = [
            schema
            for schema in payload.get("schemas")
            if schema in resource_types_schemas
        ]
        return common_schemas[0] if common_schemas else None

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
