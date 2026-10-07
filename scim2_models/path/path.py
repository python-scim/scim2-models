"""An attribute path as a string, bound to the models it is resolved against."""

from collections.abc import Iterator
from dataclasses import replace
from inspect import isclass
from typing import TYPE_CHECKING
from typing import Any
from typing import Generic
from typing import TypeVar

from ..base import BaseModel
from ..base import _is_returned
from ..urn import URN
from .access import _delete_value
from .access import _get_value
from .access import _set_value
from .binding import _BoundToModels

if TYPE_CHECKING:
    from ..annotations import CaseExact
    from ..annotations import Mutability
    from ..annotations import Required
    from ..annotations import Returned
    from ..annotations import Uniqueness
    from ..resources.resource import Resource

from ..exceptions import InvalidFilterException
from ..exceptions import InvalidPathException
from ..exceptions import NoTargetException
from .expressions import AttrPath
from .expressions import Comparison
from .expressions import FilterNode
from .expressions import PathNode
from .expressions import Present
from .expressions import Template
from .expressions import ValuePath
from .expressions import _Expression
from .expressions import _text
from .grammar import _parse_path
from .resolution import AttributeBinding
from .resolution import _designated_model
from .resolution import _resolve_attr_path
from .resolution import _unwrap_annotated

ResourceT = TypeVar("ResourceT", bound="Resource[Any]")

_Levels = tuple[tuple["Returned | None", str], ...]

_ITERATED_PATHS = "__scim_iterated_paths__"


def _node_attr_path(node: PathNode) -> AttrPath:
    """Return the attribute path a parsed path node applies to."""
    if isinstance(node, AttrPath):
        return node
    return node.attr_path


class Path(_BoundToModels, _Expression, Generic[ResourceT]):
    """A SCIM attribute path, as defined at :rfc:`RFC7644 §3.5.2 <7644#section-3.5.2>`.

    A path *is* the string it was built from, and designates one of three
    things:

    - a model, when the path is ``""`` (the resource root) or a bare schema
      URN, accessible with the :attr:`model` property;
    - an attribute, such as ``userName`` or ``name.familyName``, accessible
      with the :meth:`resolve` method as an :class:`~scim2_models.AttributeBinding`;
    - some values of a multi-valued attribute, when the path selects them as in
      ``emails[type eq "work"]``: the :attr:`value_filter` property holds the
      filter, and the :meth:`resolve` method still answers for the attribute
      they belong to.

    Syntax is checked on creation. Resolving attribute names requires a model
    to resolve them against, bound with a parameterized type such as
    ``Path[User]``. The :meth:`get`, :meth:`set` and :meth:`delete` methods
    read and write a resource through the path.

    On Python 3.14, a path can be written as a t-string, whose interpolated
    values are quoted as :meth:`ScimFilter.quote <scim2_models.ScimFilter.quote>`
    does. Another path, or a :class:`~scim2_models.ScimFilter`, is inserted
    as it stands::

        Path[Group](t"members[value eq {member_id}]")
    """

    _ast: "PathNode | None" = None
    """The parsed path, kept once :attr:`ast` has computed it."""

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
            if _resolve_attr_path(model, designated, strict=False) is not None:
                return model
        return self.__scim_models__[0]

    def __new__(cls, path: "str | Path[Any] | Template") -> "Path[Any]":
        text = _text(path)
        cls._check_syntax(text)
        return super().__new__(cls, text)

    @classmethod
    def _check_syntax(cls, path: str) -> None:
        """Check that a path conforms to the ``PATH`` rule of RFC7644 §3.5.2.

        The grammar is the published ABNF as corrected by
        `errata 7122 <https://errata.rfc-editor.org/eid7122/>`_, so a path
        is either an attribute path, a value selection optionally followed by a
        sub-attribute, or a bare comparison. An empty string is valid and
        represents the resource root. An invalid syntax raises
        InvalidPathException.
        """
        if not path:
            return

        node = _parse_path(path)

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
            self._ast = _parse_path(str(self))
        return self._ast

    def _check_attribute_notation(self) -> None:
        """Check that the path names an attribute instead of selecting values.

        The attribute notation of RFC7644 §3.10 is a schema URN, an attribute
        and at most one of its sub-attributes. A value selection or a
        comparison designates the values an attribute holds rather than the
        attribute itself, so it has no place where a single attribute is asked
        for. A path that is not in attribute notation raises
        InvalidPathException.
        """
        if not isinstance(self.ast, AttrPath):
            raise InvalidPathException(
                path=str(self),
                detail=f"{str(self)!r} is not in attribute notation",
            )

    @property
    def schema(self) -> str | None:
        """The schema URN portion of the path.

        For paths like ``urn:...:User:userName``, returns ``urn:...:User``.
        For simple paths like ``userName``, returns :data:`None`.
        """
        node = self.ast
        return None if node is None else _node_attr_path(node).uri

    def _designated_attr_path(self) -> AttrPath | None:
        """Return the attribute path this path designates, selection excluded.

        A value selection carries its sub-attribute past the brackets, so
        ``emails[type eq "work"].value`` designates ``emails.value``. The
        resource root designates no attribute at all.

        The path is normalized first, so the three spellings errata 7122 offers
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

        For paths like ``urn:...:User:userName``, returns ``userName``.
        For simple paths like ``userName``, returns ``userName``.
        For ``emails[type eq "work"].value``, returns ``emails.value``.
        For the empty path, which designates the resource itself, returns ``""``.

        Nothing tells a schema-only path from a qualified one, since the URN of
        a schema is itself a colon-separated name: ``urn:...:User`` reads as the
        attribute ``User`` of the schema ``urn:...:2.0``.
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

    @property
    def model(self) -> type[BaseModel] | None:
        """The model this path designates, when it names no attribute.

        The resource root designates the bound model, and a bare schema URN
        the resource or the extension it is the schema of. A path naming an
        attribute designates a model through none of them, and answers
        :data:`None`: :meth:`resolve` tells which attribute it is.

        >>> from scim2_models import EnterpriseUser, Path, User
        >>> Path[User]("").model is User
        True
        >>> Path[User[EnterpriseUser]](
        ...     EnterpriseUser.__schema__
        ... ).model is EnterpriseUser
        True
        >>> Path[User]("userName").model is None
        True
        """
        if not self.__scim_models__:
            return None

        if self.ast is None:
            return self.__scim_models__[0]

        for model in self.__scim_models__:
            if (designated := _designated_model(model, str(self))) is not None:
                return designated
        return None

    def resolve(
        self, model: type[BaseModel] | None = None
    ) -> "AttributeBinding | None":
        """Bind this path to the attribute it designates on a model.

        >>> from scim2_models import Group, Path, User
        >>> path = Path[User | Group]("displayName")
        >>> path.resolve().model is User
        True
        >>> path.resolve(Group).model is Group
        True

        :param model: The model to resolve against. By default, the first bound
            model declaring the attribute. Pass one to pick a type of a union, or
            to resolve an unbound path.
        :returns: The resolved attribute, or :data:`None` when there is no model
            to resolve against, when the path designates a model rather than an
            attribute, or when the model does not declare the attribute.
        """
        model = model or self._resolving_model()
        designated = self._designated_attr_path()
        if (
            model is None
            or designated is None
            or _designated_model(model, str(self)) is not None
        ):
            return None

        return _resolve_attr_path(model, designated, strict=False)

    @property
    def models(self) -> tuple[type[BaseModel], ...]:
        """The resource types the path is bound to, none for an unbound path.

        ``Path[User]`` binds one, ``Path[User | Group]`` binds two, as an
        endpoint covering several resource types does. A path is resolved
        against the first of them declaring the attribute it names.
        """
        return self.__scim_models__

    def _as_value_path(self) -> ValuePath | None:
        """Normalise a value-selecting path into a single representation.

        RFC7644 §3.5.2 as corrected by errata 7122 offers three ways to select
        values of a multi-valued attribute, which all mean the same thing
        here::

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
            return _get_value(self, resource)
        except (InvalidPathException, InvalidFilterException):
            if strict:
                raise
            return None

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
        :raises NoTargetException: If strict and a value selection matches
            nothing.
        """
        try:
            return _set_value(self, resource, value, is_add=is_add)
        except (InvalidPathException, InvalidFilterException, NoTargetException):
            if strict:
                raise
            return False

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
            return _delete_value(self, resource, value)
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
        target_type: "list[type] | None" = None,
        attributes: "list[Path[Any]] | None" = None,
        excluded_attributes: "list[Path[Any]] | None" = None,
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
        :param target_type: Only yield paths whose value is an instance of one of these
            types (e.g., [Reference]). Unlike the other filters, it does not skip the
            sub-attributes of a complex attribute: ``members.$ref`` is yielded even
            though ``members`` is not a :class:`~scim2_models.Reference`.
        :param attributes: Only yield the paths a response keeps when a client
            sends these ``attributes`` (:rfc:`RFC7644 §3.9 <7644#section-3.9>`).
            Unlike *returned*, it applies the request on top of the
            :class:`~scim2_models.Returned` annotations. An attribute is kept when
            only some of its sub-attributes are requested.
        :param excluded_attributes: Only yield the paths a response keeps when a
            client sends these ``excludedAttributes``. An attribute is kept when
            only some of its sub-attributes are excluded. Without both
            *attributes* and *excluded_attributes*, the
            :class:`~scim2_models.Returned` annotations filter nothing. Pass an
            empty list to get the default response.
        :yields: Path instances for each attribute matching the filters.
        """
        if len(cls.__scim_models__) != 1:
            raise TypeError(
                "iter_paths requires a Path bound to one model: Path[Model]"
            )
        model = cls.__scim_models__[0]

        filters = (required, mutability, uniqueness, returned, case_exact, target_type)
        key = (
            cls,
            include_subattributes,
            include_extensions,
            *(None if values is None else tuple(values) for values in filters),
        )

        # The cache is held by the model, like the one of _resolve_attr_path,
        # so that it does not keep alive the models built by from_schema.
        cache: dict[tuple[Any, ...], tuple[tuple[Path[ResourceT], _Levels], ...]] | None
        cache = model.__dict__.get(_ITERATED_PATHS)
        if cache is None:
            cache = {}
            setattr(model, _ITERATED_PATHS, cache)

        if key not in cache:
            cache[key] = tuple(
                cls._walk_paths(
                    model,
                    include_subattributes,
                    include_extensions,
                    required,
                    mutability,
                    uniqueness,
                    returned,
                    case_exact,
                    target_type,
                )
            )

        if attributes is None and excluded_attributes is None:
            for path, _ in cache[key]:
                yield path
            return

        # The parameters come from the client, so they stay out of the cache key.
        included = [str(path) for path in attributes or ()]
        excluded = [str(path) for path in excluded_attributes or ()]
        for path, levels in cache[key]:
            if all(
                _is_returned(returnability, urn, included, excluded)
                for returnability, urn in levels
            ):
                yield path

    @classmethod
    def _walk_paths(
        cls,
        model: type[BaseModel],
        include_subattributes: bool,
        include_extensions: bool,
        required: "list[Required] | None",
        mutability: "list[Mutability] | None",
        uniqueness: "list[Uniqueness] | None",
        returned: "list[Returned] | None",
        case_exact: "list[CaseExact] | None",
        target_type: "list[type] | None",
    ) -> "Iterator[tuple[Path[ResourceT], _Levels]]":
        """Walk the attributes of a model and its extensions, as iter_paths does.

        Each path comes with the returnability and the URN of each level it
        goes through, from the extension down to the sub-attribute.
        """
        from ..annotations import CaseExact
        from ..annotations import Mutability
        from ..annotations import Required
        from ..annotations import Returned
        from ..annotations import Uniqueness
        from ..attributes import ComplexAttribute
        from ..resources.resource import Extension
        from ..resources.resource import Resource

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

        def matches_target_type(target_model: type[BaseModel], field_name: str) -> bool:
            if target_type is None:
                return True
            field_type = _unwrap_annotated(target_model.get_field_root_type(field_name))
            return isclass(field_type) and issubclass(field_type, tuple(target_type))

        def iter_model_paths(
            target_model: type[Resource[Any] | Extension],
            parents: _Levels = (),
        ) -> "Iterator[tuple[Path[ResourceT], _Levels]]":
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
                    urn = target_model()._get_attribute_urn(field_name)
                else:
                    urn = target_model._scim_name(field_name)

                full_urn = target_model.__scim_info__.attribute_urns[field_name]
                levels = (
                    *parents,
                    (target_model.get_field_annotation(field_name, Returned), full_urn),
                )
                if matches_target_type(target_model, field_name):
                    yield cls(urn), levels

                is_complex = (
                    field_type is not None
                    and isclass(field_type)
                    and issubclass(field_type, ComplexAttribute)
                )
                if include_subattributes and is_complex:
                    for sub_field_name in field_type.model_fields:  # type: ignore[union-attr]
                        if not matches_filters(field_type, sub_field_name):  # type: ignore[arg-type]
                            continue
                        if not matches_target_type(field_type, sub_field_name):  # type: ignore[arg-type]
                            continue
                        sub_name = field_type._scim_name(sub_field_name)  # type: ignore[union-attr]
                        sub_level = (
                            field_type.get_field_annotation(sub_field_name, Returned),  # type: ignore[union-attr]
                            f"{full_urn}.{sub_name}",
                        )
                        yield cls(f"{urn}.{sub_name}"), (*levels, sub_level)

        yield from iter_model_paths(model)  # type: ignore[arg-type]

        if include_extensions and isclass(model) and issubclass(model, Resource):
            field_names = {
                urn: name for name, urn in model.__scim_info__.attribute_urns.items()
            }
            for schema, extension_model in model.get_extension_models().items():
                returnability = model.get_field_annotation(
                    field_names[schema], Returned
                )
                yield from iter_model_paths(extension_model, ((returnability, schema),))
