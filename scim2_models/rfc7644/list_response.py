from typing import Generic
from typing import List
from typing import Optional
from typing import Union

from pydantic import Field

from ..base import BaseModel
from ..rfc7643.resource import AnyResource
from ..rfc7643.resource import tagged_resource_union


class ListResponse(BaseModel, Generic[AnyResource]):
    @classmethod
    def of(cls, *resource_types: AnyResource):
        """Build a ListResponse instance that can handle resource_types."""

        return cls[tagged_resource_union(Union[resource_types])]

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
