import pytest

from scim2_models.base import BaseModel
from scim2_models.path import URN


def test_urn_syntax_valid_urns():
    """Test that valid SCIM URN paths are accepted."""
    valid_urns = [
        "urn:ietf:params:scim:schemas:core:2.0:User:userName",
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:employeeNumber",
        "urn:custom:namespace:schema:1.0:Resource:attribute",
        "urn:example:extension:v2:MyResource:customField",
    ]

    for urn in valid_urns:
        URN(urn)


def test_urn_syntax_invalid_urns():
    """Test that invalid SCIM URN paths are rejected."""
    invalid_urns = [
        "not_an_urn",  # Doesn't start with urn:
        "urn:invalid",  # Too short
    ]

    for urn in invalid_urns:
        with pytest.raises(ValueError):
            URN(urn)


def test_urn_as_a_type():
    class Foo(BaseModel):
        urn_schema: URN

    Foo.model_validate({"urn_schema": "urn:valid:schema"})
