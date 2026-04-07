from typing import Annotated

import pytest
from pydantic import TypeAdapter
from pydantic import ValidationError

from scim2_models import Context
from scim2_models import CreationRequestContext
from scim2_models import CreationResponseContext
from scim2_models import PatchRequestContext
from scim2_models import PatchResponseContext
from scim2_models import QueryRequestContext
from scim2_models import QueryResponseContext
from scim2_models import ReplacementRequestContext
from scim2_models import ReplacementResponseContext
from scim2_models import SCIMSerializer
from scim2_models import SCIMValidator
from scim2_models import SearchRequestContext
from scim2_models import SearchResponseContext
from scim2_models import User


def test_validator_strips_read_only_fields_on_creation():
    """read_only fields like 'id' are stripped during creation validation."""
    adapter = TypeAdapter(
        Annotated[User, SCIMValidator(Context.RESOURCE_CREATION_REQUEST)]
    )
    user = adapter.validate_python(
        {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "userName": "bjensen",
            "id": "should-be-stripped",
        }
    )
    assert user.user_name == "bjensen"
    assert user.id is None


def test_validator_rejects_missing_required_field():
    """UserName is required in creation context and must raise on absence."""
    adapter = TypeAdapter(
        Annotated[User, SCIMValidator(Context.RESOURCE_CREATION_REQUEST)]
    )
    with pytest.raises(ValidationError, match="required"):
        adapter.validate_python(
            {
                "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            }
        )


def test_validator_accepts_valid_creation_payload():
    """A minimal valid creation payload passes validation."""
    adapter = TypeAdapter(
        Annotated[User, SCIMValidator(Context.RESOURCE_CREATION_REQUEST)]
    )
    user = adapter.validate_python(
        {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "userName": "bjensen",
        }
    )
    assert user.user_name == "bjensen"


def test_validator_passes_through_already_validated_instance():
    """An already-constructed User instance passes through without re-parsing."""
    adapter = TypeAdapter(
        Annotated[User, SCIMValidator(Context.RESOURCE_CREATION_REQUEST)]
    )
    original = User(user_name="bjensen")
    result = adapter.validate_python(original)
    assert result is original


def test_validator_with_replacement_context():
    """Replacement context allows read_write and immutable fields."""
    adapter = TypeAdapter(
        Annotated[User, SCIMValidator(Context.RESOURCE_REPLACEMENT_REQUEST)]
    )
    user = adapter.validate_python(
        {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "userName": "bjensen",
            "displayName": "Barbara Jensen",
        }
    )
    assert user.display_name == "Barbara Jensen"


def test_serializer_excludes_write_only_fields():
    """write_only fields like 'password' are excluded in query response."""
    adapter = TypeAdapter(
        Annotated[User, SCIMSerializer(Context.RESOURCE_QUERY_RESPONSE)]
    )
    user = User(user_name="bjensen", password="secret")
    user.id = "123"
    data = adapter.dump_python(user)
    assert "password" not in data
    assert data["userName"] == "bjensen"


def test_serializer_includes_id_in_response():
    """Server-assigned fields like 'id' are present in response serialization."""
    adapter = TypeAdapter(
        Annotated[User, SCIMSerializer(Context.RESOURCE_CREATION_RESPONSE)]
    )
    user = User(user_name="bjensen")
    user.id = "123"
    data = adapter.dump_python(user)
    assert data["id"] == "123"
    assert data["userName"] == "bjensen"


def test_serializer_uses_camel_case_keys():
    """Serialized keys use camelCase as required by SCIM."""
    adapter = TypeAdapter(
        Annotated[User, SCIMSerializer(Context.RESOURCE_QUERY_RESPONSE)]
    )
    user = User(user_name="bjensen", display_name="Barbara")
    user.id = "123"
    data = adapter.dump_python(user)
    assert "userName" in data
    assert "displayName" in data


def test_validator_and_serializer_combined():
    """SCIMValidator on input and SCIMSerializer on output work together."""
    input_adapter = TypeAdapter(
        Annotated[User, SCIMValidator(Context.RESOURCE_CREATION_REQUEST)]
    )
    output_adapter = TypeAdapter(
        Annotated[User, SCIMSerializer(Context.RESOURCE_CREATION_RESPONSE)]
    )
    user = input_adapter.validate_python(
        {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "userName": "bjensen",
            "id": "should-be-stripped",
            "password": "secret",
        }
    )
    assert user.id is None

    user.id = "server-assigned-id"
    data = output_adapter.dump_python(user)
    assert data["id"] == "server-assigned-id"
    assert "password" not in data


def test_creation_request_context_strips_read_only_fields():
    """CreationRequestContext[User] strips read_only fields during validation."""
    adapter = TypeAdapter(CreationRequestContext[User])
    user = adapter.validate_python(
        {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "userName": "bjensen",
            "id": "should-be-stripped",
        }
    )
    assert user.user_name == "bjensen"
    assert user.id is None


def test_creation_response_context_excludes_write_only_fields():
    """CreationResponseContext[User] excludes write_only fields."""
    adapter = TypeAdapter(CreationResponseContext[User])
    user = User(user_name="bjensen", password="secret")
    user.id = "123"
    data = adapter.dump_python(user)
    assert data["id"] == "123"
    assert "password" not in data


def test_query_request_context_rejects_write_only_fields():
    """QueryRequestContext[User] rejects write_only fields during validation."""
    adapter = TypeAdapter(QueryRequestContext[User])
    with pytest.raises(ValidationError, match="writeOnly"):
        adapter.validate_python(
            {
                "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
                "userName": "bjensen",
                "password": "secret",
            }
        )


def test_query_response_context_excludes_write_only_fields():
    """QueryResponseContext[User] excludes write_only fields."""
    adapter = TypeAdapter(QueryResponseContext[User])
    user = User(user_name="bjensen", password="secret")
    user.id = "123"
    data = adapter.dump_python(user)
    assert "password" not in data
    assert data["userName"] == "bjensen"


def test_replacement_request_context_accepts_read_write_fields():
    """ReplacementRequestContext[User] accepts read_write fields."""
    adapter = TypeAdapter(ReplacementRequestContext[User])
    user = adapter.validate_python(
        {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "userName": "bjensen",
            "displayName": "Barbara Jensen",
        }
    )
    assert user.display_name == "Barbara Jensen"


def test_replacement_response_context_excludes_write_only_fields():
    """ReplacementResponseContext[User] excludes write_only fields."""
    adapter = TypeAdapter(ReplacementResponseContext[User])
    user = User(user_name="bjensen", password="secret")
    user.id = "123"
    data = adapter.dump_python(user)
    assert data["id"] == "123"
    assert "password" not in data


def test_search_request_context_rejects_write_only_fields():
    """SearchRequestContext[User] rejects write_only fields during validation."""
    adapter = TypeAdapter(SearchRequestContext[User])
    with pytest.raises(ValidationError, match="writeOnly"):
        adapter.validate_python(
            {
                "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
                "userName": "bjensen",
                "password": "secret",
            }
        )


def test_search_response_context_excludes_write_only_fields():
    """SearchResponseContext[User] excludes write_only fields."""
    adapter = TypeAdapter(SearchResponseContext[User])
    user = User(user_name="bjensen", password="secret")
    user.id = "123"
    data = adapter.dump_python(user)
    assert "password" not in data


def test_patch_request_context_accepts_partial_payload():
    """PatchRequestContext[User] accepts a partial payload."""
    adapter = TypeAdapter(PatchRequestContext[User])
    user = adapter.validate_python(
        {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "displayName": "Barbara Jensen",
        }
    )
    assert user.display_name == "Barbara Jensen"
    assert user.user_name is None


def test_patch_response_context_excludes_write_only_fields():
    """PatchResponseContext[User] excludes write_only fields."""
    adapter = TypeAdapter(PatchResponseContext[User])
    user = User(user_name="bjensen", password="secret")
    user.id = "123"
    data = adapter.dump_python(user)
    assert data["id"] == "123"
    assert "password" not in data
