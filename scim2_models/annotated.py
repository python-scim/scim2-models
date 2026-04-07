"""Pydantic-compatible annotations for SCIM context validation and serialization.

These markers can be used with :data:`typing.Annotated` to inject a SCIM
:class:`~scim2_models.Context` into Pydantic validation and serialization,
making integration with web frameworks like FastAPI idiomatic::

    from scim2_models import CreationRequestContext, CreationResponseContext, User


    @router.post("/Users", status_code=201)
    async def create_user(
        user: CreationRequestContext[User],
    ) -> CreationResponseContext[User]:
        ...
        return response_user
"""

import sys
from typing import TYPE_CHECKING
from typing import Annotated
from typing import Any
from typing import TypeVar

if sys.version_info >= (3, 12):
    from typing import TypeAliasType
else:  # pragma: no cover
    from typing_extensions import TypeAliasType

from pydantic import GetCoreSchemaHandler
from pydantic_core import CoreSchema
from pydantic_core import core_schema

from scim2_models.context import Context

T = TypeVar("T")


class SCIMValidator:
    """Annotated marker that injects a SCIM context during Pydantic validation.

    When used in a :data:`typing.Annotated` type hint, the incoming data is
    validated through :meth:`~scim2_models.base.BaseModel.model_validate` with
    the given *ctx*, activating all SCIM-specific validators (mutability,
    required fields, etc.).

    :param ctx: The SCIM context to use during validation.
    """

    def __init__(self, ctx: Context) -> None:
        self.ctx = ctx

    def __get_pydantic_core_schema__(
        self, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        schema = handler(source_type)
        ctx = self.ctx

        def validate_with_context(value: Any, handler: Any) -> Any:
            if isinstance(value, dict):
                return source_type.model_validate(value, scim_ctx=ctx)
            return handler(value)

        return core_schema.no_info_wrap_validator_function(
            validate_with_context, schema
        )


class SCIMSerializer:
    """Annotated marker that injects a SCIM context during Pydantic serialization.

    When used in a :data:`typing.Annotated` type hint on a return type, the
    response object is serialized through
    :meth:`~scim2_models.scim_object.SCIMObject.model_dump_json` with the
    given *ctx*, applying returnability and mutability rules.

    :param ctx: The SCIM context to use during serialization.
    """

    def __init__(self, ctx: Context) -> None:
        self.ctx = ctx

    def __get_pydantic_core_schema__(
        self, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        schema = handler(source_type)
        ctx = self.ctx

        def serialize_with_context(value: Any, _handler: Any) -> Any:
            return value.model_dump(scim_ctx=ctx)

        return core_schema.no_info_wrap_validator_function(
            lambda v, h: h(v),
            schema,
            serialization=core_schema.wrap_serializer_function_ser_schema(
                serialize_with_context,
                schema=schema,
            ),
        )


if TYPE_CHECKING:
    CreationRequestContext = TypeAliasType(
        "CreationRequestContext",
        Annotated[T, SCIMValidator(Context.RESOURCE_CREATION_REQUEST)],
        type_params=(T,),
    )
    CreationResponseContext = TypeAliasType(
        "CreationResponseContext",
        Annotated[T, SCIMSerializer(Context.RESOURCE_CREATION_RESPONSE)],
        type_params=(T,),
    )
    QueryRequestContext = TypeAliasType(
        "QueryRequestContext",
        Annotated[T, SCIMValidator(Context.RESOURCE_QUERY_REQUEST)],
        type_params=(T,),
    )
    QueryResponseContext = TypeAliasType(
        "QueryResponseContext",
        Annotated[T, SCIMSerializer(Context.RESOURCE_QUERY_RESPONSE)],
        type_params=(T,),
    )
    ReplacementRequestContext = TypeAliasType(
        "ReplacementRequestContext",
        Annotated[T, SCIMValidator(Context.RESOURCE_REPLACEMENT_REQUEST)],
        type_params=(T,),
    )
    ReplacementResponseContext = TypeAliasType(
        "ReplacementResponseContext",
        Annotated[T, SCIMSerializer(Context.RESOURCE_REPLACEMENT_RESPONSE)],
        type_params=(T,),
    )
    SearchRequestContext = TypeAliasType(
        "SearchRequestContext",
        Annotated[T, SCIMValidator(Context.SEARCH_REQUEST)],
        type_params=(T,),
    )
    SearchResponseContext = TypeAliasType(
        "SearchResponseContext",
        Annotated[T, SCIMSerializer(Context.SEARCH_RESPONSE)],
        type_params=(T,),
    )
    PatchRequestContext = TypeAliasType(
        "PatchRequestContext",
        Annotated[T, SCIMValidator(Context.RESOURCE_PATCH_REQUEST)],
        type_params=(T,),
    )
    PatchResponseContext = TypeAliasType(
        "PatchResponseContext",
        Annotated[T, SCIMSerializer(Context.RESOURCE_PATCH_RESPONSE)],
        type_params=(T,),
    )
else:

    class _RequestContextAlias:
        """Base class for request context type aliases."""

        _ctx: Context

        def __class_getitem__(cls, item: type) -> Any:
            return Annotated[item, SCIMValidator(cls._ctx)]

    class _ResponseContextAlias:
        """Base class for response context type aliases."""

        _ctx: Context

        def __class_getitem__(cls, item: type) -> Any:
            return Annotated[item, SCIMSerializer(cls._ctx)]

    class CreationRequestContext(_RequestContextAlias):
        """Shortcut for ``Annotated[T, SCIMValidator(Context.RESOURCE_CREATION_REQUEST)]``."""

        _ctx = Context.RESOURCE_CREATION_REQUEST

    class CreationResponseContext(_ResponseContextAlias):
        """Shortcut for ``Annotated[T, SCIMSerializer(Context.RESOURCE_CREATION_RESPONSE)]``."""

        _ctx = Context.RESOURCE_CREATION_RESPONSE

    class QueryRequestContext(_RequestContextAlias):
        """Shortcut for ``Annotated[T, SCIMValidator(Context.RESOURCE_QUERY_REQUEST)]``."""

        _ctx = Context.RESOURCE_QUERY_REQUEST

    class QueryResponseContext(_ResponseContextAlias):
        """Shortcut for ``Annotated[T, SCIMSerializer(Context.RESOURCE_QUERY_RESPONSE)]``."""

        _ctx = Context.RESOURCE_QUERY_RESPONSE

    class ReplacementRequestContext(_RequestContextAlias):
        """Shortcut for ``Annotated[T, SCIMValidator(Context.RESOURCE_REPLACEMENT_REQUEST)]``."""

        _ctx = Context.RESOURCE_REPLACEMENT_REQUEST

    class ReplacementResponseContext(_ResponseContextAlias):
        """Shortcut for ``Annotated[T, SCIMSerializer(Context.RESOURCE_REPLACEMENT_RESPONSE)]``."""

        _ctx = Context.RESOURCE_REPLACEMENT_RESPONSE

    class SearchRequestContext(_RequestContextAlias):
        """Shortcut for ``Annotated[T, SCIMValidator(Context.SEARCH_REQUEST)]``."""

        _ctx = Context.SEARCH_REQUEST

    class SearchResponseContext(_ResponseContextAlias):
        """Shortcut for ``Annotated[T, SCIMSerializer(Context.SEARCH_RESPONSE)]``."""

        _ctx = Context.SEARCH_RESPONSE

    class PatchRequestContext(_RequestContextAlias):
        """Shortcut for ``Annotated[T, SCIMValidator(Context.RESOURCE_PATCH_REQUEST)]``."""

        _ctx = Context.RESOURCE_PATCH_REQUEST

    class PatchResponseContext(_ResponseContextAlias):
        """Shortcut for ``Annotated[T, SCIMSerializer(Context.RESOURCE_PATCH_RESPONSE)]``."""

        _ctx = Context.RESOURCE_PATCH_RESPONSE
