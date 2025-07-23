from enum import Enum
from enum import auto


class Context(Enum):
    """Represent the different HTTP contexts detailed in :rfc:`RFC7644 §3.2 <7644#section-3.2>`.

    Contexts are intended to be used during model validation and serialization.
    For instance a client preparing a resource creation POST request can use
    :code:`resource.model_dump(Context.RESOURCE_CREATION_REQUEST)` and
    the server can then validate it with
    :code:`resource.model_validate(Context.RESOURCE_CREATION_REQUEST)`.
    """

    DEFAULT = auto()
    """The default context.

    All fields are accepted during validation, and all fields are
    serialized during a dump.
    """

    RESOURCE_CREATION_REQUEST = auto()
    """The resource creation request context.

    Should be used for clients building a payload for a resource creation request,
    and servers validating resource creation request payloads.

    - When used for serialization, it will not dump attributes annotated with :attr:`~scim2_models.Mutability.read_only`.
    - When used for validation, it will raise a :class:`~pydantic.ValidationError`:
        - when finding attributes annotated with :attr:`~scim2_models.Mutability.read_only`,
        - when attributes annotated with :attr:`Required.true <scim2_models.Required.true>` are missing on null.
    """

    RESOURCE_CREATION_RESPONSE = auto()
    """The resource creation response context.

    Should be used for servers building a payload for a resource
    creation response, and clients validating resource creation response
    payloads.

    - When used for validation, it will raise a :class:`~pydantic.ValidationError` when finding attributes annotated with :attr:`~scim2_models.Returned.never` or when attributes annotated with :attr:`~scim2_models.Returned.always` are missing or :data:`None`;
    - When used for serialization, it will:
        - always dump attributes annotated with :attr:`~scim2_models.Returned.always`;
        - never dump attributes annotated with :attr:`~scim2_models.Returned.never`;
        - dump attributes annotated with :attr:`~scim2_models.Returned.default` unless they are explicitly excluded;
        - not dump attributes annotated with :attr:`~scim2_models.Returned.request` unless they are explicitly included.
    """

    RESOURCE_QUERY_REQUEST = auto()
    """The resource query request context.

    Should be used for clients building a payload for a resource query request,
    and servers validating resource query request payloads.

    - When used for serialization, it will not dump attributes annotated with :attr:`~scim2_models.Mutability.write_only`.
    - When used for validation, it will raise a :class:`~pydantic.ValidationError` when finding attributes annotated with :attr:`~scim2_models.Mutability.write_only`.
    """

    RESOURCE_QUERY_RESPONSE = auto()
    """The resource query response context.

    Should be used for servers building a payload for a resource query
    response, and clients validating resource query response payloads.

    - When used for validation, it will raise a :class:`~pydantic.ValidationError` when finding attributes annotated with :attr:`~scim2_models.Returned.never` or when attributes annotated with :attr:`~scim2_models.Returned.always` are missing or :data:`None`;
    - When used for serialization, it will:
        - always dump attributes annotated with :attr:`~scim2_models.Returned.always`;
        - never dump attributes annotated with :attr:`~scim2_models.Returned.never`;
        - dump attributes annotated with :attr:`~scim2_models.Returned.default` unless they are explicitly excluded;
        - not dump attributes annotated with :attr:`~scim2_models.Returned.request` unless they are explicitly included.
    """

    RESOURCE_REPLACEMENT_REQUEST = auto()
    """The resource replacement request context.

    Should be used for clients building a payload for a resource replacement request,
    and servers validating resource replacement request payloads.

    - When used for serialization, it will not dump attributes annotated with :attr:`~scim2_models.Mutability.read_only`.
    - When used for validation, it will ignore attributes annotated with :attr:`scim2_models.Mutability.read_only` and raise a :class:`~pydantic.ValidationError`:
        - when finding attributes annotated with :attr:`~scim2_models.Mutability.immutable` different than the ``original`` parameter passed to :meth:`~scim2_models.BaseModel.model_validate`;
        - when attributes annotated with :attr:`Required.true <scim2_models.Required.true>` are missing on null.
    """

    RESOURCE_REPLACEMENT_RESPONSE = auto()
    """The resource replacement response context.

    Should be used for servers building a payload for a resource
    replacement response, and clients validating resource query
    replacement payloads.

    - When used for validation, it will raise a :class:`~pydantic.ValidationError` when finding attributes annotated with :attr:`~scim2_models.Returned.never` or when attributes annotated with :attr:`~scim2_models.Returned.always` are missing or :data:`None`;
    - When used for serialization, it will:
        - always dump attributes annotated with :attr:`~scim2_models.Returned.always`;
        - never dump attributes annotated with :attr:`~scim2_models.Returned.never`;
        - dump attributes annotated with :attr:`~scim2_models.Returned.default` unless they are explicitly excluded;
        - not dump attributes annotated with :attr:`~scim2_models.Returned.request` unless they are explicitly included.
    """

    SEARCH_REQUEST = auto()
    """The search request context.

    Should be used for clients building a payload for a search request,
    and servers validating search request payloads.

    - When used for serialization, it will not dump attributes annotated with :attr:`~scim2_models.Mutability.write_only`.
    - When used for validation, it will raise a :class:`~pydantic.ValidationError` when finding attributes annotated with :attr:`~scim2_models.Mutability.write_only`.
    """

    SEARCH_RESPONSE = auto()
    """The resource query response context.

    Should be used for servers building a payload for a search response,
    and clients validating resource search payloads.

    - When used for validation, it will raise a :class:`~pydantic.ValidationError` when finding attributes annotated with :attr:`~scim2_models.Returned.never` or when attributes annotated with :attr:`~scim2_models.Returned.always` are missing or :data:`None`;
    - When used for serialization, it will:
        - always dump attributes annotated with :attr:`~scim2_models.Returned.always`;
        - never dump attributes annotated with :attr:`~scim2_models.Returned.never`;
        - dump attributes annotated with :attr:`~scim2_models.Returned.default` unless they are explicitly excluded;
        - not dump attributes annotated with :attr:`~scim2_models.Returned.request` unless they are explicitly included.
    """

    RESOURCE_PATCH_REQUEST = auto()
    """The resource patch request context.

    Should be used for clients building a payload for a PATCH request,
    and servers validating PATCH request payloads.

    - When used for serialization, it will not dump attributes annotated with :attr:`~scim2_models.Mutability.read_only`.
    - When used for validation, it will raise a :class:`~pydantic.ValidationError`:
        - when finding attributes annotated with :attr:`~scim2_models.Mutability.read_only`,
        - when attributes annotated with :attr:`Required.true <scim2_models.Required.true>` are missing or null.
    """

    RESOURCE_PATCH_RESPONSE = auto()
    """The resource patch response context.

    Should be used for servers building a payload for a PATCH response,
    and clients validating patch response payloads.

    - When used for validation, it will raise a :class:`~pydantic.ValidationError` when finding attributes annotated with :attr:`~scim2_models.Returned.never` or when attributes annotated with :attr:`~scim2_models.Returned.always` are missing or :data:`None`;
    - When used for serialization, it will:
        - always dump attributes annotated with :attr:`~scim2_models.Returned.always`;
        - never dump attributes annotated with :attr:`~scim2_models.Returned.never`;
        - dump attributes annotated with :attr:`~scim2_models.Returned.default` unless they are explicitly excluded;
        - not dump attributes annotated with :attr:`~scim2_models.Returned.request` unless they are explicitly included.
    """

    @classmethod
    def is_request(cls, ctx: "Context") -> bool:
        return ctx in (
            cls.RESOURCE_CREATION_REQUEST,
            cls.RESOURCE_QUERY_REQUEST,
            cls.RESOURCE_REPLACEMENT_REQUEST,
            cls.SEARCH_REQUEST,
            cls.RESOURCE_PATCH_REQUEST,
        )

    @classmethod
    def is_response(cls, ctx: "Context") -> bool:
        return ctx in (
            cls.RESOURCE_CREATION_RESPONSE,
            cls.RESOURCE_QUERY_RESPONSE,
            cls.RESOURCE_REPLACEMENT_RESPONSE,
            cls.SEARCH_RESPONSE,
            cls.RESOURCE_PATCH_RESPONSE,
        )
