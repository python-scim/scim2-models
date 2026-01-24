from typing import TypeVar

import pytest
from pydantic import Field
from pydantic import ValidationError

from scim2_models import Group
from scim2_models import GroupMember
from scim2_models import InvalidPathException
from scim2_models import PatchOp
from scim2_models import PatchOperation
from scim2_models import User
from scim2_models.resources.enterprise_user import EnterpriseUser
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

    patch1 = PatchOp[User](
        operations=[
            PatchOperation[User](
                op=PatchOperation.Op.replace_,
                path="urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:employeeNumber",
                value="54321",
            )
        ]
    )
    result = patch1.patch(user)
    assert result is True
    assert user[EnterpriseUser].employee_number == "54321"

    patch2 = PatchOp[User](
        operations=[
            PatchOperation[User](
                op=PatchOperation.Op.add,
                path="urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:organization",
                value="ACME Corp",
            )
        ]
    )
    result = patch2.patch(user)
    assert result is True
    assert user[EnterpriseUser].organization == "ACME Corp"

    patch3 = PatchOp[User](
        operations=[
            PatchOperation[User](
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

    patch1 = PatchOp[User](
        operations=[
            PatchOperation[User](
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

    patch2 = PatchOp[User](
        operations=[
            PatchOperation[User](
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

    patch3 = PatchOp[User](
        operations=[
            PatchOperation[User](
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
    patch = PatchOp[User](
        operations=[
            PatchOperation[User](
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
    """Test invalidPath error for non-existent extension attributes.

    :rfc:`RFC7644 §3.5.2 <7644#section-3.5.2>`: invalidPath errors occur when
    the path references an attribute that doesn't exist in the schema.
    """
    user = User[EnterpriseUser].model_validate({"userName": "test.user"})

    patch1 = PatchOp[User](
        operations=[
            PatchOperation[User](
                op=PatchOperation.Op.add,
                path="urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:invalidAttribute",
                value="test",
            )
        ]
    )
    with pytest.raises(InvalidPathException):
        patch1.patch(user)

    patch2 = PatchOp[User](
        operations=[
            PatchOperation[User](
                op=PatchOperation.Op.add,
                path="urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:manager.invalidField",
                value="test",
            )
        ]
    )
    with pytest.raises(InvalidPathException):
        patch2.patch(user)


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


def test_values_match_integration():
    """Test values matching through remove operation with BaseModel objects."""
    # Test removing existing member (values should match)
    member1 = GroupMember(value="123", display="Test User")
    group = Group(members=[member1])

    # Remove with exact matching dict
    patch_op = PatchOp[Group](
        operations=[
            PatchOperation[Group](
                op=PatchOperation.Op.remove,
                path="members",
                value={"value": "123", "display": "Test User"},
            )
        ]
    )
    result = patch_op.patch(group)
    assert result is True
    assert group.members is None or len(group.members) == 0

    # Test removing non-existing member (values should not match)
    member2 = GroupMember(value="456", display="Other User")
    group = Group(members=[member2])

    patch_op = PatchOp[Group](
        operations=[
            PatchOperation[Group](
                op=PatchOperation.Op.remove,
                path="members",
                value={"value": "123", "display": "Test User"},
            )
        ]
    )
    result = patch_op.patch(group)
    assert result is False
    assert len(group.members) == 1


def test_generic_patchop_rejects_union():
    """Test that PatchOp rejects Union types."""
    with pytest.raises(
        TypeError, match="PatchOp type parameter must be a concrete Resource subclass"
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


def test_create_parent_object_return_none():
    """Test _create_parent_object returns None when field type is not a class."""
    T = TypeVar("T")

    class TestResourceTypeVar(Resource):
        schemas: list[str] = Field(default=["urn:test:TestResource"])
        # TypeVar is not a class, so _create_parent_object should return None
        typevar_field: T = None

    user = TestResourceTypeVar()
    patch = PatchOp[TestResourceTypeVar](
        operations=[
            PatchOperation[TestResourceTypeVar](
                op=PatchOperation.Op.add, path="typevarField.subfield", value="test"
            )
        ]
    )

    # This should fail gracefully - _create_parent_object returns None,
    # so the operation should return False
    result = patch.patch(user)
    assert result is False


def test_complex_object_creation_and_basemodel_matching():
    """Test automatic complex object creation and BaseModel value matching in lists."""
    # Test creation of parent object for valid complex field
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

    # Test BaseModel conversion in values matching
    group = Group(members=[GroupMember(value="123", display="Test")])
    patch = PatchOp[Group](
        operations=[
            PatchOperation[Group](
                op=PatchOperation.Op.remove,
                path="members",
                value=GroupMember(value="123", display="Test"),
            )
        ]
    )

    result = patch.patch(group)
    assert result is True


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

    patch = PatchOp[User](
        operations=[
            PatchOperation[User](
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


def test_patch_schema_path_with_invalid_value_type():
    """Test PATCH with schema URN path and invalid value type (non-dict)."""
    user = User(user_name="test")

    patch = PatchOp[User](
        operations=[
            PatchOperation[User](
                op=PatchOperation.Op.add,
                path="urn:ietf:params:scim:schemas:core:2.0:User",
                value="invalid string value",
            )
        ]
    )

    with pytest.raises(InvalidPathException):
        patch.patch(user)


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

    patch = PatchOp[User](
        operations=[
            PatchOperation[User](
                op=PatchOperation.Op.remove,
                path="urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
            )
        ]
    )

    result = patch.patch(user)
    assert result is True
    assert user[EnterpriseUser] is None
