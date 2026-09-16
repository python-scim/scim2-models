"""The provider and the service provider configuration a pass runs under."""

from typing import Any

import pytest
from pydantic import SerializationInfo
from pydantic import ValidationInfo
from pydantic import ValidatorFunctionWrapHandler
from pydantic import field_serializer
from pydantic import model_validator

from scim2_models import URN
from scim2_models import ComplexAttribute
from scim2_models import Resource
from scim2_models import ScimProvider
from scim2_models import ServiceProviderConfig
from scim2_models.provider import _provider
from scim2_models.provider import _spc

VALIDATION_PROVIDERS: list[ScimProvider | None] = []
VALIDATION_CONFIGS: list[ServiceProviderConfig | None] = []
SERIALIZATION_PROVIDERS: list[ScimProvider | None] = []
SERIALIZATION_CONFIGS: list[ServiceProviderConfig | None] = []


class Probe(ComplexAttribute):
    """Record the provider and the configuration each pass over this attribute reads."""

    label: str | None = None

    @model_validator(mode="wrap")
    @classmethod
    def _record_validation(
        cls, value: Any, handler: ValidatorFunctionWrapHandler, info: ValidationInfo
    ) -> "Probe":
        VALIDATION_PROVIDERS.append(_provider(info))
        VALIDATION_CONFIGS.append(_spc(info))
        return handler(value)  # type: ignore[no-any-return]

    @field_serializer("label")
    def _record_serialization(self, value: Any, info: SerializationInfo) -> Any:
        SERIALIZATION_PROVIDERS.append(_provider(info))
        SERIALIZATION_CONFIGS.append(_spc(info))
        return value


class Probed(Resource):
    __schema__ = URN("urn:org:example:Probed")

    probe: Probe | None = None


PAYLOAD = {"schemas": [str(Probed.__schema__)], "probe": {"label": "a"}}
SERVED = ServiceProviderConfig(documentation_uri="https://served.example")
PEER = ServiceProviderConfig(documentation_uri="https://peer.example")


@pytest.fixture(autouse=True)
def forget_recorded_passes():
    VALIDATION_PROVIDERS.clear()
    VALIDATION_CONFIGS.clear()
    SERIALIZATION_PROVIDERS.clear()
    SERIALIZATION_CONFIGS.clear()


@pytest.fixture
def provider():
    return ScimProvider(models=[Probed], config=SERVED)


def test_a_pass_given_nothing_knows_of_no_provider():
    """Nothing is assumed about a peer nobody described."""
    Probed.model_validate(PAYLOAD)

    assert VALIDATION_PROVIDERS == [None]
    assert VALIDATION_CONFIGS == [None]


def test_a_provider_named_at_the_call_reaches_a_validation(provider):
    """The provider crosses the whole payload, down to a nested attribute."""
    Probed.model_validate(PAYLOAD, scim_provider=provider)

    assert VALIDATION_PROVIDERS == [provider]


def test_a_provider_named_at_the_call_reaches_a_validation_from_json(provider):
    """Reading JSON carries the provider the way reading a dict does."""
    Probed.model_validate_json(
        '{"schemas": ["urn:org:example:Probed"], "probe": {"label": "a"}}',
        scim_provider=provider,
    )

    assert VALIDATION_PROVIDERS == [provider]


def test_a_provider_named_at_the_call_reaches_a_serialization(provider):
    """A dump reads the provider the way a validation does."""
    resource = Probed.model_validate(PAYLOAD)

    resource.model_dump(scim_provider=provider)

    assert SERIALIZATION_PROVIDERS == [provider]


def test_a_provider_named_at_the_call_reaches_a_serialization_for_json(provider):
    """Dumping to JSON carries the provider the way dumping to a dict does."""
    resource = Probed.model_validate(PAYLOAD)

    resource.model_dump_json(scim_provider=provider)

    assert SERIALIZATION_PROVIDERS == [provider]


def test_a_pass_reads_the_configuration_its_provider_carries(provider):
    """Naming a provider is enough: what the service declares travels with it."""
    Probed.model_validate(PAYLOAD, scim_provider=provider)

    assert VALIDATION_CONFIGS == [SERVED]


def test_a_configuration_alone_reaches_a_pass():
    """A client that discovered a peer has its configuration before it builds a provider."""
    Probed.model_validate(PAYLOAD, scim_spc=PEER)

    assert VALIDATION_PROVIDERS == [None]
    assert VALIDATION_CONFIGS == [PEER]


def test_a_configuration_named_at_the_call_wins_over_the_one_of_the_provider(provider):
    """One provider serves peers that declare different capabilities."""
    Probed.model_validate(PAYLOAD, scim_provider=provider, scim_spc=PEER)

    assert VALIDATION_PROVIDERS == [provider]
    assert VALIDATION_CONFIGS == [PEER]


def test_a_provider_carrying_no_configuration_publishes_none():
    """Unlike its policy, the configuration of a provider is optional."""
    Probed.model_validate(PAYLOAD, scim_provider=ScimProvider(models=[Probed]))

    assert VALIDATION_CONFIGS == [None]


def test_a_provider_set_around_a_block_reaches_a_validation(provider):
    """A server states once per request what it serves, instead of at every call."""
    with provider:
        Probed.model_validate(PAYLOAD)

    assert VALIDATION_PROVIDERS == [provider]
    assert VALIDATION_CONFIGS == [SERVED]


def test_a_provider_set_around_a_block_reaches_a_serialization(provider):
    """A dump made inside a block reads the provider the block opened."""
    resource = Probed.model_validate(PAYLOAD)

    with provider:
        resource.model_dump()

    assert SERIALIZATION_PROVIDERS == [provider]
    assert SERIALIZATION_CONFIGS == [SERVED]


def test_a_provider_named_at_the_call_wins_over_the_ambient_one(provider):
    """The call names what it wants, and the block only says what is otherwise meant."""
    other = ScimProvider(models=[Probed], config=PEER)

    with provider:
        Probed.model_validate(PAYLOAD, scim_provider=other)

    assert VALIDATION_PROVIDERS == [other]
    assert VALIDATION_CONFIGS == [PEER]


def test_a_configuration_named_at_the_call_wins_over_the_ambient_provider(provider):
    """Answering one peer under a block does not rewrite what the block serves."""
    with provider:
        Probed.model_validate(PAYLOAD, scim_spc=PEER)

    assert VALIDATION_PROVIDERS == [provider]
    assert VALIDATION_CONFIGS == [PEER]


def test_leaving_a_block_forgets_its_provider(provider):
    """A payload read under a provider is not read under it forever."""
    with provider:
        pass
    Probed.model_validate(PAYLOAD)

    assert VALIDATION_PROVIDERS == [None]


def test_a_nested_block_restores_the_provider_it_interrupted(provider):
    """Blocks stack, so an inner description does not outlive itself."""
    inner = ScimProvider(models=[Probed], config=PEER)

    with provider:
        with inner:
            Probed.model_validate(PAYLOAD)
        Probed.model_validate(PAYLOAD)

    assert VALIDATION_PROVIDERS == [inner, provider]


def test_an_ambient_provider_reaches_a_revalidated_assignment(provider):
    """Assigning an attribute revalidates in plain Python, out of reach of a call argument."""
    resource = Probed.model_validate(PAYLOAD)
    VALIDATION_PROVIDERS.clear()

    with provider:
        resource.probe = {"label": "b"}

    assert VALIDATION_PROVIDERS == [provider]
