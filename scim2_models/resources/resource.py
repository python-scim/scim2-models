from datetime import datetime
from typing import TYPE_CHECKING
from typing import Annotated
from typing import Any
from typing import Generic
from typing import Optional
from typing import TypeVar
from typing import Union
from typing import cast
from typing import get_args
from typing import get_origin

from pydantic import Field
from pydantic import SerializationInfo
from pydantic import SerializerFunctionWrapHandler
from pydantic import WrapSerializer
from pydantic import field_serializer

from ..annotations import CaseExact
from ..annotations import Mutability
from ..annotations import Required
from ..annotations import Returned
from ..annotations import Uniqueness
from ..attributes import ComplexAttribute
from ..attributes import MultiValuedComplexAttribute
from ..attributes import is_complex_attribute
from ..base import BaseModel
from ..context import Context
from ..reference import Reference
from ..scim_object import ScimObject
from ..urn import _validate_attribute_urn
from ..utils import UNION_TYPES
from ..utils import _normalize_attribute_name

if TYPE_CHECKING:
    from .schema import Attribute
    from .schema import Schema


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


class Extension(ScimObject):
    @classmethod
    def to_schema(cls) -> "Schema":
        """Build a :class:`~scim2_models.Schema` from the current extension class."""
        return _model_to_schema(cls)

    @classmethod
    def from_schema(cls, schema: "Schema") -> type["Extension"]:
        """Build a :class:`~scim2_models.Extension` subclass from the schema definition."""
        from .schema import _make_python_model

        return _make_python_model(schema, cls)


AnyExtension = TypeVar("AnyExtension", bound="Extension")

_PARAMETERIZED_CLASSES: dict[tuple[type, tuple[Any, ...]], type] = {}


def _extension_serializer(
    value: Any, handler: SerializerFunctionWrapHandler, info: SerializationInfo
) -> Optional[dict[str, Any]]:
    """Exclude the Resource attributes from the extension dump.

    For instance, attributes 'meta', 'id' or 'schemas' should not be
    dumped when the model is used as an extension for another model.
    """
    partial_result = handler(value)
    result = {
        attr_name: value
        for attr_name, value in partial_result.items()
        if attr_name not in Resource.model_fields
    }
    return result or None


class Resource(ScimObject, Generic[AnyExtension]):
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

    @classmethod
    def __class_getitem__(cls, item: Any) -> type["Resource"]:
        """Create a Resource class with extension fields dynamically added."""
        if hasattr(cls, "__scim_extension_metadata__"):
            return cls

        extensions = get_args(item) if get_origin(item) in UNION_TYPES else [item]

        # Skip TypeVar parameters and Any (used for generic class definitions)
        valid_extensions = [
            extension
            for extension in extensions
            if not isinstance(extension, TypeVar) and extension is not Any
        ]

        if not valid_extensions:
            return cls

        cache_key = (cls, tuple(valid_extensions))
        if cache_key in _PARAMETERIZED_CLASSES:
            return _PARAMETERIZED_CLASSES[cache_key]

        for extension in valid_extensions:
            if not (isinstance(extension, type) and issubclass(extension, Extension)):
                raise TypeError(f"{extension} is not a valid Extension type")

        class_name = (
            f"{cls.__name__}[{', '.join(ext.__name__ for ext in valid_extensions)}]"
        )

        class_attrs = {"__scim_extension_metadata__": valid_extensions}

        for extension in valid_extensions:
            schema = extension.model_fields["schemas"].default[0]
            class_attrs[extension.__name__] = Field(
                default=None,  # type: ignore[arg-type]
                serialization_alias=schema,
                validation_alias=_normalize_attribute_name(schema),
            )

        new_annotations = {
            extension.__name__: Annotated[
                Optional[extension],
                WrapSerializer(_extension_serializer),
            ]
            for extension in valid_extensions
        }

        new_class = type(
            class_name,
            (cls,),
            {
                "__annotations__": new_annotations,
                **class_attrs,
            },
        )

        _PARAMETERIZED_CLASSES[cache_key] = new_class

        return new_class

    def __getitem__(self, item: Any) -> Optional[Extension]:
        if not isinstance(item, type) or not issubclass(item, Extension):
            raise KeyError(f"{item} is not a valid extension type")

        return cast(Optional[Extension], getattr(self, item.__name__))

    def __setitem__(self, item: Any, value: "Extension") -> None:
        if not isinstance(item, type) or not issubclass(item, Extension):
            raise KeyError(f"{item} is not a valid extension type")

        setattr(self, item.__name__, value)

    @classmethod
    def get_extension_models(cls) -> dict[str, type[Extension]]:
        """Return extension a dict associating extension models with their schemas."""
        extension_models = getattr(cls, "__scim_extension_metadata__", [])
        by_schema = {
            ext.model_fields["schemas"].default[0]: ext for ext in extension_models
        }
        return by_schema

    @classmethod
    def get_extension_model(
        cls, name_or_schema: Union[str, "Schema"]
    ) -> Optional[type[Extension]]:
        """Return an extension by its name or schema."""
        for schema, extension in cls.get_extension_models().items():
            if schema == name_or_schema or extension.__name__ == name_or_schema:
                return extension
        return None

    @staticmethod
    def get_by_schema(
        resource_types: list[type["Resource"]],
        schema: str,
        with_extensions: bool = True,
    ) -> Optional[Union[type["Resource"], type["Extension"]]]:
        """Given a resource type list and a schema, find the matching resource type."""
        by_schema: dict[str, Union[type[Resource], type[Extension]]] = {
            resource_type.model_fields["schemas"].default[0].lower(): resource_type
            for resource_type in (resource_types or [])
        }
        if with_extensions:
            for resource_type in resource_types:
                by_schema.update(
                    {
                        schema.lower(): extension
                        for schema, extension in resource_type.get_extension_models().items()
                    }
                )

        return by_schema.get(schema.lower())

    @staticmethod
    def get_by_payload(
        resource_types: list[type["Resource"]],
        payload: dict[str, Any],
        **kwargs: Any,
    ) -> Optional[type]:
        """Given a resource type list and a payload, find the matching resource type."""
        if not payload or not payload.get("schemas"):
            return None

        schema = payload["schemas"][0]
        return Resource.get_by_schema(resource_types, schema, **kwargs)

    @field_serializer("schemas")
    def set_extension_schemas(
        self, schemas: Annotated[list[str], Required.true]
    ) -> list[str]:
        """Add model extension ids to the 'schemas' attribute."""
        extension_schemas = self.get_extension_models().keys()
        schemas = self.schemas + [
            schema for schema in extension_schemas if schema not in self.schemas
        ]
        return schemas

    @classmethod
    def to_schema(cls) -> "Schema":
        """Build a :class:`~scim2_models.Schema` from the current resource class."""
        return _model_to_schema(cls)

    @classmethod
    def from_schema(cls, schema: "Schema") -> type["Resource"]:
        """Build a :class:`scim2_models.Resource` subclass from the schema definition."""
        from .schema import _make_python_model

        return _make_python_model(schema, cls)

    def _prepare_model_dump(
        self,
        scim_ctx: Optional[Context] = Context.DEFAULT,
        attributes: Optional[list[str]] = None,
        excluded_attributes: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        kwargs = super()._prepare_model_dump(scim_ctx, **kwargs)

        # RFC 7644: "SHOULD ignore any query parameters they do not recognize"
        kwargs["context"]["scim_attributes"] = [
            valid_attr
            for attribute in (attributes or [])
            if (valid_attr := _validate_attribute_urn(attribute, self.__class__))
            is not None
        ]
        kwargs["context"]["scim_excluded_attributes"] = [
            valid_attr
            for attribute in (excluded_attributes or [])
            if (valid_attr := _validate_attribute_urn(attribute, self.__class__))
            is not None
        ]
        return kwargs

    def model_dump(
        self,
        *args: Any,
        scim_ctx: Optional[Context] = Context.DEFAULT,
        attributes: Optional[list[str]] = None,
        excluded_attributes: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Create a model representation that can be included in SCIM messages by using Pydantic :code:`BaseModel.model_dump`.

        :param scim_ctx: If a SCIM context is passed, some default values of
            Pydantic :code:`BaseModel.model_dump` are tuned to generate valid SCIM
            messages. Pass :data:`None` to get the default Pydantic behavior.
        :param attributes: A multi-valued list of strings indicating the names of resource
            attributes to return in the response, overriding the set of attributes that
            would be returned by default. Invalid values are ignored.
        :param excluded_attributes: A multi-valued list of strings indicating the names of resource
            attributes to be removed from the default set of attributes to return. Invalid values are ignored.
        """
        dump_kwargs = self._prepare_model_dump(
            scim_ctx, attributes, excluded_attributes, **kwargs
        )
        if scim_ctx:
            dump_kwargs.setdefault("mode", "json")
        return super(ScimObject, self).model_dump(*args, **dump_kwargs)

    def model_dump_json(
        self,
        *args: Any,
        scim_ctx: Optional[Context] = Context.DEFAULT,
        attributes: Optional[list[str]] = None,
        excluded_attributes: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> str:
        """Create a JSON model representation that can be included in SCIM messages by using Pydantic :code:`BaseModel.model_dump_json`.

        :param scim_ctx: If a SCIM context is passed, some default values of
            Pydantic :code:`BaseModel.model_dump` are tuned to generate valid SCIM
            messages. Pass :data:`None` to get the default Pydantic behavior.
        :param attributes: A multi-valued list of strings indicating the names of resource
            attributes to return in the response, overriding the set of attributes that
            would be returned by default. Invalid values are ignored.
        :param excluded_attributes: A multi-valued list of strings indicating the names of resource
            attributes to be removed from the default set of attributes to return. Invalid values are ignored.
        """
        dump_kwargs = self._prepare_model_dump(
            scim_ctx, attributes, excluded_attributes, **kwargs
        )
        return super(ScimObject, self).model_dump_json(*args, **dump_kwargs)


AnyResource = TypeVar("AnyResource", bound="Resource")


def _dedicated_attributes(
    model: type[BaseModel], excluded_models: list[type[BaseModel]]
) -> dict[str, Any]:
    """Return attributes that are not members the parent 'excluded_models'."""

    def compare_field_infos(fi1: Any, fi2: Any) -> bool:
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
        for excluded_model in excluded_models
        for field_name, field_info in excluded_model.model_fields.items()
    }
    field_infos = {
        field_name: field_info
        for field_name, field_info in model.model_fields.items()
        if not compare_field_infos(field_info, parent_field_infos.get(field_name))
    }
    return field_infos


def _model_to_schema(model: type[BaseModel]) -> "Schema":
    from scim2_models.resources.schema import Schema

    schema_urn = model.model_fields["schemas"].default[0]
    field_infos = _dedicated_attributes(model, [Resource])
    attributes = [
        _model_attribute_to_scim_attribute(model, attribute_name)
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


def _model_attribute_to_scim_attribute(
    model: type[BaseModel], attribute_name: str
) -> "Attribute":
    from scim2_models.resources.schema import Attribute

    field_info = model.model_fields[attribute_name]
    root_type = model.get_field_root_type(attribute_name)
    if root_type is None:
        raise ValueError(
            f"Could not determine root type for attribute {attribute_name}"
        )
    attribute_type = Attribute.Type.from_python(root_type)
    sub_attributes = (
        [
            _model_attribute_to_scim_attribute(root_type, sub_attribute_name)
            for sub_attribute_name in _dedicated_attributes(
                root_type,
                [MultiValuedComplexAttribute],
            )
            if (
                attribute_name != "sub_attributes"
                or sub_attribute_name != "sub_attributes"
            )
        ]
        if root_type and is_complex_attribute(root_type)
        else None
    )

    return Attribute(
        name=field_info.serialization_alias or attribute_name,
        type=Attribute.Type(attribute_type),
        multi_valued=model.get_field_multiplicity(attribute_name),
        description=field_info.description,
        canonical_values=field_info.examples,
        required=model.get_field_annotation(attribute_name, Required),
        case_exact=model.get_field_annotation(attribute_name, CaseExact),
        mutability=model.get_field_annotation(attribute_name, Mutability),
        returned=model.get_field_annotation(attribute_name, Returned),
        uniqueness=model.get_field_annotation(attribute_name, Uniqueness),
        sub_attributes=sub_attributes,
        reference_types=Reference.get_types(root_type)
        if attribute_type == Attribute.Type.reference
        else None,
    )
