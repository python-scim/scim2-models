"""Base SCIM object classes with schema identification."""

from typing import Annotated
from typing import Any
from typing import ClassVar
from typing import TypeVar

from pydantic import Field
from pydantic import ValidationInfo
from pydantic import ValidatorFunctionWrapHandler
from pydantic import field_serializer
from pydantic import model_validator
from pydantic_core import PydanticCustomError
from typing_extensions import Self

from .annotations import Required
from .base import BaseModel
from .context import Context
from .path import URN


class ScimObject(BaseModel):
    __schema__: ClassVar[URN | None] = None

    schemas: Annotated[list[str], Required.true] = Field(default_factory=list)
    """The "schemas" attribute is a REQUIRED attribute and is an array of
    Strings containing URIs that are used to indicate the namespaces of the
    SCIM schemas that define the attributes present in the current JSON
    structure.

    It only holds what a peer asserted, and is empty when a payload omitted
    it: SCIM dumps build it from the model definition.
    """

    def _model_schemas(self) -> list[str]:
        """List the schemas asserted by the model definition."""
        schema = getattr(self.__class__, "__schema__", None)
        return [str(schema)] if schema else []

    @field_serializer("schemas")
    def _serialize_schemas(self, schemas: list[str]) -> list[str]:
        """Build the 'schemas' attribute from the model definition.

        Unknown schemas a peer sent are kept, as :rfc:`RFC7643 §3
        <7643#section-3>` does not restrict the array to known schemas.
        """
        serialized = self._model_schemas()
        for schema in schemas:
            if schema not in serialized:
                serialized.append(schema)
        return serialized

    @model_validator(mode="before")
    @classmethod
    def _populate_schemas_default(cls, data: Any, info: ValidationInfo) -> Any:
        """Fill the schemas of objects built by the caller.

        The model they are built from asserts their type. Payloads validated
        in a SCIM context come from a peer, so what they omitted stays
        omitted.
        """
        if not isinstance(data, dict) or "schemas" in data:
            return data

        schema = getattr(cls, "__schema__", None)
        if not schema:
            return data

        scim_ctx = info.context.get("scim") if info.context else None
        if scim_ctx and scim_ctx != Context.DEFAULT:
            return data

        return {**data, "schemas": [schema]}

    @model_validator(mode="wrap")
    @classmethod
    def _validate_schemas_attribute(
        cls, value: Any, handler: ValidatorFunctionWrapHandler, info: ValidationInfo
    ) -> Self:
        """Validate that the schemas a payload asserts match the model.

        An object cannot contradict the model it is an instance of, whatever
        the validation context. An omitted attribute asserts nothing.
        """
        obj: Self = handler(value)

        schema = getattr(cls, "__schema__", None)
        if schema and obj.schemas and schema not in obj.schemas:
            raise PydanticCustomError(
                "schema_error",
                "schemas must contain the base schema '{schema}'",
                {"schema": schema},
            )

        return obj


AnyScimObject = TypeVar("AnyScimObject", bound=ScimObject)
