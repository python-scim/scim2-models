from typing import Annotated
from typing import Literal
from typing import Optional

from pydantic import Field

from ..base import ComplexAttribute
from ..base import Mutability
from ..base import Reference
from ..base import Required
from .resource import Extension


class Manager(ComplexAttribute):
    value: Annotated[Optional[str], Required.true] = None
    """The id of the SCIM resource representing the User's manager."""

    ref: Annotated[Optional[Reference[Literal["User"]]], Required.true] = Field(
        None,
        serialization_alias="$ref",
    )
    """The URI of the SCIM resource representing the User's manager."""

    display_name: Annotated[Optional[str], Mutability.read_only] = None
    """The displayName of the User's manager."""


class EnterpriseUser(Extension):
    schemas: Annotated[list[str], Required.true] = [
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"
    ]

    employee_number: Optional[str] = None
    """Numeric or alphanumeric identifier assigned to a person, typically based
    on order of hire or association with an organization."""

    cost_center: Optional[str] = None
    """"Identifies the name of a cost center."""

    organization: Optional[str] = None
    """Identifies the name of an organization."""

    division: Optional[str] = None
    """Identifies the name of a division."""

    department: Optional[str] = None
    """Numeric or alphanumeric identifier assigned to a person, typically based
    on order of hire or association with an organization."""

    manager: Optional[Manager] = None
    """The User's manager.

    A complex type that optionally allows service providers to represent
    organizational hierarchy by referencing the 'id' attribute of
    another User.
    """
