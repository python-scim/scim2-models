from typing import Annotated

import pytest
from pydantic import ValidationError

from scim2_models import URN
from scim2_models import PatchOp
from scim2_models import PatchOperation
from scim2_models import User
from scim2_models.annotations import Mutability
from scim2_models.resources.resource import Resource


def test_replace_operation_single_attribute():
    """Test replacing a single-valued attribute.

    :rfc:`RFC7644 §3.5.2.3 <7644#section-3.5.2.3>`: "The 'replace' operation replaces
    the value at the target location specified by the 'path'."
    """
    user = User(nick_name="OldNick")
    patch = PatchOp[User](
        operations=[
            PatchOperation[User](
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
    patch = PatchOp[User](
        operations=[
            PatchOperation[User](
                op=PatchOperation.Op.replace_, path="nickName", value="NewNick"
            )
        ]
    )
    result = patch.patch(user)
    assert result is True
    assert user.nick_name == "NewNick"


def test_replace_operation_nonexistent_attribute():
    """Test replacing a nonexistent attribute should be treated as add."""
    user = User()
    patch = PatchOp[User](
        operations=[
            PatchOperation[User](
                op=PatchOperation.Op.replace_, path="nickName", value="NewNick"
            )
        ]
    )
    result = patch.patch(user)
    assert result is True
    assert user.nick_name == "NewNick"


def test_replace_operation_same_value():
    """Test replace operation with same value should return False."""
    user = User(nick_name="Test")
    patch = PatchOp[User](
        operations=[
            PatchOperation[User](
                op=PatchOperation.Op.replace_, path="nickName", value="Test"
            )
        ]
    )
    result = patch.patch(user)
    assert result is False
    assert user.nick_name == "Test"


def test_replace_operation_sub_attribute():
    """Test replacing a sub-attribute of a complex attribute."""
    user = User(name={"familyName": "OldName", "givenName": "Barbara"})
    patch = PatchOp[User](
        operations=[
            PatchOperation[User](
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
    patch = PatchOp[User](
        operations=[
            PatchOperation[User](
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


def test_replace_operation_sub_attribute_parent_none():
    """Test replacing a sub-attribute when parent is None (should create parent)."""
    user = User(name=None)
    patch = PatchOp[User](
        operations=[
            PatchOperation[User](
                op=PatchOperation.Op.replace_, path="name.familyName", value="NewName"
            )
        ]
    )
    result = patch.patch(user)
    assert result is True
    assert user.name is not None
    assert user.name.family_name == "NewName"


def test_replace_operation_multiple_attribute_all():
    """Test replacing all items in a multi-valued attribute."""
    user = User(
        emails=[
            {"value": "old1@example.com", "type": "work"},
            {"value": "old2@example.com", "type": "home"},
        ]
    )
    patch = PatchOp[User](
        operations=[
            PatchOperation[User](
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
    patch = PatchOp[User](
        operations=[
            PatchOperation[User](
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


def test_replace_operation_no_path_same_attributes():
    """Test replace operation with no path but same attribute values should return False."""
    user = User(nick_name="Test", display_name="Display")
    patch = PatchOp[User](
        operations=[
            PatchOperation[User](
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
    patch = PatchOp[User](
        operations=[
            PatchOperation[User](op=PatchOperation.Op.replace_, value="invalid_value")
        ]
    )
    result = patch.patch(user)
    assert result is False
    assert user.nick_name == "Test"


def test_immutable_field():
    """Test that replace operations on immutable fields raise validation errors."""

    class Dummy(Resource):
        __schema__ = URN("urn:test:TestResource")

        immutable: Annotated[str, Mutability.immutable]

    with pytest.raises(ValidationError, match="mutability"):
        PatchOp[Dummy](
            operations=[
                PatchOperation[Dummy](
                    op=PatchOperation.Op.replace_, path="immutable", value="new_value"
                )
            ]
        )


def test_primary_auto_exclusion_on_add():
    """Test that adding an element with primary=true auto-excludes other primary values.

    :rfc:`RFC 7644 §3.5.2 <7644#section-3.5.2>`: "a PATCH operation that sets a
    value's 'primary' sub-attribute to 'true' SHALL cause the server to
    automatically set 'primary' to 'false' for any other values in the array."
    """
    from scim2_models import Email

    user = User(
        emails=[
            Email(value="existing@example.com", primary=True),
        ]
    )

    patch = PatchOp[User](
        operations=[
            PatchOperation[User](
                op=PatchOperation.Op.add,
                path="emails",
                value={"value": "new@example.com", "primary": True},
            )
        ]
    )

    result = patch.patch(user)

    assert result is True
    assert user.emails[0].primary is False
    assert user.emails[1].primary is True


def test_primary_auto_exclusion_on_replace_list():
    """Test that replacing a list with a new primary auto-excludes the old one."""
    from scim2_models import Email

    user = User(
        emails=[
            Email(value="old@example.com", primary=True),
        ]
    )

    patch = PatchOp[User](
        operations=[
            PatchOperation[User](
                op=PatchOperation.Op.replace_,
                path="emails",
                value=[
                    {"value": "old@example.com", "primary": False},
                    {"value": "new@example.com", "primary": True},
                ],
            )
        ]
    )

    result = patch.patch(user)

    assert result is True
    assert user.emails[0].primary is False
    assert user.emails[1].primary is True


def test_primary_no_change_when_single_primary():
    """Test that no change occurs when there's only one primary after patch."""
    from scim2_models import Email

    user = User(
        emails=[
            Email(value="a@example.com", primary=True),
            Email(value="b@example.com", primary=False),
        ]
    )

    patch = PatchOp[User](
        operations=[
            PatchOperation[User](
                op=PatchOperation.Op.add,
                path="emails",
                value={"value": "c@example.com", "primary": False},
            )
        ]
    )

    result = patch.patch(user)

    assert result is True
    assert user.emails[0].primary is True
    assert user.emails[1].primary is False
    assert user.emails[2].primary is False


def test_primary_auto_exclusion_rejects_multiple_new_primaries():
    """Test that setting multiple new primaries in one operation raises an error."""
    from scim2_models import Email

    user = User(
        emails=[
            Email(value="a@example.com", primary=False),
            Email(value="b@example.com", primary=False),
        ]
    )

    patch = PatchOp[User](
        operations=[
            PatchOperation[User](
                op=PatchOperation.Op.replace_,
                path="emails",
                value=[
                    {"value": "a@example.com", "primary": True},
                    {"value": "b@example.com", "primary": True},
                ],
            )
        ]
    )

    with pytest.raises(Exception, match="Multiple values marked as primary"):
        patch.patch(user)


def test_primary_auto_exclusion_rejects_preexisting_multiple_primaries():
    """Test that patching data with preexisting multiple primaries raises an error."""
    from scim2_models import Email

    user = User(
        emails=[
            Email(value="a@example.com", primary=True),
            Email(value="b@example.com", primary=True),
        ]
    )

    patch = PatchOp[User](
        operations=[
            PatchOperation[User](
                op=PatchOperation.Op.add,
                path="emails",
                value={"value": "c@example.com", "primary": False},
            )
        ]
    )

    with pytest.raises(Exception, match="Multiple primary values already exist"):
        patch.patch(user)
