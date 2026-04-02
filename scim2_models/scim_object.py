"""Base SCIM object classes with schema identification."""

import warnings
from typing import TYPE_CHECKING
from typing import Annotated
from typing import Any
from typing import ClassVar

from pydantic import ValidationInfo
from pydantic import ValidatorFunctionWrapHandler
from pydantic import model_validator
from pydantic._internal._model_construction import ModelMetaclass
from pydantic_core import PydanticCustomError
from typing_extensions import Self

from .annotations import Required
from .base import BaseModel
from .context import Context
from .path import URN
from .path import Path

if TYPE_CHECKING:
    pass


class ScimMetaclass(ModelMetaclass):
    """Metaclass for SCIM objects that handles __schema__ backward compatibility."""

    def __new__(
        mcs,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        **kwargs: Any,
    ) -> type:
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)

        if name in ("ScimObject", "Resource", "Extension"):
            return cls

        if getattr(cls, "__schema__", None) is None:
            schemas_field = cls.model_fields.get("schemas")  # type: ignore[attr-defined]
            if (
                schemas_field
                and schemas_field.default
                and isinstance(schemas_field.default, list)
                and schemas_field.default
            ):
                schema_value = schemas_field.default[0]
                try:
                    cls.__schema__ = URN(schema_value)  # type: ignore[attr-defined]
                    warnings.warn(
                        f"{name}: Defining schemas with a default value is deprecated "
                        f"and will be removed in version 0.7. "
                        f'Use __schema__ = URN("{schema_value}") instead.',
                        DeprecationWarning,
                        stacklevel=2,
                    )
                except ValueError:
                    pass

        return cls


class ScimObject(BaseModel, metaclass=ScimMetaclass):
    __schema__: ClassVar[URN | None] = None

    schemas: Annotated[list[str], Required.true]
    """The "schemas" attribute is a REQUIRED attribute and is an array of
    Strings containing URIs that are used to indicate the namespaces of the
    SCIM schemas that define the attributes present in the current JSON
    structure."""

    @model_validator(mode="before")
    @classmethod
    def _populate_schemas_default(cls, data: Any) -> Any:
        """Auto-generate schemas from __schema__ if not provided."""
        if isinstance(data, dict) and "schemas" not in data:
            schema = getattr(cls, "__schema__", None)
            if schema:
                data = {**data, "schemas": [schema]}
        return data

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

    def _prepare_model_dump(
        self,
        scim_ctx: Context | None = Context.DEFAULT,
        attributes: list[str | Path[Any]] | None = None,
        excluded_attributes: list[str | Path[Any]] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        kwargs.setdefault("context", {}).setdefault("scim", scim_ctx)

        if scim_ctx:
            kwargs.setdefault("exclude_none", True)
            kwargs.setdefault("by_alias", True)

        if attributes:
            kwargs["context"]["scim_attributes"] = [str(a) for a in attributes]
        if excluded_attributes:
            kwargs["context"]["scim_excluded_attributes"] = [
                str(a) for a in excluded_attributes
            ]

        return kwargs

    def model_dump(
        self,
        *args: Any,
        scim_ctx: Context | None = Context.DEFAULT,
        attributes: list[str | Path[Any]] | None = None,
        excluded_attributes: list[str | Path[Any]] | None = None,
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
            scim_ctx,
            attributes=attributes,
            excluded_attributes=excluded_attributes,
            **kwargs,
        )
        if scim_ctx:
            dump_kwargs.setdefault("mode", "json")
        return super(BaseModel, self).model_dump(*args, **dump_kwargs)

    def model_dump_json(
        self,
        *args: Any,
        scim_ctx: Context | None = Context.DEFAULT,
        attributes: list[str | Path[Any]] | None = None,
        excluded_attributes: list[str | Path[Any]] | None = None,
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
            scim_ctx,
            attributes=attributes,
            excluded_attributes=excluded_attributes,
            **kwargs,
        )
        return super(BaseModel, self).model_dump_json(*args, **dump_kwargs)
