"""Test Reference constructor functionality."""

from typing import Annotated
from typing import Optional

import pytest

from scim2_models.annotations import Required
from scim2_models.base import BaseModel
from scim2_models.reference import ExternalReference
from scim2_models.reference import Reference
from scim2_models.reference import URIReference


class ReferenceTestModel(BaseModel):
    """Test model with Reference fields."""

    schemas: Annotated[list[str], Required.true] = ["urn:example:test"]
    uri_ref: Optional[Reference[URIReference]] = None
    ext_ref: Optional[Reference[ExternalReference]] = None


def test_reference_uri_string_assignment():
    """Test that URI references accept string values."""
    model = ReferenceTestModel(uri_ref="https://example.com")
    assert model.uri_ref == "https://example.com"
    assert isinstance(model.uri_ref, str)


def test_reference_uri_constructor():
    """Test that URI references accept Reference[URIReference] constructor."""
    model = ReferenceTestModel(uri_ref=Reference[URIReference]("https://example.com"))
    assert model.uri_ref == "https://example.com"
    assert isinstance(model.uri_ref, str)


def test_reference_external_string_assignment():
    """Test that external references accept string values."""
    model = ReferenceTestModel(ext_ref="https://external.com")
    assert model.ext_ref == "https://external.com"
    assert isinstance(model.ext_ref, str)


def test_reference_external_constructor():
    """Test that external references accept Reference[ExternalReference] constructor."""
    model = ReferenceTestModel(
        ext_ref=Reference[ExternalReference]("https://external.com")
    )
    assert model.ext_ref == "https://external.com"
    assert isinstance(model.ext_ref, str)


def test_reference_plain_constructor():
    """Test that references accept plain Reference constructor."""
    model = ReferenceTestModel(uri_ref=Reference("https://example.com"))
    assert model.uri_ref == "https://example.com"
    assert isinstance(model.uri_ref, str)


def test_reference_serialization():
    """Test that Reference instances serialize correctly."""
    ref = Reference[URIReference]("https://example.com")
    model = ReferenceTestModel(uri_ref=ref)

    dumped = model.model_dump()
    assert dumped["uri_ref"] == "https://example.com"


def test_reference_validation_error():
    """Test that invalid values still raise validation errors."""
    with pytest.raises(ValueError):
        ReferenceTestModel(uri_ref=123)  # Invalid type should still fail


def test_reference_userstring_behavior():
    """Test that Reference still behaves like UserString."""
    ref = Reference[URIReference]("https://example.com")
    assert str(ref) == "https://example.com"
    assert ref == "https://example.com"
    assert ref.startswith("https://")
