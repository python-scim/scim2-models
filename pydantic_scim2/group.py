from typing import List
from typing import Optional

from pydantic import AnyUrl
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from .resource import Resource


class GroupMember(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    value: Optional[str] = None
    display: Optional[str] = None
    ref: Optional[AnyUrl] = Field(
        None,
        alias="$ref",
        description="The URI of the SCIM resource representing the User's manager.  REQUIRED.",
    )


class Group(Resource):
    schemas: List[str] = ["urn:ietf:params:scim:schemas:core:2.0:Group"]
    displayName: str = Field(
        ..., description="A human-readable name for the Group. REQUIRED."
    )
    members: Optional[List[GroupMember]] = Field(
        None, description="A list of members of the Group."
    )
