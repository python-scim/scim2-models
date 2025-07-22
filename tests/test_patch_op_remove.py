import pytest
from pydantic import ValidationError

from scim2_models import Group
from scim2_models import GroupMember
from scim2_models import PatchOp
from scim2_models import PatchOperation
from scim2_models import User
from scim2_models.base import Context


def test_remove_operation_single_attribute():
    """Test removing a single-valued attribute."""
    user = User(nick_name="Babs")
    patch = PatchOp[User](
        operations=[PatchOperation(op=PatchOperation.Op.remove, path="nickName")]
    )
    result = patch.patch(user)
    assert result is True
    assert user.nick_name is None


def test_remove_operation_nonexistent_attribute():
    """Test removing an attribute that doesn't exist should not raise an error."""
    user = User()
    patch = PatchOp[User](
        operations=[PatchOperation(op=PatchOperation.Op.remove, path="nickName")]
    )
    result = patch.patch(user)
    assert result is False
    assert user.nick_name is None


def test_remove_operation_on_non_list_attribute():
    """Test remove specific value operation on non-list attribute."""
    user = User(nick_name="TestValue")

    # Try to remove specific value from a single-valued field
    patch = PatchOp[User](
        operations=[
            PatchOperation(
                op=PatchOperation.Op.remove, path="nickName", value="TestValue"
            )
        ]
    )

    # Should return False because nickName is not a list
    result = patch.patch(user)
    assert result is False
    assert user.nick_name == "TestValue"


def test_remove_operation_sub_attribute():
    """Test removing a sub-attribute of a complex attribute."""
    user = User(name={"familyName": "Jensen", "givenName": "Barbara"})
    patch = PatchOp[User](
        operations=[PatchOperation(op=PatchOperation.Op.remove, path="name.familyName")]
    )
    result = patch.patch(user)
    assert result is True
    assert user.name.family_name is None
    assert user.name.given_name == "Barbara"


def test_remove_operation_complex_attribute():
    """Test removing an entire complex attribute."""
    user = User(name={"familyName": "Jensen", "givenName": "Barbara"})
    patch = PatchOp[User](
        operations=[PatchOperation(op=PatchOperation.Op.remove, path="name")]
    )
    result = patch.patch(user)
    assert result is True
    assert user.name is None


def test_remove_operation_sub_attribute_parent_none():
    """Test removing a sub-attribute when parent is None."""
    user = User(name=None)
    patch = PatchOp[User](
        operations=[PatchOperation(op=PatchOperation.Op.remove, path="name.familyName")]
    )
    result = patch.patch(user)
    assert result is False
    assert user.name is None


def test_remove_operation_multiple_attribute_all():
    """Test removing all items from a multi-valued attribute."""
    group = Group(
        members=[
            {
                "display": "Babs Jensen",
                "$ref": "https://example.com/v2/Users/2819c223...413861904646",
                "value": "2819c223-7f76-453a-919d-413861904646",
            },
            {
                "display": "John Smith",
                "$ref": "https://example.com/v2/Users/1234567...413861904646",
                "value": "1234567-7f76-453a-919d-413861904646",
            },
        ]
    )
    patch = PatchOp[Group](
        operations=[PatchOperation(op=PatchOperation.Op.remove, path="members")]
    )
    result = patch.patch(group)
    assert result is True
    assert group.members is None or len(group.members) == 0


def test_remove_operation_multiple_attribute_with_value():
    """Test removing specific items from a multi-valued attribute by providing value."""
    user = User(
        emails=[
            {"value": "work@example.com", "type": "work"},
            {"value": "home@example.com", "type": "home"},
        ]
    )
    patch = PatchOp[User](
        operations=[
            PatchOperation(
                op=PatchOperation.Op.remove,
                path="emails",
                value={"value": "work@example.com", "type": "work"},
            )
        ]
    )
    result = patch.patch(user)
    assert result is True
    assert len(user.emails) == 1
    assert user.emails[0].value == "home@example.com"


def test_remove_operation_with_value_not_in_list():
    """Test remove operation with value not present in list should return False."""
    user = User(emails=[{"value": "test@example.com", "type": "work"}])
    patch = PatchOp[User](
        operations=[
            PatchOperation(
                op=PatchOperation.Op.remove,
                path="emails",
                value={"value": "other@example.com", "type": "work"},
            )
        ]
    )
    result = patch.patch(user)
    assert result is False
    assert len(user.emails) == 1
    assert user.emails[0].value == "test@example.com"


def test_values_match_basemodel_second_parameter():
    """Test _values_match when first value is dict and second is BaseModel (line 423->426)."""
    # Create a group with a member as dict
    group = Group()
    group.members = [{"value": "123", "display": "Test User"}]  # Dict, not BaseModel

    # Try to remove using a BaseModel object
    member_obj = GroupMember(value="123", display="Test User")  # BaseModel
    patch = PatchOp[Group](
        operations=[
            PatchOperation(
                op=PatchOperation.Op.remove,
                path="members",
                value=member_obj,  # BaseModel as second parameter
            )
        ]
    )

    # This should trigger _values_match where:
    # - value1 (dict from list) is not BaseModel -> skip lines 423-424
    # - value2 (member_obj) is BaseModel -> execute lines 426-427
    result = patch.patch(group)
    assert result is True
    assert group.members is None or len(group.members) == 0


def test_remove_operations_on_nonexistent_and_basemodel_values():
    """Test remove operations on non-existent values and BaseModel comparisons."""
    user = User(emails=[{"value": "existing@example.com", "type": "work"}])

    # Test removing non-existent value
    patch = PatchOp[User](
        operations=[
            PatchOperation(
                op=PatchOperation.Op.remove,
                path="emails",
                value={"value": "nonexistent@example.com", "type": "work"},
            )
        ]
    )

    result = patch.patch(user)
    assert result is False
    assert len(user.emails) == 1


def test_complex_object_creation_and_basemodel_matching():
    """Test complex object creation and BaseModel value matching."""
    # Test removing from existing multi-valued attribute
    group = Group(
        members=[
            GroupMember(value="123", display="Test User"),
            GroupMember(value="456", display="Another User"),
        ]
    )

    # Remove specific member by BaseModel value
    patch = PatchOp[Group](
        operations=[
            PatchOperation(
                op=PatchOperation.Op.remove,
                path="members",
                value=GroupMember(value="123", display="Test User"),
            )
        ]
    )

    result = patch.patch(group)
    assert result is True
    assert len(group.members) == 1
    assert group.members[0].value == "456"


def test_remove_operation_bypass_validation_no_path():
    """Test remove operation with no path raises error during validation per RFC7644."""
    # Path validation now happens during model validation
    with pytest.raises(ValidationError, match="path.*invalid"):
        PatchOp.model_validate(
            {
                "operations": [
                    {"op": "remove", "value": "test"},
                ],
            },
            context={"scim": Context.RESOURCE_PATCH_REQUEST},
        )


def test_defensive_path_check_in_remove():
    """Test defensive path check in _apply_remove method."""
    user = User(nick_name="Test")
    patch = PatchOp[User](
        operations=[PatchOperation(op=PatchOperation.Op.remove, path="nickName")]
    )

    # Force path to None to test defensive check
    patch.operations[0] = PatchOperation.model_construct(
        op=PatchOperation.Op.remove, path=None
    )

    with pytest.raises(ValueError, match="path.*invalid"):
        patch.patch(user)


def test_remove_value_empty_attr_path():
    """Test _remove_value_at_path with empty attr_path after URN resolution (line 291)."""
    user = User()

    # URN with trailing colon results in empty attr_path after parsing
    patch = PatchOp[User](
        operations=[
            PatchOperation(
                op=PatchOperation.Op.remove,
                path="urn:ietf:params:scim:schemas:core:2.0:User:",
            )
        ]
    )

    with pytest.raises(ValueError, match="path"):
        patch.patch(user)


def test_remove_specific_value_empty_attr_path():
    """Test _remove_specific_value with empty attr_path after URN resolution (line 316)."""
    user = User()

    # URN with trailing colon results in empty attr_path after parsing
    patch = PatchOp[User](
        operations=[
            PatchOperation(
                op=PatchOperation.Op.remove,
                path="urn:ietf:params:scim:schemas:core:2.0:User:",
                value={"some": "value"},
            )
        ]
    )

    with pytest.raises(ValueError, match="path"):
        patch.patch(user)
