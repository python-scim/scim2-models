"""Simplified tests for PatchOp and PatchOperation - keeping only essential tests."""

from typing import Annotated

import pytest
from pydantic import ValidationError

from scim2_models import PatchOp
from scim2_models import PatchOperation
from scim2_models.annotations import Mutability
from scim2_models.annotations import Required
from scim2_models.rfc7643.resource import Resource
from scim2_models.rfc7644.message import get_resource_class


# Test resource class for basic syntax tests
class MockResource(Resource):
    """Test resource class with various metadata annotations."""

    mutable_field: str
    read_only_field: Annotated[str, Mutability.read_only]
    immutable_field: Annotated[str, Mutability.immutable]
    required_field: Annotated[str, Required.true]
    optional_field: Annotated[str, Required.false] = "default"


def test_validate_patchop_case_insensitivith():
    """Validate that a patch operation's Op declaration is case-insensitive.

    RFC 7644 Section 3.5.2: "The "op" parameter value is case insensitive."
    """
    assert PatchOp.model_validate(
        {
            "operations": [
                {"op": "Replace", "path": "userName", "value": "Rivard"},
                {"op": "ADD", "path": "userName", "value": "Rivard"},
                {"op": "ReMove", "path": "userName", "value": "Rivard"},
            ],
        },
    ) == PatchOp(
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
        PatchOp.model_validate(
            {
                "operations": [{"op": 42, "path": "userName", "value": "Rivard"}],
            },
        )


def test_path_required_for_remove_operations():
    """Test that path is required for remove operations.

    RFC 7644 Section 3.5.2.3: "If the "path" parameter is missing, the operation fails with HTTP status code 400."
    """
    PatchOp.model_validate(
        {
            "operations": [
                {"op": "replace", "value": "foobar"},
            ],
        }
    )
    PatchOp.model_validate(
        {
            "operations": [
                {"op": "add", "value": "foobar"},
            ],
        }
    )

    with pytest.raises(ValidationError):
        PatchOp.model_validate(
            {
                "operations": [
                    {"op": "remove", "value": "foobar"},
                ],
            }
        )


def test_patch_operation_path_syntax_validation():
    """Test that invalid path syntax is rejected.

    RFC 7644 Section 3.5.2: Path syntax must follow ABNF rules defined in the specification.
    """
    # Test invalid path starting with digit
    with pytest.raises(ValidationError, match="path.*invalid"):
        PatchOp.model_validate(
            {"operations": [{"op": "replace", "path": "123invalid", "value": "test"}]}
        )

    # Test invalid path with double dots
    with pytest.raises(ValidationError, match="path.*invalid"):
        PatchOp.model_validate(
            {
                "operations": [
                    {"op": "replace", "path": "invalid..path", "value": "test"}
                ]
            }
        )

    # Test invalid path with invalid characters
    with pytest.raises(ValidationError, match="path.*invalid"):
        PatchOp.model_validate(
            {"operations": [{"op": "replace", "path": "invalid@path", "value": "test"}]}
        )

    # Test invalid URN path
    with pytest.raises(ValidationError, match="path.*invalid"):
        PatchOp.model_validate(
            {"operations": [{"op": "replace", "path": "urn:invalid", "value": "test"}]}
        )

    # Test valid paths should work
    valid_paths = [
        "userName",
        "name.familyName",
        "emails.value",
        "urn:ietf:params:scim:schemas:core:2.0:User:userName",
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:employeeNumber",
    ]

    for path in valid_paths:
        # Should not raise exception
        patch_op = PatchOp.model_validate(
            {"operations": [{"op": "replace", "path": path, "value": "test"}]}
        )
        assert patch_op.operations[0].path == path


def test_patch_operation_value_required_for_add():
    """Test that value is required for add operations.

    RFC 7644 Section 3.5.2.1: "The "value" parameter contains a set of attributes to be added to the resource."
    """
    # Test add without value should fail
    with pytest.raises(ValidationError, match="required value.*missing"):
        PatchOp.model_validate({"operations": [{"op": "add", "path": "userName"}]})

    # Test add with null value should fail
    with pytest.raises(ValidationError, match="required value.*missing"):
        PatchOp.model_validate(
            {"operations": [{"op": "add", "path": "userName", "value": None}]}
        )

    # Test add with value should work
    patch_op = PatchOp.model_validate(
        {"operations": [{"op": "add", "path": "userName", "value": "test"}]}
    )
    assert patch_op.operations[0].value == "test"

    # Test replace without value should work (optional)
    patch_op = PatchOp.model_validate(
        {"operations": [{"op": "replace", "path": "userName"}]}
    )
    assert patch_op.operations[0].value is None

    # Test remove without value should work (not applicable)
    patch_op = PatchOp.model_validate(
        {"operations": [{"op": "remove", "path": "userName"}]}
    )
    assert patch_op.operations[0].value is None


def test_patch_operation_urn_path_validation():
    """Test URN path validation edge cases.

    RFC 7644 Section 3.5.2: URN paths must follow the format "urn:ietf:params:scim:schemas:..." for schema extensions.
    """
    # Test valid URN paths
    valid_urn_paths = [
        "urn:ietf:params:scim:schemas:core:2.0:User:userName",
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:employeeNumber",
        "urn:custom:namespace:schema:1.0:Resource:attribute",
    ]

    for urn_path in valid_urn_paths:
        patch_op = PatchOp.model_validate(
            {"operations": [{"op": "replace", "path": urn_path, "value": "test"}]}
        )
        assert patch_op.operations[0].path == urn_path

    # Test invalid URN paths
    invalid_urn_paths = [
        "urn:too:short",  # Not enough segments
        "urn:ietf:params:scim:schemas:core:2.0:User:",  # Empty attribute
        "urn:ietf:params:scim:schemas:core:2.0:User:123invalid",  # Attribute starts with digit
        "noturn:ietf:params:scim:schemas:core:2.0:User:userName",  # Doesn't start with urn:
    ]

    for urn_path in invalid_urn_paths:
        with pytest.raises(ValidationError, match="path.*invalid"):
            PatchOp.model_validate(
                {"operations": [{"op": "replace", "path": urn_path, "value": "test"}]}
            )


def test_patch_operation_path_edge_cases():
    """Test edge cases for path validation."""
    # Test None path (should be allowed for non-remove operations)
    patch_op = PatchOp.model_validate(
        {"operations": [{"op": "replace", "value": "test"}]}
    )
    assert patch_op.operations[0].path is None

    # Test empty path (should be invalid)
    with pytest.raises(ValidationError, match="path.*invalid"):
        PatchOp.model_validate(
            {"operations": [{"op": "replace", "path": "", "value": "test"}]}
        )

    # Test whitespace-only path (should be invalid)
    with pytest.raises(ValidationError, match="path.*invalid"):
        PatchOp.model_validate(
            {"operations": [{"op": "replace", "path": "   ", "value": "test"}]}
        )

    # Test URN with not enough parts (should be invalid)
    with pytest.raises(ValidationError, match="path.*invalid"):
        PatchOp.model_validate(
            {
                "operations": [
                    {"op": "replace", "path": "urn:invalid:path", "value": "test"}
                ]
            }
        )

    # Test URN with no colon separation (should be invalid)
    with pytest.raises(ValidationError, match="path.*invalid"):
        PatchOp.model_validate(
            {"operations": [{"op": "replace", "path": "urn:invalid", "value": "test"}]}
        )


def test_patch_operation_path_validator_directly():
    """Test path validator directly to ensure full coverage."""
    # Test that None path is handled correctly
    result = PatchOperation.validate_path_syntax(None)
    assert result is None

    # Test empty string handling
    with pytest.raises(ValueError, match="path.*invalid"):
        PatchOperation.validate_path_syntax("")

    # Test URN edge cases for full coverage
    # This tests the case where a path starts with "urn" but has invalid format
    with pytest.raises(ValueError, match="path.*invalid"):
        PatchOperation.validate_path_syntax("urn:invalid")


# Test resource classes with different metadata
class MockUser(Resource):
    """Test user resource with metadata annotations."""

    user_name: str
    password: Annotated[str, Mutability.write_only]
    read_only_field: Annotated[str, Mutability.read_only]
    immutable_field: Annotated[str, Mutability.immutable]
    required_field: Annotated[str, Required.true]
    optional_field: Annotated[str, Required.false] = "default"


class MockGroup(Resource):
    """Test group resource with metadata annotations."""

    display_name: Annotated[str, Required.true]
    members: Annotated[list, Mutability.read_only] = []


def test_patch_op_automatic_validation_with_user_type():
    """Test that PatchOp[User] automatically validates against User metadata.

    RFC 7643 Section 7: Attributes with mutability "readOnly" or "immutable" must be protected from modification.
    """
    # Test read-only field violation
    with pytest.raises(ValidationError, match="attempted modification.*mutability"):
        PatchOp[MockUser].model_validate(
            {"operations": [{"op": "add", "path": "read_only_field", "value": "test"}]}
        )

    # Test immutable field violation
    with pytest.raises(ValidationError, match="attempted modification.*mutability"):
        PatchOp[MockUser].model_validate(
            {
                "operations": [
                    {"op": "replace", "path": "immutable_field", "value": "test"}
                ]
            }
        )

    # Test required field removal
    with pytest.raises(ValidationError, match="required value.*missing"):
        PatchOp[MockUser].model_validate(
            {"operations": [{"op": "remove", "path": "required_field"}]}
        )


def test_patch_op_automatic_validation_allows_valid_operations():
    """Test that valid operations pass automatic validation."""
    # Valid operations should work
    patch_op = PatchOp[MockUser].model_validate(
        {
            "operations": [
                {"op": "add", "path": "user_name", "value": "john.doe"},
                {"op": "replace", "path": "optional_field", "value": "new_value"},
                {"op": "remove", "path": "optional_field"},
                {
                    "op": "add",
                    "path": "immutable_field",
                    "value": "initial_value",
                },  # ADD is allowed for immutable
            ]
        }
    )

    assert len(patch_op.operations) == 4


def test_patch_op_automatic_validation_with_group_type():
    """Test that PatchOp[Group] validates against Group metadata.

    RFC 7643 Section 7: Attributes with mutability "readOnly" must be protected from modification.
    """
    # Test read-only members field
    with pytest.raises(ValidationError, match="attempted modification.*mutability"):
        PatchOp[MockGroup].model_validate(
            {
                "operations": [
                    {"op": "add", "path": "members", "value": [{"value": "user123"}]}
                ]
            }
        )

    # Valid operation should work
    patch_op = PatchOp[MockGroup].model_validate(
        {
            "operations": [
                {"op": "replace", "path": "display_name", "value": "New Group Name"}
            ]
        }
    )

    assert len(patch_op.operations) == 1


def test_patch_op_without_type_parameter_no_validation():
    """Test that PatchOp without type parameter doesn't do metadata validation."""
    # This should work even though it would violate User metadata
    # because no type parameter means no automatic validation
    patch_op = PatchOp.model_validate(
        {"operations": [{"op": "add", "path": "read_only_field", "value": "test"}]}
    )

    assert len(patch_op.operations) == 1


def test_patch_op_complex_paths_ignored():
    """Test that complex paths are ignored in automatic validation.

    RFC 7644 Section 3.5.2: Complex path expressions with filters are allowed but not validated at schema level.
    """
    # Complex paths should be ignored (no validation error)
    patch_op = PatchOp[MockUser].model_validate(
        {
            "operations": [
                {
                    "op": "replace",
                    "path": 'emails[type eq "work"].value',
                    "value": "test",
                },
                {"op": "add", "path": 'groups[display eq "Admin"]', "value": "test"},
            ]
        }
    )

    assert len(patch_op.operations) == 2


def test_patch_op_nonexistent_fields_allowed():
    """Test that operations on non-existent fields are allowed.

    RFC 7644 Section 3.5.2: Servers should be tolerant of schema extensions and unrecognized attributes.
    """
    # Operations on fields that don't exist should be allowed
    patch_op = PatchOp[MockUser].model_validate(
        {
            "operations": [
                {"op": "add", "path": "nonexistent_field", "value": "test"},
                {"op": "remove", "path": "another_nonexistent_field"},
            ]
        }
    )

    assert len(patch_op.operations) == 2


def test_patch_op_field_without_annotations():
    """Test that operations on fields without mutability/required annotations are allowed."""

    class MockUserWithoutAnnotations(Resource):
        user_name: str  # No mutability annotation
        description: str = "default"  # No required annotation

    # Operations on fields without annotations should be allowed
    patch_op = PatchOp[MockUserWithoutAnnotations].model_validate(
        {
            "operations": [
                {"op": "add", "path": "user_name", "value": "test"},
                {"op": "replace", "path": "user_name", "value": "test2"},
                {"op": "remove", "path": "description"},
            ]
        }
    )

    assert len(patch_op.operations) == 3


def test_patch_op_urn_paths_validated():
    """Test that URN paths are validated with automatic validation."""
    # URN path for read-only field should fail
    with pytest.raises(ValidationError, match="attempted modification.*mutability"):
        PatchOp[MockUser].model_validate(
            {
                "operations": [
                    {
                        "op": "replace",
                        "path": "urn:ietf:params:scim:schemas:core:2.0:User:read_only_field",
                        "value": "test",
                    }
                ]
            }
        )


def test_patch_op_read_only_field_remove_operation():
    """Test that remove operations on read-only fields are allowed.

    RFC 7643 Section 7: Read-only fields can be removed but not added/replaced.
    """
    # Remove operation on read-only field should work
    patch_op = PatchOp[MockUser].model_validate(
        {"operations": [{"op": "remove", "path": "read_only_field"}]}
    )
    assert len(patch_op.operations) == 1


def test_patch_op_none_path_validation():
    """Test validation when path is None."""
    # Test with None path - should not validate field metadata
    patch_op = PatchOp[MockUser].model_validate(
        {"operations": [{"op": "replace", "value": {"read_only_field": "test"}}]}
    )
    assert len(patch_op.operations) == 1
    assert patch_op.operations[0].path is None


def test_patch_op_get_resource_class_method():
    """Test the get_resource_class method directly."""
    # With type parameter
    typed_patch = PatchOp[MockUser].model_validate(
        {"operations": [{"op": "add", "path": "user_name", "value": "test"}]}
    )
    resource_class = get_resource_class(typed_patch)
    assert resource_class == MockUser

    # With a wrong type parameter
    untyped_patch = PatchOp[int].model_validate(
        {"operations": [{"op": "add", "path": "user_name", "value": "test"}]}
    )
    resource_class = get_resource_class(untyped_patch)
    assert resource_class is None

    # Without type parameter
    untyped_patch = PatchOp.model_validate(
        {"operations": [{"op": "add", "path": "user_name", "value": "test"}]}
    )
    resource_class = get_resource_class(untyped_patch)
    assert resource_class is None


def test_patch_op_not_type_parameter():
    """Test that existing code without type parameters still works."""
    # Old way of creating PatchOp should still work
    patch_op = PatchOp(
        operations=[{"op": "add", "path": "any_field", "value": "any_value"}]
    )

    assert len(patch_op.operations) == 1
    assert get_resource_class(patch_op) is None
