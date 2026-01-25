import warnings

from scim2_models.exceptions import InvalidFilterException
from scim2_models.exceptions import InvalidPathException
from scim2_models.exceptions import InvalidSyntaxException
from scim2_models.exceptions import InvalidValueException
from scim2_models.exceptions import InvalidVersionException
from scim2_models.exceptions import MutabilityException
from scim2_models.exceptions import NoTargetException
from scim2_models.exceptions import SensitiveException
from scim2_models.exceptions import TooManyException
from scim2_models.exceptions import UniquenessException
from scim2_models.messages.error import Error


def test_predefined_errors():
    for exc in (
        InvalidFilterException(),
        TooManyException(),
        UniquenessException(),
        MutabilityException(),
        InvalidSyntaxException(),
        InvalidPathException(),
        NoTargetException(),
        InvalidValueException(),
        InvalidVersionException(),
        SensitiveException(),
    ):
        assert isinstance(exc.to_error(), Error)


def test_deprecated_make_error_methods():
    """Test deprecated make_*_error class methods emit warnings."""
    deprecated_methods = (
        Error.make_invalid_filter_error,
        Error.make_too_many_error,
        Error.make_uniqueness_error,
        Error.make_mutability_error,
        Error.make_invalid_syntax_error,
        Error.make_invalid_path_error,
        Error.make_no_target_error,
        Error.make_invalid_value_error,
        Error.make_invalid_version_error,
        Error.make_sensitive_error,
    )
    for method in deprecated_methods:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = method()
            assert isinstance(result, Error)
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "deprecated" in str(w[0].message)
