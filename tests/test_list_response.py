from typing import Union

import pytest
from pydantic import ValidationError

from pydantic_scim2 import Group
from pydantic_scim2 import ListResponse
from pydantic_scim2 import ResourceType
from pydantic_scim2 import ServiceProviderConfiguration
from pydantic_scim2 import User


def test_user(load_sample):
    resource_payload = load_sample("rfc7643-8.1-user-minimal.json")
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


def test_enterprise_user(load_sample):
    resource_payload = load_sample("rfc7643-8.3-user-enterprise_user.json")
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


def test_group(load_sample):
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


def test_service_provider_configuration(load_sample):
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


def test_resource_type(load_sample):
    """https://datatracker.ietf.org/doc/html/rfc7644#section-4"""

    user_resource_type_payload = load_sample("rfc7643-8.6-resource_type-user.json")
    group_resource_type_payload = load_sample("rfc7643-8.6-resource_type-group.json")
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


def test_mixed_types(load_sample):
    """Check that given the good type, a ListResponse can handle several
    resource types."""

    user_payload = load_sample("rfc7643-8.1-user-minimal.json")
    group_payload = load_sample("rfc7643-8.4-group.json")
    payload = {
        "totalResults": 2,
        "itemsPerPage": 10,
        "startIndex": 1,
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "Resources": [user_payload, group_payload],
    }
    response = ListResponse[Union[User, Group]].model_validate(payload)
    user, group = response.resources
    assert isinstance(user, User)
    assert isinstance(group, Group)
    assert (
        response.model_dump(
            exclude_none=True, exclude_unset=True, by_alias=True, mode="json"
        )
        == payload
    )


def test_mixed_types_type_missing(load_sample):
    """Check that if a type is missing for a resource, validation fails."""

    user_payload = load_sample("rfc7643-8.1-user-minimal.json")
    group_payload = load_sample("rfc7643-8.4-group.json")
    payload = {
        "totalResults": 2,
        "itemsPerPage": 10,
        "startIndex": 1,
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "Resources": [user_payload, group_payload],
    }
    with pytest.raises(ValidationError):
        ListResponse[Union[User]].model_validate(payload)
