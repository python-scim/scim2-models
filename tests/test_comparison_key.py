from typing import Annotated
from unicodedata import normalize

import pytest
from pydantic import ValidationError

from scim2_models import CaseExact
from scim2_models import Context
from scim2_models import Email
from scim2_models import EnterpriseUser
from scim2_models import Error
from scim2_models import Group
from scim2_models import GroupMember
from scim2_models import InvalidValueException
from scim2_models import Name
from scim2_models import PatchOp
from scim2_models import Path
from scim2_models import Resource
from scim2_models import ScimFilter
from scim2_models import ScimPolicy
from scim2_models import SearchRequest
from scim2_models import User
from scim2_models import default_comparison_key

PATCH_OP = "urn:ietf:params:scim:api:messages:2.0:PatchOp"


def refusing_spaces(binding, value):
    """Prepare strings as the default does, and refuse the ones holding a space."""
    if " " in value:
        raise ValueError("spaces are not allowed")
    return default_comparison_key(binding, value)


def compatibility_mapped(binding, value):
    """Prepare strings with NFKC, which maps fullwidth letters to ASCII."""
    return default_comparison_key(binding, normalize("NFKC", value))


REFUSING = ScimPolicy(comparison_key=refusing_spaces)


class Tagged(Resource):
    __schema__ = "urn:example:2.0:Tagged"

    tags: list[str] | None = None
    codes: Annotated[list[str] | None, CaseExact.true] = None


def patch(resource, *operations, policy=None):
    """Apply PATCH operations given as payloads."""
    patch_op = PatchOp[type(resource)].model_validate(
        {"schemas": [PATCH_OP], "Operations": list(operations)}
    )
    return patch_op.patch(resource, scim_policy=policy)


def test_the_default_key_keeps_the_sharp_s():
    """Lowercasing does not expand the sharp s, as the case mapping of RFC 8265 does not."""
    binding = Path[User]("userName").resolve()
    assert default_comparison_key(binding, "STRAẞE") == "straße"


def test_the_default_key_normalizes_a_case_exact_string_to_nfc():
    """A case-exact string keeps its case and still gets a single normalization form."""
    binding = Path[User]("externalId").resolve()
    assert default_comparison_key(binding, "JOSÉ") == "JOSÉ"


def test_comparable_uses_the_policy_it_is_given():
    """A policy passed to the call decides the comparison form."""
    binding = Path[User]("userName").resolve()
    policy = ScimPolicy(comparison_key=compatibility_mapped)
    assert binding.comparable("ＢＪｅｎｓｅｎ", policy) == "bjensen"


def test_comparable_uses_the_ambient_policy():
    """Without a policy argument, the policy of the open block decides."""
    binding = Path[User]("userName").resolve()
    with ScimPolicy(comparison_key=compatibility_mapped):
        assert binding.comparable("ＢＪｅｎｓｅｎ") == "bjensen"
    assert binding.comparable("ＢＪｅｎｓｅｎ") == "ｂｊｅｎｓｅｎ"


def test_comparable_prefers_the_policy_argument_over_the_ambient_one():
    """The argument wins over the block, as for validation."""
    binding = Path[User]("userName").resolve()
    with ScimPolicy(comparison_key=compatibility_mapped):
        assert binding.comparable("ＢＪｅｎｓｅｎ", ScimPolicy()) == "ｂｊｅｎｓｅｎ"


def test_comparable_does_not_give_other_values_to_the_key():
    """The key only prepares strings, so it need not handle other types."""
    binding = Path[User]("active").resolve()
    assert binding.comparable(True, REFUSING) is True


def test_comparable_raises_on_a_string_the_key_cannot_prepare():
    """The refusal of the key reaches the caller, which decides what it means."""
    binding = Path[User]("userName").resolve()
    with pytest.raises(ValueError, match="spaces"):
        binding.comparable("John Doe", REFUSING)


def test_a_filter_compares_under_the_ambient_policy():
    """A custom key changes which values a filter matches."""
    user = User(user_name="bjensen")
    with ScimPolicy(comparison_key=compatibility_mapped):
        assert ScimFilter[User]('userName eq "ＢＪＥＮＳＥＮ"').match(user)
    assert not ScimFilter[User]('userName eq "ＢＪＥＮＳＥＮ"').match(user)


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ('displayName eq "Babs Jensen"', False),
        ('displayName ne "Babs Jensen"', True),
        ('displayName co "s J"', False),
        ('displayName sw "Babs "', False),
        ('displayName ew " Jensen"', False),
        ('displayName gt "Babs Jensen"', False),
        ('displayName le "Babs Jensen"', False),
        ('not (displayName eq "Babs Jensen")', True),
        ("displayName pr", True),
    ],
)
def test_an_operand_the_key_cannot_prepare_is_equal_to_no_value(expression, expected):
    """Only ne holds against a string the policy refuses, and not negates as usual."""
    user = User(display_name="Babs Jensen")
    with REFUSING:
        assert ScimFilter[User](expression).match(user) is expected


def test_a_stored_value_the_key_cannot_prepare_is_equal_to_no_operand():
    """A stored string the policy refuses does not even equal its own spelling."""
    user = User(display_name="Babs Jensen")
    with REFUSING:
        assert not ScimFilter[User]('displayName eq "Babs Jensen"').match(user)
        assert ScimFilter[User]('displayName ne "BabsJensen"').match(user)


def test_ne_on_a_multi_valued_attribute_holds_when_no_value_can_be_prepared():
    """No entry equals the operand, so the universal reading of ne holds."""
    user = User(emails=[Email(value="bjensen@example.com", display="Babs Jensen")])
    with REFUSING:
        assert ScimFilter[User]('emails.display ne "Babs Jensen"').match(user)


@pytest.mark.parametrize(
    ("order", "expected"),
    [
        (SearchRequest.SortOrder.ascending, ["alice", "bob", "Babs Jensen", None]),
        (SearchRequest.SortOrder.descending, ["Babs Jensen", None, "bob", "alice"]),
    ],
)
def test_a_value_the_key_cannot_prepare_sorts_with_the_missing_values(order, expected):
    """A string the policy refuses has no comparison form, like a missing value."""
    users = [User(display_name=name) for name in ("bob", "Babs Jensen", None, "alice")]
    request = SearchRequest[User](sort_by="displayName", sort_order=order)
    with REFUSING:
        assert [user.display_name for user in request.sort(users)] == expected


def creation_payload(**attributes):
    """Build a User creation payload."""
    return {"schemas": [str(User.__schema__)], "userName": "bjensen", **attributes}


@pytest.mark.parametrize(
    "context",
    [
        Context.RESOURCE_CREATION_REQUEST,
        Context.RESOURCE_REPLACEMENT_REQUEST,
    ],
)
def test_a_request_writing_a_string_the_key_cannot_prepare_is_refused(context):
    """A value the service could never compare is refused with invalidValue."""
    with pytest.raises(ValidationError) as excinfo:
        User.model_validate(
            creation_payload(userName="John Doe"),
            scim_ctx=context,
            scim_policy=REFUSING,
        )

    error = Error.from_validation_errors(excinfo.value)[0]
    assert error.status == 400
    assert error.scim_type == "invalidValue"
    assert "urn:ietf:params:scim:schemas:core:2.0:User:userName" in error.detail


@pytest.mark.parametrize(
    "attributes",
    [
        {"name": {"givenName": "Barbara Jane"}},
        {"emails": [{"value": "bjensen@example.com", "display": "Babs Jensen"}]},
        {"title": "Tour Guide"},
    ],
)
def test_sub_attributes_and_entries_are_checked_too(attributes):
    """Every string the request writes is checked, wherever it sits."""
    with pytest.raises(ValidationError, match="cannot be compared"):
        User.model_validate(
            creation_payload(**attributes),
            scim_ctx=Context.RESOURCE_CREATION_REQUEST,
            scim_policy=REFUSING,
        )


def test_extension_attributes_are_checked_too():
    """A string of an extension is compared like any other."""
    payload = {
        "schemas": [str(User.__schema__), str(EnterpriseUser.__schema__)],
        "userName": "bjensen",
        str(EnterpriseUser.__schema__): {"department": "Tour Operations"},
    }
    with pytest.raises(ValidationError, match="enterprise:2.0:User:department"):
        User[EnterpriseUser].model_validate(
            payload,
            scim_ctx=Context.RESOURCE_CREATION_REQUEST,
            scim_policy=REFUSING,
        )


@pytest.mark.parametrize(
    "context",
    [Context.RESOURCE_QUERY_RESPONSE, Context.DEFAULT, None],
)
def test_a_response_holding_a_string_the_key_cannot_prepare_is_read(context):
    """A client must be able to read a value the policy of its service refuses."""
    user = User.model_validate(
        {**creation_payload(userName="John Doe"), "id": "2819c223"},
        scim_ctx=context,
        scim_policy=REFUSING,
    )
    assert user.user_name == "John Doe"


def test_the_default_key_refuses_nothing():
    """Under the default policy, no string is refused for its comparison form."""
    user = User.model_validate(
        creation_payload(userName="John Doe", title="Tour Guide"),
        scim_ctx=Context.RESOURCE_CREATION_REQUEST,
    )
    assert user.user_name == "John Doe"


@pytest.mark.parametrize(
    "operation",
    [
        {"op": "replace", "path": "userName", "value": "John Doe"},
        {"op": "replace", "value": {"userName": "John Doe"}},
        {"op": "add", "path": "name", "value": {"givenName": "Barbara Jane"}},
        {
            "op": "add",
            "path": "emails",
            "value": [{"value": "bjensen@example.com", "display": "Babs Jensen"}],
        },
    ],
)
def test_a_patch_writing_a_string_the_key_cannot_prepare_is_refused(operation):
    """The values of a PATCH are typed when applied, so the refusal comes then."""
    user = User(user_name="bjensen")

    with pytest.raises(InvalidValueException, match="cannot be compared"):
        patch(user, operation, policy=REFUSING)

    assert user.user_name == "bjensen"
    assert user.name is None
    assert user.emails is None


def test_a_patch_leaves_a_stored_value_it_does_not_write_alone():
    """A value the policy refuses, stored before, does not block other changes."""
    user = User(user_name="bjensen", display_name="Babs Jensen")

    assert patch(
        user, {"op": "replace", "path": "title", "value": "Guide"}, policy=REFUSING
    )
    assert user.title == "Guide"


def test_a_patch_removing_an_extension_writes_no_string():
    """Unassigning a whole extension leaves no string to compare."""
    user = User[EnterpriseUser](user_name="bjensen", display_name="Babs Jensen")
    user[EnterpriseUser] = EnterpriseUser(department="Tours")

    assert patch(
        user,
        {"op": "replace", "value": {str(EnterpriseUser.__schema__): None}},
        policy=REFUSING,
    )
    assert user[EnterpriseUser] is None


def test_a_patch_removal_is_not_refused():
    """A removal writes nothing, even where a refused value stands."""
    user = User(user_name="bjensen", display_name="Babs Jensen")

    assert patch(user, {"op": "remove", "path": "displayName"}, policy=REFUSING)
    assert user.display_name is None


def test_adding_an_entry_already_held_under_another_case_changes_nothing():
    """An add does not duplicate a value the attribute already holds, compared as a filter would."""
    user = User(
        user_name="bjensen", emails=[Email(value="bjensen@example.com", type="work")]
    )

    assert not patch(
        user,
        {
            "op": "add",
            "path": "emails",
            "value": [{"value": "BJensen@Example.com", "type": "WORK"}],
        },
    )
    assert len(user.emails) == 1


def test_adding_an_entry_differing_in_a_case_exact_sub_attribute_adds_it():
    """A member value is case-exact, so a value differing in case is another member."""
    group = Group(display_name="Tour Guides", members=[GroupMember(value="abc")])

    assert patch(group, {"op": "add", "path": "members", "value": [{"value": "ABC"}]})
    assert [member.value for member in group.members] == ["abc", "ABC"]


def test_adding_a_string_already_held_under_another_case_changes_nothing():
    """A multi-valued string attribute compares its values as a filter would."""
    tagged = Tagged(tags=["Admin"], codes=["Admin"])

    assert not patch(tagged, {"op": "add", "path": "tags", "value": ["ADMIN"]})
    assert patch(tagged, {"op": "add", "path": "codes", "value": ["ADMIN"]})
    assert tagged.tags == ["Admin"]
    assert tagged.codes == ["Admin", "ADMIN"]


def test_removing_a_value_matches_it_as_a_filter_would():
    """A removal by value finds the entry whatever its case."""
    tagged = Tagged(tags=["Admin", "Guest"])

    assert Path[Tagged]("tags").delete(tagged, "ADMIN")
    assert tagged.tags == ["Guest"]


def test_a_value_the_key_cannot_prepare_matches_no_held_value():
    """A string the policy refuses is equal to no other, so nothing is removed."""
    tagged = Tagged(tags=["Tour Guide"])

    with REFUSING:
        assert not Path[Tagged]("tags").delete(tagged, "Tour Guide")
    assert tagged.tags == ["Tour Guide"]


def test_replacing_a_value_by_another_case_is_a_change():
    """A replace keeps the case it writes, so a new case is a new value."""
    user = User(user_name="bjensen", name=Name(given_name="barbara"))

    assert patch(user, {"op": "replace", "path": "name.givenName", "value": "Barbara"})
    assert user.name.given_name == "Barbara"
