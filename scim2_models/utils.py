import re
from typing import Optional

from pydantic.alias_generators import to_snake


def int_to_str(status: Optional[int]) -> Optional[str]:
    return None if status is None else str(status)


def to_camel(string: str) -> str:
    """Transform strings to camelCase.

    This is more or less the pydantic implementation, but it does not
    add uppercase on alphanumerical characters after specials
    characters. For instance '$ref' stays '$ref'.
    """

    snake = to_snake(string)
    camel = re.sub(r"_+([0-9A-Za-z]+)", lambda m: m.group(1).title(), snake)
    return camel
