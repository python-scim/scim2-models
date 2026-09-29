import pytest
from pydantic import ValidationError

from scim2_models import Attribute
from scim2_models import Context
from scim2_models import ListResponse
from scim2_models import Resource
from scim2_models import Returned
from scim2_models import Schema
from scim2_models import User


def test_the_password_is_not_in_the_repr_of_a_user():
    """A user shows its attributes but not its password."""
    user = User(user_name="bjensen", password="S3cr3t!")

    assert "bjensen" in repr(user)
    assert "S3cr3t!" not in repr(user)
    assert "S3cr3t!" not in str(user)


def test_the_password_is_not_in_the_repr_of_a_list_response():
    """Nested resources hide their password too."""
    response = ListResponse[User](
        total_results=1,
        resources=[User(user_name="bjensen", password="S3cr3t!")],
    )

    assert "bjensen" in repr(response)
    assert "S3cr3t!" not in repr(response)


def test_a_never_returned_attribute_of_a_schema_model_is_not_in_the_repr():
    """Models built from a schema hide their never-returned attributes."""
    schema = Schema(
        id="urn:example:schemas:Device",
        name="Device",
        attributes=[
            Attribute(name="label", type=Attribute.Type.string),
            Attribute(
                name="secret", type=Attribute.Type.string, returned=Returned.never
            ),
        ],
    )
    Device = Resource.from_schema(schema)
    device = Device(label="printer", secret="S3cr3t!")

    assert "printer" in repr(device)
    assert "S3cr3t!" not in repr(device)


def test_the_password_is_not_in_a_schema_error_message():
    """A payload refused as a whole does not show its password in the message."""
    payload = {
        "schemas": ["urn:bad"],
        "userName": "bjensen",
        "password": "S3cr3t!",
    }

    with pytest.raises(ValidationError) as exc_info:
        User.model_validate(payload)

    assert "S3cr3t!" not in str(exc_info.value)
    assert exc_info.value.errors()[0]["input"] == payload


def test_the_password_is_not_in_a_mutability_error_message():
    """A password refused in a query does not show in the message."""
    with pytest.raises(ValidationError) as exc_info:
        User.model_validate(
            {"userName": "bjensen", "password": "S3cr3t!"},
            scim_ctx=Context.RESOURCE_QUERY_REQUEST,
        )

    assert "S3cr3t!" not in str(exc_info.value)
    assert exc_info.value.errors()[0]["input"] == "S3cr3t!"
