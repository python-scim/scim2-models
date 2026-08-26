"""Base SCIM object classes with schema identification."""

from typing import Annotated
from typing import Any
from typing import ClassVar
from typing import TypeVar

from pydantic import ValidationInfo
from pydantic import ValidatorFunctionWrapHandler
from pydantic import model_validator
from pydantic_core import PydanticCustomError
from typing_extensions import Self

from .annotations import Required
from .annotations import Returned
from .base import BaseModel
from .context import Context
from .path import URN


class ScimObject(BaseModel):
    __schema__: ClassVar[URN | None] = None

    schemas: Annotated[list[str], Required.true, Returned.always]
    """The "schemas" attribute is a REQUIRED attribute and is an array of
    Strings containing URIs that are used to indicate the namespaces of the
    SCIM schemas that define the attributes present in the current JSON
    structure."""

    @model_validator(mode="before")
    @classmethod
    def _populate_schemas_default(cls, data: Any, info: ValidationInfo) -> Any:
        """Auto-generate schemas from __schema__ if not provided.

        Objects built by the caller are filled, as the model they are built
        from asserts their type. Payloads validated in a SCIM context come
        from a peer that :rfc:`RFC7643 §3 <7643#section-3>` requires to send
        the attribute, so the omission is reported instead of being papered
        over. Extensions are never standalone representations, and bear no
        'schemas' attribute of their own.
        """
        if not isinstance(data, dict) or "schemas" in data:
            return data

        schema = getattr(cls, "__schema__", None)
        if not schema:
            return data

        scim_ctx = info.context.get("scim") if info.context else None
        if scim_ctx and scim_ctx != Context.DEFAULT:
            from .resources.resource import Extension

            if not issubclass(cls, Extension):
                return data

        return {**data, "schemas": [schema]}

    @model_validator(mode="wrap")
    @classmethod
    def _validate_schemas_attribute(
        cls, value: Any, handler: ValidatorFunctionWrapHandler, info: ValidationInfo
    ) -> Self:
        """Validate that the base schema is present in schemas attribute."""
        obj: Self = handler(value)

        scim_ctx = info.context.get("scim") if info.context else None
        if scim_ctx is None or scim_ctx == Context.DEFAULT:
            return obj

        schema = getattr(cls, "__schema__", None)
        if schema and schema not in obj.schemas:
            raise PydanticCustomError(
                "schema_error",
                "schemas must contain the base schema '{schema}'",
                {"schema": schema},
            )

        return obj


AnyScimObject = TypeVar("AnyScimObject", bound=ScimObject)
