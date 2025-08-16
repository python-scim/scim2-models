from inspect import isclass
from typing import Annotated
from typing import Any
from typing import Optional
from typing import get_origin

from pydantic import Field

from .annotations import Mutability

# This import will work because we'll import this module after BaseModel is defined
from .base import BaseModel
from .reference import Reference


class ComplexAttribute(BaseModel):
    """A complex attribute as defined in :rfc:`RFC7643 §2.3.8 <7643#section-2.3.8>`."""

    _attribute_urn: Optional[str] = None

    def get_attribute_urn(self, field_name: str) -> str:
        """Build the full URN of the attribute.

        See :rfc:`RFC7644 §3.10 <7644#section-3.10>`.
        """
        alias = (
            self.__class__.model_fields[field_name].serialization_alias or field_name
        )
        return f"{self._attribute_urn}.{alias}"


class MultiValuedComplexAttribute(ComplexAttribute):
    type: Optional[str] = None
    """A label indicating the attribute's function."""

    primary: Optional[bool] = None
    """A Boolean value indicating the 'primary' or preferred attribute value
    for this attribute."""

    display: Annotated[Optional[str], Mutability.immutable] = None
    """A human-readable name, primarily used for display purposes."""

    value: Optional[Any] = None
    """The value of an entitlement."""

    ref: Optional[Reference[Any]] = Field(None, serialization_alias="$ref")
    """The reference URI of a target resource, if the attribute is a
    reference."""


def is_complex_attribute(type_: type) -> bool:
    # issubclass raise a TypeError with 'Reference' on python < 3.11
    return (
        get_origin(type_) != Reference
        and isclass(type_)
        and issubclass(type_, ComplexAttribute)
    )
