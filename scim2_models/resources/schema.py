import re
from datetime import datetime
from enum import Enum
from typing import Annotated
from typing import Any
from typing import List  # noqa : UP005,UP035
from typing import Optional
from typing import TypeVar
from typing import Union

from pydantic import Base64Bytes
from pydantic import Field
from pydantic import create_model
from pydantic import field_validator
from pydantic.alias_generators import to_pascal
from pydantic.alias_generators import to_snake
from pydantic_core import Url

from ..annotations import CaseExact
from ..annotations import Mutability
from ..annotations import Required
from ..annotations import Returned
from ..annotations import Uniqueness
from ..attributes import ComplexAttribute
from ..attributes import is_complex_attribute
from ..base import BaseModel
from ..constants import RESERVED_WORDS
from ..path import URN
from ..reference import URI
from ..reference import External
from ..reference import Reference
from ..utils import _normalize_attribute_name
from .resource import Resource

T = TypeVar("T", bound=BaseModel)

_NON_WORD_OR_LEADING_DIGIT = re.compile(r"\W|^(?=\d)")


def _make_python_identifier(identifier: str) -> str:
    """Sanitize string to be a suitable Python/Pydantic class attribute name."""
    sanitized = _NON_WORD_OR_LEADING_DIGIT.sub("", identifier)
    if sanitized in RESERVED_WORDS:
        sanitized = f"{sanitized}_"

    return sanitized


def _make_python_model(
    obj: Union["Schema", "Attribute"],
    base: type[T],
) -> type[T]:
    """Build a Python model from a Schema or an Attribute object."""
    if isinstance(obj, Attribute):
        pydantic_attributes = {
            to_snake(_make_python_identifier(attr.name)): attr._to_python()
            for attr in (obj.sub_attributes or [])
            if attr.name
        }

    else:
        pydantic_attributes = {
            to_snake(_make_python_identifier(attr.name)): attr._to_python()
            for attr in (obj.attributes or [])
            if attr.name
        }

    if not obj.name:
        raise ValueError("Schema or Attribute 'name' must be defined")

    model_name = to_pascal(to_snake(obj.name))
    model: type[T] = create_model(model_name, __base__=base, **pydantic_attributes)  # type: ignore[call-overload]

    if isinstance(obj, Schema) and obj.id:
        model.__schema__ = URN(obj.id)  # type: ignore[attr-defined]

    for attr_name in model.model_fields:
        attr_type = model.get_field_root_type(attr_name)
        if attr_type and is_complex_attribute(attr_type):
            setattr(model, attr_type.__name__, attr_type)

    return model


class Attribute(ComplexAttribute):
    class Type(str, Enum):
        string = "string"
        complex = "complex"
        boolean = "boolean"
        decimal = "decimal"
        integer = "integer"
        date_time = "dateTime"
        reference = "reference"
        binary = "binary"

        def _to_python(
            self,
            reference_types: list[str] | None = None,
        ) -> type:
            if self.value == self.reference and reference_types is not None:
                if reference_types == ["external"]:
                    return Reference[External]

                if reference_types == ["uri"]:
                    return Reference[URI]

                if len(reference_types) == 1:
                    return Reference[reference_types[0]]  # type: ignore[valid-type]
                return Reference[Union[tuple(reference_types)]]  # type: ignore[misc,return-value] # noqa: UP007

            attr_types = {
                self.string: str,
                self.boolean: bool,
                self.decimal: float,
                self.integer: int,
                self.date_time: datetime,
                self.binary: Base64Bytes,
                self.complex: ComplexAttribute,
            }
            return attr_types[self]

        @classmethod
        def from_python(cls, pytype: type) -> "Attribute.Type":
            if isinstance(pytype, type) and issubclass(pytype, Reference):
                return cls.reference

            if pytype and is_complex_attribute(pytype):
                return cls.complex

            if pytype in (Required, CaseExact):
                return cls.boolean

            attr_types = {
                str: cls.string,
                bool: cls.boolean,
                float: cls.decimal,
                int: cls.integer,
                datetime: cls.date_time,
                Base64Bytes: cls.binary,
            }
            return attr_types.get(pytype, cls.string)

    name: Annotated[str | None, Mutability.read_only, Required.true, CaseExact.true] = (
        None
    )
    """The attribute's name."""

    type: Annotated[Type | None, Mutability.read_only, Required.true] = Field(
        None, examples=[item.value for item in Type]
    )
    """The attribute's data type."""

    multi_valued: Annotated[bool | None, Mutability.read_only, Required.true] = None
    """A Boolean value indicating the attribute's plurality."""

    description: Annotated[
        str | None, Mutability.read_only, Required.false, CaseExact.true
    ] = None
    """The attribute's human-readable description."""

    required: Annotated[Required, Mutability.read_only, Required.false] = Required.false
    """A Boolean value that specifies whether or not the attribute is
    required."""

    canonical_values: Annotated[
        list[str] | None, Mutability.read_only, CaseExact.true
    ] = None
    """A collection of suggested canonical values that MAY be used (e.g.,
    "work" and "home")."""

    case_exact: Annotated[CaseExact, Mutability.read_only, Required.false] = (
        CaseExact.false
    )
    """A Boolean value that specifies whether or not a string attribute is case
    sensitive."""

    mutability: Annotated[
        Mutability, Mutability.read_only, Required.false, CaseExact.true
    ] = Field(Mutability.read_write, examples=[item.value for item in Mutability])
    """A single keyword indicating the circumstances under which the value of
    the attribute can be (re)defined."""

    returned: Annotated[
        Returned, Mutability.read_only, Required.false, CaseExact.true
    ] = Field(Returned.default, examples=[item.value for item in Returned])
    """A single keyword that indicates when an attribute and associated values
    are returned in response to a GET request or in response to a PUT, POST, or
    PATCH request."""

    uniqueness: Annotated[
        Uniqueness, Mutability.read_only, Required.false, CaseExact.true
    ] = Field(Uniqueness.none, examples=[item.value for item in Uniqueness])
    """A single keyword value that specifies how the service provider enforces
    uniqueness of attribute values."""

    reference_types: Annotated[
        list[str] | None, Mutability.read_only, Required.false, CaseExact.true
    ] = None
    """A multi-valued array of JSON strings that indicate the SCIM resource
    types that may be referenced."""

    # for python 3.9 and 3.10 compatibility, this should be 'list' and not 'List'
    sub_attributes: Annotated[List["Attribute"] | None, Mutability.read_only] = None  # noqa: UP006
    """When an attribute is of type "complex", "subAttributes" defines a set of
    sub-attributes."""

    def _to_python(self) -> tuple[Any, Any] | None:
        """Build tuple suited to be passed to pydantic 'create_model'."""
        if not self.name or not self.type:
            return None

        attr_type = self.type._to_python(self.reference_types)

        if attr_type == ComplexAttribute:
            attr_type = _make_python_model(obj=self, base=attr_type)

        if self.multi_valued:
            attr_type = list[attr_type]  # type: ignore

        annotation = Annotated[
            attr_type | None,  # type: ignore
            self.required,
            self.case_exact,
            self.mutability,
            self.returned,
            self.uniqueness,
        ]

        field = Field(
            description=self.description,
            examples=self.canonical_values,
            serialization_alias=self.name,
            validation_alias=_normalize_attribute_name(self.name),
            default=None,
        )

        return annotation, field

    def get_attribute(self, attribute_name: str) -> Optional["Attribute"]:
        """Find an attribute by its name."""
        for sub_attribute in self.sub_attributes or []:
            if sub_attribute.name == attribute_name:
                return sub_attribute
        return None

    def __getitem__(self, name: str) -> "Attribute":
        """Find an attribute by its name."""
        if attribute := self.get_attribute(name):
            return attribute
        raise KeyError(f"This attribute has no '{name}' sub-attribute")


class Schema(Resource[Any]):
    __schema__ = URN("urn:ietf:params:scim:schemas:core:2.0:Schema")

    id: Annotated[str | None, Mutability.read_only, Required.true] = None
    """The unique URI of the schema."""

    name: Annotated[
        str | None, Mutability.read_only, Returned.default, Required.true
    ] = None
    """The schema's human-readable name."""

    description: Annotated[str | None, Mutability.read_only, Returned.default] = None
    """The schema's human-readable description."""

    attributes: Annotated[
        list[Attribute] | None, Mutability.read_only, Required.true
    ] = None
    """A complex type that defines service provider attributes and their
    qualities via the following set of sub-attributes."""

    @field_validator("id")
    @classmethod
    def urn_id(cls, value: str) -> str:
        """Ensure that schema ids are URI, as defined in RFC7643 §7."""
        return str(Url(value))

    def get_attribute(self, attribute_name: str) -> Attribute | None:
        """Find an attribute by its name."""
        for attribute in self.attributes or []:
            if attribute.name == attribute_name:
                return attribute
        return None

    def __getitem__(self, name: str) -> "Attribute":
        """Find an attribute by its name."""
        if attribute := self.get_attribute(name):
            return attribute
        raise KeyError(f"This schema has no '{name}' attribute")
