from collections.abc import Iterable
from collections.abc import Iterator
from collections.abc import MutableMapping
from dataclasses import replace
from inspect import isclass
from typing import TYPE_CHECKING
from typing import Any
from typing import Generic
from typing import NamedTuple
from typing import TypeVar
from typing import cast
from typing import get_args
from typing import get_origin
from weakref import WeakValueDictionary

from pydantic import GetCoreSchemaHandler
from pydantic import GetJsonSchemaHandler
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import core_schema

from .base import BaseModel
from .urn import URN
from .utils import UNION_TYPES
from .utils import _find_field_name
from .utils import _model_union
from .utils import _to_camel

if TYPE_CHECKING:
    from .annotations import CaseExact
    from .annotations import Mutability
    from .annotations import Required
    from .annotations import Returned
    from .annotations import Uniqueness
    from .resources.resource import Resource

from .exceptions import InvalidFilterException
from .exceptions import InvalidPathException
from .exceptions import NoTargetException
from .exceptions import PathNotFoundException
from .expressions import AttrPath
from .expressions import Comparison
from .expressions import FilterNode
from .expressions import PathNode
from .expressions import Present
from .expressions import Template
from .expressions import ValuePath
from .expressions import _Expression
from .expressions import _text
from .filters.filter import validate_value_filter
from .filters.visitor import Evaluator
from .grammar import parse_path
from .resolution import ResolvedAttribute
from .resolution import attribute_host
from .resolution import resolve_attr_path
from .resolution import validate_value_selection

ResourceT = TypeVar("ResourceT", bound="Resource[Any]")

_PATH_CACHE: "MutableMapping[tuple[type, tuple[type, ...]], type]" = (
    WeakValueDictionary()
)
"""The classes subscription has already built, so that two subscriptions of the
same resource types answer the same class.

The classes are held weakly: one bound to a model built at runtime, as a server
serving a schema it discovered does, would otherwise keep that model alive for
as long as the process runs."""


def _is_in_schema(path_lower: str, schema: str) -> bool:
    schema_lower = schema.lower()
    return path_lower == schema_lower or path_lower.startswith(f"{schema_lower}:")


def _designating_schema(path_lower: str, schemas: Iterable[str]) -> str | None:
    """Return the schema a qualified path is expressed in, if any.

    The longest match wins: the URN of an extension may extend the URN of the
    resource it extends, and then both match while only the longer one
    designates the model the attribute lives on.
    """
    matching = [
        schema for schema in schemas if schema and _is_in_schema(path_lower, schema)
    ]
    return max(matching, key=len) if matching else None


def _node_attr_path(node: PathNode) -> AttrPath:
    """Return the attribute path a parsed path node applies to."""
    if isinstance(node, AttrPath):
        return node
    return node.attr_path


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


def _scim_name(model: type[BaseModel], field_name: str) -> str:
    """Return the name a field is serialized under, ``$ref`` included."""
    return model.model_fields[field_name].serialization_alias or _to_camel(field_name)


def _resolve_field_names(
    model: type[BaseModel], parts: list[str], path: str
) -> list[str]:
    """Resolve each segment of a dotted path to the field name it designates.

    The segments are resolved against the declared types rather than against
    the values a resource happens to carry, so a path naming an attribute the
    model does not declare is reported the same way whether or not the
    attributes leading to it are assigned.

    :raises PathNotFoundException: If a segment names an unknown field, or if a
        segment other than the last one names an attribute with no
        sub-attributes to descend into.
    """
    field_names: list[str] = []
    for part, next_part in zip(parts, parts[1:], strict=False):
        field_name = _require_field(model, part, path)
        field_type = model.get_field_root_type(field_name)
        if not (isclass(field_type) and issubclass(field_type, BaseModel)):
            raise PathNotFoundException(path=path, field=next_part)
        field_names.append(field_name)
        model = field_type

    field_names.append(_require_field(model, parts[-1], path))
    return field_names


class _Resolution(NamedTuple):
    """Result of instance path resolution."""

    target: "BaseModel"
    path_str: str
    is_explicit_schema_path: bool = False


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


class Path(_Expression, Generic[ResourceT]):
    __scim_models__: tuple[type[BaseModel], ...] = ()

    _ast: "PathNode | None" = None
    """The parsed path, kept once :attr:`ast` has computed it."""

    def __class_getitem__(cls, model: Any) -> type["Path[Any]"]:
        """Create a Path class bound to a resource type, or to a union of them.

        A union is what an endpoint covering several resource types binds, such
        as the server root of :rfc:`RFC7644 §3.4.2.1 <7644#section-3.4.2.1>`.
        Anything that is not a resource type, a type variable in particular, is
        left to the generic machinery.
        """
        models = _model_union(model)
        if models is None:
            return super().__class_getitem__(model)  # type: ignore[misc,no-any-return]

        cache_key = (cls, models)
        if cache_key in _PATH_CACHE:
            return _PATH_CACHE[cache_key]

        names = ", ".join(each.__name__ for each in models)
        new_class = type(f"Path[{names}]", (cls,), {"__scim_models__": models})
        _PATH_CACHE[cache_key] = new_class
        return new_class

    def _resolving_model(self) -> "type[BaseModel] | None":
        """Return the bound model this path resolves against.

        A path bound to a union resolves against the first type declaring the
        attribute it designates, which is unambiguous as long as the types
        agree on it. The first type stands in when none declares it, so that
        errors name a model.
        """
        if not self.__scim_models__:
            return None

        designated = self._designated_attr_path()
        if designated is None or len(self.__scim_models__) == 1:
            return self.__scim_models__[0]

        for model in self.__scim_models__:
            if resolve_attr_path(model, designated, strict=False) is not None:
                return model
        return self.__scim_models__[0]

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: type[Any],
        _handler: GetCoreSchemaHandler,
    ) -> core_schema.CoreSchema:
        def validate_path(value: Any) -> "Path[Any]":
            if not isinstance(value, str):
                raise ValueError(f"Expected str or Path, got {type(value).__name__}")
            try:
                return cls(str(value))
            except InvalidPathException as exc:
                raise exc.as_pydantic_error() from exc

        return core_schema.no_info_plain_validator_function(
            validate_path,
            serialization=core_schema.plain_serializer_function_ser_schema(str),
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        _core_schema: core_schema.CoreSchema,
        _handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        return {"type": "string"}

    def __new__(cls, path: "str | Path[Any] | Template") -> "Path[Any]":
        text = _text(path)
        cls.check_syntax(text)
        return super().__new__(cls, text)

    @classmethod
    def check_syntax(cls, path: str) -> None:
        """Check that a path conforms to the ``PATH`` rule of :rfc:`RFC7644 §3.5.2 <7644#section-3.5.2>`.

        The grammar is the published ABNF as corrected by
        `errata 7122 <https://www.rfc-editor.org/errata/eid7122>`_, so a path
        is either an attribute path, a value selection optionally followed by a
        sub-attribute, or a bare comparison. An empty string is valid and
        represents the resource root.

        :param path: The path to validate
        :raises InvalidPathException: If the path syntax is invalid
        """
        if not path:
            return

        node = parse_path(path)

        uri = _node_attr_path(node).uri
        if uri is None:
            return

        try:
            URN(uri.lower())
        except ValueError as exc:
            raise InvalidPathException(
                path=path, detail=f"The path is not a valid URN: {exc}"
            ) from exc

    @property
    def ast(self) -> "PathNode | None":
        """The parsed form of the path, or :data:`None` for the resource root.

        >>> from scim2_models import Path
        >>> Path("name.familyName").ast
        AttrPath(attr='name', sub_attr='familyName', uri=None)
        """
        if not self:
            return None
        if self._ast is None:
            self._ast = parse_path(str(self))
        return self._ast

    def check_attribute_notation(self) -> None:
        """Check that the path names an attribute instead of selecting values.

        The attribute notation of :rfc:`RFC7644 §3.10 <7644#section-3.10>` is a
        schema URN, an attribute and at most one of its sub-attributes. A value
        selection or a comparison designates the values an attribute holds
        rather than the attribute itself, so it has no place where a single
        attribute is asked for.

        :raises InvalidPathException: If the path is not in attribute notation.
        """
        if not isinstance(self.ast, AttrPath):
            raise InvalidPathException(
                path=str(self),
                detail=f"{str(self)!r} is not in attribute notation",
            )

    @property
    def schema(self) -> str | None:
        """The schema URN portion of the path.

        For paths like "urn:...:User:userName", returns "urn:...:User".
        For simple paths like "userName", returns None.
        """
        node = self.ast
        return None if node is None else _node_attr_path(node).uri

    def _designated_attr_path(self) -> AttrPath | None:
        """Return the attribute path this path designates, selection excluded.

        A value selection carries its sub-attribute past the brackets, so
        ``emails[type eq "work"].value`` designates ``emails.value``. The
        resource root designates no attribute at all.

        The path is normalised first, so the three spellings errata 7122 offers
        for one selection designate the same attribute: the sub-attribute of
        ``emails.type eq "work"`` belongs to the filter, not to the attribute
        the path operates on.
        """
        if self.ast is None:
            return None

        node = self._as_value_path() or self.ast
        attr_path = _node_attr_path(node)
        sub_attr = node.sub_attr if isinstance(node, ValuePath) else attr_path.sub_attr
        return AttrPath(attr_path.attr, sub_attr, attr_path.uri)

    @property
    def attr(self) -> str:
        """The attribute portion of the path, selection and filter excluded.

        For paths like "urn:...:User:userName", returns "userName".
        For simple paths like "userName", returns "userName".
        For 'emails[type eq "work"].value', returns "emails.value".
        For the empty path, which designates the resource itself, returns "".

        Nothing tells a schema-only path from a qualified one, since the URN of
        a schema is itself a colon-separated name: "urn:...:User" reads as the
        attribute "User" of the schema "urn:...:2.0".
        """
        designated = self._designated_attr_path()
        if designated is None:
            return ""
        return str(replace(designated, uri=None))

    @property
    def parts(self) -> tuple[str, ...]:
        """The attribute name, and the sub-attribute name when there is one.

        A value selection is not part of the segments, so the first element is
        always the attribute a PATCH operation applies to.

        For "name.familyName", returns ("name", "familyName").
        For "userName", returns ("userName",).
        For 'emails[type eq "work"].value', returns ("emails", "value").
        For "", returns ().
        """
        designated = self._designated_attr_path()
        if designated is None:
            return ()
        if designated.sub_attr:
            return (designated.attr, designated.sub_attr)
        return (designated.attr,)

    @property
    def value_filter(self) -> "FilterNode | None":
        """The filter selecting the values this path operates on, when it has one.

        The three spellings errata 7122 offers for one selection answer the same
        filter, expressed against an entry, so it applies as it stands. An entry
        that carries no sub-attribute is addressed through the ``value`` its
        entries hold by :rfc:`RFC7643 §2.4 <7643#section-2.4>`.

        >>> from scim2_models import Path
        >>> str(Path('emails[type eq "work"].value').value_filter)
        'type eq "work"'
        >>> str(Path('emails.type eq "work"').value_filter)
        'type eq "work"'
        >>> str(Path('schemas eq "urn:x:y"').value_filter)
        'value eq "urn:x:y"'
        >>> Path("emails.value").value_filter is None
        True
        """
        value_path = self._as_value_path()
        return None if value_path is None else value_path.val_filter

    def _designated_model(self) -> type[BaseModel] | None:
        """Return the model this path designates when it names no attribute.

        The resource root and a bare schema URN both designate a model rather
        than one of its attributes, and neither can go through attribute
        resolution: the root names nothing, and nothing tells a schema URN from
        a qualified path syntactically, so it is recognised by comparing the
        whole path to the schemas the bound model knows.
        """
        from .resources.resource import Extension
        from .resources.resource import Resource

        if not self.__scim_models__:
            return None

        if self.ast is None:
            return self.__scim_models__[0]

        path = self.lower()
        for model in self.__scim_models__:
            if not (isclass(model) and issubclass(model, Resource | Extension)):
                continue

            if model.__schema__ and path == model.__schema__.lower():
                return model

            if not issubclass(model, Resource):
                continue

            for schema, extension_model in model.get_extension_models().items():
                if path == schema.lower():
                    return extension_model

        return None

    def resolve(self) -> "ResolvedAttribute | None":
        """Bind this path to the attribute it designates on the bound model.

        This is the single resolution the model-aware properties are built on.

        :returns: The resolved attribute, or :data:`None` when the path is
            unbound, designates a model rather than an attribute, or names an
            attribute the model does not declare.
        """
        model = self._resolving_model()
        if model is None or self._designated_model() is not None:
            return None

        # A path that designates no attribute has already returned above,
        # since _designated_model answers for the resource root.
        designated = self._designated_attr_path()
        assert designated is not None

        return resolve_attr_path(model, designated, strict=False)

    @property
    def models(self) -> tuple[type[BaseModel], ...]:
        """The resource types the path is bound to, none for an unbound path.

        ``Path[User]`` binds one, ``Path[User | Group]`` binds two, as an
        endpoint covering several resource types does. A path is resolved
        against the first of them declaring the attribute it names.
        """
        return self.__scim_models__

    @property
    def model(self) -> type[BaseModel] | None:
        """The model holding the attribute this path designates.

        Requires the Path to be bound to a model type via ``Path[Model]``.
        Returns None if the path is unbound or invalid.

        For "name.familyName" on Path[User], returns Name.
        For "userName" on Path[User], returns User.
        """
        if (designated := self._designated_model()) is not None:
            return designated

        resolved = self.resolve()
        return resolved.target_model if resolved is not None else None

    @property
    def field_name(self) -> str | None:
        """The Python attribute name (snake_case) for this path.

        Requires the Path to be bound to a model type via ``Path[Model]``.
        Returns None if the path is unbound, invalid, or designates a model
        rather than one of its attributes.

        For "name.familyName" on Path[User], returns "family_name".
        For "userName" on Path[User], returns "user_name".
        """
        resolved = self.resolve()
        return resolved.target_field_name if resolved is not None else None

    @property
    def field_type(self) -> type | None:
        """The Python type of the field this path points to.

        Annotated types are unwrapped, so a ``binary`` attribute declared as
        ``Base64Bytes`` reports :class:`bytes`.

        For "userName" on Path[User], returns str.
        For "name" on Path[User], returns Name.
        For "emails" on Path[User], returns Email.
        """
        resolved = self.resolve()
        return resolved.target_type if resolved is not None else None

    @property
    def is_multivalued(self) -> bool | None:
        """Whether this path points to a multi-valued attribute.

        For "emails" on Path[User], returns True.
        For "emails.value" on Path[User], returns False, as the path
        designates one value per entry.
        """
        resolved = self.resolve()
        return resolved.target_is_multivalued if resolved is not None else None

    def get_annotation(self, annotation_type: type) -> Any:
        """Get annotation value for this path's field.

        :param annotation_type: The annotation class (e.g., Required, Mutability).
        :returns: The annotation value, or None when the path designates no
            attribute.

        For "userName" on Path[User] with Required, returns Required.true.
        """
        resolved = self.resolve()
        if resolved is None or resolved.target_model is None:
            return None
        return resolved.target_model.get_field_annotation(
            resolved.target_field_name, annotation_type
        )

    @property
    def urn(self) -> str | None:
        """The fully qualified URN for this path.

        Requires the Path to be bound to a model type via ``Path[Model]``.
        Returns None if the path is unbound or invalid.

        For "userName" on Path[User], returns
        "urn:ietf:params:scim:schemas:core:2.0:User:userName".
        """
        if (designated := self._designated_model()) is not None:
            return getattr(designated, "__schema__", None) or None

        resolved = self.resolve()
        return resolved.urn if resolved is not None else None

    def _resolve_head(self) -> "tuple[type[BaseModel], str] | None":
        """Resolve the attribute the path applies to, and the model declaring it.

        A constraint on a complex attribute governs everything written under it,
        so it is the attribute a path applies to that answers for an operation
        rather than the sub-attribute it targets: ``meta`` is read-only where the
        ``meta.version`` it holds is not.
        """
        resolved = self.resolve()
        if resolved is None:
            return None
        return resolved.model, resolved.field_name

    def _resolve_instance(
        self, resource: BaseModel, *, create: bool = False
    ) -> _Resolution | None:
        """Resolve the target object and remaining path.

        :param resource: The resource to resolve against.
        :param create: If True, create extension instance if it doesn't exist.
        :returns: Resolution with target object and path, or None if target doesn't exist.
        :raises InvalidPathException: If the path references an unknown extension.
        """
        from .resources.resource import Extension
        from .resources.resource import Resource

        path_str = str(self)

        if ":" not in path_str:
            return _Resolution(resource, path_str)

        path_lower = path_str.lower()
        model_schema = ""
        if isinstance(resource, Resource | Extension):
            model_schema = getattr(type(resource), "__schema__", "") or ""
        extension_models = (
            resource.get_extension_models() if isinstance(resource, Resource) else {}
        )

        schema = _designating_schema(path_lower, [model_schema, *extension_models])
        if schema is None:
            if isinstance(resource, Resource):
                raise InvalidPathException(path=path_str)
            return None

        sub_path = path_str[len(schema) :].lstrip(":")
        ext_model = extension_models.get(schema)

        if ext_model is None:
            return _Resolution(resource, sub_path, path_lower == schema.lower())

        if path_lower == schema.lower():
            return _Resolution(resource, ext_model.__name__)

        ext_obj = getattr(resource, ext_model.__name__)
        if create and ext_obj is None:
            # Checked on the declared type before anything is instantiated, so
            # that a refused write leaves no half-built extension behind.
            _resolve_field_names(ext_model, sub_path.split("."), path_str)
            ext_obj = ext_model()
            setattr(resource, ext_model.__name__, ext_obj)
        if ext_obj is None:
            return None
        return _Resolution(ext_obj, sub_path)

    def _walk_to_target(
        self, obj: BaseModel, path_str: str, *, create: bool = False
    ) -> "_Target | None":
        """Navigate to the objects holding the field this path designates.

        A multi-valued attribute crossed on the way fans the walk out over its
        entries, as :rfc:`RFC7644 §3.5.2 <7644#section-3.5.2>` has an unfiltered
        path designate every one of them.

        :param obj: The object to walk from.
        :param path_str: The dotted path to walk.
        :param create: Whether an unassigned complex attribute is instantiated
            rather than ending the walk.
        :returns: The target, or None when nothing is left to walk to.
        :raises PathNotFoundException: If a segment names an attribute the model
            does not declare, or one with no sub-attributes to descend into.
        """
        field_names = _resolve_field_names(type(obj), path_str.split("."), str(self))
        hosts = [obj]
        multivalued = False

        for field_name in field_names[:-1]:
            entered: list[BaseModel] = []
            for host in hosts:
                value = getattr(host, field_name)
                if value is None and create:
                    value = self._create_intermediate(host, field_name)
                if isinstance(value, list):
                    multivalued = True
                    entered.extend(value)
                elif value is not None:
                    entered.append(value)
            if not entered:
                return None
            hosts = entered

        return _Target(hosts, field_names[-1], multivalued)

    @staticmethod
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

    def _as_value_path(self) -> ValuePath | None:
        """Normalise a value-selecting path into a single representation.

        :rfc:`RFC7644 §3.5.2 <7644#section-3.5.2>` as corrected by errata 7122
        offers three ways to select values of a multi-valued attribute, which
        all mean the same thing here::

            emails[type eq "work"]   a value selection
            emails.type eq "work"    a bare comparison
            schemas eq "urn:…"       a bare comparison on a scalar list
        """
        node = self.ast
        if isinstance(node, ValuePath):
            return node

        if not isinstance(node, Comparison | Present):
            return None

        # A sub-attribute in the comparison becomes the inner filter, so that
        # 'emails.type eq "work"' selects like 'emails[type eq "work"]'. Without
        # one, the values are scalars, addressed through the "value" convention.
        inner_attr = AttrPath(attr=node.attr_path.sub_attr or "value")
        head = AttrPath(attr=node.attr_path.attr, uri=node.attr_path.uri)
        inner: FilterNode = (
            Present(attr_path=inner_attr)
            if isinstance(node, Present)
            else Comparison(attr_path=inner_attr, op=node.op, value=node.value)
        )
        return ValuePath(attr_path=head, val_filter=inner)

    def _select(self, resource: BaseModel) -> "_Selection | None":
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
        value_path = self._as_value_path()
        if value_path is None:
            return None

        model = type(resource)
        resolved = resolve_attr_path(model, value_path.attr_path, strict=False)
        if resolved is None:
            raise PathNotFoundException(path=str(self), field=value_path.attr_path.attr)

        # Checked before reading the resource, so that a selection that cannot
        # apply is rejected whether or not the attribute happens to be set.
        validate_value_selection(resolved)
        validate_value_filter(resolved, value_path.val_filter)

        host = attribute_host(resource, resolved)
        if host is None:
            return _Selection(None, resolved.field_name, [], value_path.sub_attr)

        matched = Evaluator(model, resource).select(value_path)
        return _Selection(host, resolved.field_name, matched, value_path.sub_attr)

    def _get(self, resource: ResourceT) -> Any:
        """Get the value at this path from a resource."""
        if (selection := self._select(resource)) is not None:
            if selection.sub_attr is None:
                return selection.matched or None
            values = [
                getattr(
                    item,
                    _require_field(type(item), selection.sub_attr, str(self)),
                    None,
                )
                for item in selection.matched
                if isinstance(item, BaseModel)
            ]
            return values or None

        if (resolution := self._resolve_instance(resource)) is None:
            return None

        if not resolution.path_str:
            return resolution.target

        if (
            target := self._walk_to_target(resolution.target, resolution.path_str)
        ) is None:
            return None

        values = [getattr(host, target.field_name) for host in target.hosts]
        return values if target.multivalued else values[0]

    def get(self, resource: ResourceT, *, strict: bool = True) -> Any:
        """Get the value at this path from a resource.

        A path crossing a multi-valued attribute designates the sub-attribute of
        each of its entries, so ``emails.value`` answers with one item per email,
        in their order, :data:`None` included for an email carrying no value.
        Writing through such a path reaches those same entries, which is what
        makes the answer their mirror. An attribute holding no entry at all
        answers :data:`None`, as any unassigned attribute does.

        :param resource: The resource to get the value from.
        :param strict: If True, raise exceptions for invalid paths.
        :returns: The value at this path, or None if the value is absent.
        :raises PathNotFoundException: If strict and the path references a non-existent field.
        :raises InvalidPathException: If strict and the path references an unknown extension.
        :raises InvalidFilterException: If strict and a value selection does not
            apply to the attribute it selects from.
        """
        try:
            return self._get(resource)
        except (InvalidPathException, InvalidFilterException):
            if strict:
                raise
            return None

    def _set_selected(
        self, selection: "_Selection", value: Any, *, is_add: bool = False
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
            item_field = _require_field(type(item), sub_attr, str(self))
            if getattr(item, item_field) != value:
                setattr(item, item_field, value)
                modified = True
        return modified

    def _delete_selected(self, selection: "_Selection") -> bool:
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
                item_field = _require_field(type(item), sub_attr, str(self))
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

    def _set(self, resource: ResourceT, value: Any, *, is_add: bool = False) -> bool:
        """Set a value at this path on a resource."""
        if (selection := self._select(resource)) is not None:
            return self._set_selected(selection, value, is_add=is_add)

        if (resolution := self._resolve_instance(resource, create=True)) is None:
            return False

        obj = resolution.target
        path_str = resolution.path_str
        is_explicit_schema_path = resolution.is_explicit_schema_path

        if not path_str:
            if not isinstance(value, dict):
                if is_explicit_schema_path:
                    raise InvalidPathException(path=str(self))
                return False
            filtered_value = {
                k: v
                for k, v in value.items()
                if _find_field_name(type(obj), k) is not None
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

        if (target := self._walk_to_target(obj, path_str, create=True)) is None:
            return False

        changed = [
            self._set_field_value(host, target.field_name, value, is_add)
            for host in target.hosts
        ]
        return any(changed)

    def set(
        self,
        resource: ResourceT,
        value: Any,
        *,
        is_add: bool = False,
        strict: bool = True,
    ) -> bool:
        """Set a value at this path on a resource.

        A path crossing a multi-valued attribute writes the sub-attribute of each
        of its entries, so ``emails.value`` gives every email the same value. An
        unassigned multi-valued attribute has no entry to write to, and is left
        alone.

        :param resource: The resource to set the value on.
        :param value: The value to set.
        :param is_add: If True and the target is multi-valued, append to the
            list instead of replacing. Duplicates are not added.
        :param strict: If True, raise exceptions for invalid paths.
        :returns: True if the value was set/added, False if unchanged.
        :raises InvalidPathException: If strict and the path does not exist or is invalid.
        :raises InvalidFilterException: If strict and a value selection does not
            apply to the attribute it selects from.
        :raises NoTargetException: If strict, ``is_add`` is false and a value
            selection matches nothing.
        """
        try:
            return self._set(resource, value, is_add=is_add)
        except (InvalidPathException, InvalidFilterException, NoTargetException):
            if strict:
                raise
            return False

    @staticmethod
    def _set_field_value(
        obj: BaseModel, field_name: str, value: Any, is_add: bool
    ) -> bool:
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

    def _delete(self, resource: ResourceT, value: Any | None = None) -> bool:
        """Delete a value at this path from a resource."""
        if (selection := self._select(resource)) is not None:
            return self._delete_selected(selection)

        if (resolution := self._resolve_instance(resource)) is None:
            return False

        if not resolution.path_str:
            raise InvalidPathException(path=str(self))

        if (
            target := self._walk_to_target(resolution.target, resolution.path_str)
        ) is None:
            return False

        changed = [
            self._delete_field_value(host, target.field_name, value)
            for host in target.hosts
        ]
        return any(changed)

    @staticmethod
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

    def delete(
        self, resource: ResourceT, value: Any | None = None, *, strict: bool = True
    ) -> bool:
        """Delete a value at this path from a resource.

        If value is None, the entire attribute is set to None.
        If value is provided and the attribute is multi-valued,
        only matching values are removed from the list.
        A path crossing a multi-valued attribute removes the sub-attribute from
        each of its entries, so ``emails.type`` leaves the emails in place and
        untypes them.

        :param resource: The resource to delete the value from.
        :param value: Optional specific value to remove from a list.
        :param strict: If True, raise exceptions for invalid paths.
        :returns: True if a value was deleted, False if unchanged.
        :raises InvalidPathException: If strict and the path does not exist or is invalid.
        :raises InvalidFilterException: If strict and a value selection does not
            apply to the attribute it selects from.
        """
        try:
            return self._delete(resource, value)
        except (InvalidPathException, InvalidFilterException):
            if strict:
                raise
            return False

    @classmethod
    def iter_paths(
        cls,
        include_subattributes: bool = True,
        include_extensions: bool = True,
        required: "list[Required] | None" = None,
        mutability: "list[Mutability] | None" = None,
        uniqueness: "list[Uniqueness] | None" = None,
        returned: "list[Returned] | None" = None,
        case_exact: "list[CaseExact] | None" = None,
    ) -> "Iterator[Path[ResourceT]]":
        """Iterate over all paths for the bound model and its extensions.

        Requires the Path to be bound to a model type via ``Path[Model]``.

        :param include_subattributes: Whether to include sub-attribute paths.
        :param include_extensions: Whether to include extension attributes.
        :param required: Filter by Required annotation values (e.g., [Required.true]).
        :param mutability: Filter by Mutability annotation values (e.g., [Mutability.read_write]).
        :param uniqueness: Filter by Uniqueness annotation values (e.g., [Uniqueness.server]).
        :param returned: Filter by Returned annotation values (e.g., [Returned.always]).
        :param case_exact: Filter by CaseExact annotation values (e.g., [CaseExact.true]).
        :yields: Path instances for each attribute matching the filters.
        """
        from .annotations import CaseExact
        from .annotations import Mutability
        from .annotations import Required
        from .annotations import Returned
        from .annotations import Uniqueness
        from .attributes import ComplexAttribute
        from .resources.resource import Extension
        from .resources.resource import Resource

        if len(cls.__scim_models__) != 1:
            raise TypeError(
                "iter_paths requires a Path bound to one model: Path[Model]"
            )
        model = cls.__scim_models__[0]

        selected = (
            (required, Required),
            (mutability, Mutability),
            (uniqueness, Uniqueness),
            (returned, Returned),
            (case_exact, CaseExact),
        )

        def matches_filters(target_model: type[BaseModel], field_name: str) -> bool:
            return all(
                target_model.get_field_annotation(field_name, annotation) in values
                for values, annotation in selected
                if values is not None
            )

        def iter_model_paths(
            target_model: type[Resource[Any] | Extension],
        ) -> "Iterator[Path[ResourceT]]":
            for field_name in target_model.model_fields:
                if field_name in ("meta", "id", "schemas"):
                    continue

                if not matches_filters(target_model, field_name):
                    continue

                field_type = target_model.get_field_root_type(field_name)

                urn: str
                if isclass(field_type) and issubclass(field_type, Extension):
                    if not include_extensions:
                        continue
                    urn = field_type.__schema__ or ""
                elif isclass(target_model) and issubclass(target_model, Extension):
                    urn = target_model().get_attribute_urn(field_name)
                else:
                    urn = _scim_name(target_model, field_name)

                yield cls(urn)

                is_complex = (
                    field_type is not None
                    and isclass(field_type)
                    and issubclass(field_type, ComplexAttribute)
                )
                if include_subattributes and is_complex:
                    for sub_field_name in field_type.model_fields:  # type: ignore[union-attr]
                        if not matches_filters(field_type, sub_field_name):  # type: ignore[arg-type]
                            continue
                        sub_urn = f"{urn}.{_scim_name(field_type, sub_field_name)}"  # type: ignore[arg-type]
                        yield cls(sub_urn)

        yield from iter_model_paths(model)  # type: ignore[arg-type]

        if include_extensions and isclass(model) and issubclass(model, Resource):
            for extension_model in model.get_extension_models().values():
                yield from iter_model_paths(extension_model)
