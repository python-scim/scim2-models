from typing import Annotated

import pytest
from pydantic import ValidationError

from scim2_models.annotations import Mutability
from scim2_models.annotations import Required
from scim2_models.annotations import Returned
from scim2_models.attributes import ComplexAttribute
from scim2_models.context import Context
from scim2_models.resources.resource import Resource


class RetResource(Resource):
    schemas: Annotated[list[str], Required.true] = ["org:example:RetResource"]

    always_returned: Annotated[str | None, Returned.always] = None
    never_returned: Annotated[str | None, Returned.never] = None
    default_returned: Annotated[str | None, Returned.default] = None
    request_returned: Annotated[str | None, Returned.request] = None


class MutResource(Resource):
    schemas: Annotated[list[str], Required.true] = ["org:example:MutResource"]

    read_only: Annotated[str | None, Mutability.read_only] = None
    read_write: Annotated[str | None, Mutability.read_write] = None
    immutable: Annotated[str | None, Mutability.immutable] = None
    write_only: Annotated[str | None, Mutability.write_only] = None


class ReqResource(Resource):
    schemas: Annotated[list[str], Required.true] = ["org:example:ReqResource"]

    required: Annotated[str | None, Required.true] = None
    optional: Annotated[str | None, Required.false] = None


def test_validate_default_mutability():
    """Test query validation for resource creation request."""
    assert MutResource.model_validate(
        {
            "readOnly": "x",
            "readWrite": "x",
            "immutable": "x",
            "writeOnly": "x",
        },
    ) == MutResource(
        schemas=["org:example:MutResource"],
        readWrite="x",
        immutable="x",
        writeOnly="x",
        readOnly="x",
    )

    assert MutResource.model_validate(
        {
            "readOnly": "x",
            "readWrite": "x",
            "immutable": "x",
            "writeOnly": "x",
        },
        scim_ctx=None,
    ) == MutResource(
        schemas=["org:example:MutResource"],
        readWrite="x",
        immutable="x",
        writeOnly="x",
        readOnly="x",
    )

    assert MutResource.model_validate(
        {
            "readOnly": "x",
            "readWrite": "x",
            "immutable": "x",
            "writeOnly": "x",
        },
        scim_ctx=Context.DEFAULT,
    ) == MutResource(
        schemas=["org:example:MutResource"],
        readWrite="x",
        immutable="x",
        writeOnly="x",
        readOnly="x",
    )


def test_validate_creation_request_mutability():
    """Test query validation for resource creation request.

    Attributes marked as:
    - Mutability.read_only are ignored
    """
    assert MutResource.model_validate(
        {
            "readWrite": "x",
            "immutable": "x",
            "writeOnly": "x",
            "readOnly": "x",
        },
        scim_ctx=Context.RESOURCE_CREATION_REQUEST,
    ) == MutResource(
        schemas=["org:example:MutResource"],
        readWrite="x",
        immutable="x",
        writeOnly="x",
    )


def test_validate_query_request_mutability():
    """Test query validation for resource query request.

    Attributes marked as:
    - Mutability.write_only raise a ValidationError
    """
    assert MutResource.model_validate(
        {
            "readOnly": "x",
            "readWrite": "x",
            "immutable": "x",
        },
        scim_ctx=Context.RESOURCE_QUERY_REQUEST,
    ) == MutResource(
        schemas=["org:example:MutResource"],
        readOnly="x",
        readWrite="x",
        immutable="x",
    )

    with pytest.raises(
        ValidationError,
        match="Field 'write_only' has mutability 'writeOnly' but this in not valid in resource query request context",
    ):
        MutResource.model_validate(
            {
                "writeOnly": "x",
            },
            scim_ctx=Context.RESOURCE_QUERY_REQUEST,
        )


def test_validate_replacement_request_mutability():
    """Test query validation for resource model replacement requests.

    Attributes marked as:
    - Mutability.immutable raise a ValidationError if different than the 'original' item.
    - Mutability.read_only are copied from the original
    """
    original = MutResource(read_only="y", read_write="y", write_only="y", immutable="y")
    with pytest.warns(DeprecationWarning, match="original"):
        assert MutResource.model_validate(
            {
                "readOnly": "x",
                "readWrite": "x",
                "writeOnly": "x",
                "immutable": "y",
            },
            scim_ctx=Context.RESOURCE_REPLACEMENT_REQUEST,
            original=original,
        ) == MutResource(
            schemas=["org:example:MutResource"],
            read_only="y",
            readWrite="x",
            writeOnly="x",
            immutable="y",
        )

    with pytest.warns(DeprecationWarning, match="original"):
        MutResource.model_validate(
            {
                "immutable": "y",
            },
            scim_ctx=Context.RESOURCE_REPLACEMENT_REQUEST,
            original=original,
        )

    with pytest.warns(DeprecationWarning, match="original"):
        with pytest.raises(
            ValidationError,
            match="mutability",
        ):
            MutResource.model_validate(
                {
                    "immutable": "x",
                },
                scim_ctx=Context.RESOURCE_REPLACEMENT_REQUEST,
                original=original,
            )


def test_validate_replacement_request_mutability_sub_attributes():
    """Test query validation for resource model replacement requests.

    Sub-attributes marked as:
    - Mutability.immutable raise a ValidationError if different than the 'original' item.
    - Mutability.read_only are ignored
    """

    class Sub(ComplexAttribute):
        immutable: Annotated[str | None, Mutability.immutable] = None

    class Super(Resource):
        schemas: Annotated[list[str], Required.true] = ["org:example:Super"]
        sub: Sub | None = None

    original = Super(sub=Sub(immutable="y"))
    with pytest.warns(DeprecationWarning, match="original"):
        assert Super.model_validate(
            {
                "sub": {
                    "immutable": "y",
                }
            },
            scim_ctx=Context.RESOURCE_REPLACEMENT_REQUEST,
            original=original,
        ) == Super(
            schemas=["org:example:Super"],
            sub=Sub(
                immutable="y",
            ),
        )

    with pytest.warns(DeprecationWarning, match="original"):
        Super.model_validate(
            {
                "sub": {
                    "immutable": "y",
                }
            },
            scim_ctx=Context.RESOURCE_REPLACEMENT_REQUEST,
            original=original,
        )

    with pytest.warns(DeprecationWarning, match="original"):
        with pytest.raises(
            ValidationError,
            match="mutability",
        ):
            Super.model_validate(
                {
                    "sub": {
                        "immutable": "x",
                    }
                },
                scim_ctx=Context.RESOURCE_REPLACEMENT_REQUEST,
                original=original,
            )


def test_replace_detects_changed_field():
    """Replace raises MutabilityException when an immutable field differs."""
    from scim2_models.exceptions import MutabilityException

    original = MutResource(immutable="y")
    replacement = MutResource(immutable="x")
    with pytest.raises(MutabilityException):
        replacement.replace(original)


def test_replace_allows_identical_values():
    """Replace passes when immutable fields are unchanged."""
    original = MutResource(immutable="y")
    replacement = MutResource(immutable="y")
    replacement.replace(original)


def test_replace_recurses_into_complex_attributes():
    """Replace detects changes in nested complex attribute immutable fields."""
    from scim2_models.exceptions import MutabilityException

    class Sub(ComplexAttribute):
        immutable: Annotated[str | None, Mutability.immutable] = None

    class Super(Resource):
        schemas: Annotated[list[str], Required.true] = ["org:example:Super"]
        sub: Sub | None = None

    original = Super(sub=Sub(immutable="y"))
    replacement = Super(sub=Sub(immutable="x"))
    with pytest.raises(MutabilityException):
        replacement.replace(original)


def test_replace_ignores_readwrite_changes():
    """Replace does not raise when readWrite fields change."""
    original = MutResource(read_write="y")
    replacement = MutResource(read_write="x")
    replacement.replace(original)
    assert replacement.read_write == "x"


def test_replace_copies_read_only_from_original():
    """Replace copies readOnly fields from the original resource."""
    original = MutResource(read_only="server-value")
    replacement = MutResource(read_only="client-value")
    replacement.replace(original)
    assert replacement.read_only == "server-value"


def test_replace_copies_read_only_none_from_original():
    """Replace copies readOnly fields even when the original value is None."""
    original = MutResource(read_only=None)
    replacement = MutResource(read_only="client-value")
    replacement.replace(original)
    assert replacement.read_only is None


def test_replace_preserves_immutable_when_absent():
    """Replace copies immutable fields from original when absent in replacement."""
    original = MutResource(immutable="y")
    replacement = MutResource(immutable=None)
    replacement.replace(original)
    assert replacement.immutable == "y"


def test_replace_copies_read_only_in_nested_complex_attribute():
    """Replace copies readOnly sub-attributes from original in nested complex attributes."""

    class Sub(ComplexAttribute):
        read_only: Annotated[str | None, Mutability.read_only] = None
        read_write: Annotated[str | None, Mutability.read_write] = None

    class Super(Resource):
        schemas: Annotated[list[str], Required.true] = ["org:example:Super"]
        sub: Sub | None = None

    original = Super(sub=Sub(read_only="server", read_write="old"))
    replacement = Super(sub=Sub(read_only="client", read_write="new"))
    replacement.replace(original)
    assert replacement.sub.read_only == "server"
    assert replacement.sub.read_write == "new"


def test_original_parameter_emits_deprecation_warning():
    """Passing 'original' to model_validate emits a DeprecationWarning."""
    original = MutResource(immutable="y")
    with pytest.warns(DeprecationWarning, match="original"):
        MutResource.model_validate(
            {"immutable": "y"},
            scim_ctx=Context.RESOURCE_REPLACEMENT_REQUEST,
            original=original,
        )


def test_replacement_request_without_original_parameter():
    """Replacement requests work without 'original' when using replace manually."""
    from scim2_models.exceptions import MutabilityException

    original = MutResource(immutable="y")
    replacement = MutResource.model_validate(
        {"immutable": "x"},
        scim_ctx=Context.RESOURCE_REPLACEMENT_REQUEST,
    )
    with pytest.raises(MutabilityException):
        replacement.replace(original)


def test_replacement_request_without_original_allows_matching_values():
    """Replacement requests validate and replace succeeds with identical immutable values."""
    original = MutResource(immutable="y")
    replacement = MutResource.model_validate(
        {"immutable": "y"},
        scim_ctx=Context.RESOURCE_REPLACEMENT_REQUEST,
    )
    replacement.replace(original)


def test_validate_search_request_mutability():
    """Test query validation for resource query request.

    Attributes marked as:
    - Mutability.write_only raise a ValidationError
    """
    assert MutResource.model_validate(
        {
            "readOnly": "x",
            "readWrite": "x",
            "immutable": "x",
        },
        scim_ctx=Context.SEARCH_REQUEST,
    ) == MutResource(
        schemas=["org:example:MutResource"],
        readOnly="x",
        readWrite="x",
        immutable="x",
    )

    with pytest.raises(
        ValidationError,
        match="Field 'write_only' has mutability 'writeOnly' but this in not valid in search request context",
    ):
        MutResource.model_validate(
            {
                "writeOnly": "x",
            },
            scim_ctx=Context.SEARCH_REQUEST,
        )


def test_validate_default_response_returnability():
    """When no scim context is passed, every attributes are dumped."""
    assert RetResource.model_validate(
        {
            "schemas": ["org:example:RetResource"],
            "id": "id",
            "alwaysReturned": "x",
            "neverReturned": "x",
            "defaultReturned": "x",
            "requestReturned": "x",
        },
    ) == RetResource(
        schemas=["org:example:RetResource"],
        id="id",
        alwaysReturned="x",
        neverReturned="x",
        defaultReturned="x",
        requestReturned="x",
    )

    assert RetResource.model_validate(
        {
            "schemas": ["org:example:RetResource"],
            "id": "id",
            "alwaysReturned": "x",
            "neverReturned": "x",
            "defaultReturned": "x",
            "requestReturned": "x",
        },
        scim_ctx=None,
    ) == RetResource(
        schemas=["org:example:RetResource"],
        id="id",
        alwaysReturned="x",
        neverReturned="x",
        defaultReturned="x",
        requestReturned="x",
    )

    assert RetResource.model_validate(
        {
            "schemas": ["org:example:RetResource"],
            "id": "id",
            "alwaysReturned": "x",
            "neverReturned": "x",
            "defaultReturned": "x",
            "requestReturned": "x",
        },
        scim_ctx=Context.DEFAULT,
    ) == RetResource(
        schemas=["org:example:RetResource"],
        id="id",
        alwaysReturned="x",
        neverReturned="x",
        defaultReturned="x",
        requestReturned="x",
    )


@pytest.mark.parametrize(
    "context",
    [
        Context.RESOURCE_CREATION_RESPONSE,
        Context.RESOURCE_QUERY_RESPONSE,
        Context.RESOURCE_REPLACEMENT_RESPONSE,
        Context.SEARCH_RESPONSE,
    ],
)
def test_validate_response_returnability(context):
    """Test context for responses.

    Attributes marked as:
    - Returned.always raise a ValidationException if None
    - Returned.never raise a ValidationException if not None
    """
    assert RetResource.model_validate(
        {
            "schemas": ["org:example:RetResource"],
            "id": "id",
            "alwaysReturned": "x",
            "defaultReturned": "x",
            "requestReturned": "x",
        },
        scim_ctx=context,
    ) == RetResource(
        schemas=["org:example:RetResource"],
        id="id",
        alwaysReturned="x",
        defaultReturned="x",
        requestReturned="x",
    )

    # always is missing
    with pytest.raises(
        ValidationError,
        match="Field 'always_returned' has returnability 'always' but value is missing or null",
    ):
        RetResource.model_validate({"id": "id"}, scim_ctx=context)

    # always is None
    with pytest.raises(
        ValidationError,
        match="Field 'always_returned' has returnability 'always' but value is missing or null",
    ):
        RetResource.model_validate(
            {"id": "id", "alwaysReturned": None}, scim_ctx=context
        )

    # never is not None
    with pytest.raises(
        ValidationError,
        match="Field 'never_returned' has returnability 'never' but value is set",
    ):
        RetResource.model_validate(
            {
                "id": "id",
                "alwaysReturned": "x",
                "neverReturned": "x",
            },
            scim_ctx=context,
        )


def test_validate_default_necessity():
    """Test query validation for resource creation request."""
    assert ReqResource.model_validate(
        {
            "required": "x",
            "optional": "x",
        },
    ) == ReqResource(
        schemas=["org:example:ReqResource"],
        required="x",
        optional="x",
    )

    assert ReqResource.model_validate(
        {
            "required": "x",
            "optional": "x",
        },
        scim_ctx=None,
    ) == ReqResource(
        schemas=["org:example:ReqResource"],
        required="x",
        optional="x",
    )

    assert ReqResource.model_validate(
        {
            "required": "x",
            "optional": "x",
        },
        scim_ctx=Context.DEFAULT,
    ) == ReqResource(
        schemas=["org:example:ReqResource"],
        required="x",
        optional="x",
    )


@pytest.mark.parametrize(
    "context",
    [
        Context.RESOURCE_CREATION_REQUEST,
        Context.RESOURCE_REPLACEMENT_REQUEST,
    ],
)
def test_validate_creation_and_replacement_request_necessity(context):
    """Test query validation for resource creation and requests.

    Attributes marked as:
    - Required.true and missing raise a ValidationError
    """
    assert ReqResource.model_validate(
        {
            "required": "x",
            "optional": "x",
        },
        scim_ctx=context,
    ) == ReqResource(
        schemas=["org:example:ReqResource"],
        required="x",
        optional="x",
    )

    assert ReqResource.model_validate(
        {
            "required": "x",
        },
        scim_ctx=context,
    ) == ReqResource(
        schemas=["org:example:ReqResource"],
        required="x",
    )

    with pytest.raises(
        ValidationError,
        match="Field 'required' is required but value is missing or null",
    ):
        ReqResource.model_validate(
            {
                "optional": "x",
            },
            scim_ctx=context,
        )


@pytest.mark.parametrize(
    "context",
    [
        Context.RESOURCE_QUERY_RESPONSE,
        Context.SEARCH_RESPONSE,
    ],
)
def test_validate_query_and_search_request_necessity(context):
    """Test query validation for resource query request.

    Attributes marked as:
    - Required.true and missing raise a ValidationError
    """
    assert ReqResource.model_validate(
        {
            "id": "x",
            "required": "x",
            "optional": "x",
        },
        scim_ctx=context,
    ) == ReqResource(
        schemas=["org:example:ReqResource"],
        id="x",
        required="x",
        optional="x",
    )

    assert ReqResource.model_validate(
        {
            "id": "x",
            "required": "x",
        },
        scim_ctx=context,
    ) == ReqResource(
        schemas=["org:example:ReqResource"],
        id="x",
        required="x",
    )

    assert ReqResource.model_validate(
        {
            "id": "x",
            "optional": "x",
        },
        scim_ctx=context,
    ) == ReqResource(
        schemas=["org:example:ReqResource"],
        id="x",
        optional="x",
    )
