from typing import Annotated

from ..base import BaseModel
from ..base import Required


class Message(BaseModel):
    """SCIM protocol messages as defined by :rfc:`RFC7644 §3.1 <7644#section-3.1>`."""

    schemas: Annotated[list[str], Required.true]
