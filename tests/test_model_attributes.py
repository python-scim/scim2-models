import uuid
from typing import Annotated
from typing import Optional

import pytest

from scim2_models.base import BaseModel
from scim2_models.base import ComplexAttribute
from scim2_models.base import Context
from scim2_models.base import Required
from scim2_models.base import Returned
from scim2_models.base import validate_attribute_urn
from scim2_models.rfc7643.enterprise_user import EnterpriseUser
from scim2_models.rfc7643.resource import Extension
from scim2_models.rfc7643.resource import Meta
from scim2_models.rfc7643.resource import Resource
from scim2_models.rfc7643.user import User


class Sub(ComplexAttribute):
    dummy: str


class Sup(Resource):
    schemas: Annotated[list[str], Required.true] = ["urn:example:2.0:Sup"]
    dummy: str
    sub: Sub
    subs: list[Sub]


def test_guess_root_type():
    assert Sup.get_field_root_type("dummy") is str
    assert Sup.get_field_root_type("sub") == Sub
    assert Sup.get_field_root_type("subs") == Sub


class ReturnedModel(BaseModel):
    always: Annotated[Optional[str], Returned.always] = None
    never: Annotated[Optional[str], Returned.never] = None
    default: Annotated[Optional[str], Returned.default] = None
    request: Annotated[Optional[str], Returned.request] = None


class Baz(ComplexAttribute):
    baz_snake_case: str


class Foo(Resource):
    schemas: Annotated[list[str], Required.true] = ["urn:example:2.0:Foo"]
    sub: Annotated[ReturnedModel, Returned.default]
    bar: str
    snake_case: str
    baz: Optional[Baz] = None


class Bar(Resource):
    schemas: Annotated[list[str], Required.true] = ["urn:example:2.0:Bar"]
    sub: Annotated[ReturnedModel, Returned.default]
    bar: str
    snake_case: str
    baz: Optional[Baz] = None


class MyExtension(Extension):
    schemas: Annotated[list[str], Required.true] = ["urn:example:2.0:MyExtension"]
    baz: str


def test_validate_attribute_urn():
    """Test the method that validates and normalizes attribute URNs."""
    assert validate_attribute_urn("bar", Foo) == "urn:example:2.0:Foo:bar"
    assert (
        validate_attribute_urn("urn:example:2.0:Foo:bar", Foo)
        == "urn:example:2.0:Foo:bar"
    )
    assert (
        validate_attribute_urn("urn:example:2.0:Foo:bar", User, resource_types=[Foo])
        == "urn:example:2.0:Foo:bar"
    )

    assert validate_attribute_urn("sub", Foo) == "urn:example:2.0:Foo:sub"
    assert (
        validate_attribute_urn("urn:example:2.0:Foo:sub", Foo)
        == "urn:example:2.0:Foo:sub"
    )
    assert (
        validate_attribute_urn("urn:example:2.0:Foo:sub", User, resource_types=[Foo])
        == "urn:example:2.0:Foo:sub"
    )

    assert validate_attribute_urn("sub.always", Foo) == "urn:example:2.0:Foo:sub.always"
    assert (
        validate_attribute_urn("urn:example:2.0:Foo:sub.always", Foo)
        == "urn:example:2.0:Foo:sub.always"
    )
    assert (
        validate_attribute_urn(
            "urn:example:2.0:Foo:sub.always", User, resource_types=[Foo]
        )
        == "urn:example:2.0:Foo:sub.always"
    )

    assert validate_attribute_urn("snakeCase", Foo) == "urn:example:2.0:Foo:snakeCase"
    assert (
        validate_attribute_urn("urn:example:2.0:Foo:snakeCase", Foo)
        == "urn:example:2.0:Foo:snakeCase"
    )

    assert (
        validate_attribute_urn("urn:example:2.0:MyExtension:baz", Foo[MyExtension])
        == "urn:example:2.0:MyExtension:baz"
    )
    assert (
        validate_attribute_urn(
            "urn:example:2.0:MyExtension:baz", resource_types=[Foo[MyExtension]]
        )
        == "urn:example:2.0:MyExtension:baz"
    )

    with pytest.raises(ValueError, match="No default schema and relative URN"):
        validate_attribute_urn("bar", resource_types=[Foo])

    with pytest.raises(
        ValueError, match="No resource matching schema 'urn:InvalidResource'"
    ):
        validate_attribute_urn("urn:InvalidResource:bar", Foo)

    with pytest.raises(
        ValueError, match="No resource matching schema 'urn:example:2.0:Foo'"
    ):
        validate_attribute_urn("urn:example:2.0:Foo:bar")

    with pytest.raises(
        ValueError, match="Model 'Foo' has no attribute named 'invalid'"
    ):
        validate_attribute_urn("urn:example:2.0:Foo:invalid", Foo)

    with pytest.raises(
        ValueError,
        match="Attribute 'bar' is not a complex attribute, and cannot have a 'invalid' sub-attribute",
    ):
        validate_attribute_urn("bar.invalid", Foo)


def test_payload_attribute_case_sensitivity():
    """RFC7643 §2.1 indicates that attribute names should be case insensitive.

    Attribute names are case insensitive and are often "camel-cased"
    (e.g., "camelCase").

    Reported by issue #39.
    """
    payload = {
        "UserName": "UserName123",
        "Active": True,
        "displayname": "BobIsAmazing",
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        "externalId": uuid.uuid4().hex,
        "name": {
            "formatted": "Ryan Leenay",
            "familyName": "Leenay",
            "givenName": "Ryan",
        },
        "emails": [
            {"Primary": True, "type": "work", "value": "testing@bob.com"},
            {"Primary": False, "type": "home", "value": "testinghome@bob.com"},
        ],
    }
    user = User.model_validate(payload)
    assert user.user_name == "UserName123"
    assert user.display_name == "BobIsAmazing"


def test_attribute_inclusion_case_sensitivity():
    """Test that attribute inclusion supports any attribute case.

    Reported by #45.
    """
    user = User.model_validate({"userName": "foobar"})
    assert user.model_dump(
        scim_ctx=Context.RESOURCE_QUERY_RESPONSE, attributes=["userName"]
    ) == {
        "userName": "foobar",
        "schemas": [
            "urn:ietf:params:scim:schemas:core:2.0:User",
        ],
    }

    assert user.model_dump(
        scim_ctx=Context.RESOURCE_QUERY_RESPONSE, attributes=["username"]
    ) == {
        "userName": "foobar",
        "schemas": [
            "urn:ietf:params:scim:schemas:core:2.0:User",
        ],
    }

    assert user.model_dump(
        scim_ctx=Context.RESOURCE_QUERY_RESPONSE, attributes=["USERNAME"]
    ) == {
        "userName": "foobar",
        "schemas": [
            "urn:ietf:params:scim:schemas:core:2.0:User",
        ],
    }

    assert user.model_dump(
        scim_ctx=Context.RESOURCE_QUERY_RESPONSE,
        attributes=["urn:ietf:params:scim:schemas:core:2.0:User:userName"],
    ) == {
        "userName": "foobar",
        "schemas": [
            "urn:ietf:params:scim:schemas:core:2.0:User",
        ],
    }

    assert user.model_dump(
        scim_ctx=Context.RESOURCE_QUERY_RESPONSE,
        attributes=["urn:ietf:params:scim:schemas:core:2.0:User:username"],
    ) == {
        "userName": "foobar",
        "schemas": [
            "urn:ietf:params:scim:schemas:core:2.0:User",
        ],
    }
    assert user.model_dump(
        scim_ctx=Context.RESOURCE_QUERY_RESPONSE,
        attributes=["URN:IETF:PARAMS:SCIM:SCHEMAS:CORE:2.0:USER:USERNAME"],
    ) == {
        "userName": "foobar",
        "schemas": [
            "urn:ietf:params:scim:schemas:core:2.0:User",
        ],
    }


def test_attribute_inclusion_schema_extensions():
    """Verifies that attributes from schema extensions work."""
    user = User[EnterpriseUser].model_validate(
        {
            "userName": "foobar",
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
                "employeeNumber": "12345"
            },
        }
    )

    expected = {
        "schemas": [
            "urn:ietf:params:scim:schemas:core:2.0:User",
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
        ],
        "userName": "foobar",
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
            "employeeNumber": "12345",
        },
    }

    assert (
        user.model_dump(
            scim_ctx=Context.RESOURCE_QUERY_RESPONSE,
            attributes=[
                "urn:ietf:params:scim:schemas:core:2.0:User:userName",
                "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:employeeNumber",
            ],
        )
        == expected
    )

    assert (
        user.model_dump(
            scim_ctx=Context.RESOURCE_QUERY_RESPONSE,
            attributes=[
                "urn:ietf:params:scim:schemas:core:2.0:User:userName",
                "URN:IETF:PARAMS:SCIM:SCHEMAS:EXTENSION:ENTERPRISE:2.0:USER:EMPLOYEENUMBER",
            ],
        )
        == expected
    )


def test_dump_after_assignment():
    """Test that attribute assignment does not break model dump."""
    user = User(id="1", user_name="ABC")
    user.meta = Meta(
        resource_type="User",
        location="/v2/Users/foo",
    )
    assert user.model_dump(scim_ctx=Context.RESOURCE_CREATION_RESPONSE) == {
        "id": "1",
        "meta": {
            "location": "/v2/Users/foo",
            "resourceType": "User",
        },
        "schemas": [
            "urn:ietf:params:scim:schemas:core:2.0:User",
        ],
        "userName": "ABC",
    }


def test_binary_attributes():
    decoded = b"This is a very long line with a lot of characters, enough to create newlines when encoded."
    encoded = "VGhpcyBpcyBhIHZlcnkgbG9uZyBsaW5lIHdpdGggYSBsb3Qgb2YgY2hhcmFjdGVycywgZW5vdWdoIHRvIGNyZWF0ZSBuZXdsaW5lcyB3aGVuIGVuY29kZWQu"

    user = User.model_validate(
        {"userName": "foobar", "x509Certificates": [{"value": encoded}]}
    )
    assert user.x509_certificates[0].value == decoded
    assert user.model_dump()["x509Certificates"][0]["value"] == encoded

    encoded_without_newlines = "VGhpcyBpcyBhIHZlcnkgbG9uZyBsaW5lIHdpdGggYSBsb3Qgb2YgY2hhcmFjdGVycywgZW5vdWdoIHRvIGNyZWF0ZSBuZXdsaW5lcyB3aGVuIGVuY29kZWQu"
    user = User.model_validate(
        {
            "userName": "foobar",
            "x509Certificates": [{"value": encoded_without_newlines}],
        }
    )
    assert user.x509_certificates[0].value == decoded
    assert user.model_dump()["x509Certificates"][0]["value"] == encoded

    encoded_with_padding = "VGhpcyBpcyBhIHZlcnkgbG9uZyBsaW5lIHdpdGggYSBsb3Qgb2YgY2hhcmFjdGVycywgZW5vdWdoIHRvIGNyZWF0ZSBuZXdsaW5lcyB3aGVuIGVuY29kZWQu=================="
    user = User.model_validate(
        {"userName": "foobar", "x509Certificates": [{"value": encoded_with_padding}]}
    )
    assert user.x509_certificates[0].value == decoded
    assert user.model_dump()["x509Certificates"][0]["value"] == encoded
