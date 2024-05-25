from enum import Enum
from typing import Any
from typing import Generic
from typing import List
from typing import Optional
from typing import TypeVar

from pydantic import Field

from .base import SCIM2Model


class SCIMError(SCIM2Model):
    detail: str
    status: int
    schemas: List[str] = ["urn:ietf:params:scim:api:messages:2.0:Error"]

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


class PatchOperation(SCIM2Model):
    op: PatchOp
    path: str
    value: Optional[Any] = None


class PatchRequest(SCIM2Model):
    Operations: List[PatchOperation]


def get_model_name(obj: Any):
    # TODO: If discriminators could return multiple values,
    # we could read all the objects in obj["schemas"] instead and maybe implement
    # several classes at once?
    return obj["meta"]["resourceType"]


T = TypeVar("T", SCIM2Model, Any)


class ListResponse(SCIM2Model, Generic[T]):
    total_results: int
    start_index: int
    items_per_page: int
    resources: List[T] = Field(..., alias="Resources")
    schemas: List[str] = ["urn:ietf:params:scim:api:messages:2.0:ListResponse"]
