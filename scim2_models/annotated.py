"""Pydantic-compatible annotations for SCIM context validation and serialization.

These markers can be used with :data:`typing.Annotated` to inject a SCIM
:class:`~scim2_models.Context` into Pydantic validation and serialization,
making integration with web frameworks like FastAPI idiomatic::

    from typing import Annotated


    @router.post("/Users", status_code=201)
    async def create_user(
        user: Annotated[User, SCIMValidator(Context.RESOURCE_CREATION_REQUEST)],
    ) -> Annotated[User, SCIMSerializer(Context.RESOURCE_CREATION_RESPONSE)]:
        ...
        return response_user
"""

import json
from typing import Any

from pydantic import GetCoreSchemaHandler
from pydantic_core import CoreSchema
from pydantic_core import core_schema

from scim2_models.context import Context


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
            return json.loads(value.model_dump_json(scim_ctx=ctx))

        return core_schema.no_info_wrap_validator_function(
            lambda v, h: h(v),
            schema,
            serialization=core_schema.wrap_serializer_function_ser_schema(
                serialize_with_context,
                schema=schema,
            ),
        )
