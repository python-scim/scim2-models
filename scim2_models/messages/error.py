from collections.abc import Mapping
from collections.abc import Sequence
from typing import Annotated
from typing import Any

from pydantic import PlainSerializer
from pydantic import ValidationError

from ..urn import URN
from ..utils import _int_to_str
from .message import Message

_STRUCTURE_ERRORS = frozenset(
    {
        "json_invalid",
        "json_type",
        "extra_forbidden",
        "schema_error",
        "unknown_extension_schema",
    }
)
"""Errors on the structure of a payload rather than on one of its values."""

_OBJECT_TYPE_ERRORS = frozenset({"model_type", "model_attributes_type", "dict_type"})
"""Errors refusing something that is not an object, at the root of a payload or below."""

_RESPONSE_ERRORS = frozenset({"returned_error", "no_resource_error"})
"""Errors only a response can carry, for which RFC7644 defines no keyword."""


def _scim_type_of(error: Mapping[str, Any]) -> str | None:
    """Return the RFC7644 §3.12 keyword a Pydantic error stands for."""
    error_type = error["type"]
    if error_type in _RESPONSE_ERRORS:
        return None

    # A payload that is not an object at all cannot follow the request schema,
    # where the same error below the root refuses the value of a complex attribute.
    if error_type in _STRUCTURE_ERRORS or (
        error_type in _OBJECT_TYPE_ERRORS and not error["loc"]
    ):
        return "invalidSyntax"

    return "invalidValue"


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
        are preserved. Otherwise the error is mapped on the keywords of
        :rfc:`RFC7644 §3.12 <7644#section-3.12>`: a payload whose structure does
        not follow the request schema is ``invalidSyntax``, a value that does not
        fit its attribute is ``invalidValue``, and an error only a response can
        carry has no keyword.

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
        return cls(status=400, scim_type=_scim_type_of(error), detail=detail)

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
