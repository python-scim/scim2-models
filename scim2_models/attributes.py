from enum import Enum
from inspect import isclass
from typing import Annotated
from typing import Any
from typing import ClassVar
from typing import get_origin

from pydantic import Field
from pydantic import GetJsonSchemaHandler
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema
from typing_extensions import Self

from .annotations import Mutability

# This import will work because we'll import this module after BaseModel is defined
from .base import BaseModel
from .reference import Reference


class ExtensibleStringEnum(str, Enum):
    """String enum accepting values beyond its canonical ones.

    :rfc:`RFC7643 §2.3.1 <7643#section-2.3.1>` and :rfc:`§7 <7643#section-7>`
    define ``canonicalValues`` as suggestions that service providers MAY restrict,
    so unknown values are kept as-is instead of being rejected.
    """

    def __str__(self) -> str:
        return str(self.value)

    @classmethod
    def __get_pydantic_json_schema__(
        cls, core_schema: CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        """Advertise the canonical values as examples rather than as a closed set."""
        json_schema = handler.resolve_ref_schema(handler(core_schema))
        json_schema.pop("enum", None)
        json_schema["examples"] = [member.value for member in cls]
        return json_schema

    @classmethod
    def _missing_(cls, value: Any) -> Self:
        """Match canonical values regardless of their case, and keep unknown ones as-is.

        Attributes bearing ``canonicalValues`` are case-insensitive unless stated
        otherwise by :rfc:`RFC7643 §2.2 <7643#section-2.2>`.
        """
        if not isinstance(value, str):
            raise ValueError(f"{value} is not a valid string value for {cls.__name__}")

        for member in cls:
            if member.value.lower() == value.lower():
                return member

        obj = str.__new__(cls, value)
        obj._name_ = value
        obj._value_ = value
        return obj


class ComplexAttribute(BaseModel):
    """A complex attribute as defined in :rfc:`RFC7643 §2.3.8 <7643#section-2.3.8>`."""

    __is_complex_attribute__: ClassVar[bool] = True

    _attribute_urn: str | None = None

    def get_attribute_urn(self, field_name: str) -> str:
        """Build the full URN of the attribute.

        See :rfc:`RFC7644 §3.10 <7644#section-3.10>`.
        """
        alias = (
            self.__class__.model_fields[field_name].serialization_alias or field_name
        )
        return f"{self._attribute_urn}.{alias}"


class MultiValuedComplexAttribute(ComplexAttribute):
    type: str | None = None
    """A label indicating the attribute's function."""

    primary: bool | None = None
    """A Boolean value indicating the 'primary' or preferred attribute value
    for this attribute.

    Per :rfc:`RFC 7643 §2.4 <7643#section-2.4>`, the primary attribute value
    ``True`` MUST appear no more than once in a multi-valued attribute list.
    """

    display: Annotated[str | None, Mutability.immutable] = None
    """A human-readable name, primarily used for display purposes."""

    value: Any | None = None
    """The value of an entitlement."""

    ref: Reference[Any] | None = Field(None, serialization_alias="$ref")
    """The reference URI of a target resource, if the attribute is a
    reference."""


def is_complex_attribute(type_: type) -> bool:
    # issubclass raise a TypeError with 'Reference' on python < 3.11
    return (
        get_origin(type_) != Reference
        and isclass(type_)
        and issubclass(type_, ComplexAttribute)
    )
