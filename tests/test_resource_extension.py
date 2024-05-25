import datetime

from pydantic_scim2 import EnterpriseUser
from pydantic_scim2 import Manager
from pydantic_scim2 import Meta
from pydantic_scim2 import User


def test_extension_getitem():
    """Test that an extension can be accessed and update with __getitem__"""

    user = User[EnterpriseUser](
        id="2819c223-7f76-453a-919d-413861904646",
        user_name="bjensen@example.com",
        meta=Meta(
            resource_type="User",
            created=datetime.datetime(
                2010, 1, 23, 4, 56, 22, tzinfo=datetime.timezone.utc
            ),
            last_modified=datetime.datetime(
                2011, 5, 13, 4, 42, 34, tzinfo=datetime.timezone.utc
            ),
            version='W\\/"a330bc54f0671c9"',
            location="https://example.com/v2/Users/2819c223-7f76-453a-919d-413861904646",
        ),
    )
    user[EnterpriseUser].employee_number = "701984"
    user[EnterpriseUser].cost_center = "4130"
    user[EnterpriseUser].organization = "Universal Studios"
    user[EnterpriseUser].division = "Theme Park"
    user[EnterpriseUser].department = "Tour Operations"
    user[EnterpriseUser].manager = Manager(
        value="26118915-6090-4610-87e4-49d8ca9f808d",
        ref="https://example.com/v2/Users/26118915-6090-4610-87e4-49d8ca9f808d",
        display_name="John Smith",
    )

    expected_payload = {
        "id": "2819c223-7f76-453a-919d-413861904646",
        "meta": {
            "created": "2010-01-23T04:56:22Z",
            "lastModified": "2011-05-13T04:42:34Z",
            "location": "https://example.com/v2/Users/2819c223-7f76-453a-919d-413861904646",
            "resourceType": "User",
            "version": 'W\\/"a330bc54f0671c9"',
        },
        "schemas": [
            "urn:ietf:params:scim:schemas:core:2.0:User",
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
        ],
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
            "employeeNumber": "701984",
            "costCenter": "4130",
            "organization": "Universal Studios",
            "division": "Theme Park",
            "department": "Tour Operations",
            "manager": {
                "value": "26118915-6090-4610-87e4-49d8ca9f808d",
                "$ref": "https://example.com/v2/Users/26118915-6090-4610-87e4-49d8ca9f808d",
                "displayName": "John Smith",
            },
            "schemas": [
                "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
            ],
        },
        "userName": "bjensen@example.com",
    }
    assert (
        user.model_dump(exclude_none=True, by_alias=True, mode="json")
        == expected_payload
    )


def test_extension_setitem():
    """Test that an extension can be set with __setitem__"""

    user = User[EnterpriseUser](
        id="2819c223-7f76-453a-919d-413861904646",
        user_name="bjensen@example.com",
        meta=Meta(
            resource_type="User",
            created=datetime.datetime(
                2010, 1, 23, 4, 56, 22, tzinfo=datetime.timezone.utc
            ),
            last_modified=datetime.datetime(
                2011, 5, 13, 4, 42, 34, tzinfo=datetime.timezone.utc
            ),
            version='W\\/"a330bc54f0671c9"',
            location="https://example.com/v2/Users/2819c223-7f76-453a-919d-413861904646",
        ),
    )
    user[EnterpriseUser] = EnterpriseUser(
        employee_number="701984",
        cost_center="4130",
        organization="Universal Studios",
        division="Theme Park",
        department="Tour Operations",
        manager=Manager(
            value="26118915-6090-4610-87e4-49d8ca9f808d",
            ref="https://example.com/v2/Users/26118915-6090-4610-87e4-49d8ca9f808d",
            display_name="John Smith",
        ),
    )

    expected_payload = {
        "id": "2819c223-7f76-453a-919d-413861904646",
        "meta": {
            "created": "2010-01-23T04:56:22Z",
            "lastModified": "2011-05-13T04:42:34Z",
            "location": "https://example.com/v2/Users/2819c223-7f76-453a-919d-413861904646",
            "resourceType": "User",
            "version": 'W\\/"a330bc54f0671c9"',
        },
        "schemas": [
            "urn:ietf:params:scim:schemas:core:2.0:User",
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
        ],
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
            "employeeNumber": "701984",
            "costCenter": "4130",
            "organization": "Universal Studios",
            "division": "Theme Park",
            "department": "Tour Operations",
            "manager": {
                "value": "26118915-6090-4610-87e4-49d8ca9f808d",
                "$ref": "https://example.com/v2/Users/26118915-6090-4610-87e4-49d8ca9f808d",
                "displayName": "John Smith",
            },
            "schemas": [
                "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
            ],
        },
        "userName": "bjensen@example.com",
    }
    assert (
        user.model_dump(exclude_none=True, by_alias=True, mode="json")
        == expected_payload
    )


def test_extension_no_payload():
    """An extension is defined but there is no matching payload."""

    payload = {
        "id": "2819c223-7f76-453a-919d-413861904646",
        "meta": {
            "created": "2010-01-23T04:56:22Z",
            "lastModified": "2011-05-13T04:42:34Z",
            "location": "https://example.com/v2/Users/2819c223-7f76-453a-919d-413861904646",
            "resourceType": "User",
            "version": 'W\\/"a330bc54f0671c9"',
        },
        "schemas": [
            "urn:ietf:params:scim:schemas:core:2.0:User",
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
        ],
        "userName": "bjensen@example.com",
    }

    User[EnterpriseUser].model_validate(payload)
