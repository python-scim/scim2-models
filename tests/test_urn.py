"""Tests for URN utility functions."""

from scim2_models.rfc7643.enterprise_user import EnterpriseUser
from scim2_models.rfc7643.user import User
from scim2_models.urn import build_attribute_urn
from scim2_models.urn import is_absolute_urn


def test_is_absolute_urn():
    """Test is_absolute_urn function."""
    # Test absolute URN
    assert (
        is_absolute_urn("urn:ietf:params:scim:schemas:core:2.0:User:userName") is True
    )
    assert is_absolute_urn("urn:test:schema:attribute") is True

    # Test relative path
    assert is_absolute_urn("userName") is False
    assert is_absolute_urn("name.familyName") is False
    assert is_absolute_urn("") is False


def test_build_attribute_urn():
    """Test build_attribute_urn function."""
    # Test with schema
    result = build_attribute_urn(
        "urn:ietf:params:scim:schemas:core:2.0:User", "userName"
    )
    assert result == "urn:ietf:params:scim:schemas:core:2.0:User:userName"

    # Test with empty schema
    result = build_attribute_urn("", "userName")
    assert result == "userName"

    # Test with None schema
    result = build_attribute_urn(None, "userName")
    assert result == "userName"


def test_get_extension_for_schema():
    """Test get_extension_model method on Resource."""
    user = User[EnterpriseUser]()
    extension_class = user.get_extension_model(
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"
    )
    assert extension_class == EnterpriseUser

    extension_class = user.get_extension_model("urn:unknown:schema")
    assert extension_class is None
