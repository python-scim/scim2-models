from scim2_models.rfc7644.error import Error


def test_predefined_errors():
    for gen in (
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
    ):
        assert isinstance(gen(), Error)
