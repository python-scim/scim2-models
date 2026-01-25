"""Tests for SCIM exceptions."""

import pytest
from pydantic import BaseModel
from pydantic import HttpUrl
from pydantic import ValidationError
from pydantic import field_validator

from scim2_models import Error
from scim2_models import InvalidFilterException
from scim2_models import InvalidPathException
from scim2_models import InvalidSyntaxException
from scim2_models import InvalidValueException
from scim2_models import InvalidVersionException
from scim2_models import MutabilityException
from scim2_models import NoTargetException
from scim2_models import PathNotFoundException
from scim2_models import SCIMException
from scim2_models import SensitiveException
from scim2_models import TooManyException
from scim2_models import UniquenessException


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
    """from_validation_error() maps Pydantic type errors to invalidSyntax."""

    class TestModel(BaseModel):
        value: int

    with pytest.raises(ValidationError) as exc_info:
        TestModel(value="not_an_int")

    error = Error.from_validation_error(exc_info.value.errors()[0])
    assert error.status == 400
    assert error.scim_type == "invalidSyntax"
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


def test_from_validation_error_with_unmapped_error_type():
    """from_validation_error() returns scim_type=None for unmapped error types."""

    class TestModel(BaseModel):
        url: HttpUrl

    with pytest.raises(ValidationError) as exc_info:
        TestModel(url="not a url")

    error = Error.from_validation_error(exc_info.value.errors()[0])
    assert error.status == 400
    assert error.scim_type is None
    assert "url" in error.detail


def test_from_validation_errors_with_validation_error():
    """from_validation_errors() accepts a ValidationError directly."""

    class TestModel(BaseModel):
        a: int
        b: int

    with pytest.raises(ValidationError) as exc_info:
        TestModel(a="x", b="y")

    errors = Error.from_validation_errors(exc_info.value)
    assert len(errors) == 2
    assert all(e.scim_type == "invalidSyntax" for e in errors)


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
