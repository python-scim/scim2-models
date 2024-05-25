from enum import Enum
from typing import Any
from typing import List
from typing import Optional

from pydantic import Field
from pydantic import field_serializer

from ..base import SCIM2Model


class BulkOperation(SCIM2Model):
    class Method(str, Enum):
        post = "POST"
        put = "PUT"
        patch = "PATCH"
        delete = "DELETE"

    method: Method
    """The HTTP method of the current operation."""

    bulk_id: Optional[str] = None
    """The transient identifier of a newly created resource, unique within a
    bulk request and created by the client."""
    # TODO:  REQUIRED when "method" is "POST".

    version: Optional[str] = None
    """The current resource version."""

    path: Optional[str] = None
    """The resource's relative path to the SCIM service provider's root."""
    # TODO: REQUIRED in a request. (so not in a response)

    data: Optional[Any] = None
    """The resource data as it would appear for a single SCIM POST, PUT, or
    PATCH operation."""
    # TODO: REQUIRED in a request when "method" is "POST", "PUT", or "PATCH".

    location: Optional[str] = None
    """The resource endpoint URL."""
    # TODO: REQUIRED in a response, except in the event of a POST failure.

    response: Optional[Any] = None
    """The HTTP response body for the specified request operation."""

    status: Optional[int] = None
    """The HTTP response status code for the requested operation."""

    @field_serializer("status")
    def serialize_int_to_string(status: Optional[int]):
        if status is not None:
            return str(status)


class BulkRequest(SCIM2Model):
    schemas: List[str] = ["urn:ietf:params:scim:api:messages:2.0:BulkRequest"]

    fail_on_errors: Optional[int] = None
    """An integer specifying the number of errors that the service provider
    will accept before the operation is terminated and an error response is
    returned."""

    operations: List[BulkOperation] = Field(..., alias="Operations")
    """Defines operations within a bulk job."""


class BulkResponse(SCIM2Model):
    schemas: List[str] = ["urn:ietf:params:scim:api:messages:2.0:BulkResponse"]

    operations: List[BulkOperation] = Field(..., alias="Operations")
    """Defines operations within a bulk job."""
