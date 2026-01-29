import warnings
from typing import Any
from typing import Generic
from typing import Literal
from typing import TypeVar
from typing import get_args
from typing import get_origin

from pydantic import GetCoreSchemaHandler
from pydantic import GetJsonSchemaHandler
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import Url
from pydantic_core import ValidationError
from pydantic_core import core_schema

from .utils import UNION_TYPES

ReferenceTypes = TypeVar("ReferenceTypes")


class External:
    """Marker for external references per :rfc:`RFC7643 §7 <7643#section-7>`.

    Use with :class:`Reference` to type external resource URLs (photos, websites)::

        profile_url: Reference[External] | None = None
    """


class URI:
    """Marker for URI references per :rfc:`RFC7643 §7 <7643#section-7>`.

    Use with :class:`Reference` to type URI identifiers (schema URNs, endpoints)::

        endpoint: Reference[URI] | None = None
    """


class ExternalReference:
    """Deprecated. Use :class:`External` instead."""


class URIReference:
    """Deprecated. Use :class:`URI` instead."""


class Reference(str, Generic[ReferenceTypes]):
    """Reference type as defined in :rfc:`RFC7643 §2.3.7 <7643#section-2.3.7>`.

    References can take different type parameters:

    - :class:`~scim2_models.External` for external resources (photos, websites)
    - :class:`~scim2_models.URI` for URI identifiers (schema URNs, endpoints)
    - String forward references for SCIM resource types (``"User"``, ``"Group"``)
    - Resource classes directly if imports allow

    Examples::

        class Foobar(Resource):
            photo: Reference[External] | None = None
            website: Reference[URI] | None = None
            manager: Reference["User"] | None = None
            members: Reference[Union["User", "Group"]] | None = None

    .. versionchanged:: 0.6.0

        - ``Reference[ExternalReference]`` becomes ``Reference[External]``
        - ``Reference[URIReference]`` becomes ``Reference[URI]``
        - ``Reference[Literal["User"]]`` becomes ``Reference["User"]``
        - ``Reference[Literal["User"] | Literal["Group"]]`` becomes
          ``Reference[Union["User", "Group"]]``
    """

    __slots__ = ()
    __reference_types__: tuple[str, ...] = ()
    _cache: dict[tuple[str, ...], type["Reference[Any]"]] = {}

    def __class_getitem__(cls, item: Any) -> type["Reference[Any]"]:
        if get_origin(item) in UNION_TYPES:
            items = get_args(item)
        else:
            items = (item,)

        type_strings = tuple(_to_type_string(i) for i in items)

        if type_strings in cls._cache:
            return cls._cache[type_strings]

        class TypedReference(cls):  # type: ignore[valid-type,misc]
            __reference_types__ = type_strings

        TypedReference.__name__ = f"Reference[{' | '.join(type_strings)}]"
        TypedReference.__qualname__ = TypedReference.__name__
        cls._cache[type_strings] = TypedReference
        return TypedReference

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        source_type: type[Any],
        handler: GetCoreSchemaHandler,
    ) -> core_schema.CoreSchema:
        ref_types = getattr(source_type, "__reference_types__", ())

        def validate(value: Any) -> "Reference[Any]":
            if not isinstance(value, str):
                raise ValueError(f"Expected string, got {type(value).__name__}")
            if "external" in ref_types or "uri" in ref_types:
                _validate_uri(value)
            return source_type(value)  # type: ignore[no-any-return]

        return core_schema.no_info_plain_validator_function(
            validate,
            serialization=core_schema.plain_serializer_function_ser_schema(str),
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        _core_schema: core_schema.CoreSchema,
        _handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        return {"type": "string", "format": "uri"}

    @classmethod
    def get_scim_reference_types(cls) -> list[str]:
        """Return referenceTypes for SCIM schema generation."""
        return list(cls.__reference_types__)


def _to_type_string(item: Any) -> str:
    """Convert any type parameter to its SCIM referenceType string."""
    if item is Any:
        return "uri"
    if item is External:
        return "external"
    if item is ExternalReference:
        warnings.warn(
            "Reference[ExternalReference] is deprecated, "
            "use Reference[External] instead. Will be removed in 0.7.0.",
            DeprecationWarning,
            stacklevel=4,
        )
        return "external"
    if item is URI:
        return "uri"
    if item is URIReference:
        warnings.warn(
            "Reference[URIReference] is deprecated, "
            "use Reference[URI] instead. Will be removed in 0.7.0.",
            DeprecationWarning,
            stacklevel=4,
        )
        return "uri"
    if isinstance(item, str):
        return item
    if isinstance(item, type):
        return item.__name__
    if hasattr(item, "__forward_arg__"):
        return item.__forward_arg__  # type: ignore[no-any-return]
    # Support Literal["User"] for backwards compatibility
    if get_origin(item) is Literal:
        value = get_args(item)[0]
        warnings.warn(
            f'Reference[Literal["{value}"]] is deprecated, '
            f'use Reference["{value}"] instead. Will be removed in 0.7.0.',
            DeprecationWarning,
            stacklevel=4,
        )
        return value  # type: ignore[no-any-return]
    raise TypeError(f"Invalid reference type: {item!r}")


def _validate_uri(value: str) -> None:
    """Validate URI format, allowing relative URIs per RFC 7643."""
    if value.startswith("/"):
        return
    try:
        Url(value)
    except ValidationError as e:
        raise ValueError(f"Invalid URI: {value}") from e
