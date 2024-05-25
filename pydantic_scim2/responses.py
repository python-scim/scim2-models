from enum import Enum
from typing import Any
from typing import Generic
from typing import List
from typing import Optional
from typing import TypeVar

from pydantic import Field
from pydantic import field_serializer

from .base import SCIM2Model


class Error(SCIM2Model):
    schemas: List[str] = ["urn:ietf:params:scim:api:messages:2.0:Error"]

    status: int
    """The HTTP status code (see Section 6 of [RFC7231]) expressed as a JSON
    string."""

    @field_serializer("status")
    def serialize_int_to_string(status: int):
        return str(status)

    scim_type: Optional[str] = None
    """A SCIM detail error keyword."""

    detail: Optional[str] = None
    """A detailed human-readable message."""

    @classmethod
    def not_found(cls, detail: str = "Not found") -> "Error":
        return cls(detail=detail, status=404)

    @classmethod
    def conflict(cls, detail: str = "Conflict") -> "Error":
        return cls(detail=detail, status=409)

    @classmethod
    def unprocessable(cls, detail: str = "Unprocessable Entity") -> "Error":
        return cls(detail=detail, status=422)


class Op(str, Enum):
    replace = "replace"
    remove = "remove"
    add = "add"


class PatchOperation(SCIM2Model):
    op: Op
    """Each PATCH operation object MUST have exactly one "op" member, whose
    value indicates the operation to perform and MAY be one of "add", "remove",
    or "replace"."""

    path: Optional[str] = None
    """The "path" attribute value is a String containing an attribute path
    describing the target of the operation."""
    # TODO: The "path" attribute is OPTIONAL for "add" and "replace" and is REQUIRED for "remove"
    value: Optional[Any] = None


class PatchOp(SCIM2Model):
    schemas: List[str] = ["urn:ietf:params:scim:api:messages:2.0:PatchOp"]

    operations: List[PatchOperation] = Field(..., alias="Operations")
    """The body of an HTTP PATCH request MUST contain the attribute
    "Operations", whose value is an array of one or more PATCH operations."""


T = TypeVar("T", SCIM2Model, Any)


class ListResponse(SCIM2Model, Generic[T]):
    schemas: List[str] = ["urn:ietf:params:scim:api:messages:2.0:ListResponse"]

    total_results: int
    """The total number of results returned by the list or query operation."""

    start_index: Optional[int] = None
    """The 1-based index of the first result in the current set of list
    results."""

    items_per_page: Optional[int] = None
    """The number of resources returned in a list response page."""

    resources: Optional[List[T]] = Field(None, alias="Resources")
    """A multi-valued list of complex objects containing the requested
    resources."""
    # TODO: REQUIRED if "totalResults" is non-zero.


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
