import re
from collections.abc import Iterable
from collections.abc import Iterator
from inspect import isclass
from typing import TYPE_CHECKING
from typing import Any
from typing import Generic
from typing import NamedTuple
from typing import TypeVar
from typing import cast

from pydantic import GetCoreSchemaHandler
from pydantic import GetJsonSchemaHandler
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import core_schema

from .base import BaseModel
from .urn import URN
from .utils import _find_field_name
from .utils import _to_camel

if TYPE_CHECKING:
    from .annotations import CaseExact
    from .annotations import Mutability
    from .annotations import Required
    from .annotations import Returned
    from .annotations import Uniqueness
    from .resources.resource import Resource

from .exceptions import InvalidPathException
from .exceptions import PathNotFoundException

ResourceT = TypeVar("ResourceT", bound="Resource[Any]")

_VALID_PATH_PATTERN = re.compile(r'^[a-zA-Z][a-zA-Z0-9._:\-\[\]"=\s]*$')
_ATTRIBUTE_NOTATION_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9._:\-]*$")
_PATH_CACHE: dict[tuple[type, type], type] = {}


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


class Path(str, Generic[ResourceT]):
    __scim_model__: type[BaseModel] | None = None

    def __class_getitem__(cls, model: type[ResourceT]) -> type["Path[ResourceT]"]:
        """Create a Path class bound to a specific model type."""
        if not isclass(model) or not hasattr(model, "model_fields"):
            return super().__class_getitem__(model)  # type: ignore[misc,no-any-return]

        cache_key = (cls, model)
        if cache_key in _PATH_CACHE:
            return _PATH_CACHE[cache_key]

        new_class = type(f"Path[{model.__name__}]", (cls,), {"__scim_model__": model})
        _PATH_CACHE[cache_key] = new_class
        return new_class

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

    def __new__(cls, path: "str | Path[Any]") -> "Path[Any]":
        cls.check_syntax(str(path))
        return super().__new__(cls, path)

    @classmethod
    def check_syntax(cls, path: str) -> None:
        """Check if path syntax is valid according to RFC 7644 simplified rules.

        An empty string is valid and represents the resource root.

        :param path: The path to validate
        :raises InvalidPathException: If the path syntax is invalid
        """
        if not path:
            return

        if path[0].isdigit():
            raise InvalidPathException(
                path=path, detail="Paths cannot start with a digit"
            )

        if ".." in path:
            raise InvalidPathException(
                path=path, detail="Paths cannot contain double dots"
            )

        if not _VALID_PATH_PATTERN.match(path):
            raise InvalidPathException(
                path=path, detail="The path contains invalid characters"
            )

        if path.endswith(":"):
            raise InvalidPathException(
                path=path, detail="Paths cannot end with a colon"
            )

        if ":" in path:
            urn = path.rsplit(":", 1)[0]
            try:
                URN(urn.lower())
            except ValueError as exc:
                raise InvalidPathException(
                    path=path, detail=f"The path is not a valid URN: {exc}"
                ) from exc

    def check_attribute_notation(self) -> None:
        """Check that the path names an attribute instead of selecting values.

        The attribute notation of :rfc:`RFC7644 §3.10 <7644#section-3.10>` is a
        schema URN, an attribute and at most one of its sub-attributes. A value
        selection or a comparison designates the values an attribute holds
        rather than the attribute itself, so it has no place where a single
        attribute is asked for.

        :raises InvalidPathException: If the path is not in attribute notation.
        """
        if not _ATTRIBUTE_NOTATION_PATTERN.match(self):
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
        if ":" not in self:
            return None
        return self.rsplit(":", 1)[0]

    @property
    def attr(self) -> str:
        """The attribute portion of the path.

        For paths like "urn:...:User:userName", returns "userName".
        For simple paths like "userName", returns "userName".
        For schema-only paths like "urn:...:User", returns "".
        """
        if ":" not in self:
            return str(self)
        return self.rsplit(":", 1)[1]

    @property
    def parts(self) -> tuple[str, ...]:
        """The attribute path segments split by '.'.

        For "name.familyName", returns ("name", "familyName").
        For "userName", returns ("userName",).
        For "", returns ().
        """
        attr = self.attr
        if not attr:
            return ()
        return tuple(attr.split("."))

    @property
    def model(self) -> type[BaseModel] | None:
        """The target model type for this path.

        Requires the Path to be bound to a model type via ``Path[Model]``.
        Returns None if the path is unbound or invalid.

        For "name.familyName" on Path[User], returns Name.
        For "userName" on Path[User], returns User.
        """
        if (result := self._resolve_model()) is None:
            return None
        return result[0]

    @property
    def field_name(self) -> str | None:
        """The Python attribute name (snake_case) for this path.

        Requires the Path to be bound to a model type via ``Path[Model]``.
        Returns None if the path is unbound or invalid.

        For "name.familyName" on Path[User], returns "family_name".
        For "userName" on Path[User], returns "user_name".
        """
        if (result := self._resolve_model()) is None:
            return None
        return result[1]

    @property
    def field_type(self) -> type | None:
        """The Python type of the field this path points to.

        Requires the Path to be bound to a model type via ``Path[Model]``.
        Returns None if the path is unbound, invalid, or points to a schema-only path.

        For "userName" on Path[User], returns str.
        For "name" on Path[User], returns Name.
        For "emails" on Path[User], returns Email.
        """
        if self.model is None or self.field_name is None:
            return None
        return self.model.get_field_root_type(self.field_name)

    @property
    def is_multivalued(self) -> bool | None:
        """Whether this path points to a multi-valued attribute.

        Requires the Path to be bound to a model type via ``Path[Model]``.
        Returns None if the path is unbound, invalid, or points to a schema-only path.

        For "emails" on Path[User], returns True.
        For "userName" on Path[User], returns False.
        """
        if self.model is None or self.field_name is None:
            return None
        return self.model.get_field_multiplicity(self.field_name)

    def get_annotation(self, annotation_type: type) -> Any:
        """Get annotation value for this path's field.

        Requires the Path to be bound to a model type via ``Path[Model]``.
        Returns None if the path is unbound, invalid, or points to a schema-only path.

        :param annotation_type: The annotation class (e.g., Required, Mutability).
        :returns: The annotation value or None.

        For "userName" on Path[User] with Required, returns Required.true.
        """
        if self.model is None or self.field_name is None:
            return None
        return self.model.get_field_annotation(self.field_name, annotation_type)

    @property
    def urn(self) -> str | None:
        """The fully qualified URN for this path.

        Requires the Path to be bound to a model type via ``Path[Model]``.
        Returns None if the path is unbound or invalid.

        For "userName" on Path[User], returns
        "urn:ietf:params:scim:schemas:core:2.0:User:userName".
        """
        from .resources.resource import Resource

        if self.__scim_model__ is None or self.model is None:
            return None

        schema = self.schema
        if not schema and issubclass(self.__scim_model__, Resource):
            schema = self.__scim_model__.__schema__

        if not self.attr:
            return schema if schema else None
        return f"{schema}:{self.attr}" if schema else self.attr

    def _resolve_model(self) -> tuple[type[BaseModel], str | None] | None:
        """Resolve the path against the bound model type."""
        from .resources.resource import Extension
        from .resources.resource import Resource

        model = self.__scim_model__
        if model is None:
            return None

        attr_path = self.attr

        if ":" in self and isclass(model) and issubclass(model, Resource | Extension):
            path_lower = str(self).lower()

            extension_models = (
                model.get_extension_models() if issubclass(model, Resource) else {}
            )
            schema = _designating_schema(
                path_lower, [model.__schema__ or "", *extension_models]
            )

            if schema is None:
                return None

            model = extension_models.get(schema, model)
            if path_lower == schema.lower():
                return model, None
            attr_path = str(self)[len(schema) :].lstrip(":")

        if not attr_path:
            return model, None

        if "." in attr_path:
            parts = attr_path.split(".")
            current_model = model

            for part in parts[:-1]:
                if (field_name := _find_field_name(current_model, part)) is None:
                    return None
                field_type = current_model.get_field_root_type(field_name)
                if (
                    field_type is None
                    or not isclass(field_type)
                    or not issubclass(field_type, BaseModel)
                ):
                    return None
                current_model = field_type

            if (field_name := _find_field_name(current_model, parts[-1])) is None:
                return None
            return current_model, field_name

        if (field_name := _find_field_name(model, attr_path)) is None:
            return None
        return model, field_name

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

    def _get(self, resource: ResourceT) -> Any:
        """Get the value at this path from a resource."""
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
        """
        try:
            return self._get(resource)
        except InvalidPathException:
            if strict:
                raise
            return None

    def _set(self, resource: ResourceT, value: Any, *, is_add: bool = False) -> bool:
        """Set a value at this path on a resource."""
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
        """
        try:
            return self._set(resource, value, is_add=is_add)
        except InvalidPathException:
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
        """
        try:
            return self._delete(resource, value)
        except InvalidPathException:
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

        model = cls.__scim_model__
        if model is None:
            raise TypeError("iter_paths requires a bound Path type: Path[Model]")

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
                    urn = _to_camel(field_name)

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
                        sub_urn = f"{urn}.{_to_camel(sub_field_name)}"
                        yield cls(sub_urn)

        yield from iter_model_paths(model)  # type: ignore[arg-type]

        if include_extensions and isclass(model) and issubclass(model, Resource):
            for extension_model in model.get_extension_models().values():
                yield from iter_model_paths(extension_model)
