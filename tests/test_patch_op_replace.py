from typing import Annotated

import pytest
from pydantic import ValidationError

from scim2_models import URN
from scim2_models import EnterpriseUser
from scim2_models import Group
from scim2_models import InvalidFilterException
from scim2_models import InvalidValueException
from scim2_models import MutabilityException
from scim2_models import Name
from scim2_models import NoTargetException
from scim2_models import PatchOp
from scim2_models import PatchOperation
from scim2_models import ScimPolicy
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


def test_immutable_field():
    """Test that replace operations on immutable fields raise mutability errors."""

    class Dummy(Resource):
        __schema__ = URN("urn:test:TestResource")

        immutable: Annotated[str, Mutability.immutable]

    resource = Dummy.model_construct(immutable="original")
    patch = PatchOp[Dummy](
        operations=[
            PatchOperation[Dummy](
                op=PatchOperation.Op.replace_, path="immutable", value="new_value"
            )
        ]
    )
    with pytest.raises(MutabilityException):
        patch.patch(resource)


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


def test_replace_a_subattribute_of_every_entry():
    """An unfiltered path designates the sub-attribute of each entry.

    :rfc:`RFC7644 §3.5.2.3 <7644#section-3.5.2.3>` replaces every value a
    selection matches, which without a selection is all of them.
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
            PatchOperation[User](
                op=PatchOperation.Op.replace_,
                path="emails.value",
                value="new@example.com",
            )
        ]
    )
    assert patch.patch(user) is True
    assert [email.value for email in user.emails] == [
        "new@example.com",
        "new@example.com",
    ]


@pytest.mark.parametrize(
    "path",
    [
        "name.givenName",
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:costCenter",
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:manager.value",
    ],
)
def test_unassigning_under_an_unassigned_container_leaves_the_resource(path):
    """Nothing is created to hold a null value."""
    user = User[EnterpriseUser](user_name="bjensen")
    patch = PatchOp[User[EnterpriseUser]].model_validate(
        {"Operations": [{"op": "replace", "path": path, "value": None}]}
    )

    assert patch.patch(user) is False
    assert user.name is None
    assert user[EnterpriseUser] is None


def _jensen():
    return User(
        user_name="bjensen", name=Name(given_name="Barbara", family_name="Jensen")
    )


COMPLEX_WRITES = [
    pytest.param("name", {"givenName": "Babs"}, id="attribute path"),
    pytest.param(
        "urn:ietf:params:scim:schemas:core:2.0:User:name",
        {"givenName": "Babs"},
        id="qualified path",
    ),
    pytest.param(None, {"name": {"givenName": "Babs"}}, id="no path"),
    pytest.param("", {"name": {"givenName": "Babs"}}, id="empty path"),
]


@pytest.mark.parametrize("op", ["add", "replace"])
@pytest.mark.parametrize(("path", "value"), COMPLEX_WRITES)
def test_a_partial_complex_value_leaves_the_other_sub_attributes(op, path, value):
    """RFC7644 §3.5.2.3 keeps the sub-attributes the value does not specify."""
    user = _jensen()
    operation = {"op": op, "value": value}
    if path is not None:
        operation["path"] = path

    assert PatchOp[User].model_validate({"Operations": [operation]}).patch(user)

    assert user.name == Name(given_name="Babs", family_name="Jensen")


def test_a_null_sub_attribute_in_a_complex_value_unassigns_it_alone():
    """A null value unassigns only the sub-attribute it is given to."""
    user = _jensen()
    patch = PatchOp[User].model_validate(
        {
            "Operations": [
                {"op": "replace", "path": "name", "value": {"givenName": None}}
            ]
        }
    )

    patch.patch(user)

    assert user.name == Name(family_name="Jensen")


def test_a_complex_value_on_an_unassigned_attribute_assigns_it():
    """Per RFC7644 §3.5.2.3, a replace on a missing attribute adds it."""
    user = User(user_name="bjensen")
    patch = PatchOp[User].model_validate(
        {
            "Operations": [
                {"op": "replace", "path": "name", "value": {"givenName": "Babs"}}
            ]
        }
    )

    assert patch.patch(user)
    assert user.name == Name(given_name="Babs")


def test_an_undeclared_sub_attribute_in_a_complex_value_is_refused():
    """RFC7644 §3.12 defines invalidValue for a value that does not fit the resource schema."""
    with pytest.raises(ValidationError) as raised:
        PatchOp[User].model_validate(
            {"Operations": [{"op": "add", "path": "name", "value": {"bogus": 1}}]}
        )

    assert raised.value.errors()[0]["type"] == "scim_invalidValue"


def test_a_tolerant_policy_drops_an_undeclared_sub_attribute_alone():
    """The sub-attributes the value leaves out are kept when the undeclared one is dropped."""
    user = _jensen()
    tolerant = ScimPolicy(unknown=ScimPolicy.Unknown.ignore)
    patch = PatchOp[User].model_validate(
        {"Operations": [{"op": "add", "path": "name", "value": {"bogus": 1}}]},
        scim_policy=tolerant,
    )

    assert patch.patch(user, scim_policy=tolerant) is False
    assert user.name == Name(given_name="Barbara", family_name="Jensen")


def _user_with_work_email():
    return User(
        user_name="bjensen",
        emails=[
            {"value": "bjensen@example.com", "type": "work", "display": "Work"},
            {"value": "babs@example.com", "type": "home"},
        ],
    )


def test_a_replace_selecting_entries_merges_the_value_into_them():
    """RFC7644 §3.5.2.3 keeps the sub-attributes a value does not specify."""
    user = _user_with_work_email()
    patch = PatchOp[User].model_validate(
        {
            "Operations": [
                {
                    "op": "replace",
                    "path": 'emails[type eq "work"]',
                    "value": {"value": "barbara@example.com"},
                }
            ]
        }
    )

    assert patch.patch(user)

    assert user.emails[0].value == "barbara@example.com"
    assert user.emails[0].type == "work"
    assert user.emails[0].display == "Work"
    assert user.emails[1].value == "babs@example.com"


def test_a_replace_selecting_entries_unassigns_a_sub_attribute_given_null():
    """Per RFC7643 §2.5, a null value unassigns the sub-attribute it is given to."""
    user = _user_with_work_email()
    patch = PatchOp[User].model_validate(
        {
            "Operations": [
                {
                    "op": "replace",
                    "path": 'emails[type eq "work"]',
                    "value": {"display": None},
                }
            ]
        }
    )

    assert patch.patch(user)

    assert user.emails[0].display is None
    assert user.emails[0].value == "bjensen@example.com"


def test_a_replace_selecting_a_member_changes_it_without_repeating_its_value():
    """A client does not have to repeat the immutable value its filter used to select the member."""
    group = Group(
        display_name="Tour Guides",
        members=[{"value": "2819c223", "display": "Babs Jensen"}],
    )
    patch = PatchOp[Group].model_validate(
        {
            "Operations": [
                {
                    "op": "replace",
                    "path": 'members[value eq "2819c223"]',
                    "value": {"display": "Barbara Jensen"},
                }
            ]
        }
    )

    assert patch.patch(group)
    assert group.members[0].value == "2819c223"
    assert group.members[0].display == "Barbara Jensen"


def test_an_entry_replaced_through_a_selection_keeps_its_identity():
    """Entries are only told apart by identity, so a replaced entry stays the same object."""
    user = _user_with_work_email()
    entry = user.emails[0]
    patch = PatchOp[User].model_validate(
        {
            "Operations": [
                {
                    "op": "replace",
                    "path": 'emails[type eq "work"]',
                    "value": {"value": "barbara@example.com"},
                }
            ]
        }
    )

    patch.patch(user)

    assert user.emails[0] is entry


def test_an_add_selecting_entries_merges_the_value_into_them():
    """An add writes the sub-attributes in its value and leaves the others."""
    user = _user_with_work_email()
    patch = PatchOp[User].model_validate(
        {
            "Operations": [
                {
                    "op": "add",
                    "path": 'emails[type eq "work"]',
                    "value": {"display": "Office"},
                }
            ]
        }
    )

    assert patch.patch(user)

    assert user.emails[0].value == "bjensen@example.com"
    assert user.emails[0].type == "work"
    assert user.emails[0].display == "Office"


def test_an_add_selecting_entries_with_the_values_they_hold_changes_nothing():
    """Per RFC7644 §3.5.2.1, adding a value already held changes nothing."""
    user = _user_with_work_email()
    patch = PatchOp[User].model_validate(
        {
            "Operations": [
                {
                    "op": "add",
                    "path": 'emails[type eq "work"]',
                    "value": {"display": "Work"},
                }
            ]
        }
    )

    assert patch.patch(user) is False


def test_a_replace_selecting_a_member_cannot_change_its_immutable_value():
    """RFC7643 §4.2 makes member sub-attributes immutable, even when the whole entry is written."""
    group = Group(display_name="Tour Guides", members=[{"value": "2819c223"}])
    patch = PatchOp[Group].model_validate(
        {
            "Operations": [
                {
                    "op": "replace",
                    "path": 'members[value eq "2819c223"]',
                    "value": {"value": "c3a26dd3"},
                }
            ]
        }
    )

    with pytest.raises(MutabilityException):
        patch.patch(group)


class Tagged(Resource):
    __schema__ = URN("urn:example:2.0:Tagged")

    tags: list[str] | None = None


def test_a_replace_selecting_simple_values_replaces_them():
    """The values of a multi-valued attribute without sub-attributes are selected by their value."""
    resource = Tagged(tags=["red", "blue"])
    patch = PatchOp[Tagged].model_validate(
        {
            "Operations": [
                {"op": "replace", "path": 'tags[value eq "red"]', "value": "green"}
            ]
        }
    )

    assert patch.patch(resource)
    assert resource.tags == ["green", "blue"]


def test_a_replace_selecting_entries_refuses_a_value_that_is_no_entry():
    """RFC7644 §3.12 returns invalidValue for a value that does not fit the attribute type."""
    user = _user_with_work_email()
    patch = PatchOp[User].model_validate(
        {
            "Operations": [
                {"op": "replace", "path": 'emails[type eq "work"]', "value": "x"}
            ]
        }
    )

    with pytest.raises(InvalidValueException):
        patch.patch(user)


def test_a_replace_selecting_simple_values_with_the_one_they_hold_changes_nothing():
    """Writing the value already held modifies nothing."""
    resource = Tagged(tags=["red", "blue"])
    patch = PatchOp[Tagged].model_validate(
        {
            "Operations": [
                {"op": "replace", "path": 'tags[value eq "red"]', "value": "red"}
            ]
        }
    )

    assert patch.patch(resource) is False


@pytest.mark.parametrize("path", [None, "emails"])
def test_a_replace_writing_the_entries_held_reports_no_change(path):
    """A patch leaving the resource as it was reports no modification."""
    user = _user_with_work_email()
    entries = [
        {"value": "bjensen@example.com", "type": "work", "display": "Work"},
        {"value": "babs@example.com", "type": "home"},
    ]
    operation = (
        {"op": "replace", "value": {"emails": entries}}
        if path is None
        else {"op": "replace", "path": path, "value": entries}
    )

    assert (
        PatchOp[User].model_validate({"Operations": [operation]}).patch(user) is False
    )


def test_a_replace_bringing_two_primary_entries_is_refused():
    """RFC7643 §2.4 allows primary to be true on one value at most."""
    user = User(
        user_name="bjensen",
        emails=[{"value": "bjensen@example.com", "primary": True}],
    )
    patch = PatchOp[User].model_validate(
        {
            "Operations": [
                {
                    "op": "replace",
                    "path": "emails",
                    "value": [
                        {"value": "babs@example.com", "primary": True},
                        {"value": "barbara@example.com", "primary": True},
                    ],
                }
            ]
        }
    )

    with pytest.raises(InvalidValueException):
        patch.patch(user)

    assert [email.value for email in user.emails] == ["bjensen@example.com"]


def test_a_replace_bringing_one_primary_entry_keeps_it():
    """A replaced list holding a single primary entry keeps it primary."""
    user = User(
        user_name="bjensen",
        emails=[{"value": "bjensen@example.com", "primary": True}],
    )
    patch = PatchOp[User].model_validate(
        {
            "Operations": [
                {
                    "op": "replace",
                    "path": "emails",
                    "value": [
                        {"value": "babs@example.com"},
                        {"value": "barbara@example.com", "primary": True},
                    ],
                }
            ]
        }
    )

    assert patch.patch(user)
    assert [email.primary for email in user.emails] == [None, True]


@pytest.mark.parametrize("op", ["add", "replace"])
@pytest.mark.parametrize(
    "value", [{}, {"whatever": "x"}], ids=["empty", "only-undeclared"]
)
def test_a_value_writing_nothing_still_needs_a_target(op, value):
    """The filter is resolved even when the value writes nothing to the entries."""
    user = User(
        user_name="bjensen", emails=[{"value": "b@example.com", "type": "home"}]
    )
    patch = PatchOp[User].model_validate(
        {"Operations": [{"op": op, "path": 'emails[type eq "work"]', "value": value}]},
        scim_policy=ScimPolicy(unknown=ScimPolicy.Unknown.ignore),
    )

    with pytest.raises(NoTargetException):
        patch.patch(user, scim_policy=ScimPolicy(unknown=ScimPolicy.Unknown.ignore))


@pytest.mark.parametrize("op", ["add", "replace"])
def test_a_value_writing_nothing_still_needs_a_valid_filter(op):
    """A filter on an undeclared sub-attribute is rejected, whatever the value."""
    user = User(
        user_name="bjensen", emails=[{"value": "b@example.com", "type": "home"}]
    )
    patch = PatchOp[User].model_validate(
        {"Operations": [{"op": op, "path": 'emails[whatever eq "x"]', "value": {}}]}
    )

    with pytest.raises(InvalidFilterException):
        patch.patch(user)
