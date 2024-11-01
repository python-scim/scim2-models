import operator

from scim2_models.base import Context
from scim2_models.rfc7643.enterprise_user import EnterpriseUser
from scim2_models.rfc7643.group import Group
from scim2_models.rfc7643.resource_type import ResourceType
from scim2_models.rfc7643.schema import Schema
from scim2_models.rfc7643.service_provider_config import ServiceProviderConfig
from scim2_models.rfc7643.user import User


def canonic_schema(schema):
    """Remove descriptions and sort attributes so schemas are easily comparable."""
    schema["meta"] = None
    schema["name"] = None
    schema["schemas"] = None
    schema["description"] = None
    schema["attributes"].sort(key=operator.itemgetter("name"))
    for attr in schema["attributes"]:
        attr["description"] = None
        if attr.get("subAttributes"):
            attr["subAttributes"].sort(key=operator.itemgetter("name"))
            for subattr in attr["subAttributes"]:
                subattr["description"] = None
                if subattr.get("subAttributes"):
                    subattr["subAttributes"].sort(key=operator.itemgetter("name"))
                    for subsubattr in subattr["subAttributes"]:
                        subsubattr["description"] = None


def test_dynamic_group_schema(load_sample):
    sample = Schema.model_validate(
        load_sample("rfc7643-8.7.1-schema-group.json")
    ).model_dump()
    schema = Group.to_schema().model_dump()

    canonic_schema(schema)
    canonic_schema(sample)
    assert sample == schema


def test_dynamic_user_schema(load_sample):
    sample = Schema.model_validate(
        load_sample("rfc7643-8.7.1-schema-user.json")
    ).model_dump()
    schema = User.to_schema().model_dump()

    canonic_schema(schema)
    canonic_schema(sample)

    # Remove attributes that are redefined from implicit complexattributes
    for i, attr in enumerate(sample["attributes"]):
        if attr["name"] in ("roles", "entitlements"):
            sample["attributes"][i]["subAttributes"] = [
                subattr
                for subattr in attr["subAttributes"]
                if subattr["name"] not in ("type", "primary", "value", "display")
            ]

        if attr["name"] == "x509Certificates":
            sample["attributes"][i]["subAttributes"] = [
                subattr
                for subattr in attr["subAttributes"]
                if subattr["name"] not in ("type", "primary", "display")
            ]

    assert sample == schema


def test_dynamic_enterprise_user_schema(load_sample):
    sample = Schema.model_validate(
        load_sample("rfc7643-8.7.1-schema-enterprise_user.json")
    ).model_dump()
    schema = EnterpriseUser.to_schema().model_dump()

    canonic_schema(schema)
    canonic_schema(sample)
    assert sample == schema


def test_dynamic_resource_type_schema(load_sample):
    sample = Schema.model_validate(
        load_sample("rfc7643-8.7.2-schema-resource_type.json")
    ).model_dump()
    schema = ResourceType.to_schema().model_dump()

    canonic_schema(schema)
    canonic_schema(sample)
    assert sample == schema


def test_dynamic_service_provider_config_schema(load_sample):
    sample = Schema.model_validate(
        load_sample("rfc7643-8.7.2-schema-service_provider_configuration.json")
    ).model_dump()
    schema = ServiceProviderConfig.to_schema().model_dump()

    canonic_schema(schema)
    canonic_schema(sample)

    schema["attributes"] = [
        attr for attr in schema["attributes"] if attr["name"] != "id"
    ]
    for i, attr in enumerate(schema["attributes"]):
        if attr["name"] == "authenticationSchemes":
            schema["attributes"][i]["subAttributes"] = [
                subattr
                for subattr in attr["subAttributes"]
                if subattr["name"] not in ("type", "primary")
            ]

    assert sample == schema


def test_dynamic_schema_schema(load_sample):
    sample = Schema.model_validate(
        load_sample("rfc7643-8.7.2-schema-schema.json")
    ).model_dump()
    schema = Schema.to_schema().model_dump()

    canonic_schema(schema)
    canonic_schema(sample)
    assert sample == schema


def test_dump_with_context():
    models = [User, EnterpriseUser, Group, ResourceType, Schema, ServiceProviderConfig]
    for model in models:
        model.to_schema().model_dump(scim_ctx=Context.RESOURCE_QUERY_RESPONSE)
