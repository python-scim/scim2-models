from typing import List

from ..base import BaseModel


class Message(BaseModel):
    """SCIM protocol messages as defined by :rfc:`RFC7644 §3.1
    <7644#section-3.1>`."""

    schemas: List[str]
