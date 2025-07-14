from inspect import isclass
from typing import Any
from typing import Optional
from typing import get_args
from typing import get_origin

from pydantic import AliasGenerator
from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict
from pydantic import FieldSerializationInfo
from pydantic import SerializationInfo
from pydantic import SerializerFunctionWrapHandler
from pydantic import ValidationInfo
from pydantic import ValidatorFunctionWrapHandler
from pydantic import field_serializer
from pydantic import field_validator
from pydantic import model_serializer
from pydantic import model_validator
from pydantic_core import PydanticCustomError
from typing_extensions import Self

from scim2_models.annotations import Mutability
from scim2_models.annotations import Required
from scim2_models.annotations import Returned
from scim2_models.context import Context
from scim2_models.utils import normalize_attribute_name
from scim2_models.utils import to_camel

from .utils import UNION_TYPES


def validate_model_attribute(model: type["BaseModel"], attribute_base: str) -> None:
    """Validate that an attribute name or a sub-attribute path exist for a given model."""
    from scim2_models.base import BaseModel

    attribute_name, *sub_attribute_blocks = attribute_base.split(".")
    sub_attribute_base = ".".join(sub_attribute_blocks)

    aliases = {field.validation_alias for field in model.model_fields.values()}

    if normalize_attribute_name(attribute_name) not in aliases:
        raise ValueError(
            f"Model '{model.__name__}' has no attribute named '{attribute_name}'"
        )

    if sub_attribute_base:
        attribute_type = model.get_field_root_type(attribute_name)

        if not attribute_type or not issubclass(attribute_type, BaseModel):
            raise ValueError(
                f"Attribute '{attribute_name}' is not a complex attribute, and cannot have a '{sub_attribute_base}' sub-attribute"
            )

        validate_model_attribute(attribute_type, sub_attribute_base)


def extract_schema_and_attribute_base(attribute_urn: str) -> tuple[str, str]:
    # Extract the schema urn part and the attribute name part from attribute
    # name, as defined in :rfc:`RFC7644 §3.10 <7644#section-3.10>`.

    *urn_blocks, attribute_base = attribute_urn.split(":")
    schema = ":".join(urn_blocks)
    return schema, attribute_base


def validate_attribute_urn(
    attribute_name: str,
    default_resource: Optional[type["BaseModel"]] = None,
    resource_types: Optional[list[type["BaseModel"]]] = None,
) -> str:
    """Validate that an attribute urn is valid or not.

    :param attribute_name: The attribute urn to check.
    :default_resource: The default resource if `attribute_name` is not an absolute urn.
    :resource_types: The available resources in which to look for the attribute.
    :return: The normalized attribute URN.
    """
    from scim2_models.rfc7643.resource import Resource

    if not resource_types:
        resource_types = []

    if default_resource and default_resource not in resource_types:
        resource_types.append(default_resource)

    default_schema = (
        default_resource.model_fields["schemas"].default[0]
        if default_resource
        else None
    )

    schema: Optional[Any]
    schema, attribute_base = extract_schema_and_attribute_base(attribute_name)
    if not schema:
        schema = default_schema

    if not schema:
        raise ValueError("No default schema and relative URN")

    resource = Resource.get_by_schema(resource_types, schema)
    if not resource:
        raise ValueError(f"No resource matching schema '{schema}'")

    validate_model_attribute(resource, attribute_base)

    return f"{schema}:{attribute_base}"


def contains_attribute_or_subattributes(
    attribute_urns: list[str], attribute_urn: str
) -> bool:
    return attribute_urn in attribute_urns or any(
        item.startswith(f"{attribute_urn}.") or item.startswith(f"{attribute_urn}:")
        for item in attribute_urns
    )


class BaseModel(PydanticBaseModel):
    """Base Model for everything."""

    model_config = ConfigDict(
        alias_generator=AliasGenerator(
            validation_alias=normalize_attribute_name,
            serialization_alias=to_camel,
        ),
        validate_assignment=True,
        populate_by_name=True,
        use_attribute_docstrings=True,
        extra="forbid",
    )

    @classmethod
    def get_field_annotation(cls, field_name: str, annotation_type: type) -> Any:
        """Return the annotation of type 'annotation_type' of the field 'field_name'."""
        field_metadata = cls.model_fields[field_name].metadata

        default_value = getattr(annotation_type, "_default", None)

        def annotation_type_filter(item: Any) -> bool:
            return isinstance(item, annotation_type)

        field_annotation = next(
            filter(annotation_type_filter, field_metadata), default_value
        )
        return field_annotation

    @classmethod
    def get_field_root_type(cls, attribute_name: str) -> Optional[type]:
        """Extract the root type from a model field.

        For example, return 'GroupMember' for
        'Optional[List[GroupMember]]'
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
        """Indicate whether a field holds multiple values."""
        attribute_type = cls.model_fields[attribute_name].annotation

        # extract 'x' from 'Optional[x]'
        if get_origin(attribute_type) in UNION_TYPES:
            attribute_type = get_args(attribute_type)[0]

        origin = get_origin(attribute_type)
        return isinstance(origin, type) and issubclass(origin, list)

    @field_validator("*")
    @classmethod
    def check_request_attributes_mutability(
        cls, value: Any, info: ValidationInfo
    ) -> Any:
        """Check and fix that the field mutability is expected according to the requests validation context, as defined in :rfc:`RFC7643 §7 <7653#section-7>`."""
        if (
            not info.context
            or not info.context.get("scim")
            or not Context.is_request(info.context["scim"])
        ):
            return value

        context = info.context.get("scim")
        mutability = cls.get_field_annotation(info.field_name, Mutability)
        exc = PydanticCustomError(
            "mutability_error",
            "Field '{field_name}' has mutability '{field_mutability}' but this in not valid in {context} context",
            {
                "field_name": info.field_name,
                "field_mutability": mutability,
                "context": context.name.lower().replace("_", " "),
            },
        )

        if (
            context in (Context.RESOURCE_QUERY_REQUEST, Context.SEARCH_REQUEST)
            and mutability == Mutability.write_only
        ):
            raise exc

        if (
            context
            in (Context.RESOURCE_CREATION_REQUEST, Context.RESOURCE_REPLACEMENT_REQUEST)
            and mutability == Mutability.read_only
        ):
            return None

        return value

    @model_validator(mode="wrap")
    @classmethod
    def normalize_attribute_names(
        cls, value: Any, handler: ValidatorFunctionWrapHandler, info: ValidationInfo
    ) -> Self:
        """Normalize payload attribute names.

        :rfc:`RFC7643 §2.1 <7653#section-2.1>` indicate that attribute
        names should be case-insensitive. Any attribute name is
        transformed in lowercase so any case is handled the same way.
        """

        def normalize_value(value: Any) -> Any:
            if isinstance(value, dict):
                return {
                    normalize_attribute_name(k): normalize_value(v)
                    for k, v in value.items()
                }
            return value

        normalized_value = normalize_value(value)
        return handler(normalized_value)

    @model_validator(mode="wrap")
    @classmethod
    def check_response_attributes_returnability(
        cls, value: Any, handler: ValidatorFunctionWrapHandler, info: ValidationInfo
    ) -> Self:
        """Check that the fields returnability is expected according to the responses validation context, as defined in :rfc:`RFC7643 §7 <7653#section-7>`."""
        value = handler(value)

        if (
            not info.context
            or not info.context.get("scim")
            or not Context.is_response(info.context["scim"])
        ):
            return value

        for field_name in cls.model_fields:
            returnability = cls.get_field_annotation(field_name, Returned)

            if returnability == Returned.always and getattr(value, field_name) is None:
                raise PydanticCustomError(
                    "returned_error",
                    "Field '{field_name}' has returnability 'always' but value is missing or null",
                    {
                        "field_name": field_name,
                    },
                )

            if (
                returnability == Returned.never
                and getattr(value, field_name) is not None
            ):
                raise PydanticCustomError(
                    "returned_error",
                    "Field '{field_name}' has returnability 'never' but value is set",
                    {
                        "field_name": field_name,
                    },
                )

        return value

    @model_validator(mode="wrap")
    @classmethod
    def check_response_attributes_necessity(
        cls, value: Any, handler: ValidatorFunctionWrapHandler, info: ValidationInfo
    ) -> Self:
        """Check that the required attributes are present in creations and replacement requests."""
        value = handler(value)

        if (
            not info.context
            or not info.context.get("scim")
            or info.context["scim"]
            not in (
                Context.RESOURCE_CREATION_REQUEST,
                Context.RESOURCE_REPLACEMENT_REQUEST,
            )
        ):
            return value

        for field_name in cls.model_fields:
            necessity = cls.get_field_annotation(field_name, Required)

            if necessity == Required.true and getattr(value, field_name) is None:
                raise PydanticCustomError(
                    "required_error",
                    "Field '{field_name}' is required but value is missing or null",
                    {
                        "field_name": field_name,
                    },
                )

        return value

    @model_validator(mode="wrap")
    @classmethod
    def check_replacement_request_mutability(
        cls, value: Any, handler: ValidatorFunctionWrapHandler, info: ValidationInfo
    ) -> Self:
        """Check if 'immutable' attributes have been mutated in replacement requests."""
        from scim2_models.rfc7643.resource import Resource

        value = handler(value)

        context = info.context.get("scim") if info.context else None
        original = info.context.get("original") if info.context else None
        if (
            context == Context.RESOURCE_REPLACEMENT_REQUEST
            and issubclass(cls, Resource)
            and original is not None
        ):
            cls.check_mutability_issues(original, value)
        return value

    @classmethod
    def check_mutability_issues(
        cls, original: "BaseModel", replacement: "BaseModel"
    ) -> None:
        """Compare two instances, and check for differences of values on the fields marked as immutable."""
        from .attributes import is_complex_attribute

        model = replacement.__class__
        for field_name in model.model_fields:
            mutability = model.get_field_annotation(field_name, Mutability)
            if mutability == Mutability.immutable and getattr(
                original, field_name
            ) != getattr(replacement, field_name):
                raise PydanticCustomError(
                    "mutability_error",
                    "Field '{field_name}' is immutable but the request value is different than the original value.",
                    {"field_name": field_name},
                )

            attr_type = model.get_field_root_type(field_name)
            if (
                attr_type
                and is_complex_attribute(attr_type)
                and not model.get_field_multiplicity(field_name)
            ):
                original_val = getattr(original, field_name)
                replacement_value = getattr(replacement, field_name)
                if original_val is not None and replacement_value is not None:
                    cls.check_mutability_issues(original_val, replacement_value)

    def set_complex_attribute_urns(self) -> None:
        """Navigate through attributes and sub-attributes of type ComplexAttribute, and mark them with a 'attribute_urn' attribute.

        'attribute_urn' will later be used by 'get_attribute_urn'.
        """
        from scim2_models.rfc7643.resource import Resource

        from .attributes import is_complex_attribute

        for field_name in self.__class__.model_fields:
            attr_type = self.get_field_root_type(field_name)
            if not attr_type or not is_complex_attribute(attr_type):
                continue

            main_schema = (
                getattr(self, "attribute_urn", None)
                or self.__class__.model_fields["schemas"].default[0]
            )

            separator = ":" if isinstance(self, Resource) else "."
            schema = f"{main_schema}{separator}{field_name}"

            if attr_value := getattr(self, field_name):
                if isinstance(attr_value, list):
                    for item in attr_value:
                        item.attribute_urn = schema
                else:
                    attr_value.attribute_urn = schema

    @field_serializer("*", mode="wrap")
    def scim_serializer(
        self,
        value: Any,
        handler: SerializerFunctionWrapHandler,
        info: FieldSerializationInfo,
    ) -> Any:
        """Serialize the fields according to mutability indications passed in the serialization context."""
        value = handler(value)
        scim_ctx = info.context.get("scim") if info.context else None

        if scim_ctx and Context.is_request(scim_ctx):
            value = self.scim_request_serializer(value, info)

        if scim_ctx and Context.is_response(scim_ctx):
            value = self.scim_response_serializer(value, info)

        return value

    def scim_request_serializer(self, value: Any, info: FieldSerializationInfo) -> Any:
        """Serialize the fields according to mutability indications passed in the serialization context."""
        mutability = self.get_field_annotation(info.field_name, Mutability)
        scim_ctx = info.context.get("scim") if info.context else None

        if (
            scim_ctx
            in (Context.RESOURCE_CREATION_REQUEST, Context.RESOURCE_REPLACEMENT_REQUEST)
            and mutability == Mutability.read_only
        ):
            return None

        if (
            scim_ctx
            in (
                Context.RESOURCE_QUERY_REQUEST,
                Context.SEARCH_REQUEST,
            )
            and mutability == Mutability.write_only
        ):
            return None

        return value

    def scim_response_serializer(self, value: Any, info: FieldSerializationInfo) -> Any:
        """Serialize the fields according to returnability indications passed in the serialization context."""
        returnability = self.get_field_annotation(info.field_name, Returned)
        attribute_urn = self.get_attribute_urn(info.field_name)
        included_urns = info.context.get("scim_attributes", []) if info.context else []
        excluded_urns = (
            info.context.get("scim_excluded_attributes", []) if info.context else []
        )

        attribute_urn = normalize_attribute_name(attribute_urn)
        included_urns = [normalize_attribute_name(urn) for urn in included_urns]
        excluded_urns = [normalize_attribute_name(urn) for urn in excluded_urns]

        if returnability == Returned.never:
            return None

        if returnability == Returned.default and (
            (
                included_urns
                and not contains_attribute_or_subattributes(
                    included_urns, attribute_urn
                )
            )
            or attribute_urn in excluded_urns
        ):
            return None

        if returnability == Returned.request and attribute_urn not in included_urns:
            return None

        return value

    @model_serializer(mode="wrap")
    def model_serializer_exclude_none(
        self, handler: SerializerFunctionWrapHandler, info: SerializationInfo
    ) -> dict[str, Any]:
        """Remove `None` values inserted by the :meth:`~scim2_models.base.BaseModel.scim_serializer`."""
        self.set_complex_attribute_urns()
        result = handler(self)
        return {key: value for key, value in result.items() if value is not None}

    @classmethod
    def model_validate(
        cls,
        *args,
        scim_ctx: Optional[Context] = Context.DEFAULT,
        original: Optional["BaseModel"] = None,
        **kwargs: Any,
    ) -> Self:
        """Validate SCIM payloads and generate model representation by using Pydantic :code:`BaseModel.model_validate`.

        :param scim_ctx: The SCIM :class:`~scim2_models.Context` in which the validation happens.
        :param original: If this parameter is set during :attr:`~Context.RESOURCE_REPLACEMENT_REQUEST`,
            :attr:`~scim2_models.Mutability.immutable` parameters will be compared against the *original* model value.
            An exception is raised if values are different.
        """
        context = kwargs.setdefault("context", {})
        context.setdefault("scim", scim_ctx)
        context.setdefault("original", original)

        if scim_ctx == Context.RESOURCE_REPLACEMENT_REQUEST and original is None:
            raise ValueError(
                "Resource queries replacement validation must compare to an original resource"
            )

        return super().model_validate(*args, **kwargs)

    def _prepare_model_dump(
        self,
        scim_ctx: Optional[Context] = Context.DEFAULT,
        attributes: Optional[list[str]] = None,
        excluded_attributes: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        kwargs.setdefault("context", {}).setdefault("scim", scim_ctx)
        kwargs["context"]["scim_attributes"] = [
            validate_attribute_urn(attribute, self.__class__)
            for attribute in (attributes or [])
        ]
        kwargs["context"]["scim_excluded_attributes"] = [
            validate_attribute_urn(attribute, self.__class__)
            for attribute in (excluded_attributes or [])
        ]

        if scim_ctx:
            kwargs.setdefault("exclude_none", True)
            kwargs.setdefault("by_alias", True)

        return kwargs

    def model_dump(
        self,
        *args: Any,
        scim_ctx: Optional[Context] = Context.DEFAULT,
        attributes: Optional[list[str]] = None,
        excluded_attributes: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> dict:
        """Create a model representation that can be included in SCIM messages by using Pydantic :code:`BaseModel.model_dump`.

        :param scim_ctx: If a SCIM context is passed, some default values of
            Pydantic :code:`BaseModel.model_dump` are tuned to generate valid SCIM
            messages. Pass :data:`None` to get the default Pydantic behavior.
        """
        dump_kwargs = self._prepare_model_dump(
            scim_ctx, attributes, excluded_attributes, **kwargs
        )
        if scim_ctx:
            dump_kwargs.setdefault("mode", "json")
        return super().model_dump(*args, **dump_kwargs)

    def model_dump_json(
        self,
        *args: Any,
        scim_ctx: Optional[Context] = Context.DEFAULT,
        attributes: Optional[list[str]] = None,
        excluded_attributes: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> str:
        """Create a JSON model representation that can be included in SCIM messages by using Pydantic :code:`BaseModel.model_dump_json`.

        :param scim_ctx: If a SCIM context is passed, some default values of
            Pydantic :code:`BaseModel.model_dump` are tuned to generate valid SCIM
            messages. Pass :data:`None` to get the default Pydantic behavior.
        """
        dump_kwargs = self._prepare_model_dump(
            scim_ctx, attributes, excluded_attributes, **kwargs
        )
        return super().model_dump_json(*args, **dump_kwargs)

    def get_attribute_urn(self, field_name: str) -> str:
        """Build the full URN of the attribute.

        See :rfc:`RFC7644 §3.10 <7644#section-3.10>`.
        """
        main_schema = self.__class__.model_fields["schemas"].default[0]
        alias = (
            self.__class__.model_fields[field_name].serialization_alias or field_name
        )

        # if alias contains a ':' this is an extension urn
        full_urn = alias if ":" in alias else f"{main_schema}:{alias}"
        return full_urn


BaseModelType: type = type(BaseModel)
