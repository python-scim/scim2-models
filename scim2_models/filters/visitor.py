from typing import Any
from typing import Generic
from typing import TypeVar
from unicodedata import normalize

from ..base import BaseModel
from ..expressions import AttrPath
from ..expressions import CompareOperator
from ..expressions import Comparison
from ..expressions import FilterNode
from ..expressions import LogicalExpr
from ..expressions import LogicalOperator
from ..expressions import Not
from ..expressions import Present
from ..expressions import ValuePath
from ..resolution import ResolvedAttribute
from ..resolution import attribute_host
from ..resolution import coerce_value
from ..resolution import resolve_filter_path
from ..resolution import validate_operator
from ..resolution import validate_value_selection

T = TypeVar("T")


class FilterVisitor(Generic[T]):
    """Dispatch over the nodes of a filter tree.

    Subclasses implement one method per node type. Write a transpiler by
    returning whatever your backend understands::

        class SqlVisitor(FilterVisitor[str]):
            def visit_comparison(self, node):
                return f"{node.attr_path.attr} = ?"

            def visit_logical_expr(self, node):
                joiner = " AND " if node.op == LogicalOperator.and_ else " OR "
                return "(" + joiner.join(self.visit(t) for t in node.terms) + ")"
    """

    def visit(self, node: FilterNode) -> T:
        """Dispatch a node to the matching ``visit_*`` method.

        :param node: The node to visit.
        :raises TypeError: If the node type is unknown.
        """
        if isinstance(node, Comparison):
            return self.visit_comparison(node)
        if isinstance(node, Present):
            return self.visit_present(node)
        if isinstance(node, Not):
            return self.visit_not(node)
        if isinstance(node, LogicalExpr):
            return self.visit_logical_expr(node)
        if isinstance(node, ValuePath):
            return self.visit_value_path(node)
        raise TypeError(f"Unsupported filter node: {type(node).__name__}")

    def visit_comparison(self, node: Comparison) -> T:
        """Visit an attribute comparison."""
        raise NotImplementedError

    def visit_present(self, node: Present) -> T:
        """Visit a presence test."""
        raise NotImplementedError

    def visit_not(self, node: Not) -> T:
        """Visit a negation."""
        raise NotImplementedError

    def visit_logical_expr(self, node: LogicalExpr) -> T:
        """Visit a conjunction or a disjunction."""
        raise NotImplementedError

    def visit_value_path(self, node: ValuePath) -> T:
        """Visit a value selection on a multi-valued attribute."""
        raise NotImplementedError


def is_present(value: Any) -> bool:
    """Whether a value satisfies the ``pr`` operator.

    :rfc:`RFC7644 §3.4.2.2 <7644#section-3.4.2.2>` defines a match as a
    "non-empty or non-null value, or ... a non-empty node for complex
    attributes". ``False`` and ``0`` are values, and are thus present, while a
    complex attribute whose sub-attributes are all unassigned is not.
    """
    if value is None:
        return False
    if isinstance(value, str | bytes):
        return len(value) > 0
    if isinstance(value, BaseModel):
        return any(
            is_present(getattr(value, name, None)) for name in type(value).model_fields
        )
    if isinstance(value, dict):
        return any(is_present(item) for item in value.values())
    if isinstance(value, list | tuple | set):
        return any(is_present(item) for item in value)
    return True


def _comparable(value: Any, case_exact: bool) -> Any:
    """Reduce a value to the form comparisons are performed on."""
    if not isinstance(value, str):
        return value

    normalized = normalize("NFC", value)
    if case_exact:
        return normalized

    # Case folding does not preserve the normalization form, so NFC is applied
    # to its result too, and every operand comes out in the same form.
    return normalize("NFC", normalized.casefold())


def compare(
    actual: Any, expected: Any, op: CompareOperator, *, case_exact: bool = False
) -> bool:
    """Apply a comparison operator to a single pair of values.

    Values of incomparable types never match, rather than raising, so that a
    filter over a heterogeneous collection stays usable.

    :param actual: The value read from the resource.
    :param expected: The value the filter compares against.
    :param op: The comparison operator.
    :param case_exact: Whether string comparison is case-sensitive.
    """
    if actual is None or expected is None:
        if op == CompareOperator.eq:
            return actual is None and expected is None
        if op == CompareOperator.ne:
            return (actual is None) != (expected is None)
        return False

    left = _comparable(actual, case_exact)
    right = _comparable(expected, case_exact)

    if op in (CompareOperator.co, CompareOperator.sw, CompareOperator.ew):
        if not isinstance(left, str) or not isinstance(right, str):
            return False
        if op == CompareOperator.co:
            return right in left
        if op == CompareOperator.sw:
            return left.startswith(right)
        return left.endswith(right)

    try:
        if op == CompareOperator.eq:
            return bool(left == right)
        if op == CompareOperator.ne:
            return bool(left != right)
        if op == CompareOperator.gt:
            return bool(left > right)
        if op == CompareOperator.ge:
            return bool(left >= right)
        if op == CompareOperator.lt:
            return bool(left < right)
        return bool(left <= right)
    except TypeError:
        return False


class Evaluator(FilterVisitor[bool]):
    """Evaluate a filter against a Python object.

    This is the reference implementation of :class:`FilterVisitor`, used by
    :meth:`ScimFilter.match <scim2_models.ScimFilter.match>`. It doubles as the proof that the
    visitor API is enough to build a complete backend.

    :param model: The model the filter attributes are resolved against.
    :param obj: The object being tested.
    :param strict: Whether unknown attributes raise instead of not matching.
    :param urn_prefix: The URN of the enclosing attribute, when evaluating the
        inner filter of a value selection, so that errors name the whole path.
    """

    def __init__(
        self,
        model: type[BaseModel],
        obj: Any,
        *,
        strict: bool = False,
        urn_prefix: str = "",
    ):
        self.model = model
        self.obj = obj
        self.strict = strict
        self.urn_prefix = urn_prefix

    def _resolve(
        self, attr_path: AttrPath, *, for_comparison: bool = False
    ) -> ResolvedAttribute | None:
        resolved = resolve_filter_path(
            self.model, attr_path, strict=self.strict, for_comparison=for_comparison
        )
        if resolved is None or not self.urn_prefix:
            return resolved
        return resolved.nested_in(self.urn_prefix)

    def _read(self, resolved: ResolvedAttribute) -> Any:
        """Read the compared value off the object, flattening multi-valued attributes."""
        host = attribute_host(self.obj, resolved)
        if host is None:
            return None

        head = getattr(host, resolved.field_name, None)

        if resolved.sub_field_name is None:
            return head

        if isinstance(head, list):
            return [
                getattr(item, resolved.sub_field_name, None)
                for item in head
                if item is not None
            ]

        if head is None:
            return None

        return getattr(head, resolved.sub_field_name, None)

    def visit_comparison(self, node: Comparison) -> bool:
        resolved = self._resolve(node.attr_path, for_comparison=True)
        if resolved is None:
            return False

        validate_operator(resolved, node.op)
        expected = coerce_value(resolved, node.value, node.op)
        actual = self._read(resolved)

        if not isinstance(actual, list):
            return compare(actual, expected, node.op, case_exact=resolved.case_exact)

        # A filter on a multi-valued attribute matches if any of its values
        # matches. The RFC does not say what that means for "ne", so the
        # universal reading is used: no value equals the operand.
        if node.op == CompareOperator.ne:
            return all(
                compare(item, expected, node.op, case_exact=resolved.case_exact)
                for item in actual
            )

        return any(
            compare(item, expected, node.op, case_exact=resolved.case_exact)
            for item in actual
        )

    def visit_present(self, node: Present) -> bool:
        resolved = self._resolve(node.attr_path)
        if resolved is None:
            return False

        actual = self._read(resolved)
        if isinstance(actual, list) and resolved.sub_field_name is not None:
            return any(is_present(item) for item in actual)
        return is_present(actual)

    def visit_not(self, node: Not) -> bool:
        return not self.visit(node.expr)

    def visit_logical_expr(self, node: LogicalExpr) -> bool:
        results = (self.visit(term) for term in node.terms)
        return all(results) if node.op == LogicalOperator.and_ else any(results)

    def visit_value_path(self, node: ValuePath) -> bool:
        """Match when at least one value of the attribute satisfies the inner filter."""
        return len(self.select(node)) > 0

    def select(self, node: ValuePath) -> list[Any]:
        """Return the values of a multi-valued attribute matching a value selection.

        This is what a PATCH operation needs in order to know which entries of
        a list it has to modify.

        :param node: The value selection to apply.
        :returns: The matching values, in their original order.
        """
        resolved = self._resolve(node.attr_path)
        if resolved is None:
            return []

        validate_value_selection(resolved)

        host = attribute_host(self.obj, resolved)
        values = getattr(host, resolved.field_name, None) if host is not None else None

        if not isinstance(values, list):
            return []

        return [
            item
            for item in values
            if self._matches_item(item, node.val_filter, resolved)
        ]

    def _matches_item(
        self, item: Any, val_filter: FilterNode, resolved: ResolvedAttribute
    ) -> bool:
        """Evaluate a value filter against one entry of a multi-valued attribute."""
        if isinstance(item, BaseModel):
            return Evaluator(
                type(item), item, strict=self.strict, urn_prefix=resolved.urn
            ).visit(val_filter)

        return _ScalarEvaluator(item, case_exact=resolved.case_exact).visit(val_filter)


class _ScalarEvaluator(FilterVisitor[bool]):
    """Evaluate a value filter against a scalar entry of a multi-valued attribute.

    A multi-valued attribute that is not complex, such as ``schemas``, holds
    plain values with no sub-attribute to compare. Implementations
    conventionally address those with ``value``, as in
    ``schemas[value eq "urn:…"]``, so ``value`` is understood here as the entry
    itself. Any other attribute name cannot match.
    """

    def __init__(self, value: Any, *, case_exact: bool = False):
        self.value = value
        self.case_exact = case_exact

    def _targets_self(self, node: Comparison | Present) -> bool:
        return node.attr_path.attr.lower() == "value" and not node.attr_path.sub_attr

    def visit_comparison(self, node: Comparison) -> bool:
        if not self._targets_self(node):
            return False
        return compare(self.value, node.value, node.op, case_exact=self.case_exact)

    def visit_present(self, node: Present) -> bool:
        return self._targets_self(node) and is_present(self.value)

    def visit_not(self, node: Not) -> bool:
        return not self.visit(node.expr)

    def visit_logical_expr(self, node: LogicalExpr) -> bool:
        results = (self.visit(term) for term in node.terms)
        return all(results) if node.op == LogicalOperator.and_ else any(results)

    def visit_value_path(self, node: ValuePath) -> bool:
        """Refuse a value selection nested in another, which the errata forbid."""
        return False
