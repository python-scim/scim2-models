import pytest
from pydantic import ValidationError

from scim2_models import Group
from scim2_models import GroupMember
from scim2_models import InvalidValueException
from scim2_models import NoTargetException
from scim2_models import PatchOp
from scim2_models import PatchOperation
from scim2_models import User
from scim2_models.base import Context


def test_remove_operation_single_attribute():
    """Test removing a single-valued attribute."""
    user = User(nick_name="Babs")
    patch = PatchOp[User](
        operations=[PatchOperation[User](op=PatchOperation.Op.remove, path="nickName")]
    )
    result = patch.patch(user)
    assert result is True
    assert user.nick_name is None


def test_remove_operation_nonexistent_attribute():
    """Test removing an attribute that doesn't exist should not raise an error."""
    user = User()
    patch = PatchOp[User](
        operations=[PatchOperation[User](op=PatchOperation.Op.remove, path="nickName")]
    )
    result = patch.patch(user)
    assert result is False
    assert user.nick_name is None


def test_remove_operation_sub_attribute():
    """Test removing a sub-attribute of a complex attribute."""
    user = User(name={"familyName": "Jensen", "givenName": "Barbara"})
    patch = PatchOp[User](
        operations=[
            PatchOperation[User](op=PatchOperation.Op.remove, path="name.familyName")
        ]
    )
    result = patch.patch(user)
    assert result is True
    assert user.name.family_name is None
    assert user.name.given_name == "Barbara"


def test_remove_operation_complex_attribute():
    """Test removing an entire complex attribute."""
    user = User(name={"familyName": "Jensen", "givenName": "Barbara"})
    patch = PatchOp[User](
        operations=[PatchOperation[User](op=PatchOperation.Op.remove, path="name")]
    )
    result = patch.patch(user)
    assert result is True
    assert user.name is None


def test_remove_operation_sub_attribute_parent_none():
    """Test removing a sub-attribute when parent is None."""
    user = User(name=None)
    patch = PatchOp[User](
        operations=[
            PatchOperation[User](op=PatchOperation.Op.remove, path="name.familyName")
        ]
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
        operations=[PatchOperation[Group](op=PatchOperation.Op.remove, path="members")]
    )
    result = patch.patch(group)
    assert result is True
    assert group.members is None or len(group.members) == 0


def test_remove_operation_bypass_validation_no_path():
    """Test remove operation with no path raises noTarget error per RFC7644 §3.5.2.2."""
    with pytest.raises(ValidationError, match="Remove operation requires a path"):
        PatchOp.model_validate(
            {
                "operations": [
                    {"op": "remove", "value": "test"},
                ],
            },
            context={"scim": Context.RESOURCE_PATCH_REQUEST},
        )


def test_defensive_path_check_in_remove():
    """Test defensive path check in _apply_remove method per RFC7644 §3.5.2.2."""
    user = User(nick_name="Test")
    patch = PatchOp[User](
        operations=[PatchOperation[User](op=PatchOperation.Op.remove, path="nickName")]
    )

    # Force path to None to test defensive check
    patch.operations[0] = PatchOperation.model_construct(
        op=PatchOperation.Op.remove, path=None
    )

    with pytest.raises(NoTargetException, match="Remove operation requires a path"):
        patch.patch(user)


def test_remove_a_subattribute_of_every_entry():
    """An unfiltered path designates the sub-attribute of each entry.

    :rfc:`RFC7644 §3.5.2.2 <7644#section-3.5.2.2>` has an operation carrying no
    filter reach every value of a multi-valued attribute.
    """
    user = User(
        user_name="bjensen",
        emails=[
            User.Emails(value="bjensen@example.com", type="work"),
            User.Emails(value="babs@example.org", type="home"),
        ],
    )
    patch = PatchOp[User](
        operations=[
            PatchOperation[User](op=PatchOperation.Op.remove, path="emails.type")
        ]
    )
    assert patch.patch(user) is True
    assert [email.type for email in user.emails] == [None, None]
    assert [email.value for email in user.emails] == [
        "bjensen@example.com",
        "babs@example.org",
    ]


def test_remove_carrying_a_value_is_refused_at_validation():
    """:rfc:`RFC7644 §3.5.2.2 <7644#section-3.5.2.2>` defines a remove by its path alone."""
    with pytest.raises(ValidationError, match="carries no value"):
        PatchOp[Group].model_validate(
            {
                "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
                "Operations": [
                    {"op": "remove", "path": "members", "value": [{"value": "bob"}]}
                ],
            },
            scim_ctx=Context.RESOURCE_PATCH_REQUEST,
        )


def test_remove_carrying_a_value_is_refused_when_applied():
    """A remove built in Python skips validation, and must not silently do nothing."""
    group = Group(display_name="eq", members=[GroupMember(value="bob", display="Bob")])
    patch = PatchOp[Group](
        operations=[
            PatchOperation[Group](
                op=PatchOperation.Op.remove,
                path="members",
                value=[{"value": "bob"}],
            )
        ]
    )
    with pytest.raises(InvalidValueException, match="carries no value"):
        patch.patch(group)
    assert [member.value for member in group.members] == ["bob"]


def test_remove_carrying_a_value_on_a_singular_attribute_is_refused():
    """The refusal holds wherever the path lands, not only on multi-valued attributes."""
    user = User(nick_name="Babs")
    patch = PatchOp[User](
        operations=[
            PatchOperation[User](
                op=PatchOperation.Op.remove, path="nickName", value="Babs"
            )
        ]
    )
    with pytest.raises(InvalidValueException, match="carries no value"):
        patch.patch(user)
    assert user.nick_name == "Babs"


def test_remove_selecting_nothing_reports_no_change():
    """:rfc:`RFC7644 §3.5.2.2 <7644#section-3.5.2.2>` answers a success when a selection is empty.

    'If the user was not a member of this group, no changes should be made to
    the resource, and a success response should be returned.'
    """
    group = Group(display_name="eq", members=[GroupMember(value="bob")])
    patch = PatchOp[Group](
        operations=[
            PatchOperation[Group](
                op=PatchOperation.Op.remove, path='members[value eq "alice"]'
            )
        ]
    )
    assert patch.patch(group) is False
    assert [member.value for member in group.members] == ["bob"]
