import datetime

from scim2_models import Group
from scim2_models import Reference


def test_group(load_sample):
    payload = load_sample("rfc7643-8.4-group.json")
    obj = Group.model_validate(payload)

    assert obj.schemas == ["urn:ietf:params:scim:schemas:core:2.0:Group"]
    assert obj.id == "e9e30dba-f08f-4109-8486-d5c6a331660a"
    assert obj.display_name == "Tour Guides"
    assert obj.members[0].value == "2819c223-7f76-453a-919d-413861904646"
    assert obj.members[0].ref == Reference(
        "https://example.com/v2/Users/2819c223-7f76-453a-919d-413861904646"
    )
    assert obj.members[0].display == "Babs Jensen"
    assert obj.members[1].value == "902c246b-6245-4190-8e05-00816be7344a"
    assert obj.members[1].ref == Reference(
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

    assert obj.model_dump() == payload
