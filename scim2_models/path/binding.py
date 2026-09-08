from collections.abc import MutableMapping
from typing import TYPE_CHECKING
from typing import Any
from weakref import WeakValueDictionary

from pydantic import GetCoreSchemaHandler
from pydantic import GetJsonSchemaHandler
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import core_schema

from ..exceptions import SCIMException
from ..utils import _model_union

if TYPE_CHECKING:
    from ..base import BaseModel

_BOUND_CLASSES: "MutableMapping[tuple[type, tuple[type, ...]], type]" = (
    WeakValueDictionary()
)
"""The classes subscription has already built, so that two subscriptions of the
same resource types answer the same class.

The classes are held weakly: one bound to a model built at runtime, as a server
serving a schema it discovered does, would otherwise keep that model alive for
as long as the process runs."""


class _BoundToModels:
    """A string whose attribute names are resolved against resource types.

    :class:`~scim2_models.Path` and :class:`~scim2_models.ScimFilter` both name
    attributes that only mean something against a model, and both are
    subscripted with the resource types an endpoint serves. Subscription, the
    cache of classes it fills and the pydantic plumbing are the same for either.

    The :attr:`~scim2_models.Path.models` each of them answers stays declared
    where it is documented, since autodoc leaves an inherited member out.
    """

    __scim_models__: "tuple[type[BaseModel], ...]" = ()

    @classmethod
    def _unbound_name(cls) -> str:
        """Return the name of the type, without the models bound to it."""
        return cls.__name__.split("[", 1)[0]

    def __class_getitem__(cls, model: Any) -> type:
        """Create a class bound to a resource type, or to a union of them.

        A union is what an endpoint covering several resource types binds, such
        as the server root of :rfc:`RFC7644 §3.4.2.1 <7644#section-3.4.2.1>`.
        Anything that is not a resource type, a type variable in particular, is
        left to the generic machinery.
        """
        models = _model_union(model)
        if models is None:
            return super().__class_getitem__(model)  # type: ignore[misc,no-any-return]

        cache_key = (cls, models)
        if cache_key not in _BOUND_CLASSES:
            names = ", ".join(each.__name__ for each in models)
            _BOUND_CLASSES[cache_key] = type(
                f"{cls._unbound_name()}[{names}]", (cls,), {"__scim_models__": models}
            )
        return _BOUND_CLASSES[cache_key]

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: type[Any],
        _handler: GetCoreSchemaHandler,
    ) -> core_schema.CoreSchema:
        def validate(value: Any) -> Any:
            if not isinstance(value, str):
                raise ValueError(
                    f"Expected str or {cls._unbound_name()}, got {type(value).__name__}"
                )
            # Whatever the value gets wrong is reported through the pydantic
            # error, so the failure names the field it was read from and still
            # carries its scimType.
            try:
                return cls(value)  # type: ignore[call-arg]
            except SCIMException as exc:
                raise exc.as_pydantic_error() from exc

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
        return {"type": "string"}
