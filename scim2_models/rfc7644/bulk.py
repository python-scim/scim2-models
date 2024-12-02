from enum import Enum
from typing import Annotated
from typing import Any
from typing import Optional

from pydantic import Field
from pydantic import PlainSerializer

from ..base import ComplexAttribute
from ..base import Required
from ..utils import int_to_str
from .message import Message


class BulkOperation(ComplexAttribute):
    class Method(str, Enum):
        post = "POST"
        put = "PUT"
        patch = "PATCH"
        delete = "DELETE"

    method: Optional[Method] = None
    """The HTTP method of the current operation."""

    bulk_id: Optional[str] = None
    """The transient identifier of a newly created resource, unique within a
    bulk request and created by the client."""

    version: Optional[str] = None
    """The current resource version."""

    path: Optional[str] = None
    """The resource's relative path to the SCIM service provider's root."""

    data: Optional[Any] = None
    """The resource data as it would appear for a single SCIM POST, PUT, or
    PATCH operation."""

    location: Optional[str] = None
    """The resource endpoint URL."""

    response: Optional[Any] = None
    """The HTTP response body for the specified request operation."""

    status: Annotated[Optional[int], PlainSerializer(int_to_str)] = None
    """The HTTP response status code for the requested operation."""


class BulkRequest(Message):
    """Bulk request as defined in :rfc:`RFC7644 §3.7 <7644#section-3.7>`.

    .. todo::

        The models for Bulk operations are defined, but their behavior is not implemented nor tested yet.
    """

    schemas: Annotated[list[str], Required.true] = [
        "urn:ietf:params:scim:api:messages:2.0:BulkRequest"
    ]

    fail_on_errors: Optional[int] = None
    """An integer specifying the number of errors that the service provider
    will accept before the operation is terminated and an error response is
    returned."""

    operations: Optional[list[BulkOperation]] = Field(
        None, serialization_alias="Operations"
    )
    """Defines operations within a bulk job."""


class BulkResponse(Message):
    """Bulk response as defined in :rfc:`RFC7644 §3.7 <7644#section-3.7>`.

    .. todo::

        The models for Bulk operations are defined, but their behavior is not implemented nor tested yet.
    """

    schemas: Annotated[list[str], Required.true] = [
        "urn:ietf:params:scim:api:messages:2.0:BulkResponse"
    ]

    operations: Optional[list[BulkOperation]] = Field(
        None, serialization_alias="Operations"
    )
    """Defines operations within a bulk job."""
