from collections.abc import Callable
from inspect import isclass
from typing import Annotated
from typing import Any
from typing import TypeVar
from typing import Union
from typing import cast
from typing import get_args
from typing import get_origin

from pydantic import Discriminator
from pydantic import Tag
from pydantic._internal._model_construction import ModelMetaclass

from scim2_models.resources.resource import Resource

from ..base import BaseModel
from ..scim_object import ScimObject
from ..utils import UNION_TYPES


class Message(ScimObject):
    """SCIM protocol messages as defined by :rfc:`RFC7644 §3.1 <7644#section-3.1>`."""

    def _scim_response_serializer(
        self,
        serialized: dict[str, Any],
        included_attrs: list[str],
        excluded_attrs: list[str],
    ) -> None:
        """Message fields are not subject to attribute filtering."""


def _create_schema_discriminator(
    resource_types_schemas: list[str],
) -> Callable[[Any], str | None]:
    """Build the discriminator pydantic calls to tell resource types apart."""

    def get_schema_from_payload(payload: Any) -> str | None:
        """Return the first schema of the payload naming one of the resource types."""
        if not payload:
            return None

        if isinstance(payload, dict):
            payload_schemas = payload.get("schemas", [])
        else:
            # An instance asserts its type by its class.
            schema = getattr(type(payload), "__schema__", None)
            payload_schemas = ([str(schema)] if schema else []) + list(payload.schemas)

        common_schemas = [
            schema for schema in payload_schemas if schema in resource_types_schemas
        ]
        return common_schemas[0] if common_schemas else None

    return get_schema_from_payload


def _get_tag(resource_type: type[BaseModel]) -> Tag:
    """Tag a resource type by its schema, for pydantic to discriminate on."""
    return Tag(getattr(resource_type, "__schema__", None) or "")


def _create_tagged_resource_union(resource_union: Any) -> Any:
    """Build Discriminated Unions for SCIM resources.

    Creates discriminated unions so Pydantic can determine which class to
    instantiate by inspecting the payload's schemas field. A type that is not a
    union is answered as it stands.
    """
    if get_origin(resource_union) not in UNION_TYPES:
        return resource_union

    resource_types = get_args(resource_union)

    # Set up schemas for the discriminator function
    resource_types_schemas = [
        getattr(resource_type, "__schema__", None) or ""
        for resource_type in resource_types
    ]

    # Create discriminator function with schemas captured in closure
    schema_discriminator = _create_schema_discriminator(resource_types_schemas)
    discriminator = Discriminator(schema_discriminator)

    tagged_resources = [
        Annotated[resource_type, _get_tag(resource_type)]
        for resource_type in resource_types
    ]
    # Dynamic union construction from tuple - MyPy can't validate this at compile time
    union = Union[tuple(tagged_resources)]  # type: ignore  # noqa: UP007
    return Annotated[union, discriminator]


class _GenericMessageMetaclass(ModelMetaclass):
    """Metaclass for SCIM generic types with discriminated unions."""

    def __new__(
        cls, name: str, bases: tuple[type, ...], attrs: dict[str, Any], **kwargs: Any
    ) -> type:
        """Create class with tagged resource unions for generic parameters."""
        if kwargs.get("__pydantic_generic_metadata__") and kwargs[
            "__pydantic_generic_metadata__"
        ].get("args"):
            tagged_union = _create_tagged_resource_union(
                kwargs["__pydantic_generic_metadata__"]["args"][0]
            )
            kwargs["__pydantic_generic_metadata__"]["args"] = (tagged_union,)

        klass = super().__new__(cls, name, bases, attrs, **kwargs)
        return klass


def _type_parameter(model: type) -> Any | None:
    """Return the type parameter a model was built with, or None when it has none.

    A subclass of a parameterized model, such as ``class
    Users(ListResponse[User])``, carries no parameter of its own and answers
    the one it inherits.
    """
    for klass in getattr(model, "__mro__", (model,)):
        metadata = getattr(klass, "__pydantic_generic_metadata__", None)
        if metadata and metadata["args"]:
            return metadata["args"][0]
    return None


def _parameter_members(parameter: Any) -> tuple[Any, ...]:
    """Return the types a parameter names, unions flattened and annotations dropped.

    A union reaches here as it was written, or tagged for discrimination once
    the metaclass has been through it.
    """
    if get_origin(parameter) is Annotated:
        return _parameter_members(get_args(parameter)[0])

    if get_origin(parameter) in UNION_TYPES:
        members: tuple[Any, ...] = ()
        for member in get_args(parameter):
            members += _parameter_members(member)
        return members

    return (parameter,)


def _is_resource_type(member: Any) -> bool:
    return isclass(member) and issubclass(member, Resource)


def _designates_resources(parameter: Any) -> bool:
    """Whether a parameter names resource types, and nothing else.

    A type variable bound to a resource type names them too: it stands for the
    types a generic caller will substitute.
    """
    members = _parameter_members(parameter)
    return bool(members) and all(
        _is_resource_type(member)
        or (isinstance(member, TypeVar) and _is_resource_type(member.__bound__))
        for member in members
    )


def _names_concrete_resources(parameter: Any) -> bool:
    """Whether every type a parameter names declares the attributes of a resource.

    Resource itself and an unsubstituted type variable declare none, so a
    payload read against them fails on the first attribute it carries.
    """
    members = _parameter_members(parameter)
    return bool(members) and all(
        _is_resource_type(member) and member is not Resource for member in members
    )


class _ResourceParameterized:
    """A model whose type parameter names the resource types its payloads carry.

    The parameter says which model a payload is read as, so reading or building
    one requires it to name concrete resource types. Writing
    ListResponse[Resource] stays allowed where a type is expected rather than
    used, which is what an annotation covering any resource type needs.
    """

    def __class_getitem__(cls, item: Any) -> Any:
        """Refuse a parameter naming anything but resource types."""
        # Pydantic sometimes re-subscripts an already partially-parameterized
        # model by passing a 1-tuple instead of the bare value.
        parameter = item[0] if isinstance(item, tuple) and len(item) == 1 else item

        if not _designates_resources(parameter):
            raise TypeError(
                f"{cls.__name__} type parameter must name resource types, "
                f"got {parameter}. Use {cls.__name__}[User]."
            )

        return super().__class_getitem__(item)  # type: ignore[misc]

    def __new__(cls, *args: Any, **kwargs: Any) -> Any:
        _check_type_parameter(cls)
        return super().__new__(cls)

    @classmethod
    def _prepare_model_validate(cls, *args: Any, **kwargs: Any) -> dict[str, Any]:
        _check_type_parameter(cls)
        return super()._prepare_model_validate(*args, **kwargs)  # type: ignore[misc,no-any-return]


def _check_type_parameter(model: type) -> None:
    """Refuse a model whose type parameter names no concrete resource type.

    Left alone, the type variable falls back on its bound, and a valid payload
    fails deep inside on an attribute that bound does not declare, blaming an
    attribute for a missing parameter.
    """
    parameter = _type_parameter(model)
    if parameter is not None and _names_concrete_resources(parameter):
        return

    metadata = getattr(model, "__pydantic_generic_metadata__", None)
    origin = (metadata or {}).get("origin") or model
    name = origin.__name__

    if parameter is None:
        raise TypeError(
            f"{name} requires a type parameter naming the resource types its "
            f"payloads carry, such as {name}[User]."
        )

    raise TypeError(
        f"{name}[{_parameter_label(parameter)}] declares no attribute a payload "
        f"could be read as. Name the resource types the payloads carry, such as "
        f"{name}[User]."
    )


def _parameter_label(parameter: Any) -> str:
    """How a type parameter reads in an error message."""
    return " | ".join(
        getattr(member, "__name__", None) or str(member)
        for member in _parameter_members(parameter)
    )


def _get_resource_class(obj: BaseModel) -> type[Resource[Any]]:
    """Extract the resource class from generic type parameter."""
    return cast("type[Resource[Any]]", _type_parameter(obj.__class__))
