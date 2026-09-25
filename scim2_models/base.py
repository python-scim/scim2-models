import warnings
from collections.abc import Mapping
from inspect import isclass
from types import MappingProxyType
from typing import TYPE_CHECKING
from typing import Any
from typing import ClassVar
from typing import NamedTuple
from typing import NoReturn
from typing import cast
from typing import get_args
from typing import get_origin

from pydantic import AliasChoices
from pydantic import AliasGenerator
from pydantic import Base64Bytes
from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict
from pydantic import PrivateAttr
from pydantic import SerializationInfo
from pydantic import SerializerFunctionWrapHandler
from pydantic import ValidationError
from pydantic import ValidationInfo
from pydantic import ValidatorFunctionWrapHandler
from pydantic import model_serializer
from pydantic import model_validator
from pydantic.fields import FieldInfo
from pydantic_core import InitErrorDetails
from pydantic_core import PydanticCustomError
from typing_extensions import Self

from scim2_models.annotations import CaseExact
from scim2_models.annotations import Mutability
from scim2_models.annotations import Required
from scim2_models.annotations import Returned
from scim2_models.context import Context
from scim2_models.exceptions import MutabilityException
from scim2_models.policy import ScimPolicy
from scim2_models.policy import _policy
from scim2_models.reference import Reference
from scim2_models.utils import UNION_TYPES
from scim2_models.utils import _normalize_attribute_name
from scim2_models.utils import _to_camel

if TYPE_CHECKING:
    from scim2_models.messages.response_parameters import ResponseParameters
    from scim2_models.path import Path
    from scim2_models.provider import ScimProvider
    from scim2_models.resources.service_provider_config import ServiceProviderConfig


def _short_attr_path(urn: str) -> str:
    """Extract the short attribute path from a full URN.

    For URNs like ``urn:...:User:userName``, returns ``userName``. For URNs
    like ``urn:...:User:name.familyName``, returns ``name.familyName``. For
    short names like ``userName``, returns ``userName`` as-is.
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

    Used for ``excludedAttributes`` matching and Returned.request checking,
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

    alias_to_field: Mapping[str, str] = MappingProxyType({})
    """Serialization alias -> Python field name.

    Keyed by the spelling a dump carries, so a serializer can walk back from a
    key it produced to the field that holds it.
    """

    attribute_urns: Mapping[str, str] = MappingProxyType({})
    """Python field name -> fully resolved SCIM attribute URN."""

    complex_fields: frozenset[str] = frozenset()
    """Field names whose root type is a ``ComplexAttribute`` subclass."""

    extensions: frozenset[str] = frozenset()
    """Field names whose root type is a ``Extension`` subclass."""

    validation_names: Mapping[str, str] = MappingProxyType({})
    """""Python field name -> the name pydantic reads that field under.

    An attribute reaches pydantic under its SCIM spelling, which a validation
    error and a published JSON schema then carry.
    """ ""

    field_by_name: Mapping[str, str] = MappingProxyType({})
    """Lowercased attribute name -> Python field name.

    Every spelling a payload may use for a field: the name it is serialized
    under, the aliases it declares for itself, and its Python name. RFC7643
    §2.1 makes attribute names case-insensitive and nothing else — its
    ``nameChar`` rule makes ``$``, ``-`` and ``_`` part of a name — so the keys
    are lowercased and keep their punctuation.
    """


_DECLARED_ALIAS_PRIORITY = 2
"""The ``alias_priority`` pydantic gives an alias the field itself declares, an
alias generator filling the slots left empty with a priority of 1."""


def _declared_validation_names(field: FieldInfo) -> list[str]:
    """Return the names a field declares for itself.

    Only the field itself declares an attribute name: what the alias generator
    derived from a Python name is how pydantic reads the field, not a spelling
    a peer may use. An AliasChoices holds several spellings of one attribute,
    each of them usable. An AliasPath points at a place inside the payload
    rather than at an attribute, so it indexes nothing: the key it starts from
    is no attribute name, and reaches pydantic as the peer spelled it.
    """
    if field.alias_priority != _DECLARED_ALIAS_PRIORITY:
        return []

    alias = field.validation_alias
    if isinstance(alias, str):
        return [alias]
    if isinstance(alias, AliasChoices):
        return [choice for choice in alias.choices if isinstance(choice, str)]
    return []


def _validation_name(field: FieldInfo, field_name: str) -> str:
    """Return the name pydantic reads a field under.

    The alias generator gives every field its SCIM attribute name, which an
    error and a published JSON schema then carry. A field declaring
    several spellings of its own names none of them in particular, and is read
    under its Python name.
    """
    alias = field.validation_alias
    return alias if isinstance(alias, str) else field_name


def _claim_attribute_name(
    index: dict[str, str], name: str, field_name: str, owner: type
) -> None:
    """Record that a field answers to an attribute name.

    Two fields answering to one name leave a payload key reaching both, which
    the class cannot be built with, so such a class is refused where it is
    written.
    """
    key = name.lower()
    claimed = index.get(key)
    if claimed is not None and claimed != field_name:
        raise TypeError(
            f"{owner.__name__} has two fields answering to the SCIM attribute "
            f"name {name!r}: {claimed!r} and {field_name!r}. Attribute names are "
            f"case-insensitive (RFC7643 §2.1), so one payload key would reach both."
        )
    index[key] = field_name


def _claim_python_name(index: dict[str, str], field_name: str) -> None:
    """Record that a field answers to its own Python name.

    That name is a convenience rather than an attribute name, so two fields
    whose names only differ by case take it from each other instead of making
    the class impossible to build: the key then designates neither, leaving the
    SCIM name of each of them the only way to reach it.
    """
    key = field_name.lower()
    index[key] = "" if key in index and index[key] != field_name else field_name


def _holds_reference(model: type["BaseModel"], field_name: str) -> bool:
    """Say whether a field holds a reference URI, which is compared apart.

    RFC7643 §2.4 makes two spellings of one reference equivalent,
    ``.../Users/2819c223`` and ``.../v2/Users/2819c223`` among them.
    scim2-models implements no such equivalence, so an immutable reference is
    preserved rather than compared.
    """
    root_type = model.get_field_root_type(field_name)
    return isinstance(root_type, type) and issubclass(root_type, Reference)


def _entries_by_value(entries: list[Any]) -> dict[Any, list[Any]]:
    """Group the entries of a multi-valued attribute by their ``value``.

    RFC7643 §2.4 holds the significant value of an entry there, but it is no
    key: one value may appear twice under different ``type`` sub-attributes,
    and only the whole pair is unique.
    """
    grouped: dict[Any, list[Any]] = {}
    for entry in entries:
        value = getattr(entry, "value", None)
        if value is not None:
            grouped.setdefault(value, []).append(entry)
    return grouped


class BaseModel(PydanticBaseModel):
    """Base Model for everything."""

    model_config = ConfigDict(
        alias_generator=AliasGenerator(
            validation_alias=_to_camel,
            serialization_alias=_to_camel,
        ),
        validate_assignment=True,
        validate_by_name=True,
        validate_by_alias=True,
        use_attribute_docstrings=True,
        extra="forbid",
    )

    __scim_info__: ClassVar[_SCIMClassInfo] = _SCIMClassInfo()
    """Cached model metadata"""

    _unknown_attributes: dict[str, Any] = PrivateAttr(default_factory=dict)

    @property
    def unknown_attributes(self) -> dict[str, Any]:
        """The attributes of the payload that no field of this model declares.

        Keyed by the spelling the peer used. Empty unless the
        :class:`~scim2_models.ScimPolicy` the validation ran under tolerated
        them, and filled at the level they were found: a sub-attribute lands on
        the complex attribute that carries it, not on the resource above.
        """
        return self._unknown_attributes

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

        def annotation_type_filter(item: Any) -> bool:
            return isinstance(item, annotation_type)

        field_annotation = next(filter(annotation_type_filter, field_metadata), None)
        if field_annotation is not None:
            return field_annotation

        if annotation_type is CaseExact:
            return cls._default_case_exact(field_name)

        return getattr(annotation_type, "_default", None)

    @classmethod
    def _default_case_exact(cls, field_name: str) -> CaseExact:
        """Return the implicit case sensitivity of a field, based on its type.

        RFC7643 §2.3.6 and §2.3.7 state that binary and reference values are
        case exact, whatever the schema representations of §8.7 say.
        """
        root_type = cls.get_field_root_type(field_name)
        if root_type == Base64Bytes:
            return CaseExact.true

        if isclass(root_type) and issubclass(root_type, Reference):
            return CaseExact.true

        return CaseExact.false

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
    def _scim_name(cls, field_name: str) -> str:
        """Return the name a field is serialized under, ``$ref`` included."""
        return cls.model_fields[field_name].serialization_alias or _to_camel(field_name)

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
        extensions: set[str] = set()
        scim_names: dict[str, str] = {}
        python_names: dict[str, str] = {}
        validation_names: dict[str, str] = {}

        main_schema = getattr(cls, "__schema__", None)
        extension_cls: type | None = None
        if main_schema is not None:
            from scim2_models.resources.resource import Extension

            extension_cls = Extension

        for field_name, field in cls.model_fields.items():
            # Alias -> field name mapping
            serialization_alias = cls._scim_name(field_name)
            alias_to_field[serialization_alias] = field_name

            # The names this field answers to, the SCIM ones winning over the
            # Python one, which is only the spelling pydantic offers.
            _claim_attribute_name(scim_names, serialization_alias, field_name, cls)
            for declared in _declared_validation_names(field):
                _claim_attribute_name(scim_names, declared, field_name, cls)
            _claim_python_name(python_names, field_name)
            validation_names[field_name] = _validation_name(field, field_name)

            root_type = cls.get_field_root_type(field_name)

            # Is complex field
            if root_type is not None and getattr(
                root_type, "__is_complex_attribute__", False
            ):
                complex_fields.add(field_name)

            # Is extension
            is_extension = (
                extension_cls is not None
                and isclass(root_type)
                and issubclass(root_type, extension_cls)
            )
            if is_extension:
                extensions.add(field_name)

            # Attribute URNs
            if main_schema is not None and not is_extension:
                attribute_urns[field_name] = f"{main_schema}:{serialization_alias}"
            else:
                attribute_urns[field_name] = serialization_alias

        cls.__scim_info__ = _SCIMClassInfo(
            alias_to_field=alias_to_field,
            attribute_urns=attribute_urns,
            complex_fields=frozenset(complex_fields),
            extensions=frozenset(extensions),
            field_by_name={
                **{key: name for key, name in python_names.items() if name},
                **scim_names,
            },
            validation_names=validation_names,
        )

    @model_validator(mode="wrap")
    @classmethod
    def _resolve_attribute_names(
        cls, value: Any, handler: ValidatorFunctionWrapHandler, info: ValidationInfo
    ) -> Self:
        """Rewrite each payload key to the field holding it, and set aside the rest.

        RFC7643 §2.1 makes attribute names case-insensitive, so a key is looked
        up folded. What it resolves to is the Python name of the field, which
        is the one spelling pydantic accepts for every field.

        A key no field answers to is taken out of the payload with the spelling
        the peer used, unless the policy forbids unknown attributes: it is then
        left in place, so that the error pydantic raises quotes what was sent.
        """
        unknown: dict[str, Any] = {}
        if isinstance(value, dict):
            scim_info = cls.__scim_info__
            tolerated = _policy(info).unknown != ScimPolicy.Unknown.forbid
            resolved: dict[Any, Any] = {}
            for key, item in value.items():
                field_name = scim_info.field_by_name.get(_normalize_attribute_name(key))
                if field_name is not None:
                    resolved[scim_info.validation_names[field_name]] = item
                elif tolerated:
                    unknown[key] = item
                else:
                    resolved[key] = item
            value = resolved

        obj = cast(Self, handler(value))
        if unknown:
            obj._unknown_attributes = unknown
        return obj

    @model_validator(mode="after")
    def _enforce_scim_context(self, info: ValidationInfo) -> Self:
        scim_context = info.context.get("scim") if info.context else None
        if not scim_context or scim_context == Context.DEFAULT:
            return self

        is_create_or_replace = scim_context in (
            Context.RESOURCE_CREATION_REQUEST,
            Context.RESOURCE_REPLACEMENT_REQUEST,
            Context.BULK_REQUEST,
        )
        in_bulk = bool(info.context.get("scim_bulk")) if info.context else False
        fields_set = self.model_fields_set

        for field_name in self.__class__.model_fields:
            value = getattr(self, field_name)

            if Context.is_request(scim_context):
                if field_name in fields_set:
                    self._check_mutability(field_name, scim_context)
                if is_create_or_replace and not self._is_unresolved_bulk_reference(
                    field_name, in_bulk
                ):
                    self._check_necessity(field_name, value)
            else:
                # Must be response
                self._check_returnability(field_name, value)

            if self.get_field_multiplicity(field_name) and value is not None:
                self._check_primary_uniqueness(field_name, value)

        return self

    def _is_unresolved_bulk_reference(self, field_name: str, in_bulk: bool) -> bool:
        """Whether a required Reference field targets a resource still being created.

        RFC7644 §3.7.2 lets one bulk operation reference a resource another
        operation in the same request is still creating, via a
        ``"bulkId:"``-prefixed placeholder in the sibling ``value`` attribute
        (e.g. ``manager.value``). That reference's URI can only be resolved
        once the target exists, so a required Reference sub-attribute (e.g.
        ``manager.$ref``) isn't checked for necessity in this one documented
        case.

        A bulk operation's data carries the context of the single request it
        stands for, so the bulk job it belongs to is known from the flag
        BulkOperation sets while validating it.
        """
        if not in_bulk:
            return False

        sibling_value = getattr(self, "value", None)
        if not (isinstance(sibling_value, str) and sibling_value.startswith("bulkId:")):
            return False

        return _holds_reference(self.__class__, field_name)

    def _raise_field_error(
        self, field_name: str, error: PydanticCustomError
    ) -> NoReturn:
        """Raise a validation error located on a field, from a model validator.

        Errors raised by model validators are attached to the whole model.
        Wrapping the error keeps the field location, which pydantic prefixes
        with the path of the parent models.
        """
        raise ValidationError.from_exception_data(
            self.__class__.__name__,
            [
                InitErrorDetails(
                    type=error,
                    loc=(field_name,),
                    input=getattr(self, field_name),
                )
            ],
        )

    def _check_mutability(self, field_name: str, scim_context: Context) -> None:
        """Check and fix that the field mutability is expected according to the requests validation context, as defined in RFC7643 §7."""
        mutability = self.__class__.get_field_annotation(field_name, Mutability)

        if (
            scim_context in (Context.RESOURCE_QUERY_REQUEST, Context.SEARCH_REQUEST)
            and mutability == Mutability.write_only
        ):
            self._raise_field_error(
                field_name,
                PydanticCustomError(
                    "mutability_error",
                    "Field '{field_name}' has mutability '{field_mutability}' but this is not valid in {context} context",
                    {
                        "field_name": self._scim_name(field_name),
                        "field_mutability": mutability,
                        "context": scim_context.name.lower().replace("_", " "),
                    },
                ),
            )

        elif (
            scim_context
            in (
                Context.RESOURCE_CREATION_REQUEST,
                Context.RESOURCE_REPLACEMENT_REQUEST,
                Context.BULK_REQUEST,
            )
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
                    "field_name": self._scim_name(field_name),
                },
            )

    def _check_returnability(self, field_name: str, value: Any) -> None:
        """Check that the fields returnability is expected according to the responses validation context, as defined in RFC7643 §7."""
        returnability = self.__class__.get_field_annotation(field_name, Returned)

        if returnability == Returned.always and value is None:
            raise PydanticCustomError(
                "returned_error",
                "Field '{field_name}' has returnability 'always' but value is missing or null",
                {
                    "field_name": self._scim_name(field_name),
                },
            )

        elif returnability == Returned.never and value is not None:
            raise PydanticCustomError(
                "returned_error",
                "Field '{field_name}' has returnability 'never' but value is set",
                {
                    "field_name": self._scim_name(field_name),
                },
            )

    def _check_primary_uniqueness(self, field_name: str, value: Any) -> None:
        """Validate that only one attribute can be marked as primary in multi-valued lists, per RFC7643 §2.4."""
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
                    "field_name": self._scim_name(field_name),
                    "count": primary_count,
                },
            )

    def _apply_replace_constraints(self, original: Self) -> None:
        """Enforce RFC 7644 §3.5.1 replace (PUT) semantics.

        - ``readOnly`` fields are copied from *original* unconditionally.
        - ``immutable`` fields are copied from *original* when absent from
          ``self``; a MutabilityException is raised when the value differs.
        - ``writeOnly`` fields left out of ``self`` are copied from *original*,
          and only an explicit null clears them.

        Recursively applies to nested complex attributes, and to the entries of
        a multi-valued one whose ``value`` designates a single entry on both
        sides. An immutable reference is preserved rather than compared, since
        two spellings of one URI are equivalent per RFC7643 §2.4.
        """
        for field_name in type(self).model_fields:
            mutability = type(self).get_field_annotation(field_name, Mutability)
            original_val = getattr(original, field_name)

            if mutability == Mutability.read_only:
                # RFC 7644 §3.5.1: "readOnly" values provided SHALL be ignored.
                self.__dict__[field_name] = original_val
            elif mutability == Mutability.immutable:
                self_val = getattr(self, field_name)
                if self_val is None and original_val is not None:
                    # RFC 7643 §7: "SHALL NOT be updated" — omitting an
                    # immutable field is not a request to clear it.
                    self.__dict__[field_name] = original_val
                elif self_val != original_val and not _holds_reference(
                    type(self), field_name
                ):
                    # RFC 7644 §3.5.1: input values MUST match.
                    raise MutabilityException(
                        attribute=field_name, mutability="immutable"
                    )
            elif (
                mutability == Mutability.write_only
                and field_name not in self.model_fields_set
            ):
                # RFC 7644 §3.5.1 only lets an omitted "readWrite" attribute be
                # cleared: a client that retrieved the resource and revised it
                # never got the write-only value back, and cannot resend it.
                self.__dict__[field_name] = original_val

        complex_and_extensions = self.__scim_info__.complex_fields.union(
            self.__scim_info__.extensions
        )
        for complex_attr in complex_and_extensions:
            if type(self).get_field_annotation(complex_attr, Mutability) == (
                Mutability.read_only
            ):
                # The whole attribute was already taken from *original*.
                continue

            original_sub = getattr(original, complex_attr)
            replacement_sub = getattr(self, complex_attr)
            if original_sub is None or replacement_sub is None:
                continue

            if not type(self).get_field_multiplicity(complex_attr):
                replacement_sub._apply_replace_constraints(original_sub)
                continue

            # A value borne by several entries identifies none of them.
            stored_entries = _entries_by_value(original_sub)
            for value, entries in _entries_by_value(replacement_sub).items():
                candidates = stored_entries.get(value, [])
                if len(entries) == 1 and len(candidates) == 1:
                    entries[0]._apply_replace_constraints(candidates[0])

    def _get_attribute_urn(self, field_name: str) -> str:
        """Build the full URN of the attribute.

        See RFC7644 §3.10.
        """
        return self.__scim_info__.attribute_urns[field_name]

    def _set_complex_attribute_urns(self) -> None:
        """Mark each ``ComplexAttribute`` child with its ``_attribute_urn``.

        ``_attribute_urn`` is later read by _get_attribute_urn.
        """
        for field_name in self.__scim_info__.complex_fields:
            attr_value = getattr(self, field_name)
            if not attr_value:
                continue

            # ComplexAttribute overrides _get_attribute_urn to prefix the URN
            # with the one of its parent, which is unknown at class creation.
            schema = self._get_attribute_urn(field_name)

            if isinstance(attr_value, list):
                for item in attr_value:
                    item._attribute_urn = schema
            else:
                attr_value._attribute_urn = schema

    @model_serializer(mode="wrap")
    def _scim_serializer(
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
            return self._restore_unknown_attributes(serialized, info)

        # Delete empty extensions
        for extension_field in self.__scim_info__.extensions:
            key = (
                self.__scim_info__.attribute_urns[extension_field]
                if info.by_alias
                else extension_field
            )
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

        return self._restore_unknown_attributes(serialized, info)

    def _restore_unknown_attributes(
        self, serialized: dict[str, Any], info: SerializationInfo
    ) -> dict[str, Any]:
        """Put back the attributes no field declares, as the peer spelled them.

        This runs after the context filters, which map every key back to the
        field that carries it: an unknown key has none, and _get_attribute_urn
        would raise on it.
        """
        if _policy(info).unknown == ScimPolicy.Unknown.keep:
            serialized.update(self._unknown_attributes)
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
                    Context.RESOURCE_PATCH_REQUEST,
                    Context.BULK_REQUEST,
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
            # RFC7643 §3 requires 'schemas' in every representation
            if alias == "schemas":
                continue

            field_name = self.__scim_info__.alias_to_field.get(alias, alias)
            returnability = self.get_field_annotation(field_name, Returned)
            attribute_urn = self._get_attribute_urn(field_name)

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
    def _prepare_model_validate(
        cls,
        scim_ctx: Context | None = Context.DEFAULT,
        scim_policy: ScimPolicy | None = None,
        scim_provider: "ScimProvider | None" = None,
        scim_spc: "ServiceProviderConfig | None" = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        context = kwargs.setdefault("context", {})
        context.setdefault("scim", scim_ctx)
        context.setdefault("scim_policy", scim_policy)
        context.setdefault("scim_provider", scim_provider)
        context.setdefault("scim_spc", scim_spc)
        return kwargs

    @classmethod
    def model_validate(
        cls,
        *args: Any,
        scim_ctx: Context | None = Context.DEFAULT,
        scim_policy: ScimPolicy | None = None,
        scim_provider: "ScimProvider | None" = None,
        scim_spc: "ServiceProviderConfig | None" = None,
        **kwargs: Any,
    ) -> Self:
        """Validate SCIM payloads and generate model representation by using Pydantic :meth:`~pydantic.BaseModel.model_validate`.

        :param scim_ctx: The SCIM :class:`~scim2_models.Context` in which the validation happens.
        :param scim_policy: The :class:`~scim2_models.ScimPolicy` the validation
            runs under. Defaults to the strict reading of the specification.
        :param scim_provider: The :class:`~scim2_models.ScimProvider` describing
            the service the payload belongs to. Defaults to the provider of the
            innermost open block, if any.
        :param scim_spc: The
            :class:`~scim2_models.ServiceProviderConfig` the peer publishes,
            which overrides the one *scim_provider* carries.
        """
        validate_kwargs = cls._prepare_model_validate(
            scim_ctx,
            scim_policy,
            scim_provider=scim_provider,
            scim_spc=scim_spc,
            **kwargs,
        )
        return super().model_validate(*args, **validate_kwargs)

    @classmethod
    def model_validate_json(
        cls,
        *args: Any,
        scim_ctx: Context | None = Context.DEFAULT,
        scim_policy: ScimPolicy | None = None,
        scim_provider: "ScimProvider | None" = None,
        scim_spc: "ServiceProviderConfig | None" = None,
        **kwargs: Any,
    ) -> Self:
        """Validate SCIM JSON payloads and generate model representation by using Pydantic :meth:`~pydantic.BaseModel.model_validate_json`.

        Malformed JSON payloads raise a :class:`~pydantic_core.ValidationError`, like
        any other SCIM validation failure.

        :param scim_ctx: The SCIM :class:`~scim2_models.Context` in which the validation happens.
        :param scim_policy: The :class:`~scim2_models.ScimPolicy` the validation
            runs under. Defaults to the strict reading of the specification.
        :param scim_provider: The :class:`~scim2_models.ScimProvider` describing
            the service the payload belongs to. Defaults to the provider of the
            innermost open block, if any.
        :param scim_spc: The
            :class:`~scim2_models.ServiceProviderConfig` the peer publishes,
            which overrides the one *scim_provider* carries.
        """
        validate_kwargs = cls._prepare_model_validate(
            scim_ctx,
            scim_policy=scim_policy,
            scim_provider=scim_provider,
            scim_spc=scim_spc,
            **kwargs,
        )
        return super().model_validate_json(*args, **validate_kwargs)

    def _prepare_model_dump(
        self,
        scim_ctx: Context | None = Context.DEFAULT,
        attributes: list["str | Path[Any]"] | None = None,
        excluded_attributes: list["str | Path[Any]"] | None = None,
        scim_policy: ScimPolicy | None = None,
        scim_provider: "ScimProvider | None" = None,
        scim_spc: "ServiceProviderConfig | None" = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        context = kwargs.setdefault("context", {})
        context.setdefault("scim", scim_ctx)
        context.setdefault("scim_policy", scim_policy)
        context.setdefault("scim_provider", scim_provider)
        context.setdefault("scim_spc", scim_spc)

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

    @staticmethod
    def _attribute_selection(
        response_parameters: "ResponseParameters[Any] | None",
        attributes: list["str | Path[Any]"] | None,
        excluded_attributes: list["str | Path[Any]"] | None,
    ) -> tuple[list["str | Path[Any]"] | None, list["str | Path[Any]"] | None]:
        """Read the attribute selection of a dump, from either spelling."""
        if response_parameters is None:
            if attributes is not None or excluded_attributes is not None:
                warnings.warn(
                    "The 'attributes' and 'excluded_attributes' parameters are "
                    "deprecated, pass a ResponseParameters as 'response_parameters' "
                    "instead. Will be removed in 0.9.0.",
                    DeprecationWarning,
                    stacklevel=3,
                )
            return attributes, excluded_attributes

        if attributes is not None or excluded_attributes is not None:
            raise TypeError(
                "Cannot pass both 'response_parameters' and "
                "'attributes' or 'excluded_attributes'"
            )
        # les listes de ResponseParameters sont invariantes, on les recopie élargies
        selected: list[str | Path[Any]] | None = (
            list(response_parameters.attributes)
            if response_parameters.attributes is not None
            else None
        )
        excluded: list[str | Path[Any]] | None = (
            list(response_parameters.excluded_attributes)
            if response_parameters.excluded_attributes is not None
            else None
        )
        return selected, excluded

    def model_dump(
        self,
        *args: Any,
        scim_ctx: Context | None = Context.DEFAULT,
        response_parameters: "ResponseParameters[Any] | None" = None,
        attributes: list["str | Path[Any]"] | None = None,
        excluded_attributes: list["str | Path[Any]"] | None = None,
        scim_policy: ScimPolicy | None = None,
        scim_provider: "ScimProvider | None" = None,
        scim_spc: "ServiceProviderConfig | None" = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Create a model representation that can be included in SCIM messages by using Pydantic :code:`BaseModel.model_dump`.

        :param scim_ctx: If a SCIM context is passed, some default values of
            Pydantic :code:`BaseModel.model_dump` are tuned to generate valid SCIM
            messages. Pass :data:`None` to get the default Pydantic behavior.
        :param response_parameters: The
            :class:`~scim2_models.ResponseParameters` a client sent, whose
            ``attributes`` and ``excludedAttributes`` select what the dump
            carries. A :class:`~scim2_models.SearchRequest` is one, so a server
            may pass the request it received.
        :param attributes: A multi-valued list of strings indicating the names of resource
            attributes to return in the response, overriding the set of attributes that
            would be returned by default. Invalid values are ignored.

            .. deprecated:: 0.8.0
                Pass a :class:`~scim2_models.ResponseParameters` as
                *response_parameters* instead. Will be removed in 0.9.0.
        :param excluded_attributes: A multi-valued list of strings indicating the names of resource
            attributes to be removed from the default set of attributes to return. Invalid values are ignored.

            .. deprecated:: 0.8.0
                Pass a :class:`~scim2_models.ResponseParameters` as
                *response_parameters* instead. Will be removed in 0.9.0.
        :param scim_policy: The :class:`~scim2_models.ScimPolicy` the
            serialization runs under. Defaults to the strict reading of the
            specification.
        :param scim_provider: The :class:`~scim2_models.ScimProvider` describing
            the service the payload belongs to. Defaults to the provider of the
            innermost open block, if any.
        :param scim_spc: The
            :class:`~scim2_models.ServiceProviderConfig` the peer publishes,
            which overrides the one *scim_provider* carries.
        """
        attributes, excluded_attributes = self._attribute_selection(
            response_parameters, attributes, excluded_attributes
        )
        dump_kwargs = self._prepare_model_dump(
            scim_ctx,
            attributes=attributes,
            excluded_attributes=excluded_attributes,
            scim_policy=scim_policy,
            scim_provider=scim_provider,
            scim_spc=scim_spc,
            **kwargs,
        )
        if scim_ctx:
            dump_kwargs.setdefault("mode", "json")
        return super().model_dump(*args, **dump_kwargs)

    def model_dump_json(
        self,
        *args: Any,
        scim_ctx: Context | None = Context.DEFAULT,
        response_parameters: "ResponseParameters[Any] | None" = None,
        attributes: list["str | Path[Any]"] | None = None,
        excluded_attributes: list["str | Path[Any]"] | None = None,
        scim_policy: ScimPolicy | None = None,
        scim_provider: "ScimProvider | None" = None,
        scim_spc: "ServiceProviderConfig | None" = None,
        **kwargs: Any,
    ) -> str:
        """Create a JSON model representation that can be included in SCIM messages by using Pydantic :code:`BaseModel.model_dump_json`.

        :param scim_ctx: If a SCIM context is passed, some default values of
            Pydantic :code:`BaseModel.model_dump` are tuned to generate valid SCIM
            messages. Pass :data:`None` to get the default Pydantic behavior.
        :param response_parameters: The
            :class:`~scim2_models.ResponseParameters` a client sent, whose
            ``attributes`` and ``excludedAttributes`` select what the dump
            carries. A :class:`~scim2_models.SearchRequest` is one, so a server
            may pass the request it received.
        :param attributes: A multi-valued list of strings indicating the names of resource
            attributes to return in the response, overriding the set of attributes that
            would be returned by default. Invalid values are ignored.

            .. deprecated:: 0.8.0
                Pass a :class:`~scim2_models.ResponseParameters` as
                *response_parameters* instead. Will be removed in 0.9.0.
        :param excluded_attributes: A multi-valued list of strings indicating the names of resource
            attributes to be removed from the default set of attributes to return. Invalid values are ignored.

            .. deprecated:: 0.8.0
                Pass a :class:`~scim2_models.ResponseParameters` as
                *response_parameters* instead. Will be removed in 0.9.0.
        :param scim_policy: The :class:`~scim2_models.ScimPolicy` the
            serialization runs under. Defaults to the strict reading of the
            specification.
        :param scim_provider: The :class:`~scim2_models.ScimProvider` describing
            the service the payload belongs to. Defaults to the provider of the
            innermost open block, if any.
        :param scim_spc: The
            :class:`~scim2_models.ServiceProviderConfig` the peer publishes,
            which overrides the one *scim_provider* carries.
        """
        attributes, excluded_attributes = self._attribute_selection(
            response_parameters, attributes, excluded_attributes
        )
        dump_kwargs = self._prepare_model_dump(
            scim_ctx,
            attributes=attributes,
            excluded_attributes=excluded_attributes,
            scim_policy=scim_policy,
            scim_provider=scim_provider,
            scim_spc=scim_spc,
            **kwargs,
        )
        return super().model_dump_json(*args, **dump_kwargs)
