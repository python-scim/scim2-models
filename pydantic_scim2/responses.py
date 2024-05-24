from enum import Enum
from typing import Annotated
from typing import Any
from typing import List
from typing import Optional
from typing import Union

from pydantic import BaseModel
from pydantic import Discriminator
from pydantic import Tag

from pydantic_scim2.group import Group
from pydantic_scim2.resource_type import ResourceType
from pydantic_scim2.service_provider import ServiceProviderConfiguration
from pydantic_scim2.user import User


class SCIMError(BaseModel):
    detail: str
    status: int
    schemas: List[str] = {"urn:ietf:params:scim:api:messages:2.0:Error"}

    @classmethod
    def not_found(cls, detail: str = "Not found") -> "SCIMError":
        return cls(detail=detail, status=404)

    @classmethod
    def conflict(cls, detail: str = "Conflict") -> "SCIMError":
        return cls(detail=detail, status=409)

    @classmethod
    def unprocessable(cls, detail: str = "Unprocessable Entity") -> "SCIMError":
        return cls(detail=detail, status=422)


class PatchOp(str, Enum):
    replace = "replace"
    remove = "remove"
    add = "add"


class PatchOperation(BaseModel):
    op: PatchOp
    path: str
    value: Optional[Any] = None


class PatchRequest(BaseModel):
    Operations: List[PatchOperation]


def get_model_name(obj: Any):
    # TODO: If discriminators could return multiple values,
    # we could read all the objects in obj["schemas"] instead and maybe implement
    # several classes at once?
    return obj["meta"]["resourceType"]


class ListResponse(BaseModel):
    totalResults: int
    startIndex: int
    itemsPerPage: int
    Resources: List[
        Annotated[
            Union[
                Annotated[User, Tag("User")],
                Annotated[Group, Tag("Group")],
                Annotated[ResourceType, Tag("ResourceType")],
                Annotated[ServiceProviderConfiguration, Tag("ServiceProviderConfig")],
            ],
            Discriminator(get_model_name),
        ]
    ]
    schemas: List[str] = {"urn:ietf:params:scim:api:messages:2.0:ListResponse"}

    @classmethod
    def for_users(
        cls,
        users: List[User],
        total_results: int,
        start_index: int = 0,
        items_per_page: Optional[int] = None,
    ) -> "ListResponse":
        return cls(
            Resources=users,
            totalResults=total_results,
            itemsPerPage=items_per_page or len(users),
            startIndex=start_index,
        )

    @classmethod
    def for_groups(
        cls,
        groups: List[Group],
        total_results: int,
        start_index: int = 0,
        items_per_page: Optional[int] = None,
    ) -> "ListResponse":
        return cls(
            Resources=groups,
            totalResults=total_results,
            itemsPerPage=items_per_page or len(groups),
            startIndex=start_index,
        )
