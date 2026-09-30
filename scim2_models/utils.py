import re
from contextvars import ContextVar
from contextvars import Token
from inspect import isclass
from types import UnionType
from typing import TYPE_CHECKING
from typing import Any
from typing import Generic
from typing import TypeVar
from typing import Union
from typing import cast
from typing import get_args
from typing import get_origin

from pydantic.alias_generators import to_snake

if TYPE_CHECKING:
    from .base import BaseModel

UNION_TYPES = [Union, UnionType]

T = TypeVar("T")


class _AmbientStack(Generic[T]):
    """The values of the blocks a call runs inside, the innermost one being current.

    Each entry keeps the token of the value it set, and a block that exits
    resets the token of its own latest entry. A block that exits in a context
    where it did not enter raises instead of removing the entry of another
    block. Instances are meant to live at module level, like the context
    variables they hold.
    """

    def __init__(self, name: str) -> None:
        self._current: ContextVar[T | None] = ContextVar(name, default=None)
        self._entries: ContextVar[tuple[tuple[T, Token[T | None]], ...]] = ContextVar(
            f"{name}_entries", default=()
        )

    def get(self) -> T | None:
        """Return the value of the innermost open block, if any."""
        return self._current.get()

    def enter(self, value: T) -> None:
        """Make a value current until the block it opens exits."""
        token = self._current.set(value)
        self._entries.set((*self._entries.get(), (value, token)))

    def exit(self, value: T) -> None:
        """Restore the value that was current when the latest block of a value entered.

        Raise RuntimeError when the value entered no block in this context, and
        ValueError when it entered in another context.
        """
        entries = self._entries.get()
        index = next(
            (i for i in reversed(range(len(entries))) if entries[i][0] is value),
            None,
        )
        if index is None:
            raise RuntimeError(
                f"This {type(value).__name__} exits a block it did not enter in this context"
            )
        self._current.reset(entries[index][1])
        self._entries.set(entries[:index] + entries[index + 1 :])


def _model_union(annotation: Any) -> "tuple[type[BaseModel], ...] | None":
    """Return the models an annotation designates, or None for anything else.

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


def _int_to_str(status: int | None) -> str | None:
    return None if status is None else str(status)


def _to_camel(string: str) -> str:
    """Transform strings to camelCase.

    This method is used for attribute name serialization. This is more or less
    the pydantic implementation, but it does not add uppercase on
    alphanumerical characters after specials characters. For instance '$ref'
    stays '$ref'.
    """
    snake = to_snake(string)
    camel = _UNDERSCORE_ALPHANUMERIC.sub(lambda m: m.group(1).title(), snake)
    return camel


def _normalize_attribute_name(attribute_name: str) -> str:
    """Fold the case of an attribute name.

    RFC7643 §2.1 makes attribute names case-insensitive, and its ``nameChar``
    rule makes ``$``, ``-`` and ``_`` part of a name, so the case is all there
    is to fold.
    """
    return attribute_name.lower()


def _find_field_name(model_class: type["BaseModel"], attr_name: str) -> str | None:
    """Return the field a SCIM attribute name designates, or None.

    ``nickName`` designates the ``nick_name`` field, and ``$ref`` the ``ref``
    one.
    """
    return model_class.__scim_info__.field_by_name.get(
        _normalize_attribute_name(attr_name)
    )
