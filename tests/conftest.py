import pytest


@pytest.fixture
def minimal_user_payload():
    """https://www.rfc-editor.org/rfc/rfc7643#section-8.1"""

    return {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        "id": "2819c223-7f76-453a-919d-413861904646",
        "userName": "bjensen@example.com",
        "meta": {
            "resourceType": "User",
            "created": "2010-01-23T04:56:22Z",
            "lastModified": "2011-05-13T04:42:34Z",
            "version": 'W\\/"3694e05e9dff590"',
            "location": "https://example.com/v2/Users/2819c223-7f76-453a-919d-413861904646",
        },
    }


@pytest.fixture
def full_user_payload():
    """https://www.rfc-editor.org/rfc/rfc7643#section-8.2"""
    return {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        "id": "2819c223-7f76-453a-919d-413861904646",
        "externalId": "701984",
        "userName": "bjensen@example.com",
        "name": {
            "formatted": "Ms. Barbara J Jensen, III",
            "familyName": "Jensen",
            "givenName": "Barbara",
            "middleName": "Jane",
            "honorificPrefix": "Ms.",
            "honorificSuffix": "III",
        },
        "displayName": "Babs Jensen",
        "nickName": "Babs",
        "profileUrl": "https://login.example.com/bjensen",
        "emails": [
            {"value": "bjensen@example.com", "type": "work", "primary": True},
            {"value": "babs@jensen.org", "type": "home"},
        ],
        "addresses": [
            {
                "type": "work",
                "streetAddress": "100 Universal City Plaza",
                "locality": "Hollywood",
                "region": "CA",
                "postalCode": "91608",
                "country": "USA",
                "formatted": "100 Universal City Plaza\nHollywood, CA 91608 USA",
                "primary": True,
            },
            {
                "type": "home",
                "streetAddress": "456 Hollywood Blvd",
                "locality": "Hollywood",
                "region": "CA",
                "postalCode": "91608",
                "country": "USA",
                "formatted": "456 Hollywood Blvd\nHollywood, CA 91608 USA",
            },
        ],
        "phoneNumbers": [
            {"value": "555-555-5555", "type": "work"},
            {"value": "555-555-4444", "type": "mobile"},
        ],
        "ims": [{"value": "someaimhandle", "type": "aim"}],
        "photos": [
            {
                "value": "https://photos.example.com/profilephoto/72930000000Ccne/F",
                "type": "photo",
            },
            {
                "value": "https://photos.example.com/profilephoto/72930000000Ccne/T",
                "type": "thumbnail",
            },
        ],
        "userType": "Employee",
        "title": "Tour Guide",
        "preferredLanguage": "en-US",
        "locale": "en-US",
        "timezone": "America/Los_Angeles",
        "active": True,
        "password": "t1meMa$heen",
        "groups": [
            {
                "value": "e9e30dba-f08f-4109-8486-d5c6a331660a",
                "$ref": "https://example.com/v2/Groups/e9e30dba-f08f-4109-8486-d5c6a331660a",
                "display": "Tour Guides",
            },
            {
                "value": "fc348aa8-3835-40eb-a20b-c726e15c55b5",
                "$ref": "https://example.com/v2/Groups/fc348aa8-3835-40eb-a20b-c726e15c55b5",
                "display": "Employees",
            },
            {
                "value": "71ddacd2-a8e7-49b8-a5db-ae50d0a5bfd7",
                "$ref": "https://example.com/v2/Groups/71ddacd2-a8e7-49b8-a5db-ae50d0a5bfd7",
                "display": "US Employees",
            },
        ],
        "x509Certificates": [
            {
                "value": (
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
            }
        ],
        "meta": {
            "resourceType": "User",
            "created": "2010-01-23T04:56:22Z",
            "lastModified": "2011-05-13T04:42:34Z",
            "version": 'W\\/"a330bc54f0671c9"',
            "location": "https://example.com/v2/Users/2819c223-7f76-453a-919d-413861904646",
        },
    }


@pytest.fixture
def enterprise_user_payload():
    """https://www.rfc-editor.org/rfc/rfc7643#section-8.3"""
    return {
        "schemas": [
            "urn:ietf:params:scim:schemas:core:2.0:User",
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
        ],
        "id": "2819c223-7f76-453a-919d-413861904646",
        "externalId": "701984",
        "userName": "bjensen@example.com",
        "name": {
            "formatted": "Ms. Barbara J Jensen, III",
            "familyName": "Jensen",
            "givenName": "Barbara",
            "middleName": "Jane",
            "honorificPrefix": "Ms.",
            "honorificSuffix": "III",
        },
        "displayName": "Babs Jensen",
        "nickName": "Babs",
        "profileUrl": "https://login.example.com/bjensen",
        "emails": [
            {"value": "bjensen@example.com", "type": "work", "primary": True},
            {"value": "babs@jensen.org", "type": "home"},
        ],
        "addresses": [
            {
                "streetAddress": "100 Universal City Plaza",
                "locality": "Hollywood",
                "region": "CA",
                "postalCode": "91608",
                "country": "USA",
                "formatted": "100 Universal City Plaza\nHollywood, CA 91608 USA",
                "type": "work",
                "primary": True,
            },
            {
                "streetAddress": "456 Hollywood Blvd",
                "locality": "Hollywood",
                "region": "CA",
                "postalCode": "91608",
                "country": "USA",
                "formatted": "456 Hollywood Blvd\nHollywood, CA 91608 USA",
                "type": "home",
            },
        ],
        "phoneNumbers": [
            {"value": "555-555-5555", "type": "work"},
            {"value": "555-555-4444", "type": "mobile"},
        ],
        "ims": [{"value": "someaimhandle", "type": "aim"}],
        "photos": [
            {
                "value": "https://photos.example.com/profilephoto/72930000000Ccne/F",
                "type": "photo",
            },
            {
                "value": "https://photos.example.com/profilephoto/72930000000Ccne/T",
                "type": "thumbnail",
            },
        ],
        "userType": "Employee",
        "title": "Tour Guide",
        "preferredLanguage": "en-US",
        "locale": "en-US",
        "timezone": "America/Los_Angeles",
        "active": True,
        "password": "t1meMa$heen",
        "groups": [
            {
                "value": "e9e30dba-f08f-4109-8486-d5c6a331660a",
                "$ref": "../Groups/e9e30dba-f08f-4109-8486-d5c6a331660a",
                "display": "Tour Guides",
            },
            {
                "value": "fc348aa8-3835-40eb-a20b-c726e15c55b5",
                "$ref": "../Groups/fc348aa8-3835-40eb-a20b-c726e15c55b5",
                "display": "Employees",
            },
            {
                "value": "71ddacd2-a8e7-49b8-a5db-ae50d0a5bfd7",
                "$ref": "../Groups/71ddacd2-a8e7-49b8-a5db-ae50d0a5bfd7",
                "display": "US Employees",
            },
        ],
        "x509Certificates": [
            {
                "value": (
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
            }
        ],
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
            "employeeNumber": "701984",
            "costCenter": "4130",
            "organization": "Universal Studios",
            "division": "Theme Park",
            "department": "Tour Operations",
            "manager": {
                "value": "26118915-6090-4610-87e4-49d8ca9f808d",
                "$ref": "../Users/26118915-6090-4610-87e4-49d8ca9f808d",
                "displayName": "John Smith",
            },
        },
        "meta": {
            "resourceType": "User",
            "created": "2010-01-23T04:56:22Z",
            "lastModified": "2011-05-13T04:42:34Z",
            "version": 'W\\/"3694e05e9dff591"',
            "location": "https://example.com/v2/Users/2819c223-7f76-453a-919d-413861904646",
        },
    }


@pytest.fixture
def group_payload():
    """https://www.rfc-editor.org/rfc/rfc7643#section-8.4"""
    return {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"],
        "id": "e9e30dba-f08f-4109-8486-d5c6a331660a",
        "displayName": "Tour Guides",
        "members": [
            {
                "value": "2819c223-7f76-453a-919d-413861904646",
                "$ref": "https://example.com/v2/Users/2819c223-7f76-453a-919d-413861904646",
                "display": "Babs Jensen",
            },
            {
                "value": "902c246b-6245-4190-8e05-00816be7344a",
                "$ref": "https://example.com/v2/Users/902c246b-6245-4190-8e05-00816be7344a",
                "display": "Mandy Pepperidge",
            },
        ],
        "meta": {
            "resourceType": "Group",
            "created": "2010-01-23T04:56:22Z",
            "lastModified": "2011-05-13T04:42:34Z",
            "version": 'W\\/"3694e05e9dff592"',
            "location": "https://example.com/v2/Groups/e9e30dba-f08f-4109-8486-d5c6a331660a",
        },
    }


@pytest.fixture
def service_provider_configuration_payload():
    """https://www.rfc-editor.org/rfc/rfc7643#section-8.5"""
    return {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig"],
        "documentationUri": "http://example.com/help/scim.html",
        "patch": {"supported": True},
        "bulk": {"supported": True, "maxOperations": 1000, "maxPayloadSize": 1048576},
        "filter": {"supported": True, "maxResults": 200},
        "changePassword": {"supported": True},
        "sort": {"supported": True},
        "etag": {"supported": True},
        "authenticationSchemes": [
            {
                "name": "OAuth Bearer Token",
                "description": "Authentication scheme using the OAuth Bearer Token Standard",
                "specUri": "http://www.rfc-editor.org/info/rfc6750",
                "documentationUri": "http://example.com/help/oauth.html",
                "type": "oauthbearertoken",
                "primary": True,
            },
            {
                "name": "HTTP Basic",
                "description": "Authentication scheme using the HTTP Basic Standard",
                "specUri": "http://www.rfc-editor.org/info/rfc2617",
                "documentationUri": "http://example.com/help/httpBasic.html",
                "type": "httpbasic",
            },
        ],
        "meta": {
            "location": "https://example.com/v2/ServiceProviderConfig",
            "resourceType": "ServiceProviderConfig",
            "created": "2010-01-23T04:56:22Z",
            "lastModified": "2011-05-13T04:42:34Z",
            "version": 'W\\/"3694e05e9dff594"',
        },
    }


@pytest.fixture
def resource_type_payload():
    """https://www.rfc-editor.org/rfc/rfc7643#section-8.6"""
    return [
        {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ResourceType"],
            "id": "User",
            "name": "User",
            "endpoint": "/Users",
            "description": "User Account",
            "schema": "urn:ietf:params:scim:schemas:core:2.0:User",
            "schemaExtensions": [
                {
                    "schema": "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
                    "required": True,
                }
            ],
            "meta": {
                "location": "https://example.com/v2/ResourceTypes/User",
                "resourceType": "ResourceType",
            },
        },
        {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ResourceType"],
            "id": "Group",
            "name": "Group",
            "endpoint": "/Groups",
            "description": "Group",
            "schema": "urn:ietf:params:scim:schemas:core:2.0:Group",
            "meta": {
                "location": "https://example.com/v2/ResourceTypes/Group",
                "resourceType": "ResourceType",
            },
        },
    ]


@pytest.fixture
def resource_schema_payload():
    """https://www.rfc-editor.org/rfc/rfc7643#section-8.7.1"""
    return [
        {
            "id": "urn:ietf:params:scim:schemas:core:2.0:User",
            "name": "User",
            "description": "User Account",
            "attributes": [
                {
                    "name": "userName",
                    "type": "string",
                    "multiValued": False,
                    "description": (
                        "Unique identifier for the User, typically "
                        "used by the user to directly authenticate to the service provider. "
                        "Each User MUST include a non-empty userName value.  This identifier "
                        "MUST be unique across the service provider's entire set of Users. "
                        "REQUIRED."
                    ),
                    "required": True,
                    "caseExact": False,
                    "mutability": "readWrite",
                    "returned": "default",
                    "uniqueness": "server",
                },
                {
                    "name": "name",
                    "type": "complex",
                    "multiValued": False,
                    "description": (
                        "The components of the user's real name. "
                        "Providers MAY return just the full name as a single string in the "
                        "formatted sub-attribute, or they MAY return just the individual "
                        "component attributes using the other sub-attributes, or they MAY "
                        "return both.  If both variants are returned, they SHOULD be "
                        "describing the same name, with the formatted name indicating how the "
                        "component attributes should be combined."
                    ),
                    "required": False,
                    "subAttributes": [
                        {
                            "name": "formatted",
                            "type": "string",
                            "multiValued": False,
                            "description": (
                                "The full name, including all middle "
                                "names, titles, and suffixes as appropriate, formatted for display "
                                "(e.g., 'Ms. Barbara J Jensen, III')."
                            ),
                            "required": False,
                            "caseExact": False,
                            "mutability": "readWrite",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                        {
                            "name": "familyName",
                            "type": "string",
                            "multiValued": False,
                            "description": (
                                "The family name of the User, or "
                                "last name in most Western languages (e.g., 'Jensen' given the full "
                                "name 'Ms. Barbara J Jensen, III')."
                            ),
                            "required": False,
                            "caseExact": False,
                            "mutability": "readWrite",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                        {
                            "name": "givenName",
                            "type": "string",
                            "multiValued": False,
                            "description": (
                                "The given name of the User, or "
                                "first name in most Western languages (e.g., 'Barbara' given the "
                                "full name 'Ms. Barbara J Jensen, III')."
                            ),
                            "required": False,
                            "caseExact": False,
                            "mutability": "readWrite",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                        {
                            "name": "middleName",
                            "type": "string",
                            "multiValued": False,
                            "description": (
                                "The middle name(s) of the User "
                                "(e.g., 'Jane' given the full name 'Ms. Barbara J Jensen, III')."
                            ),
                            "required": False,
                            "caseExact": False,
                            "mutability": "readWrite",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                        {
                            "name": "honorificPrefix",
                            "type": "string",
                            "multiValued": False,
                            "description": (
                                "The honorific prefix(es) of the User, or "
                                "title in most Western languages (e.g., 'Ms.' given the full name "
                                "'Ms. Barbara J Jensen, III')."
                            ),
                            "required": False,
                            "caseExact": False,
                            "mutability": "readWrite",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                        {
                            "name": "honorificSuffix",
                            "type": "string",
                            "multiValued": False,
                            "description": (
                                "The honorific suffix(es) of the User, or "
                                "suffix in most Western languages (e.g., 'III' given the full name "
                                "'Ms. Barbara J Jensen, III')."
                            ),
                            "required": False,
                            "caseExact": False,
                            "mutability": "readWrite",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                    ],
                    "mutability": "readWrite",
                    "returned": "default",
                    "uniqueness": "none",
                },
                {
                    "name": "displayName",
                    "type": "string",
                    "multiValued": False,
                    "description": (
                        "The name of the User, suitable for display "
                        "to end-users.  The name SHOULD be the full name of the User being "
                        "described, if known."
                    ),
                    "required": False,
                    "caseExact": False,
                    "mutability": "readWrite",
                    "returned": "default",
                    "uniqueness": "none",
                },
                {
                    "name": "nickName",
                    "type": "string",
                    "multiValued": False,
                    "description": (
                        "The casual way to address the user in real "
                        "life, e.g., 'Bob' or 'Bobby' instead of 'Robert'.  This attribute "
                        "SHOULD NOT be used to represent a User's username (e.g., 'bjensen' or "
                        "'mpepperidge')."
                    ),
                    "required": False,
                    "caseExact": False,
                    "mutability": "readWrite",
                    "returned": "default",
                    "uniqueness": "none",
                },
                {
                    "name": "profileUrl",
                    "type": "reference",
                    "referenceTypes": ["external"],
                    "multiValued": False,
                    "description": (
                        "A fully qualified URL pointing to a page "
                        "representing the User's online profile."
                    ),
                    "required": False,
                    "caseExact": False,
                    "mutability": "readWrite",
                    "returned": "default",
                    "uniqueness": "none",
                },
                {
                    "name": "title",
                    "type": "string",
                    "multiValued": False,
                    "description": ("The user's title, such as " '"Vice President."'),
                    "required": False,
                    "caseExact": False,
                    "mutability": "readWrite",
                    "returned": "default",
                    "uniqueness": "none",
                },
                {
                    "name": "userType",
                    "type": "string",
                    "multiValued": False,
                    "description": (
                        "Used to identify the relationship between "
                        "the organization and the user.  Typical values used might be "
                        "'Contractor', 'Employee', 'Intern', 'Temp', 'External', and "
                        "'Unknown', but any value may be used."
                    ),
                    "required": False,
                    "caseExact": False,
                    "mutability": "readWrite",
                    "returned": "default",
                    "uniqueness": "none",
                },
                {
                    "name": "preferredLanguage",
                    "type": "string",
                    "multiValued": False,
                    "description": (
                        "Indicates the User's preferred written or "
                        "spoken language.  Generally used for selecting a localized user "
                        "interface; e.g., 'en_US' specifies the language English and country "
                        "US."
                    ),
                    "required": False,
                    "caseExact": False,
                    "mutability": "readWrite",
                    "returned": "default",
                    "uniqueness": "none",
                },
                {
                    "name": "locale",
                    "type": "string",
                    "multiValued": False,
                    "description": (
                        "Used to indicate the User's default location "
                        "for purposes of localizing items such as currency, date time format, or "
                        "numerical representations."
                    ),
                    "required": False,
                    "caseExact": False,
                    "mutability": "readWrite",
                    "returned": "default",
                    "uniqueness": "none",
                },
                {
                    "name": "timezone",
                    "type": "string",
                    "multiValued": False,
                    "description": (
                        "The User's time zone in the 'Olson' time zone "
                        "database format, e.g., 'America/Los_Angeles'."
                    ),
                    "required": False,
                    "caseExact": False,
                    "mutability": "readWrite",
                    "returned": "default",
                    "uniqueness": "none",
                },
                {
                    "name": "active",
                    "type": "boolean",
                    "multiValued": False,
                    "description": (
                        "A Boolean value indicating the User's "
                        "administrative status."
                    ),
                    "required": False,
                    "mutability": "readWrite",
                    "returned": "default",
                },
                {
                    "name": "password",
                    "type": "string",
                    "multiValued": False,
                    "description": (
                        "The User's cleartext password.  This "
                        "attribute is intended to be used as a means to specify an initial "
                        "password when creating a new User or to reset an existing User's"
                        "password."
                    ),
                    "required": False,
                    "caseExact": False,
                    "mutability": "writeOnly",
                    "returned": "never",
                    "uniqueness": "none",
                },
                {
                    "name": "emails",
                    "type": "complex",
                    "multiValued": True,
                    "description": (
                        "Email addresses for the user.  The value "
                        "SHOULD be canonicalized by the service provider, e.g., "
                        "'bjensen@example.com' instead of 'bjensen@EXAMPLE.COM'. "
                        "Canonical type values of 'work', 'home', and 'other'."
                    ),
                    "required": False,
                    "subAttributes": [
                        {
                            "name": "value",
                            "type": "string",
                            "multiValued": False,
                            "description": (
                                "Email addresses for the user.  The value "
                                "SHOULD be canonicalized by the service provider, e.g., "
                                "'bjensen@example.com' instead of 'bjensen@EXAMPLE.COM'. "
                                "Canonical type values of 'work', 'home', and 'other'."
                            ),
                            "required": False,
                            "caseExact": False,
                            "mutability": "readWrite",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                        {
                            "name": "display",
                            "type": "string",
                            "multiValued": False,
                            "description": (
                                "A human-readable name, primarily used "
                                "for display purposes.  READ-ONLY."
                            ),
                            "required": False,
                            "caseExact": False,
                            "mutability": "readWrite",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                        {
                            "name": "type",
                            "type": "string",
                            "multiValued": False,
                            "description": (
                                "A label indicating the attribute's "
                                "function, e.g., 'work' or 'home'."
                            ),
                            "required": False,
                            "caseExact": False,
                            "canonicalValues": ["work", "home", "other"],
                            "mutability": "readWrite",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                        {
                            "name": "primary",
                            "type": "boolean",
                            "multiValued": False,
                            "description": (
                                "A Boolean value indicating the 'primary' "
                                "or preferred attribute value for this attribute, e.g., the preferred "
                                "mailing address or primary email address.  The primary attribute "
                                "value 'True' MUST appear no more than once."
                            ),
                            "required": False,
                            "mutability": "readWrite",
                            "returned": "default",
                        },
                    ],
                    "mutability": "readWrite",
                    "returned": "default",
                    "uniqueness": "none",
                },
                {
                    "name": "phoneNumbers",
                    "type": "complex",
                    "multiValued": True,
                    "description": (
                        "Phone numbers for the User.  The value "
                        "SHOULD be canonicalized by the service provider according to the "
                        "format specified in RFC 3966, e.g., 'tel:+1-201-555-0123'. "
                        "Canonical type values of 'work', 'home', 'mobile', 'fax', 'pager', "
                        "and 'other'."
                    ),
                    "required": False,
                    "subAttributes": [
                        {
                            "name": "value",
                            "type": "string",
                            "multiValued": False,
                            "description": "Phone number of the User.",
                            "required": False,
                            "caseExact": False,
                            "mutability": "readWrite",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                        {
                            "name": "display",
                            "type": "string",
                            "multiValued": False,
                            "description": (
                                "A human-readable name, primarily used "
                                "for display purposes.  READ-ONLY."
                            ),
                            "required": False,
                            "caseExact": False,
                            "mutability": "readWrite",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                        {
                            "name": "type",
                            "type": "string",
                            "multiValued": False,
                            "description": (
                                "A label indicating the attribute's "
                                "function, e.g., 'work', 'home', 'mobile'."
                            ),
                            "required": False,
                            "caseExact": False,
                            "canonicalValues": [
                                "work",
                                "home",
                                "mobile",
                                "fax",
                                "pager",
                                "other",
                            ],
                            "mutability": "readWrite",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                        {
                            "name": "primary",
                            "type": "boolean",
                            "multiValued": False,
                            "description": (
                                "A Boolean value indicating the 'primary' "
                                "or preferred attribute value for this attribute, e.g., the preferred "
                                "phone number or primary phone number.  The primary attribute value "
                                "'True' MUST appear no more than once."
                            ),
                            "required": False,
                            "mutability": "readWrite",
                            "returned": "default",
                        },
                    ],
                    "mutability": "readWrite",
                    "returned": "default",
                },
                {
                    "name": "ims",
                    "type": "complex",
                    "multiValued": True,
                    "description": "Instant messaging addresses for the User.",
                    "required": False,
                    "subAttributes": [
                        {
                            "name": "value",
                            "type": "string",
                            "multiValued": False,
                            "description": "Instant messaging address for the User.",
                            "required": False,
                            "caseExact": False,
                            "mutability": "readWrite",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                        {
                            "name": "display",
                            "type": "string",
                            "multiValued": False,
                            "description": (
                                "A human-readable name, primarily used "
                                "for display purposes.  READ-ONLY."
                            ),
                            "required": False,
                            "caseExact": False,
                            "mutability": "readWrite",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                        {
                            "name": "type",
                            "type": "string",
                            "multiValued": False,
                            "description": (
                                "A label indicating the attribute's "
                                "function, e.g., 'aim', 'gtalk', 'xmpp'."
                            ),
                            "required": False,
                            "caseExact": False,
                            "canonicalValues": [
                                "aim",
                                "gtalk",
                                "icq",
                                "xmpp",
                                "msn",
                                "skype",
                                "qq",
                                "yahoo",
                            ],
                            "mutability": "readWrite",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                        {
                            "name": "primary",
                            "type": "boolean",
                            "multiValued": False,
                            "description": (
                                "A Boolean value indicating the 'primary' "
                                "or preferred attribute value for this attribute, e.g., the preferred "
                                "messenger or primary messenger.  The primary attribute value 'True' "
                                "MUST appear no more than once."
                            ),
                            "required": False,
                            "mutability": "readWrite",
                            "returned": "default",
                        },
                    ],
                    "mutability": "readWrite",
                    "returned": "default",
                },
                {
                    "name": "photos",
                    "type": "complex",
                    "multiValued": True,
                    "description": "URLs of photos of the User.",
                    "required": False,
                    "subAttributes": [
                        {
                            "name": "value",
                            "type": "reference",
                            "referenceTypes": ["external"],
                            "multiValued": False,
                            "description": "URL of a photo of the User.",
                            "required": False,
                            "caseExact": False,
                            "mutability": "readWrite",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                        {
                            "name": "display",
                            "type": "string",
                            "multiValued": False,
                            "description": (
                                "A human-readable name, primarily used "
                                "for display purposes.  READ-ONLY."
                            ),
                            "required": False,
                            "caseExact": False,
                            "mutability": "readWrite",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                        {
                            "name": "type",
                            "type": "string",
                            "multiValued": False,
                            "description": (
                                "A label indicating the attribute's "
                                "function, i.e., 'photo' or 'thumbnail'."
                            ),
                            "required": False,
                            "caseExact": False,
                            "canonicalValues": ["photo", "thumbnail"],
                            "mutability": "readWrite",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                        {
                            "name": "primary",
                            "type": "boolean",
                            "multiValued": False,
                            "description": (
                                "A Boolean value indicating the 'primary' "
                                "or preferred attribute value for this attribute, e.g., the preferred "
                                "photo or thumbnail.  The primary attribute value 'True' MUST appear "
                                "no more than once."
                            ),
                            "required": False,
                            "mutability": "readWrite",
                            "returned": "default",
                        },
                    ],
                    "mutability": "readWrite",
                    "returned": "default",
                },
                {
                    "name": "addresses",
                    "type": "complex",
                    "multiValued": True,
                    "description": (
                        "A physical mailing address for this User. "
                        "Canonical type values of 'work', 'home', and 'other'.  This attribute "
                        "is a complex type with the following sub-attributes."
                    ),
                    "required": False,
                    "subAttributes": [
                        {
                            "name": "formatted",
                            "type": "string",
                            "multiValued": False,
                            "description": (
                                "The full mailing address, formatted for "
                                "display or use with a mailing label.  This attribute MAY contain "
                                "newlines."
                            ),
                            "required": False,
                            "caseExact": False,
                            "mutability": "readWrite",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                        {
                            "name": "streetAddress",
                            "type": "string",
                            "multiValued": False,
                            "description": (
                                "The full street address component, "
                                "which may include house number, street name, P.O. box, and multi-line "
                                "extended street address information.  This attribute MAY contain "
                                "newlines."
                            ),
                            "required": False,
                            "caseExact": False,
                            "mutability": "readWrite",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                        {
                            "name": "locality",
                            "type": "string",
                            "multiValued": False,
                            "description": "The city or locality component.",
                            "required": False,
                            "caseExact": False,
                            "mutability": "readWrite",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                        {
                            "name": "region",
                            "type": "string",
                            "multiValued": False,
                            "description": "The state or region component.",
                            "required": False,
                            "caseExact": False,
                            "mutability": "readWrite",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                        {
                            "name": "postalCode",
                            "type": "string",
                            "multiValued": False,
                            "description": "The zip code or postal code component.",
                            "required": False,
                            "caseExact": False,
                            "mutability": "readWrite",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                        {
                            "name": "country",
                            "type": "string",
                            "multiValued": False,
                            "description": "The country name component.",
                            "required": False,
                            "caseExact": False,
                            "mutability": "readWrite",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                        {
                            "name": "type",
                            "type": "string",
                            "multiValued": False,
                            "description": (
                                "A label indicating the attribute's "
                                "function, e.g., 'work' or 'home'."
                            ),
                            "required": False,
                            "caseExact": False,
                            "canonicalValues": ["work", "home", "other"],
                            "mutability": "readWrite",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                    ],
                    "mutability": "readWrite",
                    "returned": "default",
                    "uniqueness": "none",
                },
                {
                    "name": "groups",
                    "type": "complex",
                    "multiValued": True,
                    "description": (
                        "A list of groups to which the user belongs, "
                        "either through direct membership, through nested groups, or "
                        "dynamically calculated."
                    ),
                    "required": False,
                    "subAttributes": [
                        {
                            "name": "value",
                            "type": "string",
                            "multiValued": False,
                            "description": "The identifier of the User's group.",
                            "required": False,
                            "caseExact": False,
                            "mutability": "readOnly",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                        {
                            "name": "$ref",
                            "type": "reference",
                            "referenceTypes": ["User", "Group"],
                            "multiValued": False,
                            "description": (
                                "The URI of the corresponding 'Group' "
                                "resource to which the user belongs."
                            ),
                            "required": False,
                            "caseExact": False,
                            "mutability": "readOnly",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                        {
                            "name": "display",
                            "type": "string",
                            "multiValued": False,
                            "description": (
                                "A human-readable name, primarily used "
                                "for display purposes.  READ-ONLY."
                            ),
                            "required": False,
                            "caseExact": False,
                            "mutability": "readOnly",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                        {
                            "name": "type",
                            "type": "string",
                            "multiValued": False,
                            "description": (
                                "A label indicating the attribute's "
                                "function, e.g., 'direct' or 'indirect'."
                            ),
                            "required": False,
                            "caseExact": False,
                            "canonicalValues": ["direct", "indirect"],
                            "mutability": "readOnly",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                    ],
                    "mutability": "readOnly",
                    "returned": "default",
                },
                {
                    "name": "entitlements",
                    "type": "complex",
                    "multiValued": True,
                    "description": (
                        "A list of entitlements for the User that "
                        "represent a thing the User has."
                    ),
                    "required": False,
                    "subAttributes": [
                        {
                            "name": "value",
                            "type": "string",
                            "multiValued": False,
                            "description": "The value of an entitlement.",
                            "required": False,
                            "caseExact": False,
                            "mutability": "readWrite",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                        {
                            "name": "display",
                            "type": "string",
                            "multiValued": False,
                            "description": (
                                "A human-readable name, primarily used "
                                "for display purposes.  READ-ONLY."
                            ),
                            "required": False,
                            "caseExact": False,
                            "mutability": "readWrite",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                        {
                            "name": "type",
                            "type": "string",
                            "multiValued": False,
                            "description": (
                                "A label indicating the attribute's " "function."
                            ),
                            "required": False,
                            "caseExact": False,
                            "mutability": "readWrite",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                        {
                            "name": "primary",
                            "type": "boolean",
                            "multiValued": False,
                            "description": (
                                "A Boolean value indicating the 'primary' "
                                "or preferred attribute value for this attribute.  The primary "
                                "attribute value 'True' MUST appear no more than once."
                            ),
                            "required": False,
                            "mutability": "readWrite",
                            "returned": "default",
                        },
                    ],
                    "mutability": "readWrite",
                    "returned": "default",
                },
                {
                    "name": "roles",
                    "type": "complex",
                    "multiValued": True,
                    "description": (
                        "A list of roles for the User that "
                        "collectively represent who the User is, e.g., 'Student', 'Faculty'."
                    ),
                    "required": False,
                    "subAttributes": [
                        {
                            "name": "value",
                            "type": "string",
                            "multiValued": False,
                            "description": "The value of a role.",
                            "required": False,
                            "caseExact": False,
                            "mutability": "readWrite",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                        {
                            "name": "display",
                            "type": "string",
                            "multiValued": False,
                            "description": (
                                "A human-readable name, primarily used "
                                "for display purposes.  READ-ONLY."
                            ),
                            "required": False,
                            "caseExact": False,
                            "mutability": "readWrite",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                        {
                            "name": "type",
                            "type": "string",
                            "multiValued": False,
                            "description": (
                                "A label indicating the attribute's " "function."
                            ),
                            "required": False,
                            "caseExact": False,
                            "canonicalValues": [],
                            "mutability": "readWrite",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                        {
                            "name": "primary",
                            "type": "boolean",
                            "multiValued": False,
                            "description": (
                                "A Boolean value indicating the 'primary' "
                                "or preferred attribute value for this attribute.  The primary "
                                "attribute value 'True' MUST appear no more than once."
                            ),
                            "required": False,
                            "mutability": "readWrite",
                            "returned": "default",
                        },
                    ],
                    "mutability": "readWrite",
                    "returned": "default",
                },
                {
                    "name": "x509Certificates",
                    "type": "complex",
                    "multiValued": True,
                    "description": "A list of certificates issued to the User.",
                    "required": False,
                    "caseExact": False,
                    "subAttributes": [
                        {
                            "name": "value",
                            "type": "binary",
                            "multiValued": False,
                            "description": "The value of an X.509 certificate.",
                            "required": False,
                            "caseExact": False,
                            "mutability": "readWrite",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                        {
                            "name": "display",
                            "type": "string",
                            "multiValued": False,
                            "description": (
                                "A human-readable name, primarily used "
                                "for display purposes.  READ-ONLY."
                            ),
                            "required": False,
                            "caseExact": False,
                            "mutability": "readWrite",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                        {
                            "name": "type",
                            "type": "string",
                            "multiValued": False,
                            "description": (
                                "A label indicating the attribute's " "function."
                            ),
                            "required": False,
                            "caseExact": False,
                            "canonicalValues": [],
                            "mutability": "readWrite",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                        {
                            "name": "primary",
                            "type": "boolean",
                            "multiValued": False,
                            "description": (
                                "A Boolean value indicating the 'primary' "
                                "or preferred attribute value for this attribute.  The primary "
                                "attribute value 'True' MUST appear no more than once."
                            ),
                            "required": False,
                            "mutability": "readWrite",
                            "returned": "default",
                        },
                    ],
                    "mutability": "readWrite",
                    "returned": "default",
                },
            ],
            "meta": {
                "resourceType": "Schema",
                "location": "/v2/Schemas/urn:ietf:params:scim:schemas:core:2.0:User",
            },
        },
        {
            "id": "urn:ietf:params:scim:schemas:core:2.0:Group",
            "name": "Group",
            "description": "Group",
            "attributes": [
                {
                    "name": "displayName",
                    "type": "string",
                    "multiValued": False,
                    "description": (
                        "A human-readable name for the Group. " "REQUIRED."
                    ),
                    "required": False,
                    "caseExact": False,
                    "mutability": "readWrite",
                    "returned": "default",
                    "uniqueness": "none",
                },
                {
                    "name": "members",
                    "type": "complex",
                    "multiValued": True,
                    "description": "A list of members of the Group.",
                    "required": False,
                    "subAttributes": [
                        {
                            "name": "value",
                            "type": "string",
                            "multiValued": False,
                            "description": "Identifier of the member of this Group.",
                            "required": False,
                            "caseExact": False,
                            "mutability": "immutable",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                        {
                            "name": "$ref",
                            "type": "reference",
                            "referenceTypes": ["User", "Group"],
                            "multiValued": False,
                            "description": (
                                "The URI corresponding to a SCIM resource "
                                "that is a member of this Group."
                            ),
                            "required": False,
                            "caseExact": False,
                            "mutability": "immutable",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                        {
                            "name": "type",
                            "type": "string",
                            "multiValued": False,
                            "description": (
                                "A label indicating the type of resource, "
                                "e.g., 'User' or 'Group'."
                            ),
                            "required": False,
                            "caseExact": False,
                            "canonicalValues": ["User", "Group"],
                            "mutability": "immutable",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                    ],
                    "mutability": "readWrite",
                    "returned": "default",
                },
            ],
            "meta": {
                "resourceType": "Schema",
                "location": "/v2/Schemas/urn:ietf:params:scim:schemas:core:2.0:Group",
            },
        },
        {
            "id": "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
            "name": "EnterpriseUser",
            "description": "Enterprise User",
            "attributes": [
                {
                    "name": "employeeNumber",
                    "type": "string",
                    "multiValued": False,
                    "description": (
                        "Numeric or alphanumeric identifier assigned "
                        "to a person, typically based on order of hire or association with an "
                        "organization."
                    ),
                    "required": False,
                    "caseExact": False,
                    "mutability": "readWrite",
                    "returned": "default",
                    "uniqueness": "none",
                },
                {
                    "name": "costCenter",
                    "type": "string",
                    "multiValued": False,
                    "description": "Identifies the name of a cost center.",
                    "required": False,
                    "caseExact": False,
                    "mutability": "readWrite",
                    "returned": "default",
                    "uniqueness": "none",
                },
                {
                    "name": "organization",
                    "type": "string",
                    "multiValued": False,
                    "description": "Identifies the name of an organization.",
                    "required": False,
                    "caseExact": False,
                    "mutability": "readWrite",
                    "returned": "default",
                    "uniqueness": "none",
                },
                {
                    "name": "division",
                    "type": "string",
                    "multiValued": False,
                    "description": "Identifies the name of a division.",
                    "required": False,
                    "caseExact": False,
                    "mutability": "readWrite",
                    "returned": "default",
                    "uniqueness": "none",
                },
                {
                    "name": "department",
                    "type": "string",
                    "multiValued": False,
                    "description": "Identifies the name of a department.",
                    "required": False,
                    "caseExact": False,
                    "mutability": "readWrite",
                    "returned": "default",
                    "uniqueness": "none",
                },
                {
                    "name": "manager",
                    "type": "complex",
                    "multiValued": False,
                    "description": (
                        "The User's manager.  A complex type that "
                        "optionally allows service providers to represent organizational "
                        "hierarchy by referencing the 'id' attribute of another User."
                    ),
                    "required": False,
                    "subAttributes": [
                        {
                            "name": "value",
                            "type": "string",
                            "multiValued": False,
                            "description": (
                                "The id of the SCIM resource representing "
                                "the User's manager.  REQUIRED."
                            ),
                            "required": False,
                            "caseExact": False,
                            "mutability": "readWrite",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                        {
                            "name": "$ref",
                            "type": "reference",
                            "referenceTypes": ["User"],
                            "multiValued": False,
                            "description": (
                                "The URI of the SCIM resource "
                                "representing the User's manager.  REQUIRED."
                            ),
                            "required": False,
                            "caseExact": False,
                            "mutability": "readWrite",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                        {
                            "name": "displayName",
                            "type": "string",
                            "multiValued": False,
                            "description": (
                                "The displayName of the User's manager. "
                                "OPTIONAL and READ-ONLY."
                            ),
                            "required": False,
                            "caseExact": False,
                            "mutability": "readOnly",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                    ],
                    "mutability": "readWrite",
                    "returned": "default",
                },
            ],
            "meta": {
                "resourceType": "Schema",
                "location": "/v2/Schemas/urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
            },
        },
    ]


@pytest.fixture
def service_provider_configuration_schema_payload():
    """https://www.rfc-editor.org/rfc/rfc7643#section-8.7.2"""
    return [
        {
            "id": "urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig",
            "name": "Service Provider Configuration",
            "description": (
                "Schema for representing the service provider's " "configuration"
            ),
            "attributes": [
                {
                    "name": "documentationUri",
                    "type": "reference",
                    "referenceTypes": ["external"],
                    "multiValued": False,
                    "description": (
                        "An HTTP-addressable URL pointing to the"
                        " service provider's human-consumable help documentation."
                    ),
                    "required": False,
                    "caseExact": False,
                    "mutability": "readOnly",
                    "returned": "default",
                    "uniqueness": "none",
                },
                {
                    "name": "patch",
                    "type": "complex",
                    "multiValued": False,
                    "description": (
                        "A complex type that specifies PATCH" " configuration options."
                    ),
                    "required": True,
                    "returned": "default",
                    "mutability": "readOnly",
                    "subAttributes": [
                        {
                            "name": "supported",
                            "type": "boolean",
                            "multiValued": False,
                            "description": (
                                "A Boolean value specifying whether or not"
                                " the operation is supported."
                            ),
                            "required": True,
                            "mutability": "readOnly",
                            "returned": "default",
                        }
                    ],
                },
                {
                    "name": "bulk",
                    "type": "complex",
                    "multiValued": False,
                    "description": (
                        "A complex type that specifies bulk" " configuration options."
                    ),
                    "required": True,
                    "returned": "default",
                    "mutability": "readOnly",
                    "subAttributes": [
                        {
                            "name": "supported",
                            "type": "boolean",
                            "multiValued": False,
                            "description": (
                                "A Boolean value specifying whether or not"
                                " the operation is supported."
                            ),
                            "required": True,
                            "mutability": "readOnly",
                            "returned": "default",
                        },
                        {
                            "name": "maxOperations",
                            "type": "integer",
                            "multiValued": False,
                            "description": (
                                "An integer value specifying the maximum"
                                " number of operations."
                            ),
                            "required": True,
                            "mutability": "readOnly",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                        {
                            "name": "maxPayloadSize",
                            "type": "integer",
                            "multiValued": False,
                            "description": (
                                "An integer value specifying the maximum"
                                " payload size in bytes."
                            ),
                            "required": True,
                            "mutability": "readOnly",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                    ],
                },
                {
                    "name": "filter",
                    "type": "complex",
                    "multiValued": False,
                    "description": ("A complex type that specifies" " FILTER options."),
                    "required": True,
                    "returned": "default",
                    "mutability": "readOnly",
                    "subAttributes": [
                        {
                            "name": "supported",
                            "type": "boolean",
                            "multiValued": False,
                            "description": (
                                "A Boolean value specifying whether or not"
                                " the operation is supported."
                            ),
                            "required": True,
                            "mutability": "readOnly",
                            "returned": "default",
                        },
                        {
                            "name": "maxResults",
                            "type": "integer",
                            "multiValued": False,
                            "description": (
                                "An integer value specifying the maximum"
                                " number of resources returned in a response."
                            ),
                            "required": True,
                            "mutability": "readOnly",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                    ],
                },
                {
                    "name": "changePassword",
                    "type": "complex",
                    "multiValued": False,
                    "description": (
                        "A complex type that specifies configuration"
                        " options related to changing a password."
                    ),
                    "required": True,
                    "returned": "default",
                    "mutability": "readOnly",
                    "subAttributes": [
                        {
                            "name": "supported",
                            "type": "boolean",
                            "multiValued": False,
                            "description": (
                                "A Boolean value specifying whether or not"
                                " the operation is supported."
                            ),
                            "required": True,
                            "mutability": "readOnly",
                            "returned": "default",
                        }
                    ],
                },
                {
                    "name": "sort",
                    "type": "complex",
                    "multiValued": False,
                    "description": (
                        "A complex type that specifies sort result" " options."
                    ),
                    "required": True,
                    "returned": "default",
                    "mutability": "readOnly",
                    "subAttributes": [
                        {
                            "name": "supported",
                            "type": "boolean",
                            "multiValued": False,
                            "description": (
                                "A Boolean value specifying whether or not"
                                " the operation is supported."
                            ),
                            "required": True,
                            "mutability": "readOnly",
                            "returned": "default",
                        }
                    ],
                },
                {
                    "name": "authenticationSchemes",
                    "type": "complex",
                    "multiValued": True,
                    "description": (
                        "A complex type that specifies supported"
                        " authentication scheme properties."
                    ),
                    "required": True,
                    "returned": "default",
                    "mutability": "readOnly",
                    "subAttributes": [
                        {
                            "name": "name",
                            "type": "string",
                            "multiValued": False,
                            "description": (
                                "The common authentication scheme name,"
                                " e.g., HTTP Basic."
                            ),
                            "required": True,
                            "caseExact": False,
                            "mutability": "readOnly",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                        {
                            "name": "description",
                            "type": "string",
                            "multiValued": False,
                            "description": (
                                "A description of the authentication" " scheme."
                            ),
                            "required": True,
                            "caseExact": False,
                            "mutability": "readOnly",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                        {
                            "name": "specUri",
                            "type": "reference",
                            "referenceTypes": ["external"],
                            "multiValued": False,
                            "description": (
                                "An HTTP-addressable URL pointing to the"
                                " authentication scheme's specification."
                            ),
                            "required": False,
                            "caseExact": False,
                            "mutability": "readOnly",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                        {
                            "name": "documentationUri",
                            "type": "reference",
                            "referenceTypes": ["external"],
                            "multiValued": False,
                            "description": (
                                "An HTTP-addressable URL pointing to the"
                                " authentication scheme's usage documentation."
                            ),
                            "required": False,
                            "caseExact": False,
                            "mutability": "readOnly",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                    ],
                },
            ],
        },
        {
            "id": "urn:ietf:params:scim:schemas:core:2.0:ResourceType",
            "name": "ResourceType",
            "description": (
                "Specifies the schema that describes a SCIM" " resource type"
            ),
            "attributes": [
                {
                    "name": "id",
                    "type": "string",
                    "multiValued": False,
                    "description": (
                        "The resource type's server unique id."
                        " May be the same as the 'name' attribute."
                    ),
                    "required": False,
                    "caseExact": False,
                    "mutability": "readOnly",
                    "returned": "default",
                    "uniqueness": "none",
                },
                {
                    "name": "name",
                    "type": "string",
                    "multiValued": False,
                    "description": (
                        "The resource type name.  When applicable,"
                        " service providers MUST specify the name, e.g., 'User'."
                    ),
                    "required": True,
                    "caseExact": False,
                    "mutability": "readOnly",
                    "returned": "default",
                    "uniqueness": "none",
                },
                {
                    "name": "description",
                    "type": "string",
                    "multiValued": False,
                    "description": (
                        "The resource type's human-readable"
                        " description.  When applicable, service providers MUST"
                        " specify the description."
                    ),
                    "required": False,
                    "caseExact": False,
                    "mutability": "readOnly",
                    "returned": "default",
                    "uniqueness": "none",
                },
                {
                    "name": "endpoint",
                    "type": "reference",
                    "referenceTypes": ["uri"],
                    "multiValued": False,
                    "description": (
                        "The resource type's HTTP-addressable"
                        " endpoint relative to the Base URL, e.g., '/Users'."
                    ),
                    "required": True,
                    "caseExact": False,
                    "mutability": "readOnly",
                    "returned": "default",
                    "uniqueness": "none",
                },
                {
                    "name": "schema",
                    "type": "reference",
                    "referenceTypes": ["uri"],
                    "multiValued": False,
                    "description": ("The resource type's primary/base schema" " URI."),
                    "required": True,
                    "caseExact": True,
                    "mutability": "readOnly",
                    "returned": "default",
                    "uniqueness": "none",
                },
                {
                    "name": "schemaExtensions",
                    "type": "complex",
                    "multiValued": False,
                    "description": (
                        "A list of URIs of the resource type's schema" " extensions."
                    ),
                    "required": True,
                    "mutability": "readOnly",
                    "returned": "default",
                    "subAttributes": [
                        {
                            "name": "schema",
                            "type": "reference",
                            "referenceTypes": ["uri"],
                            "multiValued": False,
                            "description": "The URI of a schema extension.",
                            "required": True,
                            "caseExact": True,
                            "mutability": "readOnly",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                        {
                            "name": "required",
                            "type": "boolean",
                            "multiValued": False,
                            "description": (
                                "A Boolean value that specifies whether"
                                " or not the schema extension is required for the"
                                " resource type.  If True, a resource of this type MUST"
                                " include this schema extension and also include any"
                                " attributes declared as required in this schema extension."
                                " If False, a resource of this type MAY omit this schema"
                                " extension."
                            ),
                            "required": True,
                            "mutability": "readOnly",
                            "returned": "default",
                        },
                    ],
                },
            ],
        },
        {
            "id": "urn:ietf:params:scim:schemas:core:2.0:Schema",
            "name": "Schema",
            "description": ("Specifies the schema that describes a" " SCIM schema"),
            "attributes": [
                {
                    "name": "id",
                    "type": "string",
                    "multiValued": False,
                    "description": (
                        "The unique URI of the schema."
                        " When applicable, service providers MUST specify the URI."
                    ),
                    "required": True,
                    "caseExact": False,
                    "mutability": "readOnly",
                    "returned": "default",
                    "uniqueness": "none",
                },
                {
                    "name": "name",
                    "type": "string",
                    "multiValued": False,
                    "description": (
                        "The schema's human-readable name.  When"
                        " applicable, service providers MUST specify the name,"
                        " e.g., 'User'."
                    ),
                    "required": True,
                    "caseExact": False,
                    "mutability": "readOnly",
                    "returned": "default",
                    "uniqueness": "none",
                },
                {
                    "name": "description",
                    "type": "string",
                    "multiValued": False,
                    "description": (
                        "The schema's human-readable name.  When"
                        " applicable, service providers MUST specify the name,"
                        " e.g., 'User'."
                    ),
                    "required": False,
                    "caseExact": False,
                    "mutability": "readOnly",
                    "returned": "default",
                    "uniqueness": "none",
                },
                {
                    "name": "attributes",
                    "type": "complex",
                    "multiValued": True,
                    "description": (
                        "A complex attribute that includes the"
                        " attributes of a schema."
                    ),
                    "required": True,
                    "mutability": "readOnly",
                    "returned": "default",
                    "subAttributes": [
                        {
                            "name": "name",
                            "type": "string",
                            "multiValued": False,
                            "description": "The attribute's name.",
                            "required": True,
                            "caseExact": True,
                            "mutability": "readOnly",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                        {
                            "name": "type",
                            "type": "string",
                            "multiValued": False,
                            "description": (
                                "The attribute's data type."
                                " Valid values include 'string', 'complex', 'boolean',"
                                " 'decimal', 'integer', 'dateTime', 'reference'."
                            ),
                            "required": True,
                            "canonicalValues": [
                                "string",
                                "complex",
                                "boolean",
                                "decimal",
                                "integer",
                                "dateTime",
                                "reference",
                            ],
                            "caseExact": False,
                            "mutability": "readOnly",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                        {
                            "name": "multiValued",
                            "type": "boolean",
                            "multiValued": False,
                            "description": (
                                "A Boolean value indicating an "
                                " attribute's plurality."
                            ),
                            "required": True,
                            "mutability": "readOnly",
                            "returned": "default",
                        },
                        {
                            "name": "description",
                            "type": "string",
                            "multiValued": False,
                            "description": (
                                "A human-readable description of the" " attribute."
                            ),
                            "required": False,
                            "caseExact": True,
                            "mutability": "readOnly",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                        {
                            "name": "required",
                            "type": "boolean",
                            "multiValued": False,
                            "description": (
                                "A boolean value indicating whether or"
                                " not the attribute is required."
                            ),
                            "required": False,
                            "mutability": "readOnly",
                            "returned": "default",
                        },
                        {
                            "name": "canonicalValues",
                            "type": "string",
                            "multiValued": True,
                            "description": (
                                "A collection of canonical values.  When "
                                " applicable, service providers MUST specify the"
                                " canonical types, e.g., 'work', 'home'."
                            ),
                            "required": False,
                            "caseExact": True,
                            "mutability": "readOnly",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                        {
                            "name": "caseExact",
                            "type": "boolean",
                            "multiValued": False,
                            "description": (
                                "A Boolean value indicating whether or"
                                " not a string attribute is case sensitive."
                            ),
                            "required": False,
                            "mutability": "readOnly",
                            "returned": "default",
                        },
                        {
                            "name": "mutability",
                            "type": "string",
                            "multiValued": False,
                            "description": (
                                "Indicates whether or not an attribute"
                                " is modifiable."
                            ),
                            "required": False,
                            "caseExact": True,
                            "mutability": "readOnly",
                            "returned": "default",
                            "uniqueness": "none",
                            "canonicalValues": [
                                "readOnly",
                                "readWrite",
                                "immutable",
                                "writeOnly",
                            ],
                        },
                        {
                            "name": "returned",
                            "type": "string",
                            "multiValued": False,
                            "description": (
                                "Indicates when an attribute is returned"
                                " in a response (e.g., to a query)."
                            ),
                            "required": False,
                            "caseExact": True,
                            "mutability": "readOnly",
                            "returned": "default",
                            "uniqueness": "none",
                            "canonicalValues": [
                                "always",
                                "never",
                                "default",
                                "request",
                            ],
                        },
                        {
                            "name": "uniqueness",
                            "type": "string",
                            "multiValued": False,
                            "description": "Indicates how unique a value must be.",
                            "required": False,
                            "caseExact": True,
                            "mutability": "readOnly",
                            "returned": "default",
                            "uniqueness": "none",
                            "canonicalValues": ["none", "server", "global"],
                        },
                        {
                            "name": "referenceTypes",
                            "type": "string",
                            "multiValued": True,
                            "description": (
                                "Used only with an attribute of type"
                                " 'reference'.  Specifies a SCIM resourceType that a"
                                " reference attribute MAY refer to, e.g., 'User'."
                            ),
                            "required": False,
                            "caseExact": True,
                            "mutability": "readOnly",
                            "returned": "default",
                            "uniqueness": "none",
                        },
                        {
                            "name": "subAttributes",
                            "type": "complex",
                            "multiValued": True,
                            "description": (
                                "Used to define the sub-attributes of a"
                                " complex attribute."
                            ),
                            "required": False,
                            "mutability": "readOnly",
                            "returned": "default",
                            "subAttributes": [
                                {
                                    "name": "name",
                                    "type": "string",
                                    "multiValued": False,
                                    "description": "The attribute's name.",
                                    "required": True,
                                    "caseExact": True,
                                    "mutability": "readOnly",
                                    "returned": "default",
                                    "uniqueness": "none",
                                },
                                {
                                    "name": "type",
                                    "type": "string",
                                    "multiValued": False,
                                    "description": (
                                        "The attribute's data type."
                                        " Valid values include 'string', 'complex', 'boolean',"
                                        " 'decimal', 'integer', 'dateTime', 'reference'."
                                    ),
                                    "required": True,
                                    "caseExact": False,
                                    "mutability": "readOnly",
                                    "returned": "default",
                                    "uniqueness": "none",
                                    "canonicalValues": [
                                        "string",
                                        "complex",
                                        "boolean",
                                        "decimal",
                                        "integer",
                                        "dateTime",
                                        "reference",
                                    ],
                                },
                                {
                                    "name": "multiValued",
                                    "type": "boolean",
                                    "multiValued": False,
                                    "description": (
                                        "A Boolean value indicating an"
                                        " attribute's plurality."
                                    ),
                                    "required": True,
                                    "mutability": "readOnly",
                                    "returned": "default",
                                },
                                {
                                    "name": "description",
                                    "type": "string",
                                    "multiValued": False,
                                    "description": (
                                        "A human-readable description of the"
                                        " attribute."
                                    ),
                                    "required": False,
                                    "caseExact": True,
                                    "mutability": "readOnly",
                                    "returned": "default",
                                    "uniqueness": "none",
                                },
                                {
                                    "name": "required",
                                    "type": "boolean",
                                    "multiValued": False,
                                    "description": (
                                        "A boolean value indicating whether or"
                                        " not the attribute is required."
                                    ),
                                    "required": False,
                                    "mutability": "readOnly",
                                    "returned": "default",
                                },
                                {
                                    "name": "canonicalValues",
                                    "type": "string",
                                    "multiValued": True,
                                    "description": (
                                        "A collection of canonical values.  When"
                                        " applicable, service providers MUST specify the"
                                        " canonical types, e.g., 'work', 'home'."
                                    ),
                                    "required": False,
                                    "caseExact": True,
                                    "mutability": "readOnly",
                                    "returned": "default",
                                    "uniqueness": "none",
                                },
                                {
                                    "name": "caseExact",
                                    "type": "boolean",
                                    "multiValued": False,
                                    "description": (
                                        "A Boolean value indicating whether or"
                                        " not a string attribute is case sensitive."
                                    ),
                                    "required": False,
                                    "mutability": "readOnly",
                                    "returned": "default",
                                },
                                {
                                    "name": "mutability",
                                    "type": "string",
                                    "multiValued": False,
                                    "description": (
                                        "Indicates whether or not an"
                                        " attribute is modifiable."
                                    ),
                                    "required": False,
                                    "caseExact": True,
                                    "mutability": "readOnly",
                                    "returned": "default",
                                    "uniqueness": "none",
                                    "canonicalValues": [
                                        "readOnly",
                                        "readWrite",
                                        "immutable",
                                        "writeOnly",
                                    ],
                                },
                                {
                                    "name": "returned",
                                    "type": "string",
                                    "multiValued": False,
                                    "description": (
                                        "Indicates when an attribute is"
                                        " returned in a response (e.g., to a query)."
                                    ),
                                    "required": False,
                                    "caseExact": True,
                                    "mutability": "readOnly",
                                    "returned": "default",
                                    "uniqueness": "none",
                                    "canonicalValues": [
                                        "always",
                                        "never",
                                        "default",
                                        "request",
                                    ],
                                },
                                {
                                    "name": "uniqueness",
                                    "type": "string",
                                    "multiValued": False,
                                    "description": "Indicates how unique a value must be.",
                                    "required": False,
                                    "caseExact": True,
                                    "mutability": "readOnly",
                                    "returned": "default",
                                    "uniqueness": "none",
                                    "canonicalValues": ["none", "server", "global"],
                                },
                                {
                                    "name": "referenceTypes",
                                    "type": "string",
                                    "multiValued": False,
                                    "description": (
                                        "Used only with an attribute of type"
                                        " 'reference'.  Specifies a SCIM resourceType that a"
                                        " reference attribute MAY refer to, e.g., 'User'."
                                    ),
                                    "required": False,
                                    "caseExact": True,
                                    "mutability": "readOnly",
                                    "returned": "default",
                                    "uniqueness": "none",
                                },
                            ],
                        },
                    ],
                },
            ],
        },
    ]
