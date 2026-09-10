import datetime
import gc
import weakref
from typing import Annotated

import pytest
from pydantic import TypeAdapter
from pydantic import ValidationError

from scim2_models import URN
from scim2_models import Attribute
from scim2_models import Context
from scim2_models import EnterpriseUser
from scim2_models import Extension
from scim2_models import InvalidPathException
from scim2_models import Manager
from scim2_models import Meta
from scim2_models import Required
from scim2_models import Resource
from scim2_models import Schema
from scim2_models import User


def test_extension_getitem():
    """Test that an extension can be accessed and update with __getitem__."""
    user = User[EnterpriseUser](
        id="2819c223-7f76-453a-919d-413861904646",
        user_name="bjensen@example.com",
        meta=Meta(
            resource_type="User",
            created=datetime.datetime(
                2010, 1, 23, 4, 56, 22, tzinfo=datetime.timezone.utc
            ),
            last_modified=datetime.datetime(
                2011, 5, 13, 4, 42, 34, tzinfo=datetime.timezone.utc
            ),
            version='W\\/"a330bc54f0671c9"',
            location="https://example.com/v2/Users/2819c223-7f76-453a-919d-413861904646",
        ),
    )
    user[EnterpriseUser] = EnterpriseUser(
        cost_center="4130",
        organization="Universal Studios",
        division="Theme Park",
        department="Tour Operations",
        manager=Manager(
            value="26118915-6090-4610-87e4-49d8ca9f808d",
            ref="https://example.com/v2/Users/26118915-6090-4610-87e4-49d8ca9f808d",
            display_name="John Smith",
        ),
    )
    user[EnterpriseUser].employee_number = "701984"

    expected_payload = {
        "id": "2819c223-7f76-453a-919d-413861904646",
        "meta": {
            "created": "2010-01-23T04:56:22Z",
            "lastModified": "2011-05-13T04:42:34Z",
            "location": "https://example.com/v2/Users/2819c223-7f76-453a-919d-413861904646",
            "resourceType": "User",
            "version": 'W\\/"a330bc54f0671c9"',
        },
        "schemas": [
            "urn:ietf:params:scim:schemas:core:2.0:User",
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
        ],
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
            "employeeNumber": "701984",
            "costCenter": "4130",
            "organization": "Universal Studios",
            "division": "Theme Park",
            "department": "Tour Operations",
            "manager": {
                "value": "26118915-6090-4610-87e4-49d8ca9f808d",
                "$ref": "https://example.com/v2/Users/26118915-6090-4610-87e4-49d8ca9f808d",
                "displayName": "John Smith",
            },
        },
        "userName": "bjensen@example.com",
    }
    assert user.model_dump() == expected_payload


def test_extension_setitem():
    """Test that an extension can be set with __setitem__."""
    user = User[EnterpriseUser](
        id="2819c223-7f76-453a-919d-413861904646",
        user_name="bjensen@example.com",
        meta=Meta(
            resource_type="User",
            created=datetime.datetime(
                2010, 1, 23, 4, 56, 22, tzinfo=datetime.timezone.utc
            ),
            last_modified=datetime.datetime(
                2011, 5, 13, 4, 42, 34, tzinfo=datetime.timezone.utc
            ),
            version='W\\/"a330bc54f0671c9"',
            location="https://example.com/v2/Users/2819c223-7f76-453a-919d-413861904646",
        ),
    )
    user[EnterpriseUser] = EnterpriseUser(
        employee_number="701984",
        cost_center="4130",
        organization="Universal Studios",
        division="Theme Park",
        department="Tour Operations",
        manager=Manager(
            value="26118915-6090-4610-87e4-49d8ca9f808d",
            ref="https://example.com/v2/Users/26118915-6090-4610-87e4-49d8ca9f808d",
            display_name="John Smith",
        ),
    )

    expected_payload = {
        "id": "2819c223-7f76-453a-919d-413861904646",
        "meta": {
            "created": "2010-01-23T04:56:22Z",
            "lastModified": "2011-05-13T04:42:34Z",
            "location": "https://example.com/v2/Users/2819c223-7f76-453a-919d-413861904646",
            "resourceType": "User",
            "version": 'W\\/"a330bc54f0671c9"',
        },
        "schemas": [
            "urn:ietf:params:scim:schemas:core:2.0:User",
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
        ],
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
            "employeeNumber": "701984",
            "costCenter": "4130",
            "organization": "Universal Studios",
            "division": "Theme Park",
            "department": "Tour Operations",
            "manager": {
                "value": "26118915-6090-4610-87e4-49d8ca9f808d",
                "$ref": "https://example.com/v2/Users/26118915-6090-4610-87e4-49d8ca9f808d",
                "displayName": "John Smith",
            },
        },
        "userName": "bjensen@example.com",
    }
    assert user.model_dump() == expected_payload


def test_extension_no_payload():
    """An extension is defined but there is no matching payload."""
    payload = {
        "id": "2819c223-7f76-453a-919d-413861904646",
        "meta": {
            "created": "2010-01-23T04:56:22Z",
            "lastModified": "2011-05-13T04:42:34Z",
            "location": "https://example.com/v2/Users/2819c223-7f76-453a-919d-413861904646",
            "resourceType": "User",
            "version": 'W\\/"a330bc54f0671c9"',
        },
        "schemas": [
            "urn:ietf:params:scim:schemas:core:2.0:User",
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
        ],
        "userName": "bjensen@example.com",
    }

    User[EnterpriseUser].model_validate(payload)


def test_extension_validate_with_context():
    """Test the use of scim_ctx when validating resources with extensions."""
    payload = {
        "id": "3b0bc21d-1a10-4678-9e52-2f354c0c7544",
        "meta": {
            "created": "2010-01-23T04:56:22Z",
            "lastModified": "2011-05-13T04:42:34Z",
            "location": "https://example.com/v2/Users/3b0bc21d-1a10-4678-9e52-2f354c0c7544",
            "resourceType": "User",
            "version": 'W\\/"3694e05e9dff590"',
        },
        "schemas": [
            "urn:ietf:params:scim:schemas:core:2.0:User",
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
        ],
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
            "division": "Theme Park",
            "employeeNumber": "701984",
        },
        "userName": "bjensen@example.com",
    }
    user = User[EnterpriseUser].model_validate(
        payload, scim_ctx=Context.RESOURCE_QUERY_RESPONSE
    )
    assert type(user[EnterpriseUser]) is EnterpriseUser


def test_invalid_getitem():
    """Test that invalid paths raise KeyError."""
    user = User[EnterpriseUser](user_name="foobar")
    with pytest.raises(KeyError):
        user["invalid"]

    with pytest.raises(InvalidPathException):
        user[object]


def test_invalid_setitem():
    """Test that invalid paths raise KeyError."""
    user = User[EnterpriseUser](user_name="foobar")
    with pytest.raises(KeyError):
        user["invalid"] = "foobar"

    with pytest.raises(InvalidPathException):
        user[object] = "foobar"


def test_getitem_by_path():
    """Access attributes using path strings."""
    user = User[EnterpriseUser](user_name="bjensen", display_name="Barbara Jensen")
    user[EnterpriseUser] = EnterpriseUser(employee_number="12345")

    assert user["userName"] == "bjensen"
    assert user["displayName"] == "Barbara Jensen"
    assert (
        user[
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:employeeNumber"
        ]
        == "12345"
    )


def test_setitem_by_path():
    """Set attributes using path strings."""
    user = User[EnterpriseUser](user_name="bjensen")

    user["displayName"] = "Barbara Jensen"
    assert user.display_name == "Barbara Jensen"

    user["name.familyName"] = "Jensen"
    assert user.name.family_name == "Jensen"


def test_delitem_by_path():
    """Delete attributes using path strings."""
    user = User(user_name="bjensen", display_name="Barbara Jensen")

    del user["displayName"]
    assert user.display_name is None


def test_delitem_extension():
    """Delete extension using type."""
    user = User[EnterpriseUser](user_name="bjensen")
    user[EnterpriseUser] = EnterpriseUser(employee_number="12345")
    assert user[EnterpriseUser] is not None

    del user[EnterpriseUser]
    assert user[EnterpriseUser] is None


def test_invalid_delitem():
    """Test that invalid paths raise KeyError on delete."""
    user = User(user_name="bjensen")
    with pytest.raises(KeyError):
        del user["invalid"]


class SuperHero(Extension):
    __schema__ = URN("urn:example:extensions:2.0:SuperHero")

    superpower: str | None = None
    """The superhero superpower."""


def test_multiple_extensions_union():
    """Test that multiple extensions can be used by using Union."""
    user_model = User[EnterpriseUser | SuperHero]
    instance = user_model()
    instance[SuperHero] = SuperHero(superpower="flight")
    assert instance[SuperHero].superpower == "flight"
    assert instance.model_dump() == {
        "schemas": [
            "urn:ietf:params:scim:schemas:core:2.0:User",
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
            "urn:example:extensions:2.0:SuperHero",
        ],
        "urn:example:extensions:2.0:SuperHero": {
            "superpower": "flight",
        },
    }


def test_extensions_schemas():
    """Verifies that attributes from schema extensions work."""
    user = User[EnterpriseUser].model_validate(
        {
            "userName": "foobar",
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
                "employeeNumber": "12345"
            },
        }
    )
    assert user.model_dump(
        scim_ctx=Context.RESOURCE_QUERY_RESPONSE,
        attributes=[
            "urn:ietf:params:scim:schemas:core:2.0:User:userName",
        ],
    ) == {
        "schemas": [
            "urn:ietf:params:scim:schemas:core:2.0:User",
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
        ],
        "userName": "foobar",
    }


def test_validate_items_without_extension():
    """A model with an optional extension should be able to validate a payload without an extension payload.

    https://github.com/python-scim/scim2-models/issues/77
    """
    payload = {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        "id": "new-user",
        "userName": "new-user@example.com",
        "meta": {
            "resourceType": "User",
            "created": "2010-01-23T04:56:22Z",
            "lastModified": "2011-05-13T04:42:34Z",
            "version": 'W\\/"3694e05e9dff590"',
            "location": "http://localhost:46459/Users/new-user",
        },
    }
    User[EnterpriseUser].model_validate(
        payload, scim_ctx=Context.RESOURCE_CREATION_RESPONSE
    )


def test_get_extension_model():
    assert User[EnterpriseUser].get_extension_model("EnterpriseUser") == EnterpriseUser
    assert (
        User[EnterpriseUser].get_extension_model(
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"
        )
        == EnterpriseUser
    )

    assert (
        User[EnterpriseUser | SuperHero].get_extension_model("EnterpriseUser")
        == EnterpriseUser
    )
    assert (
        User[EnterpriseUser | SuperHero].get_extension_model(
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"
        )
        == EnterpriseUser
    )

    assert User[SuperHero].get_extension_model("EnterpriseUser") is None
    assert (
        User[SuperHero].get_extension_model(
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"
        )
        is None
    )
    assert User.get_extension_model("EnterpriseUser") is None
    assert (
        User.get_extension_model(
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"
        )
        is None
    )


def test_class_getitem():
    UserEnt = User[EnterpriseUser]
    UserEnt2 = UserEnt[EnterpriseUser]
    assert UserEnt is UserEnt2

    # Test line 178: invalid extension type raises TypeError
    with pytest.raises(TypeError, match="is not a valid Extension type"):
        User[str]

    with pytest.raises(TypeError, match="is not a valid Extension type"):
        User[int]


def test_dump_resource_with_unset_extension():
    """Serialize a resource whose extension is declared but not populated."""
    user = User[EnterpriseUser](user_name="bjensen")
    ta = TypeAdapter(User[EnterpriseUser])
    payload = ta.dump_python(user)
    assert "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User" not in payload


def test_model_attribute_to_scim_attribute_error():
    """Test error case where get_field_root_type returns None."""
    from pydantic import Field

    from scim2_models.base import BaseModel
    from scim2_models.resources.resource import _model_attribute_to_scim_attribute

    # Create a model with a field that has no clear root type
    class TestModel(BaseModel):
        problematic_field: str | None = Field(default=None)

    # Mock get_field_root_type to return None
    original_method = TestModel.get_field_root_type
    TestModel.get_field_root_type = classmethod(lambda cls, attr: None)

    try:
        with pytest.raises(
            ValueError,
            match="Could not determine root type for attribute problematic_field",
        ):
            _model_attribute_to_scim_attribute(TestModel, "problematic_field")
    finally:
        # Restore the original method
        TestModel.get_field_root_type = original_method


def test_a_parameterized_model_built_at_runtime_is_collected_once_it_is_dropped():
    """Parameterizing a model discovered from a schema does not keep it alive.

    A server serving the schemas of its tenants builds a model per schema, then
    parameterizes it with the extensions its ``ResourceType`` declares. The
    classes parameterization answers used to hold every one of them for as long
    as the process ran.
    """
    Model = Resource.from_schema(
        Schema(
            id="urn:example:2.0:Pet",
            name="Pet",
            attributes=[
                Attribute(name="label", type=Attribute.Type.string, multi_valued=False)
            ],
        )
    )
    reference = weakref.ref(Model)

    # The assertion is made on a value that does not name the model, since
    # pytest keeps the operands of an assertion for as long as the test runs.
    parameterized = Model[EnterpriseUser].get_extension_models() == {
        EnterpriseUser.__schema__: EnterpriseUser
    }
    assert parameterized

    del Model

    # The first pass frees the validators pydantic built for the model, which
    # is what leaves the model itself unreachable for the second one.
    gc.collect()
    gc.collect()

    assert reference() is None


def test_a_required_extension_must_be_carried_by_a_creation_request():
    """An extension a resource type declares required must be present.

    :rfc:`RFC7643 §6 <7643#section-6>` has ``schemaExtensions.required`` mean
    that "a resource of this type MUST include this schema extension", which
    annotating the parameter with :attr:`Required.true <scim2_models.Required.true>`
    expresses.
    """
    payload = {"schemas": [User.__schema__], "userName": "bjensen"}

    with pytest.raises(ValidationError, match="Field 'EnterpriseUser' is required"):
        User[Annotated[EnterpriseUser, Required.true]].model_validate(
            payload, scim_ctx=Context.RESOURCE_CREATION_REQUEST
        )


def test_a_required_extension_is_accepted_when_the_payload_carries_it():
    payload = {
        "schemas": [User.__schema__, EnterpriseUser.__schema__],
        "userName": "bjensen",
        EnterpriseUser.__schema__: {"employeeNumber": "701984"},
    }

    user = User[Annotated[EnterpriseUser, Required.true]].model_validate(
        payload, scim_ctx=Context.RESOURCE_CREATION_REQUEST
    )

    assert user[EnterpriseUser].employee_number == "701984"


def test_an_optional_extension_may_be_left_out_of_a_creation_request():
    """An extension is optional unless the parameter says otherwise.

    :rfc:`RFC7643 §2.2 <7643#section-2.2>` makes optionality the implicit value
    of any attribute, so both the bare parameter and the one annotated
    :attr:`Required.false <scim2_models.Required.false>` accept the payload.
    """
    payload = {"schemas": [User.__schema__], "userName": "bjensen"}

    for model in (
        User[EnterpriseUser],
        User[Annotated[EnterpriseUser, Required.false]],
    ):
        user = model.model_validate(payload, scim_ctx=Context.RESOURCE_CREATION_REQUEST)
        assert user[EnterpriseUser] is None


def test_the_necessity_of_an_extension_tells_two_parameterizations_apart():
    required = User[Annotated[EnterpriseUser, Required.true]]

    assert required is not User[EnterpriseUser]
    assert required is User[Annotated[EnterpriseUser, Required.true]]


def test_an_annotated_extension_is_reached_the_way_a_bare_one_is():
    """The annotation qualifies the parameter, it does not rename it."""
    model = User[Annotated[EnterpriseUser, Required.true]]
    user = model(user_name="bjensen")

    user[EnterpriseUser] = EnterpriseUser(employee_number="701984")

    assert user[EnterpriseUser].employee_number == "701984"
    assert model.get_extension_models() == {EnterpriseUser.__schema__: EnterpriseUser}
