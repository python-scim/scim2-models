import pytest
from pydantic import ValidationError

from scim2_models import Error
from scim2_models.base import Context
from scim2_models.messages.bulk import BulkOperation
from scim2_models.messages.bulk import BulkRequest
from scim2_models.messages.bulk import BulkResponse
from scim2_models.messages.patch_op import PatchOp
from scim2_models.messages.patch_op import PatchOperation
from scim2_models.resources.enterprise_user import EnterpriseUser
from scim2_models.resources.group import Group
from scim2_models.resources.group import GroupMember
from scim2_models.resources.user import User


def test_bulk_operation_delete():
    """A DELETE names its target with a path and carries no payload."""
    operation = BulkOperation[User].model_validate(
        {
            "method": BulkOperation.Method.delete,
            "path": "/Users/2819c223-7f76-453a-919d-413861904646",
        },
        scim_ctx=Context.BULK_REQUEST,
    )
    assert operation.method == BulkOperation.Method.delete
    assert operation.data is None


def test_operations_required_for_bulk_request():
    with pytest.raises(ValidationError):
        BulkRequest[User].model_validate(
            {"operations": None}, context={"scim": Context.BULK_REQUEST}
        )


def test_operations_required_for_bulk_response():
    """Required.true is not consulted in a response context, so a validator of its own states it."""
    with pytest.raises(ValidationError):
        BulkResponse[User].model_validate(
            {"operations": None}, scim_ctx=Context.BULK_RESPONSE
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
        context={"scim": Context.BULK_REQUEST},
    )
    with pytest.raises(ValidationError):
        BulkOperation[User].model_validate(
            {
                "method": BulkOperation.Method.post,
                "bulkId": None,
                "path": "/Users",
                "data": User(user_name="John Doe"),
            },
            context={"scim": Context.BULK_REQUEST},
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
        context={"scim": Context.BULK_REQUEST},
    )
    with pytest.raises(ValidationError):
        BulkOperation[User].model_validate(
            {
                "method": BulkOperation.Method.post,
                "bulkId": "qwerty",
                "path": None,
                "data": User(user_name="John Doe"),
            },
            context={"scim": Context.BULK_REQUEST},
        )
    BulkOperation[User].model_validate(
        {
            "method": BulkOperation.Method.post,
            "bulkId": "qwerty",
            "path": None,
            "location": "https://example.com/users/2819c223-7f76-453a-919d-413861904646",
            "status": 201,
        },
        context={"scim": Context.BULK_RESPONSE},
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
        context={"scim": Context.BULK_REQUEST},
    )
    BulkOperation[User].model_validate(
        {
            "method": BulkOperation.Method.patch,
            "bulkId": "qwerty",
            "path": "/Users/2819c223-7f76-453a-919d-413861904646",
            "data": User(user_name="John Doe"),
        },
        context={"scim": Context.BULK_REQUEST},
    )
    BulkOperation[User].model_validate(
        {
            "method": BulkOperation.Method.put,
            "bulkId": "qwerty",
            "path": "/Users/2819c223-7f76-453a-919d-413861904646",
            "data": User(user_name="John Doe"),
        },
        context={"scim": Context.BULK_REQUEST},
    )
    with pytest.raises(ValidationError):
        BulkOperation[User].model_validate(
            {
                "method": BulkOperation.Method.post,
                "bulkId": "qwerty",
                "path": "/Users",
                "data": None,
            },
            context={"scim": Context.BULK_REQUEST},
        )
    with pytest.raises(ValidationError):
        BulkOperation[User].model_validate(
            {
                "method": BulkOperation.Method.patch,
                "bulkId": "qwerty",
                "path": "/Users/2819c223-7f76-453a-919d-413861904646",
                "data": None,
            },
            context={"scim": Context.BULK_REQUEST},
        )
    with pytest.raises(ValidationError):
        BulkOperation[User].model_validate(
            {
                "method": BulkOperation.Method.put,
                "bulkId": "qwerty",
                "path": "/Users/2819c223-7f76-453a-919d-413861904646",
                "data": None,
            },
            context={"scim": Context.BULK_REQUEST},
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
        context={"scim": Context.BULK_RESPONSE},
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
        context={"scim": Context.BULK_RESPONSE},
    )
    with pytest.raises(ValidationError):
        BulkOperation[User].model_validate(
            {
                "method": BulkOperation.Method.post,
                "bulkId": "qwerty",
                "location": None,
                "status": 201,
            },
            context={"scim": Context.BULK_RESPONSE},
        )
    with pytest.raises(ValidationError):
        BulkOperation[User].model_validate(
            {
                "method": BulkOperation.Method.patch,
                "bulkId": "qwerty",
                "location": None,
                "status": 400,
            },
            context={"scim": Context.BULK_RESPONSE},
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
            context={"scim": Context.BULK_REQUEST},
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
        context={"scim": Context.BULK_RESPONSE},
    )
    with pytest.raises(ValidationError):
        BulkOperation[User].model_validate(
            {
                "method": BulkOperation.Method.post,
                "bulkId": "qwerty",
                "status": 400,
            },
            context={"scim": Context.BULK_RESPONSE},
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
        context={"scim": Context.BULK_REQUEST},
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
        context={"scim": Context.BULK_REQUEST},
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


def test_patch_operation_data_answers_to_the_patch_request_rules():
    """A bulk job must not be a way to send the patches a PATCH endpoint refuses."""

    def patch(operations):
        return {
            "method": BulkOperation.Method.patch,
            "bulkId": "qwerty",
            "path": "/Users/2819c223-7f76-453a-919d-413861904646",
            "data": {
                "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
                "Operations": operations,
            },
        }

    with pytest.raises(ValidationError, match="value is required for add operations"):
        BulkOperation[User].model_validate(
            patch([{"op": "add", "path": "displayName"}]),
            scim_ctx=Context.BULK_REQUEST,
        )

    with pytest.raises(ValidationError, match="Remove operation requires a path"):
        BulkOperation[User].model_validate(
            patch([{"op": "remove"}]), scim_ctx=Context.BULK_REQUEST
        )

    with pytest.raises(ValidationError, match="a remove operation carries no value"):
        BulkOperation[User].model_validate(
            patch([{"op": "remove", "path": "displayName", "value": "x"}]),
            scim_ctx=Context.BULK_REQUEST,
        )

    operation = BulkOperation[User].model_validate(
        patch([{"op": "add", "path": "displayName", "value": "Jane"}]),
        scim_ctx=Context.BULK_REQUEST,
    )
    assert isinstance(operation.data, PatchOp)


def test_patch_operation_data_reports_missing_operations_as_a_patch_would():
    """PatchOp reports a clearer error than the generic check the bulk envelope would apply."""
    with pytest.raises(ValidationError, match="operations attribute is required"):
        BulkOperation[User].model_validate(
            {
                "method": BulkOperation.Method.patch,
                "bulkId": "qwerty",
                "path": "/Users/2819c223-7f76-453a-919d-413861904646",
                "data": {"schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"]},
            },
            scim_ctx=Context.BULK_REQUEST,
        )


def test_post_operation_data_answers_to_the_creation_request_rules():
    """A POST data is the payload of a single creation request, so it needs what a creation needs."""
    with pytest.raises(ValidationError):
        BulkOperation[User].model_validate(
            {
                "method": BulkOperation.Method.post,
                "bulkId": "qwerty",
                "path": "/Users",
                "data": {"schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"]},
            },
            scim_ctx=Context.BULK_REQUEST,
        )

    operation = BulkOperation[User].model_validate(
        {
            "method": BulkOperation.Method.post,
            "bulkId": "qwerty",
            "path": "/Users",
            "data": {
                "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
                "userName": "bjensen",
            },
        },
        scim_ctx=Context.BULK_REQUEST,
    )
    assert operation.data.user_name == "bjensen"


def test_operation_data_keeps_the_bulk_context_when_no_single_request_matches():
    """Neither a DELETE nor an unreadable method names a single request to borrow the rules from."""
    operation = BulkOperation[User].model_validate(
        {
            "method": BulkOperation.Method.delete,
            "path": "/Users/2819c223-7f76-453a-919d-413861904646",
            "data": {
                "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
                "userName": "bjensen",
            },
        },
        scim_ctx=Context.BULK_REQUEST,
    )
    assert operation.data.user_name == "bjensen"


def test_operation_envelope_keeps_the_bulk_context_after_its_data():
    """The data switches the context, and the envelope still needs the bulk rules afterwards."""
    with pytest.raises(ValidationError, match="Field 'method' is required"):
        BulkOperation[User].model_validate(
            {
                "bulkId": "qwerty",
                "path": "/Users",
                "data": {
                    "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
                    "userName": "bjensen",
                },
            },
            scim_ctx=Context.BULK_REQUEST,
        )


def test_reference_to_a_resource_being_created_stays_tolerated_in_operation_data():
    """A creation request requires a resolved reference, but RFC7644 §3.7.2 allows a placeholder inside a bulk job."""

    def operation(manager):
        return {
            "method": BulkOperation.Method.post,
            "bulkId": "qwerty",
            "path": "/Users",
            "data": {
                "schemas": [
                    "urn:ietf:params:scim:schemas:core:2.0:User",
                    "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
                ],
                "userName": "bjensen",
                "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
                    "manager": manager
                },
            },
        }

    BulkOperation[User[EnterpriseUser]].model_validate(
        operation({"value": "bulkId:ytrewq"}), scim_ctx=Context.BULK_REQUEST
    )

    with pytest.raises(ValidationError):
        BulkOperation[User[EnterpriseUser]].model_validate(
            operation({"value": "2819c223-7f76-453a-919d-413861904646"}),
            scim_ctx=Context.BULK_REQUEST,
        )

    with pytest.raises(ValidationError):
        BulkOperation[User[EnterpriseUser]].model_validate(
            operation({"value": "bulkId:ytrewq"}),
            scim_ctx=Context.RESOURCE_CREATION_REQUEST,
        )


def test_bulk_models_require_a_type_parameter():
    """A bare model falls back on the type variable bound and blames a valid attribute for the missing parameter."""
    for model in (BulkRequest, BulkResponse, BulkOperation):
        with pytest.raises(TypeError, match="requires a type parameter"):
            model()


def test_bulk_rules_do_not_apply_outside_a_bulk_context():
    """A payload validated under another context is not part of a bulk job, and the bulk rules would reject it wrongly."""
    operation = BulkOperation[User].model_validate(
        {
            "method": BulkOperation.Method.put,
            "location": "https://example.com/v2/Users/2819c223",
            "status": "200",
        },
        scim_ctx=Context.SEARCH_REQUEST,
    )
    assert operation.path is None
