import datetime

from pydantic import AnyUrl

from pydantic_scim2 import AddressKind
from pydantic_scim2 import EmailKind
from pydantic_scim2 import ImKind
from pydantic_scim2 import PhoneNumberKind
from pydantic_scim2 import PhotoKind
from pydantic_scim2 import User


def test_minimal_user(minimal_user_payload):
    obj = User.model_validate(minimal_user_payload)

    assert obj.schemas == ["urn:ietf:params:scim:schemas:core:2.0:User"]
    assert obj.id == "2819c223-7f76-453a-919d-413861904646"
    assert obj.userName == "bjensen@example.com"
    assert obj.meta.resourceType == "User"
    assert obj.meta.created == datetime.datetime(
        2010, 1, 23, 4, 56, 22, tzinfo=datetime.timezone.utc
    )
    assert obj.meta.lastModified == datetime.datetime(
        2011, 5, 13, 4, 42, 34, tzinfo=datetime.timezone.utc
    )
    assert obj.meta.version == 'W\\/"3694e05e9dff590"'
    assert (
        obj.meta.location
        == "https://example.com/v2/Users/2819c223-7f76-453a-919d-413861904646"
    )


def test_full_user(full_user_payload):
    obj = User.model_validate(full_user_payload)

    assert obj.schemas == ["urn:ietf:params:scim:schemas:core:2.0:User"]
    assert obj.id == "2819c223-7f76-453a-919d-413861904646"
    assert obj.externalId == "701984"
    assert obj.userName == "bjensen@example.com"
    assert obj.name
    assert obj.name.formatted == "Ms. Barbara J Jensen, III"
    assert obj.name.familyName == "Jensen"
    assert obj.name.givenName == "Barbara"
    assert obj.name.middleName == "Jane"
    assert obj.name.honorificPrefix == "Ms."
    assert obj.name.honorificSuffix == "III"
    assert obj.displayName == "Babs Jensen"
    assert obj.nickName == "Babs"
    assert obj.profileUrl == AnyUrl("https://login.example.com/bjensen")
    assert obj.emails[0].value == "bjensen@example.com"
    assert obj.emails[0].type == EmailKind.work
    assert obj.emails[0].primary is True
    assert obj.emails[1].value == "babs@jensen.org"
    assert obj.emails[1].type == EmailKind.home
    assert obj.addresses[0].type == AddressKind.work
    assert obj.addresses[0].streetAddress == "100 Universal City Plaza"
    assert obj.addresses[0].locality == "Hollywood"
    assert obj.addresses[0].region == "CA"
    assert obj.addresses[0].postalCode == "91608"
    assert obj.addresses[0].country == "USA"
    assert (
        obj.addresses[0].formatted
        == "100 Universal City Plaza\nHollywood, CA 91608 USA"
    )
    assert obj.addresses[0].primary is True
    assert obj.addresses[1].type == AddressKind.home
    assert obj.addresses[1].streetAddress == "456 Hollywood Blvd"
    assert obj.addresses[1].locality == "Hollywood"
    assert obj.addresses[1].region == "CA"
    assert obj.addresses[1].postalCode == "91608"
    assert obj.addresses[1].country == "USA"
    assert obj.addresses[1].formatted == "456 Hollywood Blvd\nHollywood, CA 91608 USA"
    assert obj.phoneNumbers[0].value == "555-555-5555"
    assert obj.phoneNumbers[0].type == PhoneNumberKind.work
    assert obj.phoneNumbers[1].value == "555-555-4444"
    assert obj.phoneNumbers[1].type == PhoneNumberKind.mobile
    assert obj.ims[0].value == "someaimhandle"
    assert obj.ims[0].type == ImKind.aim
    assert obj.photos[0].value == AnyUrl(
        "https://photos.example.com/profilephoto/72930000000Ccne/F"
    )
    assert obj.photos[0].type == PhotoKind.photo
    assert obj.photos[1].value == AnyUrl(
        "https://photos.example.com/profilephoto/72930000000Ccne/T"
    )
    assert obj.photos[1].type == PhotoKind.thumbnail
    assert obj.userType == "Employee"
    assert obj.title == "Tour Guide"
    assert obj.preferredLanguage == "en-US"
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
    assert obj.meta.resourceType == "User"
    assert obj.meta.created == datetime.datetime(
        2010, 1, 23, 4, 56, 22, tzinfo=datetime.timezone.utc
    )
    assert obj.meta.lastModified == datetime.datetime(
        2011, 5, 13, 4, 42, 34, tzinfo=datetime.timezone.utc
    )
    assert obj.meta.version == 'W\\/"a330bc54f0671c9"'
    assert (
        obj.meta.location
        == "https://example.com/v2/Users/2819c223-7f76-453a-919d-413861904646"
    )
