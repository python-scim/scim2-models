from inspect import isclass
from typing import TYPE_CHECKING
from typing import Any
from typing import NamedTuple
from typing import cast
from typing import get_args
from typing import get_origin

from .base import BaseModel
from .exceptions import InvalidPathException
from .exceptions import NoTargetException
from .exceptions import PathNotFoundException
from .filters.filter import validate_value_filter
from .filters.visitor import Evaluator
from .resolution import _target_model
from .resolution import attribute_host
from .resolution import designated_model
from .resolution import resolve_attr_path
from .resolution import validate_value_selection
from .utils import UNION_TYPES
from .utils import _find_field_name

if TYPE_CHECKING:
    from .path import Path


def _accepts_none(model: type[BaseModel], field_name: str) -> bool:
    """Whether the annotation of a field allows :data:`None`."""
    annotation = model.model_fields[field_name].annotation
    return get_origin(annotation) in UNION_TYPES and type(None) in get_args(annotation)


def _to_comparable(value: Any) -> Any:
    """Convert a value to a comparable form (dict for BaseModel)."""
    return value.model_dump() if isinstance(value, BaseModel) else value


def _values_match(value1: Any, value2: Any) -> bool:
    """Check if two values match, handling BaseModel comparison."""
    return bool(_to_comparable(value1) == _to_comparable(value2))


def _value_in_list(current_list: list[Any], new_value: Any) -> bool:
    """Check if a value exists in a list, handling BaseModel comparison."""
    return any(_values_match(item, new_value) for item in current_list)


def _require_field(model: type[BaseModel], name: str, path: str) -> str:
    """Return the field a path segment names, or report it as missing."""
    if (field_name := _find_field_name(model, name)) is None:
        raise PathNotFoundException(path=path, field=name)
    return field_name


class _Root(NamedTuple):
    """The path designates the object itself rather than one of its attributes.

    ``explicit`` tells a bare schema URN from the empty path: both land on the
    object, but only the former spells it out, and a write of anything but a
    mapping through it is a mistake to report rather than a no-op.
    """

    explicit: bool


class _Target(NamedTuple):
    """The objects a path lands on, and the field it designates on each.

    A path crossing a multi-valued attribute designates one field per entry, so
    ``emails.value`` lands on every email rather than on a single object.
    """

    hosts: list["BaseModel"]
    field_name: str
    multivalued: bool


class _Selection(NamedTuple):
    """The entries a value-selecting path matched, and where they live.

    ``sub_attr`` is the attribute targeted past the brackets, which
    :rfc:`RFC7644 §3.5.2 <7644#section-3.5.2>` allows a PATCH path to name.
    """

    host: Any
    field_name: str
    matched: list[Any]
    sub_attr: str | None


def _walk(
    path: "Path[Any]", resource: BaseModel, *, create: bool = False
) -> "_Root | _Target | None":
    """Locate the objects holding the attribute a path designates.

    The path is resolved against the type of the resource rather than the
    model it is bound to, so an unbound path reads and writes like a bound
    one, and a path bound to a union answers for the type it is applied to.
    A path crossing a multi-valued attribute fans out over its entries, as
    :rfc:`RFC7644 §3.5.2 <7644#section-3.5.2>` has an unfiltered path
    designate every one of them.

    :param resource: The object to walk from.
    :param create: Whether an unassigned extension or complex attribute is
        instantiated rather than ending the walk. Nothing is created for a
        path that resolves to nothing.
    :returns: The root when the path designates the resource itself, the
        target otherwise, or :data:`None` when nothing is left to walk to.
    :raises InvalidPathException: If the path is qualified by a URN that
        designates neither the resource nor one of its extensions.
    :raises PathNotFoundException: If the path names an attribute the model
        does not declare, or a sub-attribute of one that has none.
    """
    from .resources.resource import Resource

    if path.ast is None:
        return _Root(explicit=False)

    model = type(resource)
    if (designated := designated_model(model, str(path))) is not None:
        if isinstance(resource, designated):
            return _Root(explicit=True)
        return _Target([resource], designated.__name__, False)

    attr_path = path._designated_attr_path()
    assert attr_path is not None

    # A URN that designates no model the resource declares is refused on a
    # resource, and reaches nothing on an object handled on its own.
    if attr_path.uri and _target_model(model, attr_path, strict=False) is None:
        if isinstance(resource, Resource):
            raise InvalidPathException(path=str(path))
        return None

    resolved = resolve_attr_path(model, attr_path, strict=True)
    assert resolved is not None

    host = attribute_host(resource, resolved)
    if host is None:
        if not create:
            return None
        host = resolved.model()
        setattr(resource, resolved.model.__name__, host)

    if resolved.sub_field_name is None:
        return _Target([host], resolved.field_name, False)

    head = getattr(host, resolved.field_name)
    if head is None and create:
        head = _create_intermediate(host, resolved.field_name)
    if head is None:
        return None
    if isinstance(head, list):
        return _Target(list(head), resolved.sub_field_name, True) if head else None
    return _Target([head], resolved.sub_field_name, False)


def _create_intermediate(host: BaseModel, field_name: str) -> BaseModel | None:
    """Instantiate an unassigned complex attribute so a value can be set under it.

    The walk has already established that the attribute is complex, so only
    a multi-valued one is left alone: entries that do not exist have no
    field to write to, and inventing one would guess what the caller meant
    to address.
    """
    if type(host).get_field_multiplicity(field_name):
        return None
    field_type = cast("type[BaseModel]", type(host).get_field_root_type(field_name))
    sub_obj = field_type()
    setattr(host, field_name, sub_obj)
    return sub_obj


def _select(path: "Path[Any]", resource: BaseModel) -> "_Selection | None":
    """Resolve a value-selecting path against a resource.

    The filter between the brackets is evaluated strictly, so an attribute
    the model does not declare is reported rather than silently matching
    nothing. Tolerance belongs to :meth:`get`, :meth:`set` and
    :meth:`delete`, which swallow the failure when asked to.

    :returns: The object holding the attribute, the Python field name, and
        the matching entries, or :data:`None` if this is not a
        value-selecting path.
    :raises PathNotFoundException: If the selected attribute is unknown.
    :raises InvalidFilterException: If the filter between the brackets
        names an attribute the selected model does not declare.
    """
    value_path = path._as_value_path()
    if value_path is None:
        return None

    model = type(resource)
    resolved = resolve_attr_path(model, value_path.attr_path, strict=False)
    if resolved is None:
        raise PathNotFoundException(path=str(path), field=value_path.attr_path.attr)

    # Checked before reading the resource, so that a selection that cannot
    # apply is rejected whether or not the attribute happens to be set.
    validate_value_selection(resolved)
    validate_value_filter(resolved, value_path.val_filter)

    host = attribute_host(resource, resolved)
    if host is None:
        return _Selection(None, resolved.field_name, [], value_path.sub_attr)

    matched = Evaluator(model, resource).select(value_path)
    return _Selection(host, resolved.field_name, matched, value_path.sub_attr)


def get_value(path: "Path[Any]", resource: BaseModel) -> Any:
    """Read the value a path designates on a resource."""
    if (selection := _select(path, resource)) is not None:
        if selection.sub_attr is None:
            return selection.matched or None
        values = [
            getattr(
                item,
                _require_field(type(item), selection.sub_attr, str(path)),
                None,
            )
            for item in selection.matched
            if isinstance(item, BaseModel)
        ]
        return values or None

    target = _walk(path, resource)
    if target is None:
        return None
    if isinstance(target, _Root):
        return resource

    values = [getattr(host, target.field_name) for host in target.hosts]
    return values if target.multivalued else values[0]


def _set_selected(
    path: "Path[Any]", selection: "_Selection", value: Any, *, is_add: bool = False
) -> bool:
    """Apply a value to every entry matched by a value selection.

    :raises NoTargetException: If a replacement selection matches nothing,
        per :rfc:`RFC7644 §3.5.2.3 <7644#section-3.5.2.3>`. That failure is
        defined for ``replace`` only: :rfc:`§3.5.2.1 <7644#section-3.5.2.1>`
        says nothing of a selection that matches nothing for ``add``, so
        the operation is a no-op instead. `Errata 8097
        <https://www.rfc-editor.org/errata/eid8097>`_ asks for value
        selections in ``add`` to be clarified at all, implementations
        differing on whether they are allowed.
    """
    host, field_name, matched, sub_attr = selection

    if not matched:
        if is_add:
            return False
        raise NoTargetException(
            detail=f"no value of '{field_name}' matches the path filter"
        )

    if sub_attr is None:
        # Without a sub-attribute the matched entries are replaced wholesale.
        current = getattr(host, field_name)
        replacement = list(current)
        item_type = type(host).get_field_root_type(field_name)
        new_value = (
            item_type.model_validate(value)
            if isinstance(value, dict)
            and isclass(item_type)
            and issubclass(item_type, BaseModel)
            else value
        )
        modified = False
        for index, item in enumerate(replacement):
            if any(item is candidate for candidate in matched):
                if not _values_match(item, new_value):
                    replacement[index] = new_value
                    modified = True
        if modified:
            setattr(host, field_name, replacement)
        return modified

    modified = False
    for item in matched:
        item_field = _require_field(type(item), sub_attr, str(path))
        if getattr(item, item_field) != value:
            setattr(item, item_field, value)
            modified = True
    return modified


def _delete_selected(path: "Path[Any]", selection: "_Selection") -> bool:
    """Remove every entry matched by a value selection.

    A selection that matches nothing leaves the resource untouched and
    succeeds: :rfc:`RFC7644 §3.5.2.2 <7644#section-3.5.2.2>` requires
    ``noTarget`` only for a missing ``path``, and its removal example
    states that "if the user was not a member of this group, no changes
    should be made to the resource, and a success response should be
    returned".
    """
    host, field_name, matched, sub_attr = selection

    if not matched:
        return False

    if sub_attr is not None:
        modified = False
        for item in matched:
            item_field = _require_field(type(item), sub_attr, str(path))
            if getattr(item, item_field) is not None:
                setattr(item, item_field, None)
                modified = True
        return modified

    remaining = [
        item
        for item in getattr(host, field_name)
        if not any(item is candidate for candidate in matched)
    ]
    # An attribute left without any value is unassigned, which RFC7643 §2.5
    # makes an empty list as much as null. "schemas" is the one annotated
    # without None, so it is emptied where the others are unset. Refusing to
    # unassign a required attribute belongs to PatchOp, which answers
    # "mutability" rather than silently leaving a value behind.
    if not remaining and _accepts_none(type(host), field_name):
        setattr(host, field_name, None)
    else:
        setattr(host, field_name, remaining)
    return True


def set_value(
    path: "Path[Any]", resource: BaseModel, value: Any, *, is_add: bool = False
) -> bool:
    """Write a value where a path designates on a resource."""
    if (selection := _select(path, resource)) is not None:
        return _set_selected(path, selection, value, is_add=is_add)

    target = _walk(path, resource, create=True)
    if target is None:
        return False
    if isinstance(target, _Root):
        return _merge(path, resource, value, explicit=target.explicit)

    changed = [
        _set_field_value(host, target.field_name, value, is_add)
        for host in target.hosts
    ]
    return any(changed)


def _merge(path: "Path[Any]", obj: BaseModel, value: Any, *, explicit: bool) -> bool:
    """Write the attributes a mapping names onto the object the path designates.

    :param explicit: Whether the object was designated by its schema URN,
        in which case a value that is not a mapping is reported rather
        than ignored.
    :raises InvalidPathException: If ``explicit`` and the value is not a
        mapping.
    """
    if not isinstance(value, dict):
        if explicit:
            raise InvalidPathException(path=str(path))
        return False
    filtered_value = {
        k: v for k, v in value.items() if _find_field_name(type(obj), k) is not None
    }
    if not filtered_value:
        return False
    old_data = obj.model_dump()
    updated_data = {**old_data, **filtered_value}
    if updated_data == old_data:
        return False
    updated_obj = type(obj).model_validate(updated_data)
    obj.__dict__.update(updated_obj.__dict__)
    obj.__pydantic_fields_set__.update(updated_obj.__pydantic_fields_set__)
    return True


def _set_field_value(obj: BaseModel, field_name: str, value: Any, is_add: bool) -> bool:
    """Set or add a value to a field."""
    is_multivalued = obj.get_field_multiplicity(field_name)

    if is_add and is_multivalued:
        current_list = getattr(obj, field_name) or []
        if isinstance(value, list):
            new_values = [v for v in value if not _value_in_list(current_list, v)]
            if not new_values:
                return False
            setattr(obj, field_name, current_list + new_values)
        else:
            if _value_in_list(current_list, value):
                return False
            setattr(obj, field_name, [*current_list, value])
        return True

    if is_multivalued and not isinstance(value, list) and value is not None:
        value = [value]

    old_value = getattr(obj, field_name)
    if old_value == value:
        return False

    setattr(obj, field_name, value)
    return True


def delete_value(
    path: "Path[Any]", resource: BaseModel, value: Any | None = None
) -> bool:
    """Unassign what a path designates on a resource, or remove a value from it."""
    if (selection := _select(path, resource)) is not None:
        return _delete_selected(path, selection)

    target = _walk(path, resource)
    if target is None:
        return False
    if isinstance(target, _Root):
        raise InvalidPathException(path=str(path))

    changed = [
        _delete_field_value(host, target.field_name, value) for host in target.hosts
    ]
    return any(changed)


def _delete_field_value(
    obj: BaseModel, field_name: str, value: Any | None = None
) -> bool:
    """Unassign a field, or remove the matching entries of a multi-valued one."""
    if (current_value := getattr(obj, field_name)) is None:
        return False

    if value is None:
        setattr(obj, field_name, None)
        return True

    if not isinstance(current_value, list):
        return False

    new_list = [item for item in current_value if not _values_match(item, value)]
    if len(new_list) == len(current_value):
        return False

    setattr(obj, field_name, new_list or None)
    return True
