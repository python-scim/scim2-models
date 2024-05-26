import os

from pydantic_scim2 import BulkRequest
from pydantic_scim2 import BulkResponse
from pydantic_scim2 import Error
from pydantic_scim2 import Group
from pydantic_scim2 import ListResponse
from pydantic_scim2 import PatchOp
from pydantic_scim2 import ResourceType
from pydantic_scim2 import Schema
from pydantic_scim2 import SearchRequest
from pydantic_scim2 import ServiceProviderConfiguration
from pydantic_scim2 import User


def test_parse_and_serialize_examples(load_sample):
    samples = list(os.walk("tests/fixtures"))[0][2]
    models = {
        "user": User,
        "group": Group,
        "schema": Schema,
        "resource_type": ResourceType,
        "service_provider_configuration": ServiceProviderConfiguration,
        "list_response": ListResponse,
        "patch_op": PatchOp,
        "bulk_request": BulkRequest,
        "bulk_response": BulkResponse,
        "search_request": SearchRequest,
        "error": Error,
    }

    for sample in samples:
        model_name = sample.replace(".json", "").split("-")[2]
        model = models[model_name]

        # TODO: ListResponse must take a type parameter
        if model is ListResponse:
            continue

        payload = load_sample(sample)
        obj = model.model_validate(payload)
        assert (
            obj.model_dump(
                exclude_none=True, exclude_unset=True, by_alias=True, mode="json"
            )
            == payload
        )
