from collections.abc import Iterable
from enum import Enum
from inspect import isclass
from typing import Any
from typing import Generic

from pydantic import field_validator

from ..annotations import CaseExact
from ..annotations import Mutability
from ..base import BaseModel
from ..exceptions import InvalidFilterException
from ..exceptions import InvalidPathException
from ..path import Path
from ..path import ScimFilter
from ..path.path import ResourceT
from ..path.resolution import AttributeBinding
from ..path.resolution import _resolve_attr_path
from ..path.resolution import _unwrap_annotated
from ..path.resolution import attribute_host
from ..urn import URN
from .message import Message
from .response_parameters import ResponseParameters


def _unsortable_reason(path: str, binding: AttributeBinding) -> str | None:
    """Tell why an attribute cannot order a query, or None when it can."""
    mutabilities = [
        binding.model.get_field_annotation(binding.field_name, Mutability),
        binding.get_annotation(Mutability),
    ]
    sorted_type = binding.target_type
    if isclass(sorted_type) and issubclass(sorted_type, BaseModel):
        # "If the attribute is complex, the attribute name must be a path to a
        # sub-attribute", RFC7644 §3.4.2.3, except for a multi-valued attribute
        # sorted "by the value of the primary attribute": RFC7643 §2.4 holds
        # that value in a "value" sub-attribute, which ``emails`` stands for.
        if not binding.is_multivalued or "value" not in sorted_type.model_fields:
            return f"{path!r} is a complex attribute, sort on one of its sub-attributes"
        mutabilities.append(sorted_type.get_field_annotation("value", Mutability))
        sorted_type = _unwrap_annotated(sorted_type.get_field_root_type("value"))

    # RFC7644 §3.4.2.2 refuses to order binary values, which §3.4.2.3 gives no
    # sort order for.
    if isclass(sorted_type) and issubclass(sorted_type, bytes):
        return f"{path!r} is a binary attribute and cannot be sorted on"

    # An order over a write-only value tells a client about it, which RFC7643
    # §4.1.1 forbids for password "in any form". A value that is merely not
    # returned may still be queried, §7 letting it be used in a search filter.
    if Mutability.write_only in mutabilities:
        return f"{path!r} is write-only and cannot be sorted on"
    return None


def _sort_value(resource: Any, binding: AttributeBinding | None) -> Any:
    """Return the single value a resource is ordered by, or None when it has none."""
    if binding is None:
        return None

    host = attribute_host(resource, binding)
    value = getattr(host, binding.field_name, None) if host is not None else None
    sub_field_name = binding.sub_field_name
    case_exact = binding.case_exact
    if binding.is_multivalued:
        # "resources are sorted by the value of the primary attribute, if any,
        # or else the first value in the list, if any."
        entries = value or []
        value = next(
            (entry for entry in entries if getattr(entry, "primary", None)),
            entries[0] if entries else None,
        )
        if sub_field_name is None and isinstance(value, BaseModel):
            # RFC7643 §2.4 holds the significant value of a complex entry in a
            # "value" sub-attribute, where a scalar entry is the value itself.
            sub_field_name = "value"
            case_exact = (
                type(value).get_field_annotation("value", CaseExact) == CaseExact.true
            )

    if value is not None and sub_field_name is not None:
        value = getattr(value, sub_field_name, None)
    # "String type attributes are case insensitive by default, unless the
    # attribute type is defined as a case-exact string", RFC7644 §3.4.2.3.
    if isinstance(value, str) and not case_exact:
        return value.casefold()
    return value


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

    >>> from scim2_models import Context, SearchRequest, User
    >>> request = SearchRequest[User](
    ...     filter='userName eq "bjensen"',
    ...     sort_by="userName",
    ...     count=100,
    ... )
    >>> request.model_dump(scim_ctx=Context.SEARCH_REQUEST)
    {'schemas': ['urn:ietf:params:scim:api:messages:2.0:SearchRequest'], 'filter': 'userName eq "bjensen"', 'sortBy': 'userName', 'count': 100}
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
            try:
                value._validate_semantics()
            except InvalidFilterException as exc:
                raise exc.as_pydantic_error() from exc
        return value

    sort_by: Path[ResourceT] | None = None
    """A string indicating the attribute whose value SHALL be used to order the
    returned responses.

    On a parameterised request the attribute is resolved against the model, and
    one none of the resource types declares is refused. Where an unknown entry
    of :attr:`~scim2_models.ResponseParameters.attributes` is ignored, an order
    cannot be: a ``sortBy`` left out answers an arbitrary order the client has
    no way of telling from the one it asked for.

    A complex attribute is refused as well, :rfc:`RFC7644 §3.4.2.3
    <7644#section-3.4.2.3>` asking for a path to one of its sub-attributes. A
    multi-valued one holding a ``value`` sub-attribute stands for it, so
    ``emails`` sorts as ``emails.value``. A binary attribute, and a write-only
    attribute such as ``password``, are refused too. On a union, the attribute is accepted
    as long as one of the resource types can sort on it.
    """

    @field_validator("sort_by")
    @classmethod
    def _sort_by_names_an_attribute(cls, value: Any) -> Any:
        """Refuse an order over the values an attribute holds.

        RFC7644 §3.4.2.3 requires ``sortBy`` in the attribute notation of
        §3.10.
        """
        if value is not None:
            try:
                value._check_attribute_notation()
            except InvalidPathException as exc:
                raise exc.as_pydantic_error() from exc
        return value

    @field_validator("sort_by")
    @classmethod
    def _sortable_sort_by(cls, value: Any) -> Any:
        """Reject an attribute none of the bound resource types lets a client sort on."""
        # Parameterising the request names the resource types the endpoint
        # serves, which is what makes an attribute none of them declares a
        # client error rather than something to resolve later.
        if value is None or not value.models:
            return value

        if value.resolve() is None:
            raise InvalidPathException(
                path=str(value), detail=f"Cannot sort on {str(value)!r}"
            ).as_pydantic_error()

        designated = value._designated_attr_path()
        reasons = [
            _unsortable_reason(str(value), binding)
            for model in value.models
            if (binding := _resolve_attr_path(model, designated, strict=False))
        ]
        if None in reasons:
            return value

        raise InvalidPathException(
            path=str(value), detail=reasons[0]
        ).as_pydantic_error()

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
    def _start_index_floor(cls, value: int | None) -> int | None:
        """According to RFC7644 §3.4.2, start_index values less than 1 are interpreted as 1.

        A value less than 1 SHALL be interpreted as 1.
        """
        return None if value is None else max(1, value)

    count: int | None = None
    """An integer indicating the desired maximum number of query results per
    page."""

    @field_validator("count")
    @classmethod
    def _count_floor(cls, value: int | None) -> int | None:
        """According to RFC7644 §3.4.2, count values less than 0 are interpreted as 0.

        A negative value SHALL be interpreted as 0.
        """
        return None if value is None else max(0, value)

    def sort(self, resources: Iterable[ResourceT]) -> list[ResourceT]:
        """Order resources as :rfc:`RFC7644 §3.4.2.3 <7644#section-3.4.2.3>` describes.

        A string is compared without its case, unless its attribute is annotated
        :attr:`CaseExact.true <scim2_models.CaseExact.true>`. A multi-valued
        attribute is compared on its ``primary`` entry, or else its first one,
        and a complex one named alone on the ``value`` of that entry. A resource
        without a value comes last when ascending and first when descending, and
        so does a resource whose type does not declare the attribute or cannot
        sort on it. Resources comparing equal keep their order.

        The attribute is resolved against the type of each resource, so a request
        that names no resource type sorts as well as one that does.

        :param resources: The resources to order.
        :returns: The ordered resources, in their order when :attr:`sort_by` is
            not set.
        """
        if self.sort_by is None:
            return list(resources)

        sort_by = self.sort_by
        designated = sort_by._designated_attr_path()
        assert designated is not None
        bindings: dict[type, AttributeBinding | None] = {}

        def key(resource: ResourceT) -> tuple[bool, Any]:
            model = type(resource)
            if model not in bindings:
                # "For filtered attributes that are not part of a particular
                # resource type, the service provider SHALL treat the attribute
                # as if there is no attribute value", RFC7644 §3.4.2.1.
                binding = _resolve_attr_path(model, designated, strict=False)
                sortable = binding and _unsortable_reason(str(sort_by), binding) is None
                bindings[model] = binding if sortable else None
            value = _sort_value(resource, bindings[model])
            # "if there is no data for the specified sortBy value, they are
            # sorted via the sortOrder parameter, i.e., they are ordered last if
            # ascending and first if descending", which reversing the whole key
            # achieves.
            return value is None, value if value is not None else ""

        descending = self.sort_order == SearchRequest.SortOrder.descending
        return sorted(resources, key=key, reverse=descending)

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
