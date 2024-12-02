from typing import Annotated
from typing import Literal
from typing import Optional
from typing import Union

from pydantic import Field

from ..base import MultiValuedComplexAttribute
from ..base import Mutability
from ..base import Reference
from ..base import Required
from .resource import Resource


class GroupMember(MultiValuedComplexAttribute):
    value: Annotated[Optional[str], Mutability.immutable] = None
    """Identifier of the member of this Group."""

    ref: Annotated[
        Optional[Reference[Union[Literal["User"], Literal["Group"]]]],
        Mutability.immutable,
    ] = Field(None, serialization_alias="$ref")
    """The reference URI of a target resource, if the attribute is a
    reference."""

    type: Annotated[Optional[str], Mutability.immutable] = Field(
        None, examples=["User", "Group"]
    )
    """A label indicating the attribute's function, e.g., "work" or "home"."""

    display: Annotated[Optional[str], Mutability.read_only] = None


class Group(Resource):
    schemas: Annotated[list[str], Required.true] = [
        "urn:ietf:params:scim:schemas:core:2.0:Group"
    ]

    display_name: Optional[str] = None
    """A human-readable name for the Group."""

    members: Optional[list[GroupMember]] = None
    """A list of members of the Group."""
