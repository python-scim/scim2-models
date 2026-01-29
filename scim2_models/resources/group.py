from typing import TYPE_CHECKING
from typing import Annotated
from typing import Any
from typing import ClassVar
from typing import Union

from pydantic import Field

from ..annotations import Mutability
from ..annotations import Required
from ..attributes import ComplexAttribute
from ..path import URN
from ..reference import Reference
from .resource import Resource

if TYPE_CHECKING:
    from .user import User


class GroupMember(ComplexAttribute):
    value: Annotated[str | None, Mutability.immutable] = None
    """Identifier of the member of this Group."""

    ref: Annotated[  # type: ignore[type-arg]
        Reference[Union["User", "Group"]] | None,
        Mutability.immutable,
    ] = Field(None, serialization_alias="$ref")
    """The reference URI of a target resource, if the attribute is a
    reference."""

    type: Annotated[str | None, Mutability.immutable] = Field(
        None, examples=["User", "Group"]
    )
    """A label indicating the attribute's function, e.g., "work" or "home"."""

    display: Annotated[str | None, Mutability.read_only] = None


class Group(Resource[Any]):
    __schema__ = URN("urn:ietf:params:scim:schemas:core:2.0:Group")

    display_name: Annotated[str | None, Required.true] = None
    """A human-readable name for the Group."""

    members: list[GroupMember] | None = None
    """A list of members of the Group."""

    Members: ClassVar[type[ComplexAttribute]] = GroupMember
