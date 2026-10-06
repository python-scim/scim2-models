import re
from collections.abc import Iterable
from enum import StrEnum
from inspect import isclass
from typing import Any
from typing import Generic

from pydantic import field_validator

from ..annotations import Mutability
from ..base import BaseModel
from ..exceptions import InvalidCursorException
from ..exceptions import InvalidFilterException
from ..exceptions import InvalidPathException
from ..path import Path
from ..path import ScimFilter
from ..path.expressions import AttrPath
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
    if binding.is_multivalued:
        # "resources are sorted by the value of the primary attribute, if any,
        # or else the first value in the list, if any."
        entries = value or []
        value = next(
            (entry for entry in entries if getattr(entry, "primary", None)),
            entries[0] if entries else None,
        )

    if value is not None and binding.sub_field_name is not None:
        value = getattr(value, binding.sub_field_name, None)
    # "String type attributes are case insensitive by default, unless the
    # attribute type is defined as a case-exact string", RFC7644 §3.4.2.3.
    # A string the policy cannot prepare sorts as a missing value.
    try:
        return binding.comparable(value)
    except ValueError:
        return None


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

        reasons = [
            _unsortable_reason(str(value), binding)
            for model in value.models
            if (binding := value.resolve(model))
        ]
        if None in reasons:
            return value

        raise InvalidPathException(
            path=str(value), detail=reasons[0]
        ).as_pydantic_error()

    class SortOrder(StrEnum):
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

    cursor: str | None = None
    """A string value that can be used to retrieve the next page of results.
    The cursor value is defined in :rfc:`RFC9865 §2 <9865#section-2>`."""

    @field_validator("cursor")
    @classmethod
    def validate_cursor_chars(cls, value: str | None) -> str | None:
        """According to :rfc:`RFC9865 §2 <9865#section-2>`, cursor values may only contain unreserved characters as defined in :rfc:`RFC3986 §2.3 <3986#section-2.3>`.

        unreserved = ALPHA / DIGIT / "-" / "." / "_" / "~"
        """
        if value is not None and not re.fullmatch(r"[A-Za-z0-9\-._~]*", value):
            raise InvalidCursorException().as_pydantic_error()
        return value

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

    def sort_binding(self, model: type[BaseModel]) -> AttributeBinding | None:
        """Bind :attr:`sort_by` to the attribute of a model that orders the results.

        This is what :meth:`sort` orders by, for backends that sort on their own.
        A multi-valued complex attribute is bound to its ``value``
        sub-attribute, so ``emails`` binds as ``emails.value``, per
        :rfc:`RFC7644 §3.4.2.3 <7644#section-3.4.2.3>`.

        >>> from scim2_models import SearchRequest, User
        >>> binding = SearchRequest(sort_by="emails").sort_binding(User)
        >>> binding.field_name, binding.sub_field_name
        ('emails', 'value')

        :param model: The resource type to resolve against.
        :returns: The attribute to sort on, or :data:`None` when :attr:`sort_by`
            is not set, when the model does not declare the attribute, or when
            the model cannot sort on it.
        """
        if self.sort_by is None:
            return None

        binding = self.sort_by.resolve(model)
        if binding is None or _unsortable_reason(str(self.sort_by), binding):
            return None

        target = binding.target_type
        if not (isclass(target) and issubclass(target, BaseModel)):
            return binding

        designated = self.sort_by._designated_attr_path()
        assert designated is not None
        value_path = AttrPath(designated.attr, "value", designated.uri)
        return _resolve_attr_path(model, value_path, strict=False)

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

        bindings: dict[type, AttributeBinding | None] = {}

        def key(resource: ResourceT) -> tuple[bool, Any]:
            model = type(resource)
            if model not in bindings:
                # "For filtered attributes that are not part of a particular
                # resource type, the service provider SHALL treat the attribute
                # as if there is no attribute value", RFC7644 §3.4.2.1.
                bindings[model] = self.sort_binding(model)
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
        """The 0 indexed start index.

        Without :attr:`start_index`, it is 0, as :rfc:`RFC7644 §3.4.2.4
        <7644#section-3.4.2.4>` defaults ``startIndex`` to 1. It is :data:`None`
        when a :attr:`cursor` paginates the results instead.
        """
        if self.cursor is not None:
            return None
        return (self.start_index or 1) - 1

    @property
    def stop_index_0(self) -> int | None:
        """The 0 indexed stop index, so ``results[start_index_0:stop_index_0]`` is the page.

        It is :data:`None` when :attr:`count` is not set, or when a
        :attr:`cursor` paginates the results instead.
        """
        if self.start_index_0 is None or self.count is None:
            return None
        return self.start_index_0 + self.count
