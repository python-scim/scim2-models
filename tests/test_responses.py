from pydantic_scim2 import Group
from pydantic_scim2 import ListResponse
from pydantic_scim2 import ResourceType
from pydantic_scim2 import ServiceProviderConfiguration
from pydantic_scim2 import User


def test_user_response(load_sample):
    resource_payload = load_sample("rfc7643-8.1-minimal_user_payload.json")
    payload = {
        "totalResults": 1,
        "itemsPerPage": 10,
        "startIndex": 1,
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "Resources": [resource_payload],
    }
    response = ListResponse[User].model_validate(payload)
    obj = response.resources[0]
    assert isinstance(obj, User)


def test_enterprise_user_response(load_sample):
    resource_payload = load_sample("rfc7643-8.3-enterprise_user.json")
    payload = {
        "totalResults": 1,
        "itemsPerPage": 10,
        "startIndex": 1,
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "Resources": [resource_payload],
    }
    response = ListResponse[User].model_validate(payload)
    obj = response.resources[0]
    assert isinstance(obj, User)

    # TODO: add checks for the EnterpriseUser attributes


def test_group_response(load_sample):
    resource_payload = load_sample("rfc7643-8.4-group.json")
    payload = {
        "totalResults": 1,
        "itemsPerPage": 10,
        "startIndex": 1,
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "Resources": [resource_payload],
    }
    response = ListResponse[Group].model_validate(payload)
    obj = response.resources[0]
    assert isinstance(obj, Group)


def test_service_provider_configuration_response(load_sample):
    resource_payload = load_sample("rfc7643-8.5-service_provider_configuration.json")
    payload = {
        "totalResults": 1,
        "itemsPerPage": 10,
        "startIndex": 1,
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "Resources": [resource_payload],
    }
    response = ListResponse[ServiceProviderConfiguration].model_validate(payload)
    obj = response.resources[0]
    assert isinstance(obj, ServiceProviderConfiguration)


def test_resource_type_response(load_sample):
    """https://datatracker.ietf.org/doc/html/rfc7644#section-4"""

    user_resource_type_payload = load_sample("rfc7643-8.6-user_resource_type.json")
    group_resource_type_payload = load_sample("rfc7643-8.6-group_resource_type.json")
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
