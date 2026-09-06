from enum import Enum
from typing import Any
from typing import Generic

from pydantic import field_validator

from ..exceptions import InvalidPathException
from ..filters import ScimFilter
from ..path import URN
from ..path import Path
from ..path import ResourceT
from .message import Message
from .response_parameters import ResponseParameters


class SearchRequest(Message, ResponseParameters[ResourceT], Generic[ResourceT]):
    """SearchRequest object defined at :rfc:`RFC7644 §3.4.3 <7644#section-3.4.3>`.

    Parameterising the request with the resource type an endpoint serves, as in
    ``SearchRequest[User]`` for ``/Users`` and ``/Users/.search``, resolves
    :attr:`filter` and :attr:`sort_by` against that model. An endpoint covering
    several resource types, such as the server root and the ``/.search`` mounted
    on it, names them all: ``SearchRequest[User | Group]``. An attribute only
    some of them declare stays valid there, and evaluates to false on the
    resources of the others, as
    :rfc:`RFC7644 §3.4.2.1 <7644#section-3.4.2.1>` requires.
    """

    __schema__ = URN("urn:ietf:params:scim:api:messages:2.0:SearchRequest")

    filter: ScimFilter[ResourceT] | None = None
    """The filter used to request a subset of resources.

    Assigning a string parses it, so a malformed filter is rejected at
    validation time rather than by the server. On a parameterised request the
    filter is checked against the model as well, unknown attributes included,
    and is ready to be matched::

        SearchRequest[User](filter='userName eq "bjensen"').filter.match(user)

    An unparameterised request only has its syntax checked, there being no
    model to resolve attribute names against.
    """

    @field_validator("filter")
    @classmethod
    def _resolvable_filter(
        cls, value: "ScimFilter[Any] | None"
    ) -> "ScimFilter[Any] | None":
        """Reject an attribute the bound model does not declare."""
        # Parameterising the request names the resource types the endpoint
        # serves, which is what makes an attribute none of them declares a
        # client error rather than something to evaluate to false.
        if value is not None and value.models:
            value._validate_semantics()
        return value

    sort_by: Path[ResourceT] | None = None
    """A string indicating the attribute whose value SHALL be used to order the
    returned responses.

    On a parameterised request the attribute is resolved against the model, and
    one none of the resource types declares is refused. Where an unknown entry
    of :attr:`~scim2_models.ResponseParameters.attributes` is ignored, an order
    cannot be: a ``sortBy`` left out answers an arbitrary order the client has
    no way of telling from the one it asked for.
    """

    @field_validator("sort_by")
    @classmethod
    def _resolvable_sort_by(cls, value: "Path[Any] | None") -> "Path[Any] | None":
        """Reject an attribute the bound model does not declare."""
        # Parameterising the request names the resource types the endpoint
        # serves, which is what makes an attribute none of them declares a
        # client error rather than something to resolve later.
        if value is not None and value.models and value.resolve() is None:
            raise InvalidPathException(
                path=str(value), detail=f"Cannot sort on {str(value)!r}"
            )
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
