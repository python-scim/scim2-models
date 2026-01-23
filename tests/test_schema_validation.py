"""Tests for schema validation using __schema__ classvar."""

import pytest
from pydantic import ValidationError

from scim2_models.base import BaseModel
from scim2_models.context import Context
from scim2_models.path import URN
from scim2_models.resources.enterprise_user import EnterpriseUser
from scim2_models.resources.resource import Extension
from scim2_models.resources.resource import Resource
from scim2_models.resources.user import User


def test_validation_missing_base_schema():
    """Validation fails when base schema is missing from schemas."""
    with pytest.raises(ValidationError, match="schemas must contain"):
        User.model_validate(
            {"schemas": ["wrong:schema"], "userName": "foo"},
            context={"scim": Context.RESOURCE_CREATION_REQUEST},
        )


def test_validation_unknown_extension_schema():
    """Validation fails when unknown extension schema is provided."""
    with pytest.raises(ValidationError, match="Unknown extension"):
        User.model_validate(
            {
                "schemas": [
                    "urn:ietf:params:scim:schemas:core:2.0:User",
                    "urn:unknown:extension",
                ],
                "userName": "foo",
            },
            context={"scim": Context.RESOURCE_CREATION_REQUEST},
        )


def test_validation_valid_extension_schema():
    """Validation succeeds with valid extension schema."""
    user = User[EnterpriseUser].model_validate(
        {
            "schemas": [
                "urn:ietf:params:scim:schemas:core:2.0:User",
                "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
            ],
            "userName": "foo",
        },
        context={"scim": Context.RESOURCE_CREATION_REQUEST},
    )
    assert len(user.schemas) == 2


def test_schemas_auto_populated():
    """Schemas is auto-populated from __schema__ when not provided."""
    user = User(user_name="foo")
    assert user.schemas == ["urn:ietf:params:scim:schemas:core:2.0:User"]


def test_deprecation_warning_old_style():
    """DeprecationWarning is raised for old-style schema definition."""
    with pytest.warns(DeprecationWarning, match="removed in version 0.7"):

        class OldStyleResource(Resource):
            schemas: list[str] = ["urn:test:old"]


def test_no_validation_without_context():
    """No schema validation without SCIM context."""
    user = User.model_validate({"schemas": ["wrong:schema"], "userName": "foo"})
    assert user.schemas == ["wrong:schema"]


def test_no_validation_with_default_context():
    """No schema validation with DEFAULT context."""
    user = User.model_validate(
        {"schemas": ["wrong:schema"], "userName": "foo"},
        context={"scim": Context.DEFAULT},
    )
    assert user.schemas == ["wrong:schema"]


def test_schema_classvar_defined():
    """Resources have __schema__ classvar with correct URN."""
    assert User.__schema__ == URN("urn:ietf:params:scim:schemas:core:2.0:User")
    assert EnterpriseUser.__schema__ == URN(
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"
    )


def test_dynamic_class_inherits_schema():
    """Dynamically created resource classes inherit __schema__ from parent."""

    class TestExtension(Extension):
        __schema__ = URN("urn:test:extension")

    UserWithExt = User[TestExtension]
    assert UserWithExt.__schema__ == User.__schema__


def test_extension_schema_validation_multiple_valid():
    """Validation succeeds with multiple valid extension schemas."""

    class Ext1(Extension):
        __schema__ = URN("urn:test:ext1")

    class Ext2(Extension):
        __schema__ = URN("urn:test:ext2")

    UserWithExts = User[Ext1 | Ext2]
    user = UserWithExts.model_validate(
        {
            "schemas": [
                "urn:ietf:params:scim:schemas:core:2.0:User",
                "urn:test:ext1",
                "urn:test:ext2",
            ],
            "userName": "foo",
        },
        context={"scim": Context.RESOURCE_CREATION_REQUEST},
    )
    assert len(user.schemas) == 3


def test_extension_schema_validation_partial():
    """Validation succeeds when only some extension schemas are provided."""

    class Ext1(Extension):
        __schema__ = URN("urn:test:ext1")

    class Ext2(Extension):
        __schema__ = URN("urn:test:ext2")

    UserWithExts = User[Ext1 | Ext2]
    user = UserWithExts.model_validate(
        {
            "schemas": [
                "urn:ietf:params:scim:schemas:core:2.0:User",
                "urn:test:ext1",
            ],
            "userName": "foo",
        },
        context={"scim": Context.RESOURCE_CREATION_REQUEST},
    )
    assert len(user.schemas) == 2


def test_extension_schema_validation_rejects_unknown_with_valid():
    """Validation fails when unknown schema is mixed with valid extensions."""

    class TestExt(Extension):
        __schema__ = URN("urn:test:ext")

    UserWithExt = User[TestExt]
    with pytest.raises(ValidationError, match="Unknown extension"):
        UserWithExt.model_validate(
            {
                "schemas": [
                    "urn:ietf:params:scim:schemas:core:2.0:User",
                    "urn:test:ext",
                    "urn:unknown:bad",
                ],
                "userName": "foo",
            },
            context={"scim": Context.RESOURCE_CREATION_REQUEST},
        )


def test_get_attribute_urn_without_schema():
    """get_attribute_urn returns field name when model has no __schema__."""

    class ModelWithoutSchema(BaseModel):
        foo: str | None = None

    model = ModelWithoutSchema(foo="bar")
    assert model.get_attribute_urn("foo") == "foo"


def test_from_resource_without_schema():
    """from_resource raises ValueError when resource has no __schema__."""
    from scim2_models.resources.resource_type import ResourceType

    class NoSchemaResource(Resource):
        pass

    NoSchemaResource.__schema__ = None  # type: ignore[assignment]

    with pytest.raises(ValueError, match="has no __schema__ defined"):
        ResourceType.from_resource(NoSchemaResource)
