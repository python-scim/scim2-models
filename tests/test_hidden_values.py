from typing import Annotated

import pytest
from pydantic import ValidationError

from scim2_models import Attribute
from scim2_models import Context
from scim2_models import Extension
from scim2_models import ListResponse
from scim2_models import Mutability
from scim2_models import PatchOp
from scim2_models import PatchOperation
from scim2_models import Resource
from scim2_models import Returned
from scim2_models import Schema
from scim2_models import User

USER_SCHEMA = "urn:ietf:params:scim:schemas:core:2.0:User"


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


@pytest.mark.parametrize(
    "path,value",
    [
        ("password", "S3cr3t!"),
        ("PASSWORD", "S3cr3t!"),
        (f"{USER_SCHEMA}:password", "S3cr3t!"),
        (None, {"userName": "bjensen", "password": "S3cr3t!"}),
        (None, {USER_SCHEMA: {"password": "S3cr3t!"}}),
    ],
)
def test_the_password_is_not_in_the_repr_of_a_patch_operation(path, value):
    """A PATCH operation that writes a password does not show its value."""
    operation = PatchOperation[User](op="replace", path=path, value=value)

    assert "S3cr3t!" not in repr(operation)


def test_the_password_is_not_in_the_repr_of_a_patch_request():
    """A PATCH request does not show the password its operations write."""
    patch = PatchOp[User].model_validate(
        {
            "Operations": [
                {"op": "replace", "value": {"password": "S3cr3t!"}},
                {"op": "replace", "path": "nickName", "value": "Babs"},
            ]
        }
    )

    assert "S3cr3t!" not in repr(patch)
    assert "Babs" in repr(patch)


def test_an_operation_hides_the_password_once_its_patch_request_types_it():
    """An operation built without a resource type cannot tell a password apart until a PatchOp types it."""
    operation = PatchOperation(op="replace", value={"password": "S3cr3t!"})

    assert "S3cr3t!" in repr(operation)
    assert "S3cr3t!" not in repr(PatchOp[User](operations=[operation]))


def test_a_patch_operation_shows_the_values_of_visible_attributes():
    """Values that write no hidden attribute stay in the repr, even with keys that are not attributes."""
    value = {
        "nickName": "Babs",
        "name": {"givenName": "Barbara"},
        "emails": [{"value": "bjensen@example.com"}],
        "not an attribute": "kept",
        42: "kept",
    }
    operation = PatchOperation[User](op="add", value=value)

    assert repr(value) in repr(operation)


def test_a_hidden_attribute_of_an_extension_is_not_in_the_repr_of_a_patch_operation():
    """A write-only attribute of an extension hides the value that writes it."""

    class Vault(Extension):
        __schema__ = "urn:example:schemas:Vault"

        pin: Annotated[str | None, Mutability.write_only] = None

    operation = PatchOperation[User[Vault]](
        op="add", value={"urn:example:schemas:Vault": {"pin": "S3cr3t!"}}
    )

    assert "S3cr3t!" not in repr(operation)


def test_a_hidden_sub_attribute_is_not_in_the_repr_of_a_patch_operation():
    """A never-returned sub-attribute hides the value that writes it."""
    schema = Schema(
        id="urn:example:schemas:Device",
        name="Device",
        attributes=[
            Attribute(
                name="credentials",
                type=Attribute.Type.complex,
                sub_attributes=[
                    Attribute(name="login", type=Attribute.Type.string),
                    Attribute(
                        name="secret",
                        type=Attribute.Type.string,
                        returned=Returned.never,
                    ),
                ],
            ),
        ],
    )
    Device = Resource.from_schema(schema)

    by_path = PatchOperation[Device](
        op="replace", path="credentials.secret", value="S3cr3t!"
    )
    by_value = PatchOperation[Device](
        op="replace", path="credentials", value={"login": "l", "secret": "S3cr3t!"}
    )

    assert "S3cr3t!" not in repr(by_path)
    assert "S3cr3t!" not in repr(by_value)


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
