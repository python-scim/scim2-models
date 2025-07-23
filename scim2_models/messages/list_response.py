from typing import Annotated
from typing import Any
from typing import Generic
from typing import Optional

from pydantic import Field
from pydantic import ValidationInfo
from pydantic import ValidatorFunctionWrapHandler
from pydantic import model_validator
from pydantic_core import PydanticCustomError
from typing_extensions import Self

from ..annotations import Required
from ..context import Context
from ..resources.resource import AnyResource
from .message import Message
from .message import _GenericMessageMetaclass


class ListResponse(Message, Generic[AnyResource], metaclass=_GenericMessageMetaclass):
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
        assert isinstance(obj, cls)

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
