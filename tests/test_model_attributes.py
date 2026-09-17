import uuid
from typing import Annotated

import pytest
from pydantic import AliasChoices
from pydantic import AliasPath
from pydantic import Base64Bytes
from pydantic import Field
from pydantic import ValidationError

from scim2_models import URN
from scim2_models import ResponseParameters
from scim2_models.annotations import CaseExact
from scim2_models.annotations import Returned
from scim2_models.attributes import ComplexAttribute
from scim2_models.base import BaseModel
from scim2_models.context import Context
from scim2_models.messages.error import Error
from scim2_models.messages.patch_op import PatchOp
from scim2_models.reference import Reference
from scim2_models.resources.enterprise_user import EnterpriseUser
from scim2_models.resources.group import Group
from scim2_models.resources.group import GroupMember
from scim2_models.resources.resource import Extension
from scim2_models.resources.resource import Meta
from scim2_models.resources.resource import Resource
from scim2_models.resources.user import User


class Sub(ComplexAttribute):
    dummy: str


class Sup(Resource):
    __schema__ = URN("urn:example:2.0:Sup")

    dummy: str
    sub: Sub
    subs: list[Sub]
    ref: Reference[Sub]
    refunion: Reference[Sub | User]


def test_guess_root_type():
    assert Sup.get_field_root_type("dummy") is str
    assert Sup.get_field_root_type("sub") == Sub
    assert Sup.get_field_root_type("subs") == Sub
    assert Sup.get_field_root_type("ref") == Reference[Sub]
    assert Sup.get_field_root_type("refunion") == Reference[Sub | User]


class CaseSensitivity(Resource):
    __schema__ = URN("urn:example:2.0:CaseSensitivity")

    text: str | None = None
    ref: Reference[Sub] | None = None
    certificate: Base64Bytes | None = None
    insensitive_ref: Annotated[Reference[Sub] | None, CaseExact.false] = None


def test_reference_and_binary_values_are_case_exact():
    """RFC7643 §2.3.6 and §2.3.7 state that binary and reference values are case exact, whatever the schema representations of §8.7 say."""
    assert CaseSensitivity.get_field_annotation("text", CaseExact) == CaseExact.false
    assert CaseSensitivity.get_field_annotation("ref", CaseExact) == CaseExact.true
    assert (
        CaseSensitivity.get_field_annotation("certificate", CaseExact) == CaseExact.true
    )


def test_case_exact_annotation_takes_precedence_over_the_field_type():
    """Models can declare a reference to be case insensitive."""
    assert (
        CaseSensitivity.get_field_annotation("insensitive_ref", CaseExact)
        == CaseExact.false
    )


class ReturnedModel(BaseModel):
    always: Annotated[str | None, Returned.always] = None
    never: Annotated[str | None, Returned.never] = None
    default: Annotated[str | None, Returned.default] = None
    request: Annotated[str | None, Returned.request] = None


class Baz(ComplexAttribute):
    baz_snake_case: str


class Foo(Resource):
    __schema__ = URN("urn:example:2.0:Foo")

    sub: Annotated[ReturnedModel, Returned.default]
    bar: str
    snake_case: str
    baz: Baz | None = None


class Bar(Resource):
    __schema__ = URN("urn:example:2.0:Bar")

    sub: Annotated[ReturnedModel, Returned.default]
    bar: str
    snake_case: str
    baz: Baz | None = None


class MyExtension(Extension):
    __schema__ = URN("urn:example:2.0:MyExtension")

    baz: str


class DeepSubAttribute(ComplexAttribute):
    name: str | None = None


class DeepAttribute(ComplexAttribute):
    name: str | None = None
    sub_attributes: list[DeepSubAttribute] | None = None


class DeepResource(Resource):
    __schema__ = URN("urn:example:2.0:DeepResource")

    attributes: list[DeepAttribute] | None = None


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
        scim_ctx=Context.RESOURCE_QUERY_RESPONSE,
        response_parameters=ResponseParameters(attributes=["userName"]),
    ) == {
        "userName": "foobar",
        "schemas": [
            "urn:ietf:params:scim:schemas:core:2.0:User",
        ],
    }

    assert user.model_dump(
        scim_ctx=Context.RESOURCE_QUERY_RESPONSE,
        response_parameters=ResponseParameters(attributes=["username"]),
    ) == {
        "userName": "foobar",
        "schemas": [
            "urn:ietf:params:scim:schemas:core:2.0:User",
        ],
    }

    assert user.model_dump(
        scim_ctx=Context.RESOURCE_QUERY_RESPONSE,
        response_parameters=ResponseParameters(attributes=["USERNAME"]),
    ) == {
        "userName": "foobar",
        "schemas": [
            "urn:ietf:params:scim:schemas:core:2.0:User",
        ],
    }

    assert user.model_dump(
        scim_ctx=Context.RESOURCE_QUERY_RESPONSE,
        response_parameters=ResponseParameters(
            attributes=["urn:ietf:params:scim:schemas:core:2.0:User:userName"]
        ),
    ) == {
        "userName": "foobar",
        "schemas": [
            "urn:ietf:params:scim:schemas:core:2.0:User",
        ],
    }

    assert user.model_dump(
        scim_ctx=Context.RESOURCE_QUERY_RESPONSE,
        response_parameters=ResponseParameters(
            attributes=["urn:ietf:params:scim:schemas:core:2.0:User:username"]
        ),
    ) == {
        "userName": "foobar",
        "schemas": [
            "urn:ietf:params:scim:schemas:core:2.0:User",
        ],
    }
    assert user.model_dump(
        scim_ctx=Context.RESOURCE_QUERY_RESPONSE,
        response_parameters=ResponseParameters(
            attributes=["URN:IETF:PARAMS:SCIM:SCHEMAS:CORE:2.0:USER:USERNAME"]
        ),
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
            response_parameters=ResponseParameters(
                attributes=[
                    "urn:ietf:params:scim:schemas:core:2.0:User:userName",
                    "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:employeeNumber",
                ]
            ),
        )
        == expected
    )

    assert (
        user.model_dump(
            scim_ctx=Context.RESOURCE_QUERY_RESPONSE,
            response_parameters=ResponseParameters(
                attributes=[
                    "urn:ietf:params:scim:schemas:core:2.0:User:userName",
                    "URN:IETF:PARAMS:SCIM:SCHEMAS:EXTENSION:ENTERPRISE:2.0:USER:EMPLOYEENUMBER",
                ]
            ),
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
                    "addresses": [{"streetAddress": "911 Universal City Plaza"}],
                },
            }
        ],
    }

    patch_op = PatchOp[User].model_validate(patch_data)
    result = patch_op.model_dump()

    value = result["Operations"][0]["value"]
    assert value["addresses"][0]["streetAddress"] == "911 Universal City Plaza"


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


def test_complex_attribute_inclusion_includes_sub_attributes():
    """When a complex attribute is requested, its sub-attributes should be included."""
    user = User(
        user_name="bjensen",
        name={"given_name": "Barbara", "family_name": "Jensen"},
    )
    result = user.model_dump(
        scim_ctx=Context.RESOURCE_QUERY_RESPONSE,
        response_parameters=ResponseParameters(attributes=["name"]),
    )
    assert result["name"] == {"givenName": "Barbara", "familyName": "Jensen"}


def test_multivalued_complex_attribute_inclusion_includes_sub_attributes():
    """When a multi-valued complex attribute is requested, its sub-attributes should be included."""
    group = Group(
        id="group-123",
        display_name="Engineering",
        members=[
            GroupMember(value="user-1", type="User"),
            GroupMember(value="user-2", type="User"),
        ],
    )
    result = group.model_dump(
        scim_ctx=Context.RESOURCE_QUERY_RESPONSE,
        response_parameters=ResponseParameters(attributes=["members"]),
    )
    assert result["members"] == [
        {"value": "user-1", "type": "User"},
        {"value": "user-2", "type": "User"},
    ]


def test_nested_complex_attribute_urn_is_prefixed_by_its_parents():
    """Sub-attributes of a nested complex attribute are marked with the URN of their whole parent chain."""
    resource = DeepResource(
        id="deep",
        attributes=[
            DeepAttribute(
                name="name",
                sub_attributes=[DeepSubAttribute(name="formatted")],
            )
        ],
    )
    resource.model_dump(scim_ctx=Context.RESOURCE_QUERY_RESPONSE)
    attribute = resource.attributes[0]
    sub_attribute = attribute.sub_attributes[0]

    assert attribute._get_attribute_urn("name") == (
        "urn:example:2.0:DeepResource:attributes.name"
    )
    assert sub_attribute._get_attribute_urn("name") == (
        "urn:example:2.0:DeepResource:attributes.subAttributes.name"
    )


def test_extension_excluded_by_full_urn():
    """Excluding an extension attribute with its full URN removes only that attribute."""
    user = User[EnterpriseUser].model_validate(
        {
            "userName": "foobar",
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
                "employeeNumber": "12345",
                "department": "Engineering",
            },
        }
    )
    result = user.model_dump(
        scim_ctx=Context.RESOURCE_QUERY_RESPONSE,
        response_parameters=ResponseParameters(
            excluded_attributes=[
                "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:employeeNumber"
            ]
        ),
    )
    ext = result["urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"]
    assert "employeeNumber" not in ext
    assert ext["department"] == "Engineering"


def test_field_with_custom_validation_aliases():
    """A field is read under every name it declares for itself."""

    class AliasedResource(Resource):
        __schema__ = URN("urn:example:2.0:AliasedResource")

        value: str | None = Field(
            None, validation_alias=AliasChoices("value", "legacyvalue")
        )

    assert AliasedResource.__scim_info__.field_by_name["legacyvalue"] == "value"

    obj = AliasedResource.model_validate({"legacyValue": "x"})

    assert obj.value == "x"
    assert obj.model_dump(scim_ctx=Context.RESOURCE_QUERY_RESPONSE) == {
        "schemas": ["urn:example:2.0:AliasedResource"],
        "value": "x",
    }


def test_short_attr_path_with_plain_name():
    """The short-path helper returns plain attribute names unchanged."""
    from scim2_models.base import _short_attr_path

    assert _short_attr_path("userName") == "userName"
    assert _short_attr_path("name.familyName") == "name.familyName"


@pytest.mark.parametrize(
    "spelling", ["userName", "username", "USERNAME", "UserName", "user_name"]
)
def test_an_attribute_name_is_read_whatever_its_case(spelling):
    """RFC7643 §2.1 makes attribute names case-insensitive."""
    user = User.model_validate({"schemas": [str(User.__schema__)], spelling: "bjensen"})

    assert user.user_name == "bjensen"


@pytest.mark.parametrize(
    "spelling", ["user-name", "u.s.e.r.n.a.m.e", "user$name", "username "]
)
def test_a_name_differing_by_punctuation_is_another_attribute(spelling):
    """The nameChar rule of RFC7643 §2.1 makes $, - and _ part of a name, so dropping them would merge two attributes into one."""
    with pytest.raises(ValidationError) as exc_info:
        User.model_validate({"schemas": [str(User.__schema__)], spelling: "bjensen"})

    assert exc_info.value.errors()[0]["loc"] == (spelling,)


def test_an_unknown_attribute_is_named_as_the_peer_spelled_it():
    """A refusal quotes what was sent, so that the peer can find it in its own payload."""
    with pytest.raises(ValidationError) as exc_info:
        User.model_validate({"schemas": [str(User.__schema__)], "usr_Name": "bjensen"})

    assert exc_info.value.errors()[0]["loc"] == ("usr_Name",)


def test_a_field_is_read_under_the_alias_it_declares():
    """An alias naming an attribute the camel-cased field name would not spell is honoured."""

    class Aliased(Resource):
        __schema__ = URN("urn:example:2.0:Aliased")

        string_field: str | None = Field(None, alias="string_field")

    obj = Aliased.model_validate({"string_field": "x"})

    assert obj.string_field == "x"


def test_an_alias_wins_over_the_python_name_of_another_field():
    """The name an attribute is serialized under is the one SCIM names it by, where a Python field name is only the spelling pydantic offers."""

    class Aliased(Resource):
        __schema__ = URN("urn:example:2.0:Aliased")

        user_name: str | None = None
        legacy: str | None = Field(None, serialization_alias="user_name")

    obj = Aliased.model_validate(
        {"schemas": [str(Aliased.__schema__)], "userName": "a", "user_name": "b"}
    )

    assert obj.user_name == "a"
    assert obj.legacy == "b"


def test_a_constructor_keyword_reaches_the_field_the_attribute_name_designates():
    """A keyword is resolved as a payload key is, so an alias covering it takes it."""

    class Aliased(Resource):
        __schema__ = URN("urn:example:2.0:Aliased")

        user_name: str | None = None
        legacy: str | None = Field(None, serialization_alias="user_name")

    obj = Aliased(user_name="x")

    assert obj.legacy == "x"
    assert obj.user_name is None


def test_two_fields_cannot_answer_to_one_attribute_name():
    """A model whose fields share an attribute name is refused where it is written, no payload key being able to reach both."""
    with pytest.raises(TypeError, match="two fields answering"):

        class Ambiguous(Resource):
            __schema__ = URN("urn:example:2.0:Ambiguous")

            display_name: str | None = None
            legacy: str | None = Field(None, serialization_alias="displayName")


def test_an_extension_is_named_by_its_field_as_well_as_by_its_urn():
    """An extension answers to its class name, which is what a dump without aliases carries."""
    extended = User[EnterpriseUser](
        user_name="bjensen", EnterpriseUser=EnterpriseUser(department="Sales")
    )

    assert extended[EnterpriseUser].department == "Sales"

    revalidated = User[EnterpriseUser].model_validate(
        extended.model_dump(scim_ctx=None)
    )

    assert revalidated[EnterpriseUser].department == "Sales"


def test_a_payload_naming_one_attribute_twice_keeps_the_last_spelling():
    """RFC7643 §2.1 makes two cases of one name the same attribute, so the payload assigns it twice."""
    user = User.model_validate(
        {"schemas": [str(User.__schema__)], "userName": "first", "USERNAME": "last"}
    )

    assert user.user_name == "last"


def test_the_name_a_field_is_serialized_under_falls_back_on_its_camel_case():
    """Every model carries an alias generator, so the fallback answers for a field defined without one."""

    class Bare(BaseModel):
        model_config = {}

        user_name: str | None = None

    assert Bare._scim_name("user_name") == "userName"


def test_an_alias_naming_a_place_in_the_payload_names_no_attribute():
    """An AliasPath reaches into a payload rather than naming an attribute, so it adds no name a peer may use."""

    class Nested(Resource):
        __schema__ = URN("urn:example:2.0:Nested")

        value: str | None = Field(None, validation_alias=AliasPath("outer", "inner"))

    assert "outer" not in Nested.__scim_info__.field_by_name
    assert Nested.__scim_info__.validation_names["value"] == "value"
