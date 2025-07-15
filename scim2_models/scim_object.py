"""Base SCIM object classes with schema identification."""

from typing import Annotated

from .annotations import Required
from .base import BaseModel


class SchemaObject(BaseModel):
    schemas: Annotated[list[str], Required.true]
    """The "schemas" attribute is a REQUIRED attribute and is an array of
    Strings containing URIs that are used to indicate the namespaces of the
    SCIM schemas that define the attributes present in the current JSON
    structure."""


class ScimObject(SchemaObject): ...
