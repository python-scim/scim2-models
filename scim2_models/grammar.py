import json
from functools import lru_cache
from math import isfinite
from typing import Any
from typing import cast

from lark import Lark
from lark import Token
from lark import Transformer
from lark import v_args
from lark.exceptions import LarkError
from lark.exceptions import VisitError

from .exceptions import InvalidFilterException
from .exceptions import InvalidPathException
from .expressions import AttrPath
from .expressions import CompareOperator
from .expressions import Comparison
from .expressions import FilterNode
from .expressions import LogicalExpr
from .expressions import LogicalOperator
from .expressions import Not
from .expressions import PathNode
from .expressions import Present
from .expressions import ValuePath

_GRAMMAR = r"""
// ---- FILTER, RFC 7644 §3.4.2.2 with errata 4670 and 7322 applied
?filter: or_expr
?or_expr: and_expr (_OR and_expr)+    -> or_expr
        | and_expr
?and_expr: not_expr (_AND not_expr)+  -> and_expr
         | not_expr
// The published ABNF reads *1"not" "(" FILTER ")" with no space, so not(...)
// parses; errata 7319 would require one and is not applied.
?not_expr: _NOT _LPAR filter _RPAR    -> not_expr
         | primary
?primary: _LPAR filter _RPAR
        | value_path
        | attr_exp

// ---- PATH, RFC 7644 §3.5.2 with errata 7122 applied
?path: ATTR_PATH        -> path_attr
     | value_path_sub
     | attr_exp

// A valuePath only carries a sub-attribute in a PATCH path, never in a filter,
// where it has to stand as a boolean expression of its own.
value_path_sub: ATTR_PATH _LBRACKET val_filter _RBRACKET [_DOT SUB_ATTR]
value_path: ATTR_PATH _LBRACKET val_filter _RBRACKET

// valFilter is FILTER minus valuePath: full boolean expressions are allowed
// inside the brackets, nested value selections are not (errata 4690 and 7322).
?val_filter: val_or
?val_or: val_and (_OR val_and)+       -> or_expr
       | val_and
?val_and: val_not (_AND val_not)+     -> and_expr
        | val_not
?val_not: _NOT _LPAR val_filter _RPAR -> not_expr
        | val_primary
?val_primary: _LPAR val_filter _RPAR
            | attr_exp

attr_exp: ATTR_PATH PR                    -> present_exp
        | ATTR_PATH COMPARE_OP comp_value -> compare_exp

?comp_value: STRING -> string_value
           | NUMBER -> number_value
           | TRUE   -> true_value
           | FALSE  -> false_value
           | NULL   -> null_value

// The whole attrPath is a single token: splitting the URN from the attribute
// name is unambiguous once the full string is known, whereas letting the lexer
// decide where the URN ends requires a lookahead that LALR cannot backtrack.
// A single sub-attribute, since the ABNF reads "*1subAttr" and SCIM has no
// nested complex attributes (errata 8415 of RFC 7643).
// Case-insensitive, since a URN namespace identifier is (RFC 8141 section 2).
ATTR_PATH: /(?:urn:[A-Za-z0-9][A-Za-z0-9._-]*(?::[A-Za-z0-9][A-Za-z0-9._-]*)*:)?\$?[A-Za-z][A-Za-z0-9_-]*(?:\.\$?[A-Za-z][A-Za-z0-9_-]*)?/i
SUB_ATTR: /\$?[A-Za-z][A-Za-z0-9_-]*/

// Trailing word boundaries are mandatory: without them an attribute named
// "never" lexes as the "ne" operator followed by "ver".
COMPARE_OP.2: /(?:eq|ne|co|sw|ew|gt|lt|ge|le)(?![A-Za-z0-9_-])/i
PR.2: /pr(?![A-Za-z0-9_-])/i
TRUE.2: /true(?![A-Za-z0-9_-])/i
FALSE.2: /false(?![A-Za-z0-9_-])/i
NULL.2: /null(?![A-Za-z0-9_-])/i
_AND.3: /and(?![A-Za-z0-9_-])/i
_OR.3: /or(?![A-Za-z0-9_-])/i
_NOT.3: /not(?![A-Za-z0-9_-])/i

// Both literals follow the JSON rules the ABNF refers to, escapes included, so
// that an invalid one is a syntax error located by the lexer rather than a
// failure raised later while decoding the token.
STRING: /"(?:[^"\\\x00-\x1F]|\\["\\\/bfnrt]|\\u[0-9A-Fa-f]{4})*"/
NUMBER: /-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?/

_LPAR: "("
_RPAR: ")"
_LBRACKET: "["
_RBRACKET: "]"
_DOT: "."

%ignore /[ \t\f\r\n]+/
"""


def _split_attr_path(raw: str) -> AttrPath:
    """Split a raw ``attrPath`` token into its URN, attribute and sub-attribute.

    The URN, when present, is everything up to the last colon.
    """
    uri: str | None = None
    remainder = raw

    if raw.lower().startswith("urn:"):
        uri, _, remainder = raw.rpartition(":")

    attr, _, sub_attr = remainder.partition(".")
    return AttrPath(attr=attr, sub_attr=sub_attr or None, uri=uri)


@v_args(inline=True)
class _AstBuilder(Transformer[Token, Any]):
    """Turn a lark parse tree into the nodes of :mod:`scim2_models.expressions`."""

    def or_expr(self, *terms: FilterNode) -> FilterNode:
        return LogicalExpr(op=LogicalOperator.or_, terms=terms)

    def and_expr(self, *terms: FilterNode) -> FilterNode:
        return LogicalExpr(op=LogicalOperator.and_, terms=terms)

    def not_expr(self, expr: FilterNode) -> FilterNode:
        return Not(expr=expr)

    def value_path(self, attr_path: Token, val_filter: FilterNode) -> FilterNode:
        return ValuePath(
            attr_path=_split_attr_path(str(attr_path)), val_filter=val_filter
        )

    def value_path_sub(
        self, attr_path: Token, val_filter: FilterNode, sub_attr: Token | None = None
    ) -> FilterNode:
        return ValuePath(
            attr_path=_split_attr_path(str(attr_path)),
            val_filter=val_filter,
            sub_attr=str(sub_attr) if sub_attr is not None else None,
        )

    def compare_exp(self, attr_path: Token, op: Token, value: Any) -> FilterNode:
        return Comparison(
            attr_path=_split_attr_path(str(attr_path)),
            op=CompareOperator(str(op).lower()),
            value=value,
        )

    def present_exp(self, attr_path: Token, _pr: Token) -> FilterNode:
        return Present(attr_path=_split_attr_path(str(attr_path)))

    def path_attr(self, attr_path: Token) -> AttrPath:
        return _split_attr_path(str(attr_path))

    def string_value(self, token: Token) -> str:
        return cast(str, json.loads(str(token)))

    def number_value(self, token: Token) -> int | float:
        raw = str(token)
        if not {".", "e", "E"} & set(raw):
            return int(raw)

        value = float(raw)
        if not isfinite(value):
            # An out of range literal would render back as ``Infinity``, which
            # the ABNF has no syntax for, so the filter could not be re-parsed.
            raise ValueError(f"number out of range: {raw}")
        return value

    def true_value(self, _token: Token) -> bool:
        return True

    def false_value(self, _token: Token) -> bool:
        return False

    def null_value(self, _token: Token) -> None:
        return None


# One parser for both entry points: the two start rules share a grammar, and
# building their tables together halves the cost of importing this module.
_PARSER = Lark(_GRAMMAR, start=["filter", "path"], parser="lalr")
_BUILDER = _AstBuilder()


@lru_cache(maxsize=1024)
def parse_filter(expression: str) -> FilterNode:
    """Parse a SCIM filter expression into an abstract syntax tree.

    :param expression: The filter expression, as found in a ``filter`` query
        parameter or in :attr:`~scim2_models.SearchRequest.filter`.
    :returns: The root node of the parsed expression.
    :raises InvalidFilterException: If the expression is syntactically invalid.

    >>> from scim2_models.filters import parse_filter
    >>> parse_filter('userName eq "bjensen"')
    Comparison(attr_path=AttrPath(attr='userName', sub_attr=None, uri=None), op=<CompareOperator.eq: 'eq'>, value='bjensen')
    """
    try:
        tree = _PARSER.parse(expression, start="filter")
        return cast(FilterNode, _BUILDER.transform(tree))
    except LarkError as exc:
        raise InvalidFilterException(
            filter=expression, detail=_error_detail(exc)
        ) from exc


@lru_cache(maxsize=1024)
def parse_path(path: str) -> PathNode:
    """Parse a SCIM PATCH path into an abstract syntax tree.

    :param path: The path, as found in :attr:`~scim2_models.PatchOperation.path`.
    :returns: The parsed path.
    :raises InvalidPathException: If the path is syntactically invalid.

    >>> from scim2_models.filters import parse_path
    >>> parse_path("name.familyName")
    AttrPath(attr='name', sub_attr='familyName', uri=None)
    """
    try:
        tree = _PARSER.parse(path, start="path")
        return cast(PathNode, _BUILDER.transform(tree))
    except LarkError as exc:
        raise InvalidPathException(path=path, detail=_error_detail(exc)) from exc


def _error_detail(exc: LarkError) -> str:
    """Build a human readable message out of a lark failure."""
    if isinstance(exc, VisitError):
        return str(exc.orig_exc)

    column = getattr(exc, "column", None)
    if column is None:
        return "invalid syntax"
    return f"invalid syntax at column {column}"
