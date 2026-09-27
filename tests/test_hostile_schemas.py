import pytest

from scim2_models import Context
from scim2_models import Extension
from scim2_models import Group
from scim2_models import Resource
from scim2_models import ResourceType
from scim2_models import Schema
from scim2_models import ScimProvider
from scim2_models import ScimProviderError
from scim2_models import User
from scim2_models import get_model_by_payload

SCHEMA_ID = "urn:example:params:scim:schemas:core:2.0:Thing"

MODEL_MEMBER_NAMES = [
    ("model_config", "model_config_"),
    ("modelConfig", "model_config_"),
    ("model_fields", "model_fields_"),
    ("copy", "copy_"),
    ("validate", "validate_"),
    ("json", "json_"),
    ("dict", "dict_"),
    ("getFieldRootType", "get_field_root_type_"),
    ("get_field_annotation", "get_field_annotation_"),
    ("model_post_init", "model_post_init_"),
]
"""Names of members every SCIM model holds."""

RESOURCE_MEMBER_NAMES = [
    ("toSchema", "to_schema_"),
    ("getExtensionModels", "get_extension_models_"),
]
"""Names of members only resources hold."""


def schema(*attributes):
    return Schema.model_validate(
        {"id": SCHEMA_ID, "name": "Thing", "attributes": list(attributes)}
    )


def string(name):
    return {"name": name, "type": "string"}


def complex_(name, *sub_attributes):
    return {"name": name, "type": "complex", "subAttributes": list(sub_attributes)}


def nested(depth):
    """Return a complex attribute nesting complex attributes ``depth`` levels deep."""
    attribute = string("leaf")
    for level in range(depth, 0, -1):
        attribute = complex_(f"level{level}", attribute)
    return attribute


def discover(*schemas):
    resource_type = ResourceType(
        id="Thing", name="Thing", endpoint="/Things", schema_=SCHEMA_ID
    )
    return ScimProvider.from_discovery(schemas, [resource_type])


def round_trip(model, payload):
    resource = model.model_validate(payload, scim_ctx=Context.RESOURCE_QUERY_RESPONSE)
    return resource, resource.model_dump(scim_ctx=Context.RESOURCE_QUERY_RESPONSE)


@pytest.mark.parametrize(
    ("scim_name", "python_name"), MODEL_MEMBER_NAMES + RESOURCE_MEMBER_NAMES
)
def test_attribute_named_after_a_model_member_is_held_under_another_name(
    scim_name, python_name
):
    """A published attribute cannot hide a method or the configuration of the model."""
    model = Resource.from_schema(schema(string(scim_name), string("label")))

    resource, dumped = round_trip(
        model, {"schemas": [SCHEMA_ID], "id": "1", scim_name: "x", "label": "y"}
    )

    assert python_name in model.model_fields
    assert getattr(resource, python_name) == "x"
    assert resource[scim_name] == "x"
    assert dumped[scim_name] == "x"
    assert dumped["label"] == "y"


@pytest.mark.parametrize(("scim_name", "python_name"), MODEL_MEMBER_NAMES)
def test_extension_attribute_named_after_a_model_member_is_held_under_another_name(
    scim_name, python_name
):
    """Extensions are built on another base, whose members are protected as well."""
    model = Extension.from_schema(schema(string(scim_name)))

    assert python_name in model.model_fields
    assert model.model_validate({scim_name: "x"}).model_dump()[scim_name] == "x"


@pytest.mark.parametrize(("scim_name", "python_name"), MODEL_MEMBER_NAMES)
def test_sub_attribute_named_after_a_model_member_is_held_under_another_name(
    scim_name, python_name
):
    """Complex attributes are models too, and their members are protected as well."""
    model = Resource.from_schema(schema(complex_("box", string(scim_name))))

    resource, dumped = round_trip(
        model, {"schemas": [SCHEMA_ID], "id": "1", "box": {scim_name: "x"}}
    )

    assert getattr(resource.box, python_name) == "x"
    assert dumped["box"] == {scim_name: "x"}


@pytest.mark.parametrize(("scim_name", "python_name"), RESOURCE_MEMBER_NAMES)
def test_sub_attribute_named_after_a_resource_member_keeps_its_name(
    scim_name, python_name
):
    """Only the members of the model an attribute belongs to are protected."""
    model = Resource.from_schema(schema(complex_("box", string(scim_name))))

    resource, _ = round_trip(
        model, {"schemas": [SCHEMA_ID], "id": "1", "box": {scim_name: "x"}}
    )

    assert getattr(resource.box, python_name.rstrip("_")) == "x"


@pytest.mark.parametrize(
    ("scim_name", "python_name"),
    [("_x", "x"), ("__class__", "class__"), ("Class", "class_")],
)
def test_attribute_name_is_made_a_valid_field_name(scim_name, python_name):
    """Pydantic refuses leading underscores, and Python its keywords, whatever their case."""
    model = Resource.from_schema(schema(string(scim_name)))

    resource, dumped = round_trip(
        model, {"schemas": [SCHEMA_ID], "id": "1", scim_name: "x"}
    )

    assert getattr(resource, python_name) == "x"
    assert dumped[scim_name] == "x"


def test_schema_of_the_schemas_is_nested_two_levels_deep(load_sample):
    """RFC7643 §7 lets the Schema resource nest its complex 'subAttributes' in 'attributes'."""
    sample = Schema.model_validate(load_sample("rfc7643-8.7.2-schema-schema.json"))

    model = Resource.from_schema(sample)

    assert "sub_attributes" in model.get_field_root_type("attributes").model_fields


def test_complex_attributes_nested_two_levels_deep_are_accepted():
    """The deepest nesting a published schema shows is accepted."""
    provider = discover(schema(nested(2)))

    assert provider.models


@pytest.mark.parametrize("depth", [3, 200])
def test_complex_attributes_nested_deeper_are_refused(depth):
    """A schema nesting complex attributes deeper cannot make the models."""
    with pytest.raises(ScimProviderError, match="is nested more than 2 levels deep"):
        discover(schema(nested(depth)))


def test_attributes_naming_the_same_attribute_are_refused_as_a_provider_error():
    """Two attributes only differing by case make an incoherent service description."""
    with pytest.raises(ScimProviderError, match=f"The schema {SCHEMA_ID}"):
        discover(schema(string("label"), string("LABEL")))


@pytest.mark.parametrize(
    "names",
    [("modelConfig", "model_config"), ("x", "_x")],
)
def test_attribute_left_without_a_usable_name_is_refused(names):
    """When two attributes want the same field, the one left with its raw name must be usable."""
    with pytest.raises(ScimProviderError, match="cannot be the name of an attribute"):
        discover(schema(*(string(name) for name in names)))


@pytest.mark.parametrize(
    "payload",
    [
        {"schemas": 1},
        {"schemas": None},
        {"schemas": {"a": 1}},
        {"schemas": [1]},
        {"schemas": []},
        {"schemas": "urn:ietf:params:scim:schemas:core:2.0:User"},
        {},
    ],
)
def test_payload_without_a_list_of_schemas_matches_no_model(payload):
    """Schemas that are not a list of URIs select no model."""
    assert get_model_by_payload([User, Group], payload) is None
