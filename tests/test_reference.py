"""Test Reference type functionality."""

from typing import Annotated
from typing import Any
from typing import Literal
from typing import Union

import pytest

from scim2_models import URI
from scim2_models import External
from scim2_models import ExternalReference
from scim2_models import Reference
from scim2_models import URIReference
from scim2_models.annotations import Required
from scim2_models.base import BaseModel


class User:
    """Dummy class for testing forward references."""


class Group:
    """Dummy class for testing forward references."""


class ReferenceTestModel(BaseModel):
    """Test model with Reference fields."""

    schemas: Annotated[list[str], Required.true] = ["urn:example:test"]
    uri_ref: Reference[URI] | None = None
    ext_ref: Reference[External] | None = None
    resource_ref: Reference["User"] | None = None
    multi_ref: Reference[Union["User", "Group"]] | None = None


def test_reference_uri_string_assignment():
    """Test that URI references accept string values."""
    model = ReferenceTestModel(uri_ref="https://example.com")
    assert model.uri_ref == "https://example.com"
    assert isinstance(model.uri_ref, str)


def test_reference_uri_constructor():
    """Test that URI references accept Reference[URI] constructor."""
    model = ReferenceTestModel(uri_ref=Reference[URI]("https://example.com"))
    assert model.uri_ref == "https://example.com"
    assert isinstance(model.uri_ref, str)


def test_reference_external_string_assignment():
    """Test that external references accept string values."""
    model = ReferenceTestModel(ext_ref="https://external.com")
    assert model.ext_ref == "https://external.com"
    assert isinstance(model.ext_ref, str)


def test_reference_external_constructor():
    """Test that external references accept Reference[External] constructor."""
    model = ReferenceTestModel(ext_ref=Reference[External]("https://external.com"))
    assert model.ext_ref == "https://external.com"
    assert isinstance(model.ext_ref, str)


def test_reference_plain_constructor():
    """Test that references accept plain Reference constructor."""
    model = ReferenceTestModel(uri_ref=Reference("https://example.com"))
    assert model.uri_ref == "https://example.com"
    assert isinstance(model.uri_ref, str)


def test_reference_serialization():
    """Test that Reference instances serialize correctly."""
    ref = Reference[URI]("https://example.com")
    model = ReferenceTestModel(uri_ref=ref)

    dumped = model.model_dump()
    assert dumped["uri_ref"] == "https://example.com"


def test_reference_validation_error():
    """Test that invalid values raise validation errors."""
    with pytest.raises(ValueError):
        ReferenceTestModel(uri_ref=123)


def test_reference_string_behavior():
    """Test that Reference behaves like a string."""
    ref = Reference[URI]("https://example.com")
    assert str(ref) == "https://example.com"
    assert ref == "https://example.com"
    assert ref.startswith("https://")


def test_reference_resource_type():
    """Test Reference with resource type string."""
    model = ReferenceTestModel(resource_ref="https://example.com/Users/123")
    assert model.resource_ref == "https://example.com/Users/123"


def test_reference_union_types():
    """Test Reference with union of resource types."""
    model = ReferenceTestModel(multi_ref="https://example.com/Groups/456")
    assert model.multi_ref == "https://example.com/Groups/456"


def test_reference_get_scim_reference_types_external():
    """Test get_scim_reference_types returns 'external'."""
    ref_type = Reference[External]
    assert ref_type.get_scim_reference_types() == ["external"]


def test_reference_get_scim_reference_types_uri():
    """Test get_scim_reference_types returns 'uri'."""
    ref_type = Reference[URI]
    assert ref_type.get_scim_reference_types() == ["uri"]


def test_reference_get_scim_reference_types_resource():
    """Test get_scim_reference_types returns resource name."""
    ref_type = Reference["User"]
    assert ref_type.get_scim_reference_types() == ["User"]


def test_reference_get_scim_reference_types_union():
    """Test get_scim_reference_types returns multiple types."""
    ref_type = Reference[Union["User", "Group"]]
    assert ref_type.get_scim_reference_types() == ["User", "Group"]


def test_reference_uri_validation_valid():
    """Test URI validation accepts valid URIs."""
    model = ReferenceTestModel(uri_ref="https://example.com/path")
    assert model.uri_ref == "https://example.com/path"


def test_reference_uri_validation_relative():
    """Test URI validation accepts relative URIs."""
    model = ReferenceTestModel(uri_ref="/Users/123")
    assert model.uri_ref == "/Users/123"


def test_reference_uri_validation_invalid():
    """Test URI validation rejects invalid URIs."""
    with pytest.raises(ValueError, match="Invalid URI"):
        ReferenceTestModel(uri_ref="not a valid uri")


def test_reference_class_caching():
    """Test that Reference subclasses are cached."""
    ref1 = Reference[External]
    ref2 = Reference[External]
    assert ref1 is ref2


def test_reference_class_name():
    """Test that Reference subclass has descriptive name."""
    ref_type = Reference[Union["User", "Group"]]
    assert ref_type.__name__ == "Reference[User | Group]"


# Deprecation warnings tests


def test_external_reference_deprecation_warning():
    """Test that ExternalReference emits a deprecation warning."""
    with pytest.warns(DeprecationWarning, match="Reference\\[ExternalReference\\]"):
        Reference[ExternalReference]


def test_uri_reference_deprecation_warning():
    """Test that URIReference emits a deprecation warning."""
    with pytest.warns(DeprecationWarning, match="Reference\\[URIReference\\]"):
        Reference[URIReference]


def test_literal_reference_deprecation_warning():
    """Test that Literal type parameter emits a deprecation warning."""
    with pytest.warns(DeprecationWarning, match='Reference\\[Literal\\["User"\\]\\]'):
        Reference[Literal["User"]]


def test_deprecated_external_reference_still_works():
    """Test that deprecated ExternalReference still produces valid Reference."""
    with pytest.warns(DeprecationWarning):
        ref_type = Reference[ExternalReference]

    assert ref_type.get_scim_reference_types() == ["external"]


def test_deprecated_uri_reference_still_works():
    """Test that deprecated URIReference still produces valid Reference."""
    with pytest.warns(DeprecationWarning):
        ref_type = Reference[URIReference]

    assert ref_type.get_scim_reference_types() == ["uri"]


def test_deprecated_literal_still_works():
    """Test that deprecated Literal syntax still produces valid Reference."""
    with pytest.warns(DeprecationWarning):
        ref_type = Reference[Literal["User"]]

    assert ref_type.get_scim_reference_types() == ["User"]


def test_reference_any_type():
    """Test that Reference[Any] is treated as URI reference."""
    ref_type = Reference[Any]
    assert ref_type.get_scim_reference_types() == ["uri"]


def test_reference_invalid_type_raises_error():
    """Test that invalid type parameter raises TypeError."""
    with pytest.raises(TypeError, match="Invalid reference type"):
        Reference[123]


def test_reference_json_schema_generation():
    """Test that models with Reference fields can generate JSON Schema."""
    schema = ReferenceTestModel.model_json_schema()
    assert schema["type"] == "object"
    assert "uriref" in schema["properties"]
    assert "extref" in schema["properties"]
    assert "resourceref" in schema["properties"]
    assert "multiref" in schema["properties"]
