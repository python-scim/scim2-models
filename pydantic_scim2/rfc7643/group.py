from typing import Annotated
from typing import List
from typing import Optional

from pydantic import AnyUrl
from pydantic import Field

from ..base import ComplexAttribute
from ..base import Mutability
from .resource import Resource


class GroupMember(ComplexAttribute):
    _attribute_urn: str = "urn:ietf:params:scim:schemas:core:2.0:Group.members"

    value: Annotated[Optional[str], Mutability.immutable] = None
    """Identifier of the member of this Group."""

    display: Annotated[Optional[str], Mutability.immutable] = None

    type: Annotated[Optional[str], Mutability.immutable] = None
    """A label indicating the attribute's function, e.g., "work" or "home"."""

    ref: Annotated[Optional[AnyUrl], Mutability.immutable] = Field(None, alias="$ref")
    """The reference URI of a target resource, if the attribute is a
    reference."""


class Group(Resource):
    schemas: List[str] = ["urn:ietf:params:scim:schemas:core:2.0:Group"]

    display_name: Optional[str] = None
    """A human-readable name for the Group."""

    members: Optional[List[GroupMember]] = None
    """A list of members of the Group."""
