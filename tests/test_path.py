"""Tests for SCIM path validation utilities."""

from typing import Any

import pydantic
import pytest

from scim2_models import Email
from scim2_models import EnterpriseUser
from scim2_models import Group
from scim2_models import InvalidPathException
from scim2_models import Manager
from scim2_models import Mutability
from scim2_models import Name
from scim2_models import PathNotFoundException
from scim2_models import Required
from scim2_models import User
from scim2_models.base import BaseModel
from scim2_models.path import Path


def test_validate_scim_path_syntax_valid_paths():
    """Test that valid SCIM paths are accepted."""
    valid_paths = [
        "userName",
        "name.familyName",
        "emails.value",
        "groups.display",
        "urn:ietf:params:scim:schemas:core:2.0:User:userName",
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:employeeNumber",
        'emails[type eq "work"].value',
        'groups[display eq "Admin"]',
        "meta.lastModified",
        "a",  # Single character
        "a.b",  # Simple dotted
        "a_b",  # Underscore
        "a-b",  # Hyphen
    ]

    for path in valid_paths:
        Path(path)


def test_validate_scim_path_syntax_invalid_paths():
    """Test that invalid SCIM paths are rejected."""
    invalid_paths = [
        "   ",  # Whitespace only
        "123invalid",  # Starts with digit
        "invalid..path",  # Double dots
        "invalid@path",  # Invalid character
        "urn:invalid",  # Invalid URN format
        "urn:too:short",  # URN too short
        "urn:ending:with:a:comma:",  # URN ending with a comma
    ]

    for path in invalid_paths:
        with pytest.raises(ValueError):
            Path(path)


def test_empty_path_is_valid():
    """Empty path represents the resource root."""
    path = Path("")
    assert str(path) == ""


def test_path_generic_type_is_accepted():
    """Path with or without type parameter accepts any valid syntax."""

    class ModelWithType(BaseModel):
        path: Path[User]

    class ModelWithoutType(BaseModel):
        path: Path

    ModelWithType.model_validate({"path": "userName"})
    ModelWithType.model_validate({"path": "anyAttribute"})
    ModelWithoutType.model_validate({"path": "anyAttribute"})


def test_path_validation_from_path_instance():
    """Path field accepts another Path instance."""

    class ModelWithPath(BaseModel):
        path: Path[User]

    source_path = Path("userName")
    model = ModelWithPath.model_validate({"path": source_path})
    assert str(model.path) == "userName"


def test_path_validation_rejects_invalid_type():
    """Path field rejects non-string non-Path values."""

    class ModelWithPath(BaseModel):
        path: Path[User]

    with pytest.raises(pydantic.ValidationError):
        ModelWithPath.model_validate({"path": 123})


# --- Path bound to model tests ---


def test_model_simple_attribute():
    """Model property returns the target model for simple attribute."""
    path = Path[User]("userName")
    assert path.model == User


def test_model_complex_attribute():
    """Model property returns the nested model for complex attribute."""
    path = Path[User]("name.familyName")
    assert path.model == Name


def test_model_extension_attribute():
    """Model property returns extension model for extension path."""
    path = Path[User[EnterpriseUser]](
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:employeeNumber"
    )
    assert path.model == EnterpriseUser


def test_model_extension_complex_attribute():
    """Model property navigates into extension complex attributes."""
    path = Path[User[EnterpriseUser]](
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:manager.value"
    )
    assert path.model == Manager


def test_model_invalid_attribute():
    """Model property returns None for invalid attribute."""
    path = Path[User]("invalidAttribute")
    assert path.model is None


def test_model_unbound_path():
    """Model property returns None for unbound path."""
    path = Path("userName")
    assert path.model is None


def test_field_name_simple_attribute():
    """field_name property returns snake_case field name."""
    path = Path[User]("userName")
    assert path.field_name == "user_name"


def test_field_name_complex_attribute():
    """field_name property returns snake_case for nested attribute."""
    path = Path[User]("name.familyName")
    assert path.field_name == "family_name"


def test_field_name_extension_attribute():
    """field_name property works for extension attributes."""
    path = Path[User[EnterpriseUser]](
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:employeeNumber"
    )
    assert path.field_name == "employee_number"


def test_field_name_invalid_attribute():
    """field_name property returns None for invalid attribute."""
    path = Path[User]("invalidAttribute")
    assert path.field_name is None


def test_field_name_unbound_path():
    """field_name property returns None for unbound path."""
    path = Path("userName")
    assert path.field_name is None


def test_field_name_schema_only():
    """field_name property returns None for schema-only path."""
    path = Path[User]("urn:ietf:params:scim:schemas:core:2.0:User")
    assert path.field_name is None


def test_urn_simple_attribute():
    """URN property returns fully qualified URN."""
    path = Path[User]("userName")
    assert path.urn == "urn:ietf:params:scim:schemas:core:2.0:User:userName"


def test_urn_complex_attribute():
    """URN property includes dotted path."""
    path = Path[User]("name.familyName")
    assert path.urn == "urn:ietf:params:scim:schemas:core:2.0:User:name.familyName"


def test_urn_already_qualified():
    """URN property preserves already qualified paths."""
    path = Path[User]("urn:ietf:params:scim:schemas:core:2.0:User:userName")
    assert path.urn == "urn:ietf:params:scim:schemas:core:2.0:User:userName"


def test_urn_extension_attribute():
    """URN property works for extension attributes."""
    path = Path[User[EnterpriseUser]](
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:employeeNumber"
    )
    assert (
        path.urn
        == "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:employeeNumber"
    )


def test_urn_invalid_attribute():
    """URN property returns None for invalid attribute."""
    path = Path[User]("invalidAttribute")
    assert path.urn is None


def test_urn_unbound_path():
    """URN property returns None for unbound path."""
    path = Path("userName")
    assert path.urn is None


def test_urn_schema_only():
    """URN property returns schema for schema-only path."""
    path = Path[User]("urn:ietf:params:scim:schemas:core:2.0:User")
    assert path.urn == "urn:ietf:params:scim:schemas:core:2.0:User"


def test_path_caching():
    """Path[Model] classes are cached."""
    path_class_1 = Path[User]
    path_class_2 = Path[User]
    assert path_class_1 is path_class_2


def test_path_different_models():
    """Different models create different Path classes."""
    path_class_user = Path[User]
    path_class_group = Path[Group]
    assert path_class_user is not path_class_group


# --- Path.get() tests ---


def test_get_simple_attribute():
    """Get a simple attribute value."""
    user = User(user_name="john.doe")
    path = Path("userName")
    assert path.get(user) == "john.doe"


def test_get_complex_attribute():
    """Get a complex attribute sub-value."""
    user = User(user_name="john", name=Name(family_name="Doe", given_name="John"))
    path = Path("name.familyName")
    assert path.get(user) == "Doe"


def test_get_with_schema_urn_prefix():
    """Get value using full schema URN prefix."""
    user = User(user_name="john.doe")
    path = Path("urn:ietf:params:scim:schemas:core:2.0:User:userName")
    assert path.get(user) == "john.doe"


def test_get_extension_attribute():
    """Get an extension attribute value."""
    user = User[EnterpriseUser](user_name="john")
    user[EnterpriseUser] = EnterpriseUser(employee_number="12345")
    path = Path(
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:employeeNumber"
    )
    assert path.get(user) == "12345"


def test_get_extension_root():
    """Get the entire extension object."""
    user = User[EnterpriseUser](user_name="john")
    user[EnterpriseUser] = EnterpriseUser(employee_number="12345")
    path = Path("urn:ietf:params:scim:schemas:extension:enterprise:2.0:User")
    result = path.get(user)
    assert isinstance(result, EnterpriseUser)
    assert result.employee_number == "12345"


def test_get_none_when_attribute_missing():
    """Get returns None when attribute is not set."""
    user = User(user_name="john")
    path = Path("displayName")
    assert path.get(user) is None


def test_get_none_when_parent_missing():
    """Get returns None when parent complex attribute is not set."""
    user = User(user_name="john")
    path = Path("name.familyName")
    assert path.get(user) is None


def test_get_invalid_attribute():
    """Get raises PathNotFoundException for invalid attribute."""
    user = User(user_name="john")
    path = Path("invalidAttribute")
    with pytest.raises(PathNotFoundException):
        path.get(user)


def test_get_extension_complex_subattribute():
    """Get a sub-attribute from extension complex attribute."""
    user = User[EnterpriseUser](user_name="john")
    user[EnterpriseUser] = EnterpriseUser(
        manager=Manager(value="mgr-123", display_name="Boss")
    )
    path = Path(
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:manager.value"
    )
    assert path.get(user) == "mgr-123"


def test_get_invalid_first_part_in_complex_path():
    """Get raises PathNotFoundException when first part of complex path is invalid."""
    user = User(user_name="john", name=Name(family_name="Doe"))
    path = Path("invalidAttr.subField")
    with pytest.raises(PathNotFoundException):
        path.get(user)


def test_get_main_schema_prefix_strips_correctly():
    """Get value with main schema prefix handles stripping."""
    user = User(user_name="john", display_name="John Doe")
    path = Path("urn:ietf:params:scim:schemas:core:2.0:User:displayName")
    assert path.get(user) == "John Doe"


def test_get_extension_attribute_uppercase_urn():
    """Get extension attribute with uppercase URN."""
    user = User[EnterpriseUser](user_name="john")
    user[EnterpriseUser] = EnterpriseUser(employee_number="12345")
    path = Path(
        "URN:IETF:PARAMS:SCIM:SCHEMAS:EXTENSION:ENTERPRISE:2.0:USER:employeeNumber"
    )
    assert path.get(user) == "12345"


# --- Path.set() tests ---


def test_set_simple_attribute():
    """Set a simple attribute value."""
    user = User(user_name="john")
    path = Path("displayName")
    result = path.set(user, "John Doe")
    assert result is True
    assert user.display_name == "John Doe"


def test_set_complex_attribute():
    """Set a complex attribute sub-value, creating parent if needed."""
    user = User(user_name="john")
    path = Path("name.familyName")
    result = path.set(user, "Doe")
    assert result is True
    assert user.name.family_name == "Doe"


def test_set_with_schema_urn_prefix():
    """Set value using full schema URN prefix."""
    user = User(user_name="john")
    path = Path("urn:ietf:params:scim:schemas:core:2.0:User:displayName")
    result = path.set(user, "John Doe")
    assert result is True
    assert user.display_name == "John Doe"


def test_set_extension_attribute():
    """Set an extension attribute value, creating extension if needed."""
    user = User[EnterpriseUser](user_name="john")
    path = Path(
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:employeeNumber"
    )
    result = path.set(user, "12345")
    assert result is True
    assert user[EnterpriseUser].employee_number == "12345"


def test_set_extension_root():
    """Set the entire extension object."""
    user = User[EnterpriseUser](user_name="john")
    path = Path("urn:ietf:params:scim:schemas:extension:enterprise:2.0:User")
    result = path.set(user, EnterpriseUser(employee_number="99999"))
    assert result is True
    assert user[EnterpriseUser].employee_number == "99999"


def test_set_extension_attribute_uppercase_urn():
    """Set extension attribute with uppercase URN."""
    user = User[EnterpriseUser](user_name="john")
    path = Path(
        "URN:IETF:PARAMS:SCIM:SCHEMAS:EXTENSION:ENTERPRISE:2.0:USER:employeeNumber"
    )
    result = path.set(user, "12345")
    assert result is True
    assert user[EnterpriseUser].employee_number == "12345"


def test_set_multivalued_wraps_single_value():
    """Set wraps single value in list for multi-valued attributes."""
    user = User(user_name="john")
    path = Path("emails")
    email = Email(value="john@example.com")
    result = path.set(user, email)
    assert result is True
    assert user.emails == [email]


def test_set_invalid_attribute():
    """Set raises PathNotFoundException for invalid attribute."""
    user = User(user_name="john")
    path = Path("invalidAttribute")
    with pytest.raises(PathNotFoundException):
        path.set(user, "value")


def test_set_extension_complex_subattribute():
    """Set a sub-attribute on extension complex attribute."""
    user = User[EnterpriseUser](user_name="john")
    path = Path(
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:manager.value"
    )
    result = path.set(user, "mgr-456")
    assert result is True
    assert user[EnterpriseUser].manager.value == "mgr-456"


def test_set_invalid_first_part_in_complex_path():
    """Set raises PathNotFoundException when first part of complex path is invalid."""
    user = User(user_name="john")
    path = Path("invalidAttr.subField")
    with pytest.raises(PathNotFoundException):
        path.set(user, "value")


def test_set_main_schema_prefix_strips_correctly():
    """Set value with main schema prefix handles stripping."""
    user = User(user_name="john")
    path = Path("urn:ietf:params:scim:schemas:core:2.0:User:displayName")
    result = path.set(user, "John Doe")
    assert result is True
    assert user.display_name == "John Doe"


def test_set_creates_intermediate_objects():
    """Set creates intermediate complex objects when needed."""
    user = User(user_name="john")
    assert user.name is None
    path = Path("name.givenName")
    result = path.set(user, "John")
    assert result is True
    assert user.name.given_name == "John"


def test_set_schema_only_path_merges_dict():
    """Set with schema-only path merges dict into resource."""
    user = User(user_name="john")
    path = Path("urn:ietf:params:scim:schemas:core:2.0:User")
    result = path.set(user, {"displayName": "Test"})
    assert result is True
    assert user.display_name == "Test"


def test_set_cannot_navigate_into_list():
    """Set returns False when trying to navigate into a multi-valued attribute."""
    user = User(user_name="john", emails=[Email(value="john@example.com")])
    path = Path("emails.value")
    result = path.set(user, "new@example.com")
    assert result is False


def test_set_invalid_last_part_in_complex_path():
    """Set raises PathNotFoundException when last part of complex path is invalid."""
    user = User(user_name="john", name=Name(family_name="Doe"))
    path = Path("name.invalidField")
    with pytest.raises(PathNotFoundException):
        path.set(user, "value")


# --- Path.iter_paths() tests ---


def test_iter_paths_simple_attributes():
    """Iterate over simple attributes of a model."""
    paths = list(Path[User].iter_paths(include_subattributes=False))
    path_strings = [str(p) for p in paths]

    assert "userName" in path_strings
    assert "displayName" in path_strings
    assert "name" in path_strings
    assert "emails" in path_strings


def test_iter_paths_with_subattributes():
    """Iterate includes sub-attributes when enabled."""
    paths = list(Path[User].iter_paths(include_subattributes=True))
    path_strings = [str(p) for p in paths]

    assert "name" in path_strings
    assert "name.familyName" in path_strings
    assert "name.givenName" in path_strings
    assert "emails" in path_strings
    assert "emails.value" in path_strings
    assert "emails.type" in path_strings


def test_iter_paths_excludes_meta_id_schemas():
    """Iterate excludes meta, id, and schemas fields."""
    paths = list(Path[User].iter_paths())
    path_strings = [str(p) for p in paths]

    assert "meta" not in path_strings
    assert "id" not in path_strings
    assert "schemas" not in path_strings


def test_iter_paths_includes_extensions():
    """Iterate includes extension model attributes."""
    paths = list(Path[User[EnterpriseUser]].iter_paths(include_subattributes=False))
    path_strings = [str(p) for p in paths]

    assert "userName" in path_strings
    assert (
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:employeeNumber"
        in path_strings
    )
    assert (
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:department"
        in path_strings
    )


def test_iter_paths_excludes_extensions():
    """Iterate excludes extension attributes when include_extensions=False."""
    paths = list(
        Path[User[EnterpriseUser]].iter_paths(
            include_subattributes=False, include_extensions=False
        )
    )
    path_strings = [str(p) for p in paths]

    assert "userName" in path_strings
    assert not any("enterprise" in p.lower() for p in path_strings)


def test_iter_paths_returns_bound_paths():
    """Iterate returns paths bound to the model."""
    paths = list(Path[User[EnterpriseUser]].iter_paths(include_subattributes=False))

    user_name_path = next(p for p in paths if str(p) == "userName")
    assert user_name_path.model == User[EnterpriseUser]

    ext_path = next(
        p
        for p in paths
        if str(p)
        == "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:employeeNumber"
    )
    assert ext_path.model == EnterpriseUser


def test_iter_paths_without_extensions():
    """Iterate over model without extensions."""
    paths = list(Path[User].iter_paths(include_subattributes=False))
    path_strings = [str(p) for p in paths]

    assert "userName" in path_strings
    assert "displayName" in path_strings
    assert not any("enterprise" in p.lower() for p in path_strings)


def test_iter_paths_requires_bound_path():
    """Iterate raises TypeError if Path is not bound to a model."""
    with pytest.raises(TypeError, match="iter_paths requires a bound Path type"):
        list(Path.iter_paths())


# --- Path.set() with is_add=True tests ---


def test_set_add_to_empty_list():
    """Add a value to an empty multi-valued attribute."""
    user = User(user_name="john")
    email = Email(value="john@example.com")
    path = Path("emails")
    result = path.set(user, email, is_add=True)
    assert result is True
    assert user.emails == [email]


def test_set_add_to_existing_list():
    """Add a value to an existing multi-valued attribute."""
    email1 = Email(value="john@example.com")
    user = User(user_name="john", emails=[email1])
    email2 = Email(value="john@work.com")
    path = Path("emails")
    result = path.set(user, email2, is_add=True)
    assert result is True
    assert len(user.emails) == 2
    assert email1 in user.emails
    assert email2 in user.emails


def test_set_add_duplicate_not_added():
    """Adding a duplicate value returns False."""
    email = Email(value="john@example.com")
    user = User(user_name="john", emails=[email])
    path = Path("emails")
    result = path.set(user, Email(value="john@example.com"), is_add=True)
    assert result is False
    assert len(user.emails) == 1


def test_set_add_multiple_values():
    """Add multiple values at once."""
    user = User(user_name="john")
    emails = [Email(value="a@example.com"), Email(value="b@example.com")]
    path = Path("emails")
    result = path.set(user, emails, is_add=True)
    assert result is True
    assert len(user.emails) == 2


def test_set_add_extension_attribute():
    """Add value to extension attribute with is_add (non-list, behaves like replace)."""
    user = User[EnterpriseUser](user_name="john")
    path = Path(
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:employeeNumber"
    )
    result = path.set(user, "12345", is_add=True)
    assert result is True
    assert user[EnterpriseUser].employee_number == "12345"


# --- Path.delete() tests ---


def test_delete_simple_attribute():
    """Delete a simple attribute value."""
    user = User(user_name="john", display_name="John Doe")
    path = Path("displayName")
    result = path.delete(user)
    assert result is True
    assert user.display_name is None


def test_delete_attribute_already_none():
    """Delete returns False when attribute is already None."""
    user = User(user_name="john")
    path = Path("displayName")
    result = path.delete(user)
    assert result is False


def test_delete_from_list_specific_value():
    """Delete a specific value from a multi-valued attribute."""
    email1 = Email(value="john@example.com")
    email2 = Email(value="john@work.com")
    user = User(user_name="john", emails=[email1, email2])
    path = Path("emails")
    result = path.delete(user, Email(value="john@example.com"))
    assert result is True
    assert len(user.emails) == 1
    assert user.emails[0].value == "john@work.com"


def test_delete_from_list_value_not_found():
    """Delete returns False when value not in list."""
    email = Email(value="john@example.com")
    user = User(user_name="john", emails=[email])
    path = Path("emails")
    result = path.delete(user, Email(value="other@example.com"))
    assert result is False
    assert len(user.emails) == 1


def test_delete_last_item_from_list():
    """Delete last item from list sets attribute to None."""
    email = Email(value="john@example.com")
    user = User(user_name="john", emails=[email])
    path = Path("emails")
    result = path.delete(user, email)
    assert result is True
    assert user.emails is None


def test_delete_extension_attribute():
    """Delete an extension attribute."""
    user = User[EnterpriseUser](user_name="john")
    user[EnterpriseUser] = EnterpriseUser(employee_number="12345")
    path = Path(
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:employeeNumber"
    )
    result = path.delete(user)
    assert result is True
    assert user[EnterpriseUser].employee_number is None


def test_delete_extension_root():
    """Delete entire extension."""
    user = User[EnterpriseUser](user_name="john")
    user[EnterpriseUser] = EnterpriseUser(employee_number="12345")
    path = Path("urn:ietf:params:scim:schemas:extension:enterprise:2.0:User")
    result = path.delete(user)
    assert result is True
    assert user[EnterpriseUser] is None


def test_delete_extension_attribute_uppercase_urn():
    """Delete extension attribute with uppercase URN."""
    user = User[EnterpriseUser](user_name="john")
    user[EnterpriseUser] = EnterpriseUser(employee_number="12345")
    path = Path(
        "URN:IETF:PARAMS:SCIM:SCHEMAS:EXTENSION:ENTERPRISE:2.0:USER:employeeNumber"
    )
    result = path.delete(user)
    assert result is True
    assert user[EnterpriseUser].employee_number is None


def test_delete_complex_subattribute():
    """Delete a sub-attribute of a complex attribute."""
    user = User(user_name="john", name=Name(family_name="Doe", given_name="John"))
    path = Path("name.familyName")
    result = path.delete(user)
    assert result is True
    assert user.name.family_name is None
    assert user.name.given_name == "John"


def test_delete_invalid_path():
    """Delete raises PathNotFoundException for invalid path."""
    user = User(user_name="john")
    path = Path("invalidAttribute")
    with pytest.raises(PathNotFoundException):
        path.delete(user)


# --- Path component properties (schema, attr, parts) tests ---


def test_schema_simple_path():
    """Simple path has no schema."""
    path = Path("userName")
    assert path.schema is None


def test_schema_dotted_path():
    """Dotted path without URN has no schema."""
    path = Path("name.familyName")
    assert path.schema is None


def test_schema_urn_path():
    """URN path returns schema portion."""
    path = Path("urn:ietf:params:scim:schemas:core:2.0:User:userName")
    assert path.schema == "urn:ietf:params:scim:schemas:core:2.0:User"


def test_schema_extension_path():
    """Extension path returns extension schema."""
    path = Path(
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:employeeNumber"
    )
    assert path.schema == "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"


def test_schema_schema_only_path():
    """Schema-only path returns the full schema."""
    path = Path("urn:ietf:params:scim:schemas:core:2.0:User")
    assert path.schema == "urn:ietf:params:scim:schemas:core:2.0"


def test_attr_simple_path():
    """Simple path attr is the path itself."""
    path = Path("userName")
    assert path.attr == "userName"


def test_attr_dotted_path():
    """Dotted path attr is the full dotted path."""
    path = Path("name.familyName")
    assert path.attr == "name.familyName"


def test_attr_urn_path():
    """URN path attr is the attribute after the schema."""
    path = Path("urn:ietf:params:scim:schemas:core:2.0:User:userName")
    assert path.attr == "userName"


def test_attr_urn_dotted_path():
    """URN path with dotted attribute."""
    path = Path("urn:ietf:params:scim:schemas:core:2.0:User:name.familyName")
    assert path.attr == "name.familyName"


def test_attr_schema_only_path():
    """Schema-only path has empty attr."""
    path = Path("urn:ietf:params:scim:schemas:core:2.0:User")
    assert path.attr == "User"


def test_attr_empty_path():
    """Empty path has empty attr."""
    path = Path("")
    assert path.attr == ""


def test_parts_simple_path():
    """Simple path has single part."""
    path = Path("userName")
    assert path.parts == ("userName",)


def test_parts_dotted_path():
    """Dotted path splits into parts."""
    path = Path("name.familyName")
    assert path.parts == ("name", "familyName")


def test_parts_urn_path():
    """URN path parts are from attr portion only."""
    path = Path("urn:ietf:params:scim:schemas:core:2.0:User:userName")
    assert path.parts == ("userName",)


def test_parts_urn_dotted_path():
    """URN path with dotted attribute splits correctly."""
    path = Path("urn:ietf:params:scim:schemas:core:2.0:User:name.familyName")
    assert path.parts == ("name", "familyName")


def test_parts_empty_path():
    """Empty path has no parts."""
    path = Path("")
    assert path.parts == ()


def test_parts_deeply_nested():
    """Deeply nested path splits all parts."""
    path = Path("a.b.c.d")
    assert path.parts == ("a", "b", "c", "d")


# --- Path prefix methods (is_prefix_of, has_prefix) tests ---


def test_is_prefix_of_simple_dot():
    """Path is prefix of dotted sub-path."""
    path = Path("emails")
    assert path.is_prefix_of("emails.value") is True


def test_is_prefix_of_not_equal():
    """Equal paths are not prefixes of each other."""
    path = Path("emails")
    assert path.is_prefix_of("emails") is False


def test_is_prefix_of_not_prefix():
    """Unrelated paths are not prefixes."""
    path = Path("emails")
    assert path.is_prefix_of("userName") is False


def test_is_prefix_of_partial_match_not_prefix():
    """Partial string match without separator is not a prefix."""
    path = Path("email")
    assert path.is_prefix_of("emails") is False


def test_is_prefix_of_schema_to_attribute():
    """Schema URN is prefix of full attribute path."""
    schema = Path("urn:ietf:params:scim:schemas:core:2.0:User")
    assert (
        schema.is_prefix_of("urn:ietf:params:scim:schemas:core:2.0:User:userName")
        is True
    )


def test_is_prefix_of_case_insensitive():
    """Prefix matching is case-insensitive."""
    path = Path("Emails")
    assert path.is_prefix_of("emails.value") is True


def test_is_prefix_of_accepts_path_object():
    """is_prefix_of accepts Path objects."""
    path1 = Path("emails")
    path2 = Path("emails.value")
    assert path1.is_prefix_of(path2) is True


def test_has_prefix_simple_dot():
    """Path has prefix when it starts with prefix + dot."""
    path = Path("emails.value")
    assert path.has_prefix("emails") is True


def test_has_prefix_not_equal():
    """Equal paths don't have each other as prefix."""
    path = Path("emails")
    assert path.has_prefix("emails") is False


def test_has_prefix_not_prefix():
    """Unrelated paths don't have prefix relationship."""
    path = Path("userName")
    assert path.has_prefix("emails") is False


def test_has_prefix_partial_match_not_prefix():
    """Partial string match without separator is not a prefix."""
    path = Path("emails")
    assert path.has_prefix("email") is False


def test_has_prefix_schema_prefix():
    """Full path has schema as prefix."""
    path = Path("urn:ietf:params:scim:schemas:core:2.0:User:userName")
    assert path.has_prefix("urn:ietf:params:scim:schemas:core:2.0:User") is True


def test_has_prefix_case_insensitive():
    """Prefix matching is case-insensitive."""
    path = Path("emails.value")
    assert path.has_prefix("EMAILS") is True


def test_has_prefix_accepts_path_object():
    """has_prefix accepts Path objects."""
    path1 = Path("emails.value")
    path2 = Path("emails")
    assert path1.has_prefix(path2) is True


def test_prefix_symmetry():
    """is_prefix_of and has_prefix are symmetric."""
    parent = Path("emails")
    child = Path("emails.value")
    assert parent.is_prefix_of(child) is True
    assert child.has_prefix(parent) is True
    assert child.is_prefix_of(parent) is False
    assert parent.has_prefix(child) is False


# --- Bound path resolution edge cases ---


def test_model_extension_schema_only_path():
    """Model property returns extension for schema-only extension path."""
    path = Path[User[EnterpriseUser]](
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"
    )
    assert path.model == EnterpriseUser
    assert path.field_name is None


def test_model_urn_unknown_extension():
    """Model property returns None for URN not matching any extension."""
    path = Path[User[EnterpriseUser]](
        "urn:ietf:params:scim:schemas:extension:unknown:2.0:User:field"
    )
    assert path.model is None


def test_model_dotted_path_invalid_intermediate():
    """Model property returns None when intermediate part is invalid."""
    path = Path[User]("invalidAttr.familyName")
    assert path.model is None


def test_model_dotted_path_intermediate_not_complex():
    """Model property returns None when intermediate type is not a complex attribute."""
    path = Path[User]("userName.subField")
    assert path.model is None


def test_urn_empty_path_non_resource():
    """URN property handles empty path on non-Resource model."""
    path = Path[Name]("")
    assert path.urn is None


# --- get() edge cases ---


def test_get_extension_attribute_when_extension_is_none():
    """Get returns None when extension object doesn't exist."""
    user = User[EnterpriseUser](user_name="john")
    path = Path(
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:employeeNumber"
    )
    assert path.get(user) is None


def test_get_unknown_extension_raises():
    """Get raises InvalidPathException for unknown extension URN."""
    user = User[EnterpriseUser](user_name="john")
    path = Path("urn:ietf:params:scim:schemas:extension:unknown:2.0:User:field")
    with pytest.raises(InvalidPathException):
        path.get(user)


def test_get_strict_false_returns_none_on_invalid_path():
    """Get with strict=False returns None instead of raising."""
    user = User(user_name="john")
    path = Path("invalidAttribute")
    assert path.get(user, strict=False) is None


def test_get_urn_on_extension_instance():
    """Get with URN path on Extension instance (not Resource)."""
    ext = EnterpriseUser(employee_number="12345")
    path = Path(
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:employeeNumber"
    )
    assert path.get(ext) == "12345"


def test_get_mismatched_urn_on_extension_instance():
    """Get with mismatched URN on Extension returns None."""
    ext = EnterpriseUser(employee_number="12345")
    path = Path("urn:ietf:params:scim:schemas:core:2.0:User:userName")
    assert path.get(ext) is None


# --- set() edge cases ---


def test_set_explicit_schema_path_with_non_dict_raises():
    """Set with explicit schema path and non-dict value raises InvalidPathException."""
    user = User(user_name="john")
    path = Path("urn:ietf:params:scim:schemas:core:2.0:User")
    with pytest.raises(InvalidPathException):
        path.set(user, "not a dict")


def test_set_schema_path_with_all_invalid_fields():
    """Set with schema path where all fields are invalid returns False."""
    user = User(user_name="john")
    path = Path("urn:ietf:params:scim:schemas:core:2.0:User")
    result = path.set(user, {"invalidField1": "a", "invalidField2": "b"})
    assert result is False


def test_set_schema_path_with_unchanged_value():
    """Set with schema path where value equals existing returns False."""
    user = User(user_name="john", display_name="John")
    path = Path("urn:ietf:params:scim:schemas:core:2.0:User")
    result = path.set(user, {"displayName": "John"})
    assert result is False


def test_set_strict_false_returns_false_on_invalid_path():
    """Set with strict=False returns False instead of raising."""
    user = User(user_name="john")
    path = Path("invalidAttribute")
    result = path.set(user, "value", strict=False)
    assert result is False


def test_set_add_list_all_duplicates():
    """Set with is_add=True returns False when all list values are duplicates."""
    email = Email(value="john@example.com")
    user = User(user_name="john", emails=[email])
    path = Path("emails")
    result = path.set(
        user,
        [Email(value="john@example.com")],
        is_add=True,
    )
    assert result is False
    assert len(user.emails) == 1


def test_set_unchanged_value():
    """Set returns False when new value equals existing value."""
    user = User(user_name="john", display_name="John Doe")
    path = Path("displayName")
    result = path.set(user, "John Doe")
    assert result is False


# --- delete() edge cases ---


def test_delete_strict_false_returns_false_on_invalid_path():
    """Delete with strict=False returns False instead of raising."""
    user = User(user_name="john")
    path = Path("invalidAttribute")
    result = path.delete(user, strict=False)
    assert result is False


def test_delete_from_non_list_with_value():
    """Delete with value parameter on non-list attribute returns False."""
    user = User(user_name="john", display_name="John Doe")
    path = Path("displayName")
    result = path.delete(user, "John Doe")
    assert result is False
    assert user.display_name == "John Doe"


def test_delete_extension_already_none():
    """Delete extension that is already None returns False."""
    user = User[EnterpriseUser](user_name="john")
    path = Path("urn:ietf:params:scim:schemas:extension:enterprise:2.0:User")
    result = path.delete(user)
    assert result is False


def test_model_dotted_path_invalid_last_part():
    """Model property returns None when last part of dotted path is invalid."""
    path = Path[User]("name.invalidField")
    assert path.model is None


def test_get_schema_only_path_returns_resource():
    """Get with schema-only path returns the resource itself."""
    user = User(user_name="john", display_name="John")
    path = Path("urn:ietf:params:scim:schemas:core:2.0:User")
    result = path.get(user)
    assert result is user


def test_set_on_extension_with_mismatched_urn():
    """Set on Extension instance with mismatched URN returns False."""
    ext = EnterpriseUser(employee_number="12345")
    path = Path("urn:ietf:params:scim:schemas:core:2.0:User:userName")
    result = path.set(ext, "newValue")
    assert result is False


def test_set_empty_path_non_dict_value():
    """Set with empty path and non-dict value returns False."""
    user = User(user_name="john")
    path = Path("")
    result = path.set(user, "not a dict")
    assert result is False


def test_set_dotted_path_intermediate_type_none():
    """Set returns False when intermediate field has no determinable type."""

    class TestResource(User):
        untyped: Any = None

    resource = TestResource(user_name="john")
    path = Path("untyped.sub")
    result = path.set(resource, "value")
    assert result is False


def test_delete_on_extension_with_mismatched_urn():
    """Delete on Extension instance with mismatched URN returns False."""
    ext = EnterpriseUser(employee_number="12345")
    path = Path("urn:ietf:params:scim:schemas:core:2.0:User:userName")
    result = path.delete(ext)
    assert result is False


def test_delete_schema_only_path_raises():
    """Delete with schema-only path raises InvalidPathException."""
    user = User(user_name="john")
    path = Path("urn:ietf:params:scim:schemas:core:2.0:User")
    with pytest.raises(InvalidPathException):
        path.delete(user)


def test_delete_dotted_path_intermediate_none():
    """Delete returns False when intermediate object in path is None."""
    user = User(user_name="john")
    assert user.name is None
    path = Path("name.familyName")
    result = path.delete(user)
    assert result is False


def test_model_extension_bound_with_mismatched_urn():
    """Model property on Extension-bound path with unrelated URN."""
    path = Path[EnterpriseUser]("urn:ietf:params:scim:schemas:core:2.0:User:userName")
    assert path.model is None


def test_iter_paths_on_extension():
    """Iterate paths on an Extension model (not a Resource)."""
    paths = list(Path[EnterpriseUser].iter_paths(include_subattributes=False))
    path_strings = [str(p) for p in paths]

    assert (
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:employeeNumber"
        in path_strings
    )
    assert (
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:department"
        in path_strings
    )


# --- field_type property tests ---


def test_field_type_simple_attribute():
    """field_type returns the Python type for simple attribute."""
    path = Path[User]("userName")
    assert path.field_type is str


def test_field_type_complex_attribute():
    """field_type returns the complex attribute class."""
    path = Path[User]("name")
    assert path.field_type is Name


def test_field_type_multivalued_attribute():
    """field_type returns the element type for multi-valued attributes."""
    path = Path[User]("emails")
    assert path.field_type is Email


def test_field_type_nested_attribute():
    """field_type returns the type for nested attribute."""
    path = Path[User]("name.familyName")
    assert path.field_type is str


def test_field_type_invalid_attribute():
    """field_type returns None for invalid attribute."""
    path = Path[User]("invalidAttribute")
    assert path.field_type is None


def test_field_type_unbound_path():
    """field_type returns None for unbound path."""
    path = Path("userName")
    assert path.field_type is None


def test_field_type_schema_only_path():
    """field_type returns None for schema-only path."""
    path = Path[User]("urn:ietf:params:scim:schemas:core:2.0:User")
    assert path.field_type is None


# --- is_multivalued property tests ---


def test_is_multivalued_true():
    """is_multivalued returns True for multi-valued attribute."""
    path = Path[User]("emails")
    assert path.is_multivalued is True


def test_is_multivalued_false():
    """is_multivalued returns False for single-valued attribute."""
    path = Path[User]("userName")
    assert path.is_multivalued is False


def test_is_multivalued_nested_attribute():
    """is_multivalued works for nested attributes."""
    path = Path[User]("name.familyName")
    assert path.is_multivalued is False


def test_is_multivalued_invalid_attribute():
    """is_multivalued returns None for invalid attribute."""
    path = Path[User]("invalidAttribute")
    assert path.is_multivalued is None


def test_is_multivalued_unbound_path():
    """is_multivalued returns None for unbound path."""
    path = Path("emails")
    assert path.is_multivalued is None


# --- get_annotation() method tests ---


def test_get_annotation_required():
    """get_annotation returns Required annotation value."""
    path = Path[User]("userName")
    assert path.get_annotation(Required) == Required.true


def test_get_annotation_mutability():
    """get_annotation returns Mutability annotation value."""
    path = Path[User]("userName")
    assert path.get_annotation(Mutability) == Mutability.read_write


def test_get_annotation_nested_attribute():
    """get_annotation works for nested attributes."""
    path = Path[User]("name.familyName")
    result = path.get_annotation(Required)
    assert result is None or isinstance(result, Required)


def test_get_annotation_invalid_attribute():
    """get_annotation returns None for invalid attribute."""
    path = Path[User]("invalidAttribute")
    assert path.get_annotation(Required) is None


def test_get_annotation_unbound_path():
    """get_annotation returns None for unbound path."""
    path = Path("userName")
    assert path.get_annotation(Required) is None


# --- iter_paths() with filters tests ---


def test_iter_paths_filter_by_required():
    """iter_paths with required filter only yields matching paths."""
    paths = list(
        Path[User].iter_paths(include_subattributes=False, required=[Required.true])
    )
    path_strings = [str(p) for p in paths]

    assert "userName" in path_strings
    for path in paths:
        assert path.get_annotation(Required) == Required.true


def test_iter_paths_filter_by_mutability():
    """iter_paths with mutability filter only yields matching paths."""
    paths = list(
        Path[User].iter_paths(
            include_subattributes=False, mutability=[Mutability.read_only]
        )
    )

    for path in paths:
        assert path.get_annotation(Mutability) == Mutability.read_only


def test_iter_paths_filter_by_required_and_mutability():
    """iter_paths with both filters applies both."""
    paths = list(
        Path[User].iter_paths(
            include_subattributes=False,
            required=[Required.true],
            mutability=[Mutability.read_write],
        )
    )

    for path in paths:
        assert path.get_annotation(Required) == Required.true
        assert path.get_annotation(Mutability) == Mutability.read_write


def test_iter_paths_filter_includes_subattributes():
    """iter_paths filters are applied to subattributes too."""
    paths = list(
        Path[User].iter_paths(include_subattributes=True, required=[Required.true])
    )

    for path in paths:
        assert path.get_annotation(Required) == Required.true


def test_iter_paths_filter_no_match():
    """iter_paths with filter that matches nothing yields empty."""
    paths = list(
        Path[User].iter_paths(
            include_subattributes=False,
            required=[Required.true],
            mutability=[Mutability.immutable],
        )
    )
    assert "userName" not in [str(p) for p in paths]


def test_iter_paths_filter_excludes_subattributes():
    """iter_paths filters exclude non-matching subattributes."""
    paths_with_filter = list(
        Path[User].iter_paths(
            include_subattributes=True,
            required=[Required.true],
        )
    )
    paths_without_filter = list(Path[User].iter_paths(include_subattributes=True))
    assert len(paths_with_filter) < len(paths_without_filter)

    for path in paths_with_filter:
        assert path.get_annotation(Required) == Required.true


def test_iter_paths_filter_skips_non_matching_subattributes():
    """iter_paths skips subattributes that don't match the filter.

    Group.members has read_write mutability but its subattributes have
    immutable (value, ref, type) or read_only (display) mutability.
    When filtering by read_write, members is yielded but fewer subattributes.
    """
    paths_with_filter = list(
        Path[Group].iter_paths(
            include_subattributes=True,
            mutability=[Mutability.read_write],
        )
    )
    paths_no_filter = list(Path[Group].iter_paths(include_subattributes=True))
    path_strings = [str(p) for p in paths_with_filter]

    assert "members" in path_strings
    assert len(paths_with_filter) < len(paths_no_filter)


def test_path_init_with_path_object():
    """Path can be initialized with another Path object."""
    original = Path("userName")
    copy = Path(original)
    assert str(copy) == "userName"
    assert copy.data == original.data


def test_path_json_schema_generation():
    """Test that models with Path fields can generate JSON Schema."""

    class ModelWithPath(BaseModel):
        path: Path[User] | None = None

    schema = ModelWithPath.model_json_schema()
    assert schema["type"] == "object"
    assert "path" in schema["properties"]
