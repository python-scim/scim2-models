"""SCIM exceptions corresponding to RFC 7644 error types.

This module provides a hierarchy of exceptions that map to SCIM protocol errors.
Each exception can be converted to a :class:`~scim2_models.Error` response object
or to a :class:`~pydantic_core.PydanticCustomError` for use in Pydantic validators.
"""

from typing import TYPE_CHECKING
from typing import Any

from pydantic_core import PydanticCustomError

if TYPE_CHECKING:
    from .messages.error import Error


class SCIMException(Exception):
    """Base exception for SCIM protocol errors.

    Each subclass corresponds to a scimType defined in :rfc:`RFC 7644 Table 9 <7644#section-3.12>`.
    """

    status: int = 400
    scim_type: str = ""
    _default_detail: str = "A SCIM error occurred"

    def __init__(self, *, detail: str | None = None, **context: Any):
        self.context = context
        self._detail = detail
        super().__init__(detail or self._default_detail)

    @property
    def detail(self) -> str:
        """The error detail message."""
        return self._detail or self._default_detail

    def to_error(self) -> "Error":
        """Convert this exception to a SCIM Error response object."""
        from .messages.error import Error

        return Error(
            status=self.status,
            scim_type=self.scim_type or None,
            detail=str(self),
        )

    def as_pydantic_error(self) -> PydanticCustomError:
        """Convert to PydanticCustomError for use in Pydantic validators."""
        return PydanticCustomError(
            f"scim_{self.scim_type}" if self.scim_type else "scim_error",
            str(self),
            {"scim_type": self.scim_type, "status": self.status, **self.context},
        )

    @classmethod
    def from_error(cls, error: "Error") -> "SCIMException":
        """Create an exception from a SCIM Error object.

        :param error: The SCIM Error object to convert.
        :return: The appropriate SCIMException subclass instance.
        """
        from .messages.error import Error

        if not isinstance(error, Error):
            raise TypeError(f"Expected Error, got {type(error).__name__}")

        exception_class = _SCIM_TYPE_TO_EXCEPTION.get(error.scim_type or "", cls)
        return exception_class(detail=error.detail)


class InvalidFilterException(SCIMException):
    """The specified filter syntax was invalid.

    Corresponds to scimType ``invalidFilter`` with HTTP status 400.

    :rfc:`RFC 7644 Section 3.4.2.2 <7644#section-3.4.2.2>`
    """

    status = 400
    scim_type = "invalidFilter"
    _default_detail = (
        "The specified filter syntax was invalid, "
        "or the specified attribute and filter comparison combination is not supported"
    )

    def __init__(self, *, filter: str | None = None, **kw: Any):
        self.filter = filter
        super().__init__(**kw)


class TooManyException(SCIMException):
    """The specified filter yields too many results.

    Corresponds to scimType ``tooMany`` with HTTP status 400.

    :rfc:`RFC 7644 Section 3.4.2.2 <7644#section-3.4.2.2>`
    """

    status = 400
    scim_type = "tooMany"
    _default_detail = (
        "The specified filter yields many more results "
        "than the server is willing to calculate or process"
    )


class UniquenessException(SCIMException):
    """One or more attribute values are already in use or reserved.

    Corresponds to scimType ``uniqueness`` with HTTP status 409.

    :rfc:`RFC 7644 Section 3.3.1 <7644#section-3.3.1>`
    """

    status = 409
    scim_type = "uniqueness"
    _default_detail = (
        "One or more of the attribute values are already in use or are reserved"
    )

    def __init__(
        self, *, attribute: str | None = None, value: Any | None = None, **kw: Any
    ):
        self.attribute = attribute
        self.value = value
        super().__init__(**kw)


class MutabilityException(SCIMException):
    """The attempted modification is not compatible with the attribute's mutability.

    Corresponds to scimType ``mutability`` with HTTP status 400.

    :rfc:`RFC 7644 Section 3.5.2 <7644#section-3.5.2>`
    """

    status = 400
    scim_type = "mutability"
    _default_detail = (
        "The attempted modification is not compatible with the target attribute's "
        "mutability or current state"
    )

    def __init__(
        self,
        *,
        attribute: str | None = None,
        mutability: str | None = None,
        operation: str | None = None,
        **kw: Any,
    ):
        self.attribute = attribute
        self.mutability = mutability
        self.operation = operation
        super().__init__(**kw)


class InvalidSyntaxException(SCIMException):
    """The request body message structure was invalid.

    Corresponds to scimType ``invalidSyntax`` with HTTP status 400.

    :rfc:`RFC 7644 Section 3.12 <7644#section-3.12>`
    """

    status = 400
    scim_type = "invalidSyntax"
    _default_detail = (
        "The request body message structure was invalid "
        "or did not conform to the request schema"
    )


class InvalidPathException(SCIMException):
    """The path attribute was invalid or malformed.

    Corresponds to scimType ``invalidPath`` with HTTP status 400.

    :rfc:`RFC 7644 Section 3.5.2 <7644#section-3.5.2>`
    """

    status = 400
    scim_type = "invalidPath"
    _default_detail = "The path attribute was invalid or malformed"

    def __init__(self, *, path: str | None = None, **kw: Any):
        self.path = path
        super().__init__(**kw)


class PathNotFoundException(InvalidPathException):
    """The path references a non-existent field.

    This is a specialized form of :class:`InvalidPathException`.
    """

    _default_detail = "The specified path references a non-existent field"

    def __init__(self, *, path: str | None = None, field: str | None = None, **kw: Any):
        self.field = field
        super().__init__(path=path, **kw)

    def __str__(self) -> str:
        if self._detail:
            return self._detail
        if self.field:
            return f"Field not found: {self.field}"
        return self._default_detail


class NoTargetException(SCIMException):
    """The specified path did not yield a target that could be operated on.

    Corresponds to scimType ``noTarget`` with HTTP status 400.

    :rfc:`RFC 7644 Section 3.5.2 <7644#section-3.5.2>`
    """

    status = 400
    scim_type = "noTarget"
    _default_detail = (
        "The specified path did not yield an attribute or attribute value "
        "that could be operated on"
    )

    def __init__(self, *, path: str | None = None, **kw: Any):
        self.path = path
        super().__init__(**kw)


class InvalidValueException(SCIMException):
    """A required value was missing or the value was not compatible.

    Corresponds to scimType ``invalidValue`` with HTTP status 400.

    :rfc:`RFC 7644 Section 3.12 <7644#section-3.12>`
    """

    status = 400
    scim_type = "invalidValue"
    _default_detail = (
        "A required value was missing, or the value specified was not compatible "
        "with the operation or attribute type, or resource schema"
    )

    def __init__(
        self, *, attribute: str | None = None, reason: str | None = None, **kw: Any
    ):
        self.attribute = attribute
        self.reason = reason
        super().__init__(**kw)


class InvalidVersionException(SCIMException):
    """The specified SCIM protocol version is not supported.

    Corresponds to scimType ``invalidVers`` with HTTP status 400.

    :rfc:`RFC 7644 Section 3.13 <7644#section-3.13>`
    """

    status = 400
    scim_type = "invalidVers"
    _default_detail = "The specified SCIM protocol version is not supported"


class SensitiveException(SCIMException):
    """The request cannot be completed due to sensitive information in the URI.

    Corresponds to scimType ``sensitive`` with HTTP status 400.

    :rfc:`RFC 7644 Section 7.5.2 <7644#section-7.5.2>`
    """

    status = 400
    scim_type = "sensitive"
    _default_detail = (
        "The specified request cannot be completed, due to the passing of sensitive "
        "information in a request URI"
    )


_SCIM_TYPE_TO_EXCEPTION: dict[str, type[SCIMException]] = {
    "invalidFilter": InvalidFilterException,
    "tooMany": TooManyException,
    "uniqueness": UniquenessException,
    "mutability": MutabilityException,
    "invalidSyntax": InvalidSyntaxException,
    "invalidPath": InvalidPathException,
    "noTarget": NoTargetException,
    "invalidValue": InvalidValueException,
    "invalidVers": InvalidVersionException,
    "sensitive": SensitiveException,
}
