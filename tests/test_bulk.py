import pytest
from pydantic import ValidationError

from scim2_models.base import Context
from scim2_models.messages.bulk import BulkOperation
from scim2_models.messages.bulk import BulkRequest
from scim2_models.messages.bulk import BulkResponse
from scim2_models.messages.patch_op import PatchOp
from scim2_models.messages.patch_op import PatchOperation
from scim2_models.resources.group import Group
from scim2_models.resources.group import GroupMember
from scim2_models.resources.user import User


def test_operations_required_for_bulk_request():
    with pytest.raises(ValidationError):
        BulkRequest.model_validate(
            {"operations": None}, context={"scim": Context.RESOURCE_CREATION_REQUEST}
        )


def test_operations_required_for_bulk_response():
    with pytest.raises(ValidationError):
        BulkResponse.model_validate(
            {"operations": None}, context={"scim": Context.RESOURCE_CREATION_REQUEST}
        )


def test_bulkId_required_for_post_bulk_operations():
    """Test that bulkId is required for POST bulk operations.

    :rfc:`RFC7644` §3.7 <7644#section-3.7>: "bulkId [is] REQUIRED when "method" is "POST"."
    """
    BulkOperation.model_validate(
        {
            "method": BulkOperation.Method.post,
            "bulk_id": "qwerty",
            "path": "/Users",
            "data": {"displayName": "John Doe"},
        },
        context={"scim": Context.RESOURCE_CREATION_REQUEST},
    )
    with pytest.raises(ValidationError):
        BulkOperation.model_validate(
            {
                "method": BulkOperation.Method.post,
                "bulk_id": None,
                "path": "/Users",
                "data": {"displayName": "John Doe"},
            },
            context={"scim": Context.RESOURCE_CREATION_REQUEST},
        )


def test_path_required_for_request_bulk_operations():
    """Test that path is required for request bulk operations.

    :rfc:`RFC7644` §3.7 <7644#section-3.7>: "path [...] REQUIRED in a request."
    """
    BulkOperation.model_validate(
        {
            "method": BulkOperation.Method.post,
            "bulk_id": "qwerty",
            "path": "/Users",
            "data": {"displayName": "John Doe"},
        },
        context={"scim": Context.RESOURCE_CREATION_REQUEST},
    )
    with pytest.raises(ValidationError):
        BulkOperation.model_validate(
            {
                "method": BulkOperation.Method.post,
                "bulk_id": "qwerty",
                "path": None,
                "data": {"displayName": "John Doe"},
            },
            context={"scim": Context.RESOURCE_CREATION_REQUEST},
        )
    BulkOperation.model_validate(
        {
            "method": BulkOperation.Method.post,
            "bulk_id": "qwerty",
            "path": None,
            "location": "https://example.com/users/2819c223-7f76-453a-919d-413861904646",
            "status": 201,
        },
        context={"scim": Context.RESOURCE_CREATION_RESPONSE},
    )


def test_data_required_for_post_put_patch_request_bulk_operations():
    """Test that data is required for POST, PUT, PATCH request bulk operations.

    :rfc:`RFC7644` §3.7 <7644#section-3.7>: "data  The resource data as it would appear for a single SCIM POST,
    PUT, or PATCH operation.  REQUIRED in a request when "method" is "POST", "PUT", or "PATCH"."
    """
    BulkOperation.model_validate(
        {
            "method": BulkOperation.Method.post,
            "bulk_id": "qwerty",
            "path": "/Users",
            "data": {"displayName": "John Doe"},
        },
        context={"scim": Context.RESOURCE_CREATION_REQUEST},
    )
    BulkOperation.model_validate(
        {
            "method": BulkOperation.Method.patch,
            "bulk_id": "qwerty",
            "path": "/Users/2819c223-7f76-453a-919d-413861904646",
            "data": {"displayName": "John Doe"},
        },
        context={"scim": Context.RESOURCE_PATCH_REQUEST},
    )
    BulkOperation.model_validate(
        {
            "method": BulkOperation.Method.put,
            "bulk_id": "qwerty",
            "path": "/Users/2819c223-7f76-453a-919d-413861904646",
            "data": {"displayName": "John Doe"},
        },
        context={"scim": Context.RESOURCE_REPLACEMENT_REQUEST},
    )
    BulkOperation.model_validate(
        {
            "method": BulkOperation.Method.delete,
            "path": "/Users/2819c223-7f76-453a-919d-413861904646",
        },
        context={"scim": Context.DEFAULT},
    )
    with pytest.raises(ValidationError):
        BulkOperation.model_validate(
            {
                "method": BulkOperation.Method.post,
                "bulk_id": "qwerty",
                "path": "/Users",
                "data": None,
            },
            context={"scim": Context.RESOURCE_CREATION_REQUEST},
        )
    with pytest.raises(ValidationError):
        BulkOperation.model_validate(
            {
                "method": BulkOperation.Method.patch,
                "bulk_id": "qwerty",
                "path": "/Users/2819c223-7f76-453a-919d-413861904646",
                "data": None,
            },
            context={"scim": Context.RESOURCE_PATCH_REQUEST},
        )
    with pytest.raises(ValidationError):
        BulkOperation.model_validate(
            {
                "method": BulkOperation.Method.put,
                "bulk_id": "qwerty",
                "path": "/Users/2819c223-7f76-453a-919d-413861904646",
                "data": None,
            },
            context={"scim": Context.RESOURCE_REPLACEMENT_REQUEST},
        )


def test_location_required_for_response_bulk_operations_except_post_errors():
    """Test that location is required for response bulk operations except POST errors.

    :rfc:`RFC7644` §3.7 <7644#section-3.7>: "location  The resource endpoint URL.  REQUIRED in a response,
    except in the event of a POST failure."
    """
    BulkOperation.model_validate(
        {
            "method": BulkOperation.Method.post,
            "bulk_id": "qwerty",
            "location": "https://example.com/users/2819c223-7f76-453a-919d-413861904646",
            "status": 201,
        },
        context={"scim": Context.RESOURCE_CREATION_RESPONSE},
    )
    BulkOperation.model_validate(
        {
            "method": BulkOperation.Method.post,
            "bulk_id": "qwerty",
            "location": None,
            "status": 400,
            "response": {
                "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
                "status": 400,
                "detail": "Error",
            },
        },
        context={"scim": Context.RESOURCE_CREATION_RESPONSE},
    )
    with pytest.raises(ValidationError):
        BulkOperation.model_validate(
            {
                "method": BulkOperation.Method.post,
                "bulk_id": "qwerty",
                "location": None,
                "status": 201,
            },
            context={"scim": Context.RESOURCE_CREATION_RESPONSE},
        )
    with pytest.raises(ValidationError):
        BulkOperation.model_validate(
            {
                "method": BulkOperation.Method.patch,
                "bulk_id": "qwerty",
                "location": None,
                "status": 400,
            },
            context={"scim": Context.RESOURCE_PATCH_RESPONSE},
        )


def test_method_required_for_bulk_operations():
    """Test that method is required for bulk operations."""
    with pytest.raises(ValidationError):
        BulkOperation.model_validate(
            {
                "bulk_id": "qwerty",
                "path": "/Users",
                "data": {"displayName": "John Doe"},
            },
            context={"scim": Context.RESOURCE_CREATION_REQUEST},
        )


def test_error_detail_required_in_response():
    BulkOperation.model_validate(
        {
            "method": BulkOperation.Method.post,
            "bulk_id": "qwerty",
            "status": 400,
            "response": {
                "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
                "status": 400,
                "detail": "Error",
            },
        },
        context={"scim": Context.RESOURCE_CREATION_RESPONSE},
    )
    with pytest.raises(ValidationError):
        BulkOperation.model_validate(
            {
                "method": BulkOperation.Method.post,
                "bulk_id": "qwerty",
                "status": 400,
            },
            context={"scim": Context.RESOURCE_CREATION_RESPONSE},
        )
    with pytest.raises(ValidationError):
        BulkOperation.model_validate(
            {
                "method": BulkOperation.Method.post,
                "bulk_id": "qwerty",
                "status": 400,
                "response": {
                    "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
                    "status": 400,
                },
            },
            context={"scim": Context.RESOURCE_CREATION_RESPONSE},
        )


def test_bulk_operation_with_group():
    group = Group(
        display_name="Group 1",
        members=[GroupMember(value="123", display="Test User")],
    )
    BulkOperation.model_validate(
        {
            "method": BulkOperation.Method.post,
            "bulk_id": "qwerty",
            "path": "/Groups",
            "data": group,
        },
        context={"scim": Context.RESOURCE_CREATION_REQUEST},
    )


def test_bulk_operation_with_patch_operation():
    patch = PatchOp[User](
        operations=[
            PatchOperation[User](
                op=PatchOperation.Op.add, path="nickName", value="Babs"
            )
        ]
    )
    BulkOperation.model_validate(
        {
            "method": BulkOperation.Method.patch,
            "bulk_id": "qwerty",
            "path": "/Users",
            "data": patch,
        },
        context={"scim": Context.RESOURCE_PATCH_REQUEST},
    )
