from typing import Annotated

import pytest

from scim2_models import URN
from scim2_models import Context
from scim2_models import Email
from scim2_models import EnterpriseUser
from scim2_models import Group
from scim2_models import Manager
from scim2_models import Meta
from scim2_models import MutabilityException
from scim2_models import Name
from scim2_models import PatchOp
from scim2_models import PatchOperation
from scim2_models import User
from scim2_models.annotations import Mutability
from scim2_models.resources.resource import Resource


def paths(patch):
    """Return the path and the operation of every operation of a patch."""
    return [(operation.op.value, str(operation.path)) for operation in patch.operations]


def test_a_changed_attribute_becomes_a_replace():
    """RFC7644 §3.5.2.3 has a replace on an unset target behave as an add, so the diff never has to choose between the two."""
    before = User(user_name="bjensen", nick_name="Barb")
    after = User(user_name="bjensen", nick_name="Babs")

    patch = PatchOp.build_from(before, after)

    assert paths(patch) == [("replace", "nickName")]
    assert patch.operations[0].value == "Babs"


def test_an_unchanged_attribute_produces_no_operation():
    """An attribute the two states agree on is left out of the patch."""
    before = User(user_name="bjensen", nick_name="Babs")
    after = User(user_name="bjensen", nick_name="Babs")

    assert PatchOp.build_from(before, after) is None


def test_an_attribute_set_to_none_becomes_a_remove():
    """A caller who writes title=None means "clear the title", where a caller who never names title means "leave it alone"."""
    before = User(user_name="bjensen", title="CEO")
    after = User(user_name="bjensen", title=None)

    patch = PatchOp.build_from(before, after)

    assert paths(patch) == [("remove", "title")]


def test_an_attribute_the_wanted_state_does_not_name_is_left_alone():
    """Unlike the PUT it replaces, a patch leaves an attribute the peer manages and the caller does not model untouched."""
    before = User(user_name="bjensen", nick_name="Barb", title="CEO")
    after = User(user_name="bjensen", nick_name="Babs")

    patch = PatchOp.build_from(before, after)

    assert paths(patch) == [("replace", "nickName")]


def test_a_changed_sub_attribute_is_targeted_by_its_own_path():
    """Targeting name as a whole would replace it entirely and drop the sub-attributes the operation does not carry."""
    before = User(name=Name(given_name="Barbara", family_name="Jensen"))
    after = User(name=Name(given_name="Babs", family_name="Jensen"))

    patch = PatchOp.build_from(before, after)

    assert paths(patch) == [("replace", "name.givenName")]
    assert patch.operations[0].value == "Babs"


def test_a_complex_attribute_set_to_none_is_removed_whole():
    """Naming a complex attribute with no value removes it at its own path."""
    before = User(name=Name(given_name="Barbara"))
    after = User(name=None)

    patch = PatchOp.build_from(before, after)

    assert paths(patch) == [("remove", "name")]


def test_a_complex_attribute_the_current_state_lacks_is_built_sub_attribute_by_sub_attribute():
    """A complex attribute missing from the current state gets one path per sub-attribute."""
    before = User(user_name="bjensen")
    after = User(user_name="bjensen", name=Name(given_name="Babs"))

    patch = PatchOp.build_from(before, after)

    assert paths(patch) == [("replace", "name.givenName")]


def test_a_sub_attribute_the_wanted_state_does_not_name_is_left_alone():
    """The restriction to what the wanted state names reaches sub-attributes."""
    before = User(name=Name(given_name="Barbara", family_name="Jensen"))
    after = User(name=Name(given_name="Babs"))

    patch = PatchOp.build_from(before, after)

    assert paths(patch) == [("replace", "name.givenName")]


def test_read_only_attributes_are_never_patched():
    """RFC7644 §3.5.2 forbids a client to modify a read-only attribute, and naming it would make the patch itself invalid."""
    before = User(user_name="bjensen", id="old", meta=Meta(resource_type="User"))
    after = User(
        user_name="bjensen", id="new", meta=Meta(resource_type="User", version="W/2")
    )

    assert PatchOp.build_from(before, after) is None


def test_the_schemas_attribute_is_never_patched():
    """The schemas attribute belongs to the envelope, not to the state it describes."""
    before = User[EnterpriseUser](user_name="bjensen")
    before.schemas = [str(User.__schema__), str(EnterpriseUser.__schema__)]
    after = User[EnterpriseUser](user_name="bjensen")
    after.schemas = [str(User.__schema__)]

    assert PatchOp.build_from(before, after) is None


def test_an_immutable_attribute_the_current_state_lacks_is_added():
    """RFC7644 §3.5.2 allows adding a value to an immutable attribute that had none."""

    class Immutable(Resource):
        __schema__ = URN("urn:test:Immutable")

        once: Annotated[str | None, Mutability.immutable] = None

    before = Immutable()
    after = Immutable(once="settled")

    patch = PatchOp.build_from(before, after)

    assert paths(patch) == [("add", "once")]


def test_changing_an_immutable_attribute_is_refused():
    """An immutable attribute that already holds a value cannot be modified."""

    class Immutable(Resource):
        __schema__ = URN("urn:test:Immutable")

        once: Annotated[str | None, Mutability.immutable] = None

    before = Immutable(once="settled")
    after = Immutable(once="moved")

    with pytest.raises(MutabilityException):
        PatchOp.build_from(before, after)


def test_two_states_of_different_types_cannot_be_compared():
    """Diffing unrelated models would read every attribute of one as absent from the other."""
    with pytest.raises(TypeError):
        PatchOp.build_from(User(user_name="bjensen"), Group(display_name="admins"))


def test_the_patch_a_diff_builds_is_parameterized_by_the_resource():
    """The operations of the patch resolve their paths against the resource."""
    patch = PatchOp.build_from(
        User(nick_name="Barb"),
        User(nick_name="Babs"),
    )

    assert isinstance(patch, PatchOp[User])
    assert isinstance(patch.operations[0], PatchOperation[User])


def test_a_multi_valued_attribute_is_replaced_whole():
    """RFC7643 §2.4 gives the entries no identity, so an entry that changed cannot be told from a removed one and an added one."""
    before = User(emails=[Email(value="barb@example.com")])
    after = User(emails=[Email(value="babs@example.com")])

    patch = PatchOp.build_from(before, after)

    assert paths(patch) == [("replace", "emails")]
    assert patch.operations[0].value == [Email(value="babs@example.com")]


def test_a_multi_valued_attribute_emptied_is_removed():
    """A collection the wanted state leaves empty is removed at its own path."""
    before = User(emails=[Email(value="barb@example.com")])
    after = User(emails=[])

    patch = PatchOp.build_from(before, after)

    assert paths(patch) == [("remove", "emails")]


def test_only_the_sub_attributes_the_wanted_entries_name_are_compared():
    """A caller that only knows the address of an email leaves the peer free to qualify it, and re-sending the same address changes nothing."""
    before = User(emails=[Email(value="barb@example.com", type="work", primary=True)])
    after = User(emails=[Email(value="barb@example.com")])

    assert PatchOp.build_from(before, after) is None


def test_the_order_of_multi_valued_entries_is_not_a_change():
    """RFC7643 §2.4 gives no significance to the order of a multi-valued attribute."""
    before = User(emails=[Email(value="a@example.com"), Email(value="b@example.com")])
    after = User(emails=[Email(value="b@example.com"), Email(value="a@example.com")])

    assert PatchOp.build_from(before, after) is None


def test_a_multi_valued_attribute_of_scalars_is_compared_by_value():
    """Entries that are not complex have no sub-attribute to project on."""

    class Tagged(Resource):
        __schema__ = URN("urn:test:Tagged")

        tags: list[str] | None = None

    assert PatchOp.build_from(Tagged(tags=["a"]), Tagged(tags=["a"])) is None

    patch = PatchOp.build_from(Tagged(tags=["a"]), Tagged(tags=["a", "b"]))
    assert paths(patch) == [("replace", "tags")]


def test_an_extension_attribute_is_targeted_by_its_qualified_path():
    """An attribute an extension declares is named by its schema URN."""
    before = User[EnterpriseUser](user_name="bjensen")
    before[EnterpriseUser] = EnterpriseUser(department="Tour")
    after = User[EnterpriseUser](user_name="bjensen")
    after[EnterpriseUser] = EnterpriseUser(department="Chess")

    patch = PatchOp.build_from(before, after)

    assert paths(patch) == [
        (
            "replace",
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:department",
        )
    ]


def test_an_extension_the_current_state_lacks_is_patched_attribute_by_attribute():
    """An extension missing from the current state gets one path per attribute."""
    before = User[EnterpriseUser](user_name="bjensen")
    after = User[EnterpriseUser](user_name="bjensen")
    after[EnterpriseUser] = EnterpriseUser(department="Tour")

    patch = PatchOp.build_from(before, after)

    assert paths(patch) == [
        (
            "replace",
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:department",
        )
    ]


def test_an_extension_set_to_none_is_removed_whole():
    """Naming an extension with no value removes it at its schema URN."""
    before = User[EnterpriseUser](user_name="bjensen")
    before[EnterpriseUser] = EnterpriseUser(department="Tour")
    after = User[EnterpriseUser](user_name="bjensen")
    after.EnterpriseUser = None

    patch = PatchOp.build_from(before, after)

    assert paths(patch) == [
        ("remove", "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User")
    ]


def test_a_sub_attribute_of_an_extension_is_targeted_by_its_own_path():
    """The dotted path of a complex attribute carries its extension URN."""
    before = User[EnterpriseUser](user_name="bjensen")
    before[EnterpriseUser] = EnterpriseUser(manager=Manager(value="jan"))
    after = User[EnterpriseUser](user_name="bjensen")
    after[EnterpriseUser] = EnterpriseUser(manager=Manager(value="ada"))

    patch = PatchOp.build_from(before, after)

    assert paths(patch) == [
        (
            "replace",
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:manager.value",
        )
    ]


def test_a_read_only_sub_attribute_is_never_patched():
    """RFC7643 §4.3 declares manager.displayName read-only, where manager.value is writable."""
    before = User[EnterpriseUser](user_name="bjensen")
    before[EnterpriseUser] = EnterpriseUser(manager=Manager(display_name="Jan"))
    after = User[EnterpriseUser](user_name="bjensen")
    after[EnterpriseUser] = EnterpriseUser(manager=Manager(display_name="Ada"))

    assert PatchOp.build_from(before, after) is None


def enterprise(**kwargs):
    """Return a user carrying an enterprise extension."""
    user = User[EnterpriseUser](user_name="bjensen")
    user[EnterpriseUser] = EnterpriseUser(**kwargs)
    return user


@pytest.mark.parametrize(
    ("before", "after"),
    [
        pytest.param(
            User(nick_name="Barb"), User(nick_name="Babs"), id="changed-attribute"
        ),
        pytest.param(User(title="CEO"), User(title=None), id="cleared-attribute"),
        pytest.param(
            User(name=Name(given_name="Barbara", family_name="Jensen")),
            User(name=Name(given_name="Babs")),
            id="changed-sub-attribute",
        ),
        pytest.param(
            User(name=Name(given_name="Barbara")), User(name=None), id="cleared-complex"
        ),
        pytest.param(
            User(user_name="bjensen"),
            User(user_name="bjensen", name=Name(given_name="Babs")),
            id="created-complex",
        ),
        pytest.param(
            User(emails=[Email(value="barb@example.com")]),
            User(emails=[Email(value="babs@example.com")]),
            id="changed-collection",
        ),
        pytest.param(
            User(emails=[Email(value="barb@example.com")]),
            User(emails=[]),
            id="emptied-collection",
        ),
        pytest.param(
            enterprise(department="Tour"),
            enterprise(department="Chess"),
            id="changed-extension-attribute",
        ),
        pytest.param(
            User[EnterpriseUser](user_name="bjensen"),
            enterprise(department="Tour"),
            id="created-extension",
        ),
        pytest.param(
            User(nick_name="Barb", name=Name(given_name="Barbara"), title="CEO"),
            User(nick_name="Babs", name=Name(given_name="Babs"), title=None),
            id="several-attributes-at-once",
        ),
    ],
)
def test_applying_a_built_patch_settles_the_difference(before, after):
    """The property the whole builder answers to: whatever the wanted state asserts, the peer holds it once the patch is applied."""
    patched = before.model_copy(deep=True)
    patch = PatchOp.build_from(before, after)

    assert patch.patch(patched) is True
    assert PatchOp.build_from(patched, after) is None


def test_applying_a_built_patch_preserves_what_the_wanted_state_ignores():
    """The attributes the wanted state never names survive the modification."""
    before = User(
        user_name="bjensen",
        title="CEO",
        emails=[Email(value="barb@example.com", type="work", primary=True)],
    )
    after = User(user_name="bjensen", nick_name="Babs")
    patched = before.model_copy(deep=True)

    PatchOp.build_from(before, after).patch(patched)

    assert patched.title == "CEO"
    assert patched.emails[0].type == "work"
    assert patched.nick_name == "Babs"


def test_a_built_patch_travels_as_a_patch_request():
    """The patch a diff builds serializes into a PATCH request payload."""
    before = enterprise(department="Tour")
    after = User[EnterpriseUser](user_name="bjensen", name=Name(given_name="Babs"))
    after[EnterpriseUser] = EnterpriseUser(department="Chess")

    patch = PatchOp.build_from(before, after)
    payload = patch.model_dump(scim_ctx=Context.RESOURCE_PATCH_REQUEST)

    assert payload == {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [
            {"op": "replace", "path": "name.givenName", "value": "Babs"},
            {
                "op": "replace",
                "path": "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:department",
                "value": "Chess",
            },
        ],
    }
    assert PatchOp[User[EnterpriseUser]].model_validate(
        payload, scim_ctx=Context.RESOURCE_PATCH_REQUEST
    )
