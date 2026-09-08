from enum import Enum
from typing import Any
from typing import Generic

from pydantic import field_validator

from ..exceptions import InvalidPathException
from ..path import Path
from ..path import ResourceT
from ..urn import URN
from .message import Message
from .response_parameters import ResponseParameters


class SearchRequest(Message, ResponseParameters[ResourceT], Generic[ResourceT]):
    """SearchRequest object defined at :rfc:`RFC7644 §3.4.3 <7644#section-3.4.3>`.

    Parameterising the request with the resource type an endpoint serves, as in
    ``SearchRequest[User]``, resolves :attr:`sort_by` and the attributes of
    :class:`~scim2_models.ResponseParameters` against that model.
    """

    __schema__ = URN("urn:ietf:params:scim:api:messages:2.0:SearchRequest")

    filter: str | None = None
    """The filter string used to request a subset of resources."""

    sort_by: Path[ResourceT] | None = None
    """A string indicating the attribute whose value SHALL be used to order the
    returned responses."""

    @field_validator("sort_by")
    @classmethod
    def _sort_by_names_an_attribute(cls, value: Any) -> Any:
        """Refuse an order over the values an attribute holds.

        :rfc:`RFC7644 §3.4.2.3 <7644#section-3.4.2.3>` requires ``sortBy`` in
        the attribute notation of §3.10.
        """
        if value is not None:
            try:
                value.check_attribute_notation()
            except InvalidPathException as exc:
                raise exc.as_pydantic_error() from exc
        return value

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
