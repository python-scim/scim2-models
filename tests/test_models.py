import datetime

from pydantic import AnyUrl

from pydantic_scim2 import Address
from pydantic_scim2 import AddressKind
from pydantic_scim2 import Email
from pydantic_scim2 import EmailKind
from pydantic_scim2 import GroupMember
from pydantic_scim2 import Im
from pydantic_scim2 import ImKind
from pydantic_scim2 import Meta
from pydantic_scim2 import Name
from pydantic_scim2 import PhoneNumber
from pydantic_scim2 import PhoneNumberKind
from pydantic_scim2 import Photo
from pydantic_scim2 import PhotoKind
from pydantic_scim2 import User
from pydantic_scim2 import X509Certificate


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
    assert obj.name == Name(
        formatted="Ms. Barbara J Jensen, III",
        familyName="Jensen",
        givenName="Barbara",
        middleName="Jane",
        honorificPrefix="Ms.",
        honorificSuffix="III",
    )
    assert obj.displayName == "Babs Jensen"
    assert obj.nickName == "Babs"
    assert obj.profileUrl == AnyUrl("https://login.example.com/bjensen")
    assert obj.emails == [
        Email(value="bjensen@example.com", type=EmailKind.work, primary=True),
        Email(value="babs@jensen.org", type=EmailKind.home),
    ]
    assert obj.addresses == [
        Address(
            type=AddressKind.work,
            streetAddress="100 Universal City Plaza",
            locality="Hollywood",
            region="CA",
            postalCode="91608",
            country="USA",
            formatted="100 Universal City Plaza\nHollywood, CA 91608 USA",
            primary=True,
        ),
        Address(
            type=AddressKind.home,
            streetAddress="456 Hollywood Blvd",
            locality="Hollywood",
            region="CA",
            postalCode="91608",
            country="USA",
            formatted="456 Hollywood Blvd\nHollywood, CA 91608 USA",
        ),
    ]
    assert obj.phoneNumbers == [
        PhoneNumber(value="555-555-5555", type=PhoneNumberKind.work),
        PhoneNumber(value="555-555-4444", type=PhoneNumberKind.mobile),
    ]
    assert obj.ims == [Im(value="someaimhandle", type=ImKind.aim)]
    assert obj.photos == [
        Photo(
            value="https://photos.example.com/profilephoto/72930000000Ccne/F",
            type=PhotoKind.photo,
        ),
        Photo(
            value="https://photos.example.com/profilephoto/72930000000Ccne/T",
            type=PhotoKind.thumbnail,
        ),
    ]
    assert obj.userType == "Employee"
    assert obj.title == "Tour Guide"
    assert obj.preferredLanguage == "en-US"
    assert obj.locale == "en-US"
    assert obj.timezone == "America/Los_Angeles"
    assert obj.active is True
    assert obj.password == "t1meMa$heen"
    assert obj.groups == [
        GroupMember(
            value="e9e30dba-f08f-4109-8486-d5c6a331660a",
            ref="https://example.com/v2/Groups/e9e30dba-f08f-4109-8486-d5c6a331660a",
            display="Tour Guides",
        ),
        GroupMember(
            value="fc348aa8-3835-40eb-a20b-c726e15c55b5",
            ref="https://example.com/v2/Groups/fc348aa8-3835-40eb-a20b-c726e15c55b5",
            display="Employees",
        ),
        GroupMember(
            value="71ddacd2-a8e7-49b8-a5db-ae50d0a5bfd7",
            ref="https://example.com/v2/Groups/71ddacd2-a8e7-49b8-a5db-ae50d0a5bfd7",
            display="US Employees",
        ),
    ]
    assert obj.x509Certificates == [
        X509Certificate(
            value=(
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
        )
    ]
    assert obj.meta == Meta(
        resourceType="User",
        created=datetime.datetime(2010, 1, 23, 4, 56, 22, tzinfo=datetime.timezone.utc),
        lastModified=datetime.datetime(
            2011, 5, 13, 4, 42, 34, tzinfo=datetime.timezone.utc
        ),
        version='W\\/"a330bc54f0671c9"',
        location="https://example.com/v2/Users/2819c223-7f76-453a-919d-413861904646",
    )
