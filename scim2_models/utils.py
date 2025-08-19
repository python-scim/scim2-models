import base64
import re
from typing import TYPE_CHECKING
from typing import Annotated
from typing import Literal
from typing import Union

from pydantic import EncodedBytes
from pydantic import EncoderProtocol
from pydantic.alias_generators import to_snake
from pydantic_core import PydanticCustomError

if TYPE_CHECKING:
    from .base import BaseModel

try:
    from types import UnionType

    UNION_TYPES = [Union, UnionType]
except ImportError:
    # Python 3.9 has no UnionType
    UNION_TYPES = [Union]

_UNDERSCORE_ALPHANUMERIC = re.compile(r"_+([0-9A-Za-z]+)")
_NON_WORD_UNDERSCORE = re.compile(r"[\W_]+")


def _int_to_str(status: int | None) -> str | None:
    return None if status is None else str(status)


# Copied from Pydantic 2.10 repository
class _Base64Encoder(EncoderProtocol):  # pragma: no cover
    """Standard (non-URL-safe) Base64 encoder."""

    @classmethod
    def decode(cls, data: bytes) -> bytes:
        """Decode the data from base64 encoded bytes to original bytes data.

        Args:
            data: The data to decode.

        Returns:
            The decoded data.

        """
        try:
            return base64.b64decode(data)
        except ValueError as e:
            raise PydanticCustomError(
                "base64_decode", "Base64 decoding error: '{error}'", {"error": str(e)}
            ) from e

    @classmethod
    def encode(cls, value: bytes) -> bytes:
        """Encode the data from bytes to a base64 encoded bytes.

        Args:
            value: The data to encode.

        Returns:
            The encoded data.

        """
        return base64.b64encode(value)

    @classmethod
    def get_json_format(cls) -> Literal["base64"]:
        """Get the JSON format for the encoded data.

        Returns:
            The JSON format for the encoded data.

        """
        return "base64"


# Compatibility with Pydantic <2.10
# https://pydantic.dev/articles/pydantic-v2-10-release#use-b64decode-and-b64encode-for-base64bytes-and-base64str-types
Base64Bytes = Annotated[bytes, EncodedBytes(encoder=_Base64Encoder)]


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
