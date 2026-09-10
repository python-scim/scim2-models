"""The syntax tree that filters and paths are parsed into, and rendered back from."""

import json
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from enum import Enum
from typing import Any
from typing import Union

if sys.version_info >= (3, 14):
    from string.templatelib import Template as Template
else:  # pragma: no cover
    Template = None

_ATTR_NAME = r"\$?[A-Za-z][A-Za-z0-9_-]*"
"""The ``ATTRNAME`` rule, with the leading ``$`` of ``$ref`` that errata 8924 adds."""

_URN = r"urn:[A-Za-z0-9][A-Za-z0-9._-]*(?::[A-Za-z0-9][A-Za-z0-9._-]*)*"
"""A schema URN, the only ``URI`` an attribute path accepts."""

_ATTR_NAME_RE = re.compile(_ATTR_NAME)
_URN_RE = re.compile(_URN, re.IGNORECASE)


class _Expression(str):
    """A filter or a path, kept as the string it was built from.

    Its syntax was checked when it was created, so it can only contribute
    syntax. Interpolated in a t-string, it is inserted as it stands where any
    other value is quoted.
    """


class CompareOperator(str, Enum):
    """The comparison operators defined at :rfc:`RFC7644 §3.4.2.2 <7644#section-3.4.2.2>`."""

    eq = "eq"
    """Equal."""

    ne = "ne"
    """Not equal."""

    co = "co"
    """Contains."""

    sw = "sw"
    """Starts with."""

    ew = "ew"
    """Ends with."""

    gt = "gt"
    """Greater than."""

    ge = "ge"
    """Greater than or equal to."""

    lt = "lt"
    """Less than."""

    le = "le"
    """Less than or equal to."""


ORDERING_OPERATORS = frozenset(
    {
        CompareOperator.gt,
        CompareOperator.ge,
        CompareOperator.lt,
        CompareOperator.le,
    }
)
"""Operators that impose an ordering, and are thus invalid on boolean and
binary attributes per :rfc:`RFC7644 §3.4.2.2 <7644#section-3.4.2.2>`."""

STRING_OPERATORS = frozenset(
    {CompareOperator.co, CompareOperator.sw, CompareOperator.ew}
)
"""Operators that require a string operand."""


class LogicalOperator(str, Enum):
    """The logical operators defined at :rfc:`RFC7644 §3.4.2.2 <7644#section-3.4.2.2>`."""

    and_ = "and"
    """Conjunction."""

    or_ = "or"
    """Disjunction."""


def _json_default(value: Any) -> str:
    """Render a dateTime, the one value a filter compares that JSON has no syntax for."""
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"{type(value).__name__} is not a value a filter can carry")


def _quote(value: Any) -> str:
    """Render a comparison value using the JSON syntax mandated by the ABNF.

    A :class:`~datetime.datetime` renders as the string
    :rfc:`RFC7643 §2.3.5 <7643#section-2.3.5>` gives a dateTime.

    :raises ValueError: If the value is a float that JSON cannot express, such
        as an infinity, which would render as a literal no parser accepts.
    :raises TypeError: If the value is of a type no filter can carry.
    """
    return json.dumps(value, allow_nan=False, default=_json_default)


_CONVERSIONS: dict[str, Callable[[Any], str]] = {"a": ascii, "r": repr, "s": str}


def _render_template(template: "Template") -> str:
    """Render a t-string into filter syntax, quoting every interpolated value.

    A conversion or a format specification applies first, as in an f-string,
    and what it yields is a string. A value interpolated as it stands keeps its
    type, so ``{True}`` renders as ``true`` and ``{18}`` as ``18``.

    An :class:`_Expression`, a filter or a path, is syntax rather than a value
    and is inserted unquoted. A conversion or a format specification turns it
    into a value like any other.
    """
    parts: list[str] = []
    for part in template:
        if isinstance(part, str):
            parts.append(part)
            continue
        value = part.value
        if part.conversion is not None:
            value = _CONVERSIONS[part.conversion](value)
        if part.format_spec:
            value = format(value, part.format_spec)
        if isinstance(value, _Expression):
            parts.append(str(value))
            continue
        parts.append(_quote(value))
    return "".join(parts)


def _text(expression: Any) -> str:
    """Return the text of an expression, a t-string rendered with its values quoted."""
    if Template is not None and isinstance(expression, Template):
        return _render_template(expression)
    return str(expression)


@dataclass(frozen=True, slots=True)
class AttrPath:
    """An attribute path as defined by the ``attrPath`` ABNF rule.

    ``attrPath = [URI ":"] ATTRNAME *1subAttr``

    The names and the URN are checked as they are given, so a node built by
    hand carries nothing the grammar would not read.

    :raises ValueError: If a name is not an ``ATTRNAME``, or the URI not a URN.
    """

    attr: str
    """The attribute name, e.g. ``emails``."""

    sub_attr: str | None = None
    """The sub-attribute name, e.g. ``type`` in ``emails.type``."""

    uri: str | None = None
    """The schema URN the attribute belongs to, when explicitly qualified."""

    def __post_init__(self) -> None:
        for name in (self.attr, self.sub_attr):
            if name is not None and not _ATTR_NAME_RE.fullmatch(name):
                raise ValueError(f"{name!r} is not an attribute name")
        if self.uri is not None and not _URN_RE.fullmatch(self.uri):
            raise ValueError(f"{self.uri!r} is not a schema URN")

    def __str__(self) -> str:
        prefix = f"{self.uri}:" if self.uri else ""
        suffix = f".{self.sub_attr}" if self.sub_attr else ""
        return f"{prefix}{self.attr}{suffix}"


@dataclass(frozen=True, slots=True)
class FilterNode:
    """Base class for every filter expression node.

    Nodes compose with the Python boolean operators, which is how a filter is
    built without going through a string::

        >>> from scim2_models.path import AttrPath, Comparison, CompareOperator, Present

        >>> work = Comparison(AttrPath("type"), CompareOperator.eq, "work")
        >>> primary = Present(AttrPath("primary"))
        >>> str(work & primary)
        'type eq "work" and primary pr'
        >>> str(~work)
        'not (type eq "work")'
    """

    def __str__(self) -> str:
        raise NotImplementedError

    def _combine(self, other: "FilterNode", op: "LogicalOperator") -> "FilterNode":
        """Join two expressions, flattening a chain of the same operator."""
        terms: tuple[FilterNode, ...] = ()
        for node in (self, other):
            if isinstance(node, LogicalExpr) and node.op == op:
                terms += node.terms
            else:
                terms += (node,)
        return LogicalExpr(op=op, terms=terms)

    def __and__(self, other: "FilterNode") -> "FilterNode":
        return self._combine(other, LogicalOperator.and_)

    def __or__(self, other: "FilterNode") -> "FilterNode":
        return self._combine(other, LogicalOperator.or_)

    def __invert__(self) -> "FilterNode":
        return Not(expr=self)


@dataclass(frozen=True, slots=True)
class Comparison(FilterNode):
    """A comparison between an attribute and a value, e.g. ``userName eq "bjensen"``."""

    attr_path: AttrPath
    """The compared attribute."""

    op: CompareOperator
    """The comparison operator."""

    value: Any
    """The raw comparison value, as read from the filter string."""

    def __str__(self) -> str:
        return f"{self.attr_path} {self.op.value} {_quote(self.value)}"


@dataclass(frozen=True, slots=True)
class Present(FilterNode):
    """A presence test, e.g. ``title pr``."""

    attr_path: AttrPath
    """The tested attribute."""

    def __str__(self) -> str:
        return f"{self.attr_path} pr"


@dataclass(frozen=True, slots=True)
class Not(FilterNode):
    """A negated expression, e.g. ``not (title pr)``."""

    expr: FilterNode
    """The negated expression."""

    def __str__(self) -> str:
        return f"not ({self.expr})"


@dataclass(frozen=True, slots=True)
class LogicalExpr(FilterNode):
    """A conjunction or disjunction of two or more expressions.

    Chained operators are flattened, so ``a eq 1 and b eq 2 and c eq 3``
    yields a single node holding three terms.
    """

    op: LogicalOperator
    """The logical operator joining the terms."""

    terms: tuple[FilterNode, ...] = field(default_factory=tuple)
    """The joined expressions, in source order."""

    def __str__(self) -> str:
        separator = f" {self.op.value} "
        return separator.join(
            f"({term})" if _needs_parentheses(self, term) else str(term)
            for term in self.terms
        )


@dataclass(frozen=True, slots=True)
class ValuePath(FilterNode):
    """A value selection on a multi-valued attribute, e.g. ``emails[type eq "work"]``.

    ``sub_attr`` is only ever set when the node comes from a PATCH path, since
    :rfc:`RFC7644 §3.5.2 <7644#section-3.5.2>` allows ``valuePath [subAttr]``
    where a filter does not.
    """

    attr_path: AttrPath
    """The multi-valued attribute being selected into."""

    val_filter: FilterNode
    """The filter selecting the matching values."""

    sub_attr: str | None = None
    """The sub-attribute targeted past the selection, in a PATCH path."""

    def __str__(self) -> str:
        suffix = f".{self.sub_attr}" if self.sub_attr else ""
        return f"{self.attr_path}[{self.val_filter}]{suffix}"


def _needs_parentheses(parent: LogicalExpr, child: FilterNode) -> bool:
    """Whether a child expression must be parenthesised inside its parent.

    Only a disjunction nested in a conjunction needs them, since ``and`` binds
    tighter than ``or`` in the operator precedence of :rfc:`RFC7644 §3.4.2.2
    <7644#section-3.4.2.2>`.
    """
    return (
        isinstance(child, LogicalExpr)
        and child.op == LogicalOperator.or_
        and parent.op == LogicalOperator.and_
    )


PathNode = Union[AttrPath, ValuePath, Comparison, Present]  # noqa: UP007
"""A parsed PATCH path, per the ``PATH`` rule of :rfc:`RFC7644 §3.5.2 <7644#section-3.5.2>`
as corrected by errata 7122: ``PATH = attrPath / valuePath [subAttr] / attrExp``."""
