from enum import Enum
from typing import Annotated
from typing import Any

from pydantic import Field
from pydantic import PlainSerializer
from pydantic import ValidationInfo
from pydantic import model_validator
from typing_extensions import Self

from ..annotations import Required
from ..annotations import Returned
from ..attributes import ComplexAttribute
from ..context import Context
from ..exceptions import InvalidValueException
from ..path import URN
from ..utils import _int_to_str
from .message import Message


class BulkOperation(ComplexAttribute):
    class Method(str, Enum):
        post = "POST"
        put = "PUT"
        patch = "PATCH"
        delete = "DELETE"

    method: Annotated[Method | None, Required.true] = None
    """The HTTP method of the current operation."""

    bulk_id: str | None = None
    """The transient identifier of a newly created resource, unique within a
    bulk request and created by the client."""

    version: str | None = None
    """The current resource version."""

    path: Annotated[str | None, Returned.never] = None
    """The resource's relative path to the SCIM service provider's root."""

    data: Annotated[Any | None, Returned.never] = None
    """The resource data as it would appear for a single SCIM POST, PUT, or
    PATCH operation."""

    location: str | None = None
    """The resource endpoint URL."""

    response: Any | None = None
    """The HTTP response body for the specified request operation."""

    status: Annotated[int | None, PlainSerializer(_int_to_str)] = None
    """The HTTP response status code for the requested operation."""

    @model_validator(mode="after")
    def validate_operation_requirements(self, info: ValidationInfo) -> Self:
        """Validate operation requirements according to RFC 7644."""
        scim_ctx = info.context.get("scim") if info.context else None
        if scim_ctx and Context.is_request(scim_ctx) or scim_ctx == Context.DEFAULT:
            # RFC 7644 Section 3.7: "path [...] REQUIRED in a request."
            if self.path is None:
                raise InvalidValueException(
                    detail="path is required for request operations"
                ).as_pydantic_error()
            if self.method in (
                BulkOperation.Method.post,
                BulkOperation.Method.put,
                BulkOperation.Method.patch,
            ):
                # RFC 7644 Section 3.7: "data  The resource data as it would appear for a single SCIM POST,
                # PUT, or PATCH operation.  REQUIRED in a request when "method" is "POST", "PUT", or "PATCH"."
                if self.data is None:
                    raise InvalidValueException(
                        detail="data is required for POST, PUT, or PATCH request operations"
                    ).as_pydantic_error()
        elif scim_ctx and Context.is_response(scim_ctx):  # pragma: no branch
            # RFC 7644 Section 3.7: "location  The resource endpoint URL.  REQUIRED in a response,
            # except in the event of a POST failure."
            if self.location is None and not (
                self.method == BulkOperation.Method.post
                and self.status is not None
                and self.status >= 400
            ):
                raise InvalidValueException(
                    detail="location is required for response"
                ).as_pydantic_error()

            # RFC 7644 Section 3.7: "When indicating a response with an HTTP status
            # other than a 200-series response, the response body MUST be included.
            # [...] When indicating an error, the "response" attribute MUST contain
            # the detail error response
            if (
                self.status is not None
                and self.status >= 400
                and not (self.response and self.response.get("detail"))
            ):
                raise InvalidValueException(
                    detail="response error detail is required"
                ).as_pydantic_error()

        # RFC 7644 Section 3.7: "bulkId [...] REQUIRED when "method" is "POST"."
        if self.method == BulkOperation.Method.post and self.bulk_id is None:
            raise InvalidValueException(
                detail="bulkId is required for POST operations"
            ).as_pydantic_error()

        return self


class BulkRequest(Message):
    """Bulk request as defined in :rfc:`RFC7644 §3.7 <7644#section-3.7>`."""

    __schema__ = URN("urn:ietf:params:scim:api:messages:2.0:BulkRequest")

    fail_on_errors: int | None = None
    """An integer specifying the number of errors that the service provider
    will accept before the operation is terminated and an error response is
    returned."""

    operations: Annotated[list[BulkOperation] | None, Required.true] = Field(
        None, serialization_alias="Operations"
    )
    """Defines operations within a bulk job."""


class BulkResponse(Message):
    """Bulk response as defined in :rfc:`RFC7644 §3.7 <7644#section-3.7>`."""

    __schema__ = URN("urn:ietf:params:scim:api:messages:2.0:BulkResponse")

    operations: Annotated[list[BulkOperation] | None, Required.true] = Field(
        None, serialization_alias="Operations"
    )
    """Defines operations within a bulk job."""
