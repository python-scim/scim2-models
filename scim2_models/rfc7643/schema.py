import re
from datetime import datetime
from enum import Enum
from typing import Annotated
from typing import Any
from typing import List  # noqa : UP005,UP035
from typing import Literal
from typing import Optional
from typing import Union
from typing import get_origin

from pydantic import Field
from pydantic import create_model
from pydantic import field_validator
from pydantic.alias_generators import to_pascal
from pydantic.alias_generators import to_snake
from pydantic_core import Url

from ..base import BaseModel
from ..base import CaseExact
from ..base import ComplexAttribute
from ..base import ExternalReference
from ..base import MultiValuedComplexAttribute
from ..base import Mutability
from ..base import Reference
from ..base import Required
from ..base import Returned
from ..base import Uniqueness
from ..base import URIReference
from ..base import is_complex_attribute
from ..constants import RESERVED_WORDS
from ..utils import Base64Bytes
from ..utils import normalize_attribute_name
from .resource import Extension
from .resource import Resource


def make_python_identifier(identifier: str) -> str:
    """Sanitize string to be a suitable Python/Pydantic class attribute name."""
    sanitized = re.sub(r"\W|^(?=\d)", "", identifier)
    if sanitized in RESERVED_WORDS:
        sanitized = f"{sanitized}_"

    return sanitized


def make_python_model(
    obj: Union["Schema", "Attribute"],
    base: Optional[type[BaseModel]] = None,
    multiple=False,
) -> Union[Resource, Extension]:
    """Build a Python model from a Schema or an Attribute object."""
    if isinstance(obj, Attribute):
        pydantic_attributes = {
            to_snake(make_python_identifier(attr.name)): attr.to_python()
            for attr in (obj.sub_attributes or [])
            if attr.name
        }
        base = MultiValuedComplexAttribute if multiple else ComplexAttribute

    else:
        pydantic_attributes = {
            to_snake(make_python_identifier(attr.name)): attr.to_python()
            for attr in (obj.attributes or [])
            if attr.name
        }
        pydantic_attributes["schemas"] = (
            Annotated[list[str], Required.true],
            Field(default=[obj.id]),
        )

    model_name = to_pascal(to_snake(obj.name))
    model = create_model(model_name, __base__=base, **pydantic_attributes)

    # Set the ComplexType class as a member of the model
    # e.g. make Member an attribute of Group
    for attr_name in model.model_fields:
        attr_type = model.get_field_root_type(attr_name)
        if is_complex_attribute(attr_type):
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

        def to_python(
            self,
            multiple=False,
            reference_types: Optional[list[str]] = None,
        ) -> type:
            if self.value == self.reference and reference_types is not None:
                if reference_types == ["external"]:
                    return Reference[ExternalReference]

                if reference_types == ["uri"]:
                    return Reference[URIReference]

                types = tuple(Literal[t] for t in reference_types)
                return Reference[Union[types]]  # type: ignore

            attr_types = {
                self.string: str,
                self.boolean: bool,
                self.decimal: float,
                self.integer: int,
                self.date_time: datetime,
                self.binary: Base64Bytes,
                self.complex: MultiValuedComplexAttribute
                if multiple
                else ComplexAttribute,
            }
            return attr_types[self.value]

        @classmethod
        def from_python(cls, pytype) -> str:
            if get_origin(pytype) == Reference:
                return cls.reference.value

            if is_complex_attribute(pytype):
                return cls.complex.value

            if pytype in (Required, CaseExact):
                return cls.boolean.value

            attr_types = {
                str: cls.string.value,
                bool: cls.boolean.value,
                float: cls.decimal.value,
                int: cls.integer.value,
                datetime: cls.date_time.value,
                Base64Bytes: cls.binary.value,
            }
            return attr_types.get(pytype, cls.string.value)

    name: Annotated[
        Optional[str], Mutability.read_only, Required.true, CaseExact.true
    ] = None
    """The attribute's name."""

    type: Annotated[Type, Mutability.read_only, Required.true] = Field(
        None, examples=[item.value for item in Type]
    )
    """The attribute's data type."""

    multi_valued: Annotated[Optional[bool], Mutability.read_only, Required.true] = None
    """A Boolean value indicating the attribute's plurality."""

    description: Annotated[
        Optional[str], Mutability.read_only, Required.false, CaseExact.true
    ] = None
    """The attribute's human-readable description."""

    required: Annotated[Required, Mutability.read_only, Required.false] = Required.false
    """A Boolean value that specifies whether or not the attribute is
    required."""

    canonical_values: Annotated[
        Optional[list[str]], Mutability.read_only, CaseExact.true
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
        Optional[list[str]], Mutability.read_only, Required.false, CaseExact.true
    ] = None
    """A multi-valued array of JSON strings that indicate the SCIM resource
    types that may be referenced."""

    # for python 3.9 and 3.10 compatibility, this should be 'list' and not 'List'
    sub_attributes: Annotated[Optional[List["Attribute"]], Mutability.read_only] = None  # noqa: UP006
    """When an attribute is of type "complex", "subAttributes" defines a set of
    sub-attributes."""

    def to_python(self) -> Optional[tuple[Any, Field]]:
        """Build tuple suited to be passed to pydantic 'create_model'."""
        if not self.name:
            return None

        attr_type = self.type.to_python(self.multi_valued, self.reference_types)

        if attr_type in (ComplexAttribute, MultiValuedComplexAttribute):
            attr_type = make_python_model(obj=self, multiple=self.multi_valued)

        if self.multi_valued:
            attr_type = list[attr_type]  # type: ignore

        annotation = Annotated[
            Optional[attr_type],  # type: ignore
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
            validation_alias=normalize_attribute_name(self.name),
            default=None,
        )

        return annotation, field

    def get_attribute(self, attribute_name: str) -> Optional["Attribute"]:
        """Find an attribute by its name."""
        for sub_attribute in self.sub_attributes or []:
            if sub_attribute.name == attribute_name:
                return sub_attribute
        return None

    def __getitem__(self, name):
        """Find an attribute by its name."""
        if attribute := self.get_attribute(name):
            return attribute
        raise KeyError(f"This attribute has no '{name}' sub-attribute")


class Schema(Resource):
    schemas: Annotated[list[str], Required.true] = [
        "urn:ietf:params:scim:schemas:core:2.0:Schema"
    ]

    id: Annotated[Optional[str], Mutability.read_only, Required.true] = None
    """The unique URI of the schema."""

    name: Annotated[
        Optional[str], Mutability.read_only, Returned.default, Required.true
    ] = None
    """The schema's human-readable name."""

    description: Annotated[Optional[str], Mutability.read_only, Returned.default] = None
    """The schema's human-readable description."""

    attributes: Annotated[
        Optional[list[Attribute]], Mutability.read_only, Required.true
    ] = None
    """A complex type that defines service provider attributes and their
    qualities via the following set of sub-attributes."""

    @field_validator("id")
    @classmethod
    def urn_id(cls, value: str) -> str:
        """Ensure that schema ids are URI, as defined in RFC7643 §7."""
        return str(Url(value))

    def get_attribute(self, attribute_name: str) -> Optional[Attribute]:
        """Find an attribute by its name."""
        for attribute in self.attributes or []:
            if attribute.name == attribute_name:
                return attribute
        return None

    def __getitem__(self, name):
        """Find an attribute by its name."""
        if attribute := self.get_attribute(name):
            return attribute
        raise KeyError(f"This schema has no '{name}' attribute")
