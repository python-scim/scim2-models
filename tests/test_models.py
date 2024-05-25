import datetime

from pydantic import AnyUrl

from pydantic_scim2 import Address
from pydantic_scim2 import Attribute
from pydantic_scim2 import AuthenticationScheme
from pydantic_scim2 import BulkRequest
from pydantic_scim2 import BulkResponse
from pydantic_scim2 import Email
from pydantic_scim2 import Error
from pydantic_scim2 import Group
from pydantic_scim2 import Im
from pydantic_scim2 import ListResponse
from pydantic_scim2 import Mutability
from pydantic_scim2 import PatchOp
from pydantic_scim2 import PhoneNumber
from pydantic_scim2 import Photo
from pydantic_scim2 import ResourceType
from pydantic_scim2 import Returned
from pydantic_scim2 import Schema
from pydantic_scim2 import SearchRequest
from pydantic_scim2 import ServiceProviderConfiguration
from pydantic_scim2 import Uniqueness
from pydantic_scim2 import User


def test_minimal_user(minimal_user_payload):
    obj = User.model_validate(minimal_user_payload)

    assert obj.schemas == ["urn:ietf:params:scim:schemas:core:2.0:User"]
    assert obj.id == "2819c223-7f76-453a-919d-413861904646"
    assert obj.user_name == "bjensen@example.com"
    assert obj.meta.resource_type == "User"
    assert obj.meta.created == datetime.datetime(
        2010, 1, 23, 4, 56, 22, tzinfo=datetime.timezone.utc
    )
    assert obj.meta.last_modified == datetime.datetime(
        2011, 5, 13, 4, 42, 34, tzinfo=datetime.timezone.utc
    )
    assert obj.meta.version == 'W\\/"3694e05e9dff590"'
    assert (
        obj.meta.location
        == "https://example.com/v2/Users/2819c223-7f76-453a-919d-413861904646"
    )

    assert (
        obj.model_dump(
            exclude_none=True, exclude_unset=True, by_alias=True, mode="json"
        )
        == minimal_user_payload
    )


def test_full_user(full_user_payload):
    obj = User.model_validate(full_user_payload)

    assert obj.schemas == ["urn:ietf:params:scim:schemas:core:2.0:User"]
    assert obj.id == "2819c223-7f76-453a-919d-413861904646"
    assert obj.external_id == "701984"
    assert obj.user_name == "bjensen@example.com"
    assert obj.name
    assert obj.name.formatted == "Ms. Barbara J Jensen, III"
    assert obj.name.family_name == "Jensen"
    assert obj.name.given_name == "Barbara"
    assert obj.name.middle_name == "Jane"
    assert obj.name.honorific_prefix == "Ms."
    assert obj.name.honorific_suffix == "III"
    assert obj.display_name == "Babs Jensen"
    assert obj.nick_name == "Babs"
    assert obj.profile_url == AnyUrl("https://login.example.com/bjensen")
    assert obj.emails[0].value == "bjensen@example.com"
    assert obj.emails[0].type == Email.Type.work
    assert obj.emails[0].primary is True
    assert obj.emails[1].value == "babs@jensen.org"
    assert obj.emails[1].type == Email.Type.home
    assert obj.addresses[0].type == Address.Type.work
    assert obj.addresses[0].street_address == "100 Universal City Plaza"
    assert obj.addresses[0].locality == "Hollywood"
    assert obj.addresses[0].region == "CA"
    assert obj.addresses[0].postal_code == "91608"
    assert obj.addresses[0].country == "USA"
    assert (
        obj.addresses[0].formatted
        == "100 Universal City Plaza\nHollywood, CA 91608 USA"
    )
    assert obj.addresses[0].primary is True
    assert obj.addresses[1].type == Address.Type.home
    assert obj.addresses[1].street_address == "456 Hollywood Blvd"
    assert obj.addresses[1].locality == "Hollywood"
    assert obj.addresses[1].region == "CA"
    assert obj.addresses[1].postal_code == "91608"
    assert obj.addresses[1].country == "USA"
    assert obj.addresses[1].formatted == "456 Hollywood Blvd\nHollywood, CA 91608 USA"
    assert obj.phone_numbers[0].value == "555-555-5555"
    assert obj.phone_numbers[0].type == PhoneNumber.Type.work
    assert obj.phone_numbers[1].value == "555-555-4444"
    assert obj.phone_numbers[1].type == PhoneNumber.Type.mobile
    assert obj.ims[0].value == "someaimhandle"
    assert obj.ims[0].type == Im.Type.aim
    assert obj.photos[0].value == AnyUrl(
        "https://photos.example.com/profilephoto/72930000000Ccne/F"
    )
    assert obj.photos[0].type == Photo.Type.photo
    assert obj.photos[1].value == AnyUrl(
        "https://photos.example.com/profilephoto/72930000000Ccne/T"
    )
    assert obj.photos[1].type == Photo.Type.thumbnail
    assert obj.user_type == "Employee"
    assert obj.title == "Tour Guide"
    assert obj.preferred_language == "en-US"
    assert obj.locale == "en-US"
    assert obj.timezone == "America/Los_Angeles"
    assert obj.active is True
    assert obj.password == "t1meMa$heen"
    assert obj.groups[0].value == "e9e30dba-f08f-4109-8486-d5c6a331660a"
    assert obj.groups[0].ref == AnyUrl(
        "https://example.com/v2/Groups/e9e30dba-f08f-4109-8486-d5c6a331660a"
    )
    assert obj.groups[0].display == "Tour Guides"
    assert obj.groups[1].value == "fc348aa8-3835-40eb-a20b-c726e15c55b5"
    assert obj.groups[1].ref == AnyUrl(
        "https://example.com/v2/Groups/fc348aa8-3835-40eb-a20b-c726e15c55b5"
    )
    assert obj.groups[1].display == "Employees"
    assert obj.groups[2].value == "71ddacd2-a8e7-49b8-a5db-ae50d0a5bfd7"
    assert obj.groups[2].ref == AnyUrl(
        "https://example.com/v2/Groups/71ddacd2-a8e7-49b8-a5db-ae50d0a5bfd7"
    )
    assert obj.groups[2].display == "US Employees"
    assert obj.x509Certificates[0].value == (
        "MIIDQzCCAqygAwIBAgICEAAwDQYJKoZIhvcNAQEFBQAwTjELMAkGA1UEBhMCVVMx"
        "EzARBgNVBAgMCkNhbGlmb3JuaWExFDASBgNVBAoMC2V4YW1wbGUuY29tMRQwEgYD"
        "VQQDDAtleGFtcGxlLmNvbTAeFw0xMTEwMjIwNjI0MzFaFw0xMjEwMDQwNjI0MzFa"
        "MH8xCzAJBgNVBAYTAlVTMRMwEQYDVQQIDApDYWxpZm9ybmlhMRQwEgYDVQQKDAtl"
        "eGFtcGxlLmNvbTEhMB8GA1UEAwwYTXMuIEJhcmJhcmEgSiBKZW5zZW4gSUlJMSIw"
        "IAYJKoZIhvcNAQkBFhNiamVuc2VuQGV4YW1wbGUuY29tMIIBIjANBgkqhkiG9w0B"
        "AQEFAAOCAQ8AMIIBCgKCAQEA7Kr+Dcds/JQ5GwejJFcBIP682X3xpjis56AK02bc"
        "1FLgzdLI8auoR+cC9/Vrh5t66HkQIOdA4unHh0AaZ4xL5PhVbXIPMB5vAPKpzz5i"
        "PSi8xO8SL7I7SDhcBVJhqVqr3HgllEG6UClDdHO7nkLuwXq8HcISKkbT5WFTVfFZ"
        "zidPl8HZ7DhXkZIRtJwBweq4bvm3hM1Os7UQH05ZS6cVDgweKNwdLLrT51ikSQG3"
        "DYrl+ft781UQRIqxgwqCfXEuDiinPh0kkvIi5jivVu1Z9QiwlYEdRbLJ4zJQBmDr"
        "SGTMYn4lRc2HgHO4DqB/bnMVorHB0CC6AV1QoFK4GPe1LwIDAQABo3sweTAJBgNV"
        "HRMEAjAAMCwGCWCGSAGG+EIBDQQfFh1PcGVuU1NMIEdlbmVyYXRlZCBDZXJ0aWZp"
        "Y2F0ZTAdBgNVHQ4EFgQU8pD0U0vsZIsaA16lL8En8bx0F/gwHwYDVR0jBBgwFoAU"
        "dGeKitcaF7gnzsNwDx708kqaVt0wDQYJKoZIhvcNAQEFBQADgYEAA81SsFnOdYJt"
        "Ng5Tcq+/ByEDrBgnusx0jloUhByPMEVkoMZ3J7j1ZgI8rAbOkNngX8+pKfTiDz1R"
        "C4+dx8oU6Za+4NJXUjlL5CvV6BEYb1+QAEJwitTVvxB/A67g42/vzgAtoRUeDov1"
        "+GFiBZ+GNF/cAYKcMtGcrs2i97ZkJMo="
    )
    assert obj.meta.resource_type == "User"
    assert obj.meta.created == datetime.datetime(
        2010, 1, 23, 4, 56, 22, tzinfo=datetime.timezone.utc
    )
    assert obj.meta.last_modified == datetime.datetime(
        2011, 5, 13, 4, 42, 34, tzinfo=datetime.timezone.utc
    )
    assert obj.meta.version == 'W\\/"a330bc54f0671c9"'
    assert (
        obj.meta.location
        == "https://example.com/v2/Users/2819c223-7f76-453a-919d-413861904646"
    )

    assert (
        obj.model_dump(
            exclude_none=True, exclude_unset=True, by_alias=True, mode="json"
        )
        == full_user_payload
    )


def test_enterprise_user(enterprise_user_payload):
    obj = User.model_validate(enterprise_user_payload)

    assert obj.schemas == [
        "urn:ietf:params:scim:schemas:core:2.0:User",
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
    ]
    assert obj.id == "2819c223-7f76-453a-919d-413861904646"
    assert obj.external_id == "701984"
    assert obj.user_name == "bjensen@example.com"
    assert obj.name
    assert obj.name.formatted == "Ms. Barbara J Jensen, III"
    assert obj.name.family_name == "Jensen"
    assert obj.name.given_name == "Barbara"
    assert obj.name.middle_name == "Jane"
    assert obj.name.honorific_prefix == "Ms."
    assert obj.name.honorific_suffix == "III"
    assert obj.display_name == "Babs Jensen"
    assert obj.nick_name == "Babs"
    assert obj.profile_url == AnyUrl("https://login.example.com/bjensen")
    assert obj.emails[0].value == "bjensen@example.com"
    assert obj.emails[0].type == Email.Type.work
    assert obj.emails[0].primary is True
    assert obj.emails[1].value == "babs@jensen.org"
    assert obj.emails[1].type == Email.Type.home
    assert obj.addresses[0].type == Address.Type.work
    assert obj.addresses[0].street_address == "100 Universal City Plaza"
    assert obj.addresses[0].locality == "Hollywood"
    assert obj.addresses[0].region == "CA"
    assert obj.addresses[0].postal_code == "91608"
    assert obj.addresses[0].country == "USA"
    assert (
        obj.addresses[0].formatted
        == "100 Universal City Plaza\nHollywood, CA 91608 USA"
    )
    assert obj.addresses[0].primary is True
    assert obj.addresses[1].type == Address.Type.home
    assert obj.addresses[1].street_address == "456 Hollywood Blvd"
    assert obj.addresses[1].locality == "Hollywood"
    assert obj.addresses[1].region == "CA"
    assert obj.addresses[1].postal_code == "91608"
    assert obj.addresses[1].country == "USA"
    assert obj.addresses[1].formatted == "456 Hollywood Blvd\nHollywood, CA 91608 USA"
    assert obj.phone_numbers[0].value == "555-555-5555"
    assert obj.phone_numbers[0].type == PhoneNumber.Type.work
    assert obj.phone_numbers[1].value == "555-555-4444"
    assert obj.phone_numbers[1].type == PhoneNumber.Type.mobile
    assert obj.ims[0].value == "someaimhandle"
    assert obj.ims[0].type == Im.Type.aim
    assert obj.photos[0].value == AnyUrl(
        "https://photos.example.com/profilephoto/72930000000Ccne/F"
    )
    assert obj.photos[0].type == Photo.Type.photo
    assert obj.photos[1].value == AnyUrl(
        "https://photos.example.com/profilephoto/72930000000Ccne/T"
    )
    assert obj.photos[1].type == Photo.Type.thumbnail
    assert obj.user_type == "Employee"
    assert obj.title == "Tour Guide"
    assert obj.preferred_language == "en-US"
    assert obj.locale == "en-US"
    assert obj.timezone == "America/Los_Angeles"
    assert obj.active is True
    assert obj.password == "t1meMa$heen"
    assert obj.groups[0].value == "e9e30dba-f08f-4109-8486-d5c6a331660a"
    assert obj.groups[0].ref == AnyUrl(
        "https://example.com/v2/Groups/e9e30dba-f08f-4109-8486-d5c6a331660a"
    )
    assert obj.groups[0].display == "Tour Guides"
    assert obj.groups[1].value == "fc348aa8-3835-40eb-a20b-c726e15c55b5"
    assert obj.groups[1].ref == AnyUrl(
        "https://example.com/v2/Groups/fc348aa8-3835-40eb-a20b-c726e15c55b5"
    )
    assert obj.groups[1].display == "Employees"
    assert obj.groups[2].value == "71ddacd2-a8e7-49b8-a5db-ae50d0a5bfd7"
    assert obj.groups[2].ref == AnyUrl(
        "https://example.com/v2/Groups/71ddacd2-a8e7-49b8-a5db-ae50d0a5bfd7"
    )
    assert obj.groups[2].display == "US Employees"
    assert obj.x509Certificates[0].value == (
        "MIIDQzCCAqygAwIBAgICEAAwDQYJKoZIhvcNAQEFBQAwTjELMAkGA1UEBhMCVVMx"
        "EzARBgNVBAgMCkNhbGlmb3JuaWExFDASBgNVBAoMC2V4YW1wbGUuY29tMRQwEgYD"
        "VQQDDAtleGFtcGxlLmNvbTAeFw0xMTEwMjIwNjI0MzFaFw0xMjEwMDQwNjI0MzFa"
        "MH8xCzAJBgNVBAYTAlVTMRMwEQYDVQQIDApDYWxpZm9ybmlhMRQwEgYDVQQKDAtl"
        "eGFtcGxlLmNvbTEhMB8GA1UEAwwYTXMuIEJhcmJhcmEgSiBKZW5zZW4gSUlJMSIw"
        "IAYJKoZIhvcNAQkBFhNiamVuc2VuQGV4YW1wbGUuY29tMIIBIjANBgkqhkiG9w0B"
        "AQEFAAOCAQ8AMIIBCgKCAQEA7Kr+Dcds/JQ5GwejJFcBIP682X3xpjis56AK02bc"
        "1FLgzdLI8auoR+cC9/Vrh5t66HkQIOdA4unHh0AaZ4xL5PhVbXIPMB5vAPKpzz5i"
        "PSi8xO8SL7I7SDhcBVJhqVqr3HgllEG6UClDdHO7nkLuwXq8HcISKkbT5WFTVfFZ"
        "zidPl8HZ7DhXkZIRtJwBweq4bvm3hM1Os7UQH05ZS6cVDgweKNwdLLrT51ikSQG3"
        "DYrl+ft781UQRIqxgwqCfXEuDiinPh0kkvIi5jivVu1Z9QiwlYEdRbLJ4zJQBmDr"
        "SGTMYn4lRc2HgHO4DqB/bnMVorHB0CC6AV1QoFK4GPe1LwIDAQABo3sweTAJBgNV"
        "HRMEAjAAMCwGCWCGSAGG+EIBDQQfFh1PcGVuU1NMIEdlbmVyYXRlZCBDZXJ0aWZp"
        "Y2F0ZTAdBgNVHQ4EFgQU8pD0U0vsZIsaA16lL8En8bx0F/gwHwYDVR0jBBgwFoAU"
        "dGeKitcaF7gnzsNwDx708kqaVt0wDQYJKoZIhvcNAQEFBQADgYEAA81SsFnOdYJt"
        "Ng5Tcq+/ByEDrBgnusx0jloUhByPMEVkoMZ3J7j1ZgI8rAbOkNngX8+pKfTiDz1R"
        "C4+dx8oU6Za+4NJXUjlL5CvV6BEYb1+QAEJwitTVvxB/A67g42/vzgAtoRUeDov1"
        "+GFiBZ+GNF/cAYKcMtGcrs2i97ZkJMo="
    )
    assert obj.meta.resource_type == "User"
    assert obj.meta.created == datetime.datetime(
        2010, 1, 23, 4, 56, 22, tzinfo=datetime.timezone.utc
    )
    assert obj.meta.last_modified == datetime.datetime(
        2011, 5, 13, 4, 42, 34, tzinfo=datetime.timezone.utc
    )
    assert obj.meta.version == 'W\\/"3694e05e9dff591"'
    assert (
        obj.meta.location
        == "https://example.com/v2/Users/2819c223-7f76-453a-919d-413861904646"
    )

    # TODO: implement assertions for this
    # "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
    #     "employeeNumber": "701984",
    #     "costCenter": "4130",
    #     "organization": "Universal Studios",
    #     "division": "Theme Park",
    #     "department": "Tour Operations",
    #     "manager": {
    #         "value": "26118915-6090-4610-87e4-49d8ca9f808d",
    #         # TODO: relative URL are not supported by pydantic. Is this an error in the spec?
    #         #"$ref": "../Users/26118915-6090-4610-87e4-49d8ca9f808d",
    #         "$ref": "https://example.com/v2/Users/26118915-6090-4610-87e4-49d8ca9f808d",
    #         "displayName": "John Smith",
    #     },
    # },

    assert (
        obj.model_dump(
            exclude_none=True, exclude_unset=True, by_alias=True, mode="json"
        )
        == enterprise_user_payload
    )


def test_group(group_payload):
    obj = Group.model_validate(group_payload)

    assert obj.schemas == ["urn:ietf:params:scim:schemas:core:2.0:Group"]
    assert obj.id == "e9e30dba-f08f-4109-8486-d5c6a331660a"
    assert obj.display_name == "Tour Guides"
    assert obj.members[0].value == "2819c223-7f76-453a-919d-413861904646"
    assert obj.members[0].ref == AnyUrl(
        "https://example.com/v2/Users/2819c223-7f76-453a-919d-413861904646"
    )
    assert obj.members[0].display == "Babs Jensen"
    assert obj.members[1].value == "902c246b-6245-4190-8e05-00816be7344a"
    assert obj.members[1].ref == AnyUrl(
        "https://example.com/v2/Users/902c246b-6245-4190-8e05-00816be7344a"
    )
    assert obj.members[1].display == "Mandy Pepperidge"
    assert obj.meta.resource_type == "Group"
    assert obj.meta.created == datetime.datetime(
        2010, 1, 23, 4, 56, 22, tzinfo=datetime.timezone.utc
    )
    assert obj.meta.last_modified == datetime.datetime(
        2011, 5, 13, 4, 42, 34, tzinfo=datetime.timezone.utc
    )
    assert obj.meta.version == 'W\\/"3694e05e9dff592"'
    assert (
        obj.meta.location
        == "https://example.com/v2/Groups/e9e30dba-f08f-4109-8486-d5c6a331660a"
    )

    assert (
        obj.model_dump(
            exclude_none=True, exclude_unset=True, by_alias=True, mode="json"
        )
        == group_payload
    )


def test_service_provider_configuration(service_provider_configuration_payload):
    obj = ServiceProviderConfiguration.model_validate(
        service_provider_configuration_payload
    )

    assert obj.schemas == [
        "urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig"
    ]
    assert obj.documentation_uri == AnyUrl("http://example.com/help/scim.html")
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
    assert obj.authentication_schemes[0].spec_uri == AnyUrl(
        "http://www.rfc-editor.org/info/rfc6750"
    )
    assert obj.authentication_schemes[0].documentation_uri == AnyUrl(
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
    assert obj.authentication_schemes[1].spec_uri == AnyUrl(
        "http://www.rfc-editor.org/info/rfc2617"
    )
    assert obj.authentication_schemes[1].documentation_uri == AnyUrl(
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

    assert (
        obj.model_dump(
            exclude_none=True, exclude_unset=True, by_alias=True, mode="json"
        )
        == service_provider_configuration_payload
    )


def test_user_resource_type(user_resource_type_payload):
    obj = ResourceType.model_validate(user_resource_type_payload)

    assert obj.schemas == ["urn:ietf:params:scim:schemas:core:2.0:ResourceType"]
    assert obj.id == "User"
    assert obj.name == "User"
    assert obj.endpoint == "/Users"
    assert obj.description == "User Account"
    assert obj.schema_ == AnyUrl("urn:ietf:params:scim:schemas:core:2.0:User")
    assert obj.schema_extensions[0].schema_ == AnyUrl(
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"
    )
    assert obj.schema_extensions[0].required is True
    assert obj.meta.location == "https://example.com/v2/ResourceTypes/User"
    assert obj.meta.resource_type == "ResourceType"

    assert (
        obj.model_dump(
            exclude_none=True, exclude_unset=True, by_alias=True, mode="json"
        )
        == user_resource_type_payload
    )


def test_group_resource_type(group_resource_type_payload):
    obj = ResourceType.model_validate(group_resource_type_payload)
    assert obj.schemas == ["urn:ietf:params:scim:schemas:core:2.0:ResourceType"]
    assert obj.id == "Group"
    assert obj.name == "Group"
    assert obj.endpoint == "/Groups"
    assert obj.description == "Group"
    assert obj.schema_ == AnyUrl("urn:ietf:params:scim:schemas:core:2.0:Group")
    assert obj.meta.location == "https://example.com/v2/ResourceTypes/Group"
    assert obj.meta.resource_type == "ResourceType"

    assert (
        obj.model_dump(
            exclude_none=True, exclude_unset=True, by_alias=True, mode="json"
        )
        == group_resource_type_payload
    )


def test_user_schema(user_schema_payload):
    obj = Schema.model_validate(user_schema_payload)
    assert (
        obj.model_dump(
            exclude_none=True, exclude_unset=True, by_alias=True, mode="json"
        )
        == user_schema_payload
    )


def test_group_schema(group_schema_payload):
    obj = Schema.model_validate(group_schema_payload)

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

    assert (
        obj.model_dump(
            exclude_none=True, exclude_unset=True, by_alias=True, mode="json"
        )
        == group_schema_payload
    )


def test_enterprise_user_schema(enterprise_user_schema_payload):
    obj = Schema.model_validate(enterprise_user_schema_payload)
    assert (
        obj.model_dump(
            exclude_none=True, exclude_unset=True, by_alias=True, mode="json"
        )
        == enterprise_user_schema_payload
    )


def test_service_provider_configuration_schema(
    service_provider_configuration_schema_payload,
):
    obj = Schema.model_validate(service_provider_configuration_schema_payload)
    assert (
        obj.model_dump(
            exclude_none=True, exclude_unset=True, by_alias=True, mode="json"
        )
        == service_provider_configuration_schema_payload
    )


def test_resource_type_schema(
    resource_type_schema_payload,
):
    obj = Schema.model_validate(resource_type_schema_payload)
    assert (
        obj.model_dump(
            exclude_none=True, exclude_unset=True, by_alias=True, mode="json"
        )
        == resource_type_schema_payload
    )


def test_schema_schema(
    schema_schema_payload,
):
    obj = Schema.model_validate(schema_schema_payload)
    assert (
        obj.model_dump(
            exclude_none=True, exclude_unset=True, by_alias=True, mode="json"
        )
        == schema_schema_payload
    )


def test_post_query_list_response(
    post_query_list_response_payload,
):
    obj = ListResponse.model_validate(post_query_list_response_payload)
    assert (
        obj.model_dump(
            exclude_none=True, exclude_unset=True, by_alias=True, mode="json"
        )
        == post_query_list_response_payload
    )


def test_circular_reference_list_response(
    circular_reference_list_response_payload,
):
    obj = ListResponse[Group].model_validate(circular_reference_list_response_payload)
    assert (
        obj.model_dump(
            exclude_none=True, exclude_unset=True, by_alias=True, mode="json"
        )
        == circular_reference_list_response_payload
    )


def test_patch_add_members(
    patch_add_members_payload,
):
    obj = PatchOp.model_validate(patch_add_members_payload)
    assert (
        obj.model_dump(
            exclude_none=True, exclude_unset=True, by_alias=True, mode="json"
        )
        == patch_add_members_payload
    )


def test_patch_add_emails(
    patch_add_emails_payload,
):
    obj = PatchOp.model_validate(patch_add_emails_payload)
    assert (
        obj.model_dump(
            exclude_none=True, exclude_unset=True, by_alias=True, mode="json"
        )
        == patch_add_emails_payload
    )


def test_patch_remove_one_member(
    patch_remove_one_member_payload,
):
    obj = PatchOp.model_validate(patch_remove_one_member_payload)
    assert (
        obj.model_dump(
            exclude_none=True, exclude_unset=True, by_alias=True, mode="json"
        )
        == patch_remove_one_member_payload
    )


def test_patch_remove_all_members(
    patch_remove_all_members_payload,
):
    obj = PatchOp.model_validate(patch_remove_all_members_payload)
    assert (
        obj.model_dump(
            exclude_none=True, exclude_unset=True, by_alias=True, mode="json"
        )
        == patch_remove_all_members_payload
    )


def test_patch_remove_multi_complex_value(
    patch_remove_multi_complex_value_payload,
):
    obj = PatchOp.model_validate(patch_remove_multi_complex_value_payload)
    assert (
        obj.model_dump(
            exclude_none=True, exclude_unset=True, by_alias=True, mode="json"
        )
        == patch_remove_multi_complex_value_payload
    )


def test_patch_remove_and_add_one_member(
    patch_remove_and_add_one_member_payload,
):
    obj = PatchOp.model_validate(patch_remove_and_add_one_member_payload)
    assert (
        obj.model_dump(
            exclude_none=True, exclude_unset=True, by_alias=True, mode="json"
        )
        == patch_remove_and_add_one_member_payload
    )


def test_patch_replace_all_members(
    patch_replace_all_members_payload,
):
    obj = PatchOp.model_validate(patch_replace_all_members_payload)
    assert (
        obj.model_dump(
            exclude_none=True, exclude_unset=True, by_alias=True, mode="json"
        )
        == patch_replace_all_members_payload
    )


def test_patch_replace_user_work_address(
    patch_replace_user_work_address_payload,
):
    obj = PatchOp.model_validate(patch_replace_user_work_address_payload)
    assert (
        obj.model_dump(
            exclude_none=True, exclude_unset=True, by_alias=True, mode="json"
        )
        == patch_replace_user_work_address_payload
    )


def test_patch_replace_street_address(
    patch_replace_street_address_payload,
):
    obj = PatchOp.model_validate(patch_replace_street_address_payload)
    assert (
        obj.model_dump(
            exclude_none=True, exclude_unset=True, by_alias=True, mode="json"
        )
        == patch_replace_street_address_payload
    )


def test_patch_replace_all_email_values(
    patch_replace_all_email_values_payload,
):
    obj = PatchOp.model_validate(patch_replace_all_email_values_payload)
    assert (
        obj.model_dump(
            exclude_none=True, exclude_unset=True, by_alias=True, mode="json"
        )
        == patch_replace_all_email_values_payload
    )


def test_error_not_found(
    error_not_found_payload,
):
    obj = Error.model_validate(error_not_found_payload)
    assert (
        obj.model_dump(
            exclude_none=True, exclude_unset=True, by_alias=True, mode="json"
        )
        == error_not_found_payload
    )


def test_bulk_request_circular_conflict(
    bulk_request_circular_conflict_payload,
):
    obj = BulkRequest.model_validate(bulk_request_circular_conflict_payload)
    assert (
        obj.model_dump(
            exclude_none=True, exclude_unset=True, by_alias=True, mode="json"
        )
        == bulk_request_circular_conflict_payload
    )


def test_bulk_request_temporary_identifier(
    bulk_request_temporary_identifier_payload,
):
    obj = BulkRequest.model_validate(bulk_request_temporary_identifier_payload)
    assert (
        obj.model_dump(
            exclude_none=True, exclude_unset=True, by_alias=True, mode="json"
        )
        == bulk_request_temporary_identifier_payload
    )


def test_bulk_response_temporary_identifier(
    bulk_response_temporary_identifier_payload,
):
    obj = BulkResponse.model_validate(bulk_response_temporary_identifier_payload)
    assert (
        obj.model_dump(
            exclude_none=True, exclude_unset=True, by_alias=True, mode="json"
        )
        == bulk_response_temporary_identifier_payload
    )


def test_bulk_request_enterprise_user(
    bulk_request_enterprise_user_payload,
):
    obj = BulkRequest.model_validate(bulk_request_enterprise_user_payload)
    assert (
        obj.model_dump(
            exclude_none=True, exclude_unset=True, by_alias=True, mode="json"
        )
        == bulk_request_enterprise_user_payload
    )


def test_error_invalid_syntax(
    error_invalid_syntax_payload,
):
    obj = Error.model_validate(error_invalid_syntax_payload)
    assert (
        obj.model_dump(
            exclude_none=True, exclude_unset=True, by_alias=True, mode="json"
        )
        == error_invalid_syntax_payload
    )


def test_bulk_request_multiple_operations(
    bulk_request_multiple_operations_payload,
):
    obj = BulkRequest.model_validate(bulk_request_multiple_operations_payload)
    assert (
        obj.model_dump(
            exclude_none=True, exclude_unset=True, by_alias=True, mode="json"
        )
        == bulk_request_multiple_operations_payload
    )


def test_bulk_response_multiple_operations(
    bulk_response_multiple_operations_payload,
):
    obj = BulkResponse.model_validate(bulk_response_multiple_operations_payload)
    assert (
        obj.model_dump(
            exclude_none=True, exclude_unset=True, by_alias=True, mode="json"
        )
        == bulk_response_multiple_operations_payload
    )


def test_bulk_response_error_invalid_syntax(
    bulk_response_error_invalid_syntax_payload,
):
    obj = BulkResponse.model_validate(bulk_response_error_invalid_syntax_payload)
    assert (
        obj.model_dump(
            exclude_none=True, exclude_unset=True, by_alias=True, mode="json"
        )
        == bulk_response_error_invalid_syntax_payload
    )


def test_bulk_response_multiple_errors(
    bulk_response_multiple_errors_payload,
):
    obj = BulkResponse.model_validate(bulk_response_multiple_errors_payload)
    assert (
        obj.model_dump(
            exclude_none=True, exclude_unset=True, by_alias=True, mode="json"
        )
        == bulk_response_multiple_errors_payload
    )


def test_error_payload_too_large(
    error_payload_too_large_payload,
):
    obj = Error.model_validate(error_payload_too_large_payload)
    assert (
        obj.model_dump(
            exclude_none=True, exclude_unset=True, by_alias=True, mode="json"
        )
        == error_payload_too_large_payload
    )


def test_error_bad_request(
    error_bad_request_payload,
):
    obj = Error.model_validate(error_bad_request_payload)
    assert (
        obj.model_dump(
            exclude_none=True, exclude_unset=True, by_alias=True, mode="json"
        )
        == error_bad_request_payload
    )


def test_search_request(
    search_request_payload,
):
    obj = SearchRequest.model_validate(search_request_payload)
    assert (
        obj.model_dump(
            exclude_none=True, exclude_unset=True, by_alias=True, mode="json"
        )
        == search_request_payload
    )
