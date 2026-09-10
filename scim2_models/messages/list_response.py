from typing import Any
from typing import Generic

from pydantic import Field
from pydantic import ValidationInfo
from pydantic import ValidatorFunctionWrapHandler
from pydantic import model_validator
from pydantic_core import PydanticCustomError
from typing_extensions import Self

from ..context import Context
from ..resources.resource import AnyResource
from ..urn import URN
from .message import Message
from .message import _GenericMessageMetaclass


class ListResponse(Message, Generic[AnyResource], metaclass=_GenericMessageMetaclass):
    """A paginated list response as defined in :rfc:`RFC7644 §3.4.2 <7644#section-3.4.2>`.

    Parameterise the response with the type of resource an endpoint returns.
    The resource list serializes under SCIM's ``Resources`` name:

    >>> from scim2_models import Context, ListResponse, User
    >>> response = ListResponse[User](
    ...     total_results=1,
    ...     start_index=1,
    ...     items_per_page=1,
    ...     resources=[User(user_name="bjensen")],
    ... )
    >>> response.model_dump(scim_ctx=Context.RESOURCE_QUERY_RESPONSE)["Resources"]
    [{'schemas': ['urn:ietf:params:scim:schemas:core:2.0:User'], 'userName': 'bjensen'}]
    """

    __schema__ = URN("urn:ietf:params:scim:api:messages:2.0:ListResponse")

    total_results: int | None = None
    """The total number of results returned by the list or query operation."""

    start_index: int | None = None
    """The 1-based index of the first result in the current set of list
    results."""

    items_per_page: int | None = None
    """The number of resources returned in a list response page."""

    resources: list[AnyResource] | None = Field(None, serialization_alias="Resources")
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

        if obj.total_results > 0 and obj.resources is None:
            raise PydanticCustomError(
                "no_resource_error",
                "Field 'resources' is missing or null but 'total_results' is non-zero.",
            )

        return obj
