from typing import Optional

from pydantic import AnyUrl
from pydantic import Field

from .base import SCIM2Model


class Manager(SCIM2Model):
    value: Optional[str] = Field(
        None,
        description="The id of the SCIM resource representingthe User's manager.  REQUIRED.",
    )
    ref: Optional[AnyUrl] = Field(
        None,
        alias="$ref",
        description="The URI of the SCIM resource representing the User's manager.  REQUIRED.",
    )
    display_name: Optional[str] = Field(
        None,
        description="The displayName of the User's manager. OPTIONAL and READ-ONLY.",
    )


class EnterpriseUser(SCIM2Model):
    employee_number: Optional[str] = Field(
        None,
        description="Numeric or alphanumeric identifier assigned to a person, typically based on order of hire or association with anorganization.",
    )
    cost_center: Optional[str] = Field(
        None, description="Identifies the name of a cost center."
    )
    organization: Optional[str] = Field(
        None, description="Identifies the name of an organization."
    )
    division: Optional[str] = Field(
        None, description="Identifies the name of a division."
    )
    department: Optional[str] = Field(
        None,
        description="Numeric or alphanumeric identifier assigned to a person, typically based on order of hire or association with anorganization.",
    )
    manager: Optional[Manager] = Field(
        None,
        description="The User's manager. A complex type that optionally allows service providers to represent organizational hierarchy by referencing the 'id' attribute of another User.",
    )
