from typing import TYPE_CHECKING
from typing import Annotated

from pydantic import Field

from ..annotations import CaseExact
from ..annotations import Mutability
from ..annotations import Required
from ..attributes import ComplexAttribute
from ..path import URN
from ..reference import Reference
from .resource import Extension

if TYPE_CHECKING:
    from .user import User


class Manager(ComplexAttribute):
    value: Annotated[str | None, Required.true, CaseExact.true] = None
    """The id of the SCIM resource representing the User's manager."""

    ref: Annotated[  # type: ignore[type-arg]
        Reference["User"] | None,
        Required.true,
    ] = Field(None, serialization_alias="$ref")
    """The URI of the SCIM resource representing the User's manager."""

    display_name: Annotated[str | None, Mutability.read_only] = None
    """The displayName of the User's manager."""


class EnterpriseUser(Extension):
    __schema__ = URN("urn:ietf:params:scim:schemas:extension:enterprise:2.0:User")

    employee_number: str | None = None
    """Numeric or alphanumeric identifier assigned to a person, typically based
    on order of hire or association with an organization."""

    cost_center: str | None = None
    """"Identifies the name of a cost center."""

    organization: str | None = None
    """Identifies the name of an organization."""

    division: str | None = None
    """Identifies the name of a division."""

    department: str | None = None
    """Numeric or alphanumeric identifier assigned to a person, typically based
    on order of hire or association with an organization."""

    manager: Manager | None = None
    """The User's manager.

    A complex type that optionally allows service providers to represent
    organizational hierarchy by referencing the 'id' attribute of
    another User.
    """
