from pydantic import AnyUrl

from pydantic_scim2 import ResourceType


def test_user_resource_type(load_sample):
    payload = load_sample("rfc7643-8.6-resource_type-user.json")
    obj = ResourceType.model_validate(payload)

    assert obj.schemas == ["urn:ietf:params:scim:schemas:core:2.0:ResourceType"]
    assert obj.id == "User"
    assert obj.name == "User"
    assert obj.endpoint == "/Users"
    assert obj.description == "User Account"
    assert obj.schema_ == AnyUrl("urn:ietf:params:scim:schemas:core:2.0:User")
    assert obj.schema_extensions[0].schema_ == AnyUrl(
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"
    )
    assert obj.schema_extensions[0].required is True
    assert obj.meta.location == "https://example.com/v2/ResourceTypes/User"
    assert obj.meta.resource_type == "ResourceType"

    assert obj.model_dump(exclude_unset=True) == payload


def test_group_resource_type(load_sample):
    payload = load_sample("rfc7643-8.6-resource_type-group.json")
    obj = ResourceType.model_validate(payload)
    assert obj.schemas == ["urn:ietf:params:scim:schemas:core:2.0:ResourceType"]
    assert obj.id == "Group"
    assert obj.name == "Group"
    assert obj.endpoint == "/Groups"
    assert obj.description == "Group"
    assert obj.schema_ == AnyUrl("urn:ietf:params:scim:schemas:core:2.0:Group")
    assert obj.meta.location == "https://example.com/v2/ResourceTypes/Group"
    assert obj.meta.resource_type == "ResourceType"

    assert obj.model_dump(exclude_unset=True) == payload
