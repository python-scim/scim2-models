import json
import os

import pytest
from pydantic import ValidationError

from scim2_models import BulkRequest
from scim2_models import BulkResponse
from scim2_models import Context
from scim2_models import EnterpriseUser
from scim2_models import Error
from scim2_models import Group
from scim2_models import ListResponse
from scim2_models import PatchOp
from scim2_models import ResourceType
from scim2_models import Schema
from scim2_models import SearchRequest
from scim2_models import ServiceProviderConfig
from scim2_models import User
from scim2_models import get_model_by_payload
from scim2_models import get_model_by_schema


def _error_summary(exc: ValidationError) -> list[tuple[str, tuple]]:
    return [(error["type"], error["loc"]) for error in exc.errors()]


SAMPLE_MODELS = {
    "user": User,
    "enterprise_user": User[EnterpriseUser],
    "group": Group,
    "schema": Schema,
    "resource_type": ResourceType,
    "service_provider_configuration": ServiceProviderConfig,
    "list_response": ListResponse[User | Group | Schema | ResourceType],
    "patch_op": PatchOp[User],
    "bulk_request": BulkRequest,
    "bulk_response": BulkResponse,
    "search_request": SearchRequest,
    "error": Error,
}

SAMPLES = sorted(os.listdir("samples"))

UNDECIDABLE = pytest.mark.skip(
    reason="the resources bear no schemas and the model holds several types, "
    "so their type cannot be decided; tests/test_list_response.py covers "
    "the single-typed case"
)
UNDECIDABLE_SAMPLES = [
    "rfc7644-3.4.2-list_response-partial_attributes.json",
]
DECIDABLE_SAMPLES = [
    pytest.param(sample, marks=UNDECIDABLE) if sample in UNDECIDABLE_SAMPLES else sample
    for sample in SAMPLES
]

EXCHANGE_CONTEXTS = {
    "post_request": Context.RESOURCE_CREATION_REQUEST,
    "post_response": Context.RESOURCE_CREATION_RESPONSE,
    "put_request": Context.RESOURCE_REPLACEMENT_REQUEST,
    "put_response": Context.RESOURCE_REPLACEMENT_RESPONSE,
}

MESSAGE_CONTEXTS = {
    "patch_op": Context.RESOURCE_PATCH_REQUEST,
    "search_request": Context.SEARCH_REQUEST,
    "list_response": Context.RESOURCE_QUERY_RESPONSE,
    # An error answers any request.
    "error": Context.RESOURCE_QUERY_RESPONSE,
    # A bulk exchange is a POST on /Bulk.
    "bulk_request": Context.RESOURCE_CREATION_REQUEST,
    "bulk_response": Context.RESOURCE_CREATION_RESPONSE,
}

# RFC7643 §8.2 and §8.3 illustrate every attribute at once. They carry a
# password, which no response returns, next to an id and a meta, which no
# request sends, so no HTTP exchange carries them as they are.
SAMPLE_CONTEXTS = {
    "rfc7643-8.2-user-full.json": Context.DEFAULT,
    "rfc7643-8.3-enterprise_user.json": Context.DEFAULT,
}


def sample_model(sample: str) -> type:
    return SAMPLE_MODELS[sample.removesuffix(".json").split("-")[2]]


def sample_context(sample: str) -> Context:
    """Return the context of the HTTP exchange a sample is taken from.

    The file name carries the model and, for a resource, the exchange it
    illustrates; a bare resource is the representation a query returns.
    """
    if sample in SAMPLE_CONTEXTS:
        return SAMPLE_CONTEXTS[sample]

    stem = sample.removesuffix(".json")
    model_name = stem.split("-")[2]
    if model_name in MESSAGE_CONTEXTS:
        return MESSAGE_CONTEXTS[model_name]

    for exchange, context in EXCHANGE_CONTEXTS.items():
        if stem.endswith(exchange):
            return context

    return Context.RESOURCE_QUERY_RESPONSE


@pytest.mark.parametrize("sample", DECIDABLE_SAMPLES)
def test_parse_and_serialize_examples(sample, load_sample):
    """Examples are serialized back as they were read."""
    payload = load_sample(sample)
    obj = sample_model(sample).model_validate(payload)
    assert obj.model_dump(exclude_unset=True) == payload


@pytest.mark.parametrize("sample", DECIDABLE_SAMPLES)
def test_validate_examples_in_their_context(sample, load_sample):
    """Examples pass the validation of the HTTP exchange they illustrate."""
    sample_model(sample).model_validate(
        load_sample(sample), scim_ctx=sample_context(sample)
    )


@pytest.mark.parametrize("sample", SAMPLES)
def test_parse_json_and_decoded_examples(sample, load_sample):
    """JSON payloads and already decoded payloads are validated the same way."""
    model = sample_model(sample)
    payload = load_sample(sample)
    raw = json.dumps(payload)

    try:
        obj = model.model_validate(payload)
    except ValidationError as exc:
        with pytest.raises(ValidationError) as json_exc:
            model.model_validate_json(raw)
        assert _error_summary(json_exc.value) == _error_summary(exc)
        return

    json_obj = model.model_validate_json(raw)
    assert obj == json_obj
    assert obj.model_dump(exclude_unset=True) == json_obj.model_dump(exclude_unset=True)


def test_get_model_by_schema():
    resource_types = [Group, User[EnterpriseUser]]
    assert (
        get_model_by_schema(
            resource_types, "urn:ietf:params:scim:schemas:core:2.0:Group"
        )
        == Group
    )
    assert (
        get_model_by_schema(
            resource_types, "urn:ietf:params:scim:schemas:core:2.0:User"
        )
        == User[EnterpriseUser]
    )
    assert (
        get_model_by_schema(
            resource_types,
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
            with_extensions=False,
        )
        is None
    )
    assert (
        get_model_by_schema(
            resource_types,
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
        )
        == EnterpriseUser
    )


def test_get_message_by_schema_along_resources():
    """Messages such as ListResponse can be looked up next to resources carrying extensions."""
    resource_types = [ListResponse[User], User[EnterpriseUser]]
    assert (
        get_model_by_schema(
            resource_types, "urn:ietf:params:scim:api:messages:2.0:ListResponse"
        )
        == ListResponse[User]
    )
    assert (
        get_model_by_schema(
            resource_types,
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
        )
        == EnterpriseUser
    )


def test_get_model_by_payload():
    resource_types = [Group, User[EnterpriseUser]]
    payload = {"schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"]}
    assert get_model_by_payload(resource_types, payload) == Group

    payload = {"schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"]}
    assert get_model_by_payload(resource_types, payload) == User[EnterpriseUser]

    payload = {
        "schemas": ["urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"]
    }
    assert (
        get_model_by_payload(
            resource_types,
            payload,
            with_extensions=False,
        )
        is None
    )

    payload = {
        "schemas": ["urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"]
    }
    assert get_model_by_payload(resource_types, payload) == EnterpriseUser

    payload = {"schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"]}
    assert (
        get_model_by_payload([ListResponse[User]], payload, with_extensions=False)
        == ListResponse[User]
    )

    payload = {"foo": "bar"}
    assert get_model_by_payload(resource_types, payload) is None


def test_everything_is_optional():
    """Test that all attributes are optional on pre-defined models."""
    models = [
        User,
        EnterpriseUser,
        Group,
        Schema,
        ResourceType,
        ServiceProviderConfig,
        ListResponse[User],
        PatchOp[User],
        BulkRequest,
        BulkResponse,
        SearchRequest,
        Error,
    ]
    for model in models:
        model()


def test_json_schema_generation():
    """Test that all pre-defined models can generate a JSON Schema."""
    models = [
        User,
        User[EnterpriseUser],
        EnterpriseUser,
        Group,
        Schema,
        ResourceType,
        ServiceProviderConfig,
        ListResponse[User],
        PatchOp[User],
        BulkRequest,
        BulkResponse,
        SearchRequest,
        Error,
    ]
    for model in models:
        schema = model.model_json_schema()
        assert schema["type"] == "object"
