import datetime

from scim2_models import AuthenticationScheme
from scim2_models import Reference
from scim2_models import ServiceProviderConfig


def test_service_provider_configuration(load_sample):
    """Test creating an object representing the SPC example found in RFC7643."""
    payload = load_sample("rfc7643-8.5-service_provider_configuration.json")
    obj = ServiceProviderConfig.model_validate(payload)

    assert obj.schemas == [
        "urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig"
    ]
    assert obj.documentation_uri == Reference("http://example.com/help/scim.html")
    assert obj.patch.supported is True
    assert obj.bulk.supported is True
    assert obj.bulk.max_operations == 1000
    assert obj.bulk.max_payload_size == 1048576
    assert obj.filter.supported is True
    assert obj.filter.max_results == 200
    assert obj.change_password.supported is True
    assert obj.sort.supported is True
    assert obj.etag.supported is True
    assert obj.authentication_schemes[0].name == "OAuth Bearer Token"
    assert (
        obj.authentication_schemes[0].description
        == "Authentication scheme using the OAuth Bearer Token Standard"
    )
    assert obj.authentication_schemes[0].spec_uri == Reference(
        "http://www.rfc-editor.org/info/rfc6750"
    )
    assert obj.authentication_schemes[0].documentation_uri == Reference(
        "http://example.com/help/oauth.html"
    )
    assert (
        obj.authentication_schemes[0].type == AuthenticationScheme.Type.oauthbearertoken
    )
    assert obj.authentication_schemes[0].primary is True

    assert obj.authentication_schemes[1].name == "HTTP Basic"
    assert (
        obj.authentication_schemes[1].description
        == "Authentication scheme using the HTTP Basic Standard"
    )
    assert obj.authentication_schemes[1].spec_uri == Reference(
        "http://www.rfc-editor.org/info/rfc2617"
    )
    assert obj.authentication_schemes[1].documentation_uri == Reference(
        "http://example.com/help/httpBasic.html"
    )
    assert obj.authentication_schemes[1].type == AuthenticationScheme.Type.httpbasic
    assert obj.meta.location == "https://example.com/v2/ServiceProviderConfig"
    assert obj.meta.resource_type == "ServiceProviderConfig"
    assert obj.meta.created == datetime.datetime(
        2010, 1, 23, 4, 56, 22, tzinfo=datetime.timezone.utc
    )
    assert obj.meta.last_modified == datetime.datetime(
        2011, 5, 13, 4, 42, 34, tzinfo=datetime.timezone.utc
    )
    assert obj.meta.version == 'W\\/"3694e05e9dff594"'

    assert obj.model_dump() == payload


def test_authentication_scheme_type_is_case_insensitive():
    """Test that canonical authentication scheme types are read whatever their case is."""
    scheme = AuthenticationScheme.model_validate(
        {
            "type": "HttpBasic",
            "name": "HTTP Basic",
            "description": "Authentication scheme using the HTTP Basic Standard",
        }
    )
    assert scheme.type is AuthenticationScheme.Type.httpbasic
    assert scheme.model_dump()["type"] == "httpbasic"


def test_authentication_scheme_type_accepts_unknown_schemes():
    """Test that authentication schemes beyond those defined by RFC7643 are read."""
    scheme = AuthenticationScheme.model_validate(
        {
            "type": "oauth2bearer",
            "name": "OAuth 2 Bearer Token",
            "description": "Authentication scheme using an OAuth 2 bearer token",
        }
    )
    assert str(scheme.type) == "oauth2bearer"
    assert scheme.model_dump()["type"] == "oauth2bearer"
