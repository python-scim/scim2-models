from typing import Annotated
from typing import TypeVar

import pytest
from pydantic import ValidationError

from scim2_models import URN
from scim2_models import Group
from scim2_models import InvalidValueException
from scim2_models import Mutability
from scim2_models import MutabilityException
from scim2_models import PatchOp
from scim2_models import PatchOperation
from scim2_models import ScimPolicy
from scim2_models import User
from scim2_models.context import Context
from scim2_models.resources.enterprise_user import EnterpriseUser
from scim2_models.resources.resource import Extension
from scim2_models.resources.resource import Resource


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

    patch1 = PatchOp[User[EnterpriseUser]](
        operations=[
            PatchOperation[User[EnterpriseUser]](
                op=PatchOperation.Op.replace_,
                path="urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:employeeNumber",
                value="54321",
            )
        ]
    )
    result = patch1.patch(user)
    assert result is True
    assert user[EnterpriseUser].employee_number == "54321"

    patch2 = PatchOp[User[EnterpriseUser]](
        operations=[
            PatchOperation[User[EnterpriseUser]](
                op=PatchOperation.Op.add,
                path="urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:organization",
                value="ACME Corp",
            )
        ]
    )
    result = patch2.patch(user)
    assert result is True
    assert user[EnterpriseUser].organization == "ACME Corp"

    patch3 = PatchOp[User[EnterpriseUser]](
        operations=[
            PatchOperation[User[EnterpriseUser]](
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

    patch1 = PatchOp[User[EnterpriseUser]](
        operations=[
            PatchOperation[User[EnterpriseUser]](
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

    patch2 = PatchOp[User[EnterpriseUser]](
        operations=[
            PatchOperation[User[EnterpriseUser]](
                op=PatchOperation.Op.replace_,
                path="urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:manager",
                value={
                    "value": "super-manager-789",
                    "displayName": "John Smith",
                    "$ref": "https://example.com/Users/super-manager-789",
                },
            )
        ]
    )
    result = patch2.patch(user)
    assert result is True
    assert user[EnterpriseUser].manager.value == "super-manager-789"
    assert user[EnterpriseUser].manager.display_name == "John Smith"

    patch3 = PatchOp[User[EnterpriseUser]](
        operations=[
            PatchOperation[User[EnterpriseUser]](
                op=PatchOperation.Op.remove,
                path="urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:manager",
            )
        ]
    )
    result = patch3.patch(user)
    assert result is True
    assert user[EnterpriseUser].manager is None


def test_patch_operation_extension_mutability_handled_by_model():
    """Test that extension mutability is handled by model validation.

    Note: Mutability validation for extensions is now handled at the model level
    during PatchOp validation, not during patch execution.
    """
    user = User[EnterpriseUser].model_validate(
        {
            "userName": "test.user",
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
                "manager": {"value": "manager-123", "displayName": "John Smith"}
            },
        }
    )

    # This operation would fail during model validation for mutability,
    # but patch method assumes operations are already validated
    patch = PatchOp[User[EnterpriseUser]](
        operations=[
            PatchOperation[User[EnterpriseUser]](
                op=PatchOperation.Op.replace_,
                path="urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:employeeNumber",
                value="12345",
            )
        ]
    )
    result = patch.patch(user)
    assert result is True
    assert user[EnterpriseUser].employee_number == "12345"


def test_patch_operation_extension_invalid_path_error():
    """An attribute the extension does not declare is refused, and so is its sub-attribute."""
    with pytest.raises(ValidationError) as raised:
        PatchOp[User[EnterpriseUser]](
            operations=[
                PatchOperation[User[EnterpriseUser]](
                    op=PatchOperation.Op.add,
                    path="urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:invalidAttribute",
                    value="test",
                )
            ]
        )
    assert raised.value.errors()[0]["type"] == "scim_invalidPath"

    with pytest.raises(ValidationError) as raised:
        PatchOp[User[EnterpriseUser]](
            operations=[
                PatchOperation[User[EnterpriseUser]](
                    op=PatchOperation.Op.add,
                    path="urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:manager.invalidField",
                    value="test",
                )
            ]
        )
    assert raised.value.errors()[0]["type"] == "scim_invalidPath"


def test_urn_parsing_errors():
    """Test URN parsing errors for malformed URNs."""
    with pytest.raises(ValidationError, match="The path is not a valid URN"):
        PatchOp[User](
            operations=[
                PatchOperation[User](
                    op=PatchOperation.Op.add,
                    path="urn:malformed:incomplete",
                    value="test",
                )
            ]
        )


def test_generic_patchop_rejects_union():
    """Test that PatchOp rejects Union types."""
    with pytest.raises(
        TypeError, match="PatchOp type parameter must name one resource type"
    ):
        PatchOp[User | Group]


def test_generic_patchop_with_single_type():
    """Test that generic PatchOp works with single types."""
    patch_data = {
        "operations": [{"op": "add", "path": "userName", "value": "test.user"}]
    }

    # This should not trigger the union-specific metaclass code
    patch = PatchOp[User].model_validate(patch_data)
    assert patch.operations[0].value == "test.user"


def test_patch_a_subattribute_of_an_unresolved_generic_attribute():
    """An attribute declared as a type variable holds no sub-attribute."""
    T = TypeVar("T")

    class TestResourceTypeVar(Resource):
        __schema__ = URN("urn:test:TestResource")

        typevar_field: T = None

    with pytest.raises(ValidationError) as raised:
        PatchOp[TestResourceTypeVar](
            operations=[
                PatchOperation[TestResourceTypeVar](
                    op=PatchOperation.Op.add, path="typevarField.subfield", value="test"
                )
            ]
        )

    assert raised.value.errors()[0]["type"] == "scim_invalidPath"


def test_add_creates_the_parent_of_a_complex_attribute():
    """Adding a sub-attribute assigns the complex attribute holding it."""
    user = User()
    patch = PatchOp[User](
        operations=[
            PatchOperation[User](
                op=PatchOperation.Op.add, path="name.givenName", value="John"
            )
        ]
    )

    result = patch.patch(user)
    assert result is True
    assert user.name.given_name == "John"


def test_patch_extension_schema_path_without_attribute():
    """Test PATCH with extension schema URN as path (no specific attribute)."""
    user = User[EnterpriseUser](
        user_name="test",
        schemas=[
            "urn:ietf:params:scim:schemas:core:2.0:User",
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
        ],
    )
    user[EnterpriseUser] = EnterpriseUser()

    patch = PatchOp[User[EnterpriseUser]](
        operations=[
            PatchOperation[User[EnterpriseUser]](
                op=PatchOperation.Op.add,
                path="urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
                value={
                    "costCenter": "Engineering",
                    "department": "IT",
                    "employeeNumber": "12345",
                },
            )
        ]
    )

    result = patch.patch(user)
    assert result is True
    assert user[EnterpriseUser].cost_center == "Engineering"


def test_patch_main_schema_path_without_attribute():
    """Test PATCH with main schema URN as path (no specific attribute)."""
    user = User(user_name="original")

    patch = PatchOp[User](
        operations=[
            PatchOperation[User](
                op=PatchOperation.Op.add,
                path="urn:ietf:params:scim:schemas:core:2.0:User",
                value={
                    "displayName": "Updated Name",
                    "nickName": "Nick",
                    "title": "Manager",
                },
            )
        ]
    )

    result = patch.patch(user)
    assert result is True
    assert user.display_name == "Updated Name"
    assert user.nick_name == "Nick"
    assert user.title == "Manager"


def test_patch_delete_extension_root():
    """Test PATCH remove operation targeting the root of an extension."""
    user = User[EnterpriseUser].model_validate(
        {
            "userName": "test.user",
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
                "employeeNumber": "12345",
                "costCenter": "Engineering",
                "department": "IT",
                "manager": {"value": "manager-123", "displayName": "John Smith"},
            },
        }
    )

    assert user[EnterpriseUser] is not None
    assert user[EnterpriseUser].employee_number == "12345"
    assert user[EnterpriseUser].cost_center == "Engineering"

    patch = PatchOp[User[EnterpriseUser]](
        operations=[
            PatchOperation[User[EnterpriseUser]](
                op=PatchOperation.Op.remove,
                path="urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
            )
        ]
    )

    result = patch.patch(user)
    assert result is True
    assert user[EnterpriseUser] is None


MANAGER = "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:manager"


def _managed_user():
    return User[EnterpriseUser].model_validate(
        {
            "userName": "jane.doe",
            MANAGER.rsplit(":", 1)[0]: {
                "manager": {"value": "manager-123", "displayName": "John Smith"}
            },
        }
    )


def test_a_path_to_a_read_only_sub_attribute_is_refused():
    """RFC7644 §3.5.2 forbids changing a read-only attribute, and this path points to one."""
    with pytest.raises(ValidationError) as raised:
        PatchOp[User[EnterpriseUser]].model_validate(
            {
                "Operations": [
                    {
                        "op": "replace",
                        "path": f"{MANAGER}.displayName",
                        "value": "Alice",
                    }
                ]
            }
        )

    assert raised.value.errors()[0]["type"] == "scim_mutability"


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (MANAGER, {"value": "manager-456", "displayName": "Alice"}),
        (None, {MANAGER.rsplit(":", 1)[0]: {"manager": {"displayName": "Alice"}}}),
    ],
)
def test_a_value_changing_a_read_only_sub_attribute_is_refused(path, value):
    """A read-only sub-attribute in a value is rejected when it would change."""
    user = _managed_user()
    operation = {"op": "replace", "value": value}
    if path is not None:
        operation["path"] = path
    patch = PatchOp[User[EnterpriseUser]].model_validate({"Operations": [operation]})

    with pytest.raises(MutabilityException):
        patch.patch(user)

    assert user[EnterpriseUser].manager.display_name == "John Smith"


def test_a_complex_attribute_holding_a_read_only_sub_attribute_may_be_removed():
    """Removing an attribute also removes its read-only sub-attributes."""
    user = _managed_user()
    patch = PatchOp[User[EnterpriseUser]].model_validate(
        {"Operations": [{"op": "remove", "path": MANAGER}]}
    )

    assert patch.patch(user)
    assert user[EnterpriseUser].manager is None


def test_a_new_complex_value_cannot_assign_a_read_only_sub_attribute():
    """A client cannot set a read-only sub-attribute, even on an attribute that had no value."""
    user = User[EnterpriseUser](user_name="jane.doe")
    patch = PatchOp[User[EnterpriseUser]].model_validate(
        {
            "Operations": [
                {
                    "op": "add",
                    "path": MANAGER,
                    "value": {"value": "manager-123", "displayName": "John Smith"},
                }
            ]
        }
    )

    with pytest.raises(MutabilityException):
        patch.patch(user)


ENTERPRISE_URN = "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"


def _keyed_patch(op, value, **kwargs):
    return PatchOp[User[EnterpriseUser]].model_validate(
        {"Operations": [{"op": op, "value": value}]},
        scim_ctx=Context.RESOURCE_PATCH_REQUEST,
        **kwargs,
    )


def _keyed_user():
    user = User[EnterpriseUser](user_name="bjensen", name={"familyName": "Jensen"})
    user[EnterpriseUser] = EnterpriseUser(
        manager={"value": "m1", "displayName": "Boss"}
    )
    return user


@pytest.mark.parametrize("op", ["add", "replace"])
def test_a_dotted_key_writes_its_sub_attribute(op):
    """Entra uses paths as keys in a value without a path, and no attribute name looks like a path."""
    user = _keyed_user()

    assert _keyed_patch(op, {"name.givenName": "Barbara"}).patch(user)
    assert user.name.given_name == "Barbara"
    assert user.name.family_name == "Jensen"


@pytest.mark.parametrize("op", ["add", "replace"])
def test_a_urn_qualified_key_writes_its_extension_attribute(op):
    """The Microsoft SCIM Validator uses the full URN of extension attributes as keys."""
    user = _keyed_user()

    assert _keyed_patch(op, {f"{ENTERPRISE_URN}:employeeNumber": "42"}).patch(user)
    assert user[EnterpriseUser].employee_number == "42"


def test_a_urn_qualified_key_merges_into_its_complex_attribute():
    """A complex attribute written through a URN key keeps the sub-attributes its value leaves out."""
    user = _keyed_user()

    assert _keyed_patch(
        "replace", {f"{ENTERPRISE_URN}:manager": {"value": "m2"}}
    ).patch(user)
    assert user[EnterpriseUser].manager.value == "m2"
    assert user[EnterpriseUser].manager.display_name == "Boss"


def test_a_dotted_key_inside_an_extension_is_read_from_the_extension():
    """A key of the value an extension takes is a path relative to that extension."""
    user = _keyed_user()

    assert _keyed_patch("replace", {ENTERPRISE_URN: {"manager.value": "m2"}}).patch(
        user
    )
    assert user[EnterpriseUser].manager.value == "m2"


def test_a_key_qualified_by_the_resource_urn_writes_the_core_attribute():
    """The core schema URN qualifies the attributes of the resource as well."""
    user = _keyed_user()

    assert _keyed_patch(
        "replace", {"urn:ietf:params:scim:schemas:core:2.0:User:nickName": "Babs"}
    ).patch(user)
    assert user.nick_name == "Babs"


@pytest.mark.parametrize(
    "key",
    [
        pytest.param("name.nickName", id="undeclared sub-attribute"),
        pytest.param("urn:example:2.0:Unknown:attr", id="undeclared extension"),
        pytest.param('emails[type eq "work"].value', id="filter"),
        pytest.param("display name", id="malformed"),
    ],
)
def test_a_key_spelling_no_declared_attribute_path_is_refused(key):
    """A key that is neither an attribute name nor a declared path is undeclared."""
    with pytest.raises(ValidationError) as raised:
        _keyed_patch("replace", {key: "x"})

    assert raised.value.errors()[0]["type"] == "scim_invalidValue"


def test_a_key_spelling_no_declared_attribute_path_is_dropped_under_a_tolerant_policy():
    """The unknown policy handles such a key like any undeclared attribute."""
    user = _keyed_user()
    tolerant = ScimPolicy(unknown=ScimPolicy.Unknown.ignore)
    patch = _keyed_patch("replace", {"name.nickName": "x"}, scim_policy=tolerant)

    assert not patch.patch(user, scim_policy=tolerant)


def test_a_dotted_key_cannot_change_a_read_only_sub_attribute():
    """A path used as a key has the same constraints as in the path field."""
    user = _keyed_user()
    patch = _keyed_patch("replace", {f"{ENTERPRISE_URN}:manager.displayName": "Other"})

    with pytest.raises(MutabilityException):
        patch.patch(user)
    assert user[EnterpriseUser].manager.display_name == "Boss"


def test_a_qualified_key_cannot_unassign_a_required_attribute():
    """Unassigning a required attribute is rejected however the key spells it."""
    with pytest.raises(ValidationError) as raised:
        _keyed_patch(
            "replace", {"urn:ietf:params:scim:schemas:core:2.0:User:userName": None}
        )

    assert raised.value.errors()[0]["type"] == "scim_mutability"


ENTERPRISE = "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"
CORE = "urn:ietf:params:scim:schemas:core:2.0:User"


def _enterprise_user_from_payload():
    return User[EnterpriseUser].model_validate(
        {
            "schemas": [CORE, ENTERPRISE],
            "userName": "bjensen",
            ENTERPRISE: {"employeeNumber": "1"},
        }
    )


def _enterprise_user_built_in_python():
    user = User[EnterpriseUser](user_name="bjensen")
    user[EnterpriseUser] = EnterpriseUser(employee_number="1")
    return user


@pytest.mark.parametrize(
    "build", [_enterprise_user_from_payload, _enterprise_user_built_in_python]
)
@pytest.mark.parametrize(
    "path", [f'schemas[value eq "{ENTERPRISE}"]', f'schemas eq "{ENTERPRISE}"']
)
def test_removing_an_extension_schema_removes_the_extension(build, path):
    """Per RFC7643 §3, 'schemas' lists the schemas of the attributes present."""
    user = build()
    patch = PatchOp[User[EnterpriseUser]](
        operations=[PatchOperation(op="remove", path=path)]
    )
    assert patch.patch(user) is True
    assert user[EnterpriseUser] is None
    assert user.model_dump()["schemas"] == [CORE]


def test_replacing_schemas_without_an_extension_removes_the_extension():
    """A replace that leaves an extension schema out removes the extension."""
    user = _enterprise_user_from_payload()
    patch = PatchOp[User[EnterpriseUser]](
        operations=[PatchOperation(op="replace", path="schemas", value=[CORE])]
    )
    assert patch.patch(user) is True
    assert user[EnterpriseUser] is None


def test_removing_the_schema_of_an_absent_extension_changes_nothing():
    """A resource without the extension does not list its schema."""
    user = User[EnterpriseUser](user_name="bjensen")
    patch = PatchOp[User[EnterpriseUser]](
        operations=[
            PatchOperation(op="remove", path=f'schemas[value eq "{ENTERPRISE}"]')
        ]
    )
    assert patch.patch(user) is False


def test_removing_the_schema_of_the_resource_is_refused():
    """The resource keeps its own schema, and the failed patch changes nothing."""
    user = _enterprise_user_from_payload()
    patch = PatchOp[User[EnterpriseUser]](
        operations=[PatchOperation(op="remove", path=f'schemas[value eq "{CORE}"]')]
    )
    with pytest.raises(InvalidValueException):
        patch.patch(user)
    assert user[EnterpriseUser].employee_number == "1"


class BadgeExtension(Extension):
    __schema__ = URN("urn:example:extensions:2.0:Badge")

    badge: Annotated[str | None, Mutability.immutable] = None


def test_removing_an_extension_schema_keeps_its_assigned_immutable_attributes():
    """Removing an extension through 'schemas' follows the mutability rules of a remove."""
    user = User[BadgeExtension](user_name="bjensen")
    user[BadgeExtension] = BadgeExtension(badge="42")
    patch = PatchOp[User[BadgeExtension]](
        operations=[
            PatchOperation(
                op="remove", path='schemas[value eq "urn:example:extensions:2.0:Badge"]'
            )
        ]
    )
    with pytest.raises(MutabilityException):
        patch.patch(user)
    assert user[BadgeExtension].badge == "42"
