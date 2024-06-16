from typing import Any
from typing import Generic
from typing import List
from typing import Optional
from typing import Union

from pydantic import Field
from pydantic import ValidationInfo
from pydantic import ValidatorFunctionWrapHandler
from pydantic import model_validator
from pydantic_core import PydanticCustomError
from typing_extensions import Self

from ..base import Context
from ..rfc7643.resource import AnyResource
from ..rfc7643.resource import tagged_resource_union
from .message import Message


class ListResponse(Message, Generic[AnyResource]):
    @classmethod
    def of(cls, *resource_types: AnyResource):
        """Build a ListResponse instance that can handle resource_types."""

        return cls[tagged_resource_union(Union[resource_types])]

    schemas: List[str] = ["urn:ietf:params:scim:api:messages:2.0:ListResponse"]

    total_results: int = None
    """The total number of results returned by the list or query operation."""

    start_index: Optional[int] = None
    """The 1-based index of the first result in the current set of list
    results."""

    items_per_page: Optional[int] = None
    """The number of resources returned in a list response page."""

    resources: Optional[List[AnyResource]] = Field(None, alias="Resources")
    """A multi-valued list of complex objects containing the requested
    resources."""

    @model_validator(mode="wrap")
    @classmethod
    def check_response_attributes_returnability(
        cls, value: Any, handler: ValidatorFunctionWrapHandler, info: ValidationInfo
    ) -> Self:
        """:rfc:`RFC7644 §3.4.2 <7644#section-3.4.2.4>` indicates that
        'resources' must be set if 'totalResults' is non-zero."""

        obj = handler(value)

        if (
            not info.context
            or not info.context.get("scim")
            or not Context.is_response(info.context["scim"])
        ):
            return obj

        if obj.total_results > 0 and not obj.resources:
            raise PydanticCustomError(
                "no_resource_error",
                "Field 'resources' is missing or null but 'total_results' is non-zero.",
            )

        return obj
