from typing import Annotated
from typing import Optional

import pytest

from scim2_models.base import ComplexAttribute
from scim2_models.base import Context
from scim2_models.base import Mutability
from scim2_models.base import Required
from scim2_models.base import Returned
from scim2_models.rfc7643.resource import Resource


class SubRetModel(ComplexAttribute):
    always_returned: Annotated[Optional[str], Returned.always] = None
    never_returned: Annotated[Optional[str], Returned.never] = None
    default_returned: Annotated[Optional[str], Returned.default] = None
    request_returned: Annotated[Optional[str], Returned.request] = None


class SupRetResource(Resource):
    schemas: Annotated[list[str], Required.true] = ["org:example:SupRetResource"]

    always_returned: Annotated[Optional[str], Returned.always] = None
    never_returned: Annotated[Optional[str], Returned.never] = None
    default_returned: Annotated[Optional[str], Returned.default] = None
    request_returned: Annotated[Optional[str], Returned.request] = None

    sub: Optional[SubRetModel] = None


class MutResource(Resource):
    schemas: Annotated[list[str], Required.true] = ["org:example:MutResource"]

    read_only: Annotated[Optional[str], Mutability.read_only] = None
    read_write: Annotated[Optional[str], Mutability.read_write] = None
    immutable: Annotated[Optional[str], Mutability.immutable] = None
    write_only: Annotated[Optional[str], Mutability.write_only] = None


@pytest.fixture
def ret_resource():
    return SupRetResource(
        id="id",
        always_returned="x",
        never_returned="x",
        default_returned="x",
        request_returned="x",
        sub=SubRetModel(
            always_returned="x",
            never_returned="x",
            default_returned="x",
            request_returned="x",
        ),
    )


@pytest.fixture
def mut_resource():
    return MutResource(
        id="id",
        read_only="x",
        read_write="x",
        immutable="x",
        write_only="x",
    )


def test_model_dump_json(mut_resource):
    assert (
        mut_resource.model_dump_json()
        == '{"schemas":["org:example:MutResource"],"id":"id","readOnly":"x","readWrite":"x","immutable":"x","writeOnly":"x"}'
    )


def test_dump_default(mut_resource):
    """By default, everything is dumped."""
    assert mut_resource.model_dump() == {
        "schemas": ["org:example:MutResource"],
        "id": "id",
        "readOnly": "x",
        "readWrite": "x",
        "immutable": "x",
        "writeOnly": "x",
    }

    assert mut_resource.model_dump(scim_ctx=Context.DEFAULT) == {
        "schemas": ["org:example:MutResource"],
        "id": "id",
        "readOnly": "x",
        "readWrite": "x",
        "immutable": "x",
        "writeOnly": "x",
    }

    assert mut_resource.model_dump(scim_ctx=None) == {
        "schemas": ["org:example:MutResource"],
        "id": "id",
        "read_only": "x",
        "read_write": "x",
        "immutable": "x",
        "write_only": "x",
    }


def test_dump_creation_request(mut_resource):
    """Test query building for resource creation request.

    Attributes marked as:
    - Mutability.read_write are dumped
    - Mutability.immutable are dumped
    - Mutability.write_only are dumped
    - Mutability.read_only are not dumped
    """
    assert mut_resource.model_dump(scim_ctx=Context.RESOURCE_CREATION_REQUEST) == {
        "schemas": ["org:example:MutResource"],
        "readWrite": "x",
        "immutable": "x",
        "writeOnly": "x",
    }


def test_dump_query_request(mut_resource):
    """Test query building for resource query request.

    Attributes marked as:
    - Mutability.read_write are dumped
    - Mutability.immutable are dumped
    - Mutability.write_only are not dumped
    - Mutability.read_only are dumped
    """
    assert mut_resource.model_dump(scim_ctx=Context.RESOURCE_QUERY_REQUEST) == {
        "schemas": ["org:example:MutResource"],
        "id": "id",
        "readOnly": "x",
        "readWrite": "x",
        "immutable": "x",
    }


def test_dump_replacement_request(mut_resource):
    """Test query building for resource model replacement requests.

    Attributes marked as:
    - Mutability.read_write are dumped
    - Mutability.immutable are not dumped
    - Mutability.write_only are dumped
    - Mutability.read_only are not dumped
    """
    assert mut_resource.model_dump(scim_ctx=Context.RESOURCE_REPLACEMENT_REQUEST) == {
        "schemas": ["org:example:MutResource"],
        "readWrite": "x",
        "writeOnly": "x",
        "immutable": "x",
    }


def test_dump_search_request(mut_resource):
    """Test query building for resource query request.

    Attributes marked as:
    - Mutability.read_write are dumped
    - Mutability.immutable are dumped
    - Mutability.write_only are not dumped
    - Mutability.read_only are dumped
    """
    assert mut_resource.model_dump(scim_ctx=Context.RESOURCE_QUERY_REQUEST) == {
        "schemas": ["org:example:MutResource"],
        "id": "id",
        "readOnly": "x",
        "readWrite": "x",
        "immutable": "x",
    }


def test_dump_default_response(ret_resource):
    """When no scim context is passed, every attributes are dumped."""
    assert ret_resource.model_dump() == {
        "schemas": ["org:example:SupRetResource"],
        "id": "id",
        "alwaysReturned": "x",
        "neverReturned": "x",
        "defaultReturned": "x",
        "requestReturned": "x",
        "sub": {
            "alwaysReturned": "x",
            "neverReturned": "x",
            "defaultReturned": "x",
            "requestReturned": "x",
        },
    }


@pytest.mark.parametrize(
    "context",
    [
        Context.RESOURCE_CREATION_RESPONSE,
        Context.RESOURCE_QUERY_RESPONSE,
        Context.RESOURCE_REPLACEMENT_RESPONSE,
        Context.SEARCH_RESPONSE,
    ],
)
def test_dump_response(context, ret_resource):
    """Test context for responses.

    Attributes marked as:
    - Returned.always are always dumped
    - Returned.never are never dumped
    - Returned.default are dumped unless excluded
    - Returned.request are dumped only if included

    Including attributes with 'attributes=' replace the whole default set.
    """
    assert ret_resource.model_dump(scim_ctx=context) == {
        "schemas": ["org:example:SupRetResource"],
        "id": "id",
        "alwaysReturned": "x",
        "defaultReturned": "x",
        "sub": {
            "alwaysReturned": "x",
            "defaultReturned": "x",
        },
    }

    assert ret_resource.model_dump(scim_ctx=context, attributes={"alwaysReturned"}) == {
        "schemas": ["org:example:SupRetResource"],
        "id": "id",
        "alwaysReturned": "x",
    }

    assert ret_resource.model_dump(scim_ctx=context, attributes={"neverReturned"}) == {
        "schemas": ["org:example:SupRetResource"],
        "id": "id",
        "alwaysReturned": "x",
    }

    assert ret_resource.model_dump(
        scim_ctx=context, attributes={"defaultReturned"}
    ) == {
        "schemas": ["org:example:SupRetResource"],
        "id": "id",
        "alwaysReturned": "x",
        "defaultReturned": "x",
    }

    assert ret_resource.model_dump(scim_ctx=context, attributes={"sub"}) == {
        "schemas": ["org:example:SupRetResource"],
        "id": "id",
        "alwaysReturned": "x",
        "sub": {
            "alwaysReturned": "x",
        },
    }

    assert ret_resource.model_dump(
        scim_ctx=context, attributes={"sub.defaultReturned"}
    ) == {
        "schemas": ["org:example:SupRetResource"],
        "id": "id",
        "alwaysReturned": "x",
        "sub": {
            "alwaysReturned": "x",
            "defaultReturned": "x",
        },
    }

    assert ret_resource.model_dump(
        scim_ctx=context, attributes={"requestReturned"}
    ) == {
        "schemas": ["org:example:SupRetResource"],
        "id": "id",
        "alwaysReturned": "x",
        "requestReturned": "x",
    }

    assert ret_resource.model_dump(
        scim_ctx=context,
        attributes={"defaultReturned", "requestReturned"},
    ) == {
        "schemas": ["org:example:SupRetResource"],
        "id": "id",
        "alwaysReturned": "x",
        "defaultReturned": "x",
        "requestReturned": "x",
    }

    assert ret_resource.model_dump(
        scim_ctx=context, excluded_attributes={"alwaysReturned"}
    ) == {
        "schemas": ["org:example:SupRetResource"],
        "id": "id",
        "alwaysReturned": "x",
        "defaultReturned": "x",
        "sub": {
            "alwaysReturned": "x",
            "defaultReturned": "x",
        },
    }

    assert ret_resource.model_dump(
        scim_ctx=context, excluded_attributes={"neverReturned"}
    ) == {
        "schemas": ["org:example:SupRetResource"],
        "id": "id",
        "alwaysReturned": "x",
        "defaultReturned": "x",
        "sub": {
            "alwaysReturned": "x",
            "defaultReturned": "x",
        },
    }

    assert ret_resource.model_dump(
        scim_ctx=context, excluded_attributes={"defaultReturned"}
    ) == {
        "schemas": ["org:example:SupRetResource"],
        "id": "id",
        "alwaysReturned": "x",
        "sub": {
            "alwaysReturned": "x",
            "defaultReturned": "x",
        },
    }

    assert ret_resource.model_dump(
        scim_ctx=context, excluded_attributes={"requestReturned"}
    ) == {
        "schemas": ["org:example:SupRetResource"],
        "id": "id",
        "alwaysReturned": "x",
        "defaultReturned": "x",
        "sub": {
            "alwaysReturned": "x",
            "defaultReturned": "x",
        },
    }

    assert ret_resource.model_dump(
        scim_ctx=context,
        excluded_attributes={"defaultReturned", "requestReturned"},
    ) == {
        "schemas": ["org:example:SupRetResource"],
        "id": "id",
        "alwaysReturned": "x",
        "sub": {
            "alwaysReturned": "x",
            "defaultReturned": "x",
        },
    }
