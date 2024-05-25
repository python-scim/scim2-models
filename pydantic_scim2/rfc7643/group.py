from typing import List
from typing import Optional

from pydantic import AnyUrl
from pydantic import ConfigDict
from pydantic import Field

from ..base import SCIM2Model
from .resource import Resource


class GroupMember(SCIM2Model):
    model_config = ConfigDict(populate_by_name=True)

    value: Optional[str] = None
    display: Optional[str] = None
    ref: Optional[AnyUrl] = Field(None, alias="$ref")
    """The reference URI of a target resource, if the attribute is a
    reference."""


class Group(Resource):
    schemas: List[str] = ["urn:ietf:params:scim:schemas:core:2.0:Group"]
    display_name: str
    """A human-readable name for the Group."""

    members: Optional[List[GroupMember]] = None
    """A list of members of the Group."""
