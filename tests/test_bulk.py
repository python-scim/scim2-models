import pytest
from pydantic import ValidationError

from scim2_models import Error
from scim2_models.base import Context
from scim2_models.messages.bulk import BulkOperation
from scim2_models.messages.bulk import BulkRequest
from scim2_models.messages.bulk import BulkResponse
from scim2_models.messages.patch_op import PatchOp
from scim2_models.messages.patch_op import PatchOperation
from scim2_models.resources.group import Group
from scim2_models.resources.group import GroupMember
from scim2_models.resources.user import User


def test_bulk_operation_delete():
    BulkOperation[User].model_validate(
        {
            "method": BulkOperation.Method.delete,
            "path": "/Users/2819c223-7f76-453a-919d-413861904646",
        }
    )


def test_operations_required_for_bulk_request():
    with pytest.raises(ValidationError):
        BulkRequest.model_validate(
            {"operations": None}, context={"scim": Context.BULK_REQUEST}
        )


def test_operations_required_for_bulk_response():
    with pytest.raises(ValidationError):
        BulkResponse.model_validate(
            {"operations": None}, context={"scim": Context.BULK_REQUEST}
        )


def test_bulkId_required_for_post_bulk_operations():
    """Test that bulkId is required for POST bulk operations.

    :rfc:`RFC7644` §3.7 <7644#section-3.7>: "bulkId [is] REQUIRED when "method" is "POST"."
    """
    BulkOperation[User].model_validate(
        {
            "method": BulkOperation.Method.post,
            "bulkId": "qwerty",
            "path": "/Users",
            "data": User(user_name="John Doe"),
        },
        context={"scim": Context.RESOURCE_CREATION_REQUEST},
    )
    with pytest.raises(ValidationError):
        BulkOperation[User].model_validate(
            {
                "method": BulkOperation.Method.post,
                "bulkId": None,
                "path": "/Users",
                "data": User(user_name="John Doe"),
            },
            context={"scim": Context.RESOURCE_CREATION_REQUEST},
        )


def test_path_required_for_request_bulk_operations():
    """Test that path is required for request bulk operations.

    :rfc:`RFC7644` §3.7 <7644#section-3.7>: "path [...] REQUIRED in a request."
    """
    BulkOperation[User].model_validate(
        {
            "method": BulkOperation.Method.post,
            "bulkId": "qwerty",
            "path": "/Users",
            "data": User(user_name="John Doe"),
        },
        context={"scim": Context.RESOURCE_CREATION_REQUEST},
    )
    with pytest.raises(ValidationError):
        BulkOperation[User].model_validate(
            {
                "method": BulkOperation.Method.post,
                "bulkId": "qwerty",
                "path": None,
                "data": User(user_name="John Doe"),
            },
            context={"scim": Context.RESOURCE_CREATION_REQUEST},
        )
    BulkOperation[User].model_validate(
        {
            "method": BulkOperation.Method.post,
            "bulkId": "qwerty",
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
    BulkOperation[User].model_validate(
        {
            "method": BulkOperation.Method.post,
            "bulkId": "qwerty",
            "path": "/Users",
            "data": User(user_name="John Doe"),
        },
        context={"scim": Context.RESOURCE_CREATION_REQUEST},
    )
    BulkOperation[User].model_validate(
        {
            "method": BulkOperation.Method.patch,
            "bulkId": "qwerty",
            "path": "/Users/2819c223-7f76-453a-919d-413861904646",
            "data": User(user_name="John Doe"),
        },
        context={"scim": Context.RESOURCE_PATCH_REQUEST},
    )
    BulkOperation[User].model_validate(
        {
            "method": BulkOperation.Method.put,
            "bulkId": "qwerty",
            "path": "/Users/2819c223-7f76-453a-919d-413861904646",
            "data": User(user_name="John Doe"),
        },
        context={"scim": Context.RESOURCE_REPLACEMENT_REQUEST},
    )
    with pytest.raises(ValidationError):
        BulkOperation[User].model_validate(
            {
                "method": BulkOperation.Method.post,
                "bulkId": "qwerty",
                "path": "/Users",
                "data": None,
            },
            context={"scim": Context.RESOURCE_CREATION_REQUEST},
        )
    with pytest.raises(ValidationError):
        BulkOperation[User].model_validate(
            {
                "method": BulkOperation.Method.patch,
                "bulkId": "qwerty",
                "path": "/Users/2819c223-7f76-453a-919d-413861904646",
                "data": None,
            },
            context={"scim": Context.RESOURCE_PATCH_REQUEST},
        )
    with pytest.raises(ValidationError):
        BulkOperation[User].model_validate(
            {
                "method": BulkOperation.Method.put,
                "bulkId": "qwerty",
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
    BulkOperation[User].model_validate(
        {
            "method": BulkOperation.Method.post,
            "bulkId": "qwerty",
            "location": "https://example.com/users/2819c223-7f76-453a-919d-413861904646",
            "status": 201,
        },
        context={"scim": Context.RESOURCE_CREATION_RESPONSE},
    )
    BulkOperation[User].model_validate(
        {
            "method": BulkOperation.Method.post,
            "bulkId": "qwerty",
            "location": None,
            "status": 400,
            "response": Error(
                status=400,
            ),
        },
        context={"scim": Context.RESOURCE_CREATION_RESPONSE},
    )
    with pytest.raises(ValidationError):
        BulkOperation[User].model_validate(
            {
                "method": BulkOperation.Method.post,
                "bulkId": "qwerty",
                "location": None,
                "status": 201,
            },
            context={"scim": Context.RESOURCE_CREATION_RESPONSE},
        )
    with pytest.raises(ValidationError):
        BulkOperation[User].model_validate(
            {
                "method": BulkOperation.Method.patch,
                "bulkId": "qwerty",
                "location": None,
                "status": 400,
            },
            context={"scim": Context.RESOURCE_PATCH_RESPONSE},
        )


def test_method_required_for_bulk_operations():
    """Test that method is required for bulk operations."""
    with pytest.raises(ValidationError):
        BulkOperation[User].model_validate(
            {
                "bulkId": "qwerty",
                "path": "/Users",
                "data": User(user_name="John Doe"),
            },
            context={"scim": Context.RESOURCE_CREATION_REQUEST},
        )


def test_error_response_required_in_response():
    BulkOperation[User].model_validate(
        {
            "method": BulkOperation.Method.post,
            "bulkId": "qwerty",
            "status": 400,
            "response": Error(
                status=400,
            ),
        },
        context={"scim": Context.RESOURCE_CREATION_RESPONSE},
    )
    with pytest.raises(ValidationError):
        BulkOperation[User].model_validate(
            {
                "method": BulkOperation.Method.post,
                "bulkId": "qwerty",
                "status": 400,
            },
            context={"scim": Context.RESOURCE_CREATION_RESPONSE},
        )


def test_bulk_operation_with_group():
    group = Group(
        display_name="Group 1",
        members=[GroupMember(value="123", display="Test User")],
    )
    BulkOperation[Group].model_validate(
        {
            "method": BulkOperation.Method.post,
            "bulkId": "qwerty",
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
    BulkOperation[User].model_validate(
        {
            "method": BulkOperation.Method.patch,
            "bulkId": "qwerty",
            "path": "/Users",
            "data": patch,
        },
        context={"scim": Context.RESOURCE_PATCH_REQUEST},
    )


def test_bulk_request_with_multiple_resource_types():
    """A single bulk request can create both users and groups."""
    request = BulkRequest[User | Group].model_validate(
        {
            "operations": [
                {
                    "method": BulkOperation.Method.post,
                    "bulkId": "create-user",
                    "path": "/Users",
                    "data": {"userName": "bjensen"},
                },
                {
                    "method": BulkOperation.Method.post,
                    "bulkId": "create-group",
                    "path": "/Groups",
                    "data": {"displayName": "Tour Guides"},
                },
            ]
        },
        context={"scim": Context.BULK_REQUEST},
    )

    assert isinstance(request.operations[0].data, User)
    assert request.operations[0].data.user_name == "bjensen"
    assert isinstance(request.operations[1].data, Group)
    assert request.operations[1].data.display_name == "Tour Guides"


def test_bulk_response_with_multiple_resource_types():
    """A single bulk response can carry both user and group results."""
    response = BulkResponse[User | Group].model_validate(
        {
            "operations": [
                {
                    "method": BulkOperation.Method.post,
                    "bulkId": "create-user",
                    "location": "https://example.com/v2/Users/92b725cd-9465-4d2f-9d49-d0d8aabb54d1",
                    "status": 201,
                    "response": {
                        "id": "92b725cd-9465-4d2f-9d49-d0d8aabb54d1",
                        "userName": "bjensen",
                    },
                },
                {
                    "method": BulkOperation.Method.post,
                    "bulkId": "create-group",
                    "location": "https://example.com/v2/Groups/e9e30dba-f08f-4109-8486-d5c6a331660a",
                    "status": 201,
                    "response": {
                        "id": "e9e30dba-f08f-4109-8486-d5c6a331660a",
                        "displayName": "Tour Guides",
                        "members": [
                            {
                                "value": "92b725cd-9465-4d2f-9d49-d0d8aabb54d1",
                                "display": "bjensen",
                            }
                        ],
                    },
                },
            ]
        },
        context={"scim": Context.BULK_RESPONSE},
    )

    assert isinstance(response.operations[0].response, User)
    assert response.operations[0].response.user_name == "bjensen"
    assert isinstance(response.operations[1].response, Group)
    assert response.operations[1].response.display_name == "Tour Guides"
