from typing import Generic
from typing import List
from typing import Optional

from pydantic import Field

from ..base import SCIM2Model
from ..rfc7643.resource import AnyResource


class ListResponse(SCIM2Model, Generic[AnyResource]):
    schemas: List[str] = ["urn:ietf:params:scim:api:messages:2.0:ListResponse"]

    total_results: int
    """The total number of results returned by the list or query operation."""

    start_index: Optional[int] = None
    """The 1-based index of the first result in the current set of list
    results."""

    items_per_page: Optional[int] = None
    """The number of resources returned in a list response page."""

    resources: Optional[List[AnyResource]] = Field(None, alias="Resources")
    """A multi-valued list of complex objects containing the requested
    resources."""
