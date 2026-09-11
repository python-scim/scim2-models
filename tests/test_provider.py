from typing import Annotated
from typing import Any

import pytest
from pydantic import ValidationError

from scim2_models import URI
from scim2_models import URN
from scim2_models import Context
from scim2_models import EnterpriseUser
from scim2_models import Error
from scim2_models import Extension
from scim2_models import Group
from scim2_models import Reference
from scim2_models import Required
from scim2_models import Resource
from scim2_models import ResourceType
from scim2_models import Schema
from scim2_models import SchemaExtension
from scim2_models import ScimProvider
from scim2_models import ScimProviderError
from scim2_models import ServiceProviderConfig
from scim2_models import User


class PetOwner(Extension):
    __schema__ = URN("urn:example:2.0:PetOwner")

    pet_name: str | None = None


def resource_type(name, endpoint, schema, extensions=()):
    """Build a resource type binding a resource to the extensions it carries."""
    return ResourceType(
        id=name,
        name=name,
        description=name,
        endpoint=Reference[URI](endpoint),
        schema_=Reference[URI](schema),
        schema_extensions=[
            SchemaExtension(schema_=Reference[URI](str(schema)), required=required)
            for schema, required in extensions
        ],
    )


# The catalogue of models


def test_a_provider_publishes_the_schema_of_each_model():
    """Every model contributes one schema to ``/Schemas``, in the order it was listed."""
    provider = ScimProvider(models=[User, Group, PetOwner])

    assert [schema.id for schema in provider.schemas] == [
        User.__schema__,
        Group.__schema__,
        PetOwner.__schema__,
    ]


def test_an_extension_no_resource_type_references_is_still_published():
    """A service may describe a schema before binding it to a resource type."""
    provider = ScimProvider(models=[User, PetOwner])

    assert PetOwner.__schema__ in [schema.id for schema in provider.schemas]
    assert provider.model_for(str(PetOwner.__schema__)) is PetOwner


def test_two_models_sharing_a_schema_are_refused():
    """A schema URI designates one model, since it is how a payload names it."""

    class Twin(Resource[Any]):
        __schema__ = URN(str(User.__schema__))

    with pytest.raises(ScimProviderError, match=str(User.__schema__)):
        ScimProvider(models=[User, Twin])


def test_a_parameterized_model_is_refused():
    """A resource type binds a resource to its extensions, and nothing else does.

    :rfc:`RFC7643 §6 <7643#section-6>` has ``schemaExtensions`` carry that
    binding. Letting a parameterized model carry it too would give a service two
    ways to say one thing, and no way to settle a disagreement.
    """
    with pytest.raises(ScimProviderError, match="from_resource"):
        ScimProvider(models=[User[EnterpriseUser]])


def test_a_model_that_is_neither_a_resource_nor_an_extension_is_refused():
    """A catalogue describes what a service serves, not the messages carrying it."""
    with pytest.raises(ScimProviderError, match="neither a resource nor an extension"):
        ScimProvider(models=[Error])


def test_a_model_declaring_no_schema_is_refused():
    """A model with no ``__schema__`` cannot be indexed, nor named by a resource type."""

    class Anonymous(Resource[Any]):
        label: str | None = None

    with pytest.raises(ScimProviderError, match="Anonymous declares no schema"):
        ScimProvider(models=[Anonymous])


# Composing a resource with its extensions


def test_a_resource_type_composes_its_resource_with_its_extensions():
    """The catalogue holds bare models, and the resource type says how to assemble them."""
    provider = ScimProvider(
        models=[User, EnterpriseUser],
        resource_types=[ResourceType.from_resource(User[EnterpriseUser])],
    )

    assert provider.model_for("User") is User[EnterpriseUser]


def test_a_required_extension_is_composed_as_required():
    """``schemaExtensions.required`` survives composition and refuses a creation without it."""
    provider = ScimProvider(
        models=[User, EnterpriseUser],
        resource_types=[
            ResourceType.from_resource(User[Annotated[EnterpriseUser, Required.true]])
        ],
    )

    with pytest.raises(ValidationError, match="is required"):
        provider.model_for("User").model_validate(
            {"schemas": [User.__schema__], "userName": "bjensen"},
            scim_ctx=Context.RESOURCE_CREATION_REQUEST,
        )


def test_two_resource_types_serve_two_variants_of_one_schema():
    """:rfc:`RFC7643 §6 <7643#section-6>` binds extensions and endpoint to the resource type.

    Two resource types may therefore share a base schema and differ by their
    extensions, each served under its own endpoint. ``meta.resourceType`` is
    what tells the resources apart, as :rfc:`RFC7643 §3 <7643#section-3>` says.
    """
    provider = ScimProvider(
        models=[User, PetOwner],
        resource_types=[
            resource_type("User", "/Users", User.__schema__),
            resource_type(
                "PetOwner",
                "/PetOwners",
                User.__schema__,
                [(PetOwner.__schema__, False)],
            ),
        ],
    )

    assert provider.model_for_endpoint("/Users") is User
    assert provider.model_for_endpoint("/PetOwners") is User[PetOwner]


def test_resource_types_are_derived_without_extensions_when_they_are_left_out():
    """A service whose resources carry no extension needs to declare nothing."""
    provider = ScimProvider(models=[User, Group])

    assert [(rt.name, rt.endpoint) for rt in provider.resource_types] == [
        ("User", "/Users"),
        ("Group", "/Groups"),
    ]
    assert provider.model_for("User") is User


def test_a_resource_type_naming_a_schema_no_model_describes_is_refused():
    """A resource type the provider cannot compose is a broken description."""
    with pytest.raises(ScimProviderError, match=str(Group.__schema__)):
        ScimProvider(models=[User], resource_types=[ResourceType.from_resource(Group)])


def test_a_resource_type_naming_an_extension_no_model_describes_is_refused():
    """An extension is looked up in the catalogue like the resource it extends."""
    with pytest.raises(ScimProviderError, match=str(EnterpriseUser.__schema__)):
        ScimProvider(
            models=[User],
            resource_types=[ResourceType.from_resource(User[EnterpriseUser])],
        )


def test_a_resource_type_naming_a_resource_as_its_extension_is_refused():
    """An extension is not a resource, and a resource does not extend another."""
    with pytest.raises(ScimProviderError, match=str(Group.__schema__)):
        ScimProvider(
            models=[User, Group],
            resource_types=[
                resource_type(
                    "User", "/Users", User.__schema__, [(Group.__schema__, False)]
                )
            ],
        )


# Lookups


def test_a_schema_uri_answers_the_bare_model():
    """A schema URI designates a schema, not a resource type.

    The catalogue answers it: the resource without its extensions, or the
    extension itself.
    """
    provider = ScimProvider(
        models=[User, EnterpriseUser],
        resource_types=[ResourceType.from_resource(User[EnterpriseUser])],
    )

    assert provider.model_for(str(User.__schema__)) is User
    assert provider.model_for(str(EnterpriseUser.__schema__)) is EnterpriseUser
    assert provider.model_for(User.to_schema()) is User


def test_a_name_and_an_endpoint_answer_the_composed_model():
    """The four ways of naming a resource type all reach the same composed class."""
    provider = ScimProvider(
        models=[User, EnterpriseUser],
        resource_types=[ResourceType.from_resource(User[EnterpriseUser])],
    )
    composed = User[EnterpriseUser]

    assert provider.model_for("User") is composed
    assert provider.model_for_endpoint("/Users") is composed
    assert provider.model_for_endpoint("Users") is composed
    assert (
        provider.model_for(ResourceType.from_resource(User[EnterpriseUser])) is composed
    )


def test_a_name_lookup_takes_the_name_a_resource_type_declares():
    """:rfc:`RFC7643 §6 <7643#section-6>` has that name carried by ``meta.resourceType``.

    It is neither the name of the Python class serving the resource, nor the
    endpoint, which ``model_for_endpoint`` takes. They only ever coincide
    because a derived resource type is named after the last segment of the
    schema URI.
    """
    provider = ScimProvider(
        models=[User],
        resource_types=[resource_type("Staff", "/People", User.__schema__)],
    )

    assert provider.model_for("Staff") is User
    assert provider.model_for("User") is None
    assert provider.model_for("/People") is None
    assert provider.model_for_endpoint("/People") is User


def test_a_lookup_ignores_the_case_of_its_key():
    """:rfc:`RFC7643 §2.1 <7643#section-2.1>` makes attribute names case insensitive.

    Names, endpoints and schema URIs are matched the same way, so a peer
    spelling them differently is still understood.
    """
    provider = ScimProvider(models=[User])

    assert provider.model_for("user") is User
    assert provider.model_for(str(User.__schema__).upper()) is User
    assert provider.model_for_endpoint("/USERS") is User


def test_a_lookup_answers_none_when_nothing_matches():
    """An unknown key is not a protocol error: a server answers it with a 404."""
    provider = ScimProvider(models=[User])

    assert provider.model_for("Pet") is None
    assert provider.model_for("urn:example:2.0:Pet") is None
    assert provider.model_for_endpoint("/Pets") is None


def test_the_discovery_resources_are_known_without_being_registered():
    """:rfc:`RFC7644 §4 <7644#section-4>` defines three endpoints every service serves.

    They hold resources like the others, but no service publishes them among
    its resource types.
    """
    provider = ScimProvider(models=[User])

    assert provider.model_for("Schema") is Schema
    assert provider.model_for(str(ResourceType.__schema__)) is ResourceType
    assert (
        provider.model_for_endpoint("/ServiceProviderConfig") is ServiceProviderConfig
    )

    assert provider.models == (User,)
    assert [rt.name for rt in provider.resource_types] == ["User"]
    assert [schema.id for schema in provider.schemas] == [User.__schema__]


def test_two_resource_types_sharing_a_name_are_refused():
    """The name is a lookup key, and ``meta.resourceType`` could not tell the two apart."""
    with pytest.raises(ScimProviderError, match="User"):
        ScimProvider(
            models=[User, Group],
            resource_types=[
                resource_type("User", "/Users", User.__schema__),
                resource_type("User", "/Groups", Group.__schema__),
            ],
        )


def test_two_resource_types_sharing_an_endpoint_are_refused():
    """The endpoint is a lookup key, and a URL could not tell the two apart."""
    with pytest.raises(ScimProviderError, match="/Users"):
        ScimProvider(
            models=[User, Group],
            resource_types=[
                resource_type("User", "/Users", User.__schema__),
                resource_type("Group", "/Users", Group.__schema__),
            ],
        )


# What the service announces


def test_a_provider_carries_the_service_provider_config():
    """What a service announces travels with what it serves."""
    config = ServiceProviderConfig(documentation_uri="https://example.com")

    provider = ScimProvider(models=[User], config=config)

    assert provider.config is config


def test_a_provider_serving_nothing_yet_is_built():
    """A server builds its provider before it knows what it serves."""
    provider = ScimProvider()

    assert provider.models == ()
    assert provider.schemas == ()
    assert provider.resource_types == ()
    assert provider.config is None
    assert provider.model_for("User") is None


# Discovery


def test_a_provider_is_rebuilt_from_what_a_service_publishes():
    """What a service publishes is enough to describe it.

    A client reads ``/Schemas`` and ``/ResourceTypes``, and gets back the models
    the service would have registered.
    """
    served = ScimProvider(
        models=[User, EnterpriseUser, Group],
        resource_types=[
            ResourceType.from_resource(User[Annotated[EnterpriseUser, Required.true]]),
            ResourceType.from_resource(Group),
        ],
    )

    discovered = ScimProvider.from_discovery(served.schemas, served.resource_types)

    assert [schema.model_dump() for schema in discovered.schemas] == [
        schema.model_dump() for schema in served.schemas
    ]


def test_a_required_extension_survives_discovery():
    """``schemaExtensions.required`` is read back, where it used to be dropped."""
    served = ScimProvider(
        models=[User, EnterpriseUser],
        resource_types=[
            ResourceType.from_resource(User[Annotated[EnterpriseUser, Required.true]])
        ],
    )

    discovered = ScimProvider.from_discovery(served.schemas, served.resource_types)

    with pytest.raises(ValidationError, match="is required"):
        discovered.model_for("User").model_validate(
            {"schemas": [User.__schema__], "userName": "bjensen"},
            scim_ctx=Context.RESOURCE_CREATION_REQUEST,
        )


def test_an_optional_extension_survives_discovery():
    """An extension declared optional stays optional once the models are rebuilt."""
    served = ScimProvider(
        models=[User, EnterpriseUser],
        resource_types=[ResourceType.from_resource(User[EnterpriseUser])],
    )

    discovered = ScimProvider.from_discovery(served.schemas, served.resource_types)
    model = discovered.model_for("User")

    assert list(model.get_extension_models()) == [EnterpriseUser.__schema__]
    assert model.model_validate(
        {"schemas": [User.__schema__], "userName": "bjensen"},
        scim_ctx=Context.RESOURCE_CREATION_REQUEST,
    )


def test_discovering_a_resource_type_whose_base_schema_is_missing_is_refused():
    """A dangling reference names what is missing, rather than raising a bare KeyError."""
    served = ScimProvider(models=[User, Group])

    with pytest.raises(ScimProviderError, match=str(Group.__schema__)):
        ScimProvider.from_discovery([User.to_schema()], served.resource_types)


def test_a_discovered_provider_carries_the_config_it_is_given():
    """``/ServiceProviderConfig`` is part of what a client learns about its peer."""
    config = ServiceProviderConfig(documentation_uri="https://example.com")
    served = ScimProvider(models=[User])

    discovered = ScimProvider.from_discovery(
        served.schemas, served.resource_types, config
    )

    assert discovered.config is config


def test_a_discovered_provider_serves_the_endpoints_the_service_publishes():
    """The endpoint comes from the resource type, not from a naive derivation."""
    published = resource_type("User", "/People", User.__schema__)

    discovered = ScimProvider.from_discovery([User.to_schema()], [published])

    assert discovered.model_for_endpoint("/People") is discovered.model_for("User")
    assert discovered.model_for_endpoint("/Users") is None
