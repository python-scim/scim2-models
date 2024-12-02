from datetime import datetime
from typing import Annotated
from typing import Any
from typing import Generic
from typing import Optional
from typing import TypeVar
from typing import Union
from typing import get_args
from typing import get_origin

from pydantic import Field
from pydantic import WrapSerializer
from pydantic import field_serializer

from ..base import BaseModel
from ..base import BaseModelType
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
    """All "meta" sub-attributes are assigned by the service provider (have a "mutability" of "readOnly"), and all of these sub-attributes have a "returned" characteristic of "default".

    This attribute SHALL be ignored when provided by clients.  "meta" contains the following sub-attributes:
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


class Extension(BaseModel):
    @classmethod
    def to_schema(cls):
        """Build a :class:`~scim2_models.Schema` from the current extension class."""
        return model_to_schema(cls)

    @classmethod
    def from_schema(cls, schema) -> "Extension":
        """Build a :class:`~scim2_models.Extension` subclass from the schema definition."""
        from .schema import make_python_model

        return make_python_model(schema, cls)


AnyExtension = TypeVar("AnyExtension", bound="Extension")


def extension_serializer(value: Any, handler, info) -> Optional[dict[str, Any]]:
    """Exclude the Resource attributes from the extension dump.

    For instance, attributes 'meta', 'id' or 'schemas' should not be
    dumped when the model is used as an extension for another model.
    """
    partial_result = handler(value, info)
    result = {
        attr_name: value
        for attr_name, value in partial_result.items()
        if attr_name not in Resource.model_fields
    }
    return result or None


class ResourceMetaclass(BaseModelType):
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
                    WrapSerializer(extension_serializer),
                ]
                attrs[extension.__name__] = Field(
                    None,
                    serialization_alias=schema,
                    validation_alias=normalize_attribute_name(schema),
                )

        klass = super().__new__(cls, name, bases, attrs, **kwargs)
        return klass


class Resource(BaseModel, Generic[AnyExtension], metaclass=ResourceMetaclass):
    schemas: Annotated[list[str], Required.true]
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

    external_id: Annotated[
        Optional[str], Mutability.read_write, Returned.default, CaseExact.true
    ] = None
    """A String that is an identifier for the resource as defined by the
    provisioning client."""

    meta: Annotated[Optional[Meta], Mutability.read_only, Returned.default] = None
    """A complex attribute containing resource metadata."""

    def __getitem__(self, item: Any):
        if not isinstance(item, type) or not issubclass(item, Extension):
            raise KeyError(f"{item} is not a valid extension type")

        return getattr(self, item.__name__)

    def __setitem__(self, item: Any, value: "Resource"):
        if not isinstance(item, type) or not issubclass(item, Extension):
            raise KeyError(f"{item} is not a valid extension type")

        setattr(self, item.__name__, value)

    @classmethod
    def get_extension_models(cls) -> dict[str, type[Extension]]:
        """Return extension a dict associating extension models with their schemas."""
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

    @classmethod
    def get_extension_model(cls, name_or_schema) -> Optional[type[Extension]]:
        """Return an extension by its name or schema."""
        for schema, extension in cls.get_extension_models().items():
            if schema == name_or_schema or extension.__name__ == name_or_schema:
                return extension
        return None

    @staticmethod
    def get_by_schema(
        resource_types: list[type[BaseModel]], schema: str, with_extensions=True
    ) -> Optional[type]:
        """Given a resource type list and a schema, find the matching resource type."""
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
    def get_by_payload(resource_types: list[type], payload: dict, **kwargs):
        """Given a resource type list and a payload, find the matching resource type."""
        if not payload or not payload.get("schemas"):
            return None

        schema = payload["schemas"][0]
        return Resource.get_by_schema(resource_types, schema, **kwargs)

    @field_serializer("schemas")
    def set_extension_schemas(self, schemas: Annotated[list[str], Required.true]):
        """Add model extension ids to the 'schemas' attribute."""
        extension_schemas = self.get_extension_models().keys()
        schemas = self.schemas + [
            schema for schema in extension_schemas if schema not in self.schemas
        ]
        return schemas

    @classmethod
    def to_schema(cls):
        """Build a :class:`~scim2_models.Schema` from the current resource class."""
        return model_to_schema(cls)

    @classmethod
    def from_schema(cls, schema) -> "Resource":
        """Build a :class:`scim2_models.Resource` subclass from the schema definition."""
        from .schema import make_python_model

        return make_python_model(schema, cls)


AnyResource = TypeVar("AnyResource", bound="Resource")


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


def model_to_schema(model: type[BaseModel]):
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


def get_reference_types(type) -> list[str]:
    first_arg = get_args(type)[0]
    types = get_args(first_arg) if get_origin(first_arg) == Union else [first_arg]

    def serialize_ref_type(ref_type):
        if ref_type == URIReference:
            return "uri"

        elif ref_type == ExternalReference:
            return "external"

        return get_args(ref_type)[0]

    return list(map(serialize_ref_type, types))


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
        multi_valued=model.get_field_multiplicity(attribute_name),
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
