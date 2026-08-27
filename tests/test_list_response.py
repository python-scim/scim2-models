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
from scim2_models.path import URN


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
    resource_payload = load_sample("rfc7643-8.3-enterprise_user.json")
    payload = {
        "totalResults": 1,
        "itemsPerPage": 10,
        "startIndex": 1,
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "Resources": [resource_payload],
    }
    response = ListResponse[User[EnterpriseUser]].model_validate(payload)
    obj = response.resources[0]
    assert isinstance(obj, User)


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
    response = ListResponse[ServiceProviderConfig].model_validate(payload)
    obj = response.resources[0]
    assert isinstance(obj, ServiceProviderConfig)


def test_resource_type(load_sample):
    """Test returning a list of resource types.

    https://datatracker.ietf.org/doc/html/rfc7644#section-4
    """
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
    """Check that given the good type, a ListResponse can handle several resource types."""
    user_payload = load_sample("rfc7643-8.1-user-minimal.json")
    group_payload = load_sample("rfc7643-8.4-group.json")
    payload = {
        "totalResults": 2,
        "itemsPerPage": 10,
        "startIndex": 1,
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "Resources": [user_payload, group_payload],
    }
    response = ListResponse[User | Group].model_validate(payload)
    user, group = response.resources
    assert isinstance(user, User)
    assert isinstance(group, Group)
    assert response.model_dump() == payload


class Foobar(Resource):
    __schema__ = URN("urn:example:foobar")


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

    ListResponse[User | Group].model_validate(payload)

    with pytest.raises(ValidationError):
        ListResponse[User | Foobar].model_validate(payload)

    with pytest.raises(ValidationError):
        ListResponse[User].model_validate(payload)


def test_missing_resource_payload(load_sample):
    """Check that validation fails if resources schemas are missing."""
    payload = {
        "totalResults": 2,
        "itemsPerPage": 10,
        "startIndex": 1,
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "Resources": [{}],
    }

    with pytest.raises(ValidationError):
        ListResponse[User | Group].model_validate(payload, strict=True)

    # TODO: This should raise a ValidationError
    ListResponse[User].model_validate(payload, strict=True)


def test_missing_resource_schema(load_sample):
    """Check that validation fails if resources schemas are missing."""
    payload = {
        "totalResults": 2,
        "itemsPerPage": 10,
        "startIndex": 1,
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "Resources": [{"id": "foobar"}],
    }

    with pytest.raises(ValidationError):
        ListResponse[User | Group].model_validate(payload, strict=True)

    # TODO: This should raise a ValidationError
    ListResponse[User].model_validate(payload, strict=True)


def test_resources_without_schemas_are_read(load_sample):
    """Resources omitting their 'schemas' attribute are read against the ListResponse parameter.

    :rfc:`RFC7644 §3.4.3 <7644#section-3.4.3>` displays partial responses
    where resources bear no 'schemas' attribute. A single-typed ListResponse
    knows their type, so they are read as-is and the attribute is rebuilt on
    serialization.
    """
    payload = load_sample("rfc7644-3.4.3-list_response-post_query.json")

    response = ListResponse[User].model_validate(
        payload, scim_ctx=Context.RESOURCE_QUERY_RESPONSE
    )

    assert [resource.id for resource in response.resources] == [
        "2819c223-7f76-413861904646",
        "c8596b90-7539-4f20968d1908",
    ]
    assert all(resource.schemas == [] for resource in response.resources)
    assert all(
        resource["schemas"] == ["urn:ietf:params:scim:schemas:core:2.0:User"]
        for resource in response.model_dump()["Resources"]
    )


def test_resources_without_schemas_need_a_single_type(load_sample):
    """A ListResponse holding several types cannot guess the type of an unlabelled resource.

    The :rfc:`RFC7644 §3.4.3 <7644#section-3.4.3>` example is undecidable:
    its second resource only bears 'id' and 'displayName', which both
    :class:`~scim2_models.User` and :class:`~scim2_models.Group` define.
    """
    payload = load_sample("rfc7644-3.4.3-list_response-post_query.json")

    with pytest.raises(ValidationError) as exc_info:
        ListResponse[User | Group].model_validate(
            payload, scim_ctx=Context.RESOURCE_QUERY_RESPONSE
        )

    assert [error["type"] for error in exc_info.value.errors()] == [
        "union_tag_not_found",
        "union_tag_not_found",
    ]


def test_zero_results():
    """:rfc:`RFC7644 §3.4.2 <7644#section-3.4.2>` indicates that ListResponse.Resources is required when ListResponse.totalResults is non- zero.

    This MAY be a subset of the full set of resources if pagination
    (Section 3.4.2.4) is requested. REQUIRED if "totalResults" is non-
    zero.
    """
    payload = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "totalResults": 1,
        "Resources": [
            {
                "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
                "userName": "foobar",
                "id": "foobar",
            }
        ],
    }
    ListResponse[User].model_validate(payload, scim_ctx=Context.RESOURCE_QUERY_RESPONSE)

    payload = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "totalResults": 1,
        "Resources": [],
    }
    ListResponse[User].model_validate(payload, scim_ctx=Context.RESOURCE_QUERY_RESPONSE)

    payload = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "totalResults": 1,
    }
    with pytest.raises(ValidationError):
        ListResponse[User].model_validate(
            payload, scim_ctx=Context.RESOURCE_QUERY_RESPONSE
        )


def test_list_response_schema_ordering():
    """Test that the "schemas" attribute order does not impact behavior.

    https://datatracker.ietf.org/doc/html/rfc7643#section-3
    """
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
    ListResponse[User[EnterpriseUser] | Group].model_validate(payload)


def test_attributes_inclusion():
    """ListResponse.model_dump propagates the 'attributes' parameter to embedded resources."""
    response = ListResponse[User](
        total_results=1,
        resources=[
            User(id="user-id", user_name="user-name", display_name="display-name")
        ],
    )
    payload = response.model_dump(
        scim_ctx=Context.RESOURCE_QUERY_RESPONSE, attributes=["userName"]
    )
    assert payload == {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "totalResults": 1,
        "Resources": [
            {
                "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
                "id": "user-id",
                "userName": "user-name",
            }
        ],
    }


def test_excluded_attributes():
    """ListResponse.model_dump propagates the 'excluded_attributes' parameter to embedded resources."""
    response = ListResponse[User](
        total_results=1,
        resources=[
            User(id="user-id", user_name="user-name", display_name="display-name")
        ],
    )
    payload = response.model_dump(
        scim_ctx=Context.RESOURCE_QUERY_RESPONSE, excluded_attributes=["displayName"]
    )
    assert "displayName" not in payload["Resources"][0]
    assert payload["Resources"][0]["userName"] == "user-name"


def test_attributes_inclusion_with_full_urn():
    """ListResponse propagates full URN attributes to embedded resources."""
    response = ListResponse[User](
        total_results=1,
        resources=[
            User(id="user-id", user_name="user-name", display_name="display-name")
        ],
    )
    payload = response.model_dump(
        scim_ctx=Context.RESOURCE_QUERY_RESPONSE,
        attributes=["urn:ietf:params:scim:schemas:core:2.0:User:userName"],
    )
    resource = payload["Resources"][0]
    assert resource["userName"] == "user-name"
    assert "displayName" not in resource


def test_excluded_attributes_with_full_urn():
    """ListResponse propagates full URN excluded attributes to embedded resources."""
    response = ListResponse[User](
        total_results=1,
        resources=[
            User(id="user-id", user_name="user-name", display_name="display-name")
        ],
    )
    payload = response.model_dump(
        scim_ctx=Context.RESOURCE_QUERY_RESPONSE,
        excluded_attributes=["urn:ietf:params:scim:schemas:core:2.0:User:displayName"],
    )
    resource = payload["Resources"][0]
    assert "displayName" not in resource
    assert resource["userName"] == "user-name"


def test_attributes_with_union_type(load_sample):
    """ListResponse with a Union type resolves attributes against the matching resource type."""
    user_payload = load_sample("rfc7643-8.1-user-minimal.json")
    group_payload = load_sample("rfc7643-8.4-group.json")
    payload = {
        "totalResults": 2,
        "itemsPerPage": 10,
        "startIndex": 1,
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "Resources": [user_payload, group_payload],
    }
    response = ListResponse[User | Group].model_validate(payload)
    dumped = response.model_dump(
        scim_ctx=Context.RESOURCE_QUERY_RESPONSE, attributes=["userName"]
    )
    user_resource = dumped["Resources"][0]
    assert "userName" in user_resource
    assert "displayName" not in user_resource


def test_attributes_with_empty_resources():
    """ListResponse serialization handles empty resources when attributes are set."""
    response = ListResponse[User](total_results=0, resources=[])
    payload = response.model_dump(
        scim_ctx=Context.RESOURCE_QUERY_RESPONSE, attributes=["userName"]
    )
    assert payload["Resources"] == []


def test_model_dump_without_scim_context():
    """ListResponse.model_dump works without a SCIM context."""
    response = ListResponse[User](
        total_results=1,
        resources=[User(id="user-id", user_name="user-name")],
    )
    payload = response.model_dump(scim_ctx=None)
    assert payload["resources"][0]["user_name"] == "user-name"


def test_total_results_required():
    """ListResponse.total_results is required."""
    payload = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "Resources": [
            {
                "schemas": [
                    "urn:ietf:params:scim:schemas:core:2.0:User",
                ],
                "userName": "bjensen@example.com",
                "id": "foobar",
            }
        ],
    }

    with pytest.raises(
        ValidationError,
        match="Field 'total_results' is required but value is missing or null",
    ):
        ListResponse[User].model_validate(
            payload, scim_ctx=Context.RESOURCE_QUERY_RESPONSE
        )
