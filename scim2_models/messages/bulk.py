from enum import Enum
from typing import Annotated
from typing import Any
from typing import ClassVar
from typing import Generic
from typing import TypeVar
from typing import Union
from typing import get_args
from typing import get_origin

from pydantic import Field
from pydantic import PlainSerializer
from pydantic import ValidationInfo
from pydantic import ValidatorFunctionWrapHandler
from pydantic import field_validator
from pydantic import model_validator
from pydantic_core import PydanticCustomError
from typing_extensions import Self

from ..annotations import Required
from ..annotations import Returned
from ..attributes import ComplexAttribute
from ..context import Context
from ..exceptions import InvalidValueException
from ..resources.resource import Resource
from ..urn import URN
from ..utils import UNION_TYPES
from ..utils import _int_to_str
from .error import Error
from .message import Message
from .message import _ResourceParameterized
from .patch_op import PatchOp

ResourceT = TypeVar("ResourceT", bound=Resource[Any])


class BulkOperation(_ResourceParameterized, ComplexAttribute, Generic[ResourceT]):
    """One operation of a bulk job, as defined in :rfc:`RFC7644 §3.7 <7644#section-3.7>`.

    ``data`` is validated in the context of the single request the operation
    stands for, as :attr:`~scim2_models.Context.BULK_REQUEST` describes.
    Parameterize the operation with the resource type it targets, e.g.
    ``BulkOperation[User]``.
    """

    class Method(str, Enum):
        post = "POST"
        put = "PUT"
        patch = "PATCH"
        delete = "DELETE"

    _DATA_CONTEXTS: ClassVar[dict[Method, Context]] = {
        Method.post: Context.RESOURCE_CREATION_REQUEST,
        Method.put: Context.RESOURCE_REPLACEMENT_REQUEST,
        Method.patch: Context.RESOURCE_PATCH_REQUEST,
    }
    """The single operation each method makes its data the payload of."""

    method: Annotated[Method | None, Required.true] = None
    """The HTTP method of the current operation."""

    bulk_id: str | None = None
    """The transient identifier of a newly created resource, unique within a
    bulk request and created by the client."""

    version: str | None = None
    """The current resource version."""

    path: Annotated[str | None, Returned.request] = None
    """The resource's relative path to the SCIM service provider's root."""

    data: Annotated[ResourceT | PatchOp[ResourceT] | None, Returned.request] = None
    """The resource data as it would appear for a single SCIM POST, PUT, or
    PATCH operation."""

    location: str | None = None
    """The resource endpoint URL."""

    response: ResourceT | Error | None = None
    """The HTTP response body for the specified request operation."""

    status: Annotated[int | None, PlainSerializer(_int_to_str)] = None
    """The HTTP response status code for the requested operation."""

    @field_validator("data", mode="wrap")
    @classmethod
    def _validate_data_as_a_single_operation(
        cls,
        value: Any,
        handler: ValidatorFunctionWrapHandler,
        info: ValidationInfo,
    ) -> Any:
        """Validate data in the context of the operation it is the payload of.

        RFC 7644 §3.7: "data  The resource data as it would appear for a single
        SCIM POST, PUT, or PATCH operation." A payload answers to the rules of
        the request it would be sent alone in, not to those of the bulk
        envelope carrying it. The envelope keeps BULK_REQUEST, and a flag
        carries what stays specific to a bulk job, such as a reference to a
        resource another operation is still creating.
        """
        context = info.context
        if not context or context.get("scim") != Context.BULK_REQUEST:
            return handler(value)

        method = info.data.get("method")
        derived = cls._DATA_CONTEXTS.get(method) if method else None
        if derived is None:
            return handler(value)

        context["scim"] = derived
        context["scim_bulk"] = True
        try:
            return handler(value)
        finally:
            context["scim"] = Context.BULK_REQUEST
            del context["scim_bulk"]

    def __class_getitem__(cls, item: Any) -> Any:
        """Turn ``BulkOperation[User | Group]`` into ``BulkOperation[User] | BulkOperation[Group]``.

        A bulk job's operations can each target a different resource type, but
        substituting the union directly for ``ResourceT`` would build ``data``'s
        ``PatchOp[User | Group]``, which :class:`PatchOp` rejects: a PATCH
        always targets one concrete resource type.
        """
        # Pydantic sometimes re-subscripts an already partially-parameterized
        # model (e.g. while substituting BulkRequest's own type parameter)
        # by passing a 1-tuple instead of the bare value.
        param = item[0] if isinstance(item, tuple) and len(item) == 1 else item

        if not isinstance(param, TypeVar) and get_origin(param) in UNION_TYPES:
            members = get_args(param)
            return Union[tuple(cls[member] for member in members)]  # type: ignore  # noqa: UP007

        return super().__class_getitem__(item)

    @model_validator(mode="after")
    def _validate_operation_requirements(self, info: ValidationInfo) -> Self:
        """Validate operation requirements according to RFC 7644."""
        scim_ctx = info.context.get("scim") if info.context else None

        if scim_ctx not in (Context.BULK_REQUEST, Context.BULK_RESPONSE):
            return self

        if scim_ctx == Context.BULK_REQUEST:
            # RFC 7644 Section 3.7: "path [...] REQUIRED in a request."
            if self.path is None:
                raise InvalidValueException(
                    detail="path is required for request operations"
                ).as_pydantic_error()

            # RFC 7644 Section 3.7: "data  The resource data as it would appear for a single SCIM POST,
            # PUT, or PATCH operation.  REQUIRED in a request when "method" is "POST", "PUT", or "PATCH"."
            if self.data is None and self.method in (
                BulkOperation.Method.post,
                BulkOperation.Method.put,
                BulkOperation.Method.patch,
            ):
                raise InvalidValueException(
                    detail="data is required for POST, PUT, or PATCH request operations"
                ).as_pydantic_error()
        else:
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
            # other than a 200-series response, the response body MUST be included."
            if (
                self.status is not None
                and not 200 <= self.status < 300
                and (self.response is None or not isinstance(self.response, Error))
            ):
                raise InvalidValueException(
                    detail="response parameter describing error is required"
                ).as_pydantic_error()

        # RFC 7644 Section 3.7: "bulkId [...] REQUIRED when "method" is "POST"."
        if self.method == BulkOperation.Method.post and self.bulk_id is None:
            raise InvalidValueException(
                detail="bulkId is required for POST operations"
            ).as_pydantic_error()

        return self


class BulkRequest(_ResourceParameterized, Message, Generic[ResourceT]):
    """Bulk request as defined in :rfc:`RFC7644 §3.7 <7644#section-3.7>`.

    The request groups independent SCIM operations. Its ``Operations`` field
    keeps the SCIM capitalization during serialization. Parameterize it with
    the resource type(s) the operations carry, e.g. ``BulkRequest[User |
    Group]`` when a single bulk job creates both users and groups:

    >>> from scim2_models import BulkOperation, BulkRequest, Context, User
    >>> request = BulkRequest[User](
    ...     operations=[
    ...         BulkOperation[User](
    ...             method="POST",
    ...             bulk_id="create-user",
    ...             path="/Users",
    ...             data={"userName": "bjensen"},
    ...         )
    ...     ]
    ... )
    >>> request.model_dump(scim_ctx=Context.BULK_REQUEST)["Operations"]
    [{'method': 'POST', 'bulkId': 'create-user', 'path': '/Users', 'data': {'schemas': ['urn:ietf:params:scim:schemas:core:2.0:User'], 'userName': 'bjensen'}}]

    scim2-models validates and serializes the message. Applying the operations it
    carries is left to the application.
    """

    __schema__ = URN("urn:ietf:params:scim:api:messages:2.0:BulkRequest")

    fail_on_errors: int | None = None
    """An integer specifying the number of errors that the service provider
    will accept before the operation is terminated and an error response is
    returned."""

    operations: Annotated[list[BulkOperation[ResourceT]] | None, Required.true] = Field(
        None, serialization_alias="Operations"
    )
    """Defines operations within a bulk job."""


class BulkResponse(_ResourceParameterized, Message, Generic[ResourceT]):
    """Bulk response as defined in :rfc:`RFC7644 §3.7 <7644#section-3.7>`.

    scim2-models validates and serializes the message. Building it from the
    outcome of the operations is left to the application. Parameterize it
    with the resource type(s) the operations carry, e.g. ``BulkResponse[User
    | Group]``.
    """

    __schema__ = URN("urn:ietf:params:scim:api:messages:2.0:BulkResponse")

    operations: Annotated[list[BulkOperation[ResourceT]] | None, Required.true] = Field(
        None, serialization_alias="Operations"
    )
    """Defines operations within a bulk job."""

    @model_validator(mode="after")
    def _check_operations(self, info: ValidationInfo) -> Self:
        """Validate that a bulk response carries its operations.

        RFC7644 §3.7 makes ``Operations`` required in a bulk response as it is
        in a bulk request. A response context checks what a peer returns rather
        than what it must send, so the necessity of the attribute is stated
        here.
        """
        scim_ctx = info.context.get("scim") if info.context else None
        if scim_ctx != Context.BULK_RESPONSE:
            return self

        if self.operations is None:
            raise PydanticCustomError(
                "required_error",
                "Field 'Operations' is required but value is missing or null",
            )

        return self
