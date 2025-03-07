from typing import Annotated
from typing import Any
from typing import Generic
from typing import Optional
from typing import Union
from typing import get_args
from typing import get_origin

from pydantic import Discriminator
from pydantic import Field
from pydantic import Tag
from pydantic import ValidationInfo
from pydantic import ValidatorFunctionWrapHandler
from pydantic import model_validator
from pydantic_core import PydanticCustomError
from typing_extensions import Self

from ..base import BaseModel
from ..base import BaseModelType
from ..base import Context
from ..base import Required
from ..rfc7643.resource import AnyResource
from .message import Message


class ListResponseMetaclass(BaseModelType):
    def tagged_resource_union(resource_union):
        """Build Discriminated Unions, so pydantic can guess which class are needed to instantiate by inspecting a payload.

        https://docs.pydantic.dev/latest/concepts/unions/#discriminated-unions
        """
        if not get_origin(resource_union) == Union:
            return resource_union

        resource_types = get_args(resource_union)

        def get_schema_from_payload(payload: Any) -> Optional[str]:
            if not payload:
                return None

            payload_schemas = (
                payload.get("schemas", [])
                if isinstance(payload, dict)
                else payload.schemas
            )

            resource_types_schemas = [
                resource_type.model_fields["schemas"].default[0]
                for resource_type in resource_types
            ]
            common_schemas = [
                schema for schema in payload_schemas if schema in resource_types_schemas
            ]
            return common_schemas[0] if common_schemas else None

        discriminator = Discriminator(get_schema_from_payload)

        def get_tag(resource_type: type[BaseModel]) -> Tag:
            return Tag(resource_type.model_fields["schemas"].default[0])

        tagged_resources = [
            Annotated[resource_type, get_tag(resource_type)]
            for resource_type in resource_types
        ]
        union = Union[tuple(tagged_resources)]
        return Annotated[union, discriminator]

    def __new__(cls, name, bases, attrs, **kwargs):
        if kwargs.get("__pydantic_generic_metadata__") and kwargs[
            "__pydantic_generic_metadata__"
        ].get("args"):
            tagged_union = cls.tagged_resource_union(
                kwargs["__pydantic_generic_metadata__"]["args"][0]
            )
            kwargs["__pydantic_generic_metadata__"]["args"] = (tagged_union,)

        klass = super().__new__(cls, name, bases, attrs, **kwargs)
        return klass


class ListResponse(Message, Generic[AnyResource], metaclass=ListResponseMetaclass):
    schemas: Annotated[list[str], Required.true] = [
        "urn:ietf:params:scim:api:messages:2.0:ListResponse"
    ]

    total_results: Optional[int] = None
    """The total number of results returned by the list or query operation."""

    start_index: Optional[int] = None
    """The 1-based index of the first result in the current set of list
    results."""

    items_per_page: Optional[int] = None
    """The number of resources returned in a list response page."""

    resources: Optional[list[AnyResource]] = Field(
        None, serialization_alias="Resources"
    )
    """A multi-valued list of complex objects containing the requested
    resources."""

    @model_validator(mode="wrap")
    @classmethod
    def check_results_number(
        cls, value: Any, handler: ValidatorFunctionWrapHandler, info: ValidationInfo
    ) -> Self:
        """Validate result numbers.

        :rfc:`RFC7644 §3.4.2 <7644#section-3.4.2.4>` indicates that:

        - 'totalResults' is required
        - 'resources' must be set if 'totalResults' is non-zero.
        """
        obj = handler(value)

        if (
            not info.context
            or not info.context.get("scim")
            or not Context.is_response(info.context["scim"])
        ):
            return obj

        if obj.total_results is None:
            raise PydanticCustomError(
                "required_error",
                "Field 'total_results' is required but value is missing or null",
            )

        if obj.total_results > 0 and not obj.resources:
            raise PydanticCustomError(
                "no_resource_error",
                "Field 'resources' is missing or null but 'total_results' is non-zero.",
            )

        return obj
