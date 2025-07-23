from typing import TypeVar
from typing import Union

import pytest
from pydantic import ValidationError

from scim2_models import Group
from scim2_models import PatchOp
from scim2_models import PatchOperation
from scim2_models import User
from scim2_models.base import Context
from scim2_models.resources.resource import Resource


def test_patch_op_without_type_parameter():
    """Test that PatchOp cannot be instantiated without a type parameter."""
    with pytest.raises(TypeError, match="PatchOp requires a type parameter"):
        PatchOp(operations=[{"op": "replace", "path": "userName", "value": "test"}])


def test_patch_op_with_resource_type():
    """Test that PatchOp[Resource] is rejected."""
    with pytest.raises(
        TypeError,
        match="PatchOp requires a concrete Resource subclass, not Resource itself",
    ):
        PatchOp[Resource]


def test_patch_op_with_invalid_type():
    """Test that PatchOp with invalid types like str is rejected."""
    with pytest.raises(
        TypeError, match="PatchOp type parameter must be a concrete Resource subclass"
    ):
        PatchOp[str]


def test_patch_op_union_types_not_supported():
    """Test that PatchOp with Union types are rejected."""
    with pytest.raises(
        TypeError, match="PatchOp type parameter must be a concrete Resource subclass"
    ):
        PatchOp[Union[User, Group]]


def test_validate_patchop_case_insensitivity():
    """Validate that a patch operation's Op declaration is case-insensitive.

    Note: While :rfc:`RFC7644 §3.4.2.2 <7644#section-3.4.2.2>` specifies case insensitivity
    for attribute names and operators in filters, this implementation extends this principle
    to PATCH operation names for Microsoft Entra compatibility.
    """
    assert PatchOp[User].model_validate(
        {
            "operations": [
                {"op": "Replace", "path": "userName", "value": "Rivard"},
                {"op": "ADD", "path": "userName", "value": "Rivard"},
                {"op": "ReMove", "path": "userName", "value": "Rivard"},
            ],
        },
    ) == PatchOp[User](
        operations=[
            PatchOperation(
                op=PatchOperation.Op.replace_, path="userName", value="Rivard"
            ),
            PatchOperation(op=PatchOperation.Op.add, path="userName", value="Rivard"),
            PatchOperation(
                op=PatchOperation.Op.remove, path="userName", value="Rivard"
            ),
        ]
    )
    with pytest.raises(
        ValidationError,
        match="1 validation error for PatchOp",
    ):
        PatchOp[User].model_validate(
            {
                "operations": [{"op": 42, "path": "userName", "value": "Rivard"}],
            },
        )


def test_path_required_for_remove_operations():
    """Test that path is required for remove operations.

    :rfc:`RFC7644 §3.5.2.2 <7644#section-3.5.2.2>`: "If 'path' is unspecified,
    the operation fails with HTTP status code 400 and a 'scimType' error code of 'noTarget'."
    """
    PatchOp[User].model_validate(
        {
            "operations": [
                {"op": "replace", "value": "foobar"},
            ],
        },
        context={"scim": Context.RESOURCE_PATCH_REQUEST},
    )
    PatchOp[User].model_validate(
        {
            "operations": [
                {"op": "add", "value": "foobar"},
            ],
        },
        context={"scim": Context.RESOURCE_PATCH_REQUEST},
    )

    # Validation now happens during model validation
    with pytest.raises(ValidationError, match="path.*invalid"):
        PatchOp[User].model_validate(
            {
                "operations": [
                    {"op": "remove", "value": "foobar"},
                ],
            },
            context={"scim": Context.RESOURCE_PATCH_REQUEST},
        )


def test_value_required_for_add_operations():
    """Test that value is required for add operations.

    :rfc:`RFC7644 §3.5.2.1 <7644#section-3.5.2.1>`: "The operation MUST contain a 'value'
    member whose content specifies the value to be added."
    """
    PatchOp[User].model_validate(
        {
            "operations": [
                {"op": "replace", "path": "foobar"},
            ],
        },
        context={"scim": Context.RESOURCE_PATCH_REQUEST},
    )
    with pytest.raises(ValidationError):
        PatchOp[User].model_validate(
            {
                "operations": [
                    {"op": "add", "path": "foobar"},
                ],
            },
            context={"scim": Context.RESOURCE_PATCH_REQUEST},
        )

    PatchOp[User].model_validate(
        {
            "operations": [
                {"op": "remove", "path": "foobar"},
            ],
        },
        context={"scim": Context.RESOURCE_PATCH_REQUEST},
    )


def test_patch_operation_validation_contexts():
    """Test RFC7644 validation behavior in different contexts.

    Validates that operations are only validated in PATCH request contexts,
    following :rfc:`RFC7644 §3.5.2 <7644#section-3.5.2>` validation requirements.
    """
    with pytest.raises(ValidationError, match="path"):
        PatchOperation.model_validate(
            {"op": "add", "path": "   ", "value": "test"},
            context={"scim": Context.RESOURCE_PATCH_REQUEST},
        )

    # Validation for missing path in remove operations now happens during model validation
    with pytest.raises(ValidationError, match="path.*invalid"):
        PatchOperation.model_validate(
            {"op": "remove"},
            context={"scim": Context.RESOURCE_PATCH_REQUEST},
        )

    with pytest.raises(ValidationError, match="required value was missing"):
        PatchOperation.model_validate(
            {"op": "add", "path": "test"},
            context={"scim": Context.RESOURCE_PATCH_REQUEST},
        )

    operation1 = PatchOperation.model_validate(
        {"op": "add", "path": "   ", "value": "test"}
    )
    assert operation1.path == "   "

    operation2 = PatchOperation.model_validate({"op": "remove"})
    assert operation2.path is None

    operation3 = PatchOperation.model_validate({"op": "add", "path": "test"})
    assert operation3.value is None


def test_validate_mutability_readonly_error():
    """Test mutability validation error for readOnly attributes."""
    # Test add operation on readOnly field
    with pytest.raises(ValidationError, match="mutability"):
        PatchOp[User].model_validate(
            {"operations": [{"op": "add", "path": "id", "value": "new-id"}]},
            context={"scim": Context.RESOURCE_PATCH_REQUEST},
        )

    # Test replace operation on readOnly field
    with pytest.raises(ValidationError, match="mutability"):
        PatchOp[User].model_validate(
            {"operations": [{"op": "replace", "path": "id", "value": "new-id"}]},
            context={"scim": Context.RESOURCE_PATCH_REQUEST},
        )


def test_validate_mutability_immutable_error():
    """Test mutability validation error for immutable attributes."""
    # Test replace operation on immutable field within groups complex attribute
    with pytest.raises(ValidationError, match="mutability"):
        PatchOp[User].model_validate(
            {
                "operations": [
                    {
                        "op": "replace",
                        "path": "groups.value",
                        "value": "new-group-id",
                    }
                ]
            },
            context={"scim": Context.RESOURCE_PATCH_REQUEST},
        )


def test_patch_validation_allows_unknown_fields():
    """Test that patch validation allows unknown fields in operations."""
    # This should not raise an error even though 'unknownField' doesn't exist on User
    patch_op = PatchOp[User].model_validate(
        {
            "operations": [
                {"op": "add", "path": "unknownField", "value": "some-value"},
            ]
        },
        context={"scim": Context.RESOURCE_PATCH_REQUEST},
    )
    assert len(patch_op.operations) == 1
    assert patch_op.operations[0].path == "unknownField"


def test_non_replace_operations_on_immutable_fields_allowed():
    """Test that non-replace operations on immutable fields are allowed."""
    # Test with non-immutable fields since groups.value is immutable
    patch_op = PatchOp[User].model_validate(
        {
            "operations": [
                {"op": "add", "path": "nickName", "value": "test-nick"},
                {"op": "remove", "path": "nickName"},
            ]
        },
        context={"scim": Context.RESOURCE_PATCH_REQUEST},
    )
    assert len(patch_op.operations) == 2


def test_remove_operation_on_unknown_field_validates():
    """Test remove operation on unknown field validates successfully."""
    patch_op = PatchOp[User].model_validate(
        {
            "operations": [
                {"op": "remove", "path": "unknownField"},
            ]
        },
        context={"scim": Context.RESOURCE_PATCH_REQUEST},
    )
    assert len(patch_op.operations) == 1
    assert patch_op.operations[0].path == "unknownField"


def test_remove_operation_on_non_required_field_allowed():
    """Test remove operation on non-required field is allowed."""
    # nickName is not required, so remove should be allowed
    PatchOp[User].model_validate(
        {
            "operations": [
                {"op": "remove", "path": "nickName"},
            ]
        },
        context={"scim": Context.RESOURCE_PATCH_REQUEST},
    )


def test_patch_operations_with_none_path_skipped():
    """Test that patch operations with None path are skipped during validation."""
    # Create a patch operation with None path (bypassing normal validation)
    patch_op = PatchOp[User](
        operations=[
            PatchOperation.model_construct(
                op=PatchOperation.Op.add, path=None, value="test"
            )
        ]
    )

    # The validate_operations method should skip operations with None path
    # This should not raise an error
    user = User(user_name="test")
    result = patch_op.patch(user)
    assert result is False  # Should return False because operation was skipped


def test_patch_operation_with_schema_only_urn_path():
    """Test patch operation with URN path that contains only schema."""
    # Test edge case where extract_field_name returns None for schema-only URNs
    user = User(user_name="test")

    # This URN resolves to just the schema without an attribute name
    patch = PatchOp[User](
        operations=[
            PatchOperation(
                op=PatchOperation.Op.add,
                path="urn:ietf:params:scim:schemas:core:2.0:User",
                value="test",
            )
        ]
    )

    # This should trigger the path where extract_field_name returns None
    with pytest.raises(ValueError, match="path"):
        patch.patch(user)


def test_add_remove_operations_on_group_members_allowed():
    """Test that add/remove operations work on group collections."""
    # Test operations on group collection (not the immutable value field)
    patch_op = PatchOp[User].model_validate(
        {
            "operations": [
                {"op": "add", "path": "emails", "value": {"value": "test@example.com"}},
                {
                    "op": "remove",
                    "path": "emails",
                    "value": {"value": "test@example.com"},
                },
            ]
        },
        context={"scim": Context.RESOURCE_PATCH_REQUEST},
    )
    assert len(patch_op.operations) == 2


def test_patch_error_handling_invalid_path():
    """Test error handling for invalid patch paths."""
    user = User(user_name="test")

    # Test with invalid path format
    patch = PatchOp[User](
        operations=[
            PatchOperation(op=PatchOperation.Op.add, path="invalid..path", value="test")
        ]
    )

    with pytest.raises(ValueError):
        patch.patch(user)


def test_patch_error_handling_no_operations():
    """Test patch behavior with no operations (using model_construct to bypass validation)."""
    user = User(user_name="test")
    # Use model_construct to bypass Pydantic validation that requires at least 1 operation
    patch = PatchOp[User].model_construct(operations=[])

    result = patch.patch(user)
    assert result is False


def test_patch_error_handling_type_mismatch():
    """Test error handling when patch value type doesn't match field type."""
    user = User(user_name="test")

    # Try to set active (boolean) to a string
    patch = PatchOp[User](
        operations=[
            PatchOperation(
                op=PatchOperation.Op.replace_, path="active", value="not_a_boolean"
            )
        ]
    )

    with pytest.raises(ValidationError):
        patch.patch(user)


T = TypeVar("T", bound=Resource)
UserT = TypeVar("UserT", bound=User)
UnboundT = TypeVar("UnboundT")


def test_patch_op_with_typevar_bound_to_resource():
    """Test that PatchOp accepts TypeVar bound to Resource."""
    # Should not raise any exception
    patch_type = PatchOp[T]
    assert patch_type is not None


def test_patch_op_with_typevar_bound_to_resource_subclass():
    """Test that PatchOp accepts TypeVar bound to Resource subclass."""
    # Should not raise any exception
    patch_type = PatchOp[UserT]
    assert patch_type is not None


def test_patch_op_with_unbound_typevar():
    """Test that PatchOp rejects unbound TypeVar."""
    with pytest.raises(
        TypeError,
        match="PatchOp TypeVar must be bound to Resource or its subclass, got ~UnboundT",
    ):
        PatchOp[UnboundT]


def test_patch_op_with_typevar_bound_to_non_resource():
    """Test that PatchOp rejects TypeVar bound to non-Resource class."""
    NonResourceT = TypeVar("NonResourceT", bound=str)
    with pytest.raises(
        TypeError,
        match="PatchOp TypeVar must be bound to Resource or its subclass, got ~NonResourceT",
    ):
        PatchOp[NonResourceT]


def test_create_parent_object_return_none():
    """Test _create_parent_object returns None when type resolution fails."""
    # This test uses a TypeVar to trigger the case where get_field_root_type returns None
    user = User()

    # Create a patch that will trigger _create_parent_object with complex path
    patch = PatchOp[User](
        operations=[
            PatchOperation(
                op=PatchOperation.Op.add,
                path="complexField.subField",  # Non-existent complex field
                value="test",
            )
        ]
    )

    # This should raise ValueError because field doesn't exist
    with pytest.raises(ValueError, match="no match|did not yield"):
        patch.patch(user)


def test_validate_required_field_removal():
    """Test that removing required fields raises validation error."""
    # Test removing schemas (required field) should raise validation error
    with pytest.raises(ValidationError, match="required value was missing"):
        PatchOp[User].model_validate(
            {"operations": [{"op": "remove", "path": "schemas"}]},
            context={"scim": Context.RESOURCE_PATCH_REQUEST},
        )


def test_patch_error_handling_invalid_operation():
    """Test error handling when patch operation has invalid operation type."""
    user = User(user_name="test")
    patch = PatchOp[User](
        operations=[
            PatchOperation(op=PatchOperation.Op.add, path="nickName", value="test")
        ]
    )

    # Force invalid operation type to test error handling
    object.__setattr__(patch.operations[0], "op", "invalid_operation")

    with pytest.raises(ValueError, match="invalid value|required value was missing"):
        patch.patch(user)


def test_remove_value_at_path_invalid_field():
    """Test removing value at path with invalid parent field name."""
    user = User(name={"familyName": "Test"})

    # Create patch that attempts to remove from invalid parent field
    patch = PatchOp[User](
        operations=[
            PatchOperation(op=PatchOperation.Op.remove, path="invalidParent.subField")
        ]
    )

    # This should raise ValueError for invalid field name
    with pytest.raises(ValueError, match="no match|did not yield"):
        patch.patch(user)


def test_remove_specific_value_invalid_field():
    """Test removing specific value from invalid field name."""
    user = User()

    # Create patch that attempts to remove specific value from invalid field
    patch = PatchOp[User](
        operations=[
            PatchOperation(
                op=PatchOperation.Op.remove,
                path="invalidField",
                value={"some": "value"},
            )
        ]
    )

    # This should raise ValueError for invalid field name
    with pytest.raises(ValueError, match="no match|did not yield"):
        patch.patch(user)
