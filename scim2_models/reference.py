from collections import UserString
from typing import Any
from typing import Generic
from typing import TypeVar
from typing import get_args
from typing import get_origin

from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema
from typing_extensions import NewType

from .utils import UNION_TYPES

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
            cls._validate,
            core_schema.union_schema(
                [core_schema.str_schema(), core_schema.is_instance_schema(cls)]
            ),
        )

    @classmethod
    def _validate(cls, input_value: Any, /) -> str:
        return str(input_value)

    @classmethod
    def get_types(cls, type_annotation: Any) -> list[str]:
        """Get reference types from a type annotation.

        :param type_annotation: Type annotation to extract reference types from
        :return: List of reference type strings
        """
        first_arg = get_args(type_annotation)[0]
        types = (
            get_args(first_arg) if get_origin(first_arg) in UNION_TYPES else [first_arg]
        )

        def serialize_ref_type(ref_type: Any) -> str:
            if ref_type == URIReference:
                return "uri"

            elif ref_type == ExternalReference:
                return "external"

            return str(get_args(ref_type)[0])

        return list(map(serialize_ref_type, types))
