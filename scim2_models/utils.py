import re
from functools import lru_cache
from inspect import isclass
from typing import TYPE_CHECKING
from typing import Any
from typing import Union
from typing import cast
from typing import get_args
from typing import get_origin

from pydantic.alias_generators import to_snake

if TYPE_CHECKING:
    from .base import BaseModel

try:
    from types import UnionType

    UNION_TYPES = [Union, UnionType]
except ImportError:
    # Python 3.9 has no UnionType
    UNION_TYPES = [Union]


def _model_union(annotation: Any) -> "tuple[type[BaseModel], ...] | None":
    """Return the models an annotation designates, or :data:`None` for anything else.

    A single model, a ``Union[User, Group]`` and a ``User | Group`` all name
    resource types to resolve against, which is what an endpoint covering
    several of them binds. A type variable or a plain type names none.
    """
    if isclass(annotation) and hasattr(annotation, "model_fields"):
        return (cast("type[BaseModel]", annotation),)

    if get_origin(annotation) in UNION_TYPES:
        members = get_args(annotation)
        if members and all(
            isclass(each) and hasattr(each, "model_fields") for each in members
        ):
            return cast("tuple[type[BaseModel], ...]", members)
    return None


_UNDERSCORE_ALPHANUMERIC = re.compile(r"_+([0-9A-Za-z]+)")
_NON_WORD_UNDERSCORE = re.compile(r"[\W_]+")


def _int_to_str(status: int | None) -> str | None:
    return None if status is None else str(status)


def _to_camel(string: str) -> str:
    """Transform strings to camelCase.

    This method is used for attribute name serialization. This is more
    or less the pydantic implementation, but it does not add uppercase
    on alphanumerical characters after specials characters. For instance
    '$ref' stays '$ref'.
    """
    snake = to_snake(string)
    camel = _UNDERSCORE_ALPHANUMERIC.sub(lambda m: m.group(1).title(), snake)
    return camel


@lru_cache(maxsize=256)
def _normalize_attribute_name(attribute_name: str) -> str:
    """Remove all non-alphabetical characters and lowerise a string.

    This method is used for attribute name validation.
    """
    is_extension_attribute = ":" in attribute_name
    if not is_extension_attribute:
        attribute_name = _NON_WORD_UNDERSCORE.sub("", attribute_name)

    return attribute_name.lower()


def _find_field_name(model_class: type["BaseModel"], attr_name: str) -> str | None:
    """Find the actual field name in a resource class from an attribute name.

    :param resource_class: The resource class to search in
    :param attr_name: The attribute name to find (e.g., "nickName")
    :returns: The actual field name if found (e.g., "nick_name"), None otherwise
    """
    normalized_attr_name = _normalize_attribute_name(attr_name)

    for field_key in model_class.model_fields:
        if _normalize_attribute_name(field_key) == normalized_attr_name:
            return field_key

    return None
