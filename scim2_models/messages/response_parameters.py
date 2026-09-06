from typing import Any
from typing import Generic

from pydantic import field_validator
from pydantic import model_validator

from ..base import BaseModel
from ..path import Path
from ..path import ResourceT


class ResponseParameters(BaseModel, Generic[ResourceT]):
    """:rfc:`RFC7644 §3.9 <7644#section-3.9>` ``attributes`` and ``excludedAttributes`` query parameters.

    Parameterising them with the resource type an endpoint serves, as in
    ``ResponseParameters[User]``, resolves each path against that model, so a
    server can tell which attribute a client asked for. An endpoint covering
    several types takes a union of them.
    """

    attributes: list[Path[ResourceT]] | None = None
    """A multi-valued list of strings indicating the names of resource
    attributes to return in the response, overriding the set of attributes that
    would be returned by default."""

    excluded_attributes: list[Path[ResourceT]] | None = None
    """A multi-valued list of strings indicating the names of resource
    attributes to be removed from the default set of attributes to return."""

    @field_validator("attributes", "excluded_attributes", mode="before")
    @classmethod
    def split_comma_separated(cls, value: Any) -> Any:
        """Split comma-separated strings into lists.

        :rfc:`RFC7644 §3.9 <7644#section-3.9>` defines these as
        comma-separated query parameter values.
        """
        if isinstance(value, str):
            return [v.strip() for v in value.split(",") if v.strip()]
        if isinstance(value, list) and len(value) == 1 and isinstance(value[0], str):
            return [v.strip() for v in value[0].split(",") if v.strip()]
        return value

    @model_validator(mode="after")
    def attributes_validator(self) -> "ResponseParameters[ResourceT]":
        if self.attributes and self.excluded_attributes:
            raise ValueError(
                "'attributes' and 'excluded_attributes' are mutually exclusive"
            )

        return self
