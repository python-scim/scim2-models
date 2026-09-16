"""The resource a failing patch was applied to is left as it was."""

from typing import Annotated

import pytest

from scim2_models import URN
from scim2_models import Email
from scim2_models import EnterpriseUser
from scim2_models import MutabilityException
from scim2_models import NoTargetException
from scim2_models import PatchOp
from scim2_models import PatchOperation
from scim2_models import ScimPolicy
from scim2_models import User
from scim2_models.annotations import Mutability
from scim2_models.resources.resource import Resource


def test_an_operation_failing_on_a_selection_undoes_the_ones_before_it():
    """A peer sends the operations it wants applied together, not one by one."""
    user = User(user_name="bjensen", title="Engineer")
    patch = PatchOp[User](
        operations=[
            PatchOperation[User](
                op=PatchOperation.Op.replace_, path="title", value="Manager"
            ),
            PatchOperation[User](
                op=PatchOperation.Op.replace_,
                path='emails[type eq "work"].value',
                value="bjensen@example.com",
            ),
        ]
    )

    with pytest.raises(NoTargetException):
        patch.patch(user)

    assert user.title == "Engineer"


def test_an_operation_failing_on_mutability_undoes_the_ones_before_it():
    """An immutable attribute already holding a value is only known from the state."""

    class Dummy(Resource):
        __schema__ = URN("urn:test:TestResource")

        mutable: str
        immutable: Annotated[str, Mutability.immutable]

    resource = Dummy.model_construct(mutable="before", immutable="original")
    patch = PatchOp[Dummy](
        operations=[
            PatchOperation[Dummy](
                op=PatchOperation.Op.replace_, path="mutable", value="after"
            ),
            PatchOperation[Dummy](
                op=PatchOperation.Op.replace_, path="immutable", value="new_value"
            ),
        ]
    )

    with pytest.raises(MutabilityException):
        patch.patch(resource)

    assert resource.mutable == "before"
    assert resource.immutable == "original"


def test_an_operation_failing_on_primary_undoes_the_ones_before_it():
    """Two values claiming to be primary are only counted once the write went through."""
    user = User(
        user_name="bjensen",
        title="Engineer",
        emails=[Email(value="a@example.com"), Email(value="b@example.com")],
    )
    patch = PatchOp[User](
        operations=[
            PatchOperation[User](
                op=PatchOperation.Op.replace_, path="title", value="Manager"
            ),
            PatchOperation[User](
                op=PatchOperation.Op.replace_,
                path="emails",
                value=[
                    {"value": "a@example.com", "primary": True},
                    {"value": "b@example.com", "primary": True},
                ],
            ),
        ]
    )

    with pytest.raises(Exception, match="Multiple values marked as primary"):
        patch.patch(user)

    assert user.title == "Engineer"
    assert [email.primary for email in user.emails] == [None, None]


def test_a_failing_patch_leaves_the_attributes_it_never_reached_alone():
    """Restoring the resource may not turn an unset attribute into a set one."""
    user = User(user_name="bjensen")
    patch = PatchOp[User](
        operations=[
            PatchOperation[User](
                op=PatchOperation.Op.replace_,
                path='emails[type eq "work"].value',
                value="bjensen@example.com",
            ),
        ]
    )

    with pytest.raises(NoTargetException):
        patch.patch(user)

    assert user.model_dump() == {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        "userName": "bjensen",
    }


def test_the_caller_keeps_the_object_it_passed():
    """A server writes back the resource it read, so the patch may not swap it."""
    user = User(user_name="bjensen", emails=[Email(type="work", value="a@example.com")])
    patch = PatchOp[User](
        operations=[
            PatchOperation[User](
                op=PatchOperation.Op.replace_,
                path='emails[type eq "work"].value',
                value="b@example.com",
            )
        ]
    )
    same = user

    assert patch.patch(user) is True
    assert same is user
    assert user.emails[0].value == "b@example.com"


def test_a_patched_extension_survives_the_restoration():
    """An extension is held apart from the fields the resource declares."""
    user = User[EnterpriseUser](
        user_name="bjensen",
        **{
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": EnterpriseUser(
                department="Tour Operations"
            )
        },
    )
    patch = PatchOp[User[EnterpriseUser]](
        operations=[
            PatchOperation[User[EnterpriseUser]](
                op=PatchOperation.Op.replace_,
                path="urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:department",
                value="Sales",
            )
        ]
    )

    assert patch.patch(user) is True
    assert user[EnterpriseUser].department == "Sales"


def test_an_unknown_attribute_survives_the_restoration():
    """What a lenient policy set aside is held outside the fields, and is still reported."""
    user = User.model_validate(
        {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "userName": "bjensen",
            "unknownAttr": "x",
        },
        scim_policy=ScimPolicy(unknown=ScimPolicy.Unknown.ignore),
    )
    patch = PatchOp[User](
        operations=[
            PatchOperation[User](
                op=PatchOperation.Op.replace_, path="title", value="Manager"
            )
        ]
    )

    assert patch.patch(user) is True
    assert user.unknown_attributes == {"unknownAttr": "x"}
