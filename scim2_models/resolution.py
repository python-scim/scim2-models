from dataclasses import dataclass
from dataclasses import replace
from functools import lru_cache
from inspect import isclass
from typing import Any
from typing import cast
from typing import get_args

from pydantic import TypeAdapter
from pydantic import ValidationError

from .annotations import CaseExact
from .base import BaseModel
from .exceptions import InvalidFilterException
from .exceptions import PathNotFoundException
from .expressions import ORDERING_OPERATORS
from .expressions import STRING_OPERATORS
from .expressions import AttrPath
from .expressions import CompareOperator
from .utils import _find_field_name

# Python types that RFC7644 §3.4.2.2 forbids comparing with an ordering operator.
_UNORDERABLE_TYPES = (bool, bytes)


def _unwrap_annotated(type_: Any) -> type | None:
    """Strip the metadata of an :data:`~typing.Annotated` type.

    A ``binary`` attribute is declared as ``Base64Bytes``, which is an
    annotated :class:`bytes` rather than a class of its own.
    """
    metadata = getattr(type_, "__metadata__", None)
    unwrapped = get_args(type_)[0] if metadata else type_
    return cast("type | None", unwrapped)


@dataclass(frozen=True)
class ResolvedAttribute:
    """A syntactic attribute path bound to the model it designates.

    Transpilers get everything they need to emit a query out of this: which
    table or column, whether a join is required, and whether the comparison
    should be case-sensitive.
    """

    model: type[BaseModel]
    """The model holding the head attribute, either a resource or an extension."""

    field_name: str
    """The Python name of the head attribute, e.g. ``emails``."""

    field_type: type | None
    """The Python type of the head attribute, e.g. ``Email``."""

    is_multivalued: bool
    """Whether the head attribute holds several values, which usually means a join."""

    sub_field_name: str | None = None
    """The Python name of the sub-attribute, e.g. ``type`` in ``emails.type``."""

    sub_field_type: type | None = None
    """The Python type of the sub-attribute."""

    case_exact: bool = False
    """Whether the compared attribute is case-sensitive."""

    urn: str = ""
    """The fully qualified URN of the compared attribute."""

    @property
    def target_type(self) -> type | None:
        """The type of the attribute actually compared, sub-attribute included.

        Annotated types are unwrapped, so a ``binary`` attribute declared as
        ``Base64Bytes`` reports :class:`bytes`.
        """
        raw = self.sub_field_type if self.sub_field_name else self.field_type
        return _unwrap_annotated(raw)

    @property
    def target_model(self) -> type[BaseModel] | None:
        """The model holding the attribute actually compared."""
        if not self.sub_field_name:
            return self.model
        if isclass(self.field_type) and issubclass(self.field_type, BaseModel):
            return self.field_type
        return None

    @property
    def target_field_name(self) -> str:
        """The Python name of the attribute actually compared."""
        return self.sub_field_name or self.field_name

    def nested_in(self, urn: str) -> "ResolvedAttribute":
        """Return the same attribute, qualified by the URN it was resolved under.

        An attribute resolved inside a value selection is resolved against a
        complex model, which has no schema of its own, so its URN is only
        complete once the URN of the enclosing attribute is known.
        """
        return replace(self, urn=f"{urn}.{self.urn}")


def attribute_host(obj: Any, resolved: ResolvedAttribute) -> Any:
    """Return the object actually holding a resolved attribute.

    An attribute qualified by an extension URN lives on the extension instance,
    which hangs off the resource under the extension class name.

    :param obj: The resource the attribute was resolved against.
    :param resolved: The attribute to look for.
    :returns: The object to read the attribute from, or :data:`None` when the
        extension holding it is not set.
    """
    from .resources.resource import Extension

    model = resolved.model
    if not (isclass(model) and issubclass(model, Extension)):
        return obj
    if isinstance(obj, model):
        return obj
    return getattr(obj, model.__name__, None)


def _extension_models(model: type[BaseModel]) -> dict[str, type[BaseModel]]:
    """Return the extension models of a resource, keyed by schema URN."""
    from .resources.resource import Resource

    if not (isclass(model) and issubclass(model, Resource)):
        return {}
    return dict(model.get_extension_models())


def _target_model(
    model: type[BaseModel], attr_path: AttrPath, *, strict: bool
) -> type[BaseModel] | None:
    """Resolve which model an attribute path applies to.

    A path without a URN applies to the resource itself. A qualified path
    applies either to the resource or to one of its extensions.
    """
    from .resources.resource import Extension
    from .resources.resource import Resource

    if attr_path.uri is None:
        return model

    uri = attr_path.uri.lower()

    own_schema = getattr(model, "__schema__", None) if isclass(model) else None
    if own_schema and uri == own_schema.lower():
        return model

    for schema, extension_model in _extension_models(model).items():
        if uri == schema.lower():
            return extension_model

    # An unqualified sub-model such as a complex attribute has no schema of its
    # own, so a qualified path can only be addressed to a resource or extension.
    if not (isclass(model) and issubclass(model, Resource | Extension)):
        return None

    if strict:
        raise PathNotFoundException(path=str(attr_path), field=attr_path.attr)
    return None


@lru_cache(maxsize=1024)
def resolve_attr_path(
    model: type[BaseModel], attr_path: AttrPath, *, strict: bool = True
) -> ResolvedAttribute | None:
    """Bind an attribute path to the field it designates on a model.

    :param model: The resource or extension model to resolve against.
    :param attr_path: The attribute path to resolve.
    :param strict: Whether an unknown attribute raises instead of returning
        :data:`None`. Servers are expected to be tolerant of schema
        extensions, per :rfc:`RFC7644 §3.5.2 <7644#section-3.5.2>`.
    :returns: The resolved attribute, or :data:`None` when it cannot be
        resolved and ``strict`` is false. Results are cached and shared, which
        is safe since :class:`ResolvedAttribute` is immutable.
    :raises PathNotFoundException: If ``strict`` and the attribute is unknown.
    """
    target = _target_model(model, attr_path, strict=strict)
    if target is None:
        return None

    field_name = _find_field_name(target, attr_path.attr)
    if field_name is None:
        if strict:
            raise PathNotFoundException(path=str(attr_path), field=attr_path.attr)
        return None

    field_type = target.get_field_root_type(field_name)
    is_multivalued = target.get_field_multiplicity(field_name)

    sub_field_name: str | None = None
    sub_field_type: type | None = None

    if attr_path.sub_attr is not None:
        if not (isclass(field_type) and issubclass(field_type, BaseModel)):
            if strict:
                raise PathNotFoundException(
                    path=str(attr_path), field=attr_path.sub_attr
                )
            return None

        sub_field_name = _find_field_name(field_type, attr_path.sub_attr)
        if sub_field_name is None:
            if strict:
                raise PathNotFoundException(
                    path=str(attr_path), field=attr_path.sub_attr
                )
            return None

        sub_field_type = field_type.get_field_root_type(sub_field_name)

    # A sub-attribute is only resolved on a model, as checked above, so the
    # holder is always one.
    case_exact_holder = field_type if sub_field_name else target
    case_exact = (
        case_exact_holder.get_field_annotation(  # type: ignore[union-attr]
            sub_field_name or field_name, CaseExact
        )
        == CaseExact.true
    )

    return ResolvedAttribute(
        model=target,
        field_name=field_name,
        field_type=field_type,
        is_multivalued=is_multivalued,
        sub_field_name=sub_field_name,
        sub_field_type=sub_field_type,
        case_exact=case_exact,
        urn=_build_urn(target, attr_path),
    )


def _addresses_entry_values(resolved: ResolvedAttribute) -> bool:
    """Whether a comparison against this attribute applies to ``value`` instead."""
    return (
        resolved.sub_field_name is None
        and resolved.is_multivalued
        and isclass(resolved.field_type)
        and issubclass(resolved.field_type, BaseModel)
        and _find_field_name(resolved.field_type, "value") is not None
    )


def resolve_comparison_path(
    model: type[BaseModel], attr_path: AttrPath, *, strict: bool = True
) -> ResolvedAttribute | None:
    """Bind the attribute a comparison applies to.

    :rfc:`RFC7644 §3.4.2.2 <7644#section-3.4.2.2>` uses ``emails co
    "example.com"`` and ``emails.value co "example.org"`` in the same
    expression, so a comparison against a multi-valued complex attribute
    applies to the ``value`` sub-attribute its entries carry
    (:rfc:`RFC7643 §2.4 <7643#section-2.4>`). Presence tests and value
    selections keep addressing the attribute itself, since ``pr`` is defined on
    "a non-empty node for complex attributes".

    :param model: The resource or extension model to resolve against.
    :param attr_path: The attribute path to resolve.
    :param strict: Whether an unknown attribute raises instead of returning
        :data:`None`.
    :returns: The resolved attribute, or :data:`None` when it cannot be
        resolved and ``strict`` is false.
    :raises PathNotFoundException: If ``strict`` and the attribute is unknown.

    >>> from scim2_models import User
    >>> from scim2_models.filters import AttrPath, resolve_comparison_path

    >>> resolve_comparison_path(User, AttrPath("emails")).sub_field_name
    'value'
    """
    resolved = resolve_attr_path(model, attr_path, strict=strict)
    if resolved is None or not _addresses_entry_values(resolved):
        return resolved

    return resolve_attr_path(
        model, AttrPath(attr_path.attr, "value", attr_path.uri), strict=strict
    )


def resolve_filter_path(
    model: type[BaseModel],
    attr_path: AttrPath,
    *,
    strict: bool = True,
    for_comparison: bool = False,
) -> ResolvedAttribute | None:
    """Bind an attribute path taken from a filter.

    An attribute a model does not declare makes the *filter* invalid rather
    than the path, since :rfc:`RFC7644 §3.12 <7644#section-3.12>` defines
    ``invalidPath`` for the ``path`` of a PATCH operation, and ``invalidFilter``
    for "the specified attribute and filter comparison combination".

    :param model: The resource or extension model to resolve against.
    :param attr_path: The attribute path to resolve.
    :param strict: Whether an unknown attribute raises instead of returning
        :data:`None`.
    :param for_comparison: Whether the path is the one of a comparison, which
        follows the ``value`` convention of :func:`resolve_comparison_path`.
    :returns: The resolved attribute, or :data:`None` when it cannot be
        resolved and ``strict`` is false.
    :raises InvalidFilterException: If ``strict`` and the attribute is unknown.
    """
    resolve = resolve_comparison_path if for_comparison else resolve_attr_path
    try:
        return resolve(model, attr_path, strict=strict)
    except PathNotFoundException as exc:
        raise InvalidFilterException(detail=str(exc)) from exc


def _build_urn(model: type[BaseModel], attr_path: AttrPath) -> str:
    """Build the fully qualified URN of a resolved attribute."""
    schema = attr_path.uri or (
        getattr(model, "__schema__", None) if isclass(model) else None
    )
    suffix = str(AttrPath(attr=attr_path.attr, sub_attr=attr_path.sub_attr))
    return f"{schema}:{suffix}" if schema else suffix


def coerce_value(
    resolved: ResolvedAttribute, value: Any, op: CompareOperator | None = None
) -> Any:
    """Convert a raw comparison value to the Python type of its attribute.

    A filter carries JSON values, but a model holds Python ones: a
    ``dateTime`` attribute compared against ``"2011-05-13T04:42:34Z"`` has to
    be compared against a :class:`~datetime.datetime`.

    The substring operators are exempt, since they match a fragment rather than
    a whole value: ``emails[value co "example"]`` is a legitimate filter even
    though ``"example"`` is not a valid email address on its own.

    :param resolved: The attribute the value is compared against.
    :param value: The raw value read from the filter.
    :param op: The operator the value is used with, when known.
    :returns: The value converted to the attribute type, left untouched when
        no conversion applies.
    :raises InvalidFilterException: If the value is not valid for the attribute.
    """
    target_type = resolved.target_type
    if value is None or target_type is None or target_type is Any:
        return value

    if op is not None and op in STRING_OPERATORS:
        return value

    if not isclass(target_type) or issubclass(target_type, BaseModel):
        return value

    if isinstance(value, target_type) and not issubclass(target_type, bytes):
        return value

    # The annotated form is what carries a decoder, so a base64 operand of a
    # binary attribute is decoded rather than taken for raw bytes.
    annotated_type = (
        resolved.sub_field_type if resolved.sub_field_name else resolved.field_type
    )

    try:
        return TypeAdapter(annotated_type).validate_python(value)
    except ValidationError as exc:
        raise InvalidFilterException(
            detail=f"value {value!r} is not valid for attribute '{resolved.urn}'"
        ) from exc


def validate_operator(resolved: ResolvedAttribute, op: CompareOperator) -> None:
    """Check that an operator may be applied to an attribute.

    :rfc:`RFC7644 §3.4.2.2 <7644#section-3.4.2.2>` requires boolean and binary
    attributes to be rejected for the ordering operators. The same is done for
    the substring operators, which have no meaning on those types either.

    :param resolved: The attribute the operator is applied to.
    :param op: The operator to check.
    :raises InvalidFilterException: If the combination is not supported.
    """
    target_type = resolved.target_type
    if not isclass(target_type) or not issubclass(target_type, _UNORDERABLE_TYPES):
        return

    if op not in ORDERING_OPERATORS | STRING_OPERATORS:
        return

    kind = "boolean" if issubclass(target_type, bool) else "binary"
    raise InvalidFilterException(
        detail=f"operator '{op.value}' cannot be applied to the {kind} attribute '{resolved.urn}'"
    )


def validate_value_selection(resolved: ResolvedAttribute) -> None:
    """Check that a value selection applies to a multi-valued attribute.

    :rfc:`RFC7644 §3.5.2 <7644#section-3.5.2>` defines the ``valuePath`` rule
    as selecting "specific values of a complex multi-valued attribute", so an
    attribute holding a single value has nothing to select from.

    :param resolved: The attribute the selection applies to.
    :raises InvalidFilterException: If the attribute is not multi-valued.
    """
    if resolved.is_multivalued:
        return

    raise InvalidFilterException(
        detail=f"attribute '{resolved.urn}' is not multi-valued and holds no values to select"
    )
