"""Tests for SCIM exceptions."""

import pytest
from pydantic import BaseModel
from pydantic import HttpUrl
from pydantic import ValidationError
from pydantic import field_validator

from scim2_models import BulkResponse
from scim2_models import ConflictException
from scim2_models import Context
from scim2_models import EnterpriseUser
from scim2_models import Error
from scim2_models import ExpiredCursorException
from scim2_models import ForbiddenException
from scim2_models import Group
from scim2_models import InvalidCountException
from scim2_models import InvalidCursorException
from scim2_models import InvalidFilterException
from scim2_models import InvalidPathException
from scim2_models import InvalidSyntaxException
from scim2_models import InvalidValueException
from scim2_models import InvalidVersionException
from scim2_models import ListResponse
from scim2_models import MutabilityException
from scim2_models import NoTargetException
from scim2_models import NotFoundException
from scim2_models import NotImplementedException
from scim2_models import PatchOp
from scim2_models import PathNotFoundException
from scim2_models import PayloadTooLargeException
from scim2_models import PreconditionFailedException
from scim2_models import SCIMException
from scim2_models import SensitiveException
from scim2_models import TooManyException
from scim2_models import UnauthorizedException
from scim2_models import UniquenessException
from scim2_models import User


def test_base_exception_default_message():
    """SCIMException uses default message when no detail is provided."""
    exc = SCIMException()
    assert str(exc) == "A SCIM error occurred"
    assert exc.status == 400
    assert exc.scim_type == ""


def test_base_exception_custom_message():
    """SCIMException uses custom detail when provided."""
    exc = SCIMException(detail="Custom error message")
    assert str(exc) == "Custom error message"
    assert exc.detail == "Custom error message"


def test_to_error():
    """to_error() converts SCIMException to Error response object."""
    exc = SCIMException(detail="Test error")
    error = exc.to_error()
    assert isinstance(error, Error)
    assert error.status == 400
    assert error.scim_type is None
    assert error.detail == "Test error"


def test_as_pydantic_error():
    """as_pydantic_error() converts to PydanticCustomError."""
    exc = InvalidPathException(detail="Bad path", path="/invalid")
    pydantic_error = exc.as_pydantic_error()
    assert pydantic_error.type == "scim_invalidPath"
    assert "Bad path" in str(pydantic_error)


def test_context_attributes():
    """Extra keyword arguments are stored in context dict."""
    exc = InvalidPathException(detail="Error", path="/test", extra="data")
    assert exc.path == "/test"
    assert exc.context["extra"] == "data"


def test_invalid_filter_exception():
    """InvalidFilterException has correct status and scim_type."""
    exc = InvalidFilterException(filter="invalid()")
    assert exc.status == 400
    assert exc.scim_type == "invalidFilter"
    assert exc.filter == "invalid()"
    error = exc.to_error()
    assert error.scim_type == "invalidFilter"


def test_too_many_exception():
    """TooManyException has correct status and scim_type."""
    exc = TooManyException()
    assert exc.status == 400
    assert exc.scim_type == "tooMany"


def test_invalid_cursor_exception():
    """InvalidCursorException has correct status and scim_type."""
    exc = InvalidCursorException()
    assert exc.status == 400
    assert exc.scim_type == "invalidCursor"


def test_expired_cursor_exception():
    """ExpiredCursorException has correct status and scim_type."""
    exc = ExpiredCursorException()
    assert exc.status == 400
    assert exc.scim_type == "expiredCursor"


def test_invalid_count_exception():
    """InvalidCountException has correct status and scim_type."""
    exc = InvalidCountException()
    assert exc.status == 400
    assert exc.scim_type == "invalidCount"


def test_uniqueness_exception():
    """UniquenessException has status 409 and stores attribute/value."""
    exc = UniquenessException(attribute="userName", value="john")
    assert exc.status == 409
    assert exc.scim_type == "uniqueness"
    assert exc.attribute == "userName"
    assert exc.value == "john"


def test_mutability_exception():
    """MutabilityException stores attribute, mutability and operation."""
    exc = MutabilityException(
        attribute="id", mutability="readOnly", operation="replace"
    )
    assert exc.status == 400
    assert exc.scim_type == "mutability"
    assert exc.attribute == "id"
    assert exc.mutability == "readOnly"
    assert exc.operation == "replace"


def test_invalid_syntax_exception():
    """InvalidSyntaxException has correct status and scim_type."""
    exc = InvalidSyntaxException()
    assert exc.status == 400
    assert exc.scim_type == "invalidSyntax"


def test_invalid_path_exception():
    """InvalidPathException stores the invalid path."""
    exc = InvalidPathException(path="invalid..path")
    assert exc.status == 400
    assert exc.scim_type == "invalidPath"
    assert exc.path == "invalid..path"


def test_path_not_found_exception():
    """PathNotFoundException includes field name in message."""
    exc = PathNotFoundException(path="unknownField", field="unknownField")
    assert exc.status == 400
    assert exc.scim_type == "invalidPath"
    assert exc.path == "unknownField"
    assert exc.field == "unknownField"
    assert isinstance(exc, InvalidPathException)
    assert str(exc) == "Field not found: unknownField"


def test_path_not_found_exception_with_custom_detail():
    """PathNotFoundException uses custom detail when provided."""
    exc = PathNotFoundException(field="foo", detail="Custom message")
    assert str(exc) == "Custom message"


def test_path_not_found_exception_without_field():
    """PathNotFoundException uses default message when no field is provided."""
    exc = PathNotFoundException()
    assert str(exc) == "The specified path references a non-existent field"


def test_no_target_exception():
    """NoTargetException stores the path that yielded no target."""
    exc = NoTargetException(path="emails[type eq 'work']")
    assert exc.status == 400
    assert exc.scim_type == "noTarget"
    assert exc.path == "emails[type eq 'work']"


def test_invalid_value_exception():
    """InvalidValueException stores attribute and reason."""
    exc = InvalidValueException(attribute="active", reason="must be boolean")
    assert exc.status == 400
    assert exc.scim_type == "invalidValue"
    assert exc.attribute == "active"
    assert exc.reason == "must be boolean"


def test_invalid_version_exception():
    """InvalidVersionException has scim_type 'invalidVers'."""
    exc = InvalidVersionException()
    assert exc.status == 400
    assert exc.scim_type == "invalidVers"


def test_sensitive_exception():
    """SensitiveException has correct status and scim_type."""
    exc = SensitiveException()
    assert exc.status == 400
    assert exc.scim_type == "sensitive"


def test_exception_in_pydantic_validator():
    """SCIM exceptions can be raised in Pydantic validators via as_pydantic_error()."""

    class TestModel(BaseModel):
        value: str

        @field_validator("value")
        @classmethod
        def validate_value(cls, v: str) -> str:
            if v == "invalid":
                raise InvalidValueException(
                    detail="Value cannot be 'invalid'"
                ).as_pydantic_error()
            return v

    with pytest.raises(ValidationError) as exc_info:
        TestModel(value="invalid")

    errors = exc_info.value.errors()
    assert len(errors) == 1
    assert errors[0]["type"] == "scim_invalidValue"
    assert "Value cannot be 'invalid'" in errors[0]["msg"]

    assert TestModel(value="valid").value == "valid"


def test_from_validation_error_with_scim_error():
    """from_validation_error() preserves scim_type from SCIM exceptions."""

    class TestModel(BaseModel):
        value: str

        @field_validator("value")
        @classmethod
        def validate_value(cls, v: str) -> str:
            if v == "bad":
                raise NoTargetException(detail="No target found").as_pydantic_error()
            return v

    with pytest.raises(ValidationError) as exc_info:
        TestModel(value="bad")

    error = Error.from_validation_error(exc_info.value.errors()[0])
    assert error.status == 400
    assert error.scim_type == "noTarget"
    assert error.detail == "No target found"

    assert TestModel(value="good").value == "good"


def test_from_validation_error_with_standard_pydantic_error():
    """from_validation_error() maps a value not fitting its attribute type to invalidValue."""

    class TestModel(BaseModel):
        value: int

    with pytest.raises(ValidationError) as exc_info:
        TestModel(value="not_an_int")

    error = Error.from_validation_error(exc_info.value.errors()[0])
    assert error.status == 400
    assert error.scim_type == "invalidValue"
    assert "value" in error.detail


def test_from_validation_error_with_missing_field():
    """from_validation_error() maps missing required fields to invalidValue."""

    class TestModel(BaseModel):
        required_field: str

    with pytest.raises(ValidationError) as exc_info:
        TestModel()

    error = Error.from_validation_error(exc_info.value.errors()[0])
    assert error.status == 400
    assert error.scim_type == "invalidValue"
    assert "required_field" in error.detail


def test_from_validation_error_with_any_value_error_type():
    """from_validation_error() maps a value error it has no explicit rule for to invalidValue."""

    class TestModel(BaseModel):
        url: HttpUrl

    with pytest.raises(ValidationError) as exc_info:
        TestModel(url="not a url")

    error = Error.from_validation_error(exc_info.value.errors()[0])
    assert error.status == 400
    assert error.scim_type == "invalidValue"
    assert "url" in error.detail


@pytest.mark.parametrize(
    "payload",
    [
        {"schemas": [User.__schema__], "userName": "bjensen", "active": "maybe"},
        {"schemas": [User.__schema__], "userName": "bjensen", "name": "Barbara"},
        {
            "schemas": [User.__schema__],
            "userName": "bjensen",
            "emails": [{"value": "bjensen@example.com", "type": {"work": True}}],
        },
        {
            "schemas": [User.__schema__],
            "userName": "bjensen",
            "emails": [
                {"value": "a@example.com", "primary": True},
                {"value": "b@example.com", "primary": True},
            ],
        },
    ],
    ids=["boolean", "complex attribute", "enumeration", "primary"],
)
def test_from_validation_error_maps_values_to_invalid_value(payload):
    """A value that does not fit its attribute is invalidValue, per RFC7644 §3.12."""
    with pytest.raises(ValidationError) as exc_info:
        User.model_validate(payload, scim_ctx=Context.RESOURCE_CREATION_REQUEST)

    error = Error.from_validation_error(exc_info.value.errors()[0])
    assert error.scim_type == "invalidValue"


@pytest.mark.parametrize(
    "payload",
    [
        [],
        {"schemas": [User.__schema__], "userName": "bjensen", "unknown": "x"},
        {"schemas": ["urn:example:Unknown"], "userName": "bjensen"},
        {"schemas": [User.__schema__, "urn:example:Unknown"], "userName": "bjensen"},
    ],
    ids=["not an object", "unknown attribute", "base schema", "unknown extension"],
)
def test_from_validation_error_maps_structure_to_invalid_syntax(payload):
    """A payload not following the request schema is invalidSyntax, per RFC7644 §3.12."""
    with pytest.raises(ValidationError) as exc_info:
        User.model_validate(payload, scim_ctx=Context.RESOURCE_CREATION_REQUEST)

    error = Error.from_validation_error(exc_info.value.errors()[0])
    assert error.scim_type == "invalidSyntax"


def test_from_validation_error_maps_malformed_json_to_invalid_syntax():
    """A body that is not JSON is invalidSyntax."""
    with pytest.raises(ValidationError) as exc_info:
        User.model_validate_json("{", scim_ctx=Context.RESOURCE_CREATION_REQUEST)

    error = Error.from_validation_error(exc_info.value.errors()[0])
    assert error.scim_type == "invalidSyntax"


def test_from_validation_error_gives_no_keyword_to_response_errors():
    """RFC7644 §3.12 defines no keyword for what only a response can get wrong."""
    with pytest.raises(ValidationError) as exc_info:
        User.model_validate(
            {"schemas": [User.__schema__], "userName": "bjensen"},
            scim_ctx=Context.RESOURCE_QUERY_RESPONSE,
        )

    error = Error.from_validation_error(exc_info.value.errors()[0])
    assert error.status == 400
    assert error.scim_type is None


def test_from_validation_errors_with_validation_error():
    """from_validation_errors() accepts a ValidationError directly."""

    class TestModel(BaseModel):
        a: int
        b: int

    with pytest.raises(ValidationError) as exc_info:
        TestModel(a="x", b="y")

    errors = Error.from_validation_errors(exc_info.value)
    assert len(errors) == 2
    assert all(e.scim_type == "invalidValue" for e in errors)


def test_from_validation_errors_with_list():
    """from_validation_errors() accepts a list of error dicts."""

    class TestModel(BaseModel):
        a: int
        b: int

    with pytest.raises(ValidationError) as exc_info:
        TestModel(a="x", b="y")

    errors = Error.from_validation_errors(exc_info.value.errors())
    assert len(errors) == 2
    assert all(isinstance(e, Error) for e in errors)


def test_all_exceptions_inherit_from_scim_exception():
    """All SCIM exceptions inherit from SCIMException, not ValueError."""
    exceptions = [
        InvalidFilterException(),
        TooManyException(),
        UniquenessException(),
        MutabilityException(),
        InvalidSyntaxException(),
        InvalidPathException(),
        PathNotFoundException(),
        NoTargetException(),
        InvalidValueException(),
        InvalidVersionException(),
        SensitiveException(),
        InvalidCursorException(),
        ExpiredCursorException(),
        InvalidCountException(),
        UnauthorizedException(),
        ForbiddenException(),
        NotFoundException(),
        ConflictException(),
        PreconditionFailedException(),
        PayloadTooLargeException(),
        NotImplementedException(),
    ]
    for exc in exceptions:
        assert isinstance(exc, SCIMException)
        assert isinstance(exc, Exception)
        assert not isinstance(exc, ValueError)


def test_path_not_found_is_invalid_path():
    """PathNotFoundException is a subclass of InvalidPathException."""
    exc = PathNotFoundException()
    assert isinstance(exc, InvalidPathException)
    assert exc.scim_type == "invalidPath"


def test_from_error_invalid_filter():
    """from_error() creates InvalidFilterException from Error with scim_type invalidFilter."""
    error = Error(status=400, scim_type="invalidFilter", detail="Bad filter")
    exc = SCIMException.from_error(error)
    assert isinstance(exc, InvalidFilterException)
    assert exc.detail == "Bad filter"


def test_from_error_too_many():
    """from_error() creates TooManyException from Error with scim_type tooMany."""
    error = Error(status=400, scim_type="tooMany", detail="Too many results")
    exc = SCIMException.from_error(error)
    assert isinstance(exc, TooManyException)
    assert exc.detail == "Too many results"


def test_from_error_uniqueness():
    """from_error() creates UniquenessException from Error with scim_type uniqueness."""
    error = Error(status=409, scim_type="uniqueness", detail="Duplicate userName")
    exc = SCIMException.from_error(error)
    assert isinstance(exc, UniquenessException)
    assert exc.detail == "Duplicate userName"


def test_from_error_mutability():
    """from_error() creates MutabilityException from Error with scim_type mutability."""
    error = Error(status=400, scim_type="mutability", detail="Cannot modify id")
    exc = SCIMException.from_error(error)
    assert isinstance(exc, MutabilityException)
    assert exc.detail == "Cannot modify id"


def test_from_error_invalid_syntax():
    """from_error() creates InvalidSyntaxException from Error with scim_type invalidSyntax."""
    error = Error(status=400, scim_type="invalidSyntax", detail="Malformed JSON")
    exc = SCIMException.from_error(error)
    assert isinstance(exc, InvalidSyntaxException)
    assert exc.detail == "Malformed JSON"


def test_from_error_invalid_path():
    """from_error() creates InvalidPathException from Error with scim_type invalidPath."""
    error = Error(status=400, scim_type="invalidPath", detail="Bad path")
    exc = SCIMException.from_error(error)
    assert isinstance(exc, InvalidPathException)
    assert exc.detail == "Bad path"


def test_from_error_no_target():
    """from_error() creates NoTargetException from Error with scim_type noTarget."""
    error = Error(status=400, scim_type="noTarget", detail="No match")
    exc = SCIMException.from_error(error)
    assert isinstance(exc, NoTargetException)
    assert exc.detail == "No match"


def test_from_error_invalid_value():
    """from_error() creates InvalidValueException from Error with scim_type invalidValue."""
    error = Error(status=400, scim_type="invalidValue", detail="Missing required")
    exc = SCIMException.from_error(error)
    assert isinstance(exc, InvalidValueException)
    assert exc.detail == "Missing required"


def test_from_error_invalid_version():
    """from_error() creates InvalidVersionException from Error with scim_type invalidVers."""
    error = Error(status=400, scim_type="invalidVers", detail="Unsupported version")
    exc = SCIMException.from_error(error)
    assert isinstance(exc, InvalidVersionException)
    assert exc.detail == "Unsupported version"


def test_from_error_sensitive():
    """from_error() creates SensitiveException from Error with scim_type sensitive."""
    error = Error(status=400, scim_type="sensitive", detail="Sensitive data in URI")
    exc = SCIMException.from_error(error)
    assert isinstance(exc, SensitiveException)
    assert exc.detail == "Sensitive data in URI"


def test_from_error_invalid_cursor():
    """from_error() creates InvalidCursorException from Error with scim_type invalidCursor."""
    error = Error(status=400, scim_type="invalidCursor", detail="Bad cursor")
    exc = SCIMException.from_error(error)
    assert isinstance(exc, InvalidCursorException)
    assert exc.detail == "Bad cursor"


def test_from_error_expired_cursor():
    """from_error() creates ExpiredCursorException from Error with scim_type expiredCursor."""
    error = Error(status=400, scim_type="expiredCursor", detail="Cursor expired")
    exc = SCIMException.from_error(error)
    assert isinstance(exc, ExpiredCursorException)
    assert exc.detail == "Cursor expired"


def test_from_error_invalid_count():
    """from_error() creates InvalidCountException from Error with scim_type invalidCount."""
    error = Error(status=400, scim_type="invalidCount", detail="Bad count")
    exc = SCIMException.from_error(error)
    assert isinstance(exc, InvalidCountException)
    assert exc.detail == "Bad count"


def test_from_error_unknown_scim_type():
    """from_error() creates base SCIMException for unknown scim_type."""
    error = Error(status=400, scim_type="unknownType", detail="Unknown error")
    exc = SCIMException.from_error(error)
    assert type(exc) is SCIMException
    assert exc.detail == "Unknown error"


def test_from_error_no_scim_type():
    """from_error() creates base SCIMException when scim_type is None."""
    error = Error(status=500, detail="Internal error")
    exc = SCIMException.from_error(error)
    assert type(exc) is SCIMException
    assert exc.detail == "Internal error"


def test_from_error_no_detail():
    """from_error() uses default detail when Error has no detail."""
    error = Error(status=400, scim_type="invalidFilter")
    exc = SCIMException.from_error(error)
    assert isinstance(exc, InvalidFilterException)
    assert exc.detail == InvalidFilterException._default_detail


def test_from_error_type_error():
    """from_error() raises TypeError for non-Error input."""
    with pytest.raises(TypeError, match="Expected Error"):
        SCIMException.from_error("not an error")


def test_scim_ctx_default_none():
    """SCIMException has scim_ctx=None by default."""
    exc = SCIMException()
    assert exc.scim_ctx is None


def test_scim_ctx_set_directly():
    """SCIMException can have scim_ctx set directly."""
    exc = SCIMException(detail="Test error", scim_ctx=Context.RESOURCE_CREATION_REQUEST)
    assert exc.scim_ctx == Context.RESOURCE_CREATION_REQUEST
    assert exc.detail == "Test error"


def test_scim_ctx_on_subclass():
    """Exception subclasses can have scim_ctx set."""
    exc = InvalidValueException(
        detail="Invalid input",
        attribute="userName",
        scim_ctx=Context.RESOURCE_CREATION_REQUEST,
    )
    assert exc.scim_ctx == Context.RESOURCE_CREATION_REQUEST
    assert exc.attribute == "userName"


def test_from_error_with_scim_ctx():
    """from_error() passes scim_ctx to the created exception."""
    error = Error(status=400, scim_type="invalidValue", detail="Missing required")
    exc = SCIMException.from_error(error, scim_ctx=Context.RESOURCE_CREATION_RESPONSE)
    assert isinstance(exc, InvalidValueException)
    assert exc.scim_ctx == Context.RESOURCE_CREATION_RESPONSE
    assert exc.detail == "Missing required"


def test_from_error_without_scim_ctx():
    """from_error() creates exception with scim_ctx=None when not provided."""
    error = Error(status=400, scim_type="invalidFilter", detail="Bad filter")
    exc = SCIMException.from_error(error)
    assert isinstance(exc, InvalidFilterException)
    assert exc.scim_ctx is None


def test_from_error_keeps_the_error_object():
    """to_error() gives back the very object from_error() was built from."""
    error = Error(status=404, detail="Resource unknown not found")
    exc = SCIMException.from_error(error)
    assert exc.to_error() is error


def test_from_error_keeps_what_no_exception_class_describes():
    """from_error() keeps a status and a scimType that match no exception class."""
    error = Error(status=429, scim_type="tooManyRequests", detail="Slow down")
    exc = SCIMException.from_error(error)
    assert exc.status == 429
    assert exc.scim_type == "tooManyRequests"


def test_from_error_without_status():
    """from_error() keeps the class status when the Error object carries none."""
    error = Error(scim_type="uniqueness", detail="Duplicate userName")
    exc = SCIMException.from_error(error)
    assert exc.status == 409


ENTERPRISE_USER_SCHEMA = "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"
USER_SCHEMA = "urn:ietf:params:scim:schemas:core:2.0:User"


def first_error_detail(model, payload, scim_ctx):
    """Return the detail of the first SCIM error a payload raises."""
    with pytest.raises(ValidationError) as exc_info:
        model.model_validate(payload, scim_ctx=scim_ctx)
    return Error.from_validation_errors(exc_info.value)[0].detail


@pytest.mark.parametrize(
    "model,payload,scim_ctx,path",
    [
        (
            User,
            {"userName": "bjensen", "name": {"givenName": 3}},
            Context.RESOURCE_CREATION_REQUEST,
            "name.givenName",
        ),
        (
            User,
            {
                "userName": "bjensen",
                "emails": [{"value": "a@example.com"}, {"value": 3}],
            },
            Context.RESOURCE_CREATION_REQUEST,
            "emails[1].value",
        ),
        (
            User[EnterpriseUser],
            {"userName": "bjensen", ENTERPRISE_USER_SCHEMA: {"manager": {"value": 3}}},
            Context.RESOURCE_CREATION_REQUEST,
            f"{ENTERPRISE_USER_SCHEMA}:manager.value",
        ),
        (
            ListResponse[User | Group],
            {"Resources": [{"schemas": [USER_SCHEMA], "id": "1", "userName": 3}]},
            Context.RESOURCE_QUERY_RESPONSE,
            "Resources[0].userName",
        ),
        (
            ListResponse[User[EnterpriseUser] | Group],
            {
                "Resources": [
                    {
                        "schemas": [USER_SCHEMA, ENTERPRISE_USER_SCHEMA],
                        "id": "1",
                        "userName": "bjensen",
                        ENTERPRISE_USER_SCHEMA: {"employeeNumber": 3},
                    }
                ]
            },
            Context.RESOURCE_QUERY_RESPONSE,
            f"Resources[0].{ENTERPRISE_USER_SCHEMA}:employeeNumber",
        ),
        (
            BulkResponse[User],
            {
                "Operations": [
                    {
                        "method": "POST",
                        "status": 201,
                        "location": "https://example.com/v2/Users/1",
                        "response": {"schemas": [USER_SCHEMA], "userName": 3},
                    }
                ]
            },
            Context.BULK_RESPONSE,
            "Operations[0].response.userName",
        ),
    ],
)
def test_the_detail_of_an_error_locates_it_with_an_attribute_path(
    model, payload, scim_ctx, path
):
    """Sub-attributes follow a dot, extension attributes their schema URN and a colon, values their index.

    The members of the unions pydantic tried are not part of the payload, and
    are left out.
    """
    assert first_error_detail(model, payload, scim_ctx) == (
        f"Input should be a valid string: {path}"
    )


def test_the_detail_of_an_error_at_the_root_of_a_payload_carries_no_path():
    """An error on the payload itself has no attribute to point at."""
    with pytest.raises(ValidationError) as exc_info:
        User.model_validate("not an object", scim_ctx=Context.RESOURCE_CREATION_REQUEST)
    error = Error.from_validation_errors(exc_info.value)[0]
    assert error.detail == "Input should be a valid dictionary or instance of User"


@pytest.mark.parametrize("key", ["Operations", "operations", "OPERATIONS"])
def test_message_attributes_keep_their_case_insensitive_names(key):
    """The Operations of a message are named as RFC 7644 spells them, and read whatever their case."""
    patch = PatchOp[User].model_validate(
        {key: [{"op": "replace", "path": "nickName", "value": "Babs"}]},
        scim_ctx=Context.RESOURCE_PATCH_REQUEST,
    )
    assert patch.operations[0].value == "Babs"
    assert "Operations" in patch.model_dump(scim_ctx=Context.RESOURCE_PATCH_REQUEST)


STATUS_EXCEPTIONS = [
    (UnauthorizedException, 401),
    (ForbiddenException, 403),
    (NotFoundException, 404),
    (ConflictException, 409),
    (PreconditionFailedException, 412),
    (PayloadTooLargeException, 413),
    (NotImplementedException, 501),
]


@pytest.mark.parametrize("exception_class,status", STATUS_EXCEPTIONS)
def test_status_exception_converts_to_an_error_without_scim_type(
    exception_class, status
):
    """An exception for a status of RFC 7644 Table 8 gives an Error with that status and no scimType."""
    error = exception_class(detail="Something went wrong").to_error()
    assert error.status == status
    assert error.scim_type is None
    assert error.detail == "Something went wrong"


@pytest.mark.parametrize("exception_class,status", STATUS_EXCEPTIONS)
def test_status_exception_has_a_default_detail(exception_class, status):
    """An exception for a status of RFC 7644 Table 8 has a default detail."""
    assert exception_class().detail == exception_class._default_detail


@pytest.mark.parametrize("exception_class,status", STATUS_EXCEPTIONS)
def test_from_error_picks_the_exception_from_the_status(exception_class, status):
    """from_error() picks the exception from the status of an Error without scimType."""
    error = Error(status=status, detail="Something went wrong")
    exc = SCIMException.from_error(error)
    assert type(exc) is exception_class
    assert exc.status == status
    assert exc.to_error() is error


def test_uniqueness_is_a_conflict():
    """UniquenessException is a subclass of ConflictException."""
    exc = UniquenessException()
    assert isinstance(exc, ConflictException)
    assert exc.status == 409
    assert exc.scim_type == "uniqueness"


def test_from_error_conflict_without_scim_type_is_not_a_uniqueness_error():
    """A 409 without scimType gives a ConflictException, as the conflict may be on a version."""
    error = Error(status=409, detail="Version mismatch")
    exc = SCIMException.from_error(error)
    assert type(exc) is ConflictException


def test_from_error_scim_type_wins_over_the_status():
    """from_error() picks the exception from the scimType when the status names another one."""
    error = Error(status=404, scim_type="invalidFilter", detail="Bad filter")
    exc = SCIMException.from_error(error)
    assert isinstance(exc, InvalidFilterException)
    assert exc.status == 404


def test_from_error_unknown_scim_type_falls_back_to_the_status():
    """from_error() picks the exception from the status when the scimType is vendor specific."""
    error = Error(status=404, scim_type="vendorNotFound", detail="Not here")
    exc = SCIMException.from_error(error)
    assert type(exc) is NotFoundException
    assert exc.scim_type == "vendorNotFound"
