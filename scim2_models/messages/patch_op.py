import copy
from collections.abc import Iterator
from dataclasses import replace
from enum import StrEnum
from functools import reduce
from inspect import isclass
from operator import and_
from operator import or_
from typing import Annotated
from typing import Any
from typing import Generic
from typing import Self
from typing import TypeVar
from typing import cast
from typing import get_origin

from pydantic import Field
from pydantic import SerializationInfo
from pydantic import SerializerFunctionWrapHandler
from pydantic import ValidationError
from pydantic import ValidationInfo
from pydantic import field_validator
from pydantic import model_serializer
from pydantic import model_validator

from ..annotations import Mutability
from ..annotations import Required
from ..attributes import ComplexAttribute
from ..base import BaseModel
from ..context import Context
from ..exceptions import InvalidPathException
from ..exceptions import InvalidValueException
from ..exceptions import MutabilityException
from ..exceptions import NoTargetException
from ..exceptions import SCIMException
from ..path import AttrPath
from ..path import CompareOperator
from ..path import Comparison
from ..path import FilterNode
from ..path import LogicalExpr
from ..path import LogicalOperator
from ..path import Path
from ..path.access import _select
from ..path.access import _set_values
from ..policy import ScimPolicy
from ..policy import _effective_policy
from ..policy import _policy
from ..resources.resource import Resource
from ..urn import URN
from ..utils import UNION_TYPES
from .message import Message
from .message import _get_resource_class
from .message import _ResourceParameterized

ResourceT = TypeVar("ResourceT", bound=Resource[Any])


class PatchOperation(ComplexAttribute, Generic[ResourceT]):
    class Op(StrEnum):
        replace_ = "replace"
        remove = "remove"
        add = "add"

    op: Op
    """Each PATCH operation object MUST have exactly one "op" member, whose
    value indicates the operation to perform and MAY be one of "add", "remove",
    or "replace".

    .. note::

        For the sake of compatibility with Microsoft Entra,
        despite :rfc:`RFC7644 §3.5.2 <7644#section-3.5.2>`, op is case-insensitive.
    """

    path: Path[ResourceT] | None = None
    """The "path" attribute value is a String containing an attribute path
    describing the target of the operation."""

    value: Any | None = None

    @model_validator(mode="after")
    def _validate_request_operation(self, info: ValidationInfo) -> Self:
        """Reject an operation that lacks a member RFC7644 §3.5.2 requires.

        A remove needs a path. An add needs a value, and null is not one. A
        replace needs a value, and null unassigns the target.
        """
        if not _in_patch_request(info):
            return self
        if self.op == PatchOperation.Op.remove and self.path is None:
            raise NoTargetException(
                detail="Remove operation requires a path"
            ).as_pydantic_error()
        if (self.op == PatchOperation.Op.add and self.value is None) or (
            self.op == PatchOperation.Op.replace_
            and "value" not in self.model_fields_set
        ):
            raise InvalidValueException(
                detail=f"value is required for {self.op.value} operations"
            ).as_pydantic_error()
        return self

    @model_serializer(mode="wrap")
    def _scim_serializer(
        self, handler: SerializerFunctionWrapHandler, info: SerializationInfo
    ) -> dict[str, Any]:
        """Keep a null value the operation was given.

        SCIM dumps drop null values, so a replace that clears its target would
        be sent without a value.
        """
        serialized = super()._scim_serializer(handler, info)
        if (
            self.op != PatchOperation.Op.remove
            and "value" in self.model_fields_set
            and self.value is None
        ):
            serialized["value"] = None
        return serialized

    @field_validator("op", mode="before")
    @classmethod
    def _normalize_op(cls, v: Any) -> Any:
        """Ignore case for op.

        This brings
        `compatibility with Microsoft Entra <https://learn.microsoft.com/en-us/entra/identity/app-provisioning/use-scim-to-provision-users-and-groups#general>`_:

        Don't require a case-sensitive match on structural elements in SCIM, in
        particular PATCH op operation values, as defined in section 3.5.2.
        Microsoft Entra ID emits the values of op as Add, Replace, and Remove.
        """
        if isinstance(v, str):
            v = v.lower()
        try:
            return cls.Op(v)
        except ValueError:
            # RFC7644 §3.5.2 defines no scimType for an unknown operation, and
            # §3.12 defines invalidValue for a value that does not fit the
            # operation.
            raise InvalidValueException(
                detail=f"{v!r} is not a PATCH operation: add, remove or replace"
            ).as_pydantic_error() from None


class PatchOp(_ResourceParameterized, Message, Generic[ResourceT]):
    """Patch Operation as defined in :rfc:`RFC7644 §3.5.2 <7644#section-3.5.2>`.

    Parameterise the message with the resource type the patched resource has,
    as in ``PatchOp[User]``. The parameter is what resolves the paths the
    operations carry, so a patch cannot be validated or applied without it. A
    union names several types where one resource is patched, so it is refused:
    a PATCH targets the one resource its endpoint designates.

    >>> from scim2_models import PatchOp, User
    >>> user = User(user_name="bjensen")
    >>> patch = PatchOp[User](
    ...     operations=[
    ...         {"op": "replace", "path": "displayName", "value": "Barbara Jensen"}
    ...     ]
    ... )
    >>> patch.patch(user), user.display_name
    (True, 'Barbara Jensen')
    """

    def __class_getitem__(cls, item: Any) -> Any:
        """Refuse a union: a PATCH targets one resource type."""
        parameter = item[0] if isinstance(item, tuple) and len(item) == 1 else item

        if get_origin(parameter) in UNION_TYPES:
            raise TypeError(
                f"{cls.__name__} type parameter must name one resource type, "
                f"got {parameter}. A PATCH targets the resource its endpoint "
                f"designates, so use {cls.__name__}[User]."
            )

        return super().__class_getitem__(item)

    __schema__ = URN("urn:ietf:params:scim:api:messages:2.0:PatchOp")

    operations: Annotated[list[PatchOperation[ResourceT]] | None, Required.true] = (
        Field(None, serialization_alias="Operations")
    )
    """The body of an HTTP PATCH request MUST contain the attribute
    "Operations", whose value is an array of one or more PATCH operations."""

    @model_validator(mode="after")
    def _validate_operations(self, info: ValidationInfo) -> Self:
        """Reject the errors the operations have on any resource of the type."""
        if self.operations is None:
            if _in_patch_request(info):
                raise InvalidValueException(
                    detail="operations attribute is required"
                ).as_pydantic_error()
            return self
        if not self.operations:
            raise InvalidValueException(
                detail="operations holds one or more operations"
            ).as_pydantic_error()

        model = _get_resource_class(self)
        try:
            for operation in self.operations:
                _check_operation(
                    model, operation, _policy(info), in_request=_in_patch_request(info)
                )
        except SCIMException as exc:
            raise exc.as_pydantic_error() from exc
        return self

    @classmethod
    def build_from(
        cls, before: ResourceT, after: ResourceT
    ) -> "PatchOp[ResourceT] | None":
        """Build the patch turning a resource state into another one.

        Only the attributes *after* names take part in the comparison: what a
        wanted state never mentions is left to the peer, which is what
        distinguishes a patch from the :meth:`~scim2_models.Resource.replace`
        it stands for. An attribute named with no value is removed, as
        ``title=None`` reads as "clear the title" where an unnamed ``title``
        reads as "leave it alone".

        A multi-valued attribute is replaced as a whole, and only the
        sub-attributes the wanted entries name decide whether it changed.
        Read-only attributes never appear in the patch.

        >>> from scim2_models import PatchOp, User
        >>> patch = PatchOp.build_from(User(nick_name="Barb"), User(nick_name="Babs"))
        >>> patch.model_dump()["Operations"]
        [{'op': 'replace', 'path': 'nickName', 'value': 'Babs'}]

        :param before: The state the peer is believed to hold.
        :param after: The state the peer should hold.
        :return: The patch to send, or :data:`None` when the two states agree.
        :raises MutabilityException: If an immutable attribute already holding a
            value would be modified.
        :raises TypeError: If the two states are not of the same resource type.
        """
        if type(before) is not type(after):
            raise TypeError(
                "Cannot compare two states of different types: "
                f"{type(before).__name__} and {type(after).__name__}"
            )

        # Subscripted through the call the syntax stands for: mypy reads the
        # index of a generic as a type, not as a value.
        model = type(after)
        operation_class: Any = PatchOperation.__class_getitem__(model)
        operations = [
            operation_class(op=op, path=path, value=value)
            for op, path, value in _differences(before, after, "")
        ]
        if not operations:
            return None

        patch_class = PatchOp.__class_getitem__(model)
        patch = cast("PatchOp[ResourceT]", patch_class(operations=operations))
        # Apply to a copy, so that a patch the peer would reject fails here.
        patch.patch(before.model_copy(deep=True))
        return patch

    def patch(self, resource: ResourceT, scim_policy: ScimPolicy | None = None) -> bool:
        """Apply all PATCH operations to the given SCIM resource in sequence.

        The resource is modified in-place.

        Each operation in the PatchOp is applied in order, modifying the resource in-place
        according to :rfc:`RFC7644 §3.5.2 <7644#section-3.5.2>`. Supported operations are
        "add", "replace", and "remove". If any operation modifies the resource, the method
        returns True; otherwise, False.

        Per :rfc:`RFC 7644 §3.5.2 <7644#section-3.5.2>`, when an operation sets a value's
        ``primary`` sub-attribute to ``True``, any other values in the same multi-valued
        attribute will have their ``primary`` set to ``False`` automatically.

        The operations are applied as a whole: when one fails, the resource is
        left as it was. The resource object itself is kept, but the values it
        holds are then copies of the ones it held, so a reference taken on one
        of them beforehand no longer reflects the resource.

        :param resource: The SCIM resource to patch. This object is modified in-place.
        :param scim_policy: The :class:`~scim2_models.ScimPolicy` the patch is
            applied under. Defaults to the strict reading of the specification.
        :return: True if the resource was modified by any operation, False otherwise.
        :raises InvalidValueException: If a value is not compatible with the type of
            the attribute it is written to, if multiple values are marked as primary
            in a single operation, or if multiple primary values already exist
            before the patch.
        :raises MutabilityException: If an operation changes an immutable value,
            changes a read-only value through its value, or leaves a required
            attribute unassigned.
        :raises NoTargetException: If the path filter of an ``add`` or
            ``replace`` matches no value, and
            :attr:`~scim2_models.ScimPolicy.unmatched_path_filter` creates no
            entry for it.
        """
        snapshot = resource.model_copy(deep=True)
        try:
            # The policy is made ambient for the whole application: the passes
            # it governs below are revalidations that start from no call of ours.
            with _effective_policy(scim_policy):
                modified = [
                    _apply_operation(resource, operation, _effective_policy())
                    for operation in self.operations or []
                ]
        except Exception:
            _restore(resource, snapshot)
            raise
        return any(modified)


def _in_patch_request(info: ValidationInfo) -> bool:
    """Whether a validation reads the payload of a PATCH request."""
    return (info.context or {}).get("scim") == Context.RESOURCE_PATCH_REQUEST


def _is_model(type_: Any) -> bool:
    """Whether a type is a model, whose values hold attributes."""
    return isclass(type_) and issubclass(type_, BaseModel)


def _as_payload(value: Any) -> Any:
    """Return the payload a value built in Python would be sent as."""
    if isinstance(value, BaseModel):
        return value.model_dump(scim_ctx=Context.DEFAULT)
    return value


def _dropped(path: Path[Any], policy: ScimPolicy) -> bool:
    """Whether the policy drops the undeclared attribute of a path."""
    return (
        path.model is None
        and path.resolve() is None
        and policy.unknown != ScimPolicy.Unknown.forbid
    )


def _check_operation(
    model: type[Resource[Any]],
    operation: PatchOperation[Any],
    policy: ScimPolicy,
    *,
    in_request: bool,
) -> None:
    """Reject the errors an operation has on any resource.

    The path must target a declared attribute that is not read-only, and must
    not remove or unassign a required attribute. The attributes in a value are
    checked against the resource when the patch is applied.
    """
    path = Path.__class_getitem__(model)(operation.path or "")
    removal = operation.op == PatchOperation.Op.remove
    if removal and in_request:
        _removal_path(path, operation.value, policy)
    if _dropped(path, policy):
        return

    if path.model is None:
        binding = path.resolve()
        if binding is None:
            raise InvalidPathException(
                path=str(path), detail=f"'{path}' is not an attribute of the schema"
            )
        mutabilities = (
            binding.model.get_field_annotation(binding.field_name, Mutability),
            binding.get_annotation(Mutability),
        )
        if Mutability.read_only in mutabilities:
            raise MutabilityException(
                attribute=str(path), detail=f"'{path}' is read-only"
            )

    if not removal:
        for write_path, value in _writes(path, operation.value, policy):
            if value is None or (value == [] and operation.op != PatchOperation.Op.add):
                _refuse_unassigning(write_path, "unassigned")
        return

    if operation.path is not None:
        _refuse_unassigning(path, "removed")


def _refuse_unassigning(path: Path[Any], verb: str) -> None:
    """Reject an operation that unassigns a required attribute (RFC7644 §3.5.2.2).

    A sub-attribute is only required when its parent is assigned, and a
    selection may leave values behind, so both are checked when the patch is
    applied.
    """
    binding = path.resolve()
    if binding is None or binding.sub_field_name or path.value_filter is not None:
        return
    if (
        binding.model.get_field_annotation(binding.field_name, Required)
        == Required.true
    ):
        raise MutabilityException(
            attribute=str(path), detail=f"required attribute cannot be {verb}"
        )


def _removal_path(path: Path[Any], value: Any, policy: ScimPolicy) -> Path[Any] | None:
    """Return the path a remove deletes, or None when its value selects nothing.

    RFC7644 §3.5.2.2 reads the target of a remove from its path only. Under the
    apply policy, the value lists the entries to remove by their sub-
    attributes, as Microsoft Entra sends it.
    """
    if value is None:
        return path
    if policy.remove_value_as_filter == ScimPolicy.RemoveValue.forbid:
        raise InvalidValueException(
            detail="a remove operation carries no value, "
            "a filter in the path selects what to remove"
        )
    if path.model is not None:
        raise InvalidPathException(
            path=str(path),
            detail="a remove selecting values by its value needs "
            "a path to the attribute holding them",
        )

    entries = value if isinstance(value, list) else [value]
    if path.value_filter is not None or not all(
        isinstance(entry, dict) and entry for entry in entries
    ):
        raise InvalidValueException(
            detail="the value of a remove must be non-empty objects, "
            "on a path without a filter"
        )
    if not entries:
        return None
    try:
        selection = reduce(
            or_,
            (
                reduce(and_, (_selector(name, item) for name, item in entry.items()))
                for entry in entries
            ),
        )
        selected = f"{path}[{selection}]"
    except ValueError as exc:
        raise InvalidValueException(detail=str(exc)) from exc
    return type(path)(selected)


def _selector(name: str, item: Any) -> FilterNode:
    """Build the comparison for one key of a remove value.

    AttrPath refuses a key that is not an attribute name, so a key cannot add
    filter syntax.
    """
    if isinstance(item, dict | list):
        raise ValueError(f"{name!r} must be compared to a single value")
    return Comparison(AttrPath(name), CompareOperator.eq, item)


def _apply_operation(
    resource: Resource[Any], operation: PatchOperation[Any], policy: ScimPolicy
) -> bool:
    """Apply one operation as RFC7644 §3.5.2 defines it, then check the result."""
    if not isinstance(operation.op, PatchOperation.Op):
        raise InvalidValueException(detail=f"{operation.op!r} is not a PATCH operation")
    path = Path.__class_getitem__(type(resource))(operation.path or "")
    if _dropped(path, policy):
        return False

    removal = None
    if operation.op == PatchOperation.Op.remove:
        if operation.path is None:
            raise NoTargetException(detail="Remove operation requires a path")
        removal = _removal_path(path, operation.value, policy)
        writes = []
        touched = [] if removal is None else [removal]
    else:
        writes = list(_writes(path, operation.value, policy))
        touched = [path, *(write_path for write_path, _ in writes)]

    memo: dict[int, Any] = {}
    before = _snapshot(resource, touched, memo)
    try:
        if operation.op == PatchOperation.Op.remove:
            if removal is not None:
                removal.delete(resource)
        elif not _create_described_entry(resource, path, operation.value, policy):
            _write(resource, path, writes, is_add=operation.op == PatchOperation.Op.add)
    except ValidationError as exc:
        raise InvalidValueException(detail=str(exc)) from exc
    _settle(before, resource, memo)
    return not all(
        _same(getattr(before, name), getattr(resource, name))
        for name in type(resource).model_fields
    )


def _write(
    resource: Resource[Any],
    path: Path[Any],
    writes: list[tuple[Path[Any], Any]],
    *,
    is_add: bool,
) -> None:
    """Write the value of an add or a replace.

    The path filter is resolved even when the value writes nothing, so a filter
    that matches nothing is always reported.
    """
    if not writes:
        selection = _select(path, resource)
        if selection is not None and not selection.matched:
            raise NoTargetException(
                detail=f"no value of '{selection.field_name}' matches the path filter"
            )
    _set_values(resource, writes, is_add=is_add)


def _writes(
    path: Path[Any], value: Any, policy: ScimPolicy
) -> Iterator[tuple[Path[Any], Any]]:
    """Split the value of an add or a replace into single writes.

    A value for a model or a complex attribute is written key by key, so the
    attributes it leaves out are kept, as RFC7644 §3.5.2.3 requires. A key can
    be an attribute path. Any other value is written at the path.
    """
    value = _as_payload(value)
    prefix = _key_prefix(path)
    if prefix is None or (path.model is None and not isinstance(value, dict)):
        yield path, value
        return
    if not isinstance(value, dict):
        raise InvalidValueException(
            detail=f"the value written to '{path}' must be an object"
        )

    for key, item in value.items():
        if key.lower() == "schemas":
            continue
        key_path = _declared(path, prefix + key, policy)
        if key_path is not None and key_path.model is not None and item is None:
            yield key_path, None
        elif key_path is not None:
            yield from _writes(key_path, item, policy)


def _key_prefix(path: Path[Any]) -> str | None:
    """Return the path the keys of a value are relative to.

    The keys of a value for a model are attribute names or paths. The keys of a
    value for a complex attribute, or for the entries a filter selects, are
    sub-attribute names. Any other target takes a plain value, and gets None.
    """
    if path.model is not None:
        return "" if path.model is path.models[0] else f"{path}:"

    binding = path.resolve()
    if (
        binding is None
        or binding.sub_field_name is not None
        or not _is_model(binding.field_type)
        or (binding.is_multivalued and path.value_filter is None)
    ):
        return None
    return f"{path._as_value_path() or path}."


def _declared(parent: Path[Any], text: str, policy: ScimPolicy) -> Path[Any] | None:
    """Return the path a key of a value stands for.

    The key must match a declared attribute, without a filter. Otherwise it is
    dropped under a tolerant policy, or rejected with invalidValue, which
    RFC7644 §3.12 defines for a value that does not fit the schema.
    """
    try:
        key_path = type(parent)(text)
    except InvalidPathException:
        key_path = None
    if (
        key_path is not None
        and key_path.value_filter == parent.value_filter
        and (key_path.model or key_path.resolve())
    ):
        return key_path
    if policy.unknown != ScimPolicy.Unknown.forbid:
        return None
    raise InvalidValueException(
        detail=f"'{text}' is not declared by the resource schema"
    )


def _create_described_entry(
    resource: Resource[Any], path: Path[Any], value: Any, policy: ScimPolicy
) -> bool:
    """Add the entry an unmatched path filter describes, under the create policy.

    The entry gets the values the eq comparisons of the filter compare, then
    the value of the operation. It must still match the filter, so that later
    operations find it.
    """
    value_path = path._as_value_path()
    if (
        value_path is None
        or policy.unmatched_path_filter != ScimPolicy.UnmatchedPathFilter.create
    ):
        return False

    selection = type(path)(str(replace(value_path, sub_attr=None)))
    described = _described_entry(value_path.val_filter)
    binding = selection.resolve()
    written = (
        {value_path.sub_attr: value} if value_path.sub_attr else _as_payload(value)
    )
    if (
        selection.get(resource) is not None
        or described is None
        or binding is None
        or not _is_model(binding.field_type)
        or not isinstance(written, dict)
    ):
        return False

    type(path)(str(value_path.attr_path)).set(
        resource, {**described, **written}, is_add=True
    )
    if selection.get(resource) is None:
        raise InvalidValueException(
            detail=f"the value contradicts the filter of '{path}'"
        )
    return True


def _described_entry(val_filter: FilterNode) -> dict[str, Any] | None:
    """Return the sub-attribute values set by eq comparisons joined by and."""
    terms = (
        val_filter.terms
        if isinstance(val_filter, LogicalExpr) and val_filter.op == LogicalOperator.and_
        else (val_filter,)
    )
    comparisons = [
        term
        for term in terms
        if isinstance(term, Comparison)
        and term.op == CompareOperator.eq
        and term.attr_path.sub_attr is None
        and term.attr_path.uri is None
    ]
    if len(comparisons) != len(terms):
        return None
    return {comparison.attr_path.attr: comparison.value for comparison in comparisons}


def _snapshot(
    resource: Resource[Any], paths: list[Path[Any]], memo: dict[int, Any]
) -> Resource[Any]:
    """Copy the attributes an operation may change, and share the others.

    The memo maps each object to its copy, which pairs each entry of a multi-
    valued attribute with its earlier state. When no path reaches into the
    entries of a multi-valued attribute, through a filter or a sub-attribute,
    entries can only be added or removed, so they are shared instead of copied.
    """
    reached: dict[str, bool] = {}
    for path in paths:
        binding = None if path.model is not None else path.resolve()
        model = path.model if binding is None else binding.model
        if model is None or model is type(resource):
            if binding is not None:
                reaches = binding.sub_field_name is not None or bool(path.value_filter)
                name = binding.field_name
                reached[name] = reached.get(name, False) or reaches
        else:
            reached[model.__name__] = True

    before = copy.copy(resource)
    for name, reaches in reached.items():
        value = getattr(resource, name)
        if isinstance(value, list) and not reaches:
            memo.update({id(entry): entry for entry in value})
            before.__dict__[name] = list(value)
        else:
            before.__dict__[name] = copy.deepcopy(value, memo)
    return before


def _settle(before: Any, after: Any, memo: dict[int, Any]) -> None:
    """Compare the state after an operation with the state before it.

    Each attribute is compared with its earlier value, and each entry of a
    multi-valued attribute with its earlier state, as the memo pairs them. Per
    RFC7644 §3.5.2, a read-only attribute cannot change, an immutable one
    cannot change once assigned, and a required one cannot become unassigned.
    Removing an extension or a complex attribute may remove its read-only and
    required attributes, but not its assigned immutable ones. A value marked
    primary unmarks the others.
    """
    if before is after:
        return
    removed = after is None
    model = type(before if removed else after)
    for field_name in model.model_fields:
        old = getattr(before, field_name, None)
        new = getattr(after, field_name, None)
        if _same(old, new):
            continue

        name = model._scim_name(field_name)
        mutability = model.get_field_annotation(field_name, Mutability)
        if mutability == Mutability.immutable and _assigned(old):
            raise MutabilityException(attribute=name, detail=f"'{name}' is immutable")
        if not removed and mutability == Mutability.read_only:
            raise MutabilityException(attribute=name, detail=f"'{name}' is read-only")
        if (
            not removed
            and model.get_field_annotation(field_name, Required) == Required.true
            and _assigned(old)
            and not _assigned(new)
        ):
            raise MutabilityException(
                attribute=name, detail=f"required attribute '{name}' became unassigned"
            )

        for old_value, new_value in _counterparts(old, new, memo):
            _settle(old_value, new_value, memo)
        if isinstance(new, list):
            _settle_primary(new, memo)


def _counterparts(old: Any, new: Any, memo: dict[int, Any]) -> list[tuple[Any, Any]]:
    """Pair the objects an attribute holds with their earlier state.

    Entries of a multi-valued attribute have no identity other than the object,
    so a removed entry is not visited, and an added entry has no pair.
    """
    if isinstance(new, list):
        return [
            (memo.get(id(entry)), entry)
            for entry in new
            if isinstance(entry, BaseModel)
        ]
    if isinstance(old, BaseModel) or isinstance(new, BaseModel):
        return [(old, new)]
    return []


def _settle_primary(entries: list[Any], memo: dict[int, Any]) -> None:
    """Keep the value just marked primary as the only primary one.

    Per RFC7644 §3.5.2, a value marked primary unmarks the others, and per
    RFC7643 §2.4, only one value can be primary.
    """
    primary = [
        entry
        for entry in entries
        if "primary" in getattr(type(entry), "model_fields", {})
        and entry.primary is True
    ]
    marked = [
        entry
        for entry in primary
        if getattr(memo.get(id(entry)), "primary", None) is not True
    ]
    if len(marked) > 1:
        raise InvalidValueException(detail="Multiple values marked as primary")
    if not marked and len(primary) > 1:
        raise InvalidValueException(detail="Multiple primary values already exist")
    for entry in primary:
        if marked and entry is not marked[0]:
            entry.primary = False


def _same(old: Any, new: Any) -> bool:
    """Whether a value is unchanged, the order of entries aside (RFC7643 §2.4)."""
    if old == new:
        return True
    if not (isinstance(old, list) and isinstance(new, list)) or len(old) != len(new):
        return False
    return bool(_comparable(old) == _comparable(new))


def _comparable(value: Any, include: set[str] | None = None) -> Any:
    """Reduce a value to a form that compares equal regardless of entry order."""
    if isinstance(value, list):
        return sorted((_comparable(item, include) for item in value), key=repr)
    if isinstance(value, BaseModel):
        return value.model_dump(include=include)
    return value


def _assigned(value: Any) -> bool:
    """Whether a value is assigned, as RFC7643 §2.5 defines it."""
    if isinstance(value, BaseModel):
        return any(_assigned(getattr(value, name)) for name in type(value).model_fields)
    return value is not None and value != []


def _restore(resource: BaseModel, snapshot: BaseModel) -> None:
    """Restore a resource from a copy, keeping the same object."""
    for attribute in ("__dict__", "__pydantic_fields_set__", "__pydantic_private__"):
        object.__setattr__(resource, attribute, getattr(snapshot, attribute))


def _differences(
    before: Any, after: BaseModel, prefix: str
) -> Iterator[tuple[PatchOperation.Op, str, Any]]:
    """Yield the operations that set the attributes of the wanted state.

    A complex attribute or an extension is compared attribute by attribute. A
    multi-valued attribute is compared on the sub-attributes its wanted entries
    name.
    """
    model = type(after)
    for field_name in model.model_fields:
        mutability = model.get_field_annotation(field_name, Mutability)
        if (
            field_name not in after.model_fields_set
            or field_name == "schemas"
            or mutability == Mutability.read_only
        ):
            continue

        old = getattr(before, field_name, None)
        new = getattr(after, field_name)
        path = f"{prefix}{model._scim_name(field_name)}"
        include = _named_sub_attributes(new)
        if isinstance(new, BaseModel):
            separator = ":" if field_name in model.__scim_info__.extensions else "."
            yield from _differences(old, new, path + separator)
        elif not _assigned(new):
            if _assigned(old):
                yield PatchOperation.Op.remove, path, None
        elif _comparable(old, include) != _comparable(new, include):
            op = (
                PatchOperation.Op.add
                if mutability == Mutability.immutable and old is None
                else PatchOperation.Op.replace_
            )
            yield op, path, new


def _named_sub_attributes(value: Any) -> set[str] | None:
    """Return the sub-attributes the entries of a wanted collection name."""
    if not isinstance(value, list):
        return None
    return {
        name
        for entry in value
        if isinstance(entry, BaseModel)
        for name in entry.model_fields_set
    }
