from typing import Annotated
from typing import Optional

import pytest
from pydantic import ValidationError

from scim2_models import Attribute
from scim2_models import CaseExact
from scim2_models import Mutability
from scim2_models import Required
from scim2_models import Returned
from scim2_models import Schema
from scim2_models import Uniqueness
from scim2_models.resources.resource import Resource
from scim2_models.resources.resource import _model_to_schema


def test_group_schema(load_sample):
    payload = load_sample("rfc7643-8.7.1-schema-group.json")
    obj = Schema.model_validate(payload)

    assert obj.id == "urn:ietf:params:scim:schemas:core:2.0:Group"
    assert obj.name == "Group"
    assert obj.description == "Group"
    assert obj.attributes[0].name == "displayName"
    assert obj.attributes[0].type == Attribute.Type.string
    assert not obj.attributes[0].multi_valued
    assert obj.attributes[0].description == (
        "A human-readable name for the Group. REQUIRED."
    )
    assert not obj.attributes[0].required
    assert not obj.attributes[0].case_exact
    assert obj.attributes[0].mutability == Mutability.read_write
    assert obj.attributes[0].returned == Returned.default
    assert obj.attributes[0].uniqueness == Uniqueness.none
    assert obj.attributes[1].name == "members"
    assert obj.attributes[1].type == Attribute.Type.complex
    assert obj.attributes[1].multi_valued
    assert obj.attributes[1].description == "A list of members of the Group."
    assert not obj.attributes[1].required
    assert obj.attributes[1].sub_attributes[0].name == "value"
    assert obj.attributes[1].sub_attributes[0].type == Attribute.Type.string
    assert not obj.attributes[1].sub_attributes[0].multi_valued
    assert (
        obj.attributes[1].sub_attributes[0].description
        == "Identifier of the member of this Group."
    )
    assert not obj.attributes[1].sub_attributes[0].required
    assert not obj.attributes[1].sub_attributes[0].case_exact
    assert obj.attributes[1].sub_attributes[0].mutability == Mutability.immutable
    assert obj.attributes[1].sub_attributes[0].returned == Returned.default
    assert obj.attributes[1].sub_attributes[0].uniqueness == Uniqueness.none
    assert obj.attributes[1].sub_attributes[1].name == "$ref"
    assert obj.attributes[1].sub_attributes[1].type == Attribute.Type.reference
    assert obj.attributes[1].sub_attributes[1].reference_types == ["User", "Group"]
    assert not obj.attributes[1].sub_attributes[1].multi_valued
    assert obj.attributes[1].sub_attributes[1].description == (
        "The URI corresponding to a SCIM resource that is a member of this Group."
    )
    assert not obj.attributes[1].sub_attributes[1].required
    assert not obj.attributes[1].sub_attributes[1].case_exact
    assert obj.attributes[1].sub_attributes[1].mutability == Mutability.immutable
    assert obj.attributes[1].sub_attributes[1].returned == Returned.default
    assert obj.attributes[1].sub_attributes[1].uniqueness == Uniqueness.none
    assert obj.attributes[1].sub_attributes[2].name == "type"
    assert obj.attributes[1].sub_attributes[2].type == Attribute.Type.string
    assert not obj.attributes[1].sub_attributes[2].multi_valued
    assert obj.attributes[1].sub_attributes[2].description == (
        "A label indicating the type of resource, e.g., 'User' or 'Group'."
    )
    assert not obj.attributes[1].sub_attributes[2].required
    assert not obj.attributes[1].sub_attributes[2].case_exact
    assert obj.attributes[1].sub_attributes[2].canonical_values == ["User", "Group"]
    assert obj.attributes[1].sub_attributes[2].mutability == Mutability.immutable
    assert obj.attributes[1].sub_attributes[2].returned == Returned.default
    assert obj.attributes[1].sub_attributes[2].uniqueness == Uniqueness.none
    assert obj.attributes[1].mutability == Mutability.read_write
    assert obj.attributes[1].returned == Returned.default
    assert obj.meta.resource_type == "Schema"
    assert (
        obj.meta.location == "/v2/Schemas/urn:ietf:params:scim:schemas:core:2.0:Group"
    )

    assert obj.model_dump(exclude_unset=True) == payload


def test_uri_ids():
    """Test that schema ids are URI, as defined in RFC7643 §7.

    https://datatracker.ietf.org/doc/html/rfc7643#section-7
    """
    Schema(id="urn:ietf:params:scim:schemas:extension:enterprise:2.0:User")
    with pytest.raises(ValidationError):
        Schema(id="invalid\nuri")


def test_get_schema_attribute(load_sample):
    """Test the Schema.get_attribute method."""
    payload = load_sample("rfc7643-8.7.1-schema-user.json")
    schema = Schema.model_validate(payload)
    assert schema.get_attribute("invalid") is None
    with pytest.raises(KeyError):
        schema["invalid"]

    assert schema.attributes[0].name == "userName"
    assert schema.attributes[0].mutability == Mutability.read_write

    schema.get_attribute("userName").mutability = Mutability.read_only
    assert schema.attributes[0].mutability == Mutability.read_only

    schema["userName"].mutability = Mutability.read_write
    assert schema.attributes[0].mutability == Mutability.read_write


def test_get_attribute_attribute(load_sample):
    """Test the Schema.get_attribute method."""
    payload = load_sample("rfc7643-8.7.1-schema-group.json")
    schema = Schema.model_validate(payload)
    attribute = schema.get_attribute("members")

    assert attribute.get_attribute("invalid") is None
    with pytest.raises(KeyError):
        attribute["invalid"]

    assert attribute.sub_attributes[0].name == "value"
    assert attribute.sub_attributes[0].mutability == Mutability.immutable

    attribute.get_attribute("value").mutability = Mutability.read_only
    assert attribute.sub_attributes[0].mutability == Mutability.read_only

    attribute["value"].mutability = Mutability.read_write
    assert attribute.sub_attributes[0].mutability == Mutability.read_write


def test_model_to_schema_excludes_none_type_attributes():
    """Test that _model_to_schema excludes attributes with None type from schema."""

    class TestResource(Resource):
        schemas: list[str] = ["urn:test:schema"]
        valid_attr: Optional[str] = None
        none_attr: None = None

    schema = TestResource.to_schema()

    assert schema.id == "urn:test:schema"
    assert schema.name == "TestResource"

    attribute_names = [attr.name for attr in schema.attributes]

    assert "validAttr" in attribute_names
    assert "noneAttr" not in attribute_names


def test_external_id_redefined_in_subclass_is_exported():
    class CustomResource(Resource):
        schemas: list[str] = ["urn:custom:schema"]

        external_id: Annotated[
            Optional[str],
            Mutability.immutable,
            Returned.always,
            Required.true,
            CaseExact.false,
        ] = None

    schema = CustomResource.to_schema()

    attribute_names = [attr.name for attr in schema.attributes]
    assert "externalId" in attribute_names


def test_external_id_not_exported_when_not_redefined():
    class SimpleResource(Resource):
        schemas: list[str] = ["urn:simple:schema"]

    schema = _model_to_schema(SimpleResource)

    attribute_names = [attr.name for attr in schema.attributes]
    assert "externalId" not in attribute_names
