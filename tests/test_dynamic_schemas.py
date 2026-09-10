import copyreg
import operator

import pytest
from pydantic import Field
from pydantic.fields import FieldInfo

from scim2_models import URN
from scim2_models.attributes import ExtensibleStringEnum
from scim2_models.context import Context
from scim2_models.resources.enterprise_user import EnterpriseUser
from scim2_models.resources.group import Group
from scim2_models.resources.resource import Resource
from scim2_models.resources.resource_type import ResourceType
from scim2_models.resources.schema import Attribute
from scim2_models.resources.schema import Schema
from scim2_models.resources.schema import _make_python_model
from scim2_models.resources.service_provider_config import ServiceProviderConfig
from scim2_models.resources.user import User


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


def test_inheritance():
    """Check that parent attributes are included in the schema."""

    class Foo(Resource):
        __schema__ = URN("urn:ietf:params:scim:schemas:core:2.0:Foo")

        foo: str | None = None

    class Bar(Foo):
        bar: str | None = None

    schema = Bar.to_schema()
    assert schema.model_dump() == {
        "attributes": [
            {
                "caseExact": False,
                "multiValued": False,
                "mutability": "readWrite",
                "name": "foo",
                "required": False,
                "returned": "default",
                "type": "string",
                "uniqueness": "none",
            },
            {
                "caseExact": False,
                "multiValued": False,
                "mutability": "readWrite",
                "name": "bar",
                "required": False,
                "returned": "default",
                "type": "string",
                "uniqueness": "none",
            },
        ],
        "description": "Bar",
        "id": "urn:ietf:params:scim:schemas:core:2.0:Foo",
        "name": "Bar",
        "schemas": [
            "urn:ietf:params:scim:schemas:core:2.0:Schema",
        ],
    }


def test_to_schema_without_slotnames_cache():
    """Regression test for ``FieldInfo.__slotnames__`` usage.

    ``FieldInfo.__slotnames__`` is a cache populated lazily by ``copy.copy`` /
    ``copyreg._slotnames``. Computing a schema must not rely on that cache
    being already warm, otherwise ``to_schema`` raises ``AttributeError`` on a
    fresh process.
    """
    copyreg._slotnames(FieldInfo)
    del FieldInfo.__slotnames__

    class Foo(Resource):
        __schema__ = URN("urn:ietf:params:scim:schemas:core:2.0:Foo")

        foo: str | None = None

    Foo.to_schema()


def test_make_python_model_validates_name():
    """Test that make_python_model raises an exception when obj.name is not defined."""
    # Test with Schema object without name
    schema = Schema(id="urn:example:schema")
    schema.name = None

    with pytest.raises(ValueError, match="Schema or Attribute 'name' must be defined"):
        _make_python_model(schema, Resource)

    # Test with Attribute object without name
    attribute = Attribute(type=Attribute.Type.string)
    attribute.name = None

    with pytest.raises(ValueError, match="Schema or Attribute 'name' must be defined"):
        _make_python_model(attribute, Resource)


def test_canonical_values_are_read_from_a_string_enumeration():
    """The members of a string enumeration are the canonical values of an attribute."""

    class Kind(ExtensibleStringEnum):
        cat = "cat"
        dog = "dog"

    class Pet(Resource):
        __schema__ = URN("urn:example:Pet")

        kind: Kind | None = None

    assert Pet.to_schema().attributes[0].canonical_values == ["cat", "dog"]


def test_canonical_values_declared_as_examples_are_kept():
    """An explicit list of examples answers for the canonical values of an attribute."""

    class Kind(ExtensibleStringEnum):
        cat = "cat"
        dog = "dog"

    class Pet(Resource):
        __schema__ = URN("urn:example:Pet")

        kind: Kind | None = Field(None, examples=["cat"])

    assert Pet.to_schema().attributes[0].canonical_values == ["cat"]


def test_a_boolean_enumeration_declares_no_canonical_values():
    """``canonicalValues`` describes string attributes, where Required holds booleans."""
    attributes = Schema.to_schema().attributes
    described = next(
        attribute for attribute in attributes if attribute.name == "attributes"
    )
    sub_attributes = {sub.name: sub for sub in described.sub_attributes}
    assert sub_attributes["required"].canonical_values is None
    assert sub_attributes["type"].canonical_values == [
        "string",
        "complex",
        "boolean",
        "decimal",
        "integer",
        "dateTime",
        "reference",
        "binary",
    ]


def test_a_standard_resource_publishes_the_canonical_values_of_its_enumerations():
    """The canonical values of ``emails.type`` are the members of its enumeration."""
    attributes = {
        attribute.name: attribute for attribute in User.to_schema().attributes
    }
    sub_attributes = {sub.name: sub for sub in attributes["emails"].sub_attributes}
    assert sub_attributes["type"].canonical_values == ["work", "home", "other"]
