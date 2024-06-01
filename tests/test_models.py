import os

from pydantic_scim2 import BulkRequest
from pydantic_scim2 import BulkResponse
from pydantic_scim2 import EnterpriseUser
from pydantic_scim2 import Error
from pydantic_scim2 import Group
from pydantic_scim2 import ListResponse
from pydantic_scim2 import PatchOp
from pydantic_scim2 import Resource
from pydantic_scim2 import ResourceType
from pydantic_scim2 import Schema
from pydantic_scim2 import SearchRequest
from pydantic_scim2 import ServiceProviderConfiguration
from pydantic_scim2 import User


def test_parse_and_serialize_examples(load_sample):
    samples = list(os.walk("samples"))[0][2]
    models = {
        "user": User,
        "enterprise_user": User[EnterpriseUser],
        "group": Group,
        "schema": Schema,
        "resource_type": ResourceType,
        "service_provider_configuration": ServiceProviderConfiguration,
        "list_response": ListResponse.of(
            User[EnterpriseUser], Group, Schema, ResourceType
        ),
        "patch_op": PatchOp,
        "bulk_request": BulkRequest,
        "bulk_response": BulkResponse,
        "search_request": SearchRequest,
        "error": Error,
    }

    for sample in samples:
        model_name = sample.replace(".json", "").split("-")[2]
        model = models[model_name]

        # partial resources are not supported yet
        skipped = [
            "rfc7644-3.4.2-list_response-partial_attributes.json",
            "rfc7644-3.4.3-list_response-post_query.json",
            "rfc7644-3.9-user-partial_response.json",
        ]
        if sample in skipped:
            continue

        payload = load_sample(sample)
        obj = model.model_validate(payload)
        assert obj.model_dump(exclude_unset=True) == payload


def test_get_resource_by_schema():
    resource_types = [Group, User[EnterpriseUser]]
    assert (
        Resource.get_by_schema(
            resource_types, "urn:ietf:params:scim:schemas:core:2.0:Group"
        )
        == Group
    )
    assert (
        Resource.get_by_schema(
            resource_types, "urn:ietf:params:scim:schemas:core:2.0:User"
        )
        == User[EnterpriseUser]
    )
    assert (
        Resource.get_by_schema(
            resource_types,
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
            with_extensions=False,
        )
        is None
    )
    assert (
        Resource.get_by_schema(
            resource_types,
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
        )
        == EnterpriseUser
    )
