from scim2_models import Attribute
from scim2_models import Mutability
from scim2_models import Returned
from scim2_models import Schema
from scim2_models import Uniqueness


def test_group_schema(load_sample):
    payload = load_sample("rfc7643-8.7.1-schema-group.json")
    obj = Schema.model_validate(payload)

    assert obj.id == "urn:ietf:params:scim:schemas:core:2.0:Group"
    assert obj.name == "Group"
    assert obj.description == "Group"
    assert obj.attributes[0].name == "displayName"
    assert obj.attributes[0].type == Attribute.Type.string
    assert obj.attributes[0].multi_valued is False
    assert obj.attributes[0].description == (
        "A human-readable name for the Group. " "REQUIRED."
    )
    assert obj.attributes[0].required is False
    assert obj.attributes[0].case_exact is False
    assert obj.attributes[0].mutability == Mutability.read_write
    assert obj.attributes[0].returned == Returned.default
    assert obj.attributes[0].uniqueness == Uniqueness.none
    assert obj.attributes[1].name == "members"
    assert obj.attributes[1].type == Attribute.Type.complex
    assert obj.attributes[1].multi_valued is True
    assert obj.attributes[1].description == "A list of members of the Group."
    assert obj.attributes[1].required is False
    assert obj.attributes[1].sub_attributes[0].name == "value"
    assert obj.attributes[1].sub_attributes[0].type == Attribute.Type.string
    assert obj.attributes[1].sub_attributes[0].multi_valued is False
    assert (
        obj.attributes[1].sub_attributes[0].description
        == "Identifier of the member of this Group."
    )
    assert obj.attributes[1].sub_attributes[0].required is False
    assert obj.attributes[1].sub_attributes[0].case_exact is False
    assert obj.attributes[1].sub_attributes[0].mutability == Mutability.immutable
    assert obj.attributes[1].sub_attributes[0].returned == Returned.default
    assert obj.attributes[1].sub_attributes[0].uniqueness == Uniqueness.none
    assert obj.attributes[1].sub_attributes[1].name == "$ref"
    assert obj.attributes[1].sub_attributes[1].type == Attribute.Type.reference
    assert obj.attributes[1].sub_attributes[1].reference_types == ["User", "Group"]
    assert obj.attributes[1].sub_attributes[1].multi_valued is False
    assert obj.attributes[1].sub_attributes[1].description == (
        "The URI corresponding to a SCIM resource " "that is a member of this Group."
    )
    assert obj.attributes[1].sub_attributes[1].required is False
    assert obj.attributes[1].sub_attributes[1].case_exact is False
    assert obj.attributes[1].sub_attributes[1].mutability == Mutability.immutable
    assert obj.attributes[1].sub_attributes[1].returned == Returned.default
    assert obj.attributes[1].sub_attributes[1].uniqueness == Uniqueness.none
    assert obj.attributes[1].sub_attributes[2].name == "type"
    assert obj.attributes[1].sub_attributes[2].type == Attribute.Type.string
    assert obj.attributes[1].sub_attributes[2].multi_valued is False
    assert obj.attributes[1].sub_attributes[2].description == (
        "A label indicating the type of resource, " "e.g., 'User' or 'Group'."
    )
    assert obj.attributes[1].sub_attributes[2].required is False
    assert obj.attributes[1].sub_attributes[2].case_exact is False
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
