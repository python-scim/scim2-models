import os
from typing import Union

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
    samples = list(os.walk("samples"))[0][2]
    models = {
        "user": User,
        "group": Group,
        "schema": Schema,
        "resource_type": ResourceType,
        "service_provider_configuration": ServiceProviderConfiguration,
        "list_response": ListResponse[Union[User, Group, Schema, ResourceType]],
        "patch_op": PatchOp,
        "bulk_request": BulkRequest,
        "bulk_response": BulkResponse,
        "search_request": SearchRequest,
        "error": Error,
    }

    for sample in samples:
        model_name = sample.replace(".json", "").split("-")[2]
        model = models[model_name]

        # partial resources are not supported yet
        skipped = [
            "rfc7644-3.4.2-list_response-partial_attributes.json",
            "rfc7644-3.4.3-list_response-post_query.json",
            "rfc7644-3.9-user-partial_response.json",
        ]
        if sample in skipped:
            continue

        payload = load_sample(sample)
        obj = model.model_validate(payload)
        assert (
            obj.model_dump(
                exclude_none=True, exclude_unset=True, by_alias=True, mode="json"
            )
            == payload
        )
