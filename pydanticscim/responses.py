from enum import Enum
from typing import Tuple, List, Optional, Any, Union, Annotated

from pydantic import BaseModel, Discriminator, Tag

from pydanticscim.group import Group
from pydanticscim.user import User
from pydanticscim.resource_type import ResourceType
from pydanticscim.service_provider import ServiceProviderConfiguration


class SCIMError(BaseModel):
    detail: str
    status: int
    schemas: Tuple[str] = ("urn:ietf:params:scim:api:messages:2.0:Error",)

    @classmethod
    def not_found(cls, detail: str = "Not found") -> "SCIMError":
        return cls(detail=detail, status=404)

    @classmethod
    def conflict(cls, detail: str = "Conflict") -> "SCIMError":
        return cls(detail=detail, status=409)

    @classmethod
    def unprocessable(cls, detail: str = "Unprocessable Entity") -> "SCIMError":
        return cls(detail=detail, status=422)


class PatchOp(Enum):
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
    schemas: Tuple[str] = ("urn:ietf:params:scim:api:messages:2.0:ListResponse",)

    @classmethod
    def for_users(
        cls,
        users: List[User],
        total_results: int,
        start_index: int = 0,
        items_per_page: int | None = None,
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
        items_per_page: int | None = None,
    ) -> "ListResponse":
        return cls(
            Resources=groups,
            totalResults=total_results,
            itemsPerPage=items_per_page or len(groups),
            startIndex=start_index,
        )
