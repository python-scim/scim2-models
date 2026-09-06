from inspect import isclass
from typing import TYPE_CHECKING
from typing import Any
from typing import Generic
from typing import TypeVar

from pydantic import GetCoreSchemaHandler
from pydantic import GetJsonSchemaHandler
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import core_schema

from ..base import BaseModel
from ..expressions import AttrPath
from ..expressions import Comparison
from ..expressions import FilterNode
from ..expressions import LogicalExpr
from ..expressions import Not
from ..expressions import Present
from ..expressions import ValuePath
from ..grammar import parse_filter
from ..resolution import ResolvedAttribute
from ..resolution import coerce_value
from ..resolution import resolve_filter_path
from ..resolution import validate_operator
from ..resolution import validate_value_selection
from ..utils import _model_union
from .visitor import Evaluator
from .visitor import FilterVisitor

if TYPE_CHECKING:
    from ..resources.resource import Resource

ResourceT = TypeVar("ResourceT", bound="Resource[Any]")

_FILTER_CACHE: dict[tuple[type, tuple[type, ...]], type] = {}


class _Validator(FilterVisitor[None]):
    """Check every expression of a filter against the model it applies to."""

    def __init__(self, *models: type[BaseModel], strict: bool, urn_prefix: str = ""):
        self.models = models
        self.strict = strict
        self.urn_prefix = urn_prefix

    def _resolve(
        self, attr_path: AttrPath, *, for_comparison: bool = False
    ) -> ResolvedAttribute | None:
        """Bind an attribute path to the first model of the union declaring it.

        An endpoint covering several resource types accepts a filter naming an
        attribute only some of them declare, since
        :rfc:`RFC7644 §3.4.2.1 <7644#section-3.4.2.1>` has the others evaluate
        it to false. Resolution therefore fails only when no model declares it.
        """
        for model in self.models:
            resolved = resolve_filter_path(
                model, attr_path, strict=False, for_comparison=for_comparison
            )
            if resolved is not None:
                if not self.urn_prefix:
                    return resolved
                return resolved.nested_in(self.urn_prefix)

        if self.strict:
            # Let the first model raise, so the error names the attribute.
            resolve_filter_path(
                self.models[0],
                attr_path,
                strict=True,
                for_comparison=for_comparison,
            )
        return None

    def visit_not(self, node: Not) -> None:
        self.visit(node.expr)

    def visit_logical_expr(self, node: LogicalExpr) -> None:
        for term in node.terms:
            self.visit(term)

    def visit_present(self, node: Present) -> None:
        self._resolve(node.attr_path)

    def visit_comparison(self, node: Comparison) -> None:
        resolved = self._resolve(node.attr_path, for_comparison=True)
        if resolved is None:
            return
        validate_operator(resolved, node.op)
        coerce_value(resolved, node.value, node.op)

    def visit_value_path(self, node: ValuePath) -> None:
        resolved = self._resolve(node.attr_path)
        if resolved is None:
            return

        validate_value_selection(resolved)
        validate_value_filter(resolved, node.val_filter, strict=self.strict)


def validate_value_filter(
    resolved: ResolvedAttribute, val_filter: FilterNode, *, strict: bool = True
) -> None:
    """Check the filter of a value selection against the attribute it selects from.

    A list of scalars has no model to resolve the inner filter against, so it
    is left alone.

    :raises InvalidFilterException: If the filter names an attribute the
        selected model does not declare, or compares one in a way it does not
        accept.
    """
    item_model = resolved.field_type
    if not isclass(item_model) or not issubclass(item_model, BaseModel):
        return

    _Validator(item_model, strict=strict, urn_prefix=resolved.urn).visit(val_filter)


class ScimFilter(str, Generic[ResourceT]):
    """A SCIM filter, as defined at :rfc:`RFC7644 §3.4.2.2 <7644#section-3.4.2.2>`.

    A filter *is* the string it was built from, so it can be passed around,
    compared and sliced like one, while also exposing its parsed form through
    :attr:`ast` and its semantics through :meth:`match`.

    Syntax is checked on creation. Binding to a model, which is what resolves
    attribute names and value types, requires a parameterised type::

        >>> from scim2_models import ScimFilter, User

        >>> ScimFilter('userName eq "bjensen"') == 'userName eq "bjensen"'
        True

        >>> user = User(user_name="bjensen")
        >>> ScimFilter[User]('userName eq "BJensen"').match(user)
        True

    A bound filter is checked against its models as it is created, so an
    operator or a value its attribute cannot take is refused straight away.
    Unknown attributes are the exception, since
    :rfc:`RFC7644 §3.4.2.1 <7644#section-3.4.2.1>` requires an endpoint covering
    several resource types to evaluate them to false; binding the filter to all
    of them, as :class:`~scim2_models.SearchRequest` does, is what turns an
    attribute none of them declares into an error.

    Attribute names are matched case-insensitively, and so is the comparison
    itself unless the attribute is annotated
    :attr:`CaseExact.true <scim2_models.CaseExact.true>`.
    """

    __scim_models__: tuple[type[BaseModel], ...] = ()

    _ast: FilterNode

    def __class_getitem__(cls, model: type[ResourceT]) -> type["ScimFilter[ResourceT]"]:
        """Create a filter class bound to a resource type, or to a union of them.

        A union is what an endpoint covering several resource types binds, such
        as the server root of :rfc:`RFC7644 §3.4.2.1 <7644#section-3.4.2.1>`.
        """
        models = _model_union(model)
        if models is None:
            return super().__class_getitem__(model)  # type: ignore[misc,no-any-return]

        cache_key = (cls, models)
        if cache_key not in _FILTER_CACHE:
            name = ", ".join(each.__name__ for each in models)
            _FILTER_CACHE[cache_key] = type(
                f"ScimFilter[{name}]", (cls,), {"__scim_models__": models}
            )
        return _FILTER_CACHE[cache_key]

    def __new__(
        cls, expression: "str | ScimFilter[Any] | FilterNode"
    ) -> "ScimFilter[ResourceT]":
        filter_ = super().__new__(cls, str(expression))
        # Parsing on creation is what makes an invalid filter fail early, and
        # the tree is kept so that it is only ever parsed once.
        filter_._ast = (
            expression
            if isinstance(expression, FilterNode)
            else parse_filter(str(filter_))
        )
        # Semantics are checked here rather than on evaluation, where the
        # boolean operators short-circuit and would only report the branches
        # they walk. Unknown attributes are left out, as an endpoint covering
        # several resource types binds the same filter to each of its types and
        # must evaluate them to false.
        if cls.__scim_models__:
            filter_._validate_semantics(strict=False)
        return filter_

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: type[Any],
        _handler: GetCoreSchemaHandler,
    ) -> core_schema.CoreSchema:
        def validate(value: Any) -> "ScimFilter[Any]":
            if isinstance(value, str):
                return cls(str(value))
            raise ValueError(f"Expected str or ScimFilter, got {type(value).__name__}")

        return core_schema.no_info_plain_validator_function(
            validate,
            serialization=core_schema.plain_serializer_function_ser_schema(str),
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        _core_schema: core_schema.CoreSchema,
        _handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        return {"type": "string"}

    @property
    def ast(self) -> FilterNode:
        """The parsed form of the filter.

        This is the tree a transpiler walks with a
        :class:`~scim2_models.filters.FilterVisitor`.
        """
        return self._ast

    def _single_model(self, method: str) -> "type[BaseModel] | None":
        """Return the one model this filter resolves against, if there is one.

        :raises TypeError: If the filter is bound to a union, which has no
            single model to resolve against. A transpiler emits one query per
            resource type, so it binds the filter to each of them in turn.
        """
        if len(self.__scim_models__) > 1:
            names = ", ".join(each.__name__ for each in self.__scim_models__)
            raise TypeError(
                f"{method} requires a filter bound to a single model, "
                f"got a union of {names}"
            )
        return self.model

    @property
    def models(self) -> tuple[type[BaseModel], ...]:
        """The resource types this filter is bound to, empty when it is unbound.

        It holds several models when the filter is bound to a union, which is
        what an endpoint covering several resource types does.
        """
        return self.__scim_models__

    @property
    def model(self) -> type[BaseModel] | None:
        """The model this filter is bound to, or :data:`None` when it is unbound.

        A filter bound to a union has no single model; read :attr:`models`
        instead.
        """
        return self.__scim_models__[0] if len(self.__scim_models__) == 1 else None

    def resolve(
        self, attr_path: AttrPath, *, strict: bool = True
    ) -> ResolvedAttribute | None:
        """Bind an attribute path of this filter to the model it designates.

        The path is resolved as it is written, which is what a presence test
        or a value selection needs. A comparison additionally follows the
        ``value`` convention, for which :meth:`resolve_comparison` is the
        right method.

        :param attr_path: The attribute path to resolve, usually taken from a
            node of :attr:`ast`.
        :param strict: Whether an unknown attribute raises instead of
            returning :data:`None`.
        :returns: The resolved attribute, or :data:`None` when the filter is
            not bound to a model.
        :raises InvalidFilterException: If ``strict`` and the attribute is unknown.

        >>> from scim2_models import ScimFilter, User
        >>> from scim2_models.filters import AttrPath

        >>> resolved = ScimFilter[User]('emails.type eq "work"').resolve(
        ...     AttrPath(attr="emails", sub_attr="type")
        ... )
        >>> resolved.field_name, resolved.sub_field_name, resolved.is_multivalued
        ('emails', 'type', True)
        """
        if (model := self._single_model("resolve")) is None:
            return None
        return resolve_filter_path(model, attr_path, strict=strict)

    def resolve_comparison(
        self, attr_path: AttrPath, *, strict: bool = True
    ) -> ResolvedAttribute | None:
        """Bind the attribute path of a comparison to the model it designates.

        A comparison against a multi-valued complex attribute applies to its
        ``value`` sub-attribute, so ``members co "x"`` compares
        ``members.value``. This is what :meth:`match` compares, and what a
        transpiler must emit its query against, down to the case sensitivity,
        which the sub-attribute carries rather than the attribute holding it.

        :param attr_path: The attribute path to resolve, usually taken from a
            :class:`~scim2_models.filters.Comparison` node of :attr:`ast`.
        :param strict: Whether an unknown attribute raises instead of
            returning :data:`None`.
        :returns: The resolved attribute, or :data:`None` when the filter is
            not bound to a model.
        :raises InvalidFilterException: If ``strict`` and the attribute is unknown.

        >>> from scim2_models import Group, ScimFilter
        >>> from scim2_models.filters import AttrPath

        >>> scim_filter = ScimFilter[Group]('members co "2819c223"')
        >>> resolved = scim_filter.resolve_comparison(AttrPath(attr="members"))
        >>> resolved.field_name, resolved.sub_field_name, resolved.case_exact
        ('members', 'value', True)
        """
        if (model := self._single_model("resolve_comparison")) is None:
            return None
        return resolve_filter_path(model, attr_path, strict=strict, for_comparison=True)

    def _validate_semantics(self, *, strict: bool = True) -> None:
        """Check the whole filter against the models it is bound to.

        Creating a bound filter runs this with ``strict=False``, which rejects
        an operator an attribute type forbids, a value that cannot be read as
        that type, and a value selection over an attribute holding a single
        value. Unknown attributes are left to ``strict``, which
        :class:`~scim2_models.SearchRequest` turns on: naming the resource
        types an endpoint serves is what makes an attribute none of them
        declares a client error, where
        :rfc:`RFC7644 §3.4.2.1 <7644#section-3.4.2.1>` has an unparameterised
        request evaluate it to false instead.

        :param strict: Whether unknown attributes raise instead of being ignored.
        :raises InvalidFilterException: If ``strict`` and an attribute is unknown,
            or if a value or an operator is not valid for its attribute.
        """
        if not self.__scim_models__:
            return
        _Validator(*self.__scim_models__, strict=strict).visit(self.ast)

    def match(self, resource: ResourceT, *, strict: bool = False) -> bool:
        """Whether a resource satisfies this filter.

        Attribute names are compared case-insensitively, and so are string
        values unless the attribute is annotated
        :attr:`CaseExact.true <scim2_models.CaseExact.true>`. A filter over a
        multi-valued attribute matches when any of its values matches.

        :param resource: The resource to test.
        :param strict: Whether an unknown attribute raises instead of not matching.
        :returns: :data:`True` if the resource matches.
        :raises TypeError: If the filter is not bound to a model.
        :raises InvalidFilterException: If ``strict`` and the filter names an
            attribute the model does not declare. Anything else a filter can get
            wrong about its model is already refused when the bound filter is
            created.

        >>> from scim2_models import ScimFilter, User

        >>> user = User(
        ...     user_name="bjensen",
        ...     emails=[{"type": "work", "value": "bjensen@example.com"}],
        ... )
        >>> ScimFilter[User]('emails[type eq "work"]').match(user)
        True
        >>> ScimFilter[User]('emails[type eq "home"]').match(user)
        False
        >>> ScimFilter[User]('userName sw "bj" and title pr').match(user)
        False
        """
        if not self.__scim_models__:
            raise TypeError("match requires a bound filter type: ScimFilter[Model]")

        model = self.model or type(resource)
        return Evaluator(model, resource, strict=strict).visit(self.ast)
