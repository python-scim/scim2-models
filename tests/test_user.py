import datetime

from scim2_models import Address
from scim2_models import Email
from scim2_models import Im
from scim2_models import PhoneNumber
from scim2_models import Photo
from scim2_models import Reference
from scim2_models import User


def test_minimal_user(load_sample):
    """Test creating an object representing the minimal user example of RFC7643."""
    payload = load_sample("rfc7643-8.1-user-minimal.json")
    obj = User.model_validate(payload)

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


def test_full_user(load_sample):
    """Test creating an object representing the full user example of RFC7643."""
    payload = load_sample("rfc7643-8.2-user-full.json")
    obj = User.model_validate(payload)

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
    assert obj.profile_url == Reference("https://login.example.com/bjensen")
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
    assert obj.photos[0].value == Reference(
        "https://photos.example.com/profilephoto/72930000000Ccne/F"
    )
    assert obj.photos[0].type == Photo.Type.photo
    assert obj.photos[1].value == Reference(
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
    assert obj.groups[0].ref == Reference(
        "https://example.com/v2/Groups/e9e30dba-f08f-4109-8486-d5c6a331660a"
    )
    assert obj.groups[0].display == "Tour Guides"
    assert obj.groups[1].value == "fc348aa8-3835-40eb-a20b-c726e15c55b5"
    assert obj.groups[1].ref == Reference(
        "https://example.com/v2/Groups/fc348aa8-3835-40eb-a20b-c726e15c55b5"
    )
    assert obj.groups[1].display == "Employees"
    assert obj.groups[2].value == "71ddacd2-a8e7-49b8-a5db-ae50d0a5bfd7"
    assert obj.groups[2].ref == Reference(
        "https://example.com/v2/Groups/71ddacd2-a8e7-49b8-a5db-ae50d0a5bfd7"
    )
    assert obj.groups[2].display == "US Employees"
    assert obj.x509_certificates[0].value == (
        b"0\x82\x03C0\x82\x02\xac\xa0\x03\x02\x01\x02\x02\x02\x10\x000\r\x06\t*\x86H\x86\xf7\r\x01\x01\x05\x05\x000N1\x0b0\t\x06\x03U\x04\x06\x13\x02US1\x130\x11\x06\x03U\x04\x08\x0c\nCalifornia1\x140\x12\x06\x03U\x04\n\x0c\x0bexample.com1\x140\x12\x06\x03U\x04\x03\x0c\x0bexample.com0\x1e\x17\r111022062431Z\x17\r121004062431Z0\x7f1\x0b0\t\x06\x03U\x04\x06\x13\x02US1\x130\x11\x06\x03U\x04\x08\x0c\nCalifornia1\x140\x12\x06\x03U\x04\n\x0c\x0bexample.com1!0\x1f\x06\x03U\x04\x03\x0c\x18Ms. Barbara J Jensen III1\"0 \x06\t*\x86H\x86\xf7\r\x01\t\x01\x16\x13bjensen@example.com0\x82\x01\"0\r\x06\t*\x86H\x86\xf7\r\x01\x01\x01\x05\x00\x03\x82\x01\x0f\x000\x82\x01\n\x02\x82\x01\x01\x00\xec\xaa\xfe\r\xc7l\xfc\x949\x1b\x07\xa3$W\x01 \xfe\xbc\xd9}\xf1\xa68\xac\xe7\xa0\n\xd3f\xdc\xd4R\xe0\xcd\xd2\xc8\xf1\xab\xa8G\xe7\x02\xf7\xf5k\x87\x9bz\xe8y\x10 \xe7@\xe2\xe9\xc7\x87@\x1ag\x8cK\xe4\xf8Umr\x0f0\x1eo\x00\xf2\xa9\xcf>b=(\xbc\xc4\xef\x12/\xb2;H8\\\x05Ra\xa9Z\xab\xdcx%\x94A\xbaP)Cts\xbb\x9eB\xee\xc1z\xbc\x1d\xc2\x12*F\xd3\xe5aSU\xf1Y\xce'O\x97\xc1\xd9\xec8W\x91\x92\x11\xb4\x9c\x01\xc1\xea\xb8n\xf9\xb7\x84\xcdN\xb3\xb5\x10\x1fNYK\xa7\x15\x0e\x0c\x1e(\xdc\x1d,\xba\xd3\xe7X\xa4I\x01\xb7\r\x8a\xe5\xf9\xfb{\xf3U\x10D\x8a\xb1\x83\n\x82}q.\x0e(\xa7>\x1d$\x92\xf2\"\xe68\xafV\xedY\xf5\x08\xb0\x95\x81\x1dE\xb2\xc9\xe32P\x06`\xebHd\xccb~%E\xcd\x87\x80s\xb8\x0e\xa0\x7fns\x15\xa2\xb1\xc1\xd0 \xba\x01]P\xa0R\xb8\x18\xf7\xb5/\x02\x03\x01\x00\x01\xa3{0y0\t\x06\x03U\x1d\x13\x04\x020\x000,\x06\t`\x86H\x01\x86\xf8B\x01\r\x04\x1f\x16\x1dOpenSSL Generated Certificate0\x1d\x06\x03U\x1d\x0e\x04\x16\x04\x14\xf2\x90\xf4SK\xecd\x8b\x1a\x03^\xa5/\xc1'\xf1\xbct\x17\xf80\x1f\x06\x03U\x1d#\x04\x180\x16\x80\x14tg\x8a\x8a\xd7\x1a\x17\xb8'\xce\xc3p\x0f\x1e\xf4\xf2J\x9aV\xdd0\r\x06\t*\x86H\x86\xf7\r\x01\x01\x05\x05\x00\x03\x81\x81\x00\x03\xcdR\xb0Y\xceu\x82m6\x0eSr\xaf\xbf\x07!\x03\xac\x18'\xba\xcct\x8eZ\x14\x84\x1c\x8f0Ed\xa0\xc6w'\xb8\xf5f\x02<\xac\x06\xce\x90\xd9\xe0_\xcf\xa9)\xf4\xe2\x0f=Q\x0b\x8f\x9d\xc7\xca\x14\xe9\x96\xbe\xe0\xd2WR9K\xe4+\xd5\xe8\x11\x18o_\x90\x00Bp\x8a\xd4\xd5\xbf\x10\x7f\x03\xae\xe0\xe3o\xef\xce\x00-\xa1\x15\x1e\x0e\x8b\xf5\xf8ab\x05\x9f\x864_\xdc\x01\x82\x9c2\xd1\x9c\xae\xcd\xa2\xf7\xb6d$\xca"
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
