from typing import Union

import pytest
from pydantic import ValidationError

from scim2_models import Group
from scim2_models import GroupMember
from scim2_models import PatchOp
from scim2_models import PatchOperation
from scim2_models import User
from scim2_models.rfc7643.enterprise_user import EnterpriseUser

# ==============================================================================
# VALIDATION AND RFC COMPLIANCE
# ==============================================================================


def test_validate_patchop_case_insensitivity():
    """Validate that a patch operation's Op declaration is case-insensitive.

    Note: While :rfc:`RFC7644 §3.4.2.2 <7644#section-3.4.2.2>` specifies case insensitivity
    for attribute names and operators in filters, this implementation extends this principle
    to PATCH operation names for Microsoft Entra compatibility.
    """
    assert PatchOp.model_validate(
        {
            "operations": [
                {"op": "Replace", "path": "userName", "value": "Rivard"},
                {"op": "ADD", "path": "userName", "value": "Rivard"},
                {"op": "ReMove", "path": "userName", "value": "Rivard"},
            ],
        },
    ) == PatchOp(
        operations=[
            PatchOperation(
                op=PatchOperation.Op.replace_, path="userName", value="Rivard"
            ),
            PatchOperation(op=PatchOperation.Op.add, path="userName", value="Rivard"),
            PatchOperation(
                op=PatchOperation.Op.remove, path="userName", value="Rivard"
            ),
        ]
    )
    with pytest.raises(
        ValidationError,
        match="1 validation error for PatchOp",
    ):
        PatchOp.model_validate(
            {
                "operations": [{"op": 42, "path": "userName", "value": "Rivard"}],
            },
        )


def test_path_required_for_remove_operations():
    """Test that path is required for remove operations.

    :rfc:`RFC7644 §3.5.2.2 <7644#section-3.5.2.2>`: "If 'path' is unspecified,
    the operation fails with HTTP status code 400 and a 'scimType' error code of 'noTarget'."
    """
    from scim2_models.base import Context

    PatchOp.model_validate(
        {
            "operations": [
                {"op": "replace", "value": "foobar"},
            ],
        },
        context={"scim": Context.RESOURCE_PATCH_REQUEST},
    )
    PatchOp.model_validate(
        {
            "operations": [
                {"op": "add", "value": "foobar"},
            ],
        },
        context={"scim": Context.RESOURCE_PATCH_REQUEST},
    )

    # Validation now happens during model validation
    with pytest.raises(ValidationError, match="required for remove"):
        PatchOp.model_validate(
            {
                "operations": [
                    {"op": "remove", "value": "foobar"},
                ],
            },
            context={"scim": Context.RESOURCE_PATCH_REQUEST},
        )


def test_value_required_for_add_operations():
    """Test that value is required for add operations.

    :rfc:`RFC7644 §3.5.2.1 <7644#section-3.5.2.1>`: "The operation MUST contain a 'value'
    member whose content specifies the value to be added."
    """
    from scim2_models.base import Context

    PatchOp.model_validate(
        {
            "operations": [
                {"op": "replace", "path": "foobar"},
            ],
        },
        context={"scim": Context.RESOURCE_PATCH_REQUEST},
    )
    with pytest.raises(ValidationError):
        PatchOp.model_validate(
            {
                "operations": [
                    {"op": "add", "path": "foobar"},
                ],
            },
            context={"scim": Context.RESOURCE_PATCH_REQUEST},
        )

    PatchOp.model_validate(
        {
            "operations": [
                {"op": "remove", "path": "foobar"},
            ],
        },
        context={"scim": Context.RESOURCE_PATCH_REQUEST},
    )


def test_patch_operation_validation_contexts():
    """Test RFC7644 validation behavior in different contexts.

    Validates that operations are only validated in PATCH request contexts,
    following :rfc:`RFC7644 §3.5.2 <7644#section-3.5.2>` validation requirements.
    """
    from scim2_models.base import Context

    with pytest.raises(ValidationError, match="path"):
        PatchOperation.model_validate(
            {"op": "add", "path": "   ", "value": "test"},
            context={"scim": Context.RESOURCE_PATCH_REQUEST},
        )

    # Validation for missing path in remove operations now happens during model validation
    with pytest.raises(ValidationError, match="required for remove"):
        PatchOperation.model_validate(
            {"op": "remove"},
            context={"scim": Context.RESOURCE_PATCH_REQUEST},
        )

    with pytest.raises(ValidationError, match="required for add"):
        PatchOperation.model_validate(
            {"op": "add", "path": "test"},
            context={"scim": Context.RESOURCE_PATCH_REQUEST},
        )

    operation1 = PatchOperation.model_validate(
        {"op": "add", "path": "   ", "value": "test"}
    )
    assert operation1.path == "   "

    operation2 = PatchOperation.model_validate({"op": "remove"})
    assert operation2.path is None

    operation3 = PatchOperation.model_validate({"op": "add", "path": "test"})
    assert operation3.value is None


# ==============================================================================
# ADD OPERATIONS
# ==============================================================================


def test_add_operation_single_attribute():
    """Test adding a value to a single-valued attribute."""
    user = User()
    patch = PatchOp(
        operations=[
            PatchOperation(op=PatchOperation.Op.add, path="nickName", value="Babs")
        ]
    )
    result = patch.patch(user)
    assert result is True
    assert user.nick_name == "Babs"


def test_add_operation_single_attribute_already_present():
    """Test adding a value to a single-valued attribute that already has a value."""
    user = User(nick_name="foobar")
    patch = PatchOp(
        operations=[
            PatchOperation(op=PatchOperation.Op.add, path="nickName", value="Babs")
        ]
    )
    result = patch.patch(user)
    assert result is True
    assert user.nick_name == "Babs"


def test_add_operation_sub_attribute():
    """Test adding a value to a sub-attribute of a complex attribute."""
    user = User()
    patch = PatchOp(
        operations=[
            PatchOperation(
                op=PatchOperation.Op.add, path="name.familyName", value="Jensen"
            )
        ]
    )
    result = patch.patch(user)
    assert result is True
    assert user.name.family_name == "Jensen"


def test_add_operation_complex_attribute():
    """Test adding a complex attribute with sub-attributes."""
    user = User()
    patch = PatchOp(
        operations=[
            PatchOperation(
                op=PatchOperation.Op.add, path="name", value={"familyName": "Jensen"}
            )
        ]
    )
    result = patch.patch(user)
    assert result is True
    assert user.name.family_name == "Jensen"


def test_add_operation_multiple_attribute():
    """Test adding values to a multi-valued attribute."""
    group = Group()
    patch = PatchOp(
        operations=[
            PatchOperation(
                op=PatchOperation.Op.add,
                path="members",
                value=[
                    {
                        "display": "Babs Jensen",
                        "$ref": "https://example.com/v2/Users/2819c223...413861904646",
                        "value": "2819c223-7f76-453a-919d-413861904646",
                    }
                ],
            )
        ]
    )
    result = patch.patch(group)
    assert result is True
    assert group.members[0].display == "Babs Jensen"


def test_add_operation_multiple_attribute_already_present():
    """Test adding a value that already exists in a multi-valued attribute."""
    member = GroupMember(
        display="Babs Jensen",
        ref="https://example.com/v2/Users/2819c223...413861904646",
        value="2819c223-7f76-453a-919d-413861904646",
    )
    group = Group(members=[member])
    assert len(group.members) == 1

    patch = PatchOp(
        operations=[
            PatchOperation(
                op=PatchOperation.Op.add,
                path="members",
                value=[member.model_dump()],
            )
        ]
    )
    result = patch.patch(group)
    assert result is False
    assert len(group.members) == 1


def test_add_operation_no_path():
    """Test adding multiple attributes when no path is specified."""
    user = User()
    patch = PatchOp(
        operations=[
            PatchOperation(
                op=PatchOperation.Op.add,
                value={
                    "emails": [{"value": "babs@jensen.org", "type": "home"}],
                    "nickName": "Babs",
                },
            )
        ]
    )
    result = patch.patch(user)
    assert result is True
    assert user.nick_name == "Babs"
    assert user.emails[0].value == "babs@jensen.org"


def test_add_operation_same_value():
    """Test adding the same value to a single-valued attribute."""
    user = User(nick_name="Test")
    patch = PatchOp(
        operations=[
            PatchOperation(op=PatchOperation.Op.add, path="nickName", value="Test")
        ]
    )
    result = patch.patch(user)
    assert result is False
    assert user.nick_name == "Test"


def test_add_operation_no_path_same_attributes():
    """Test add operation with no path but same attribute values should return False."""
    user = User(nick_name="Test")
    patch = PatchOp(
        operations=[
            PatchOperation(
                op=PatchOperation.Op.add,
                value={"nickName": "Test"},
            )
        ]
    )
    result = patch.patch(user)
    assert result is False
    assert user.nick_name == "Test"


def test_add_operation_with_non_dict_value_no_path():
    """Test add operation with no path and non-dict value should return False."""
    user = User()
    patch = PatchOp(
        operations=[PatchOperation(op=PatchOperation.Op.add, value="invalid_value")]
    )
    result = patch.patch(user)
    assert result is False


def test_add_operation_single_value_in_multivalued_field():
    """Test adding a single value (not a list) to a multi-valued field.

    :rfc:`RFC7644 §3.5.2.1 <7644#section-3.5.2.1>`: "If the target location is a
    multi-valued attribute, a new value is added to the attribute."
    """
    group = Group(members=[])
    patch = PatchOp(
        operations=[
            PatchOperation(
                op=PatchOperation.Op.add,
                path="members",
                value={
                    "display": "Single Member",
                    "$ref": "https://example.com/v2/Users/single",
                    "value": "single-id",
                },
            )
        ]
    )
    result = patch.patch(group)
    assert result is True
    assert len(group.members) == 1
    assert group.members[0].display == "Single Member"


def test_add_operation_no_path_with_invalid_attribute():
    """Test add operation with no path but invalid attribute name."""
    user = User(nick_name="Test")
    patch = PatchOp(
        operations=[
            PatchOperation(
                op=PatchOperation.Op.add,
                value={"invalidAttributeName": "value", "nickName": "Updated"},
            )
        ]
    )
    result = patch.patch(user)
    assert result is True
    assert user.nick_name == "Updated"


def test_add_multiple_values_empty_new_values():
    """Test _add_multiple_values when all values already exist."""
    member1 = GroupMember(
        display="Member 1",
        ref="https://example.com/v2/Users/1",
        value="1",
    )
    member2 = GroupMember(
        display="Member 2",
        ref="https://example.com/v2/Users/2",
        value="2",
    )

    group = Group(members=[member1, member2])
    patch = PatchOp(
        operations=[
            PatchOperation(
                op=PatchOperation.Op.add,
                path="members",
                value=[
                    member1.model_dump(),
                    member2.model_dump(),
                ],
            )
        ]
    )

    result = patch.patch(group)
    assert result is False
    assert len(group.members) == 2


def test_add_single_value_existing():
    """Test _add_single_value when value already exists (line 266)."""
    group = Group(members=[GroupMember(value="123", display="Test User")])
    patch = PatchOp(
        operations=[
            PatchOperation(
                op=PatchOperation.Op.add,
                path="members",
                value={"value": "123", "display": "Test User"},  # Same value
            )
        ]
    )

    result = patch.patch(group)
    assert result is False  # Should return False because value already exists
    assert len(group.members) == 1


# ==============================================================================
# REMOVE OPERATIONS
# ==============================================================================


def test_remove_operation_single_attribute():
    """Test removing a single-valued attribute."""
    user = User(nick_name="Babs")
    patch = PatchOp(
        operations=[PatchOperation(op=PatchOperation.Op.remove, path="nickName")]
    )
    result = patch.patch(user)
    assert result is True
    assert user.nick_name is None


def test_remove_operation_sub_attribute():
    """Test removing a sub-attribute of a complex attribute."""
    user = User(name={"familyName": "Jensen", "givenName": "Barbara"})
    patch = PatchOp(
        operations=[PatchOperation(op=PatchOperation.Op.remove, path="name.familyName")]
    )
    result = patch.patch(user)
    assert result is True
    assert user.name.family_name is None
    assert user.name.given_name == "Barbara"


def test_remove_operation_complex_attribute():
    """Test removing an entire complex attribute."""
    user = User(name={"familyName": "Jensen", "givenName": "Barbara"})
    patch = PatchOp(
        operations=[PatchOperation(op=PatchOperation.Op.remove, path="name")]
    )
    result = patch.patch(user)
    assert result is True
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
    patch = PatchOp(
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
    patch = PatchOp(
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


def test_remove_operation_nonexistent_attribute():
    """Test removing an attribute that doesn't exist should not raise an error."""
    user = User()
    patch = PatchOp(
        operations=[PatchOperation(op=PatchOperation.Op.remove, path="nickName")]
    )
    result = patch.patch(user)
    assert result is False
    assert user.nick_name is None


def test_remove_operation_sub_attribute_parent_none():
    """Test removing a sub-attribute when parent is None."""
    user = User(name=None)
    patch = PatchOp(
        operations=[PatchOperation(op=PatchOperation.Op.remove, path="name.familyName")]
    )
    result = patch.patch(user)
    assert result is False
    assert user.name is None


def test_remove_operation_with_value_not_in_list():
    """Test remove operation with value not present in list should return False."""
    user = User(emails=[{"value": "test@example.com", "type": "work"}])
    patch = PatchOp(
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


def test_remove_operation_on_non_list_attribute():
    """Test remove specific value operation on non-list attribute."""
    user = User(nick_name="TestValue")

    # Try to remove specific value from a single-valued field
    patch = PatchOp(
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


def test_remove_operation_bypass_validation_no_path():
    """Test remove operation with no path raises error during validation per RFC7644."""
    from scim2_models.base import Context

    # Path validation now happens during model validation
    with pytest.raises(ValidationError, match="required for remove"):
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
    patch = PatchOp(
        operations=[PatchOperation(op=PatchOperation.Op.remove, path="nickName")]
    )

    # Force path to None to test defensive check
    patch.operations[0] = PatchOperation.model_construct(
        op=PatchOperation.Op.remove, path=None
    )

    with pytest.raises(ValueError, match="required for remove"):
        patch.patch(user)


def test_remove_value_empty_attr_path():
    """Test _remove_value_at_path with empty attr_path after URN resolution (line 291)."""
    user = User()

    # URN with trailing colon results in empty attr_path after parsing
    patch = PatchOp(
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
    patch = PatchOp(
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


# ==============================================================================
# REPLACE OPERATIONS
# ==============================================================================


def test_replace_operation_single_attribute():
    """Test replacing a single-valued attribute.

    :rfc:`RFC7644 §3.5.2.3 <7644#section-3.5.2.3>`: "The 'replace' operation replaces
    the value at the target location specified by the 'path'."
    """
    user = User(nick_name="OldNick")
    patch = PatchOp(
        operations=[
            PatchOperation(
                op=PatchOperation.Op.replace_, path="nickName", value="NewNick"
            )
        ]
    )
    result = patch.patch(user)
    assert result is True
    assert user.nick_name == "NewNick"


def test_replace_operation_single_attribute_none_to_value():
    """Test replacing a None single-valued attribute with a value."""
    user = User(nick_name=None)
    patch = PatchOp(
        operations=[
            PatchOperation(
                op=PatchOperation.Op.replace_, path="nickName", value="NewNick"
            )
        ]
    )
    result = patch.patch(user)
    assert result is True
    assert user.nick_name == "NewNick"


def test_replace_operation_sub_attribute():
    """Test replacing a sub-attribute of a complex attribute."""
    user = User(name={"familyName": "OldName", "givenName": "Barbara"})
    patch = PatchOp(
        operations=[
            PatchOperation(
                op=PatchOperation.Op.replace_, path="name.familyName", value="NewName"
            )
        ]
    )
    result = patch.patch(user)
    assert result is True
    assert user.name.family_name == "NewName"
    assert user.name.given_name == "Barbara"


def test_replace_operation_complex_attribute():
    """Test replacing an entire complex attribute."""
    user = User(name={"familyName": "OldName", "givenName": "Barbara"})
    patch = PatchOp(
        operations=[
            PatchOperation(
                op=PatchOperation.Op.replace_,
                path="name",
                value={"familyName": "NewName", "givenName": "John"},
            )
        ]
    )
    result = patch.patch(user)
    assert result is True
    assert user.name.family_name == "NewName"
    assert user.name.given_name == "John"


def test_replace_operation_multiple_attribute_all():
    """Test replacing all items in a multi-valued attribute."""
    user = User(
        emails=[
            {"value": "old1@example.com", "type": "work"},
            {"value": "old2@example.com", "type": "home"},
        ]
    )
    patch = PatchOp(
        operations=[
            PatchOperation(
                op=PatchOperation.Op.replace_,
                path="emails",
                value=[{"value": "new@example.com", "type": "work"}],
            )
        ]
    )
    result = patch.patch(user)
    assert result is True
    assert len(user.emails) == 1
    assert user.emails[0].value == "new@example.com"
    assert user.emails[0].type == "work"


def test_replace_operation_no_path():
    """Test replacing multiple attributes when no path is specified.

    :rfc:`RFC7644 §3.5.2.3 <7644#section-3.5.2.3>`: "If the 'path' parameter is omitted,
    the target is assumed to be the resource itself, and the 'value' parameter
    SHALL contain the replacement attributes."
    """
    user = User(nick_name="OldNick", display_name="Old Display")
    patch = PatchOp(
        operations=[
            PatchOperation(
                op=PatchOperation.Op.replace_,
                value={
                    "nickName": "NewNick",
                    "displayName": "New Display",
                },
            )
        ]
    )
    result = patch.patch(user)
    assert result is True
    assert user.nick_name == "NewNick"
    assert user.display_name == "New Display"


def test_replace_operation_nonexistent_attribute():
    """Test replacing a nonexistent attribute should be treated as add."""
    user = User()
    patch = PatchOp(
        operations=[
            PatchOperation(
                op=PatchOperation.Op.replace_, path="nickName", value="NewNick"
            )
        ]
    )
    result = patch.patch(user)
    assert result is True
    assert user.nick_name == "NewNick"


def test_replace_operation_sub_attribute_parent_none():
    """Test replacing a sub-attribute when parent is None (should create parent)."""
    user = User(name=None)
    patch = PatchOp(
        operations=[
            PatchOperation(
                op=PatchOperation.Op.replace_, path="name.familyName", value="NewName"
            )
        ]
    )
    result = patch.patch(user)
    assert result is True
    assert user.name is not None
    assert user.name.family_name == "NewName"


def test_replace_operation_same_value():
    """Test replace operation with same value should return False."""
    user = User(nick_name="Test")
    patch = PatchOp(
        operations=[
            PatchOperation(op=PatchOperation.Op.replace_, path="nickName", value="Test")
        ]
    )
    result = patch.patch(user)
    assert result is False
    assert user.nick_name == "Test"


def test_replace_operation_no_path_same_attributes():
    """Test replace operation with no path but same attribute values should return False."""
    user = User(nick_name="Test", display_name="Display")
    patch = PatchOp(
        operations=[
            PatchOperation(
                op=PatchOperation.Op.replace_,
                value={"nickName": "Test", "displayName": "Display"},
            )
        ]
    )
    result = patch.patch(user)
    assert result is False
    assert user.nick_name == "Test"
    assert user.display_name == "Display"


def test_replace_operation_with_non_dict_value_no_path():
    """Test replace operation with no path and non-dict value should return False."""
    user = User(nick_name="Test")
    patch = PatchOp(
        operations=[
            PatchOperation(op=PatchOperation.Op.replace_, value="invalid_value")
        ]
    )
    result = patch.patch(user)
    assert result is False
    assert user.nick_name == "Test"


# ==============================================================================
# ERROR HANDLING
# ==============================================================================


def test_patch_with_none_operations():
    """Test PatchOp with None operations should return False."""
    user = User(nick_name="Test")
    patch = PatchOp(operations=None)
    result = patch.patch(user)
    assert result is False
    assert user.nick_name == "Test"


def test_complex_operation_with_invalid_sub_path():
    """Test operation with invalid sub-path should raise ValueError."""
    user = User(name={"familyName": "Test"})
    patch = PatchOp(
        operations=[
            PatchOperation(
                op=PatchOperation.Op.add, path="name.invalidSubField", value="test"
            )
        ]
    )
    with pytest.raises(ValueError, match="no match"):
        patch.patch(user)


def test_multiple_operations_with_mixed_results():
    """Test where some operations succeed and some don't."""
    user = User(nick_name="Original")
    patch = PatchOp(
        operations=[
            PatchOperation(op=PatchOperation.Op.replace_, path="nickName", value="New"),
            PatchOperation(op=PatchOperation.Op.add, path="invalidField", value="test"),
            PatchOperation(
                op=PatchOperation.Op.add, path="displayName", value="Display"
            ),
        ]
    )
    with pytest.raises(ValueError, match="no match"):
        patch.patch(user)
    assert user.nick_name == "New"


def test_patch_operation_no_target_errors():
    """Test noTarget errors for various invalid paths.

    :rfc:`RFC7644 §3.5.2.2 <7644#section-3.5.2.2>`: "If the target location path
    specifies an attribute that does not exist, the service provider SHALL
    return an HTTP status code 400 with a 'scimType' error code of 'noTarget'."
    """
    user = User()

    patch1 = PatchOp(
        operations=[
            PatchOperation(
                op=PatchOperation.Op.add, path="nonExistentField", value="test"
            )
        ]
    )
    with pytest.raises(ValueError, match="no match"):
        patch1.patch(user)

    patch2 = PatchOp(
        operations=[
            PatchOperation(
                op=PatchOperation.Op.add, path="nonExistent.subField", value="test"
            )
        ]
    )
    with pytest.raises(ValueError, match="no match"):
        patch2.patch(user)

    patch3 = PatchOp(
        operations=[
            PatchOperation(op=PatchOperation.Op.remove, path="nonExistentField")
        ]
    )
    with pytest.raises(ValueError, match="no match"):
        patch3.patch(user)

    patch4 = PatchOp(
        operations=[
            PatchOperation(
                op=PatchOperation.Op.remove,
                path="nonExistentField",
                value={"some": "value"},
            )
        ]
    )
    with pytest.raises(ValueError, match="no match"):
        patch4.patch(user)


def test_patch_operation_mutability_errors():
    """Test mutability errors for readOnly/immutable fields.

    :rfc:`RFC7644 §3.5.2 <7644#section-3.5.2>`: "Each operation against an attribute
    MUST be compatible with the attribute's mutability and schema... a client MUST NOT
    modify an attribute that has mutability 'readOnly' or 'immutable'."
    """
    user = User(id="123")

    patch1 = PatchOp(
        operations=[PatchOperation(op=PatchOperation.Op.add, path="id", value="456")]
    )
    with pytest.raises(ValueError, match="mutability"):
        patch1.patch(user)

    patch2 = PatchOp(
        operations=[
            PatchOperation(op=PatchOperation.Op.replace_, path="id", value="456")
        ]
    )
    with pytest.raises(ValueError, match="mutability"):
        patch2.patch(user)

    patch3 = PatchOp(
        operations=[
            PatchOperation(
                op=PatchOperation.Op.add, path="groups", value=[{"value": "group1"}]
            )
        ]
    )
    with pytest.raises(ValueError, match="mutability"):
        patch3.patch(user)


def test_invalid_operation_type_error():
    """Test that invalid operation types raise appropriate errors per RFC7644.

    :rfc:`RFC7644 §3.5.2 <7644#section-3.5.2>`: Each PATCH operation object MUST have
    exactly one "op" member, whose value indicates the operation to perform and
    MAY be one of "add", "remove", or "replace".
    """
    user = User(nick_name="Test")
    patch = PatchOp(
        operations=[
            PatchOperation(op=PatchOperation.Op.add, path="nickName", value="temp")
        ]
    )
    # Bypass Pydantic validation to simulate invalid operation type
    object.__setattr__(patch.operations[0], "op", "invalid_operation")

    with pytest.raises(ValueError, match="required value was missing|not compatible"):
        patch.patch(user)


def test_remove_operation_empty_path_after_urn_resolution():
    """Test remove operation with empty path after URN resolution raises error per RFC7644.

    :rfc:`RFC7644 §3.5.2.3 <7644#section-3.5.2.3>`: "If the 'path' is provided and
    contains an invalid path, the operation SHALL fail with scimType 'invalidPath'."
    """
    user = User()

    # Create a patch with an invalid URN that resolves to empty path
    patch = PatchOp(
        operations=[
            PatchOperation(op=PatchOperation.Op.remove, path="urn:invalid:schema:")
        ]
    )

    with pytest.raises(ValueError, match="path"):
        patch.patch(user)


def test_remove_specific_value_empty_path_after_urn_resolution():
    """Test remove specific value with empty path after URN resolution raises error per RFC7644."""
    user = User()

    # Create a patch with an invalid URN that resolves to empty path
    patch = PatchOp(
        operations=[
            PatchOperation(
                op=PatchOperation.Op.remove,
                path="urn:invalid:schema:",
                value={"some": "value"},
            )
        ]
    )

    with pytest.raises(ValueError, match="path"):
        patch.patch(user)


def test_parent_object_creation_failure():
    """Test when parent object creation fails due to invalid field type."""
    from unittest.mock import patch as mock_patch

    user = User()
    patch_op = PatchOp(
        operations=[
            PatchOperation(
                op=PatchOperation.Op.add,
                path="invalidComplexField.subField",
                value="test",
            )
        ]
    )

    # Mock get_field_root_type to return None to simulate creation failure
    with mock_patch.object(type(user), "get_field_root_type", return_value=None):
        with pytest.raises(ValueError, match="no match"):
            patch_op.patch(user)


def test_mutability_validation_exception_handling():
    """Test that non-ValueError exceptions in mutability validation are handled gracefully."""
    from unittest.mock import patch as mock_patch

    user = User(user_name="test")
    patch_op = PatchOp(
        operations=[
            PatchOperation(op=PatchOperation.Op.add, path="userName", value="newname")
        ]
    )

    # Mock _validate_path_mutability to raise a non-ValueError exception
    with mock_patch.object(
        patch_op,
        "_validate_path_mutability",
        side_effect=RuntimeError("Unexpected error"),
    ):
        # This should not raise an exception - the RuntimeError should be caught and ignored
        patch_op.validate_mutability(user)


def test_set_complex_attribute_creation_failure():
    """Test _set_complex_attribute when parent object creation fails (line 225)."""
    from unittest.mock import patch as mock_patch

    user = User()
    patch_op = PatchOp(
        operations=[
            PatchOperation(
                op=PatchOperation.Op.add, path="name.familyName", value="TestName"
            )
        ]
    )

    # Mock _create_parent_object to return None to simulate creation failure
    with mock_patch.object(patch_op, "_create_parent_object", return_value=None):
        result = patch_op.patch(user)
        assert result is False


# ==============================================================================
# SCIM EXTENSIONS
# ==============================================================================


def test_patch_operation_extension_simple_attribute():
    """Test PATCH operations on simple extension attributes using schema URN paths."""
    user = User[EnterpriseUser].model_validate(
        {
            "userName": "john.doe",
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
                "employeeNumber": "12345",
                "costCenter": "Engineering",
            },
        }
    )

    patch1 = PatchOp(
        operations=[
            PatchOperation(
                op=PatchOperation.Op.replace_,
                path="urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:employeeNumber",
                value="54321",
            )
        ]
    )
    result = patch1.patch(user)
    assert result is True
    assert user[EnterpriseUser].employee_number == "54321"

    patch2 = PatchOp(
        operations=[
            PatchOperation(
                op=PatchOperation.Op.add,
                path="urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:organization",
                value="ACME Corp",
            )
        ]
    )
    result = patch2.patch(user)
    assert result is True
    assert user[EnterpriseUser].organization == "ACME Corp"

    patch3 = PatchOp(
        operations=[
            PatchOperation(
                op=PatchOperation.Op.remove,
                path="urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:costCenter",
            )
        ]
    )
    result = patch3.patch(user)
    assert result is True
    assert user[EnterpriseUser].cost_center is None


def test_patch_operation_extension_complex_attribute():
    """Test PATCH operations on complex extension attributes using schema URN paths."""
    user = User[EnterpriseUser].model_validate(
        {
            "userName": "jane.doe",
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
                "employeeNumber": "67890",
                "manager": {"value": "manager-123", "displayName": "John Smith"},
            },
        }
    )

    patch1 = PatchOp(
        operations=[
            PatchOperation(
                op=PatchOperation.Op.replace_,
                path="urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:manager.value",
                value="new-manager-456",
            )
        ]
    )
    result = patch1.patch(user)
    assert result is True
    assert user[EnterpriseUser].manager.value == "new-manager-456"
    assert user[EnterpriseUser].manager.display_name == "John Smith"

    patch2 = PatchOp(
        operations=[
            PatchOperation(
                op=PatchOperation.Op.replace_,
                path="urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:manager",
                value={
                    "value": "super-manager-789",
                    "displayName": "Alice Johnson",
                    "$ref": "https://example.com/Users/super-manager-789",
                },
            )
        ]
    )
    result = patch2.patch(user)
    assert result is True
    assert user[EnterpriseUser].manager.value == "super-manager-789"
    assert user[EnterpriseUser].manager.display_name == "Alice Johnson"

    patch3 = PatchOp(
        operations=[
            PatchOperation(
                op=PatchOperation.Op.remove,
                path="urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:manager",
            )
        ]
    )
    result = patch3.patch(user)
    assert result is True
    assert user[EnterpriseUser].manager is None


def test_patch_operation_extension_read_only_attribute():
    """Test mutability error on readOnly extension attributes.

    :rfc:`RFC7644 §3.5.2 <7644#section-3.5.2>`: Mutability constraints apply to all
    attributes including those in extensions. ReadOnly attributes cannot be modified.
    """
    user = User[EnterpriseUser].model_validate(
        {
            "userName": "test.user",
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
                "manager": {"value": "manager-123", "displayName": "John Smith"}
            },
        }
    )

    patch = PatchOp(
        operations=[
            PatchOperation(
                op=PatchOperation.Op.replace_,
                path="urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:manager.displayName",
                value="New Name",
            )
        ]
    )
    with pytest.raises(ValueError, match="mutability"):
        patch.patch(user)


def test_patch_operation_extension_no_target_error():
    """Test noTarget error for invalid extension paths.

    :rfc:`RFC7644 §3.5.2.2 <7644#section-3.5.2.2>`: noTarget errors apply to
    extension attributes when the specified path does not exist.
    """
    user = User[EnterpriseUser].model_validate({"userName": "test.user"})

    patch1 = PatchOp(
        operations=[
            PatchOperation(
                op=PatchOperation.Op.add,
                path="urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:invalidAttribute",
                value="test",
            )
        ]
    )
    with pytest.raises(ValueError, match="no match"):
        patch1.patch(user)

    patch2 = PatchOp(
        operations=[
            PatchOperation(
                op=PatchOperation.Op.add,
                path="urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:manager.invalidField",
                value="test",
            )
        ]
    )
    with pytest.raises(ValueError, match="no match"):
        patch2.patch(user)


def test_extension_path_without_attribute():
    """Test extension path resolution when attr_path is empty."""
    from scim2_models.urn import resolve_urn_to_target

    user = User[EnterpriseUser].model_validate(
        {
            "userName": "test.user",
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
                "employeeNumber": "12345"
            },
        }
    )

    # Test the specific case where extension schema is treated as attribute path
    target, attr_path = resolve_urn_to_target(
        user,
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
        "",  # Empty attr_path
    )

    assert target == user
    assert attr_path == "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"


# ==============================================================================
# TECHNICAL/EDGE CASES
# ==============================================================================


def test_urn_parsing_errors():
    """Test URN parsing errors for malformed URNs."""
    user = User()

    # Test with malformed URN that causes extract_schema_and_attribute_base to fail
    patch = PatchOp(
        operations=[
            PatchOperation(
                op=PatchOperation.Op.add, path="urn:malformed:incomplete", value="test"
            )
        ]
    )

    with pytest.raises(ValueError, match="no match"):
        patch.patch(user)


def test_values_match_with_basemodel():
    """Test _values_match method with BaseModel objects."""
    from scim2_models import GroupMember

    patch_op = PatchOp(
        operations=[PatchOperation(op=PatchOperation.Op.add, path="test", value="test")]
    )

    # Test with two BaseModel objects that should match
    member1 = GroupMember(value="123", display="Test User")
    member2 = GroupMember(value="123", display="Test User")

    assert patch_op._values_match(member1, member2) is True

    # Test with BaseModel and dict
    member_dict = {"value": "123", "display": "Test User"}
    assert patch_op._values_match(member1, member_dict) is True

    # Test with different values
    member3 = GroupMember(value="456", display="Other User")
    assert patch_op._values_match(member1, member3) is False


def test_generic_patchop_with_union():
    """Test that generic PatchOp works with Union types."""
    # Test the metaclass code path with Union types
    patch_data = {
        "operations": [{"op": "add", "path": "displayName", "value": "Test User"}]
    }

    # This should trigger the metaclass code
    patch = PatchOp[Union[User, Group]].model_validate(patch_data)
    assert patch.operations[0].value == "Test User"


def test_generic_patchop_with_single_type():
    """Test that generic PatchOp works with single types."""
    patch_data = {
        "operations": [{"op": "add", "path": "userName", "value": "test.user"}]
    }

    # This should not trigger the union-specific metaclass code
    patch = PatchOp[User].model_validate(patch_data)
    assert patch.operations[0].value == "test.user"


def test_values_match_first_basemodel_only():
    """Test _values_match when only first value is BaseModel (line 399->402)."""
    patch_op = PatchOp(
        operations=[PatchOperation(op=PatchOperation.Op.add, path="test", value="test")]
    )

    member = GroupMember(value="123", display="Test User")
    dict_value = {"value": "123", "display": "Test User"}

    # Test when first parameter is BaseModel but second is not
    assert patch_op._values_match(member, dict_value) is True


def test_malformed_urn_extract_error():
    """Test URN extraction that raises IndexError (lines 364-365)."""
    from unittest.mock import patch as mock_patch

    user = User()
    patch = PatchOp(
        operations=[
            PatchOperation(op=PatchOperation.Op.add, path="urn:malformed", value="test")
        ]
    )

    # Mock extract_schema_and_attribute_base to raise IndexError
    with mock_patch(
        "scim2_models.urn.extract_schema_and_attribute_base",
        side_effect=IndexError("Index error"),
    ):
        with pytest.raises(ValueError, match="no match"):
            patch.patch(user)


def test_values_match_second_basemodel_only():
    """Test _values_match when only second value is BaseModel (covers remaining branch)."""
    patch_op = PatchOp(
        operations=[PatchOperation(op=PatchOperation.Op.add, path="test", value="test")]
    )

    dict_value = {"value": "123", "display": "Test User"}
    member = GroupMember(value="123", display="Test User")

    # Test when second parameter is BaseModel but first is not - this should hit the 399->402 branch
    assert patch_op._values_match(dict_value, member) is True


def test_create_parent_object_with_non_class_type():
    """Test _create_parent_object when field type is not a class."""
    from unittest.mock import patch as mock_patch

    user = User()
    patch_op = PatchOp(
        operations=[PatchOperation(op=PatchOperation.Op.add, path="test", value="test")]
    )

    # Mock get_field_root_type to return a non-class type (like str)
    # This should make _create_parent_object return None without trying to set the attribute
    with mock_patch.object(type(user), "get_field_root_type", return_value=str):
        # Also mock isclass to return False for str to trigger the None return
        with mock_patch("scim2_models.rfc7644.patch_op.isclass", return_value=False):
            result = patch_op._create_parent_object(user, "name")
            assert result is None
