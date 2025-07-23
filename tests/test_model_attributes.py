import uuid
from typing import Annotated
from typing import Optional

from scim2_models.annotations import Required
from scim2_models.annotations import Returned
from scim2_models.attributes import ComplexAttribute
from scim2_models.base import BaseModel
from scim2_models.context import Context
from scim2_models.messages.error import Error
from scim2_models.messages.patch_op import PatchOp
from scim2_models.resources.enterprise_user import EnterpriseUser
from scim2_models.resources.resource import Extension
from scim2_models.resources.resource import Meta
from scim2_models.resources.resource import Resource
from scim2_models.resources.user import User
from scim2_models.urn import _validate_attribute_urn


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
    assert _validate_attribute_urn("bar", Foo) == "urn:example:2.0:Foo:bar"
    assert (
        _validate_attribute_urn("urn:example:2.0:Foo:bar", Foo)
        == "urn:example:2.0:Foo:bar"
    )

    assert _validate_attribute_urn("sub", Foo) == "urn:example:2.0:Foo:sub"
    assert (
        _validate_attribute_urn("urn:example:2.0:Foo:sub", Foo)
        == "urn:example:2.0:Foo:sub"
    )

    assert (
        _validate_attribute_urn("sub.always", Foo) == "urn:example:2.0:Foo:sub.always"
    )
    assert (
        _validate_attribute_urn("urn:example:2.0:Foo:sub.always", Foo)
        == "urn:example:2.0:Foo:sub.always"
    )

    assert _validate_attribute_urn("snakeCase", Foo) == "urn:example:2.0:Foo:snakeCase"
    assert (
        _validate_attribute_urn("urn:example:2.0:Foo:snakeCase", Foo)
        == "urn:example:2.0:Foo:snakeCase"
    )

    assert (
        _validate_attribute_urn("urn:example:2.0:MyExtension:baz", Foo[MyExtension])
        == "urn:example:2.0:MyExtension:baz"
    )

    assert _validate_attribute_urn("urn:InvalidResource:bar", Foo) is None

    assert _validate_attribute_urn("urn:example:2.0:Foo:invalid", Foo) is None

    assert _validate_attribute_urn("bar.invalid", Foo) is None

    assert (
        _validate_attribute_urn("urn:example:2.0:MyExtension:invalid", Foo[MyExtension])
        is None
    )


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


def test_scim_object_model_dump_coverage():
    """Test ScimObject.model_dump for coverage of mode setting."""
    # Test with scim_ctx=None (no mode setting)
    error = Error(status="400", detail="Test error")
    result = error.model_dump(scim_ctx=None)
    assert isinstance(result, dict)

    # Test model_dump_json coverage
    json_result = error.model_dump_json(scim_ctx=None)
    assert isinstance(json_result, str)


def test_patch_op_preserves_case_in_value_fields():
    """Test that PatchOp preserves original case in operation values."""
    # Test data from the GitHub issue
    patch_data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [
            {
                "op": "replace",
                "value": {
                    "streetAddress": "911 Universal City Plaza",
                },
            }
        ],
    }

    patch_op = PatchOp[User].model_validate(patch_data)
    result = patch_op.model_dump()

    value = result["Operations"][0]["value"]
    assert value["streetAddress"] == "911 Universal City Plaza"


def test_patch_op_preserves_case_in_sub_value_fields():
    """Test that nested objects within Any fields are still normalized according to their schema."""
    patch_data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [
            {
                "op": "replace",
                "value": {
                    "name": {"givenName": "John"},
                },
            }
        ],
    }

    patch_op = PatchOp[User].model_validate(patch_data)
    result = patch_op.model_dump()

    value = result["Operations"][0]["value"]

    assert value["name"]["givenName"] == "John"
