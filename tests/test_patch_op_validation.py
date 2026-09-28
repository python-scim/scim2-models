from datetime import UTC
from datetime import datetime
from typing import Annotated
from typing import TypeVar

import pytest
from pydantic import ValidationError

from scim2_models import URN
from scim2_models import ComplexAttribute
from scim2_models import Extension
from scim2_models import Group
from scim2_models import InvalidFilterException
from scim2_models import InvalidPathException
from scim2_models import InvalidValueException
from scim2_models import Mutability
from scim2_models import MutabilityException
from scim2_models import NoTargetException
from scim2_models import PatchOp
from scim2_models import PatchOperation
from scim2_models import Path
from scim2_models import PathNotFoundException
from scim2_models import Required
from scim2_models import ScimPolicy
from scim2_models import User
from scim2_models.base import Context
from scim2_models.resources.resource import Resource


class ImmutableFieldResource(Resource):
    locked: Annotated[str | None, Mutability.immutable] = None


class ConstrainedComplex(ComplexAttribute):
    label: str | None = None


class ConstrainedResource(Resource):
    __schema__ = URN("urn:example:2.0:ConstrainedResource")

    read_only_attr: Annotated[str | None, Mutability.read_only] = None
    immutable_attr: Annotated[str | None, Mutability.immutable] = None
    immutable_complex: Annotated[ConstrainedComplex | None, Mutability.immutable] = None
    immutable_date: Annotated[datetime | None, Mutability.immutable] = None
    immutable_list: Annotated[list[ConstrainedComplex] | None, Mutability.immutable] = (
        None
    )
    required_attr: Annotated[str | None, Required.true] = None
    plain_attr: str | None = None


class ConstrainedExtension(Extension):
    __schema__ = URN("urn:example:2.0:Constrained")

    read_only_attr: Annotated[str | None, Mutability.read_only] = None
    immutable_attr: Annotated[str | None, Mutability.immutable] = None
    required_attr: Annotated[str | None, Required.true] = None
    plain_attr: str | None = None


def test_a_path_naming_an_extension_the_resource_does_not_carry_is_refused():
    """A schema URN the type parameter leaves out designates no target."""
    with pytest.raises(ValidationError) as raised:
        PatchOp[User](
            operations=[
                PatchOperation[User](
                    op="add",
                    path="urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
                    value={"employeeNumber": "12345"},
                )
            ]
        )

    assert raised.value.errors()[0]["type"] == "scim_invalidPath"


def test_a_schema_urn_separated_from_its_attribute_by_a_dot_is_refused():
    """A URN carries its attribute behind a colon, and a dot names a sub-attribute of it."""
    with pytest.raises(ValidationError) as raised:
        PatchOp[User[ConstrainedExtension]](
            operations=[
                PatchOperation[User[ConstrainedExtension]](
                    op="replace",
                    path="urn:example:2.0:Constrained.plainAttr",
                    value="test",
                )
            ]
        )

    assert raised.value.errors()[0]["type"] == "scim_invalidPath"


def test_patch_op_without_type_parameter():
    """Test that PatchOp cannot be instantiated without a type parameter."""
    with pytest.raises(TypeError, match="PatchOp requires a type parameter"):
        PatchOp(operations=[{"op": "replace", "path": "userName", "value": "test"}])


def test_patch_op_parameterized_with_resource_is_refused_when_used():
    """Resource declares no attribute, so it can annotate a patch but not read one."""
    assert PatchOp[Resource] is not None

    with pytest.raises(
        TypeError,
        match=r"PatchOp\[Resource\] declares no attribute a payload could be read as",
    ):
        PatchOp[Resource](
            operations=[{"op": "replace", "path": "userName", "value": "test"}]
        )


def test_patch_op_with_invalid_type():
    """Test that PatchOp with invalid types like str is rejected."""
    with pytest.raises(
        TypeError, match="PatchOp type parameter must name resource types"
    ):
        PatchOp[str]


def test_patch_op_union_types_not_supported():
    """Test that PatchOp with Union types are rejected."""
    with pytest.raises(
        TypeError, match="PatchOp type parameter must name one resource type"
    ):
        PatchOp[User | Group]


def test_validate_patchop_case_insensitivity():
    """Validate that a patch operation's Op declaration is case-insensitive.

    Note: While :rfc:`RFC7644 §3.4.2.2 <7644#section-3.4.2.2>` specifies case insensitivity
    for attribute names and operators in filters, this implementation extends this principle
    to PATCH operation names for Microsoft Entra compatibility.
    """
    assert PatchOp[User].model_validate(
        {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "operations": [
                {"op": "Replace", "path": "displayName", "value": "Rivard"},
                {"op": "ADD", "path": "displayName", "value": "Rivard"},
                {"op": "ReMove", "path": "displayName", "value": "Rivard"},
            ],
        },
    ) == PatchOp[User](
        schemas=["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        operations=[
            PatchOperation[User](
                op=PatchOperation.Op.replace_, path="displayName", value="Rivard"
            ),
            PatchOperation[User](
                op=PatchOperation.Op.add, path="displayName", value="Rivard"
            ),
            PatchOperation[User](
                op=PatchOperation.Op.remove, path="displayName", value="Rivard"
            ),
        ],
    )
    with pytest.raises(
        ValidationError,
        match="1 validation error for PatchOp",
    ):
        PatchOp[User].model_validate(
            {
                "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
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
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "operations": [
                {"op": "replace", "value": {"nickName": "foobar"}},
            ],
        },
        context={"scim": Context.RESOURCE_PATCH_REQUEST},
    )
    PatchOp[User].model_validate(
        {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "operations": [
                {"op": "add", "value": {"nickName": "foobar"}},
            ],
        },
        context={"scim": Context.RESOURCE_PATCH_REQUEST},
    )

    # RFC 7644 §3.5.2.2: remove without path returns noTarget error
    with pytest.raises(ValidationError, match="Remove operation requires a path"):
        PatchOp[User].model_validate(
            {
                "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
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
    with pytest.raises(ValidationError):
        PatchOp[User].model_validate(
            {
                "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
                "operations": [
                    {"op": "add", "path": "nickName"},
                ],
            },
            context={"scim": Context.RESOURCE_PATCH_REQUEST},
        )

    PatchOp[User].model_validate(
        {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "operations": [
                {"op": "remove", "path": "nickName"},
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

    # RFC 7644 §3.5.2.2: remove without path returns noTarget error
    with pytest.raises(ValidationError, match="Remove operation requires a path"):
        PatchOperation.model_validate(
            {"op": "remove"},
            context={"scim": Context.RESOURCE_PATCH_REQUEST},
        )

    with pytest.raises(ValidationError, match="value is required for add operations"):
        PatchOperation.model_validate(
            {"op": "add", "path": "test"},
            context={"scim": Context.RESOURCE_PATCH_REQUEST},
        )

    operation = PatchOperation.model_validate({"op": "remove"})
    assert operation.path is None


def test_validate_mutability_readonly_error():
    """All PATCH operations on readOnly attributes are rejected at parse-time."""
    for op, extra in [
        ("add", {"value": "x"}),
        ("replace", {"value": "x"}),
        ("remove", {}),
    ]:
        with pytest.raises(ValidationError, match="mutability"):
            PatchOp[User].model_validate(
                {
                    "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
                    "operations": [{"op": op, "path": "id", **extra}],
                },
                context={"scim": Context.RESOURCE_PATCH_REQUEST},
            )


def test_validate_mutability_readonly_via_complex_path():
    """Replacing a readOnly complex attribute path is rejected at parse-time."""
    with pytest.raises(ValidationError, match="mutability"):
        PatchOp[User].model_validate(
            {
                "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
                "operations": [
                    {
                        "op": "replace",
                        "path": "groups.value",
                        "value": "new-group-id",
                    }
                ],
            },
            context={"scim": Context.RESOURCE_PATCH_REQUEST},
        )


def test_patch_remove_on_immutable_field_with_value_is_rejected():
    """Removing an existing immutable attribute via PATCH is rejected at runtime."""
    resource = ImmutableFieldResource.model_construct(locked="existing")
    patch_op = PatchOp[ImmutableFieldResource].model_validate(
        {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "operations": [{"op": "remove", "path": "locked"}],
        },
        context={"scim": Context.RESOURCE_PATCH_REQUEST},
    )
    with pytest.raises(MutabilityException):
        patch_op.patch(resource)


def test_patch_remove_on_immutable_field_without_value_is_allowed():
    """Removing an unset immutable attribute is a no-op and is allowed."""
    resource = ImmutableFieldResource.model_construct()
    patch_op = PatchOp[ImmutableFieldResource].model_validate(
        {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "operations": [{"op": "remove", "path": "locked"}],
        },
        context={"scim": Context.RESOURCE_PATCH_REQUEST},
    )
    patch_op.patch(resource)
    assert resource.locked is None


def test_patch_add_on_immutable_field_with_existing_value_is_rejected():
    """Adding to an immutable attribute that already has a value is rejected."""
    resource = ImmutableFieldResource.model_construct(locked="existing")
    patch_op = PatchOp[ImmutableFieldResource].model_validate(
        {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "operations": [{"op": "add", "path": "locked", "value": "new"}],
        },
        context={"scim": Context.RESOURCE_PATCH_REQUEST},
    )
    with pytest.raises(MutabilityException):
        patch_op.patch(resource)


def test_patch_add_on_immutable_field_without_value_is_allowed():
    """Adding to an immutable attribute with no previous value is allowed per RFC 7644."""
    resource = ImmutableFieldResource.model_construct()
    patch_op = PatchOp[ImmutableFieldResource].model_validate(
        {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "operations": [{"op": "add", "path": "locked", "value": "initial"}],
        },
        context={"scim": Context.RESOURCE_PATCH_REQUEST},
    )
    patch_op.patch(resource)
    assert resource.locked == "initial"


def test_patch_replace_on_immutable_field_with_different_value_is_rejected():
    """Replacing an immutable attribute with a different value is rejected."""
    resource = ImmutableFieldResource.model_construct(locked="existing")
    patch_op = PatchOp[ImmutableFieldResource].model_validate(
        {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "operations": [{"op": "replace", "path": "locked", "value": "other"}],
        },
        context={"scim": Context.RESOURCE_PATCH_REQUEST},
    )
    with pytest.raises(MutabilityException):
        patch_op.patch(resource)


def test_patch_replace_on_immutable_field_with_same_value_is_allowed():
    """Replacing an immutable attribute with its current value is a no-op and is allowed."""
    resource = ImmutableFieldResource.model_construct(locked="existing")
    patch_op = PatchOp[ImmutableFieldResource].model_validate(
        {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "operations": [{"op": "replace", "path": "locked", "value": "existing"}],
        },
        context={"scim": Context.RESOURCE_PATCH_REQUEST},
    )
    patch_op.patch(resource)
    assert resource.locked == "existing"


def test_patch_remove_on_readonly_field_is_rejected():
    """Removing a readOnly attribute via PATCH is rejected per RFC 7643 §7."""
    with pytest.raises(ValidationError, match="mutability"):
        PatchOp[User].model_validate(
            {
                "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
                "operations": [{"op": "remove", "path": "id"}],
            },
            context={"scim": Context.RESOURCE_PATCH_REQUEST},
        )


def test_patch_operations_on_readwrite_fields_allowed():
    """All patch operations are allowed on readWrite fields."""
    patch_op = PatchOp[User].model_validate(
        {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "operations": [
                {"op": "add", "path": "nickName", "value": "test-nick"},
                {"op": "remove", "path": "nickName"},
            ],
        },
        context={"scim": Context.RESOURCE_PATCH_REQUEST},
    )
    assert len(patch_op.operations) == 2


def test_remove_operation_on_non_required_field_allowed():
    """Test remove operation on non-required field is allowed."""
    # nickName is not required, so remove should be allowed
    PatchOp[User].model_validate(
        {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "operations": [
                {"op": "remove", "path": "nickName"},
            ],
        },
        context={"scim": Context.RESOURCE_PATCH_REQUEST},
    )


def test_add_remove_operations_on_group_members_allowed():
    """Test that add/remove operations work on group collections."""
    # Test operations on group collection (not the immutable value field)
    patch_op = PatchOp[User].model_validate(
        {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "operations": [
                {"op": "add", "path": "emails", "value": {"value": "test@example.com"}},
                {
                    "op": "remove",
                    "path": 'emails[value eq "test@example.com"]',
                },
            ],
        },
        context={"scim": Context.RESOURCE_PATCH_REQUEST},
    )
    assert len(patch_op.operations) == 2


def test_patch_error_handling_no_operations():
    """Test patch behavior with no operations (using model_construct to bypass validation)."""
    user = User(user_name="test")
    # Use model_construct to bypass Pydantic validation that requires at least 1 operation
    patch = PatchOp[User].model_construct(operations=[])

    result = patch.patch(user)
    assert result is False


def test_patch_error_handling_type_mismatch():
    """RFC7644 §3.12 returns invalidValue for a value that does not fit the attribute type."""
    user = User(user_name="test")

    # Try to set active (boolean) to a string
    patch = PatchOp[User](
        operations=[
            PatchOperation[User](
                op=PatchOperation.Op.replace_, path="active", value="not_a_boolean"
            )
        ]
    )

    with pytest.raises(InvalidValueException) as raised:
        patch.patch(user)

    assert raised.value.scim_type == "invalidValue"


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
        match="PatchOp type parameter must name resource types, got ~UnboundT",
    ):
        PatchOp[UnboundT]


def test_patch_op_with_typevar_bound_to_non_resource():
    """Test that PatchOp rejects TypeVar bound to non-Resource class."""
    NonResourceT = TypeVar("NonResourceT", bound=str)
    with pytest.raises(
        TypeError,
        match="PatchOp type parameter must name resource types, got ~NonResourceT",
    ):
        PatchOp[NonResourceT]


def test_validate_required_field_removal():
    """Test that removing required fields raises validation error."""
    # Test removing schemas (required field) should raise validation error
    with pytest.raises(ValidationError, match="required attribute cannot be removed"):
        PatchOp[User].model_validate(
            {
                "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
                "operations": [{"op": "remove", "path": "schemas"}],
            },
            context={"scim": Context.RESOURCE_PATCH_REQUEST},
        )


def test_patch_error_handling_invalid_operation():
    """Test error handling when patch operation has invalid operation type."""
    user = User(user_name="test")
    patch = PatchOp[User](
        operations=[
            PatchOperation[User](
                op=PatchOperation.Op.add, path="nickName", value="test"
            )
        ]
    )

    # Force invalid operation type to test error handling
    object.__setattr__(patch.operations[0], "op", "invalid_operation")

    with pytest.raises(InvalidValueException):
        patch.patch(user)


def test_a_path_whose_parent_attribute_no_model_declares_is_refused():
    """A sub-attribute is looked up on the attribute holding it, which must exist first."""
    with pytest.raises(ValidationError) as raised:
        PatchOp[User](
            operations=[
                PatchOperation[User](
                    op=PatchOperation.Op.remove, path="invalidParent.subField"
                )
            ]
        )

    assert raised.value.errors()[0]["type"] == "scim_invalidPath"


def test_remove_an_attribute_no_model_declares():
    """A remove names its target in its path, and one outside the schema is refused."""
    with pytest.raises(ValidationError) as raised:
        PatchOp[User](
            operations=[
                PatchOperation[User](
                    op=PatchOperation.Op.remove,
                    path="invalidField",
                )
            ]
        )

    assert raised.value.errors()[0]["type"] == "scim_invalidPath"


def test_patch_op_operations_attribute_required_in_patch_context():
    """Test that Operations attribute is required in PATCH request context per RFC 7644."""
    # Operations attribute must be present in PATCH request context
    with pytest.raises(ValidationError, match="operations attribute is required"):
        PatchOp[User].model_validate(
            {"schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"]},
            context={"scim": Context.RESOURCE_PATCH_REQUEST},
        )

    # Operations can be None when not in PATCH request context
    patch_op = PatchOp[User].model_validate(
        {"schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"]}
    )
    assert patch_op.operations is None

    # Operations with at least one operation is valid in PATCH request context
    patch_op = PatchOp[User].model_validate(
        {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "operations": [{"op": "add", "path": "userName", "value": "test"}],
        },
        context={"scim": Context.RESOURCE_PATCH_REQUEST},
    )
    assert len(patch_op.operations) == 1


@pytest.mark.parametrize(
    "path",
    [
        "groups",
        "GROUPS",
        "Groups",
        "urn:ietf:params:scim:schemas:core:2.0:User:groups",
    ],
)
def test_a_read_only_attribute_is_protected_whatever_its_spelling(path):
    """Attribute names are case-insensitive per :rfc:`RFC7643 §2.1 <7643#section-2.1>`.

    ``groups`` is readOnly, so every spelling designating it must be refused.
    """
    with pytest.raises(ValidationError, match="mutability"):
        PatchOp[User](
            operations=[
                PatchOperation[User](
                    op=PatchOperation.Op.replace_,
                    path=path,
                    value=[{"value": "group-id"}],
                )
            ]
        )


@pytest.mark.parametrize(
    "path",
    ["userName", "USERNAME", "urn:ietf:params:scim:schemas:core:2.0:User:userName"],
)
def test_a_required_attribute_cannot_be_removed_whatever_its_spelling(path):
    """``userName`` is required, and its SCIM name differs from its field name."""
    with pytest.raises(ValidationError, match="required attribute cannot be removed"):
        PatchOp[User](
            operations=[PatchOperation[User](op=PatchOperation.Op.remove, path=path)]
        )


def test_an_immutable_attribute_is_protected_whatever_its_spelling():
    """The runtime check reads the current value, so it resolves the name too."""
    resource = ImmutableFieldResource(locked="original")
    patch = PatchOp[ImmutableFieldResource](
        operations=[
            PatchOperation[ImmutableFieldResource](
                op=PatchOperation.Op.replace_, path="LOCKED", value="hijacked"
            )
        ]
    )

    with pytest.raises(MutabilityException):
        patch.patch(resource)
    assert resource.locked == "original"


def test_an_operation_on_the_resource_root_has_no_attribute_to_check():
    """An empty path designates the resource itself, so no constraint applies."""
    resource = User(user_name="bjensen")
    patch = PatchOp[User](
        operations=[
            PatchOperation[User](
                op=PatchOperation.Op.add, path="", value={"displayName": "Barbara"}
            )
        ]
    )

    assert patch.patch(resource)
    assert resource.display_name == "Barbara"


def test_a_replace_cannot_unassign_a_required_attribute():
    """:rfc:`RFC7643` §2.5 makes a null value equivalent to an unassigned attribute, which §3.5.2.2 of :rfc:`RFC7644` refuses on a required one."""
    for value in (None, []):
        with pytest.raises(
            ValidationError, match="required attribute cannot be unassigned"
        ):
            PatchOp[User].model_validate(
                {
                    "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
                    "Operations": [
                        {"op": "replace", "path": "userName", "value": value}
                    ],
                },
                scim_ctx=Context.RESOURCE_PATCH_REQUEST,
            )


def test_a_replace_may_empty_a_required_string():
    """An empty string is a value, where :rfc:`RFC7643` §2.5 only equates null and the empty array to an unassigned attribute."""
    patch = PatchOp[User].model_validate(
        {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "Operations": [{"op": "replace", "path": "userName", "value": ""}],
        },
        scim_ctx=Context.RESOURCE_PATCH_REQUEST,
    )
    user = User(id="1", user_name="bjensen")
    patch.patch(user)
    assert user.user_name == ""


def test_a_replace_may_unassign_an_optional_attribute():
    """Only a required attribute is protected from becoming unassigned."""
    patch = PatchOp[User].model_validate(
        {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "Operations": [{"op": "replace", "path": "displayName", "value": None}],
        },
        scim_ctx=Context.RESOURCE_PATCH_REQUEST,
    )
    user = User(id="1", user_name="bjensen", display_name="Babs")
    patch.patch(user)
    assert user.display_name is None


def test_an_operation_without_path_cannot_change_a_read_only_attribute():
    """RFC7644 §3.5.2 forbids changing a read-only attribute, here set in the value."""
    patch = PatchOp[User].model_validate(
        {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "Operations": [{"op": "replace", "value": {"id": "chosen-by-the-client"}}],
        },
        scim_ctx=Context.RESOURCE_PATCH_REQUEST,
    )
    user = User(id="srv-1", user_name="bjensen")

    with pytest.raises(MutabilityException):
        patch.patch(user)
    assert user.id == "srv-1"


def test_an_operation_without_path_cannot_assign_a_read_only_complex_attribute():
    """A client cannot set a read-only complex attribute that has no value."""
    patch = PatchOp[User].model_validate(
        {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "Operations": [
                {"op": "replace", "value": {"meta": {"resourceType": "Group"}}}
            ],
        },
        scim_ctx=Context.RESOURCE_PATCH_REQUEST,
    )
    user = User(id="srv-1", user_name="bjensen")

    with pytest.raises(MutabilityException):
        patch.patch(user)
    assert user.meta is None


def test_an_operation_without_path_ignores_a_read_only_attribute_sent_back_unchanged():
    """Okta sends back the id of a group it renames, and RFC7643 §3.1 says to ignore it."""
    patch = PatchOp[Group].model_validate(
        {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "Operations": [
                {"op": "replace", "value": {"id": "grp-1", "displayName": "Admins"}}
            ],
        },
        scim_ctx=Context.RESOURCE_PATCH_REQUEST,
    )
    group = Group(id="grp-1", display_name="Staff")

    assert patch.patch(group)
    assert group.id == "grp-1"
    assert group.display_name == "Admins"


def test_an_operation_without_path_ignores_a_resource_sent_back_as_it_was_read():
    """The read-only meta of a dumped resource compares equal once parsed, whatever its spelling."""
    user = User(
        id="srv-1",
        user_name="bjensen",
        meta={
            "resourceType": "User",
            "created": datetime(2020, 1, 1, tzinfo=UTC),
            "version": 'W/"1"',
        },
    )
    value = user.model_dump(scim_ctx=Context.RESOURCE_QUERY_RESPONSE)
    value["nickName"] = "Babs"
    patch = PatchOp[User].model_validate(
        {"Operations": [{"op": "replace", "value": value}]},
        scim_ctx=Context.RESOURCE_PATCH_REQUEST,
    )

    assert patch.patch(user)
    assert user.nick_name == "Babs"
    assert user.meta.version == 'W/"1"'


def test_an_operation_without_path_cannot_unassign_a_required_attribute():
    """A null value in the ``value`` unassigns its attribute as surely as a remove does."""
    with pytest.raises(
        ValidationError, match="required attribute cannot be unassigned"
    ):
        PatchOp[User].model_validate(
            {
                "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
                "Operations": [{"op": "replace", "value": {"userName": None}}],
            },
            scim_ctx=Context.RESOURCE_PATCH_REQUEST,
        )


def test_an_add_without_path_cannot_change_a_read_only_attribute():
    """RFC7644 §3.5.2.1 lets add omit the path, as replace does."""
    patch = PatchOp[User].model_validate(
        {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "Operations": [{"op": "add", "value": {"id": "chosen-by-the-client"}}],
        },
        scim_ctx=Context.RESOURCE_PATCH_REQUEST,
    )
    user = User(id="srv-1", user_name="bjensen")

    with pytest.raises(MutabilityException):
        patch.patch(user)
    assert user.id == "srv-1"


def test_a_path_to_a_read_only_attribute_is_refused_even_unchanged():
    """A path to a read-only attribute targets it on purpose, whatever the value."""
    with pytest.raises(ValidationError) as raised:
        PatchOp[User].model_validate(
            {"Operations": [{"op": "replace", "path": "id", "value": "srv-1"}]},
            scim_ctx=Context.RESOURCE_PATCH_REQUEST,
        )

    assert raised.value.errors()[0]["type"] == "scim_mutability"


def test_an_operation_without_path_refuses_an_undeclared_attribute():
    """§3.5.2 has an operation incompatible with an attribute's schema return an error.

    §3.12 names ``invalidValue`` for a value "not compatible with [...] the
    resource schema", and there is no path here to call invalid.
    """
    with pytest.raises(ValidationError) as raised:
        PatchOp[User].model_validate(
            {
                "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
                "Operations": [
                    {"op": "replace", "value": {"whatever": "x", "displayName": "Babs"}}
                ],
            },
            scim_ctx=Context.RESOURCE_PATCH_REQUEST,
        )

    assert raised.value.errors()[0]["type"] == "scim_invalidValue"


def test_an_operation_without_path_may_unassign_an_extension():
    """An extension is not an attribute of the resource, so it is not required."""
    patch = PatchOp[User[ConstrainedExtension]].model_validate(
        {
            "Operations": [
                {"op": "replace", "value": {"urn:example:2.0:Constrained": None}}
            ]
        }
    )
    user = User[ConstrainedExtension](user_name="bjensen")

    patch.patch(user)
    assert user[ConstrainedExtension] is None


def test_an_operation_without_path_writes_an_extension_it_names():
    """The value names an extension by its schema URN, which the model declares."""
    patch = PatchOp[User[ConstrainedExtension]].model_validate(
        {
            "Operations": [
                {
                    "op": "replace",
                    "value": {
                        "displayName": "Babs",
                        "urn:example:2.0:Constrained": {"plainAttr": "written"},
                    },
                }
            ]
        }
    )
    user = User[ConstrainedExtension](user_name="bjensen")

    patch.patch(user)
    assert user.display_name == "Babs"


def test_an_operation_without_path_writes_the_attributes_it_may():
    """A writable attribute goes through, and the rest of the resource is left alone."""
    patch = PatchOp[User].model_validate(
        {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "Operations": [{"op": "replace", "value": {"displayName": "Babs"}}],
        },
        scim_ctx=Context.RESOURCE_PATCH_REQUEST,
    )
    user = User(id="srv-1", user_name="bjensen")
    patch.patch(user)
    assert user.display_name == "Babs"
    assert user.id == "srv-1"
    assert user.user_name == "bjensen"


def test_unassigning_a_required_attribute_answers_mutability():
    """:rfc:`RFC7644 §3.5.2.2 <7644#section-3.5.2.2>`: "If an attribute is removed or becomes unassigned and is defined as a required attribute [...] the server SHALL return [...] a "scimType" error code of "mutability"."."""
    payloads = [
        [{"op": "remove", "path": "userName"}],
        [{"op": "replace", "path": "userName", "value": None}],
        [{"op": "replace", "value": {"userName": None}}],
    ]
    for operations in payloads:
        with pytest.raises(ValidationError) as exc_info:
            PatchOp[User].model_validate(
                {
                    "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
                    "Operations": operations,
                },
                scim_ctx=Context.RESOURCE_PATCH_REQUEST,
            )
        assert exc_info.value.errors()[0]["type"] == "scim_mutability"


def test_an_operation_without_path_takes_a_model_as_value():
    """A client building its payload in Python passes a resource, where a server parses a dict."""
    patch = PatchOp[User](
        operations=[
            PatchOperation[User](
                op=PatchOperation.Op.replace_, value=User(display_name="Babs")
            )
        ]
    )
    user = User(id="srv-1", user_name="bjensen")
    assert patch.patch(user)
    assert user.display_name == "Babs"
    assert user.user_name == "bjensen"


def test_a_model_value_answers_to_the_same_constraints_as_a_dict_one():
    """The form the value takes says nothing about what the operation may write."""
    patch = PatchOp[User](
        operations=[
            PatchOperation[User](
                op=PatchOperation.Op.replace_,
                value=User(id="chosen-by-the-client"),
            )
        ]
    )
    user = User(id="srv-1", user_name="bjensen")

    with pytest.raises(MutabilityException):
        patch.patch(user)
    assert user.id == "srv-1"


def test_a_model_value_carries_the_attributes_its_payload_would():
    """A null attribute is not serialized, so it is neither written nor refused.

    Unassigning through an operation without a path takes the payload form,
    ``{"userName": null}``, which :rfc:`RFC7643 §2.5 <7643#section-2.5>` makes
    equivalent to an unassigned attribute.
    """
    patch = PatchOp[User](
        operations=[
            PatchOperation[User](
                op=PatchOperation.Op.replace_,
                value=User(user_name=None, display_name="Babs"),
            )
        ]
    )
    user = User(id="srv-1", user_name="bjensen")
    patch.patch(user)
    assert user.user_name == "bjensen"
    assert user.display_name == "Babs"


def test_a_urn_that_merely_starts_like_a_schema_reaches_no_attribute():
    """A schema URN carries an attribute behind a colon, not behind a prefix.

    Read as a prefix, ``…:2.0:UserId`` designates the ``Id`` attribute of
    ``…:2.0:User`` and writes a :attr:`~scim2_models.Mutability.read_only`
    attribute that every other spelling of it is refused.
    """
    with pytest.raises(ValidationError) as raised:
        PatchOp[User](
            operations=[
                PatchOperation[User](
                    op=PatchOperation.Op.replace_,
                    path="urn:ietf:params:scim:schemas:core:2.0:UserId",
                    value="forged",
                )
            ]
        )

    assert raised.value.errors()[0]["type"] == "scim_invalidPath"


def test_a_patch_path_naming_a_subattribute_of_a_scalar_answers_invalid_path():
    """A path no model can carry is answered, not crashed on.

    :rfc:`RFC7644 §3.12 <7644#section-3.12>` gives ``invalidPath`` for a path
    that is unknown, which a client may write without meaning to.
    """
    with pytest.raises(ValidationError) as raised:
        PatchOp[User](
            operations=[
                PatchOperation[User](
                    op=PatchOperation.Op.replace_, path="userName.foo", value="forged"
                )
            ]
        )

    assert raised.value.errors()[0]["type"] == "scim_invalidPath"


def _constrained_user():
    user = User[ConstrainedExtension](user_name="bjensen")
    user[ConstrainedExtension] = ConstrainedExtension(
        read_only_attr="original",
        immutable_attr="original",
        required_attr="original",
    )
    return user


@pytest.mark.parametrize(
    ("op", "attribute", "value"),
    [
        pytest.param("replace", "readOnlyAttr", "hijacked", id="read-only replaced"),
        pytest.param("add", "readOnlyAttr", "hijacked", id="read-only added"),
        pytest.param("replace", "immutableAttr", "hijacked", id="immutable replaced"),
        pytest.param("remove", "immutableAttr", None, id="immutable removed"),
        pytest.param("replace", "requiredAttr", None, id="required unassigned"),
        pytest.param("remove", "requiredAttr", None, id="required removed"),
    ],
)
def test_an_extension_attribute_answers_for_its_own_constraints(op, attribute, value):
    """The attribute a qualified path applies to is declared by the extension.

    The checks used to read the first segment of the path and look it up on the
    resource, which declares none of the attributes an extension holds, so every
    constraint an extension carried went unchecked.
    """
    user = _constrained_user()
    operation = {"op": op, "path": f"urn:example:2.0:Constrained:{attribute}"}
    if op != "remove":
        operation["value"] = value

    with pytest.raises((ValidationError, MutabilityException)):
        PatchOp[User[ConstrainedExtension]].model_validate(
            {"Operations": [operation]}
        ).patch(user)

    extension = user[ConstrainedExtension]
    assert extension.read_only_attr == "original"
    assert extension.immutable_attr == "original"
    assert extension.required_attr == "original"


def test_an_extension_attribute_without_a_constraint_is_written():
    """Resolving the path must not refuse what the extension allows."""
    user = _constrained_user()

    assert (
        PatchOp[User[ConstrainedExtension]]
        .model_validate(
            {
                "Operations": [
                    {
                        "op": "replace",
                        "path": "urn:example:2.0:Constrained:plainAttr",
                        "value": "written",
                    }
                ]
            }
        )
        .patch(user)
    )

    assert user[ConstrainedExtension].plain_attr == "written"


def test_an_immutable_extension_attribute_takes_the_value_it_already_has():
    """§3.5.2 lets a client add to an immutable attribute that has no value yet."""
    user = User[ConstrainedExtension](user_name="bjensen")
    user[ConstrainedExtension] = ConstrainedExtension(immutable_attr="original")
    patch = PatchOp[User[ConstrainedExtension]].model_validate(
        {
            "Operations": [
                {
                    "op": "replace",
                    "path": "urn:example:2.0:Constrained:immutableAttr",
                    "value": "original",
                }
            ]
        }
    )

    patch.patch(user)
    assert user[ConstrainedExtension].immutable_attr == "original"


def test_patch_selection_naming_an_unknown_attribute_fails_the_operation():
    """An attribute the model does not declare must not pass for a no-op success."""
    user = User(user_name="bjensen")
    patch = PatchOp[User](
        operations=[
            PatchOperation[User](
                op=PatchOperation.Op.add,
                path='emails[nonexistent eq "work"].value',
                value="bjensen@example.com",
            )
        ]
    )

    with pytest.raises(InvalidFilterException, match="nonexistent"):
        patch.patch(user)


def test_a_path_naming_an_attribute_no_model_declares_is_refused():
    """A path outside the resource schema is refused, as the same mistake without a path is."""
    with pytest.raises(ValidationError) as raised:
        PatchOp[User].model_validate(
            {
                "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
                "Operations": [{"op": "add", "path": "nonexistent", "value": "x"}],
            },
            scim_ctx=Context.RESOURCE_PATCH_REQUEST,
        )

    assert raised.value.errors()[0]["type"] == "scim_invalidPath"


def test_a_path_naming_a_subattribute_no_model_declares_is_refused():
    """A sub-attribute outside the schema of the attribute holding it is refused too."""
    with pytest.raises(ValidationError) as raised:
        PatchOp[User].model_validate(
            {
                "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
                "Operations": [
                    {"op": "replace", "path": "name.nonexistent", "value": "x"}
                ],
            },
            scim_ctx=Context.RESOURCE_PATCH_REQUEST,
        )

    assert raised.value.errors()[0]["type"] == "scim_invalidPath"


def test_a_path_designating_the_resource_itself_is_accepted():
    """The resource root names no attribute, and answers to the value as a pathless operation."""
    patch = PatchOp[User].model_validate(
        {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "Operations": [{"op": "add", "path": "", "value": {"nickName": "Babs"}}],
        },
        scim_ctx=Context.RESOURCE_PATCH_REQUEST,
    )

    user = User(user_name="bjensen")
    patch.patch(user)
    assert user.nick_name == "Babs"


CONSTRAINED_RESOURCE_URN = "urn:example:2.0:ConstrainedResource"
CONSTRAINED_EXTENSION_URN = "urn:example:2.0:Constrained"
CORE_USER_URN = "urn:ietf:params:scim:schemas:core:2.0:User"


def _constrained_resource():
    return ConstrainedResource(
        read_only_attr="original",
        immutable_attr="original",
        immutable_complex=ConstrainedComplex(label="original"),
        immutable_date=datetime(2020, 1, 1, tzinfo=UTC),
        immutable_list=[ConstrainedComplex(label="original")],
        required_attr="original",
    )


def _operation(op, path, value):
    operation = {"op": op, "value": value}
    if path is not None:
        operation["path"] = path
    return operation


RESOURCE_PATHS = [
    pytest.param(None, id="no path"),
    pytest.param("", id="empty path"),
    pytest.param(CONSTRAINED_RESOURCE_URN, id="schema URN"),
    pytest.param(CONSTRAINED_RESOURCE_URN.upper(), id="schema URN in capitals"),
]

USER_PATHS = [
    pytest.param(None, id="no path"),
    pytest.param("", id="empty path"),
    pytest.param(CORE_USER_URN, id="schema URN"),
    pytest.param(CORE_USER_URN.upper(), id="schema URN in capitals"),
]

VALIDATION_VIOLATIONS = [
    pytest.param("replace", "requiredAttr", None, id="required unassigned"),
]

APPLICATION_VIOLATIONS = [
    pytest.param("replace", "readOnlyAttr", "hijacked", id="read-only replaced"),
    pytest.param("add", "readOnlyAttr", "hijacked", id="read-only added"),
    pytest.param("replace", "immutableAttr", "hijacked", id="immutable replaced"),
    pytest.param("add", "immutableAttr", "hijacked", id="immutable added over a value"),
]


def _assert_constraints_kept(holder):
    assert holder.read_only_attr == "original"
    assert holder.immutable_attr == "original"
    assert holder.required_attr == "original"


def _assert_refused_for_mutability(raised):
    assert raised.value.errors()[0]["type"] == "scim_mutability"


@pytest.mark.parametrize("path", RESOURCE_PATHS)
@pytest.mark.parametrize(("op", "attribute", "value"), VALIDATION_VIOLATIONS)
def test_a_path_designating_the_resource_refuses_the_value_at_validation(
    path, op, attribute, value
):
    """When the path targets the resource, the value holds the attributes (RFC7644 §3.5.2.3)."""
    with pytest.raises(ValidationError) as raised:
        PatchOp[ConstrainedResource].model_validate(
            {"Operations": [_operation(op, path, {attribute: value})]},
            scim_ctx=Context.RESOURCE_PATCH_REQUEST,
        )

    _assert_refused_for_mutability(raised)


@pytest.mark.parametrize("path", RESOURCE_PATHS)
@pytest.mark.parametrize(("op", "attribute", "value"), APPLICATION_VIOLATIONS)
def test_a_path_designating_the_resource_refuses_a_constrained_change_when_applied(
    path, op, attribute, value
):
    """Only the resource tells whether the value changes a read-only or immutable attribute, so this is checked when the patch is applied."""
    resource = _constrained_resource()
    patch = PatchOp[ConstrainedResource].model_validate(
        {"Operations": [_operation(op, path, {attribute: value})]},
        scim_ctx=Context.RESOURCE_PATCH_REQUEST,
    )

    with pytest.raises(MutabilityException):
        patch.patch(resource)

    _assert_constraints_kept(resource)


@pytest.mark.parametrize("path", USER_PATHS)
@pytest.mark.parametrize(
    "value",
    [
        pytest.param({"id": "other-id"}, id="id"),
        pytest.param({"groups": [{"value": "admins"}]}, id="groups"),
        pytest.param({"meta": {"version": 'W/"999"'}}, id="meta"),
    ],
)
def test_a_path_designating_the_resource_cannot_rewrite_its_identity(path, value):
    """The read-only attributes of a user are rejected, whatever path targets the user."""
    user = User(id="srv-1", user_name="bjensen")
    patch = PatchOp[User].model_validate(
        {"Operations": [_operation("replace", path, value)]},
        scim_ctx=Context.RESOURCE_PATCH_REQUEST,
    )

    with pytest.raises(MutabilityException):
        patch.patch(user)
    assert user.id == "srv-1"
    assert user.groups is None
    assert user.meta is None


@pytest.mark.parametrize("path", RESOURCE_PATHS)
@pytest.mark.parametrize(
    ("op", "attribute", "value"),
    [
        pytest.param("replace", "plainAttr", "written", id="plain replaced"),
        pytest.param("replace", "immutableAttr", "original", id="immutable kept"),
        pytest.param("replace", "readOnlyAttr", "original", id="read-only kept"),
        pytest.param("add", "readOnlyAttr", "original", id="read-only added unchanged"),
    ],
)
def test_a_path_designating_the_resource_writes_what_the_schema_allows(
    path, op, attribute, value
):
    """The checks reject what the constraints forbid, and nothing else."""
    resource = _constrained_resource()

    PatchOp[ConstrainedResource].model_validate(
        {"Operations": [_operation(op, path, {attribute: value})]},
        scim_ctx=Context.RESOURCE_PATCH_REQUEST,
    ).patch(resource)

    assert resource.model_dump(by_alias=True)[attribute] == value


IMMUTABLE_VALUES_AS_SPELLED = [
    pytest.param("immutableAttr", "original", id="string"),
    pytest.param("immutableComplex", {"LABEL": "original"}, id="complex"),
    pytest.param("immutableDate", "2020-01-01T00:00:00Z", id="datetime"),
    pytest.param("immutableList", [{"label": "original"}], id="multi-valued"),
]


def test_an_immutable_multi_valued_attribute_takes_back_its_entries_in_another_order():
    """RFC7643 §2.4 gives no significance to the order of a multi-valued attribute."""
    resource = _constrained_resource()
    resource.immutable_list = [
        ConstrainedComplex(label="first"),
        ConstrainedComplex(label="second"),
    ]
    patch = PatchOp[ConstrainedResource].model_validate(
        {
            "Operations": [
                _operation(
                    "replace",
                    None,
                    {"immutableList": [{"label": "second"}, {"label": "first"}]},
                )
            ]
        },
        scim_ctx=Context.RESOURCE_PATCH_REQUEST,
    )

    patch.patch(resource)

    assert {entry.label for entry in resource.immutable_list} == {"first", "second"}


@pytest.mark.parametrize(
    "value",
    [
        pytest.param([{"label": "original"}, {"label": "other"}], id="entry added"),
        pytest.param([{"label": "other"}], id="entry replaced"),
    ],
)
def test_an_immutable_multi_valued_attribute_refuses_other_entries(value):
    """Comparing entries regardless of order still detects a different collection."""
    resource = _constrained_resource()
    patch = PatchOp[ConstrainedResource].model_validate(
        {"Operations": [_operation("replace", None, {"immutableList": value})]},
        scim_ctx=Context.RESOURCE_PATCH_REQUEST,
    )

    with pytest.raises(MutabilityException):
        patch.patch(resource)

    assert resource.immutable_list == [ConstrainedComplex(label="original")]


@pytest.mark.parametrize("op", ["add", "replace"])
@pytest.mark.parametrize(("attribute", "value"), IMMUTABLE_VALUES_AS_SPELLED)
@pytest.mark.parametrize("path", RESOURCE_PATHS)
def test_an_immutable_attribute_takes_back_the_value_it_holds_through_the_value(
    path, attribute, value, op
):
    """A client that sends the whole state sends the current value of an immutable attribute as JSON."""
    resource = _constrained_resource()
    patch = PatchOp[ConstrainedResource].model_validate(
        {"Operations": [_operation(op, path, {attribute: value})]},
        scim_ctx=Context.RESOURCE_PATCH_REQUEST,
    )

    patch.patch(resource)

    assert resource.model_dump() == _constrained_resource().model_dump()


@pytest.mark.parametrize("op", ["add", "replace"])
@pytest.mark.parametrize(("attribute", "value"), IMMUTABLE_VALUES_AS_SPELLED)
def test_an_immutable_attribute_takes_back_the_value_it_holds_through_an_attribute_path(
    attribute, value, op
):
    """RFC7644 §3.5.2.1 makes no change when the target already holds the value."""
    resource = _constrained_resource()
    patch = PatchOp[ConstrainedResource].model_validate(
        {"Operations": [_operation(op, attribute, value)]},
        scim_ctx=Context.RESOURCE_PATCH_REQUEST,
    )

    patch.patch(resource)

    assert resource.model_dump() == _constrained_resource().model_dump()


def test_an_immutable_attribute_refuses_a_value_its_type_does_not_accept():
    """A value the attribute rejects is reported as invalid before any mutability check."""
    resource = _constrained_resource()
    patch = PatchOp[ConstrainedResource].model_validate(
        {"Operations": [_operation("replace", None, {"immutableDate": "not a date"})]},
        scim_ctx=Context.RESOURCE_PATCH_REQUEST,
    )

    with pytest.raises(InvalidValueException):
        patch.patch(resource)

    assert resource.immutable_date == datetime(2020, 1, 1, tzinfo=UTC)


@pytest.mark.parametrize("op", ["add", "replace"])
@pytest.mark.parametrize(
    "path", [*RESOURCE_PATHS, pytest.param("immutableAttr", id="attribute path")]
)
def test_an_immutable_attribute_without_value_takes_its_first_value(path, op):
    """§3.5.2 lets a client assign an immutable attribute with no value, and §3.5.2.3 treats a replace on it as an add."""
    resource = ConstrainedResource(required_attr="original")
    value = "first" if path == "immutableAttr" else {"immutableAttr": "first"}

    PatchOp[ConstrainedResource].model_validate(
        {"Operations": [_operation(op, path, value)]},
        scim_ctx=Context.RESOURCE_PATCH_REQUEST,
    ).patch(resource)

    assert resource.immutable_attr == "first"


def test_a_path_designating_the_resource_refuses_an_undeclared_attribute():
    """An attribute the schema URN does not declare is incompatible with the resource schema."""
    with pytest.raises(ValidationError) as raised:
        PatchOp[ConstrainedResource].model_validate(
            {
                "Operations": [
                    _operation("replace", CONSTRAINED_RESOURCE_URN, {"whatever": "x"})
                ]
            },
            scim_ctx=Context.RESOURCE_PATCH_REQUEST,
        )

    assert raised.value.errors()[0]["type"] == "scim_invalidValue"


@pytest.mark.parametrize("path", ["", CORE_USER_URN])
def test_a_path_designating_the_resource_writes_a_resource_given_as_value(path):
    """A resource given as the value writes the attributes it was checked against."""
    user = User(user_name="bjensen")
    patch = PatchOp[User](
        operations=[
            PatchOperation[User](
                op=PatchOperation.Op.replace_, path=path, value=User(nick_name="Babs")
            )
        ]
    )

    assert patch.patch(user)
    assert user.nick_name == "Babs"


@pytest.mark.parametrize(
    "path",
    [
        pytest.param("", id="empty path"),
        pytest.param(CORE_USER_URN, id="resource schema URN"),
        pytest.param(CONSTRAINED_EXTENSION_URN, id="extension schema URN"),
    ],
)
def test_a_remove_selecting_by_value_needs_a_path_to_an_attribute(path):
    """Under the apply policy the value of a remove selects entries of the attribute in its path."""
    with pytest.raises(ValidationError) as raised:
        PatchOp[User[ConstrainedExtension]].model_validate(
            {"Operations": [_operation("remove", path, [{"plainAttr": "x"}])]},
            scim_ctx=Context.RESOURCE_PATCH_REQUEST,
            scim_policy=ScimPolicy(remove_value_as_filter=ScimPolicy.RemoveValue.apply),
        )

    assert raised.value.errors()[0]["type"] == "scim_invalidPath"


def test_a_remove_on_the_schema_urn_of_an_extension_unassigns_it():
    """An extension is not an attribute of the resource, so it is not required."""
    user = User[ConstrainedExtension](user_name="bjensen")
    user[ConstrainedExtension] = ConstrainedExtension(
        required_attr="original", plain_attr="original"
    )

    PatchOp[User[ConstrainedExtension]].model_validate(
        {"Operations": [{"op": "remove", "path": CONSTRAINED_EXTENSION_URN}]},
        scim_ctx=Context.RESOURCE_PATCH_REQUEST,
    ).patch(user)

    assert user[ConstrainedExtension] is None


EXTENSION_TARGETS = [
    pytest.param(None, CONSTRAINED_EXTENSION_URN, id="no path"),
    pytest.param(
        None, CONSTRAINED_EXTENSION_URN.upper(), id="no path, key in capitals"
    ),
    pytest.param("", CONSTRAINED_EXTENSION_URN, id="empty path"),
    pytest.param(CORE_USER_URN, CONSTRAINED_EXTENSION_URN, id="resource schema URN"),
    pytest.param(CONSTRAINED_EXTENSION_URN, None, id="extension schema URN"),
    pytest.param(
        CONSTRAINED_EXTENSION_URN.upper(), None, id="extension schema URN in capitals"
    ),
]


def _extension_value(key, attribute, value):
    written = {attribute: value}
    return {key: written} if key is not None else written


@pytest.mark.parametrize(("path", "key"), EXTENSION_TARGETS)
@pytest.mark.parametrize(("op", "attribute", "value"), VALIDATION_VIOLATIONS)
def test_an_extension_in_the_value_refuses_its_constrained_attributes_at_validation(
    path, key, op, attribute, value
):
    """The attributes of an extension in the value follow the constraints the extension declares."""
    with pytest.raises(ValidationError) as raised:
        PatchOp[User[ConstrainedExtension]].model_validate(
            {
                "Operations": [
                    _operation(op, path, _extension_value(key, attribute, value))
                ]
            },
            scim_ctx=Context.RESOURCE_PATCH_REQUEST,
        )

    _assert_refused_for_mutability(raised)


@pytest.mark.parametrize(("path", "key"), EXTENSION_TARGETS)
@pytest.mark.parametrize(("op", "attribute", "value"), APPLICATION_VIOLATIONS)
def test_an_extension_in_the_value_refuses_a_constrained_change_when_applied(
    path, key, op, attribute, value
):
    """A read-only or immutable attribute of an extension in the value is protected once it has a value."""
    user = _constrained_user()
    patch = PatchOp[User[ConstrainedExtension]].model_validate(
        {"Operations": [_operation(op, path, _extension_value(key, attribute, value))]},
        scim_ctx=Context.RESOURCE_PATCH_REQUEST,
    )

    with pytest.raises(MutabilityException):
        patch.patch(user)

    _assert_constraints_kept(user[ConstrainedExtension])


@pytest.mark.parametrize(("path", "key"), EXTENSION_TARGETS)
def test_an_extension_in_the_value_refuses_an_attribute_it_does_not_declare(path, key):
    """An attribute outside the extension schema is incompatible with it."""
    with pytest.raises(ValidationError) as raised:
        PatchOp[User[ConstrainedExtension]].model_validate(
            {
                "Operations": [
                    _operation("replace", path, _extension_value(key, "whatever", "x"))
                ]
            },
            scim_ctx=Context.RESOURCE_PATCH_REQUEST,
        )

    assert raised.value.errors()[0]["type"] == "scim_invalidValue"


def _user_with_hijacked_extension():
    user = User[ConstrainedExtension]()
    user[ConstrainedExtension] = ConstrainedExtension(read_only_attr="hijacked")
    return user


@pytest.mark.parametrize(
    ("path", "value"),
    [
        pytest.param(
            CONSTRAINED_EXTENSION_URN,
            ConstrainedExtension(read_only_attr="hijacked"),
            id="extension on its schema URN",
        ),
        pytest.param(None, _user_with_hijacked_extension(), id="resource without path"),
    ],
)
def test_an_extension_given_as_a_model_answers_for_its_own_constraints(path, value):
    """A value built in Python is checked like the same value in a payload."""
    user = _constrained_user()
    patch = PatchOp[User[ConstrainedExtension]](
        operations=[
            PatchOperation[User[ConstrainedExtension]](
                op=PatchOperation.Op.replace_, path=path, value=value
            )
        ]
    )

    with pytest.raises(MutabilityException):
        patch.patch(user)
    _assert_constraints_kept(user[ConstrainedExtension])


def _unvalidated_patch_writing_an_undeclared_attribute():
    return PatchOp[ConstrainedResource].model_construct(
        operations=[
            PatchOperation[ConstrainedResource].model_construct(
                op=PatchOperation.Op.replace_, path=None, value={"whatever": "x"}
            )
        ]
    )


def test_an_unvalidated_patch_refuses_an_undeclared_attribute_when_applied():
    """The policy passed to patch decides what happens to undeclared attributes."""
    patch = _unvalidated_patch_writing_an_undeclared_attribute()

    with pytest.raises(InvalidValueException):
        patch.patch(_constrained_resource())


def test_an_unvalidated_patch_drops_an_undeclared_attribute_under_a_tolerant_policy():
    """A tolerant policy drops the attribute, and the operation writes nothing."""
    patch = _unvalidated_patch_writing_an_undeclared_attribute()
    tolerant = ScimPolicy(unknown=ScimPolicy.Unknown.ignore)

    assert patch.patch(_constrained_resource(), scim_policy=tolerant) is False


def test_an_unvalidated_patch_leaves_an_undeclared_path_to_the_write():
    """An undeclared path has no immutability constraint, and fails when the write finds no field."""
    resource = _constrained_resource()
    patch = PatchOp[ConstrainedResource].model_construct(
        operations=[
            PatchOperation[ConstrainedResource].model_construct(
                op=PatchOperation.Op.replace_,
                path=Path[ConstrainedResource]("whatever"),
                value="x",
            )
        ]
    )

    with pytest.raises(PathNotFoundException):
        patch.patch(resource)


def test_a_remove_without_path_carrying_a_value_has_no_target_outside_a_request():
    """RFC7644 §3.5.2.2 returns noTarget for a remove without a path, whatever its value."""
    patch = PatchOp[User].model_validate(
        {"Operations": [{"op": "remove", "value": {"nickName": "x"}}]}
    )

    with pytest.raises(NoTargetException):
        patch.patch(User(user_name="bjensen"))


def test_a_remove_carrying_a_value_on_a_schema_urn_is_refused_by_default_outside_a_request():
    """Without the apply policy, the value of a remove is rejected, as on any path."""
    patch = PatchOp[User].model_validate(
        {
            "Operations": [
                {"op": "remove", "path": CORE_USER_URN, "value": [{"nickName": "x"}]}
            ]
        }
    )

    with pytest.raises(InvalidValueException):
        patch.patch(User(user_name="bjensen"))


@pytest.mark.parametrize(
    "unknown", [ScimPolicy.Unknown.ignore, ScimPolicy.Unknown.keep], ids=str
)
@pytest.mark.parametrize(("path", "key"), EXTENSION_TARGETS)
def test_a_tolerant_policy_writes_the_declared_attributes_beside_an_undeclared_one(
    path, key, unknown
):
    """The unknown policy applies to the value of a patch as it does to a resource."""
    policy = ScimPolicy(unknown=unknown)
    user = _constrained_user()
    value = _extension_value(key, "plainAttr", "written")
    if key is not None:
        value[key]["whatever"] = "x"
    else:
        value["whatever"] = "x"

    PatchOp[User[ConstrainedExtension]].model_validate(
        {"Operations": [_operation("replace", path, value)]},
        scim_ctx=Context.RESOURCE_PATCH_REQUEST,
        scim_policy=policy,
    ).patch(user, scim_policy=policy)

    dumped = user.model_dump(scim_ctx=Context.RESOURCE_QUERY_RESPONSE)
    assert dumped[CONSTRAINED_EXTENSION_URN]["plainAttr"] == "written"
    assert "whatever" not in dumped[CONSTRAINED_EXTENSION_URN]


@pytest.mark.parametrize(
    "unknown", [ScimPolicy.Unknown.ignore, ScimPolicy.Unknown.keep], ids=str
)
@pytest.mark.parametrize("path", RESOURCE_PATHS)
def test_a_tolerant_policy_drops_an_undeclared_attribute_of_the_resource(path, unknown):
    """An undeclared attribute has no field to write to."""
    policy = ScimPolicy(unknown=unknown)
    resource = _constrained_resource()

    PatchOp[ConstrainedResource].model_validate(
        {"Operations": [_operation("replace", path, {"plainAttr": "w", "zzz": "x"})]},
        scim_ctx=Context.RESOURCE_PATCH_REQUEST,
        scim_policy=policy,
    ).patch(resource, scim_policy=policy)

    assert resource.plain_attr == "w"
    assert "zzz" not in resource.model_dump()


EXTENSION_UNASSIGNMENTS = [
    pytest.param(
        {"op": "remove", "path": CONSTRAINED_EXTENSION_URN}, id="removed by URN"
    ),
    pytest.param(
        {"op": "replace", "value": {CONSTRAINED_EXTENSION_URN: None}},
        id="null key without path",
    ),
    pytest.param(
        {"op": "replace", "path": "", "value": {CONSTRAINED_EXTENSION_URN: None}},
        id="null key on the empty path",
    ),
    pytest.param(
        {
            "op": "replace",
            "path": CORE_USER_URN,
            "value": {CONSTRAINED_EXTENSION_URN: None},
        },
        id="null key on the resource URN",
    ),
]


@pytest.mark.parametrize("operation", EXTENSION_UNASSIGNMENTS)
def test_an_extension_holding_an_immutable_value_cannot_be_unassigned(operation):
    """Unassigning an extension changes its immutable attributes, which RFC7644 §3.5.2 forbids once they hold a value."""
    user = _constrained_user()
    patch = PatchOp[User[ConstrainedExtension]].model_validate(
        {"Operations": [operation]}, scim_ctx=Context.RESOURCE_PATCH_REQUEST
    )

    with pytest.raises(MutabilityException):
        patch.patch(user)

    _assert_constraints_kept(user[ConstrainedExtension])


@pytest.mark.parametrize("operation", EXTENSION_UNASSIGNMENTS)
def test_an_extension_without_immutable_value_can_be_unassigned(operation):
    """Unassigning an extension does not change an immutable attribute that has no value yet."""
    user = User[ConstrainedExtension](user_name="bjensen")
    user[ConstrainedExtension] = ConstrainedExtension(
        read_only_attr="original", required_attr="original"
    )

    PatchOp[User[ConstrainedExtension]].model_validate(
        {"Operations": [operation]}, scim_ctx=Context.RESOURCE_PATCH_REQUEST
    ).patch(user)

    assert user[ConstrainedExtension] is None


@pytest.mark.parametrize("path", ["", CORE_USER_URN])
def test_a_remove_designating_the_resource_itself_is_refused(path):
    """A remove on the resource root has no attribute to unassign."""
    patch = PatchOp[User].model_validate(
        {"Operations": [{"op": "remove", "path": path}]},
        scim_ctx=Context.RESOURCE_PATCH_REQUEST,
    )

    with pytest.raises(InvalidPathException):
        patch.patch(User(user_name="bjensen"))


def test_building_the_unassignment_of_an_extension_holding_an_immutable_value_is_refused():
    """The peer would reject the patch, so building it fails."""
    after = User[ConstrainedExtension](user_name="bjensen")
    after.ConstrainedExtension = None

    with pytest.raises(MutabilityException):
        PatchOp.build_from(_constrained_user(), after)


def test_the_unassignment_built_for_an_extension_without_immutable_value_applies():
    """A patch built from two states is one the resource accepts."""
    before = User[ConstrainedExtension](user_name="bjensen")
    before[ConstrainedExtension] = ConstrainedExtension(plain_attr="original")
    after = User[ConstrainedExtension](user_name="bjensen")
    after.ConstrainedExtension = None

    patch = PatchOp.build_from(before, after)

    assert patch.patch(before)
    assert before[ConstrainedExtension] is None


def test_a_replace_unassigning_its_target_keeps_its_null_value_when_dumped():
    """A replace dumped without its value would be read back as missing its value."""
    patch = PatchOp[User](
        operations=[PatchOperation[User](op="replace", path="title", value=None)]
    )

    payload = patch.model_dump(scim_ctx=Context.RESOURCE_PATCH_REQUEST)

    assert payload["Operations"] == [{"op": "replace", "path": "title", "value": None}]
    user = User(user_name="bjensen", title="CEO")
    PatchOp[User].model_validate(
        payload, scim_ctx=Context.RESOURCE_PATCH_REQUEST
    ).patch(user)
    assert user.title is None


def test_an_operation_given_no_value_is_dumped_without_one():
    """Only a null value the operation was given is kept in the dump."""
    operation = PatchOperation[User](op="replace", path="title")

    assert operation.model_dump(scim_ctx=Context.RESOURCE_PATCH_REQUEST) == {
        "op": "replace",
        "path": "title",
    }


def test_a_remove_given_a_null_value_is_dumped_without_one():
    """RFC7644 §3.5.2.2 reads a remove from its path only, so a null value is left out."""
    operation = PatchOperation[User](op="remove", path="title", value=None)

    assert operation.model_dump(scim_ctx=Context.RESOURCE_PATCH_REQUEST) == {
        "op": "remove",
        "path": "title",
    }


@pytest.mark.parametrize("path", [None, "nickName"])
def test_a_replace_needs_a_value(path):
    """RFC7644 §3.5.2.3 replaces the target with the value, and a missing one would read as null."""
    operation = {"op": "replace"} if path is None else {"op": "replace", "path": path}

    with pytest.raises(ValidationError) as raised:
        PatchOp[User].model_validate(
            {"Operations": [operation]}, scim_ctx=Context.RESOURCE_PATCH_REQUEST
        )

    assert raised.value.errors()[0]["type"] == "scim_invalidValue"


@pytest.mark.parametrize("op", ["add", "replace"])
@pytest.mark.parametrize("value", ["Babs", ["Babs"], None])
@pytest.mark.parametrize("path", [*USER_PATHS, CONSTRAINED_EXTENSION_URN])
def test_a_path_designating_a_model_needs_an_object_value(op, value, path):
    """RFC7644 §3.5.2.1 and §3.5.2.3 require that value to be a set of attributes."""
    with pytest.raises(ValidationError) as raised:
        PatchOp[User[ConstrainedExtension]].model_validate(
            {"Operations": [_operation(op, path, value)]}
        )

    assert raised.value.errors()[0]["type"] == "scim_invalidValue"


@pytest.mark.parametrize("path", [None, CONSTRAINED_EXTENSION_URN])
def test_an_unvalidated_non_object_value_is_refused_when_applied(path):
    """A patch built in Python reaches no validator, and is refused when applied."""
    patch = PatchOp[User[ConstrainedExtension]].model_construct(
        operations=[
            PatchOperation[User[ConstrainedExtension]].model_construct(
                op=PatchOperation.Op.add,
                path=None if path is None else Path[User[ConstrainedExtension]](path),
                value="Babs",
            )
        ]
    )

    with pytest.raises(InvalidValueException):
        patch.patch(User[ConstrainedExtension](user_name="bjensen"))


@pytest.mark.parametrize("path", USER_PATHS)
def test_an_extension_in_a_value_needs_an_object(path):
    """An extension is a container of attributes, not a value of its own."""
    with pytest.raises(ValidationError) as raised:
        PatchOp[User[ConstrainedExtension]].model_validate(
            {"Operations": [_operation("add", path, {CONSTRAINED_EXTENSION_URN: "x"})]}
        )

    assert raised.value.errors()[0]["type"] == "scim_invalidValue"


def _group_with_member():
    return Group(
        display_name="Tour Guides", members=[{"value": "2819c223", "display": "Babs"}]
    )


@pytest.mark.parametrize(
    "path", ['members[value eq "2819c223"].value', "members.value"]
)
def test_an_immutable_sub_attribute_of_an_entry_cannot_change(path):
    """RFC7643 §4.2 lets members be added and removed, and makes their sub-attributes immutable."""
    group = _group_with_member()
    patch = PatchOp[Group].model_validate(
        {"Operations": [{"op": "replace", "path": path, "value": "c3a26dd3"}]}
    )

    with pytest.raises(MutabilityException):
        patch.patch(group)

    assert group.members[0].value == "2819c223"


def test_a_mutable_sub_attribute_of_an_entry_may_change():
    """Only the sub-attributes declared immutable must keep their value."""
    group = _group_with_member()
    patch = PatchOp[Group].model_validate(
        {
            "Operations": [
                {
                    "op": "replace",
                    "path": 'members[value eq "2819c223"].display',
                    "value": "Barbara",
                }
            ]
        }
    )

    assert patch.patch(group)
    assert group.members[0].display == "Barbara"


def test_an_entry_holding_immutable_sub_attributes_may_be_removed():
    """Removing a member changes none of the sub-attributes of the ones left."""
    group = Group(
        display_name="Tour Guides",
        members=[{"value": "2819c223"}, {"value": "c3a26dd3"}],
    )
    patch = PatchOp[Group].model_validate(
        {"Operations": [{"op": "remove", "path": 'members[value eq "2819c223"]'}]}
    )

    assert patch.patch(group)
    assert [member.value for member in group.members] == ["c3a26dd3"]


def test_an_entry_kept_through_an_assignment_is_the_same_object():
    """Entries are told apart by identity, which assigning a list must keep."""
    group = _group_with_member()
    member = group.members[0]

    group.members = [*group.members, Group.Members(value="c3a26dd3")]

    assert group.members[0] is member


@pytest.mark.parametrize("op", ["add", "replace"])
def test_an_immutable_complex_takes_back_the_sub_attribute_it_holds(op):
    """Writing the value a sub-attribute holds modifies nothing."""
    resource = _constrained_resource()
    patch = PatchOp[ConstrainedResource].model_validate(
        {"Operations": [_operation(op, "immutableComplex.label", "original")]}
    )

    assert patch.patch(resource) is False


def test_an_immutable_complex_refuses_a_new_sub_attribute_value():
    """A complex attribute holding a value is immutable down to its sub-attributes."""
    resource = _constrained_resource()
    patch = PatchOp[ConstrainedResource].model_validate(
        {"Operations": [_operation("replace", "immutableComplex.label", "changed")]}
    )

    with pytest.raises(MutabilityException):
        patch.patch(resource)


def test_a_remove_selecting_nothing_in_an_immutable_attribute_is_accepted():
    """Per RFC7644 §3.5.2.2, a remove that selects nothing changes nothing."""
    resource = _constrained_resource()
    patch = PatchOp[ConstrainedResource].model_validate(
        {"Operations": [{"op": "remove", "path": 'immutableList[label eq "none"]'}]}
    )

    assert patch.patch(resource) is False


class StampedEntry(ComplexAttribute):
    value: str | None = None
    stamp: Annotated[str | None, Mutability.read_only] = None


class StampedResource(Resource):
    __schema__ = URN("urn:example:2.0:StampedResource")

    entries: list[StampedEntry] | None = None


def _stamped():
    return StampedResource(entries=[StampedEntry(value="a", stamp="server")])


def _replace_entry(value):
    return PatchOp[StampedResource].model_validate(
        {
            "Operations": [
                {"op": "replace", "path": 'entries[value eq "a"]', "value": value}
            ]
        }
    )


def test_an_entry_written_back_with_its_read_only_sub_attribute_is_accepted():
    """An entry sent as it was read changes none of its read-only sub-attributes."""
    resource = _stamped()

    assert _replace_entry({"value": "a", "stamp": "server"}).patch(resource) is False


def test_an_entry_cannot_change_its_read_only_sub_attribute():
    """RFC7644 §3.5.2 forbids changing a read-only attribute, including a sub-attribute of an entry."""
    resource = _stamped()

    with pytest.raises(MutabilityException):
        _replace_entry({"value": "a", "stamp": "client"}).patch(resource)


def test_an_added_entry_cannot_assign_a_read_only_sub_attribute():
    """A client cannot set a read-only sub-attribute, even on an entry it adds."""
    resource = _stamped()
    patch = PatchOp[StampedResource].model_validate(
        {
            "Operations": [
                {
                    "op": "add",
                    "path": "entries",
                    "value": [{"value": "b", "stamp": "client"}],
                }
            ]
        }
    )

    with pytest.raises(MutabilityException):
        patch.patch(resource)


class Tag(ComplexAttribute):
    value: str | None = None


class Parts(ComplexAttribute):
    first: str | None = None
    last: str | None = None


class Contact(ComplexAttribute):
    value: Annotated[str | None, Required.true] = None
    label: str | None = None


class RequiringResource(Resource):
    __schema__ = URN("urn:example:2.0:RequiringResource")

    tags: Annotated[list[Tag] | None, Required.true] = None
    parts: Annotated[Parts | None, Required.true] = None
    contact: Contact | None = None


def _requiring():
    return RequiringResource(
        tags=[Tag(value="a"), Tag(value="b")],
        parts=Parts(first="Barbara", last="Jensen"),
        contact=Contact(value="555", label="work"),
    )


def _apply(operation):
    patch = PatchOp[RequiringResource].model_validate({"Operations": [operation]})
    resource = _requiring()
    return patch.patch(resource), resource


@pytest.mark.parametrize(
    "operation",
    [
        pytest.param(
            {"op": "remove", "path": 'tags[value eq "a"]'}, id="some entries removed"
        ),
        pytest.param(
            {"op": "remove", "path": 'tags[value eq "none"]'}, id="no entry selected"
        ),
        pytest.param(
            {"op": "remove", "path": "parts.first"}, id="a sub-attribute removed"
        ),
        pytest.param({"op": "add", "path": "tags", "value": []}, id="no value added"),
        pytest.param(
            {"op": "remove", "path": "contact"},
            id="a required sub-attribute removed with its parent",
        ),
    ],
)
def test_a_required_attribute_left_assigned_is_accepted(operation):
    """RFC7644 §3.5.2.2 only rejects a required attribute that is removed or becomes unassigned."""
    _, resource = _apply(operation)

    assert resource.tags
    assert resource.parts


@pytest.mark.parametrize(
    "operation",
    [
        pytest.param(
            {"op": "remove", "path": 'tags[value eq "a" or value eq "b"]'},
            id="every entry removed",
        ),
        pytest.param(
            {"op": "replace", "path": "parts", "value": {"first": None, "last": None}},
            id="every sub-attribute unassigned",
        ),
        pytest.param(
            {"op": "remove", "path": "contact.value"},
            id="required sub-attribute removed",
        ),
    ],
)
def test_a_required_attribute_becoming_unassigned_is_refused_when_applied(operation):
    """Only the result of the patch shows that a required attribute became unassigned."""
    patch = PatchOp[RequiringResource].model_validate({"Operations": [operation]})
    resource = _requiring()

    with pytest.raises(MutabilityException):
        patch.patch(resource)

    assert resource == _requiring()


def test_a_required_extension_cannot_be_removed():
    """Per RFC7643 §6, a resource includes the extensions its resource type requires."""
    model = User[Annotated[ConstrainedExtension, Required.true]]
    user = model(user_name="bjensen")
    user[ConstrainedExtension] = ConstrainedExtension(plain_attr="x")
    patch = PatchOp[model].model_validate(
        {"Operations": [{"op": "remove", "path": CONSTRAINED_EXTENSION_URN}]}
    )

    with pytest.raises(MutabilityException):
        patch.patch(user)


def test_a_patch_without_any_operation_is_refused():
    """RFC7644 §3.5.2 requires "Operations" to hold at least one operation."""
    with pytest.raises(ValidationError) as raised:
        PatchOp[User].model_validate({"Operations": []})

    assert raised.value.errors()[0]["type"] == "scim_invalidValue"


@pytest.mark.parametrize("op", ["move", "copy", 1])
def test_an_unknown_operation_is_refused(op):
    """RFC7644 §3.5.2 defines add, remove and replace, and §3.12 gives invalidValue for anything else."""
    with pytest.raises(ValidationError) as raised:
        PatchOp[User].model_validate(
            {"Operations": [{"op": op, "path": "nickName", "value": "Babs"}]}
        )

    assert raised.value.errors()[0]["type"] == "scim_invalidValue"


def test_an_add_with_a_null_value_is_refused():
    """RFC7644 §3.5.2.1 requires an add to carry a value, and null is not one."""
    with pytest.raises(ValidationError) as raised:
        PatchOp[User].model_validate(
            {"Operations": [{"op": "add", "path": "nickName", "value": None}]},
            scim_ctx=Context.RESOURCE_PATCH_REQUEST,
        )

    assert raised.value.errors()[0]["type"] == "scim_invalidValue"


@pytest.mark.parametrize("op", ["add", "replace"])
def test_an_empty_value_on_a_read_only_attribute_is_refused(op):
    """The path points to a read-only attribute, whatever the value writes under it."""
    with pytest.raises(ValidationError) as raised:
        PatchOp[Group].model_validate(
            {"Operations": [{"op": op, "path": "meta", "value": {}}]},
            scim_ctx=Context.RESOURCE_PATCH_REQUEST,
        )

    assert raised.value.errors()[0]["type"] == "scim_mutability"


@pytest.mark.parametrize(
    "policy",
    [
        ScimPolicy(unknown=ScimPolicy.Unknown.ignore),
        ScimPolicy(unknown=ScimPolicy.Unknown.keep),
    ],
    ids=["ignore", "keep"],
)
def test_a_remove_value_on_an_undeclared_path_is_refused_under_a_tolerant_policy(
    policy,
):
    """The value of a remove is rejected before the path is dropped."""
    with pytest.raises(ValidationError) as raised:
        PatchOp[User].model_validate(
            {"Operations": [{"op": "remove", "path": "whatever", "value": "x"}]},
            scim_ctx=Context.RESOURCE_PATCH_REQUEST,
            scim_policy=policy,
        )

    assert raised.value.errors()[0]["type"] == "scim_invalidValue"


def test_a_path_nested_too_deep_is_rejected_as_an_invalid_path():
    """A deeply nested path is a client error, not a failure of the server."""
    deep = "emails[" + "not(" * 1000 + "value pr" + ")" * 1000 + "].type"
    with pytest.raises(ValidationError, match="nests more than 32") as raised:
        PatchOp[User].model_validate(
            {"Operations": [{"op": "replace", "path": deep, "value": "work"}]}
        )
    assert raised.value.errors()[0]["type"] == "scim_invalidPath"
