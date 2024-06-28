from collections import UserString
from enum import Enum
from enum import auto
from inspect import isclass
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

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import GetCoreSchemaHandler
from pydantic import SerializationInfo
from pydantic import SerializerFunctionWrapHandler
from pydantic import ValidationInfo
from pydantic import ValidatorFunctionWrapHandler
from pydantic import field_serializer
from pydantic import field_validator
from pydantic import model_serializer
from pydantic import model_validator
from pydantic.alias_generators import to_camel
from pydantic_core import PydanticCustomError
from pydantic_core import core_schema
from typing_extensions import NewType
from typing_extensions import Self

from scim2_models.attributes import contains_attribute_or_subattributes
from scim2_models.attributes import validate_attribute_urn

ReferenceTypes = TypeVar("ReferenceTypes")
URIReference = NewType("URIReference", str)
ExternalReference = NewType("ExternalReference", str)


class Reference(UserString, Generic[ReferenceTypes]):
    """Reference type as defined in :rfc:`RFC7643 §2.3.7 <7643#section-2.3.7>`.

    References can take different type parameters:

        - Any :class:`~scim2_models.Resource` subtype, or :class:`~typing.ForwardRef` of a Resource subtype, or :data:`~typing.Union` of those,
        - :data:`~scim2_models.ExternalReference`
        - :data:`~scim2_models.URIReference`

    Examples

    .. code-block:: python

        class Foobar(Resource):
            bff: Reference[User]
            managers: Reference[Union["User", "Group"]]
            photo: Reference[ExternalReference]
            website: Reference[URIReference]
    """

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source: type[Any],
        _handler: GetCoreSchemaHandler,
    ) -> core_schema.CoreSchema:
        return core_schema.no_info_after_validator_function(
            cls._validate, core_schema.str_schema()
        )

    @classmethod
    def _validate(cls, input_value: str, /) -> str:
        return input_value


class Context(Enum):
    """Represent the different HTTP contexts detailed in :rfc:`RFC7644 §3.2
    <7644#section-3.2>`

    Contexts are intented to be used during model validation and serialization.
    For instance a client preparing a resource creation POST request can use
    :code:`resource.model_dump(Context.RESOURCE_CREATION_REQUEST)` and
    the server can then validate it with
    :code:`resource.model_validate(Context.RESOURCE_CREATION_REQUEST)`.
    """

    DEFAULT = auto()
    """The default context.

    All fields are accepted during validation, and all fields are
    serialized during a dump.
    """

    RESOURCE_CREATION_REQUEST = auto()
    """The resource creation request context.

    Should be used for clients building a payload for a resource creation request,
    and servers validating resource creation request payloads.

    - When used for serialization, it will not dump attributes annotated with :attr:`~scim2_models.Mutability.read_only`.
    - When used for validation, it will raise a :class:`~pydantic.ValidationError`:
        - when finding attributes annotated with :attr:`~scim2_models.Mutability.read_only`,
        - when attributes annotated with :attr:`Required.true <scim2_models.Required.true>` are missing on null.
    """

    RESOURCE_CREATION_RESPONSE = auto()
    """The resource creation response context.

    Should be used for servers building a payload for a resource
    creation response, and clients validating resource creation response
    payloads.

    - When used for validation, it will raise a :class:`~pydantic.ValidationError` when finding attributes annotated with :attr:`~scim2_models.Returned.never` or when attributes annotated with :attr:`~scim2_models.Returned.always` are missing or :data:`None`;
    - When used for serialization, it will:
        - always dump attributes annotated with :attr:`~scim2_models.Returned.always`;
        - never dump attributes annotated with :attr:`~scim2_models.Returned.never`;
        - dump attributes annotated with :attr:`~scim2_models.Returned.default` unless they are explicitly excluded;
        - not dump attributes annotated with :attr:`~scim2_models.Returned.request` unless they are explicitly included.
    """

    RESOURCE_QUERY_REQUEST = auto()
    """The resource query request context.

    Should be used for clients building a payload for a resource query request,
    and servers validating resource query request payloads.

    - When used for serialization, it will not dump attributes annotated with :attr:`~scim2_models.Mutability.write_only`.
    - When used for validation, it will raise a :class:`~pydantic.ValidationError` when finding attributes annotated with :attr:`~scim2_models.Mutability.write_only`.
    """

    RESOURCE_QUERY_RESPONSE = auto()
    """The resource query response context.

    Should be used for servers building a payload for a resource query
    response, and clients validating resource query response payloads.

    - When used for validation, it will raise a :class:`~pydantic.ValidationError` when finding attributes annotated with :attr:`~scim2_models.Returned.never` or when attributes annotated with :attr:`~scim2_models.Returned.always` are missing or :data:`None`;
    - When used for serialization, it will:
        - always dump attributes annotated with :attr:`~scim2_models.Returned.always`;
        - never dump attributes annotated with :attr:`~scim2_models.Returned.never`;
        - dump attributes annotated with :attr:`~scim2_models.Returned.default` unless they are explicitly excluded;
        - not dump attributes annotated with :attr:`~scim2_models.Returned.request` unless they are explicitly included.
    """

    RESOURCE_REPLACEMENT_REQUEST = auto()
    """The resource replacement request context.

    Should be used for clients building a payload for a resource replacement request,
    and servers validating resource replacement request payloads.

    - When used for serialization, it will not dump attributes annotated with :attr:`~scim2_models.Mutability.read_only` and :attr:`~scim2_models.Mutability.immutable`.
    - When used for validation, it will ignore attributes annotated with :attr:`scim2_models.Mutability.read_only` and raise a :class:`~pydantic.ValidationError`:
        - when finding attributes annotated with :attr:`~scim2_models.Mutability.immutable`,
        - when attributes annotated with :attr:`Required.true <scim2_models.Required.true>` are missing on null.
    """

    RESOURCE_REPLACEMENT_RESPONSE = auto()
    """The resource replacement response context.

    Should be used for servers building a payload for a resource
    replacement response, and clients validating resource query
    replacement payloads.

    - When used for validation, it will raise a :class:`~pydantic.ValidationError` when finding attributes annotated with :attr:`~scim2_models.Returned.never` or when attributes annotated with :attr:`~scim2_models.Returned.always` are missing or :data:`None`;
    - When used for serialization, it will:
        - always dump attributes annotated with :attr:`~scim2_models.Returned.always`;
        - never dump attributes annotated with :attr:`~scim2_models.Returned.never`;
        - dump attributes annotated with :attr:`~scim2_models.Returned.default` unless they are explicitly excluded;
        - not dump attributes annotated with :attr:`~scim2_models.Returned.request` unless they are explicitly included.
    """

    SEARCH_REQUEST = auto()
    """The search request context.

    Should be used for clients building a payload for a search request,
    and servers validating search request payloads.

    - When used for serialization, it will not dump attributes annotated with :attr:`~scim2_models.Mutability.write_only`.
    - When used for validation, it will raise a :class:`~pydantic.ValidationError` when finding attributes annotated with :attr:`~scim2_models.Mutability.write_only`.
    """

    SEARCH_RESPONSE = auto()
    """The resource query response context.

    Should be used for servers building a payload for a search response,
    and clients validating resource search payloads.

    - When used for validation, it will raise a :class:`~pydantic.ValidationError` when finding attributes annotated with :attr:`~scim2_models.Returned.never` or when attributes annotated with :attr:`~scim2_models.Returned.always` are missing or :data:`None`;
    - When used for serialization, it will:
        - always dump attributes annotated with :attr:`~scim2_models.Returned.always`;
        - never dump attributes annotated with :attr:`~scim2_models.Returned.never`;
        - dump attributes annotated with :attr:`~scim2_models.Returned.default` unless they are explicitly excluded;
        - not dump attributes annotated with :attr:`~scim2_models.Returned.request` unless they are explicitly included.
    """

    @classmethod
    def is_request(cls, ctx: "Context") -> bool:
        return ctx in (
            cls.RESOURCE_CREATION_REQUEST,
            cls.RESOURCE_QUERY_REQUEST,
            cls.RESOURCE_REPLACEMENT_REQUEST,
            cls.SEARCH_REQUEST,
        )

    @classmethod
    def is_response(cls, ctx: "Context") -> bool:
        return ctx in (
            cls.RESOURCE_CREATION_RESPONSE,
            cls.RESOURCE_QUERY_RESPONSE,
            cls.RESOURCE_REPLACEMENT_RESPONSE,
            cls.SEARCH_RESPONSE,
        )


class Mutability(str, Enum):
    """A single keyword indicating the circumstances under which the value of
    the attribute can be (re)defined:"""

    read_only = "readOnly"
    """The attribute SHALL NOT be modified."""

    read_write = "readWrite"
    """The attribute MAY be updated and read at any time."""

    immutable = "immutable"
    """The attribute MAY be defined at resource creation (e.g., POST) or at
    record replacement via a request (e.g., a PUT).

    The attribute SHALL NOT be updated.
    """

    write_only = "writeOnly"
    """The attribute MAY be updated at any time.

    Attribute values SHALL NOT be returned (e.g., because the value is a
    stored hash).  Note: An attribute with a mutability of "writeOnly"
    usually also has a returned setting of "never".
    """

    _default = read_write


class Returned(str, Enum):
    """A single keyword that indicates when an attribute and associated values
    are returned in response to a GET request or in response to a PUT, POST, or
    PATCH request."""

    always = "always"  # cannot be excluded
    """The attribute is always returned, regardless of the contents of the
    "attributes" parameter.

    For example, "id" is always returned to identify a SCIM resource.
    """

    never = "never"  # always excluded
    """The attribute is never returned, regardless of the contents of the
    "attributes" parameter."""

    default = "default"  # included by default but can be excluded
    """The attribute is returned by default in all SCIM operation responses
    where attribute values are returned, unless it is explicitly excluded."""

    request = "request"  # excluded by default but can be included
    """The attribute is returned in response to any PUT, POST, or PATCH
    operations if specified in the "attributes" parameter."""

    _default = default


class Uniqueness(str, Enum):
    """A single keyword value that specifies how the service provider enforces
    uniqueness of attribute values."""

    none = "none"
    """The values are not intended to be unique in any way."""

    server = "server"
    """The value SHOULD be unique within the context of the current SCIM
    endpoint (or tenancy) and MAY be globally unique (e.g., a "username", email
    address, or other server-generated key or counter).

    No two resources on the same server SHOULD possess the same value.
    """

    global_ = "global"
    """The value SHOULD be globally unique (e.g., an email address, a GUID, or
    other value).

    No two resources on any server SHOULD possess the same value.
    """

    _default = none


class Required(Enum):
    """A Boolean value that specifies whether or not the attribute is required.

    Missing required attributes raise a :class:`~pydantic.ValidationError` on :attr:`~scim2_models.Context.RESOURCE_CREATION_REQUEST` and :attr:`~scim2_models.Context.RESOURCE_REPLACEMENT_REQUEST` validations.
    """

    true = True
    false = False

    _default = false

    def __bool__(self):
        return self.value


class CaseExact(Enum):
    """A Boolean value that specifies whether or not a string attribute is case
    sensitive."""

    true = True
    false = False

    _default = false

    def __bool__(self):
        return self.value


class BaseModel(BaseModel):
    """Base Model for everything."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    @classmethod
    def get_field_annotation(cls, field_name: str, annotation_type: Type) -> Any:
        """Return the annotation of type 'annotation_type' of the field
        'field_name'."""
        field_metadata = cls.model_fields[field_name].metadata

        default_value = getattr(annotation_type, "_default", None)

        def annotation_type_filter(item):
            return isinstance(item, annotation_type)

        field_annotation = next(
            filter(annotation_type_filter, field_metadata), default_value
        )
        return field_annotation

    @classmethod
    def get_field_root_type(cls, attribute_name: str) -> Type:
        """Extract the root type from a model field.

        For example, return 'GroupMember' for
        'Optional[List[GroupMember]]'
        """

        attribute_type = cls.model_fields[attribute_name].annotation

        # extract 'x' from 'Optional[x]'
        if get_origin(attribute_type) is Union:
            attribute_type = get_args(attribute_type)[0]

        # extract 'x' from 'List[x]'
        if isinstance(get_origin(attribute_type), Type) and issubclass(
            get_origin(attribute_type), List
        ):
            attribute_type = get_args(attribute_type)[0]

        return attribute_type

    @field_validator("*")
    @classmethod
    def check_request_attributes_mutability(
        cls, value: Any, info: ValidationInfo
    ) -> Any:
        """Check that the field mutability is expected according to the
        requests validation context, as defined in :rfc:`RFC7643 §7
        <7653#section-7>`."""

        if (
            not info.context
            or not info.context.get("scim")
            or not Context.is_request(info.context["scim"])
        ):
            return value

        context = info.context.get("scim")
        mutability = cls.get_field_annotation(info.field_name, Mutability)
        exc = PydanticCustomError(
            "mutability_error",
            "Field '{field_name}' has mutability '{field_mutability}' but this in not valid in {context} context",
            {
                "field_name": info.field_name,
                "field_mutability": mutability,
                "context": context.name.lower().replace("_", " "),
            },
        )

        if (
            context in (Context.RESOURCE_QUERY_REQUEST, Context.SEARCH_REQUEST)
            and mutability == Mutability.write_only
        ):
            raise exc

        if (
            context == Context.RESOURCE_REPLACEMENT_REQUEST
            and mutability == Mutability.immutable
        ):
            raise exc

        if (
            context
            in (Context.RESOURCE_CREATION_REQUEST, Context.RESOURCE_REPLACEMENT_REQUEST)
            and mutability == Mutability.read_only
        ):
            return None

        return value

    @model_validator(mode="wrap")
    @classmethod
    def check_response_attributes_returnability(
        cls, value: Any, handler: ValidatorFunctionWrapHandler, info: ValidationInfo
    ) -> Self:
        """Check that the fields returnability is expected according to the
        responses validation context, as defined in :rfc:`RFC7643 §7
        <7653#section-7>`."""
        if (
            not info.context
            or not info.context.get("scim")
            or not Context.is_response(info.context["scim"])
        ):
            return handler(value)

        for field_name, field in cls.model_fields.items():
            returnability = cls.get_field_annotation(field_name, Returned)
            alias = field.alias or field_name

            if returnability == Returned.always and value.get(alias) is None:
                raise PydanticCustomError(
                    "returned_error",
                    "Field '{field_name}' has returnability 'always' but value is missing or null",
                    {
                        "field_name": field_name,
                    },
                )

            if returnability == Returned.never and value.get(alias) is not None:
                raise PydanticCustomError(
                    "returned_error",
                    "Field '{field_name}' has returnability 'never' but value is set",
                    {
                        "field_name": field_name,
                    },
                )

        return handler(value)

    @model_validator(mode="wrap")
    @classmethod
    def check_response_attributes_necessity(
        cls, value: Any, handler: ValidatorFunctionWrapHandler, info: ValidationInfo
    ) -> Self:
        """Check that the required attributes are present in creations and
        replacement requests."""
        if (
            not info.context
            or not info.context.get("scim")
            or info.context["scim"]
            not in (
                Context.RESOURCE_CREATION_REQUEST,
                Context.RESOURCE_REPLACEMENT_REQUEST,
            )
        ):
            return handler(value)

        for field_name, field in cls.model_fields.items():
            necessity = cls.get_field_annotation(field_name, Required)
            alias = field.alias or field_name

            if necessity == Required.true and value.get(alias) is None:
                raise PydanticCustomError(
                    "required_error",
                    "Field '{field_name}' is required but value is missing or null",
                    {
                        "field_name": field_name,
                    },
                )

        return handler(value)

    def mark_with_schema(self):
        """Navigate through attributes and subattributes of type
        ComplexAttribute, and mark them with a '_schema' attribute.

        '_schema' will later be used by 'get_attribute_urn'.
        """

        from scim2_models.rfc7643.resource import Resource

        for field_name, field in self.model_fields.items():
            attr_type = self.get_field_root_type(field_name)
            if not is_complex_attribute(attr_type):
                continue

            main_schema = self.model_fields["schemas"].default[0]

            separator = ":" if isinstance(self, Resource) else "."
            schema = f"{main_schema}{separator}{field_name}"

            if attr_value := getattr(self, field_name):
                if isinstance(attr_value, list):
                    for item in attr_value:
                        item._schema = schema
                else:
                    attr_value._schema = schema

    @field_serializer("*", mode="wrap")
    def scim_serializer(
        self,
        value: Any,
        handler: SerializerFunctionWrapHandler,
        info: SerializationInfo,
    ) -> Any:
        """Serialize the fields according to mutability indications passed in
        the serialization context."""

        value = handler(value)

        if info.context.get("scim") and Context.is_request(info.context["scim"]):
            value = self.scim_request_serializer(value, info)

        if info.context.get("scim") and Context.is_response(info.context["scim"]):
            value = self.scim_response_serializer(value, info)

        return value

    def scim_request_serializer(self, value: Any, info: SerializationInfo) -> Any:
        """Serialize the fields according to mutability indications passed in
        the serialization context."""

        mutability = self.get_field_annotation(info.field_name, Mutability)
        context = info.context.get("scim")

        if (
            context == Context.RESOURCE_CREATION_REQUEST
            and mutability == Mutability.read_only
        ):
            return None

        if (
            context
            in (
                Context.RESOURCE_QUERY_REQUEST,
                Context.SEARCH_REQUEST,
            )
            and mutability == Mutability.write_only
        ):
            return None

        if context == Context.RESOURCE_REPLACEMENT_REQUEST and mutability in (
            Mutability.immutable,
            Mutability.read_only,
        ):
            return None

        return value

    def scim_response_serializer(self, value: Any, info: SerializationInfo) -> Any:
        """Serialize the fields according to returability indications passed in
        the serialization context."""

        returnability = self.get_field_annotation(info.field_name, Returned)
        attribute_urn = self.get_attribute_urn(info.field_name)
        included_urns = info.context.get("scim_attributes", [])
        excluded_urns = info.context.get("scim_excluded_attributes", [])

        if returnability == Returned.never:
            return None

        if returnability == Returned.default and (
            (
                included_urns
                and not contains_attribute_or_subattributes(
                    included_urns, attribute_urn
                )
            )
            or attribute_urn in excluded_urns
        ):
            return None

        if returnability == Returned.request and attribute_urn not in included_urns:
            return None

        return value

    @model_serializer(mode="wrap")
    def model_serializer_exclude_none(
        self, handler, info: SerializationInfo
    ) -> Dict[str, Any]:
        """Remove `None` values inserted by the
        :meth:`~scim2_models.base.BaseModel.scim_serializer`."""

        result = handler(self)
        return {key: value for key, value in result.items() if value is not None}

    @classmethod
    def model_validate(
        cls, *args, scim_ctx: Optional[Context] = Context.DEFAULT, **kwargs
    ) -> "BaseModel":
        """Validate SCIM payloads and generate model representation by using
        Pydantic :code:`BaseModel.model_validate`."""

        kwargs.setdefault("context", {}).setdefault("scim", scim_ctx)
        return super().model_validate(*args, **kwargs)

    def model_dump(
        self,
        *args,
        scim_ctx: Optional[Context] = Context.DEFAULT,
        attributes: Optional[List[str]] = None,
        excluded_attributes: Optional[List[str]] = None,
        **kwargs,
    ):
        """Create a model representation that can be included in SCIM messages
        by using Pydantic :code:`BaseModel.model_dump`.

        :param scim_ctx: If a SCIM context is passed, some default values of
            Pydantic :code:`BaseModel.model_dump` are tuned to generate valid SCIM
            messages. Pass :data:`None` to get the default Pydantic behavior.
        """

        kwargs.setdefault("context", {}).setdefault("scim", scim_ctx)
        kwargs["context"]["scim_attributes"] = [
            validate_attribute_urn(attribute, self.__class__)
            for attribute in (attributes or [])
        ]
        kwargs["context"]["scim_excluded_attributes"] = [
            validate_attribute_urn(attribute, self.__class__)
            for attribute in (excluded_attributes or [])
        ]

        if scim_ctx:
            kwargs.setdefault("exclude_none", True)
            kwargs.setdefault("by_alias", True)
            kwargs.setdefault("mode", "json")

        return super().model_dump(*args, **kwargs)

    def get_attribute_urn(self, field_name: str) -> Returned:
        """Build the full URN of the attribute.

        See :rfc:`RFC7644 §3.12 <7644#section-3.12>`.
        """
        main_schema = self.model_fields["schemas"].default[0]
        alias = self.model_fields[field_name].alias or field_name
        return f"{main_schema}:{alias}"


class ComplexAttribute(BaseModel):
    """A complex attribute as defined in :rfc:`RFC7643 §2.3.8
    <7643#section-2.3.8>`."""

    _schema: str

    def get_attribute_urn(self, field_name: str) -> Returned:
        """Build the full URN of the attribute.

        See :rfc:`RFC7644 §3.12 <7644#section-3.12>`.
        """
        alias = self.model_fields[field_name].alias or field_name
        return f"{self._schema}.{alias}"


class MultiValuedComplexAttribute(ComplexAttribute):
    type: Optional[str] = None
    """A label indicating the attribute's function."""

    primary: Optional[bool] = None
    """A Boolean value indicating the 'primary' or preferred attribute value
    for this attribute."""

    display: Annotated[Optional[str], Mutability.immutable] = None
    """A human-readable name, primarily used for display purposes."""

    value: Optional[str] = None
    """The value of an entitlement."""

    ref: Optional[Reference] = Field(None, alias="$ref")
    """The reference URI of a target resource, if the attribute is a
    reference."""


def is_complex_attribute(type):
    # issubclass raise a TypeError with 'Reference' on python < 3.11
    return (
        get_origin(type) != Reference
        and isclass(type)
        and issubclass(type, (ComplexAttribute, MultiValuedComplexAttribute))
    )


AnyModel = TypeVar("AnyModel", bound=BaseModel)
