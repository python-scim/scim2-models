from scim2_models import Group
from scim2_models import GroupMember
from scim2_models import PatchOp
from scim2_models import PatchOperation
from scim2_models import User


def test_add_operation_single_attribute():
    """Test adding a value to a single-valued attribute."""
    user = User()
    patch = PatchOp[User](
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
    patch = PatchOp[User](
        operations=[
            PatchOperation(op=PatchOperation.Op.add, path="nickName", value="Babs")
        ]
    )
    result = patch.patch(user)
    assert result is True
    assert user.nick_name == "Babs"


def test_add_operation_same_value():
    """Test adding the same value to a single-valued attribute."""
    user = User(nick_name="Test")
    patch = PatchOp[User](
        operations=[
            PatchOperation(op=PatchOperation.Op.add, path="nickName", value="Test")
        ]
    )
    result = patch.patch(user)
    assert result is False
    assert user.nick_name == "Test"


def test_add_operation_sub_attribute():
    """Test adding a value to a sub-attribute of a complex attribute."""
    user = User()
    patch = PatchOp[User](
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
    patch = PatchOp[User](
        operations=[
            PatchOperation(
                op=PatchOperation.Op.add, path="name", value={"familyName": "Jensen"}
            )
        ]
    )
    result = patch.patch(user)
    assert result is True
    assert user.name.family_name == "Jensen"


def test_add_operation_creates_parent_complex_object():
    """Test add operation creating parent complex object when it doesn't exist."""
    user = User()

    # Add to a sub-attribute when parent doesn't exist
    patch = PatchOp[User](
        operations=[
            PatchOperation(
                op=PatchOperation.Op.add, path="name.givenName", value="John"
            )
        ]
    )

    result = patch.patch(user)
    assert result is True
    assert user.name is not None
    assert user.name.given_name == "John"


def test_add_operation_multiple_attribute():
    """Test adding values to a multi-valued attribute."""
    group = Group()
    patch = PatchOp[Group](
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

    patch = PatchOp[Group](
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


def test_add_operation_single_value_in_multivalued_field():
    """Test adding a single value (not a list) to a multi-valued field.

    :rfc:`RFC7644 §3.5.2.1 <7644#section-3.5.2.1>`: "If the target location is a
    multi-valued attribute, a new value is added to the attribute."
    """
    group = Group(members=[])
    patch = PatchOp[Group](
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
    patch = PatchOp[Group](
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
    patch = PatchOp[Group](
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


def test_add_operation_no_path():
    """Test adding multiple attributes when no path is specified."""
    user = User()
    patch = PatchOp[User](
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


def test_add_operation_no_path_same_attributes():
    """Test add operation with no path but same attribute values should return False."""
    user = User(nick_name="Test")
    patch = PatchOp[User](
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


def test_add_operation_no_path_with_invalid_attribute():
    """Test add operation with no path but invalid attribute name."""
    user = User(nick_name="Test")
    patch = PatchOp[User](
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


def test_add_operation_with_non_dict_value_no_path():
    """Test add operation with no path and non-dict value should return False."""
    user = User()
    patch = PatchOp[User](
        operations=[PatchOperation(op=PatchOperation.Op.add, value="invalid_value")]
    )
    result = patch.patch(user)
    assert result is False
