from typing import Annotated
from typing import List
from typing import Optional

from pydantic import PlainSerializer

from ..base import SCIM2Model
from ..base import int_to_str


class Error(SCIM2Model):
    schemas: List[str] = ["urn:ietf:params:scim:api:messages:2.0:Error"]

    status: Annotated[int, PlainSerializer(int_to_str)]
    """The HTTP status code (see Section 6 of [RFC7231]) expressed as a JSON
    string."""

    scim_type: Optional[str] = None
    """A SCIM detail error keyword."""

    detail: Optional[str] = None
    """A detailed human-readable message."""
