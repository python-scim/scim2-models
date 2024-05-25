from pydantic_scim2 import Group
from pydantic_scim2 import ListResponse
from pydantic_scim2 import ResourceType
from pydantic_scim2 import ServiceProviderConfiguration
from pydantic_scim2 import User


def test_user_response(minimal_user_payload):
    payload = {
        "totalResults": 1,
        "itemsPerPage": 10,
        "startIndex": 1,
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "Resources": [minimal_user_payload],
    }
    response = ListResponse[User].model_validate(payload)
    obj = response.resources[0]
    assert isinstance(obj, User)


def test_enterprise_user_response(enterprise_user_payload):
    payload = {
        "totalResults": 1,
        "itemsPerPage": 10,
        "startIndex": 1,
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "Resources": [enterprise_user_payload],
    }
    response = ListResponse[User].model_validate(payload)
    obj = response.resources[0]
    assert isinstance(obj, User)

    # TODO: add checks for the EnterpriseUser attributes


def test_group_response(group_payload):
    payload = {
        "totalResults": 1,
        "itemsPerPage": 10,
        "startIndex": 1,
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "Resources": [group_payload],
    }
    response = ListResponse[Group].model_validate(payload)
    obj = response.resources[0]
    assert isinstance(obj, Group)


def test_service_provider_configuration_response(
    service_provider_configuration_payload,
):
    payload = {
        "totalResults": 1,
        "itemsPerPage": 10,
        "startIndex": 1,
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "Resources": [service_provider_configuration_payload],
    }
    response = ListResponse[ServiceProviderConfiguration].model_validate(payload)
    obj = response.resources[0]
    assert isinstance(obj, ServiceProviderConfiguration)


def test_resource_type_response(
    user_resource_type_payload, group_resource_type_payload
):
    """https://datatracker.ietf.org/doc/html/rfc7644#section-4"""

    payload = {
        "totalResults": 2,
        "itemsPerPage": 10,
        "startIndex": 1,
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "Resources": [user_resource_type_payload, group_resource_type_payload],
    }
    response = ListResponse[ResourceType].model_validate(payload)
    obj = response.resources[0]
    assert isinstance(obj, ResourceType)
