import pytest

from scim2_models import BaseModel
from scim2_models import EnterpriseUser
from scim2_models import Extension
from scim2_models import Group
from scim2_models import InvalidFilterException
from scim2_models import NoTargetException
from scim2_models import Path
from scim2_models import PathNotFoundException
from scim2_models import User


@pytest.fixture
def user():
    return User(
        user_name="bjensen",
        emails=[
            {"type": "work", "value": "work@example.com", "primary": True},
            {"type": "home", "value": "home@example.com", "primary": False},
            {"type": "work", "value": "work2@example.com", "primary": False},
        ],
    )


@pytest.fixture
def group():
    return Group(
        display_name="Admins",
        members=[
            {"value": "2819c223", "display": "Babs"},
            {"value": "902c246f", "display": "Jim"},
        ],
    )


# --- Parsed form ---


def test_a_value_selecting_path_exposes_its_filter():
    assert str(Path('emails[type eq "work"].value').value_filter) == 'type eq "work"'


def test_a_plain_path_has_no_filter():
    assert Path("emails.value").value_filter is None
    assert Path("").value_filter is None


def test_a_bare_comparison_path_is_its_own_filter():
    """Errata 7122 allows ``attrExp`` as a path."""
    assert str(Path('schemas eq "urn:x:y"').value_filter) == 'schemas eq "urn:x:y"'


def test_a_bare_presence_path_is_its_own_filter():
    assert str(Path("title pr").value_filter) == "title pr"


def test_the_root_path_has_no_parsed_form():
    assert Path("").ast is None


def test_a_value_selection_is_not_part_of_the_segments():
    """``parts[0]`` stays the attribute a PATCH operation applies to."""
    assert Path('emails[type eq "work"].value').parts == ("emails", "value")
    assert Path('emails[type eq "work"]').parts == ("emails",)


def test_a_value_selecting_path_keeps_its_attribute_portion():
    path = Path(
        'urn:ietf:params:scim:schemas:core:2.0:User:emails[type eq "work"].value'
    )
    assert path.schema == "urn:ietf:params:scim:schemas:core:2.0:User"
    assert path.attr == 'emails[type eq "work"].value'


# --- Reading ---


def test_reading_a_sub_attribute_of_the_matching_values(user):
    assert Path[User]('emails[type eq "work"].value').get(user) == [
        "work@example.com",
        "work2@example.com",
    ]


def test_reading_the_matching_values_themselves(user):
    matched = Path[User]('emails[type eq "home"]').get(user)
    assert [email.value for email in matched] == ["home@example.com"]


def test_reading_a_selection_that_matches_nothing(user):
    assert Path[User]('emails[type eq "other"]').get(user) is None


def test_reading_a_sub_attribute_of_a_selection_that_matches_nothing(user):
    assert Path[User]('emails[type eq "other"].value').get(user) is None


def test_reading_a_selection_on_an_unset_attribute():
    assert Path[User]('emails[type eq "work"]').get(User(user_name="x")) is None


def test_reading_a_selection_on_an_unknown_attribute_raises():
    with pytest.raises(PathNotFoundException):
        Path[User]('nonexistent[type eq "work"]').get(User(user_name="x"))


def test_reading_with_a_boolean_selection(user):
    matched = Path[User]("emails[primary eq true]").get(user)
    assert [email.value for email in matched] == ["work@example.com"]


def test_reading_with_a_composed_selection(user):
    matched = Path[User]('emails[type eq "work" and primary eq false]').get(user)
    assert [email.value for email in matched] == ["work2@example.com"]


def test_reading_a_group_member_sub_attribute(group):
    assert Path[Group]('members[value eq "2819c223"].display').get(group) == ["Babs"]


# --- Writing ---


def test_writing_a_sub_attribute_of_the_matching_values(user):
    assert Path[User]('emails[type eq "work"].value').set(user, "new@example.com")
    assert [email.value for email in user.emails] == [
        "new@example.com",
        "home@example.com",
        "new@example.com",
    ]


def test_writing_an_unset_sub_attribute_of_the_matching_values(user):
    assert Path[User]('emails[type eq "home"].display').set(user, "Home")
    assert [email.display for email in user.emails] == [None, "Home", None]


def test_writing_the_same_value_changes_nothing(user):
    assert not Path[User]('emails[type eq "home"].value').set(user, "home@example.com")


def test_writing_replaces_the_matching_values_wholesale(user):
    """§3.5.2.3: all matching record values are replaced."""
    assert Path[User]('emails[type eq "home"]').set(
        user, {"type": "other", "value": "other@example.com"}
    )
    assert [email.type for email in user.emails] == ["work", "other", "work"]


def test_writing_the_same_whole_value_changes_nothing(user):
    assert not Path[User]('emails[type eq "home"]').set(
        user, {"type": "home", "value": "home@example.com", "primary": False}
    )


def test_writing_to_a_selection_that_matches_nothing_has_no_target(user):
    """§3.5.2.3 requires a ``noTarget`` failure when no record matched."""
    with pytest.raises(NoTargetException):
        Path[User]('emails[type eq "other"].value').set(user, "x")


def test_writing_to_a_selection_on_an_unset_attribute_has_no_target():
    with pytest.raises(NoTargetException):
        Path[User]('emails[type eq "work"].value').set(User(user_name="x"), "y")


def test_writing_to_a_selection_that_matches_nothing_is_silent_when_tolerant(user):
    """A tolerant caller gets a plain failure instead of an exception."""
    assert not Path[User]('emails[type eq "other"].value').set(user, "x", strict=False)


def test_writing_an_unknown_sub_attribute_raises(user):
    with pytest.raises(PathNotFoundException):
        Path[User]('emails[type eq "work"].nonexistent').set(user, "x")


# --- Removing ---


def test_removing_the_matching_values(user):
    assert Path[User]('emails[type eq "work"]').delete(user)
    assert [email.value for email in user.emails] == ["home@example.com"]


def test_removing_a_sub_attribute_of_the_matching_values(user):
    assert Path[User]('emails[type eq "work"].value').delete(user)
    assert [email.value for email in user.emails] == [
        None,
        "home@example.com",
        None,
    ]


def test_removing_an_already_unset_sub_attribute_changes_nothing(user):
    assert not Path[User]('emails[type eq "work"].display').delete(user)


def test_removing_every_value_unassigns_the_attribute():
    """§3.5.2.2: an attribute left without any value is unassigned."""
    user = User(user_name="x", emails=[{"type": "work", "value": "w@x.com"}])
    assert Path[User]('emails[type eq "work"]').delete(user)
    assert user.emails is None


def test_removing_a_selection_that_matches_nothing_changes_nothing(user):
    """§3.5.2.2 asks for a success and an untouched resource, not a failure.

    Its removal example states that "if the user was not a member of this
    group, no changes should be made to the resource, and a success response
    should be returned".
    """
    before = user.model_dump()
    assert not Path[User]('emails[type eq "other"]').delete(user)
    assert user.model_dump() == before


def test_removing_a_selection_on_an_unset_attribute_changes_nothing():
    assert not Path[User]('emails[type eq "work"]').delete(User(user_name="x"))


def test_removing_a_group_member(group):
    assert Path[Group]('members[value eq "2819c223"]').delete(group)
    assert [member.value for member in group.members] == ["902c246f"]


# --- The other two notations ---


def test_a_dotted_comparison_selects_like_a_value_path(user):
    """``emails.type eq "work"`` means ``emails[type eq "work"]``."""
    assert Path[User]('emails.type eq "work"').delete(user)
    assert [email.value for email in user.emails] == ["home@example.com"]


def test_a_bare_comparison_selects_a_value_of_a_scalar_list():
    """Errata 7122: the only way to target a value of a non-complex list."""
    user = User(
        user_name="x",
        schemas=[
            "urn:ietf:params:scim:schemas:core:2.0:User",
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
        ],
    )
    assert Path[User](
        'schemas eq "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"'
    ).delete(user)
    assert user.schemas == ["urn:ietf:params:scim:schemas:core:2.0:User"]


def test_the_value_convention_also_selects_a_value_of_a_scalar_list():
    """Implementations conventionally write ``attr[value eq "…"]``."""
    user = User(
        user_name="x", schemas=["urn:ietf:params:scim:schemas:core:2.0:User", "urn:z:w"]
    )
    assert Path[User]('schemas[value eq "urn:z:w"]').delete(user)
    assert user.schemas == ["urn:ietf:params:scim:schemas:core:2.0:User"]


def test_a_bare_presence_selects_every_assigned_value():
    """A required attribute is emptied rather than unset.

    RFC 7643 §7 forbids removing a required attribute, so ``schemas`` keeps an
    empty list where an optional attribute would become :data:`None`.
    """
    user = User(user_name="x", schemas=["urn:ietf:params:scim:schemas:core:2.0:User"])
    assert Path[User]("schemas pr").delete(user)
    assert user.schemas == []


def test_a_selection_on_a_single_valued_extension_attribute_is_invalid():
    """``employeeNumber`` holds one value, so there is nothing to select from."""
    user = User[EnterpriseUser](user_name="x")
    user[EnterpriseUser] = EnterpriseUser(employee_number="1")
    path = Path[User[EnterpriseUser]](
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:employeeNumber "
        'eq "1"'
    )
    with pytest.raises(InvalidFilterException, match="not multi-valued"):
        path.delete(user)


def test_a_selection_on_an_unset_extension_is_invalid():
    user = User[EnterpriseUser](user_name="x")
    path = Path[User[EnterpriseUser]](
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:employeeNumber "
        'eq "1"'
    )
    with pytest.raises(InvalidFilterException, match="not multi-valued"):
        path.delete(user)


def test_a_selection_on_a_single_valued_attribute_is_invalid():
    """§3.5.2 defines a selection over a complex multi-valued attribute only."""
    user = User(user_name="x", name={"family_name": "Jensen"})
    with pytest.raises(InvalidFilterException, match="not multi-valued"):
        Path[User]('name[familyName eq "Jensen"]').delete(user)


def test_a_selection_on_a_single_valued_attribute_is_silent_when_tolerant():
    user = User(user_name="x", name={"family_name": "Jensen"})
    path = Path[User]('name[familyName eq "Jensen"]')
    assert path.get(user, strict=False) is None
    assert not path.set(user, "x", strict=False)
    assert not path.delete(user, strict=False)


class Membership(Extension):
    __schema__ = "urn:example:extensions:Membership"

    class Team(BaseModel):
        name: str | None = None
        role: str | None = None

    teams: list[Team] | None = None


def test_a_selection_on_a_multivalued_attribute_of_an_unset_extension():
    """An extension the resource does not carry holds no values to select."""
    user = User[Membership](user_name="x")
    path = Path[User[Membership]](
        'urn:example:extensions:Membership:teams[name eq "core"]'
    )
    assert path.get(user) is None
    assert not path.delete(user)


def test_adding_to_a_selection_that_matches_nothing_changes_nothing(user):
    """§3.5.2.1 does not define this case, and errata 8097 leaves it open.

    Microsoft Entra ID emits exactly this operation expecting the entry to be
    created, which is not what the published text says, so the operation is a
    no-op rather than a failure.
    """
    before = user.model_dump()
    assert not Path[User]('emails[type eq "other"].value').set(
        user, "other@example.com", is_add=True
    )
    assert user.model_dump() == before


def test_replacing_a_selection_that_matches_nothing_has_no_target(user):
    """§3.5.2.3 is the only operation the RFC requires ``noTarget`` for."""
    with pytest.raises(NoTargetException):
        Path[User]('emails[type eq "other"].value').set(user, "x")


def test_a_selection_comparing_an_invalid_value_is_an_invalid_filter(user):
    """``zz`` is not an email address, so the selection cannot be evaluated."""
    path = Path[User]('emails[value eq "zz"]')
    with pytest.raises(InvalidFilterException, match="not valid for attribute"):
        path.get(user)

    assert path.get(user, strict=False) is None
    assert not path.set(user, "x", strict=False)
    assert not path.delete(user, strict=False)


def test_a_selection_naming_an_unknown_attribute_is_an_invalid_filter(user):
    """The filter between the brackets is resolved against the selected model.

    :class:`~scim2_models.ScimFilter` rejects the same expression, so a path
    must not let it silently match nothing instead.
    """
    path = Path[User]('emails[nonexistent eq "work"].value')
    with pytest.raises(InvalidFilterException, match="nonexistent"):
        path.get(user)
    with pytest.raises(InvalidFilterException, match="nonexistent"):
        path.set(user, "x")
    with pytest.raises(InvalidFilterException, match="nonexistent"):
        path.delete(user)


def test_a_selection_naming_an_unknown_attribute_is_silent_when_tolerant(user):
    path = Path[User]('emails[nonexistent eq "work"].value')
    assert path.get(user, strict=False) is None
    assert not path.set(user, "x", strict=False)
    assert not path.delete(user, strict=False)
