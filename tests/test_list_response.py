from typing import List
from typing import Union

import pytest
from pydantic import ValidationError

from scim2_models import Context
from scim2_models import EnterpriseUser
from scim2_models import Group
from scim2_models import ListResponse
from scim2_models import Resource
from scim2_models import ResourceType
from scim2_models import ServiceProviderConfig
from scim2_models import User


def test_user(load_sample):
    resource_payload = load_sample("rfc7643-8.1-user-minimal.json")
    payload = {
        "totalResults": 1,
        "itemsPerPage": 10,
        "startIndex": 1,
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "Resources": [resource_payload],
    }
    response = ListResponse.of(User).model_validate(payload)
    obj = response.resources[0]
    assert isinstance(obj, User)


def test_enterprise_user(load_sample):
    resource_payload = load_sample("rfc7643-8.3-enterprise_user.json")
    payload = {
        "totalResults": 1,
        "itemsPerPage": 10,
        "startIndex": 1,
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "Resources": [resource_payload],
    }
    response = ListResponse.of(User[EnterpriseUser]).model_validate(payload)
    obj = response.resources[0]
    assert isinstance(obj, User[EnterpriseUser])


def test_group(load_sample):
    resource_payload = load_sample("rfc7643-8.4-group.json")
    payload = {
        "totalResults": 1,
        "itemsPerPage": 10,
        "startIndex": 1,
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "Resources": [resource_payload],
    }
    response = ListResponse.of(Group).model_validate(payload)
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
    response = ListResponse.of(ServiceProviderConfig).model_validate(payload)
    obj = response.resources[0]
    assert isinstance(obj, ServiceProviderConfig)


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
    response = ListResponse.of(ResourceType).model_validate(payload)
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
    response = ListResponse.of(Union[User, Group]).model_validate(payload)
    user, group = response.resources
    assert isinstance(user, User)
    assert isinstance(group, Group)
    assert response.model_dump() == payload


class Foobar(Resource):
    schemas: List[str] = ["foobarschema"]


def test_mixed_types_type_missing(load_sample):
    """Check that ValidationError are raised when unknown schemas are met."""

    user_payload = load_sample("rfc7643-8.1-user-minimal.json")
    group_payload = load_sample("rfc7643-8.4-group.json")
    payload = {
        "totalResults": 2,
        "itemsPerPage": 10,
        "startIndex": 1,
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "Resources": [user_payload, group_payload],
    }

    ListResponse.of(User, Group).model_validate(payload)

    with pytest.raises(ValidationError):
        ListResponse.of(User, Foobar).model_validate(payload)

    with pytest.raises(ValidationError):
        ListResponse.of(User).model_validate(payload)


def test_missing_resource_schema(load_sample):
    """Check that validation fails if resources schemas are missing."""

    payload = {
        "totalResults": 2,
        "itemsPerPage": 10,
        "startIndex": 1,
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "Resources": [{}],
    }

    with pytest.raises(ValidationError):
        ListResponse.of(User, Group).model_validate(payload, strict=True)

    # TODO: This should raise a ValidationError
    ListResponse.of(User).model_validate(payload, strict=True)


def test_zero_results():
    """:rfc:`RFC7644 §3.4.2 <7644#section-3.4.2>` indicates that
    ListResponse.Resources is required when ListResponse.totalResults is non-
    zero.

    This MAY be a subset of the full set of resources if pagination
    (Section 3.4.2.4) is requested. REQUIRED if "totalResults" is non-
    zero.
    """

    payload = {
        "totalResults": 1,
        "Resources": [
            {
                "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
                "userName": "foobar",
                "id": "foobar",
            }
        ],
    }
    ListResponse.of(User).model_validate(
        payload, scim_ctx=Context.RESOURCE_QUERY_RESPONSE
    )

    payload = {"totalResults": 1, "Resources": []}
    with pytest.raises(ValidationError):
        ListResponse.of(User).model_validate(
            payload, scim_ctx=Context.RESOURCE_QUERY_RESPONSE
        )

    payload = {"totalResults": 1}
    with pytest.raises(ValidationError):
        ListResponse.of(User).model_validate(
            payload, scim_ctx=Context.RESOURCE_QUERY_RESPONSE
        )


def test_list_response_schema_ordering():
    """Test that the "schemas" attribute order does not impact behavior
    https://datatracker.ietf.org/doc/html/rfc7643#section-3"""

    payload = {
        "totalResults": 1,
        "Resources": [
            {
                "schemas": [
                    "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
                    "urn:ietf:params:scim:schemas:core:2.0:User",
                ],
                "userName": "bjensen@example.com",
            }
        ],
    }
    ListResponse.of(User[EnterpriseUser], Group).model_validate(payload)
