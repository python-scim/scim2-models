from collections.abc import Iterator
from enum import Enum
from inspect import isclass
from typing import Annotated
from typing import Any
from typing import Generic
from typing import TypeVar
from typing import cast
from typing import get_origin

from pydantic import BaseModel as PydanticBaseModel
from pydantic import Field
from pydantic import ValidationInfo
from pydantic import field_validator
from pydantic import model_validator
from typing_extensions import Self

from ..annotations import Mutability
from ..annotations import Required
from ..attributes import ComplexAttribute
from ..base import BaseModel
from ..context import Context
from ..exceptions import InvalidValueException
from ..exceptions import MutabilityException
from ..exceptions import NoTargetException
from ..exceptions import PathNotFoundException
from ..path import Path
from ..path import ScimFilter
from ..path import attribute_host
from ..policy import ScimPolicy
from ..policy import _effective_policy
from ..policy import _policy
from ..resources.resource import Resource
from ..urn import URN
from ..utils import UNION_TYPES
from ..utils import _find_field_name
from .message import Message
from .message import _get_resource_class
from .message import _ResourceParameterized

ResourceT = TypeVar("ResourceT", bound=Resource[Any])


def _commit(resource: Any, working: Any) -> None:
    """Write a patched copy back onto the resource the caller holds.

    Assignment is bypassed on purpose: ``working`` was built by the very passes
    ``validate_assignment`` would run again.
    """
    resource.__dict__.clear()
    resource.__dict__.update(working.__dict__)
    resource.__pydantic_fields_set__.clear()
    resource.__pydantic_fields_set__.update(working.__pydantic_fields_set__)
    resource.__pydantic_private__ = working.__pydantic_private__


def _targeted_attributes(value: Any) -> dict[str, Any]:
    """Return the attributes an operation without a path writes.

    RFC7644 §3.5.2.3 has the ``value`` name them when the path is omitted. A
    client building its payload in Python passes a resource, where a server
    parses a mapping, and both name the same attributes. Anything else names
    none.
    """
    if isinstance(value, BaseModel):
        # Dumped out of context on purpose: a payload dumped in the PATCH
        # context already leaves read-only attributes out, and an operation
        # naming one is to be refused rather than quietly trimmed.
        return value.model_dump(exclude_unset=True)
    return value if isinstance(value, dict) else {}


def _resolved_field(resource_class: type[BaseModel], attr_name: str) -> str | None:
    """Return the Python field a SCIM attribute name designates.

    Attribute names are case-insensitive per RFC7643 §2.1 and differ from the
    field names of the model, so the constraint checks resolve the name instead
    of matching it against ``model_fields``.
    """
    return _find_field_name(resource_class, attr_name)


_ENVELOPE_FIELDS = frozenset({"schemas"})
"""Fields that carry the payload rather than the state it describes."""


def _asserted_sub_attributes(entries: Any) -> set[str]:
    """Return the sub-attributes the entries of a wanted state name."""
    asserted: set[str] = set()
    for entry in entries or []:
        if isinstance(entry, BaseModel):
            asserted |= entry.model_fields_set
    return asserted


def _projection(entries: Any, asserted: set[str]) -> list[Any]:
    """Reduce the entries of a multi-valued attribute to what is worth comparing.

    RFC7643 §2.4 gives no significance to the order of a multi-valued
    attribute, so the projections are sorted before comparison.
    """
    projected = [
        tuple(sorted((name, getattr(entry, name, None)) for name in asserted))
        if isinstance(entry, BaseModel)
        else entry
        for entry in entries or []
    ]
    return sorted(projected, key=repr)


def _operation(
    path: str, old: Any, new: Any, mutability: Mutability | None
) -> tuple["PatchOperation.Op", str, Any]:
    """Return the operation writing *new* where the current state holds *old*.

    Called once a difference is established. RFC7644 §3.5.2.3 has a service
    provider treat a ``replace`` on an unset target as an ``add``, so a single
    operation covers both. An immutable attribute is the exception: RFC7644
    §3.5.2 lets a client add a value to one that had none, and nothing else.
    """
    if mutability == Mutability.immutable:
        if old is not None:
            raise MutabilityException(
                attribute=path, mutability="immutable", operation="replace"
            )
        return PatchOperation.Op.add, path, new

    if new is None or new == []:
        return PatchOperation.Op.remove, path, None

    return PatchOperation.Op.replace_, path, new


def _diff_multi_valued(
    path: str, old: Any, new: Any, mutability: Mutability | None
) -> Iterator[tuple["PatchOperation.Op", str, Any]]:
    """Diff a multi-valued attribute, which is replaced as a whole.

    Only the sub-attributes the wanted entries name take part in the
    comparison, so the sub-attributes the peer alone maintains do not read as a
    difference. When the collection does change it is replaced entirely:
    RFC7643 §2.4 gives the entries no identity, so an entry that changed cannot
    be told from a removed one and an added one.
    """
    asserted = _asserted_sub_attributes(new)
    if _projection(old, asserted) == _projection(new, asserted):
        return

    yield _operation(path, old, new, mutability)


def _diff_sub_object(
    prefix: str,
    path: str,
    old: Any,
    new: Any,
    mutability: Mutability | None,
) -> Iterator[tuple["PatchOperation.Op", str, Any]]:
    """Diff a complex attribute or an extension, one sub-attribute at a time."""
    if new is not None:
        yield from _diff(old, new, prefix)
        return

    if old is not None:
        yield _operation(path, old, None, mutability)


def _diff(
    before: Any, after: Any, prefix: str = ""
) -> Iterator[tuple["PatchOperation.Op", str, Any]]:
    """Yield the operations turning *before* into *after*.

    Only the attributes *after* names are candidates: what a wanted state never
    mentions is left to the peer. Attributes are visited in declaration order,
    so a diff is reproducible.
    """
    model = type(after)
    info = model.__scim_info__
    for field_name in model.model_fields:
        if field_name not in after.model_fields_set:
            continue

        if field_name in _ENVELOPE_FIELDS:
            continue

        mutability = model.get_field_annotation(field_name, Mutability)
        if mutability == Mutability.read_only:
            continue

        old = getattr(before, field_name, None) if before is not None else None
        new = getattr(after, field_name, None)
        path = f"{prefix}{model._scim_name(field_name)}"

        if model.get_field_multiplicity(field_name):
            yield from _diff_multi_valued(path, old, new, mutability)

        elif field_name in info.extensions:
            urn = info.attribute_urns[field_name]
            yield from _diff_sub_object(f"{urn}:", urn, old, new, mutability)

        elif field_name in info.complex_fields:
            yield from _diff_sub_object(f"{path}.", path, old, new, mutability)

        elif old != new:
            yield _operation(path, old, new, mutability)


class PatchOperation(ComplexAttribute, Generic[ResourceT]):
    class Op(str, Enum):
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

    def _validate_mutability(
        self, resource_class: type[BaseModel], field_name: str
    ) -> None:
        """Validate mutability constraints at parse-time.

        Only scim2_models.Mutability.read_only is validated here.
        scim2_models.Mutability.immutable validation requires access to the
        resource instance and is enforced at runtime in
        PatchOp._check_immutable.
        """
        mutability = resource_class.get_field_annotation(field_name, Mutability)

        if mutability == Mutability.read_only:
            raise MutabilityException(
                attribute=field_name, mutability="readOnly", operation=self.op.value
            ).as_pydantic_error()

    def _validate_required_attribute(
        self,
        resource_class: type[BaseModel],
        field_name: str,
        written: Any = None,
    ) -> None:
        """Refuse an operation that would leave a required attribute unassigned.

        ``written`` is the value the operation writes to that attribute, which
        an operation without a path takes from its ``value``.
        """
        # RFC7643 §2.5 makes a null value, an empty array and an unassigned
        # attribute equivalent in state, so writing one of those unassigns the
        # attribute as surely as a remove does.
        if self.op == PatchOperation.Op.remove:
            detail = "required attribute cannot be removed"
        elif self.op in (
            PatchOperation.Op.replace_,
            PatchOperation.Op.add,
        ) and written in (None, []):
            detail = "required attribute cannot be unassigned"
        else:
            return

        required = resource_class.get_field_annotation(field_name, Required)

        # RFC7644 §3.5.2.2 has a server answer "mutability" when a required
        # attribute is removed or becomes unassigned.
        if required == Required.true:
            raise MutabilityException(
                detail=detail, attribute=field_name, operation=self.op.value
            ).as_pydantic_error()

    @model_validator(mode="after")
    def _validate_operation_requirements(self, info: ValidationInfo) -> Self:
        """Validate operation requirements according to RFC 7644."""
        # Only validate in PATCH request context
        scim_ctx = info.context.get("scim") if info.context else None
        if scim_ctx != Context.RESOURCE_PATCH_REQUEST:
            return self

        # RFC 7644 Section 3.5.2.2: "If 'path' is unspecified, the operation
        # fails with HTTP status code 400 and a 'scimType' error of 'noTarget'"
        if self.path is None and self.op == PatchOperation.Op.remove:
            raise NoTargetException(
                detail="Remove operation requires a path"
            ).as_pydantic_error()

        # RFC 7644 Section 3.5.2.2 defines a remove by its path alone: the four
        # target locations it lists all read off "path", and a selection is
        # spelled as a filter there. An operation carrying a value is thus
        # incompatible with the schema of the attribute it targets, which
        # Section 3.5.2 answers with an error.
        if (
            self.op == PatchOperation.Op.remove
            and self.value is not None
            and _policy(info).remove_value_as_filter != ScimPolicy.RemoveValue.apply
        ):
            raise InvalidValueException(
                detail="a remove operation carries no value, "
                "a filter in the path selects what to remove"
            ).as_pydantic_error()

        # RFC 7644 Section 3.5.2.1: "Value is required for add operations"
        if self.op == PatchOperation.Op.add and self.value is None:
            raise InvalidValueException(
                detail="value is required for add operations"
            ).as_pydantic_error()

        return self

    value: Any | None = None

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
            return v.lower()
        return v


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
        Field(None, serialization_alias="Operations", min_length=1)
    )
    """The body of an HTTP PATCH request MUST contain the attribute
    "Operations", whose value is an array of one or more PATCH operations."""

    @model_validator(mode="after")
    def _validate_operations(self, info: ValidationInfo) -> Self:
        """Validate operations against resource type metadata if available.

        When PatchOp is used with a specific resource type (e.g.,
        PatchOp[User]), this validator will automatically check mutability and
        required constraints.
        """
        # RFC 7644: The body of an HTTP PATCH request MUST contain the attribute "Operations"
        scim_ctx = info.context.get("scim") if info.context else None
        if scim_ctx == Context.RESOURCE_PATCH_REQUEST and self.operations is None:
            raise InvalidValueException(
                detail="operations attribute is required"
            ).as_pydantic_error()

        resource_class = _get_resource_class(self)
        if resource_class is None or not self.operations:
            return self

        for operation in self.operations:
            if operation.path is None:
                # §3.5.2.1 and §3.5.2.3: "If the path parameter is omitted, the
                # target is assumed to be the resource itself", the value naming
                # the attributes to write. Each of them is a target of its own,
                # and answers to §3.5.2 as a named path does.
                for attr_name, written in _targeted_attributes(operation.value).items():
                    field_name = _resolved_field(resource_class, attr_name)
                    if field_name is None:
                        # §3.5.2 has an operation that is not compatible with an
                        # attribute's schema return an error, and §3.12 defines
                        # invalidValue for a value "not compatible with [...] the
                        # resource schema". There is no path here to call invalid.
                        raise InvalidValueException(
                            detail=f"attribute '{attr_name}' is not declared by the resource schema"
                        ).as_pydantic_error()
                    operation._validate_mutability(resource_class, field_name)
                    operation._validate_required_attribute(
                        resource_class, field_name, written
                    )
                continue

            # The attribute a qualified path applies to is declared by the
            # extension the URN designates, not by the resource, so the checks
            # resolve the path instead of reading its first segment. They read
            # the attribute the path applies to rather than the sub-attribute it
            # targets, as a constraint on a complex attribute governs everything
            # written under it: "meta" is read-only where "meta.version" is not.
            if (resolved := operation.path.resolve()) is None:
                if operation.path.model is None:
                    raise PathNotFoundException(
                        path=str(operation.path),
                        detail=f"path '{operation.path}' is not declared by the resource schema",
                    ).as_pydantic_error()
                continue
            operation._validate_mutability(resolved.model, resolved.field_name)
            operation._validate_required_attribute(
                resolved.model, resolved.field_name, operation.value
            )

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
        path_class = Path.__class_getitem__(model)
        operations = [
            operation_class(op=op, path=path_class(path), value=value)
            for op, path, value in _diff(before, after)
        ]
        if not operations:
            return None

        patch_class = PatchOp.__class_getitem__(model)
        return cast("PatchOp[ResourceT]", patch_class(operations=operations))

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
        holds are replaced, so a reference taken on one of them beforehand no
        longer reflects the resource.

        :param resource: The SCIM resource to patch. This object is modified in-place.
        :param scim_policy: The :class:`~scim2_models.ScimPolicy` the patch is
            applied under. Defaults to the strict reading of the specification.
        :return: True if the resource was modified by any operation, False otherwise.
        :raises InvalidValueException: If multiple values are marked as primary in a single
            operation, or if multiple primary values already exist before the patch.
        """
        if not self.operations:
            return False

        modified = False
        # §3.5.2 has a failing operation leave the resource as it was, and an
        # operation only fails once tried: a filter selecting nothing is known
        # from the state, not from the payload.
        working = resource.model_copy(deep=True)

        # The policy is made ambient for the whole application: the passes it
        # governs below are revalidations that start from no call of ours.
        with _effective_policy(scim_policy):
            # RFC 7644 Section 3.5.2: "Apply each operation in sequence"
            for operation in self.operations:
                if self._apply_operation(working, operation):
                    modified = True

        _commit(resource, working)
        return modified

    def _apply_operation(
        self, resource: Resource[Any], operation: PatchOperation[ResourceT]
    ) -> bool:
        """Apply a single patch operation, and say whether the resource changed.

        An operation modifying an immutable attribute raises
        MutabilityException.
        """
        if operation.path is not None:
            self._check_immutable(resource, operation)

        if operation.op in (PatchOperation.Op.add, PatchOperation.Op.replace_):
            return self._apply_add_replace(resource, operation)
        if operation.op == PatchOperation.Op.remove:
            return self._apply_remove(resource, operation)

        raise InvalidValueException(detail=f"unsupported operation: {operation.op}")

    def _check_immutable(
        self, resource: Resource[Any], operation: PatchOperation[ResourceT]
    ) -> None:
        """Validate immutable constraints at runtime.

        RFC 7644 §3.5.2:

            *"A client MUST NOT modify an attribute that has mutability
            "readOnly" or "immutable".  However, a client MAY "add" a value
            to an "immutable" attribute if the attribute had no previous
            value."*

        An operation is considered a no-op (and thus allowed) when it would not
        effectively change the resource state: ``remove`` on an unset field, or
        ``replace`` with the current value.
        """
        assert operation.path is not None
        if (resolved := operation.path.resolve()) is None:
            return
        field_name = resolved.field_name

        mutability = resolved.model.get_field_annotation(field_name, Mutability)
        if mutability != Mutability.immutable:
            return

        host = attribute_host(resource, resolved)
        current_value = getattr(host, field_name, None)

        if operation.op == PatchOperation.Op.add and current_value is None:
            return

        if operation.op == PatchOperation.Op.remove and current_value is None:
            return

        if (
            operation.op == PatchOperation.Op.replace_
            and operation.value == current_value
        ):
            return

        raise MutabilityException(
            attribute=field_name,
            mutability="immutable",
            operation=operation.op.value,
        )

    def _apply_add_replace(
        self, resource: Resource[Any], operation: PatchOperation[ResourceT]
    ) -> bool:
        """Apply an add or replace operation."""
        before_state = self._capture_primary_state(resource)

        value = operation.value
        if operation.path is None and isinstance(value, BaseModel):
            # Path("").set writes the attributes a mapping names, so a resource
            # given as a value is dumped to the payload it stands for, and to
            # the very attributes the operation was checked against.
            value = _targeted_attributes(value)

        path = operation.path if operation.path is not None else Path("")
        modified = path.set(
            resource,  # type: ignore[arg-type]
            value,
            is_add=operation.op == PatchOperation.Op.add,
        )

        if modified:
            self._normalize_primary_after_patch(resource, before_state)

        return modified

    def _capture_primary_state(self, resource: Resource[Any]) -> dict[str, set[int]]:
        """Capture indices of elements with primary=True for each multi-valued attribute."""
        state: dict[str, set[int]] = {}
        for field_name in type(resource).model_fields:
            if not resource.get_field_multiplicity(field_name):
                continue

            field_value = getattr(resource, field_name, None)
            if not field_value:
                continue

            element_type = resource.get_field_root_type(field_name)
            if (
                not element_type
                or not isclass(element_type)
                or not issubclass(element_type, PydanticBaseModel)
                or "primary" not in element_type.model_fields
            ):
                continue

            primary_indices = {
                i
                for i, item in enumerate(field_value)
                if getattr(item, "primary", None) is True
            }
            state[field_name] = primary_indices

        return state

    def _normalize_primary_after_patch(
        self, resource: Resource[Any], before_state: dict[str, set[int]]
    ) -> None:
        """Normalize primary attributes after a patch operation.

        Per RFC 7644 §3.5.2: a PATCH operation that sets a value's "primary"
        sub-attribute to "true" SHALL cause the server to automatically set
        "primary" to "false" for any other values.
        """
        for field_name in type(resource).model_fields:
            if not resource.get_field_multiplicity(field_name):
                continue

            field_value = getattr(resource, field_name, None)
            if not field_value:
                continue

            element_type = resource.get_field_root_type(field_name)
            if (
                not element_type
                or not isclass(element_type)
                or not issubclass(element_type, PydanticBaseModel)
                or "primary" not in element_type.model_fields
            ):
                continue

            current_primary_indices = {
                i
                for i, item in enumerate(field_value)
                if getattr(item, "primary", None) is True
            }

            if len(current_primary_indices) <= 1:
                continue

            before_primaries = before_state.get(field_name, set())
            new_primaries = current_primary_indices - before_primaries

            if len(new_primaries) > 1:
                raise InvalidValueException(
                    detail=f"Multiple values marked as primary in field '{field_name}'"
                )

            if not new_primaries:
                raise InvalidValueException(
                    detail=f"Multiple primary values already exist in field '{field_name}'"
                )

            keep_index = next(iter(new_primaries))
            for i in current_primary_indices:
                if i != keep_index:
                    field_value[i].primary = False

    def _apply_remove(
        self, resource: Resource[Any], operation: PatchOperation[ResourceT]
    ) -> bool:
        """Apply a remove operation."""
        if operation.path is None:
            raise NoTargetException(detail="Remove operation requires a path")

        # Checked again here, a PatchOp built in Python reaching no validator.
        if operation.value is not None:
            if (
                _effective_policy().remove_value_as_filter
                != ScimPolicy.RemoveValue.apply
            ):
                raise InvalidValueException(
                    detail="a remove operation carries no value, "
                    "a filter in the path selects what to remove"
                )
            return self._remove_selected_values(
                resource, operation.path, operation.value
            )

        return operation.path.delete(resource)  # type: ignore[arg-type]

    def _remove_selected_values(
        self, resource: Resource[Any], path: Path[ResourceT], value: Any
    ) -> bool:
        """Remove the entries the value of a remove operation selects.

        Microsoft Entra puts the selection in ``value`` where RFC7644 §3.5.2.2
        puts it in ``path``. Each entry becomes a filter on the sub-attributes
        it names, which is the path the operation should have carried.
        """
        if path.value_filter is not None:
            raise InvalidValueException(
                detail="a remove operation carrying a value cannot also "
                "select values in its path"
            )

        entries = value if isinstance(value, list) else [value]
        if not all(isinstance(entry, dict) and entry for entry in entries):
            raise InvalidValueException(
                detail="the value of a remove operation names the "
                "sub-attributes selecting what to remove"
            )

        removed = False
        for entry in entries:
            conditions = " and ".join(
                f"{name} eq {ScimFilter.quote(item)}" for name, item in entry.items()
            )
            # Subscripted through the call the syntax stands for: mypy reads
            # the index of a generic as a type, not as a value.
            selection = Path.__class_getitem__(type(resource))(f"{path}[{conditions}]")
            removed = selection.delete(resource) or removed
        return removed
