from enum import Enum
from typing import Annotated
from typing import Optional

from pydantic import field_validator
from pydantic import model_validator

from ..base import Required
from .message import Message


class SearchRequest(Message):
    """SearchRequest object defined at RFC7644.

    https://datatracker.ietf.org/doc/html/rfc7644#section-3.4.3
    """

    schemas: Annotated[list[str], Required.true] = [
        "urn:ietf:params:scim:api:messages:2.0:SearchRequest"
    ]

    attributes: Optional[list[str]] = None
    """A multi-valued list of strings indicating the names of resource
    attributes to return in the response, overriding the set of attributes that
    would be returned by default."""

    excluded_attributes: Optional[list[str]] = None
    """A multi-valued list of strings indicating the names of resource
    attributes to be removed from the default set of attributes to return."""

    filter: Optional[str] = None
    """The filter string used to request a subset of resources."""

    sort_by: Optional[str] = None
    """A string indicating the attribute whose value SHALL be used to order the
    returned responses."""

    class SortOrder(str, Enum):
        ascending = "ascending"
        descending = "descending"

    sort_order: Optional[SortOrder] = None
    """A string indicating the order in which the "sortBy" parameter is
    applied."""

    start_index: Optional[int] = None
    """An integer indicating the 1-based index of the first query result."""

    @field_validator("start_index")
    @classmethod
    def start_index_floor(cls, value: int) -> int:
        """According to :rfc:`RFC7644 §3.4.2 <7644#section-3.4.2.4>, start_index values less than 1 are interpreted as 1.

        A value less than 1 SHALL be interpreted as 1.
        """
        return None if value is None else max(1, value)

    count: Optional[int] = None
    """An integer indicating the desired maximum number of query results per
    page."""

    @field_validator("count")
    @classmethod
    def count_floor(cls, value: int) -> int:
        """According to :rfc:`RFC7644 §3.4.2 <7644#section-3.4.2.4>, count values less than 0 are interpreted as 0.

        A negative value SHALL be interpreted as 0.
        """
        return None if value is None else max(0, value)

    @model_validator(mode="after")
    def attributes_validator(self):
        if self.attributes and self.excluded_attributes:
            raise ValueError(
                "'attributes' and 'excluded_attributes' are mutually exclusive"
            )

        return self

    @property
    def start_index_0(self):
        """The 0 indexed start index."""
        return self.start_index - 1 if self.start_index is not None else None

    @property
    def stop_index_0(self):
        """The 0 indexed stop index."""
        return (
            self.start_index_0 + self.count
            if self.start_index_0 is not None and self.count is not None
            else None
        )
