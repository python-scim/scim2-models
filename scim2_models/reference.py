from collections import UserString
from typing import Any
from typing import Generic
from typing import TypeVar

from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema
from typing_extensions import NewType

ReferenceTypes = TypeVar("ReferenceTypes")

URIReference = NewType("URIReference", str)
ExternalReference = NewType("ExternalReference", str)


class Reference(UserString, Generic[ReferenceTypes]):
    """Reference type as defined in :rfc:`RFC7643 §2.3.7 <7643#section-2.3.7>`.

    References can take different type parameters:

        - Any :class:`~scim2_models.Resource` subtype, or :class:`~typing.ForwardRef` of a Resource subtype, or :data:`~typing.Union` of those,
        - :data:`~scim2_models.ExternalReference`
        - :data:`~scim2_models.URIReference`

    Examples
    --------

    .. code-block:: python

        class Foobar(Resource):
            bff: Reference[User]
            managers: Reference[Union["User", "Group"]]
            photo: Reference[ExternalReference]
            website: Reference[URIReference]

    """

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source: type[Any],
        _handler: GetCoreSchemaHandler,
    ) -> core_schema.CoreSchema:
        return core_schema.no_info_after_validator_function(
            cls._validate, core_schema.str_schema()
        )

    @classmethod
    def _validate(cls, input_value: str, /) -> str:
        return input_value
