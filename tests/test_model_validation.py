from typing import Annotated
from typing import List
from typing import Optional

import pytest
from pydantic import ValidationError

from pydantic_scim2.base import Context
from pydantic_scim2.base import Mutability
from pydantic_scim2.base import Returned
from pydantic_scim2.rfc7643.resource import Resource


class RetResource(Resource):
    schemas: List[str] = ["org:example:RetResource"]

    always_returned: Annotated[Optional[str], Returned.always] = None
    never_returned: Annotated[Optional[str], Returned.never] = None
    default_returned: Annotated[Optional[str], Returned.default] = None
    request_returned: Annotated[Optional[str], Returned.request] = None


class MutResource(Resource):
    schemas: List[str] = ["org:example:MutResource"]

    read_only: Annotated[Optional[str], Mutability.read_only] = None
    read_write: Annotated[Optional[str], Mutability.read_write] = None
    immutable: Annotated[Optional[str], Mutability.immutable] = None
    write_only: Annotated[Optional[str], Mutability.write_only] = None


def test_validate_default():
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


def test_validate_creation_request():
    """Test query validation for resource creation request:

    Attributes marked as:
    - Mutability.read_only raise a ValidationError
    """
    assert MutResource.model_validate(
        {
            "readWrite": "x",
            "immutable": "x",
            "writeOnly": "x",
        },
        scim_ctx=Context.RESOURCE_CREATION_REQUEST,
    ) == MutResource(
        schemas=["org:example:MutResource"],
        readWrite="x",
        immutable="x",
        writeOnly="x",
    )

    with pytest.raises(
        ValidationError,
        match="Field 'read_only' has mutability 'readOnly' but this in not valid in resource creation request context",
    ):
        MutResource.model_validate(
            {
                "readOnly": "x",
            },
            scim_ctx=Context.RESOURCE_CREATION_REQUEST,
        )


def test_validate_query_request():
    """Test query validation for resource query request:

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


def test_validate_replacement_request():
    """Test query validation for resource model replacement requests:

    Attributes marked as:
    - Mutability.immutable raise a ValidationError
    - Mutability.read_only are ignored"""

    assert MutResource.model_validate(
        {
            "readOnly": "x",
            "readWrite": "x",
            "writeOnly": "x",
        },
        scim_ctx=Context.RESOURCE_REPLACEMENT_REQUEST,
    ) == MutResource(
        schemas=["org:example:MutResource"],
        readWrite="x",
        writeOnly="x",
    )

    with pytest.raises(
        ValidationError,
        match="Field 'immutable' has mutability 'immutable' but this in not valid in resource replacement request context",
    ):
        MutResource.model_validate(
            {
                "immutable": "x",
            },
            scim_ctx=Context.RESOURCE_REPLACEMENT_REQUEST,
        )


def test_validate_search_request():
    """Test query validation for resource query request:

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


def test_validate_default_response():
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
def test_validate_response(context):
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
