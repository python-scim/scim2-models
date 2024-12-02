import os
from typing import Union

from scim2_models import BulkRequest
from scim2_models import BulkResponse
from scim2_models import EnterpriseUser
from scim2_models import Error
from scim2_models import Group
from scim2_models import ListResponse
from scim2_models import PatchOp
from scim2_models import Resource
from scim2_models import ResourceType
from scim2_models import Schema
from scim2_models import SearchRequest
from scim2_models import ServiceProviderConfig
from scim2_models import User


def test_parse_and_serialize_examples(load_sample):
    samples = list(os.walk("samples"))[0][2]
    models = {
        "user": User,
        "enterprise_user": User[EnterpriseUser],
        "group": Group,
        "schema": Schema,
        "resource_type": ResourceType,
        "service_provider_configuration": ServiceProviderConfig,
        "list_response": ListResponse[
            Union[User[EnterpriseUser], Group, Schema, ResourceType]
        ],
        "patch_op": PatchOp,
        "bulk_request": BulkRequest,
        "bulk_response": BulkResponse,
        "search_request": SearchRequest,
        "error": Error,
    }

    for sample in samples:
        model_name = sample.replace(".json", "").split("-")[2]
        model = models[model_name]

        skipped = [
            # resources without schemas are not yet supported
            # https://github.com/python-scim/scim2-models/issues/20
            "rfc7644-3.4.2-list_response-partial_attributes.json",
            "rfc7644-3.4.3-list_response-post_query.json",
            # BulkOperation.data PatchOperation.value should be of type resource
            # instead of Any, so serialization case would be respected.
            "rfc7644-3.7.1-bulk_request-circular_conflict.json",
            "rfc7644-3.7.2-bulk_request-enterprise_user.json",
            "rfc7644-3.7.2-bulk_request-temporary_identifier.json",
            "rfc7644-3.7.2-bulk_response-temporary_identifier.json",
            "rfc7644-3.7.3-bulk_request-multiple_operations.json",
            "rfc7644-3.7.3-bulk_response-error_invalid_syntax.json",
            "rfc7644-3.7.3-bulk_response-multiple_errors.json",
            "rfc7644-3.7.3-bulk_response-multiple_operations.json",
            "rfc7644-3.5.2.1-patch_op-add_emails.json",
            "rfc7644-3.5.2.1-patch_op-add_members.json",
            "rfc7644-3.5.2.2-patch_op-remove_all_members.json",
            "rfc7644-3.5.2.2-patch_op-remove_and_add_one_member.json",
            "rfc7644-3.5.2.2-patch_op-remove_multi_complex_value.json",
            "rfc7644-3.5.2.2-patch_op-remove_one_member.json",
            "rfc7644-3.5.2.3-patch_op-replace_all_email_values.json",
            "rfc7644-3.5.2.3-patch_op-replace_all_members.json",
            "rfc7644-3.5.2.3-patch_op-replace_street_address.json",
            "rfc7644-3.5.2.3-patch_op-replace_user_work_address.json",
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


def test_get_resource_by_payload():
    resource_types = [Group, User[EnterpriseUser]]
    payload = {"schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"]}
    assert Resource.get_by_payload(resource_types, payload) == Group

    payload = {"schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"]}
    assert Resource.get_by_payload(resource_types, payload) == User[EnterpriseUser]

    payload = {
        "schemas": ["urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"]
    }
    assert (
        Resource.get_by_payload(
            resource_types,
            payload,
            with_extensions=False,
        )
        is None
    )

    payload = {
        "schemas": ["urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"]
    }
    assert Resource.get_by_payload(resource_types, payload) == EnterpriseUser

    payload = {"schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"]}
    assert (
        Resource.get_by_payload([ListResponse[User]], payload, with_extensions=False)
        == ListResponse[User]
    )

    payload = {"foo": "bar"}
    assert Resource.get_by_payload(resource_types, payload) is None


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
        PatchOp,
        BulkRequest,
        BulkResponse,
        SearchRequest,
        Error,
    ]
    for model in models:
        model()
