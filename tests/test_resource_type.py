from scim2_models import EnterpriseUser
from scim2_models import Reference
from scim2_models import ResourceType
from scim2_models import User


def test_user_resource_type(load_sample):
    payload = load_sample("rfc7643-8.6-resource_type-user.json")
    obj = ResourceType.model_validate(payload)

    assert obj.schemas == ["urn:ietf:params:scim:schemas:core:2.0:ResourceType"]
    assert obj.id == "User"
    assert obj.name == "User"
    assert obj.endpoint == "/Users"
    assert obj.description == "User Account"
    assert obj.schema_ == Reference("urn:ietf:params:scim:schemas:core:2.0:User")
    assert obj.schema_extensions[0].schema_ == Reference(
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
    assert obj.schema_ == Reference("urn:ietf:params:scim:schemas:core:2.0:Group")
    assert obj.meta.location == "https://example.com/v2/ResourceTypes/Group"
    assert obj.meta.resource_type == "ResourceType"

    assert obj.model_dump(exclude_unset=True) == payload


def test_from_simple_resource():
    user_rt = ResourceType.from_resource(User)
    assert user_rt.id == "User"
    assert user_rt.name == "User"
    assert user_rt.description == "User"
    assert user_rt.endpoint == "/Users"
    assert user_rt.schema_ == "urn:ietf:params:scim:schemas:core:2.0:User"
    assert not user_rt.schema_extensions


def test_from_resource_with_extensions():
    enterprise_user_rt = ResourceType.from_resource(User[EnterpriseUser])
    assert enterprise_user_rt.id == "User"
    assert enterprise_user_rt.name == "User"
    assert enterprise_user_rt.description == "User"
    assert enterprise_user_rt.endpoint == "/Users"
    assert enterprise_user_rt.schema_ == "urn:ietf:params:scim:schemas:core:2.0:User"
    assert (
        enterprise_user_rt.schema_extensions[0].schema_
        == "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"
    )
    assert not enterprise_user_rt.schema_extensions[0].required
