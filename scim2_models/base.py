import warnings
from inspect import isclass
from typing import TYPE_CHECKING
from typing import Any
from typing import ClassVar
from typing import NamedTuple
from typing import Optional
from typing import cast
from typing import get_args
from typing import get_origin

from pydantic import AliasGenerator
from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict
from pydantic import SerializationInfo
from pydantic import SerializerFunctionWrapHandler
from pydantic import ValidationInfo
from pydantic import ValidatorFunctionWrapHandler
from pydantic import model_serializer
from pydantic import model_validator
from pydantic_core import PydanticCustomError
from typing_extensions import Self

from scim2_models.annotations import Mutability
from scim2_models.annotations import Required
from scim2_models.annotations import Returned
from scim2_models.context import Context
from scim2_models.exceptions import MutabilityException
from scim2_models.utils import UNION_TYPES
from scim2_models.utils import _normalize_attribute_name
from scim2_models.utils import _to_camel

if TYPE_CHECKING:
    from scim2_models.path import Path


def _short_attr_path(urn: str) -> str:
    """Extract the short attribute path from a full URN.

    For URNs like ``urn:...:User:userName``, returns ``userName``.
    For URNs like ``urn:...:User:name.familyName``, returns ``name.familyName``.
    For short names like ``userName``, returns ``userName`` as-is.
    """
    if ":" in urn:
        return urn.rsplit(":", 1)[1]
    return urn


def _attr_matches(requested: str, current_urn: str) -> bool:
    """Check if a single requested attribute matches the current field URN.

    Supports short names (``userName``), dotted paths (``name.familyName``),
    and full extension URNs. Handles parent/child relationships.
    """
    req_lower = requested.lower()

    if ":" in requested:
        current_lower = current_urn.lower()
        return (
            current_lower == req_lower
            or req_lower.startswith(current_lower + ":")
            or req_lower.startswith(current_lower + ".")
            or current_lower.startswith(req_lower + ".")
            or current_lower.startswith(req_lower + ":")
        )

    current_short = _short_attr_path(current_urn).lower()
    return (
        current_short == req_lower
        or current_short.startswith(req_lower + ".")
        or req_lower.startswith(current_short + ".")
    )


def _exact_attr_match(attrs: list[str], current_urn: str) -> bool:
    """Check if current_urn exactly matches any entry in attrs (case-insensitive).

    Used for ``excludedAttributes`` matching and :attr:`Returned.request` checking,
    where parent/child relationship should not apply.
    """
    current_short = _short_attr_path(current_urn).lower()
    for attr in attrs:
        attr_lower = attr.lower()
        if ":" in attr:
            if current_urn.lower() == attr_lower:
                return True
        else:
            if current_short == attr_lower:
                return True
    return False


def _is_attribute_requested(requested_attrs: list[str], current_urn: str) -> bool:
    """Check if an attribute should be included based on the requested attributes.

    Returns True if:
    - The current attribute is explicitly requested
    - A sub-attribute of the current attribute is requested
    - The current attribute is a sub-attribute of a requested attribute
    """
    return any(_attr_matches(req, current_urn) for req in requested_attrs)


class _SCIMClassInfo(NamedTuple):
    """SCIM metadata for BaseModel."""

    alias_to_field: dict[str, str] = {}
    """Alias -> Python field name.

    Holds both validation and serialization aliases.
    """

    attribute_urns: dict[str, str] = {}
    """Python field name -> fully resolved SCIM attribute URN."""

    complex_fields: frozenset[str] = frozenset()
    """Field names whose root type is a ``ComplexAttribute`` subclass."""


class BaseModel(PydanticBaseModel):
    """Base Model for everything."""

    model_config = ConfigDict(
        alias_generator=AliasGenerator(
            validation_alias=_normalize_attribute_name,
            serialization_alias=_to_camel,
        ),
        validate_assignment=True,
        populate_by_name=True,
        use_attribute_docstrings=True,
        extra="forbid",
    )

    __scim_info__: ClassVar[_SCIMClassInfo] = _SCIMClassInfo()
    """Cached model metadata"""

    @classmethod
    def get_field_annotation(cls, field_name: str, annotation_type: type) -> Any:
        """Return the annotation of type 'annotation_type' of the field 'field_name'.

        This method extracts SCIM-specific annotations from a field's metadata,
        such as :class:`~scim2_models.Mutability`, :class:`~scim2_models.Required`,
        or :class:`~scim2_models.Returned` annotations.

        :return: The annotation instance if found, otherwise the annotation type's default value

        >>> from scim2_models.resources.user import User
        >>> from scim2_models.annotations import Mutability, Required

        Get the mutability annotation of the 'id' field:

        >>> mutability = User.get_field_annotation("id", Mutability)
        >>> mutability
        <Mutability.read_only: 'readOnly'>

        Get the required annotation of the 'user_name' field:

        >>> required = User.get_field_annotation("user_name", Required)
        >>> required
        <Required.true: True>

        If no annotation is found, returns the default value:

        >>> missing = User.get_field_annotation("display_name", Required)
        >>> missing
        <Required.false: False>
        """
        field_metadata = cls.model_fields[field_name].metadata

        default_value = getattr(annotation_type, "_default", None)

        def annotation_type_filter(item: Any) -> bool:
            return isinstance(item, annotation_type)

        field_annotation = next(
            filter(annotation_type_filter, field_metadata), default_value
        )
        return field_annotation

    @classmethod
    def get_field_root_type(cls, attribute_name: str) -> type | None:
        """Extract the root type from a model field.

        This method unwraps complex type annotations to find the underlying
        type, removing Optional and List wrappers to get to the actual type
        of the field's content.

        :return: The root type of the field, or None if not found

        >>> from scim2_models.resources.user import User
        >>> from scim2_models.resources.group import Group

        Simple type:

        >>> User.get_field_root_type("user_name")
        <class 'str'>

        ``Optional`` type unwraps to the underlying type:

        >>> User.get_field_root_type("display_name")
        <class 'str'>

        ``List`` type unwraps to the element type:

        >>> User.get_field_root_type("emails")  # doctest: +ELLIPSIS
        <class 'scim2_models.resources.user.Email'>

        ``Optional[List[T]]`` unwraps to ``T``:

        >>> Group.get_field_root_type("members")  # doctest: +ELLIPSIS
        <class 'scim2_models.resources.group.GroupMember'>
        """
        attribute_type = cls.model_fields[attribute_name].annotation

        # extract 'x' from 'Optional[x]'
        if get_origin(attribute_type) in UNION_TYPES:
            attribute_type = get_args(attribute_type)[0]

        # extract 'x' from 'List[x]'
        origin = get_origin(attribute_type)
        if origin and isclass(origin) and issubclass(origin, list):
            attribute_type = get_args(attribute_type)[0]

        return attribute_type

    @classmethod
    def get_field_multiplicity(cls, attribute_name: str) -> bool:
        """Indicate whether a field holds multiple values.

        This method determines if a field is defined as a list type,
        which indicates it can contain multiple values. It handles
        Optional wrappers correctly.

        :return: True if the field holds multiple values (is a list), False otherwise

        >>> from scim2_models.resources.user import User
        >>> User.get_field_multiplicity("user_name")
        False
        >>> User.get_field_multiplicity("emails")
        True
        """
        attribute_type = cls.model_fields[attribute_name].annotation

        # extract 'x' from 'Optional[x]'
        if get_origin(attribute_type) in UNION_TYPES:
            attribute_type = get_args(attribute_type)[0]

        origin = get_origin(attribute_type)
        return isinstance(origin, type) and issubclass(origin, list)

    @classmethod
    def __pydantic_on_complete__(cls) -> None:
        """Build the per-class SCIM metadata table on ``cls.__scim_info__``.

        Fires after pydantic resolves field types (re-fires after ``model_rebuild``). Idempotent.
        """
        if not cls.model_fields:
            return

        alias_to_field: dict[str, str] = {}
        attribute_urns: dict[str, str] = {}
        complex_fields: set[str] = set()

        main_schema = getattr(cls, "__schema__", None)
        extension_cls: type | None = None
        if main_schema is not None:
            from scim2_models.resources.resource import Extension

            extension_cls = Extension

        for field_name, field in cls.model_fields.items():
            # Alias -> field name mapping
            serialization_alias = field.serialization_alias or field_name
            alias_to_field[serialization_alias] = field_name
            alias_to_field[cast(str, field.validation_alias)] = field_name

            root_type = cls.get_field_root_type(field_name)

            # Is complex field
            if root_type is not None and getattr(
                root_type, "__is_complex_attribute__", False
            ):
                complex_fields.add(field_name)

            # Attribute URNs
            if main_schema is not None and not (
                extension_cls is not None
                and isclass(root_type)
                and issubclass(root_type, extension_cls)
            ):
                attribute_urns[field_name] = f"{main_schema}:{serialization_alias}"
            else:
                attribute_urns[field_name] = serialization_alias

        cls.__scim_info__ = _SCIMClassInfo(
            alias_to_field=alias_to_field,
            attribute_urns=attribute_urns,
            complex_fields=frozenset(complex_fields),
        )

    @model_validator(mode="wrap")
    @classmethod
    def normalize_attribute_names(
        cls, value: Any, handler: ValidatorFunctionWrapHandler, info: ValidationInfo
    ) -> Self:
        """Normalize payload attribute names.

        :rfc:`RFC7643 §2.1 <7643#section-2.1>` indicate that attribute
        names should be case-insensitive. Any attribute name is
        transformed in lowercase so any case is handled the same way.
        """
        if isinstance(value, dict):
            value = {_normalize_attribute_name(k): v for k, v in value.items()}
        return cast(Self, handler(value))

    @model_validator(mode="after")
    def enforce_scim_context(self, info: ValidationInfo) -> Self:
        scim_context = info.context.get("scim") if info.context else None
        if not scim_context or scim_context == Context.DEFAULT:
            return self

        from scim2_models.resources.resource import Resource

        is_create_or_replace = scim_context in (
            Context.RESOURCE_CREATION_REQUEST,
            Context.RESOURCE_REPLACEMENT_REQUEST,
        )
        original = info.context.get("original") if info.context else None
        fields_set = self.model_fields_set

        for field_name in self.__class__.model_fields:
            value = getattr(self, field_name)

            if Context.is_request(scim_context):
                if field_name in fields_set:
                    self._check_mutability(field_name, scim_context)
                if is_create_or_replace:
                    self._check_necessity(field_name, value)
            else:
                # Must be response
                self._check_returnability(field_name, value)

            if self.get_field_multiplicity(field_name) and value is not None:
                self._check_primary_uniqueness(field_name, value)

        if (
            scim_context == Context.RESOURCE_REPLACEMENT_REQUEST
            and original is not None
            and issubclass(type(self), Resource)
        ):
            # TODO: We loop all the fields a second time
            # Could replace with field specific mutability check
            self._check_replacement_mutability(original)

        return self

    def _check_mutability(self, field_name: str, scim_context: Context) -> None:
        """Check and fix that the field mutability is expected according to the requests validation context, as defined in :rfc:`RFC7643 §7 <7643#section-7>`."""
        mutability = self.__class__.get_field_annotation(field_name, Mutability)

        if (
            scim_context in (Context.RESOURCE_QUERY_REQUEST, Context.SEARCH_REQUEST)
            and mutability == Mutability.write_only
        ):
            raise PydanticCustomError(
                "mutability_error",
                "Field '{field_name}' has mutability '{field_mutability}' but this in not valid in {context} context",
                {
                    "field_name": field_name,
                    "field_mutability": mutability,
                    "context": scim_context.name.lower().replace("_", " "),
                },
            )

        elif (
            scim_context
            in (Context.RESOURCE_CREATION_REQUEST, Context.RESOURCE_REPLACEMENT_REQUEST)
            and mutability == Mutability.read_only
        ):
            # Avoid re-triggering this validation by using __dict__
            self.__dict__[field_name] = None

    def _check_necessity(self, field_name: str, value: Any) -> None:
        """Check that the required attributes are present in creations and replacement requests."""
        necessity = self.__class__.get_field_annotation(field_name, Required)

        if necessity == Required.true and value is None:
            raise PydanticCustomError(
                "required_error",
                "Field '{field_name}' is required but value is missing or null",
                {
                    "field_name": field_name,
                },
            )

    def _check_returnability(self, field_name: str, value: Any) -> None:
        """Check that the fields returnability is expected according to the responses validation context, as defined in :rfc:`RFC7643 §7 <7643#section-7>`."""
        returnability = self.__class__.get_field_annotation(field_name, Returned)

        if returnability == Returned.always and value is None:
            raise PydanticCustomError(
                "returned_error",
                "Field '{field_name}' has returnability 'always' but value is missing or null",
                {
                    "field_name": field_name,
                },
            )

        elif returnability == Returned.never and value is not None:
            raise PydanticCustomError(
                "returned_error",
                "Field '{field_name}' has returnability 'never' but value is set",
                {
                    "field_name": field_name,
                },
            )

    def _check_replacement_mutability(self, original: "BaseModel") -> None:
        """Check if 'immutable' attributes have been mutated in replacement requests."""
        try:
            self._apply_replace_constraints(original)
        except MutabilityException as exc:
            raise exc.as_pydantic_error() from exc

    def _check_primary_uniqueness(self, field_name: str, value: Any) -> None:
        """Validate that only one attribute can be marked as primary in multi-valued lists, per :rfc:`RFC7643 §2.4 <7643#section-2.4>`."""
        element_type = self.get_field_root_type(field_name)
        if (
            element_type is None
            or not isclass(element_type)
            or not issubclass(element_type, PydanticBaseModel)
            or "primary" not in element_type.model_fields
        ):
            return

        primary_count = sum(
            1 for item in value if getattr(item, "primary", None) is True
        )

        if primary_count > 1:
            raise PydanticCustomError(
                "primary_uniqueness_error",
                "Field '{field_name}' has {count} items marked as primary, but only one is allowed per RFC 7643",
                {
                    "field_name": field_name,
                    "count": primary_count,
                },
            )

    def _apply_replace_constraints(self, original: Self) -> None:
        """Enforce RFC 7644 §3.5.1 replace (PUT) semantics.

        - ``readOnly`` fields are copied from *original* unconditionally.
        - ``immutable`` fields are copied from *original* when absent from
          ``self``; a :class:`~scim2_models.MutabilityException` is raised
          when the value differs.

        Recursively applies to nested single-valued complex attributes.
        """
        from .attributes import is_complex_attribute

        for field_name in type(self).model_fields:
            mutability = type(self).get_field_annotation(field_name, Mutability)
            original_val = getattr(original, field_name)

            if mutability == Mutability.read_only:
                # RFC 7644 §3.5.1: "readOnly" values provided SHALL be ignored.
                setattr(self, field_name, original_val)
            elif mutability == Mutability.immutable:
                self_val = getattr(self, field_name)
                if self_val is None and original_val is not None:
                    # RFC 7643 §7: "SHALL NOT be updated" — omitting an
                    # immutable field is not a request to clear it.
                    setattr(self, field_name, original_val)
                elif self_val != original_val:
                    # RFC 7644 §3.5.1: input values MUST match.
                    raise MutabilityException(
                        attribute=field_name, mutability="immutable"
                    )

            attr_type = type(self).get_field_root_type(field_name)
            if (
                attr_type
                and is_complex_attribute(attr_type)
                and not type(self).get_field_multiplicity(field_name)
            ):
                original_sub = getattr(original, field_name)
                replacement_sub = getattr(self, field_name)
                if original_sub is not None and replacement_sub is not None:
                    replacement_sub._apply_replace_constraints(original_sub)

    def get_attribute_urn(self, field_name: str) -> str:
        """Build the full URN of the attribute.

        See :rfc:`RFC7644 §3.10 <7644#section-3.10>`.
        """
        return self.__scim_info__.attribute_urns[field_name]

    def _set_complex_attribute_urns(self) -> None:
        """Mark each ``ComplexAttribute`` child with its ``_attribute_urn``.

        ``_attribute_urn`` is later read by :meth:`get_attribute_urn`.
        """
        cls = self.__class__
        info = cls.__scim_info__
        complex_fields = info.complex_fields

        for field_name in complex_fields:
            attr_value = getattr(self, field_name)
            if not attr_value:
                continue

            schema = info.attribute_urns[field_name]

            if isinstance(attr_value, list):
                for item in attr_value:
                    item._attribute_urn = schema
            else:
                attr_value._attribute_urn = schema

    @model_serializer(mode="wrap")
    def scim_serializer(
        self, handler: SerializerFunctionWrapHandler, info: SerializationInfo
    ) -> dict[str, Any]:
        """Serialize the fields according to mutability indications passed in the serialization context."""
        scim_ctx = info.context.get("scim") if info.context else None
        is_response = Context.is_response(scim_ctx) if scim_ctx else False

        if is_response:
            # Complex attribute urns are only used in responses
            self._set_complex_attribute_urns()

        serialized: dict[str, Any] = handler(self)

        if not scim_ctx:
            return serialized

        # Delete empty extensions
        if (get_extension_models := getattr(self, "get_extension_models", None)) is not None:
            for ext_urn, ext_cls in get_extension_models().items():
                key = ext_urn if info.by_alias else ext_cls.__name__
                if key in serialized and serialized[key] is None:
                    del serialized[key]

        # Serialize according to given context
        if scim_ctx != Context.DEFAULT:
            if is_response:
                included_attrs = (
                    info.context.get("scim_attributes", []) if info.context else []
                )
                excluded_attrs = (
                    info.context.get("scim_excluded_attributes", [])
                    if info.context
                    else []
                )
                self._scim_response_serializer(
                    serialized, included_attrs, excluded_attrs
                )
            else:
                # Must be request
                self._scim_request_serializer(serialized, scim_ctx)

        return serialized

    def _scim_request_serializer(
        self, serialized: dict[str, Any], scim_ctx: Context
    ) -> None:
        """Serialize the fields according to mutability indications passed in the serialization context."""
        for alias in set(serialized):
            field_name = self.__scim_info__.alias_to_field.get(alias, alias)
            mutability = self.get_field_annotation(field_name, Mutability)

            if (
                scim_ctx
                in (
                    Context.RESOURCE_CREATION_REQUEST,
                    Context.RESOURCE_REPLACEMENT_REQUEST,
                )
                and mutability == Mutability.read_only
            ):
                del serialized[alias]

            elif (
                scim_ctx
                in (
                    Context.RESOURCE_QUERY_REQUEST,
                    Context.SEARCH_REQUEST,
                )
                and mutability == Mutability.write_only
            ):
                del serialized[alias]

    def _scim_response_serializer(
        self,
        serialized: dict[str, Any],
        included_attrs: list[str],
        excluded_attrs: list[str],
    ) -> None:
        """Serialize the fields according to returnability indications passed in the serialization context."""
        for alias in set(serialized):
            field_name = self.__scim_info__.alias_to_field.get(alias, alias)
            returnability = self.get_field_annotation(field_name, Returned)
            attribute_urn = self.get_attribute_urn(field_name)

            if returnability == Returned.never:
                del serialized[alias]
            elif returnability == Returned.default and (
                (
                    included_attrs
                    and not _is_attribute_requested(included_attrs, attribute_urn)
                )
                or _exact_attr_match(excluded_attrs, attribute_urn)
            ):
                del serialized[alias]
            elif returnability == Returned.request and not _exact_attr_match(
                included_attrs, attribute_urn
            ):
                del serialized[alias]

    @classmethod
    def model_validate(
        cls,
        *args: Any,
        scim_ctx: Context | None = Context.DEFAULT,
        original: Optional["BaseModel"] = None,
        **kwargs: Any,
    ) -> Self:
        """Validate SCIM payloads and generate model representation by using Pydantic :meth:`~pydantic.BaseModel.model_validate`.

        :param scim_ctx: The SCIM :class:`~scim2_models.Context` in which the validation happens.
        :param original: If this parameter is set during :attr:`~Context.RESOURCE_REPLACEMENT_REQUEST`,
            :attr:`~scim2_models.Mutability.immutable` parameters will be compared against the *original* model value.
            An exception is raised if values are different.

            .. deprecated:: 0.6.7
                Use :meth:`replace` on the validated instance instead.
                Will be removed in 0.8.0.
        """
        if original is not None:
            warnings.warn(
                "The 'original' parameter is deprecated, "
                "use the 'replace' method on the validated instance instead. "
                "Will be removed in 0.8.0.",
                DeprecationWarning,
                stacklevel=2,
            )

        context = kwargs.setdefault("context", {})
        context.setdefault("scim", scim_ctx)
        context.setdefault("original", original)

        return super().model_validate(*args, **kwargs)

    def _prepare_model_dump(
        self,
        scim_ctx: Context | None = Context.DEFAULT,
        attributes: list["str | Path[Any]"] | None = None,
        excluded_attributes: list["str | Path[Any]"] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        kwargs.setdefault("context", {}).setdefault("scim", scim_ctx)

        if scim_ctx:
            kwargs.setdefault("exclude_none", True)
            kwargs.setdefault("by_alias", True)

        if attributes:
            kwargs["context"]["scim_attributes"] = [str(a) for a in attributes]
        if excluded_attributes:
            kwargs["context"]["scim_excluded_attributes"] = [
                str(a) for a in excluded_attributes
            ]

        return kwargs

    def model_dump(
        self,
        *args: Any,
        scim_ctx: Context | None = Context.DEFAULT,
        attributes: list["str | Path[Any]"] | None = None,
        excluded_attributes: list["str | Path[Any]"] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Create a model representation that can be included in SCIM messages by using Pydantic :code:`BaseModel.model_dump`.

        :param scim_ctx: If a SCIM context is passed, some default values of
            Pydantic :code:`BaseModel.model_dump` are tuned to generate valid SCIM
            messages. Pass :data:`None` to get the default Pydantic behavior.
        :param attributes: A multi-valued list of strings indicating the names of resource
            attributes to return in the response, overriding the set of attributes that
            would be returned by default. Invalid values are ignored.
        :param excluded_attributes: A multi-valued list of strings indicating the names of resource
            attributes to be removed from the default set of attributes to return. Invalid values are ignored.
        """
        dump_kwargs = self._prepare_model_dump(
            scim_ctx,
            attributes=attributes,
            excluded_attributes=excluded_attributes,
            **kwargs,
        )
        if scim_ctx:
            dump_kwargs.setdefault("mode", "json")
        return super().model_dump(*args, **dump_kwargs)

    def model_dump_json(
        self,
        *args: Any,
        scim_ctx: Context | None = Context.DEFAULT,
        attributes: list["str | Path[Any]"] | None = None,
        excluded_attributes: list["str | Path[Any]"] | None = None,
        **kwargs: Any,
    ) -> str:
        """Create a JSON model representation that can be included in SCIM messages by using Pydantic :code:`BaseModel.model_dump_json`.

        :param scim_ctx: If a SCIM context is passed, some default values of
            Pydantic :code:`BaseModel.model_dump` are tuned to generate valid SCIM
            messages. Pass :data:`None` to get the default Pydantic behavior.
        :param attributes: A multi-valued list of strings indicating the names of resource
            attributes to return in the response, overriding the set of attributes that
            would be returned by default. Invalid values are ignored.
        :param excluded_attributes: A multi-valued list of strings indicating the names of resource
            attributes to be removed from the default set of attributes to return. Invalid values are ignored.
        """
        dump_kwargs = self._prepare_model_dump(
            scim_ctx,
            attributes=attributes,
            excluded_attributes=excluded_attributes,
            **kwargs,
        )
        return super().model_dump_json(*args, **dump_kwargs)
