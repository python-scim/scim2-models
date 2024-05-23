from typing import List
from typing import Optional

from pydantic import AnyUrl
from pydantic import BaseModel
from pydantic import Extra
from pydantic import Field


class SchemaExtension(BaseModel):
    class Config:
        extra = Extra.allow

    schema_: AnyUrl = Field(
        ..., alias="schema", description="The URI of a schema extension."
    )
    required: bool = Field(
        ...,
        description="A Boolean value that specifies whether or not the schema extension is required for the resource type.  If true, a resource of this type MUST include this schema extension and also include any attributes declared as required in this schema extension. If false, a resource of this type MAY omit this schema extension.",
    )


class ResourceType(BaseModel):
    class Config:
        extra = Extra.allow

    id: Optional[str] = Field(
        None,
        description="The resource type's server unique id. May be the same as the 'name' attribute.",
    )
    name: str = Field(
        ...,
        description="The resource type name.  When applicable, service providers MUST specify the name, e.g., 'User'.",
    )
    description: Optional[str] = Field(
        None,
        description="The resource type's human-readable description.  When applicable, service providers MUST specify the description.",
    )
    endpoint: str = Field(
        ...,
        description="The resource type's HTTP-addressable endpoint relative to the Base URL, e.g., '/Users'.",
    )
    schema_: AnyUrl = Field(
        ..., alias="schema", description="The resource type's primary/base schema URI."
    )
    schemaExtensions: Optional[List[SchemaExtension]] = Field(
        None, description="A list of URIs of the resource type's schema extensions."
    )
