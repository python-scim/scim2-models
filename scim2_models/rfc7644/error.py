from typing import Annotated
from typing import List
from typing import Optional

from pydantic import PlainSerializer

from ..utils import int_to_str
from .message import Message


class Error(Message):
    """Representation of SCIM API errors.

    Here is the exhaustive list of pre-defined errors:

    .. py:data:: pydanti_scim2.InvalidFilterError

       The specified filter syntax
       was invalid (does not comply
       with :rfc:`Figure 1 of RFC7644 <7644#section-3.4.2.2>`), or the
       specified attribute and filter
       comparison combination is not
       supported.

    .. py:data:: pydanti_scim2.TooManyError

       The specified filter yields
       many more results than the
       server is willing to calculate
       or process.  For example, a
       filter such as ``(userName pr)``
       by itself would return all
       entries with a ``userName`` and
       MAY not be acceptable to the
       service provider.

    .. py:data:: pydanti_scim2.UniquenessError

       One or more of the attribute
       values are already in use or
       are reserved.

    .. py:data:: pydanti_scim2.MutabilityError

       The attempted modification is
       not compatible with the target
       attribute's mutability or
       current state (e.g.,
       modification of an "immutable"
       attribute with an existing
       value).

    .. py:data:: pydanti_scim2.InvalidSyntaxError

       The request body message
       structure was invalid or did
       not conform to the request
       schema.

    .. py:data:: pydanti_scim2.InvalidPathError

       The "path" attribute was
       invalid or malformed (see
       :rfc:`Figure 7 of RFC7644 <7644#section-3.5.2>`).

    .. py:data:: pydanti_scim2.NoTargetError

       The specified "path" did not
       yield an attribute or
       attribute value that could be
       operated on.  This occurs when
       the specified "path" value
       contains a filter that yields
       no match.

    .. py:data:: pydanti_scim2.InvalidValueError

       A required value was missing,
       or the value specified was not
       compatible with the operation
       or attribute type (see :rfc:`Section
       2.2 of RFC7643 <7643#section-2.2>`), or resource
       schema (see :rfc:`Section 4 of
       RFC7643 <7643#section-4>`).

    .. py:data:: pydanti_scim2.InvalidVersionError

       The specified SCIM protocol
       version is not supported (see
       :rfc:`Section 3.13 of RFC7644 <7644#section-3.13>`).

    .. py:data:: pydanti_scim2.SensitiveError

       The specified request cannot
       be completed, due to the
       passing of sensitive (e.g.,
       personal) information in a
       request URI.  For example,
       personal information SHALL NOT
       be transmitted over request
       URIs.  See :rfc:`Section 7.5.2 of RFC7644 <7644#section-7.5.2>`.
    """

    schemas: List[str] = ["urn:ietf:params:scim:api:messages:2.0:Error"]

    status: Annotated[Optional[int], PlainSerializer(int_to_str)] = None
    """The HTTP status code (see Section 6 of [RFC7231]) expressed as a JSON
    string."""

    scim_type: Optional[str] = None
    """A SCIM detail error keyword."""

    detail: Optional[str] = None
    """A detailed human-readable message."""

    @classmethod
    def make_invalid_filter_error(cls):
        return Error(
            status=400,
            scim_type="invalidFilter",
            detail="""The specified filter syntax was invalid (does not comply with Figure 1 of RFC7644), or the specified attribute and filter comparison combination is not supported.""",
        )

    @classmethod
    def make_too_many_error(cls):
        return Error(
            status=400,
            scim_type="tooMany",
            detail="""The specified filter yields many more results than the server is willing to calculate or process.  For example, a filter such as "(userName pr)" by itself would return all entries with a "userName" and MAY not be acceptable to the service provider.""",
        )

    @classmethod
    def make_uniqueness_error(cls):
        return Error(
            status=409,
            scim_type="uniqueness",
            detail="""One or more of the attribute values are already in use or are reserved.""",
        )

    @classmethod
    def make_mutability_error(cls):
        return Error(
            status=400,
            scim_type="mutability",
            detail="""The attempted modification is not compatible with the target attribute's mutability or current state (e.g., modification of an "immutable" attribute with an existing value).""",
        )

    @classmethod
    def make_invalid_syntaxError(cls):
        return Error(
            status=400,
            scim_type="invalidSyntax",
            detail="""The request body message structure was invalid or did not conform to the request schema.""",
        )

    @classmethod
    def make_invalid_path_error(cls):
        return Error(
            status=400,
            scim_type="invalidPath",
            detail="""The "path" attribute was invalid or malformed (see Figure 7 of RFC7644).""",
        )

    @classmethod
    def make_no_target_error(cls):
        return Error(
            status=400,
            scim_type="noTarget",
            detail="""The specified "path" did not yield an attribute or attribute value that could be operated on.  This occurs when the specified "path" value contains a filter that yields no match.""",
        )

    @classmethod
    def make_invalid_value_error(cls):
        return Error(
            status=400,
            scim_type="invalidValue",
            detail="""A required value was missing, or the value specified was not compatible with the operation or attribute type (see Section 2.2 of RFC7643), or resource schema (see Section 4 of RFC7643).""",
        )

    @classmethod
    def make_invalid_version_error(cls):
        return Error(
            status=400,
            scim_type="invalidVers",
            detail="""The specified SCIM protocol version is not supported (see Section 3.13 of RFC7644).""",
        )

    @classmethod
    def make_sensitive_error(cls):
        return Error(
            status=400,
            scim_type="sensitive",
            detail="""The specified request cannot be completed, due to the passing of sensitive (e.g., personal) information in a request URI.  For example, personal information SHALL NOT be transmitted over request URIs.  See Section 7.5.2. of RFC7644""",
        )
