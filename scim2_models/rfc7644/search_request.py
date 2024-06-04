from enum import Enum
from typing import List
from typing import Optional

from .message import Message


class SortOrder(str, Enum):
    ascending = "ascending"
    descending = "descending"


class SearchRequest(Message):
    """SearchRequest object defined at https://datatracker.ietf.org/doc/html/rfc7644#section-3.4.3"""

    schemas: List[str] = ["urn:ietf:params:scim:api:messages:2.0:SearchRequest"]

    attributes: Optional[List[str]] = None
    """A multi-valued list of strings indicating the names of resource
    attributes to return in the response, overriding the set of attributes that
    would be returned by default."""

    excluded_attributes: Optional[List[str]] = None
    """A multi-valued list of strings indicating the names of resource
    attributes to be removed from the default set of attributes to return."""

    filter: Optional[str] = None
    """The filter string used to request a subset of resources."""

    sort_by: Optional[str] = None
    """A string indicating the attribute whose value SHALL be used to order the
    returned responses."""

    sort_order: Optional[SortOrder] = None
    """A string indicating the order in which the "sortBy" parameter is
    applied."""

    start_index: Optional[int] = None
    """An integer indicating the 1-based index of the first query result."""

    count: Optional[int] = None
    """An integer indicating the desired maximum number of query results per
    page."""
