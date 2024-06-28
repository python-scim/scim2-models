import re
from datetime import datetime
from enum import Enum
from typing import Annotated
from typing import List
from typing import Optional
from typing import Tuple
from typing import Type
from typing import Union

from pydantic import Field
from pydantic import create_model
from pydantic.alias_generators import to_pascal
from pydantic.alias_generators import to_snake

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
from .resource import Resource


def make_python_identifier(identifier: str) -> str:
    """Sanitize string to be a suitable Python/Pydantic class attribute
    name."""

    sanitized = re.sub(r"\W|^(?=\d)", "", identifier)
    if sanitized in RESERVED_WORDS:
        sanitized = f"{sanitized}_"

    return sanitized


def make_python_model(obj: Union["Schema", "Attribute"], multiple=False) -> "Resource":
    """Build a Python model from a Schema or an Attribute object."""

    from scim2_models.rfc7643.resource import Resource

    if isinstance(obj, Attribute):
        pydantic_attributes = {
            to_snake(make_python_identifier(attr.name)): attr.to_python()
            for attr in obj.sub_attributes
        }
        base = MultiValuedComplexAttribute if multiple else ComplexAttribute

    else:
        pydantic_attributes = {
            to_snake(make_python_identifier(attr.name)): attr.to_python()
            for attr in obj.attributes
        }
        pydantic_attributes["schemas"] = (Optional[List[str]], Field(default=[obj.id]))
        base = Resource

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
        boolean = "boolean"
        decimal = "decimal"
        integer = "integer"
        date_time = "dateTime"
        reference = "reference"
        binary = "binary"
        complex = "complex"

        def to_python(self, multiple=False, reference_types=None) -> Type:
            if self.value == self.reference:
                if reference_types == ["external"]:
                    return Reference[ExternalReference]

                if reference_types == ["uri"]:
                    return Reference[URIReference]

                return Reference[Union[tuple(reference_types)]]

            attr_types = {
                self.string: str,
                self.boolean: bool,
                self.decimal: float,
                self.integer: int,
                self.date_time: datetime,
                self.binary: bytes,
                self.complex: MultiValuedComplexAttribute
                if multiple
                else ComplexAttribute,
            }
            return attr_types[self.value]

    name: Annotated[str, Mutability.read_only, Required.true, CaseExact.true] = None
    """The attribute's name."""

    type: Annotated[Type, Mutability.read_only, Required.true]
    """The attribute's data type."""

    multi_valued: Annotated[Optional[bool], Mutability.read_only, Required.true] = None
    """A Boolean value indicating the attribute's plurality."""

    description: Annotated[
        Optional[str], Mutability.read_only, Required.true, CaseExact.true
    ] = None
    """The attribute's human-readable description."""

    required: Annotated[Required, Mutability.read_only, Required.true] = Required.false
    """A Boolean value that specifies whether or not the attribute is
    required."""

    canonical_values: Annotated[
        Optional[List[str]], Mutability.read_only, CaseExact.true
    ] = None
    """A collection of suggested canonical values that MAY be used (e.g.,
    "work" and "home")."""

    case_exact: Annotated[CaseExact, Mutability.read_only, Required.true] = (
        CaseExact.false
    )
    """A Boolean value that specifies whether or not a string attribute is case
    sensitive."""

    mutability: Annotated[
        Mutability, Mutability.read_only, Required.true, CaseExact.true
    ] = Mutability.read_write
    """A single keyword indicating the circumstances under which the value of
    the attribute can be (re)defined."""

    returned: Annotated[
        Returned, Mutability.read_only, Required.true, CaseExact.true
    ] = Returned.default
    """A single keyword that indicates when an attribute and associated values
    are returned in response to a GET request or in response to a PUT, POST, or
    PATCH request."""

    uniqueness: Annotated[
        Uniqueness, Mutability.read_only, Required.true, CaseExact.true
    ] = Uniqueness.none
    """A single keyword value that specifies how the service provider enforces
    uniqueness of attribute values."""

    reference_types: Annotated[
        Optional[List[str]], Mutability.read_only, Required.true, CaseExact.true
    ] = None
    """A multi-valued array of JSON strings that indicate the SCIM resource
    types that may be referenced."""

    sub_attributes: Annotated[Optional[List["Attribute"]], Mutability.read_only] = None
    """When an attribute is of type "complex", "subAttributes" defines a set of
    sub-attributes."""

    def to_python(self) -> Tuple[Type, Field]:
        """Build tuple suited to be passed to pydantic 'create_model'."""

        attr_type = self.type.to_python(self.multi_valued, self.reference_types)

        if attr_type in (ComplexAttribute, MultiValuedComplexAttribute):
            attr_type = make_python_model(self, self.multi_valued)

        if self.multi_valued:
            attr_type = List[attr_type]

        return (
            Annotated[
                Optional[attr_type],
                self.required,
                self.case_exact,
                self.mutability,
                self.returned,
                self.uniqueness,
            ],
            Field(
                description=self.description,
                examples=self.canonical_values,
                alias=self.name,
                default=None,
            ),
        )


class Schema(Resource):
    schemas: List[str] = ["urn:ietf:params:scim:schemas:core:2.0:Schema"]

    id: Annotated[Optional[str], Mutability.read_only, Required.true] = None
    """The unique URI of the schema."""

    name: Annotated[Optional[str], Mutability.read_only, Returned.default] = None
    """The schema's human-readable name."""

    description: Annotated[Optional[str], Mutability.read_only, Returned.default] = None
    """The schema's human-readable description."""

    attributes: Annotated[
        Optional[List[Attribute]], Mutability.read_only, Required.true
    ] = None
    """A complex type that defines service provider attributes and their
    qualities via the following set of sub-attributes."""

    def make_model(self) -> "Resource":
        """Build a Python model from the schema definition."""

        return make_python_model(self)
