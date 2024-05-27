from typing import Annotated
from typing import List
from typing import Optional

from pydantic import PlainSerializer

from ..base import SCIM2Model
from ..base import int_to_str


class Error(SCIM2Model):
    schemas: List[str] = ["urn:ietf:params:scim:api:messages:2.0:Error"]

    status: Annotated[int, PlainSerializer(int_to_str)]
    """The HTTP status code (see Section 6 of [RFC7231]) expressed as a JSON
    string."""

    scim_type: Optional[str] = None
    """A SCIM detail error keyword."""

    detail: Optional[str] = None
    """A detailed human-readable message."""


InvalidFilterError = Error(
    status=400,
    scim_type="invalidFilter",
    detail="""The specified filter syntax was invalid (does not comply with Figure 1 of RFC7644), or the specified attribute and filter comparison combination is not supported.""",
)

TooManyError = Error(
    status=400,
    scim_type="tooMany",
    detail="""The specified filter yields many more results than the server is willing to calculate or process.  For example, a filter such as "(userName pr)" by itself would return all entries with a "userName" and MAY not be acceptable to the service provider.""",
)

UniquenessError = Error(
    status=400,
    scim_type="uniqueness",
    detail="""One or more of the attribute values are already in use or are reserved.""",
)

MutabilityError = Error(
    status=400,
    scim_type="mutability",
    detail="""The attempted modification is not compatible with the target attribute's mutability or current state (e.g., modification of an "immutable" attribute with an existing value).""",
)

InvalidSyntaxError = Error(
    status=400,
    scim_type="invalidSyntax",
    detail="""The request body message structure was invalid or did not conform to the request schema.""",
)

InvalidPathError = Error(
    status=400,
    scim_type="invalidPath",
    detail="""The "path" attribute was invalid or malformed (see Figure 7 of RFC7644).""",
)

NoTargetError = Error(
    status=400,
    scim_type="noTarget",
    detail="""The specified "path" did not yield an attribute or attribute value that could be operated on.  This occurs when the specified "path" value contains a filter that yields no match.""",
)

InvalidValueError = Error(
    status=400,
    scim_type="invalidValue",
    detail="""A required value was missing, or the value specified was not compatible with the operation or attribute type (see Section 2.2 of RFC7643), or resource schema (see Section 4 of RFC7643).""",
)

InvalidVersionError = Error(
    status=400,
    scim_type="invalidVers",
    detail="""The specified SCIM protocol version is not supported (see Section 3.13 of RFC7644).""",
)

SensitiveError = Error(
    status=400,
    scim_type="sensitive",
    detail="""The specified request cannot be completed, due to the passing of sensitive (e.g., personal) information in a request URI.  For example, personal information SHALL NOT be transmitted over request URIs.  See Section 7.5.2. of RFC7644""",
)
