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
