from enum import Enum
from typing import Annotated
from typing import Any

from pydantic import Field
from pydantic import PlainSerializer

from ..attributes import ComplexAttribute
from ..urn import URN
from ..utils import _int_to_str
from .message import Message


class BulkOperation(ComplexAttribute):
    class Method(str, Enum):
        post = "POST"
        put = "PUT"
        patch = "PATCH"
        delete = "DELETE"

    method: Method | None = None
    """The HTTP method of the current operation."""

    bulk_id: str | None = None
    """The transient identifier of a newly created resource, unique within a
    bulk request and created by the client."""

    version: str | None = None
    """The current resource version."""

    path: str | None = None
    """The resource's relative path to the SCIM service provider's root."""

    data: Any | None = None
    """The resource data as it would appear for a single SCIM POST, PUT, or
    PATCH operation."""

    location: str | None = None
    """The resource endpoint URL."""

    response: Any | None = None
    """The HTTP response body for the specified request operation."""

    status: Annotated[int | None, PlainSerializer(_int_to_str)] = None
    """The HTTP response status code for the requested operation."""


class BulkRequest(Message):
    """Bulk request as defined in :rfc:`RFC7644 §3.7 <7644#section-3.7>`.

    The request groups independent SCIM operations. Its ``Operations`` field
    keeps the SCIM capitalization during serialization:

    >>> from scim2_models import BulkOperation, BulkRequest, Context
    >>> request = BulkRequest(
    ...     operations=[
    ...         BulkOperation(
    ...             method="POST",
    ...             bulk_id="create-user",
    ...             path="/Users",
    ...             data={"userName": "bjensen"},
    ...         )
    ...     ]
    ... )
    >>> request.model_dump(scim_ctx=Context.RESOURCE_CREATION_REQUEST)["Operations"]
    [{'method': 'POST', 'bulkId': 'create-user', 'path': '/Users', 'data': {'userName': 'bjensen'}}]

    scim2-models validates and serializes the message. Applying the operations it
    carries is left to the application.

    .. todo::

        The models for Bulk operations are defined, but their behavior is not implemented nor tested yet.
    """

    __schema__ = URN("urn:ietf:params:scim:api:messages:2.0:BulkRequest")

    fail_on_errors: int | None = None
    """An integer specifying the number of errors that the service provider
    will accept before the operation is terminated and an error response is
    returned."""

    operations: list[BulkOperation] | None = Field(
        None, serialization_alias="Operations"
    )
    """Defines operations within a bulk job."""


class BulkResponse(Message):
    """Bulk response as defined in :rfc:`RFC7644 §3.7 <7644#section-3.7>`.

    scim2-models validates and serializes the message. Building it from the
    outcome of the operations is left to the application.

    .. todo::

        The models for Bulk operations are defined, but their behavior is not implemented nor tested yet.
    """

    __schema__ = URN("urn:ietf:params:scim:api:messages:2.0:BulkResponse")

    operations: list[BulkOperation] | None = Field(
        None, serialization_alias="Operations"
    )
    """Defines operations within a bulk job."""
