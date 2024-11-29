import re
from typing import Optional
from typing import Union

from pydantic.alias_generators import to_snake

try:
    from types import UnionType  # type: ignore

    UNION_TYPES = [Union, UnionType]
except ImportError:
    # Python 3.9 has no UnionType
    UNION_TYPES = [Union]


def int_to_str(status: Optional[int]) -> Optional[str]:
    return None if status is None else str(status)


def to_camel(string: str) -> str:
    """Transform strings to camelCase.

    This method is used for attribute name serialization. This is more
    or less the pydantic implementation, but it does not add uppercase
    on alphanumerical characters after specials characters. For instance
    '$ref' stays '$ref'.
    """
    snake = to_snake(string)
    camel = re.sub(r"_+([0-9A-Za-z]+)", lambda m: m.group(1).title(), snake)
    return camel


def normalize_attribute_name(attribute_name: str) -> str:
    """Remove all non-alphabetical characters and lowerise a string.

    This method is used for attribute name validation.
    """
    is_extension_attribute = ":" in attribute_name
    if not is_extension_attribute:
        attribute_name = re.sub(r"[\W_]+", "", attribute_name)

    return attribute_name.lower()
