import warnings
from collections.abc import Mapping
from collections.abc import Sequence
from typing import Annotated
from typing import Any

from pydantic import PlainSerializer
from pydantic import ValidationError

from ..path import URN
from ..utils import _int_to_str
from .message import Message


class Error(Message):
    """Representation of SCIM API errors.

    :rfc:`RFC 7644 Section 3.12 <7644#section-3.12>`
    """

    __schema__ = URN("urn:ietf:params:scim:api:messages:2.0:Error")

    status: Annotated[int | None, PlainSerializer(_int_to_str)] = None
    """The HTTP status code (see Section 6 of [RFC7231]) expressed as a JSON
    string."""

    scim_type: str | None = None
    """A SCIM detail error keyword."""

    detail: str | None = None
    """A detailed human-readable message."""

    @classmethod
    def make_invalid_filter_error(cls) -> "Error":
        """Pre-defined error intended to be raised when the specified filter syntax was invalid (does not comply with :rfc:`Figure 1 of RFC7644 <7644#section-3.4.2.2>`), or the specified attribute and filter comparison combination is not supported.

        .. deprecated:: 0.6.0
            Use :class:`~scim2_models.InvalidFilterException` instead.
            Will be removed in 0.7.0.
        """
        warnings.warn(
            "make_invalid_filter_error is deprecated, use InvalidFilterException().to_error() instead. "
            "Will be removed in 0.7.0.",
            DeprecationWarning,
            stacklevel=2,
        )
        return Error(
            status=400,
            scim_type="invalidFilter",
            detail="""The specified filter syntax was invalid (does not comply with Figure 1 of RFC7644), or the specified attribute and filter comparison combination is not supported.""",
        )

    @classmethod
    def make_too_many_error(cls) -> "Error":
        """Pre-defined error intended to be raised when the specified filter yields many more results than the server is willing to calculate or process.  For example, a filter such as ``(userName pr)`` by itself would return all entries with a ``userName`` and MAY not be acceptable to the service provider.

        .. deprecated:: 0.6.0
            Use :class:`~scim2_models.TooManyException` instead.
            Will be removed in 0.7.0.
        """
        warnings.warn(
            "make_too_many_error is deprecated, use TooManyException().to_error() instead. "
            "Will be removed in 0.7.0.",
            DeprecationWarning,
            stacklevel=2,
        )
        return Error(
            status=400,
            scim_type="tooMany",
            detail="""The specified filter yields many more results than the server is willing to calculate or process.  For example, a filter such as "(userName pr)" by itself would return all entries with a "userName" and MAY not be acceptable to the service provider.""",
        )

    @classmethod
    def make_uniqueness_error(cls) -> "Error":
        """Pre-defined error intended to be raised when One or more of the attribute values are already in use or are reserved.

        .. deprecated:: 0.6.0
            Use :class:`~scim2_models.UniquenessException` instead.
            Will be removed in 0.7.0.
        """
        warnings.warn(
            "make_uniqueness_error is deprecated, use UniquenessException().to_error() instead. "
            "Will be removed in 0.7.0.",
            DeprecationWarning,
            stacklevel=2,
        )
        return Error(
            status=409,
            scim_type="uniqueness",
            detail="""One or more of the attribute values are already in use or are reserved.""",
        )

    @classmethod
    def make_mutability_error(cls) -> "Error":
        """Pre-defined error intended to be raised when the attempted modification is not compatible with the target attribute's mutability or current state (e.g., modification of an "immutable" attribute with an existing value).

        .. deprecated:: 0.6.0
            Use :class:`~scim2_models.MutabilityException` instead.
            Will be removed in 0.7.0.
        """
        warnings.warn(
            "make_mutability_error is deprecated, use MutabilityException().to_error() instead. "
            "Will be removed in 0.7.0.",
            DeprecationWarning,
            stacklevel=2,
        )
        return Error(
            status=400,
            scim_type="mutability",
            detail="""The attempted modification is not compatible with the target attribute's mutability or current state (e.g., modification of an "immutable" attribute with an existing value).""",
        )

    @classmethod
    def make_invalid_syntax_error(cls) -> "Error":
        """Pre-defined error intended to be raised when the request body message structure was invalid or did not conform to the request schema.

        .. deprecated:: 0.6.0
            Use :class:`~scim2_models.InvalidSyntaxException` instead.
            Will be removed in 0.7.0.
        """
        warnings.warn(
            "make_invalid_syntax_error is deprecated, use InvalidSyntaxException().to_error() instead. "
            "Will be removed in 0.7.0.",
            DeprecationWarning,
            stacklevel=2,
        )
        return Error(
            status=400,
            scim_type="invalidSyntax",
            detail="""The request body message structure was invalid or did not conform to the request schema.""",
        )

    @classmethod
    def make_invalid_path_error(cls) -> "Error":
        """Pre-defined error intended to be raised when the "path" attribute was invalid or malformed (see :rfc:`Figure 7 of RFC7644 <7644#section-3.5.2>`).

        .. deprecated:: 0.6.0
            Use :class:`~scim2_models.InvalidPathException` instead.
            Will be removed in 0.7.0.
        """
        warnings.warn(
            "make_invalid_path_error is deprecated, use InvalidPathException().to_error() instead. "
            "Will be removed in 0.7.0.",
            DeprecationWarning,
            stacklevel=2,
        )
        return Error(
            status=400,
            scim_type="invalidPath",
            detail="""The "path" attribute was invalid or malformed (see Figure 7 of RFC7644).""",
        )

    @classmethod
    def make_no_target_error(cls) -> "Error":
        """Pre-defined error intended to be raised when the specified "path" did not yield an attribute or attribute value that could be operated on.  This occurs when the specified "path" value contains a filter that yields no match.

        .. deprecated:: 0.6.0
            Use :class:`~scim2_models.NoTargetException` instead.
            Will be removed in 0.7.0.
        """
        warnings.warn(
            "make_no_target_error is deprecated, use NoTargetException().to_error() instead. "
            "Will be removed in 0.7.0.",
            DeprecationWarning,
            stacklevel=2,
        )
        return Error(
            status=400,
            scim_type="noTarget",
            detail="""The specified "path" did not yield an attribute or attribute value that could be operated on.  This occurs when the specified "path" value contains a filter that yields no match.""",
        )

    @classmethod
    def make_invalid_value_error(cls) -> "Error":
        """Pre-defined error intended to be raised when a required value was missing, or the value specified was not compatible with the operation or attribute type (see :rfc:`Section 2.2 of RFC7643 <7643#section-2.2>`), or resource schema (see :rfc:`Section 4 of RFC7643 <7643#section-4>`).

        .. deprecated:: 0.6.0
            Use :class:`~scim2_models.InvalidValueException` instead.
            Will be removed in 0.7.0.
        """
        warnings.warn(
            "make_invalid_value_error is deprecated, use InvalidValueException().to_error() instead. "
            "Will be removed in 0.7.0.",
            DeprecationWarning,
            stacklevel=2,
        )
        return Error(
            status=400,
            scim_type="invalidValue",
            detail="""A required value was missing, or the value specified was not compatible with the operation or attribute type (see Section 2.2 of RFC7643), or resource schema (see Section 4 of RFC7643).""",
        )

    @classmethod
    def make_invalid_version_error(cls) -> "Error":
        """Pre-defined error intended to be raised when the specified SCIM protocol version is not supported (see :rfc:`Section 3.13 of RFC7644 <7644#section-3.13>`).

        .. deprecated:: 0.6.0
            Use :class:`~scim2_models.InvalidVersionException` instead.
            Will be removed in 0.7.0.
        """
        warnings.warn(
            "make_invalid_version_error is deprecated, use InvalidVersionException().to_error() instead. "
            "Will be removed in 0.7.0.",
            DeprecationWarning,
            stacklevel=2,
        )
        return Error(
            status=400,
            scim_type="invalidVers",
            detail="""The specified SCIM protocol version is not supported (see Section 3.13 of RFC7644).""",
        )

    @classmethod
    def make_sensitive_error(cls) -> "Error":
        """Pre-defined error intended to be raised when the specified request cannot be completed, due to the passing of sensitive (e.g., personal) information in a request URI.  For example, personal information SHALL NOT be transmitted over request URIs.  See :rfc:`Section 7.5.2 of RFC7644 <7644#section-7.5.2>`.

        .. deprecated:: 0.6.0
            Use :class:`~scim2_models.SensitiveException` instead.
            Will be removed in 0.7.0.
        """
        warnings.warn(
            "make_sensitive_error is deprecated, use SensitiveException().to_error() instead. "
            "Will be removed in 0.7.0.",
            DeprecationWarning,
            stacklevel=2,
        )
        return Error(
            status=400,
            scim_type="sensitive",
            detail="""The specified request cannot be completed, due to the passing of sensitive (e.g., personal) information in a request URI.  For example, personal information SHALL NOT be transmitted over request URIs.  See Section 7.5.2. of RFC7644""",
        )

    @classmethod
    def from_validation_error(cls, error: Mapping[str, Any]) -> "Error":
        """Convert a single Pydantic error dict to a SCIM Error.

        If the error is a SCIM-specific error (raised via
        :meth:`SCIMException.as_pydantic_error`), its scim_type and status
        are preserved. Otherwise, a best-effort mapping is performed.

        :param error: A single error dict from ``ValidationError.errors()``.
        :return: A SCIM Error object.
        """
        if error["type"].startswith("scim_"):
            ctx = error.get("ctx", {})
            return cls(
                status=ctx.get("status", 400),
                scim_type=ctx.get("scim_type"),
                detail=error["msg"],
            )

        loc = ", ".join(str(loc) for loc in error["loc"])
        detail = f"{error['msg']}: {loc}" if loc else error["msg"]

        scim_type: str | None = None
        error_type = error["type"]
        if error_type in ("missing", "required_error"):
            scim_type = "invalidValue"
        elif error_type in (
            "string_type",
            "int_type",
            "int_parsing",
            "bool_type",
            "bool_parsing",
            "float_type",
            "float_parsing",
            "json_invalid",
            "value_error",
        ):
            scim_type = "invalidSyntax"

        return cls(status=400, scim_type=scim_type, detail=detail)

    @classmethod
    def from_validation_errors(
        cls, errors: ValidationError | Sequence[Mapping[str, Any]]
    ) -> list["Error"]:
        """Convert Pydantic validation errors to a list of SCIM Errors.

        :param errors: A ``ValidationError`` or a list of error dicts.
        :return: A list of SCIM Error objects.
        """
        error_list = errors.errors() if isinstance(errors, ValidationError) else errors
        return [cls.from_validation_error(error) for error in error_list]
