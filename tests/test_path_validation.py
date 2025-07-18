"""Tests for SCIM path validation utilities."""

from scim2_models.utils import validate_scim_path_syntax
from scim2_models.utils import validate_scim_urn_syntax


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
    ]

    for path in valid_paths:
        assert validate_scim_path_syntax(path), f"Path should be valid: {path}"


def test_validate_scim_path_syntax_invalid_paths():
    """Test that invalid SCIM paths are rejected."""
    invalid_paths = [
        "",  # Empty string
        "   ",  # Whitespace only
        "123invalid",  # Starts with digit
        "invalid..path",  # Double dots
        "invalid@path",  # Invalid character
        "urn:invalid",  # Invalid URN format
        "urn:too:short",  # URN too short
    ]

    for path in invalid_paths:
        assert not validate_scim_path_syntax(path), f"Path should be invalid: {path}"


def test_validate_scim_urn_syntax_valid_urns():
    """Test that valid SCIM URN paths are accepted."""
    valid_urns = [
        "urn:ietf:params:scim:schemas:core:2.0:User:userName",
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:employeeNumber",
        "urn:custom:namespace:schema:1.0:Resource:attribute",
        "urn:example:extension:v2:MyResource:customField",
    ]

    for urn in valid_urns:
        assert validate_scim_urn_syntax(urn), f"URN should be valid: {urn}"


def test_validate_scim_urn_syntax_invalid_urns():
    """Test that invalid SCIM URN paths are rejected."""
    invalid_urns = [
        "not_an_urn",  # Doesn't start with urn:
        "urn:too:short",  # Not enough segments
        "urn:ietf:params:scim:schemas:core:2.0:User:",  # Empty attribute
        "urn:ietf:params:scim:schemas:core:2.0:User:123invalid",  # Attribute starts with digit
        "urn:invalid",  # Too short
        "urn:only:two:attribute",  # URN part too short
    ]

    for urn in invalid_urns:
        assert not validate_scim_urn_syntax(urn), f"URN should be invalid: {urn}"


def test_validate_scim_path_syntax_edge_cases():
    """Test edge cases for path validation."""
    # Test None handling (shouldn't happen in practice but defensive)
    assert not validate_scim_path_syntax("")

    # Test borderline valid cases
    assert validate_scim_path_syntax("a")  # Single character
    assert validate_scim_path_syntax("a.b")  # Simple dotted
    assert validate_scim_path_syntax("a_b")  # Underscore
    assert validate_scim_path_syntax("a-b")  # Hyphen

    # Test borderline invalid cases
    assert not validate_scim_path_syntax("9invalid")  # Starts with digit
    assert not validate_scim_path_syntax("a..b")  # Double dots


def test_validate_scim_urn_syntax_edge_cases():
    """Test edge cases for URN validation."""
    # Test minimal valid URN
    assert validate_scim_urn_syntax("urn:a:b:c:d")

    # Test boundary cases
    assert not validate_scim_urn_syntax("urn:a:b:c:")  # Empty attribute
    assert not validate_scim_urn_syntax("urn:a:b:")  # Missing resource
    assert not validate_scim_urn_syntax("urn:")  # Just urn:
