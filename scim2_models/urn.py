from typing import Any

from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema


class URN(str):
    """URN string type with validation."""

    def __new__(cls, urn: str) -> "URN":
        cls._check_syntax(urn)
        return super().__new__(cls, urn)

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source: type[Any],
        _handler: GetCoreSchemaHandler,
    ) -> core_schema.CoreSchema:
        return core_schema.no_info_after_validator_function(
            cls,
            core_schema.str_schema(),
            serialization=core_schema.plain_serializer_function_ser_schema(
                str,
            ),
        )

    @classmethod
    def _check_syntax(cls, path: str) -> None:
        """Check that a string is a URN, and raise ValueError otherwise."""
        if not path.startswith("urn:"):
            raise ValueError("The URN does not start with urn:")

        urn_segments = path.split(":")
        if len(urn_segments) < 3:
            raise ValueError("URNs must have at least 3 parts")
