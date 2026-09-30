import pytest
from pydantic import ValidationError

from scim2_models import Error
from scim2_models import ScimProvider
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
    """A bulk request without operations describes no work at all."""
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
            "data": PatchOp[User](
                operations=[
                    PatchOperation[User](
                        op=PatchOperation.Op.add, path="nickName", value="Babs"
                    )
                ]
            ),
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
    with pytest.raises(ValidationError, match="data is required"):
        BulkOperation[User].model_validate(
            {
                "method": BulkOperation.Method.post,
                "bulkId": "qwerty",
                "path": "/Users",
                "data": None,
            },
            context={"scim": Context.BULK_REQUEST},
        )
    with pytest.raises(ValidationError, match="data is required"):
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
    """An operation that failed must say why, or the caller only learns that something went wrong."""
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
    """A bulk job carries any resource type, so an operation must not be tied to User."""
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
    """A PATCH operation carries a patch rather than a resource, which the data union must accept."""
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


def test_patch_operation_data_must_be_a_patch():
    """A PATCH carries a PatchOp, so a full resource cannot slip read-only attributes through."""
    with pytest.raises(ValidationError) as exc_info:
        BulkOperation[User].model_validate(
            {
                "method": BulkOperation.Method.patch,
                "path": "/Users/2819c223-7f76-453a-919d-413861904646",
                "data": {
                    "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
                    "id": "evil",
                    "userName": "bjensen",
                    "groups": [{"value": "admins"}],
                },
            },
            scim_ctx=Context.BULK_REQUEST,
        )
    assert {error["loc"] for error in exc_info.value.errors()} == {
        ("data", "id"),
        ("data", "userName"),
        ("data", "groups"),
    }


@pytest.mark.parametrize(
    "method,path",
    [
        (BulkOperation.Method.post, "/Users"),
        (BulkOperation.Method.put, "/Users/2819c223-7f76-453a-919d-413861904646"),
    ],
)
def test_post_and_put_operation_data_must_be_a_resource(method, path):
    """A POST or a PUT carries a resource, not a PatchOp."""
    with pytest.raises(ValidationError) as exc_info:
        BulkOperation[User].model_validate(
            {
                "method": method,
                "bulkId": "qwerty",
                "path": path,
                "data": {
                    "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
                    "Operations": [{"op": "add", "path": "userName", "value": "x"}],
                },
            },
            scim_ctx=Context.BULK_REQUEST,
        )
    assert [error["loc"] for error in exc_info.value.errors()] == [
        ("data", "Operations")
    ]


def test_operation_data_errors_come_from_the_payload_of_the_method():
    """An invalid PATCH data reports the errors of the patch alone."""
    with pytest.raises(ValidationError) as exc_info:
        BulkOperation[User].model_validate(
            {
                "method": BulkOperation.Method.patch,
                "path": "/Users/2819c223-7f76-453a-919d-413861904646",
                "data": {
                    "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
                    "Operations": [{"op": "frobnicate", "path": "userName"}],
                },
            },
            scim_ctx=Context.BULK_REQUEST,
        )
    assert [error["loc"] for error in exc_info.value.errors()] == [
        ("data", "Operations", 0, "op")
    ]


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


def test_a_subclass_of_a_parameterized_operation_reads_its_data():
    """A class deriving from BulkOperation[User] validates its data as a User."""

    class UserOperation(BulkOperation[User]):
        pass

    operation = UserOperation.model_validate(
        {
            "method": BulkOperation.Method.post,
            "bulkId": "qwerty",
            "path": "/Users",
            "data": {"userName": "bjensen"},
        },
        scim_ctx=Context.BULK_REQUEST,
    )
    assert operation.data.user_name == "bjensen"


GROUP_PATH = "/Groups/e9e30dba-f08f-4109-8486-d5c6a331660a"
PATCH_DISPLAY_NAME = {
    "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
    "Operations": [{"op": "replace", "path": "displayName", "value": "Tour Guides"}],
}


def bulk_payload(*operations, **envelope):
    """Build a raw bulk request carrying the given operations."""
    return {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:BulkRequest"],
        **envelope,
        "Operations": list(operations),
    }


def test_an_invalid_operation_fails_alone():
    """RFC 7644 §3.7.3: an operation the service provider cannot perform is reported in its own result."""
    request = BulkRequest[User].model_validate(
        bulk_payload(
            {
                "method": "POST",
                "bulkId": "invalid",
                "path": "/Users",
                "data": {"userName": 42},
            },
            {
                "method": "POST",
                "bulkId": "valid",
                "path": "/Users",
                "data": {"userName": "bjensen"},
            },
            failOnErrors=1,
        ),
        scim_ctx=Context.BULK_REQUEST,
    )

    invalid, valid = request.operations
    assert request.fail_on_errors == 1
    assert invalid.method == BulkOperation.Method.post
    assert invalid.bulk_id == "invalid"
    assert invalid.path == "/Users"
    assert invalid.data is None
    assert invalid.status == 400
    assert invalid.response.scim_type == "invalidValue"
    assert valid.data.user_name == "bjensen"
    assert valid.response is None


def test_an_invalid_operation_keeps_what_its_result_can_carry():
    """Only the values a result can hold are kept from an operation that cannot be read."""
    request = BulkRequest[User].model_validate(
        bulk_payload(
            {"METHOD": "FETCH", "BULKID": 42, "PATH": ["/Users"]},
            "not an operation",
        ),
        scim_ctx=Context.BULK_REQUEST,
    )

    unreadable, not_an_object = request.operations
    assert (unreadable.method, unreadable.bulk_id, unreadable.path) == (
        None,
        None,
        None,
    )
    assert unreadable.status == 400
    assert not_an_object.status == 400
    assert isinstance(not_an_object.response, Error)


def test_attribute_names_of_an_invalid_operation_are_case_insensitive():
    """The method, bulkId and path of an invalid operation are read whatever their case."""
    request = BulkRequest[User].model_validate(
        bulk_payload(
            {"METHOD": "POST", "BulkId": "invalid", "Path": "/Users", "data": {}}
        ),
        scim_ctx=Context.BULK_REQUEST,
    )

    (invalid,) = request.operations
    assert (invalid.method, invalid.bulk_id, invalid.path) == (
        BulkOperation.Method.post,
        "invalid",
        "/Users",
    )


@pytest.mark.parametrize(
    "envelope",
    [
        {"Operations": "not a list"},
        {"failOnErrors": "not a number", "Operations": []},
    ],
)
def test_an_invalid_envelope_fails_the_whole_request(envelope):
    """The operations fail one by one, but a request whose envelope is invalid fails whole."""
    with pytest.raises(ValidationError):
        BulkRequest[User].model_validate(envelope, scim_ctx=Context.BULK_REQUEST)


def test_an_invalid_operation_fails_the_request_outside_a_bulk_request_context():
    """Only a bulk request received by a service provider reports invalid operations one by one."""
    with pytest.raises(ValidationError):
        BulkRequest[User].model_validate(
            bulk_payload({"method": "POST", "path": "/Users", "data": {"userName": 42}})
        )


def test_the_provider_picks_the_model_from_the_path():
    """Under a provider, an operation is read as the resource type its endpoint serves."""
    provider = ScimProvider(models=[User, Group])
    payload = bulk_payload(
        {"method": "PATCH", "path": GROUP_PATH, "data": PATCH_DISPLAY_NAME},
        {"method": "DELETE", "path": GROUP_PATH},
    )

    with provider:
        request = BulkRequest[User | Group].model_validate(
            payload, scim_ctx=Context.BULK_REQUEST
        )

    patch, delete = request.operations
    assert isinstance(patch.data, PatchOp[Group])
    assert isinstance(delete, BulkOperation[Group])


def test_a_provider_given_to_the_validation_picks_the_model_from_the_path():
    """The provider can be given to the validation rather than opened as a block."""
    request = BulkRequest[User | Group].model_validate(
        bulk_payload(
            {"method": "PATCH", "path": GROUP_PATH, "data": PATCH_DISPLAY_NAME}
        ),
        scim_ctx=Context.BULK_REQUEST,
        scim_provider=ScimProvider(models=[User, Group]),
    )

    (patch,) = request.operations
    assert isinstance(patch.data, PatchOp[Group])


def test_without_provider_the_model_is_picked_from_the_data():
    """Without a provider, nothing tells which resource type an endpoint serves."""
    request = BulkRequest[User | Group].model_validate(
        bulk_payload(
            {"method": "PATCH", "path": GROUP_PATH, "data": PATCH_DISPLAY_NAME}
        ),
        scim_ctx=Context.BULK_REQUEST,
    )

    (patch,) = request.operations
    assert isinstance(patch.data, PatchOp[User])


def test_an_operation_on_an_unknown_endpoint_fails_alone():
    """Under a provider, an endpoint no resource type is served at fails the operation with invalidPath."""
    request = BulkRequest[User].model_validate(
        bulk_payload(
            {"method": "DELETE", "path": "/Pets/1"},
            {"method": "DELETE", "path": "/Users/1"},
        ),
        scim_ctx=Context.BULK_REQUEST,
        scim_provider=ScimProvider(models=[User]),
    )

    unknown, known = request.operations
    assert unknown.status == 400
    assert unknown.response.scim_type == "invalidPath"
    assert unknown.response.detail == "No resource type is served at /Pets"
    assert known.status is None


def test_an_endpoint_whose_model_the_request_does_not_declare_is_a_programming_error():
    """The type parameter of the request must cover every resource type the provider serves."""
    with pytest.raises(TypeError, match="Group"):
        BulkRequest[User].model_validate(
            bulk_payload({"method": "DELETE", "path": GROUP_PATH}),
            scim_ctx=Context.BULK_REQUEST,
            scim_provider=ScimProvider(models=[User, Group]),
        )


@pytest.mark.parametrize(
    "path,endpoint,resource_id",
    [
        ("/Users", "/Users", None),
        ("/Users/2819c223", "/Users", "2819c223"),
        ("Users/2819c223", "/Users", "2819c223"),
        ("/Users/", "/Users", None),
        (None, None, None),
    ],
)
def test_the_target_of_an_operation_is_read_from_its_path(path, endpoint, resource_id):
    """The endpoint and the resource identifier come from the path, a creation having no identifier."""
    operation = BulkOperation[User](path=path)
    assert operation.endpoint == endpoint
    assert operation.resource_id == resource_id
