from typing import List
from typing import Optional

from pydantic import AnyUrl
from pydantic import Field

from ..base import SCIM2Model
from .resource import Resource


class GroupMember(SCIM2Model):
    value: Optional[str] = None

    display: Optional[str] = None

    type: Optional[str] = None
    """A label indicating the attribute's function, e.g., "work" or "home"."""

    ref: Optional[AnyUrl] = Field(None, alias="$ref")
    """The reference URI of a target resource, if the attribute is a
    reference."""


class Group(Resource):
    schemas: List[str] = ["urn:ietf:params:scim:schemas:core:2.0:Group"]

    display_name: Optional[str] = None
    """A human-readable name for the Group."""

    members: Optional[List[GroupMember]] = None
    """A list of members of the Group."""
