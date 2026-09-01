from enum import Enum
from typing import Any

from pydantic import field_validator

from ..filters import ScimFilter
from ..path import URN
from ..path import Path
from .message import Message
from .response_parameters import ResponseParameters


class SearchRequest(Message, ResponseParameters):
    """SearchRequest object defined at :rfc:`RFC7644 §3.4.3 <7644#section-3.4.3>`."""

    __schema__ = URN("urn:ietf:params:scim:api:messages:2.0:SearchRequest")

    filter: ScimFilter[Any] | None = None
    """The filter used to request a subset of resources.

    Assigning a string parses and validates it, so a malformed filter is
    rejected at validation time rather than by the server. Only the syntax is
    checked here: a ``/.search`` request may target several resource types at
    once, so there is no single model to resolve attribute names against. Bind
    it to one with :class:`~scim2_models.ScimFilter` to go further::

        ScimFilter[User](search_request.filter).match(user)
    """

    sort_by: Path[Any] | None = None
    """A string indicating the attribute whose value SHALL be used to order the
    returned responses."""

    class SortOrder(str, Enum):
        ascending = "ascending"
        descending = "descending"

    sort_order: SortOrder | None = None
    """A string indicating the order in which the "sortBy" parameter is
    applied."""

    start_index: int | None = None
    """An integer indicating the 1-based index of the first query result."""

    @field_validator("start_index")
    @classmethod
    def start_index_floor(cls, value: int | None) -> int | None:
        """According to :rfc:`RFC7644 §3.4.2 <7644#section-3.4.2.4>`, start_index values less than 1 are interpreted as 1.

        A value less than 1 SHALL be interpreted as 1.
        """
        return None if value is None else max(1, value)

    count: int | None = None
    """An integer indicating the desired maximum number of query results per
    page."""

    @field_validator("count")
    @classmethod
    def count_floor(cls, value: int | None) -> int | None:
        """According to :rfc:`RFC7644 §3.4.2 <7644#section-3.4.2.4>`, count values less than 0 are interpreted as 0.

        A negative value SHALL be interpreted as 0.
        """
        return None if value is None else max(0, value)

    @property
    def start_index_0(self) -> int | None:
        """The 0 indexed start index."""
        return self.start_index - 1 if self.start_index is not None else None

    @property
    def stop_index_0(self) -> int | None:
        """The 0 indexed stop index."""
        return (
            self.start_index_0 + self.count
            if self.start_index_0 is not None and self.count is not None
            else None
        )
