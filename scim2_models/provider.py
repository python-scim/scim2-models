"""The description of a SCIM service: the resources it serves and what it announces."""

import operator
from collections.abc import Iterable
from functools import cached_property
from functools import reduce
from types import TracebackType
from typing import Annotated
from typing import Any
from typing import TypeVar
from typing import cast

from .annotations import Required
from .policy import ScimPolicy
from .resources.resource import Extension
from .resources.resource import Resource
from .resources.resource_type import ResourceType
from .resources.schema import Schema
from .resources.service_provider_config import ServiceProviderConfig
from .scim_object import ScimObject

DescribedModel = type[Resource[Any]] | type[Extension]
"""A model a schema describes: a resource, or an extension of one."""

_AnyDescribed = TypeVar("_AnyDescribed", bound=ScimObject)

_DISCOVERY_ENDPOINTS: dict[type[Resource[Any]], str] = {
    Schema: "/Schemas",
    ResourceType: "/ResourceTypes",
    ServiceProviderConfig: "/ServiceProviderConfig",
}
"""The endpoints :rfc:`RFC7644 §4 <7644#section-4>` gives every service.

A service never publishes them among its resource types, so the lookups resolve
them apart from the registry.
"""


def _endpoint_key(endpoint: Any) -> str:
    """Return the key an endpoint is matched under.

    :rfc:`RFC7643 §6 <7643#section-6>` only says an endpoint is relative to the
    base URL, so a service may publish it with or without a leading slash.
    """
    return str(endpoint).casefold().lstrip("/")


def _schema_key(schema: Any) -> str:
    return str(schema).casefold()


_DISCOVERY_BY_NAME = {
    model.__name__.casefold(): model for model in _DISCOVERY_ENDPOINTS
}
_DISCOVERY_BY_SCHEMA = {
    _schema_key(model.__schema__): model for model in _DISCOVERY_ENDPOINTS
}
_DISCOVERY_BY_ENDPOINT = {
    _endpoint_key(endpoint): model for model, endpoint in _DISCOVERY_ENDPOINTS.items()
}


class ScimProviderError(ValueError):
    """A provider cannot describe a coherent service.

    Only the code that builds a provider raises this. It stays out of the
    :class:`~scim2_models.SCIMException` hierarchy, where every class maps to a
    ``scimType`` and turns into an :class:`~scim2_models.Error` response.
    """


class ScimProvider:
    """A SCIM service: the resources it serves, and the capabilities it declares.

    A service publishes ``schemas``, ``resource_types`` and ``config`` on the
    three discovery endpoints of :rfc:`RFC7644 §4 <7644#section-4>`. A server
    describes itself with a provider, and a client describes the peer it
    queries; the class carries no notion of either role.

    ``models`` is the catalogue of what the service can build: bare resources
    and extensions, each identified by its schema URI. ``resource_types`` binds
    extensions to a resource and gives it an endpoint, as :rfc:`RFC7643 §6
    <7643#section-6>` describes. The provider composes the two:

    >>> from scim2_models import EnterpriseUser, ResourceType, ScimProvider, User
    >>> provider = ScimProvider(
    ...     models=[User, EnterpriseUser],
    ...     resource_types=[ResourceType.from_resource(User[EnterpriseUser])],
    ... )
    >>> provider.model_for("User") is User[EnterpriseUser]
    True
    >>> provider.model_for(str(User.__schema__)) is User
    True

    Leave ``resource_types`` out for a service whose resources carry no
    extension: the provider derives one per resource.

    A provider is immutable. It validates its whole description at
    construction, since nothing can change afterwards.

    :param models: The bare resource and extension models the service builds
        its resources from.
    :param resource_types: The bindings between a resource, its extensions and
        an endpoint, derived from the models when left out.
    :param config: The capabilities the service declares.
    :raises ScimProviderError: When a model declares no schema or is already
        parameterized, when two models share a schema, when two resource types
        share a name or an endpoint, or when a resource type names a schema no
        model describes.
    """

    def __init__(
        self,
        models: Iterable[DescribedModel] = (),
        resource_types: Iterable[ResourceType] | None = None,
        config: ServiceProviderConfig | None = None,
        policy: ScimPolicy | None = None,
    ) -> None:
        self._models = tuple(models)
        self._config = config
        self._policy = policy or ScimPolicy()
        self._models_by_schema = self._index_models()
        self._resource_types = (
            tuple(resource_types)
            if resource_types is not None
            else tuple(
                ResourceType.from_resource(model)
                for model in self._models
                if issubclass(model, Resource)
            )
        )
        self._models_by_name: dict[str, type[Resource[Any]]] = {}
        self._models_by_endpoint: dict[str, type[Resource[Any]]] = {}
        self._index_resource_types()

    def _index_models(self) -> dict[str, DescribedModel]:
        by_schema: dict[str, DescribedModel] = {}
        for model in self._models:
            if not issubclass(model, Resource | Extension):
                raise ScimProviderError(
                    f"{model.__name__} is neither a resource nor an extension"
                )

            if hasattr(model, "__scim_extension_metadata__"):
                raise ScimProviderError(
                    f"{model.__name__} is already parameterized: list the bare "
                    "resource and its extensions, and bind them with a resource "
                    "type, as ResourceType.from_resource builds one"
                )

            schema = getattr(model, "__schema__", None)
            if not schema:
                raise ScimProviderError(f"{model.__name__} declares no schema")

            if _schema_key(schema) in by_schema:
                raise ScimProviderError(f"Two models share the schema {schema}")

            by_schema[_schema_key(schema)] = model
        return by_schema

    def _index_resource_types(self) -> None:
        for resource_type in self._resource_types:
            model = self._compose(resource_type)

            name = str(resource_type.name).casefold()
            if name in self._models_by_name:
                raise ScimProviderError(
                    f"Two resource types share the name {resource_type.name}"
                )

            endpoint = _endpoint_key(resource_type.endpoint)
            if endpoint in self._models_by_endpoint:
                raise ScimProviderError(
                    f"Two resource types share the endpoint {resource_type.endpoint}"
                )

            self._models_by_name[name] = model
            self._models_by_endpoint[endpoint] = model

    def _compose(self, resource_type: ResourceType) -> type[Resource[Any]]:
        """Build the model a resource type designates, extensions included."""
        model = self._described(resource_type.schema_, Resource)

        parameters = [
            Annotated[extension, Required.true] if declared.required else extension
            for declared in resource_type.schema_extensions or []
            for extension in [self._described(declared.schema_, Extension)]
        ]
        if not parameters:
            return model

        # The union is built and subscripted through the calls the syntax stands
        # for: mypy reads the index of a generic as a type, not as a value.
        return model.__class_getitem__(reduce(operator.or_, parameters))

    def _described(self, uri: Any, kind: type[_AnyDescribed]) -> type[_AnyDescribed]:
        model = self._models_by_schema.get(_schema_key(uri))
        if model is None or not issubclass(model, kind):
            raise ScimProviderError(f"No {kind.__name__.lower()} describes {uri}")
        return cast("type[_AnyDescribed]", model)

    @property
    def models(self) -> tuple[DescribedModel, ...]:
        """The bare resource and extension models the service builds from."""
        return self._models

    @property
    def resource_types(self) -> tuple[ResourceType, ...]:
        """What the service publishes on ``/ResourceTypes``."""
        return self._resource_types

    @property
    def config(self) -> ServiceProviderConfig | None:
        """What the service publishes on ``/ServiceProviderConfig``."""
        return self._config

    @property
    def policy(self) -> ScimPolicy:
        """How much the payloads the service reads may depart from the specification.

        Unlike :attr:`config`, this is never :data:`None`: a policy always
        applies, and a provider given none declares the strict reading.
        """
        return self._policy

    def __enter__(self) -> "ScimProvider":
        """Make the policy of this provider the one the block runs under."""
        self._policy.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Restore the policy the block interrupted."""
        self._policy.__exit__(exc_type, exc_value, traceback)

    @cached_property
    def schemas(self) -> tuple[Schema, ...]:
        """What the service publishes on ``/Schemas``.

        Every model contributes one schema, whether a resource type references
        it or not: a service may describe a schema before binding it.
        """
        return tuple(model.to_schema() for model in self._models)

    def model_for(self, key: str | Schema | ResourceType) -> type[ScimObject] | None:
        """Return the model a key designates, or :data:`None`.

        The name a resource type declares, or the
        :class:`~scim2_models.ResourceType` itself, answers the composed model,
        extensions included. That name is the one ``meta.resourceType`` carries
        (:rfc:`RFC7643 §6 <7643#section-6>`), not the name of a Python class and
        not an endpoint, which :meth:`model_for_endpoint` takes.

        A schema URI, or a :class:`~scim2_models.Schema`, answers the catalogue
        instead: the bare resource, or the extension the URI names.
        :rfc:`RFC7643 §3 <7643#section-3>` has ``meta.resourceType``, not
        ``schemas``, tell what a resource is.

        An unknown key is not a protocol error, so nothing is raised: a server
        answers it with a 404.

        >>> from scim2_models import ScimProvider, User
        >>> provider = ScimProvider(models=[User])
        >>> provider.model_for("User") is User
        True
        >>> provider.model_for("Pet") is None
        True

        The derived resource type is named after the last segment of the schema
        URI, which is why ``"User"`` answers above.
        """
        if isinstance(key, Schema):
            return self._model_for_schema(key.id)

        if isinstance(key, ResourceType):
            return self._models_by_name.get(str(key.name).casefold())

        if ":" in key:
            return self._model_for_schema(key)

        return self._models_by_name.get(key.casefold()) or _DISCOVERY_BY_NAME.get(
            key.casefold()
        )

    def _model_for_schema(self, schema: Any) -> type[ScimObject] | None:
        key = _schema_key(schema)
        return self._models_by_schema.get(key) or _DISCOVERY_BY_SCHEMA.get(key)

    def model_for_endpoint(self, endpoint: str) -> type[ScimObject] | None:
        """Return the composed model an endpoint serves, or :data:`None`.

        >>> from scim2_models import ScimProvider, User
        >>> provider = ScimProvider(models=[User])
        >>> provider.model_for_endpoint("/Users") is User
        True
        """
        key = _endpoint_key(endpoint)
        return self._models_by_endpoint.get(key) or _DISCOVERY_BY_ENDPOINT.get(key)

    @classmethod
    def from_discovery(
        cls,
        schemas: Iterable[Schema],
        resource_types: Iterable[ResourceType],
        config: ServiceProviderConfig | None = None,
        policy: ScimPolicy | None = None,
    ) -> "ScimProvider":
        """Build a provider from what a service publishes about itself.

        This is how a client describes the peer it queried, and how a server
        describes itself when its resources are configured rather than written
        in Python. Each schema becomes a model, a resource or an extension
        depending on how the resource types name it.

        :param schemas: What ``/Schemas`` answered.
        :param resource_types: What ``/ResourceTypes`` answered.
        :param config: What ``/ServiceProviderConfig`` answered.
        :param policy: How much the answers of the peer are allowed to depart
            from the specification. This is a choice, not something a service
            publishes about itself.
        :raises ScimProviderError: When a resource type names a schema the
            service does not publish.
        """
        resource_types = tuple(resource_types)
        extended = {
            _schema_key(declared.schema_)
            for resource_type in resource_types
            for declared in resource_type.schema_extensions or []
        }
        models = [
            Extension.from_schema(schema)
            if _schema_key(schema.id) in extended
            else Resource.from_schema(schema)
            for schema in schemas
        ]
        return cls(
            models=models,
            resource_types=resource_types,
            config=config,
            policy=policy,
        )
