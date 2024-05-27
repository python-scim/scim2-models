Tutorial
--------

Model parsing
=============

Pydantic :func:`~pydantic.BaseModel.model_validate` method can be used to parse and validate SCIM2 payloads.
Python models have generally the same name than in the SCIM specifications, they are simply snake cased.


.. code-block:: python

    from pydantic_scim2 import User
    import datetime

    payload = {
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

    user = User.model_validate(payload)
    assert user.user_name == "bjensen@example.com"
    assert user.meta.created == datetime.datetime(
        2010, 1, 23, 4, 56, 22, tzinfo=datetime.timezone.utc
    )


Model serialization
===================

Pydantic :func:`~pydantic.BaseModel.model_dump` method can be used to produce valid SCIM2 payloads:

.. code-block:: python

    from pydantic_scim2 import User, Meta
    import datetime

    user = User(
        id="2819c223-7f76-453a-919d-413861904646",
        user_name="bjensen@example.com",
        meta=Meta(
            resource_type="User",
            created=datetime.datetime(2010, 1, 23, 4, 56, 22, tzinfo=datetime.timezone.utc),
            last_modified=datetime.datetime(2011, 5, 13, 4, 42, 34, tzinfo=datetime.timezone.utc),
            version='W\\/"3694e05e9dff590"',
            location="https://example.com/v2/Users/2819c223-7f76-453a-919d-413861904646",
        ),
    )
    dump = user.model_dump(exclude_none=True, by_alias=True, mode="json")
    assert dump == {
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


Typed ListResponse
==================

:class:`~pydantic_scim2.ListResponse` models take a type or a :data:`~typing.Union` of types.
You must pass the type you expect in the response, e.g. :class:`~pydantic_scim2.ListResponse[User]` or :class:`~pydantic_scim2.ListResponse[Union[User, Group]]`.
If a response resource type cannot be found, a `pydantic.ValidationError` will be raised.

.. code-block:: python

    from typing import Union
    from pydantic_scim2 import User, Group, ListResponse

    payload = {
        "totalResults": 2,
        "itemsPerPage": 10,
        "startIndex": 1,
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "Resources": [
            {
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
            },
            {
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
            },
        ],
    }

    response = ListResponse[Union[User, Group]].model_validate(payload)
    user, group = response.resources
    assert isinstance(user, User)
    assert isinstance(group, Group)


Schema extensions
=================

:rfc:`RFC7643 §3.3 <7643#section-3.3>` extensions are supported.
Extensions must be passed as resource type parameter, e.g. ``user = User[EnterpriseUser]`` or ``user = User[EnterpriseUser, SuperHero]``.
Extensions attributes are accessed with brackets, e.g. ``user[EnterpriseUser].employee_number``.

.. code-block:: python

    import datetime
    from pydantic_scim2 import User, EnterpriseUser, Meta

    user = User[EnterpriseUser](
        id="2819c223-7f76-453a-919d-413861904646",
        user_name="bjensen@example.com",
        meta=Meta(
            resource_type="User",
            created=datetime.datetime(
                2010, 1, 23, 4, 56, 22, tzinfo=datetime.timezone.utc
            ),
        ),
    )
    user[EnterpriseUser].employee_number = "701984"
    dump = user.model_dump(exclude_none=True, by_alias=True, mode="json")
    assert dump == {
        "schemas": [
            "urn:ietf:params:scim:schemas:core:2.0:User",
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"
        ],
        "id": "2819c223-7f76-453a-919d-413861904646",
        "meta": {
            "resourceType": "User",
            "created": "2010-01-23T04:56:22Z"
        },
        "userName": "bjensen@example.com",
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
            "schemas": [
                "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"
            ],
            "employeeNumber": "701984"
        }
    }


Pre-defined Error objects
=========================

:rfc:`RFC7643 §3.12 <7643#section-3.12>` pre-defined errors are usable.

.. code-block:: python

    from pydantic_scim2 import InvalidPathError

    dump = InvalidPathError.model_dump(exclude_none=True, by_alias=True, mode="json")
    assert dump == {
        'detail': 'The "path" attribute was invalid or malformed.',
        'schemas': ['urn:ietf:params:scim:api:messages:2.0:Error'],
        'scimType': 'invalidPath',
        'status': '400'
    }

Here is the exhaustive list of pre-defined errors:

.. py:data:: pydanti_scim2.InvalidFilterError

   The specified filter syntax
   was invalid (does not comply
   with :rfc:`Figure 1 of RFC7644 <7644#section-3.4.2.2>`), or the
   specified attribute and filter
   comparison combination is not
   supported.

.. py:data:: pydanti_scim2.TooManyError

   The specified filter yields
   many more results than the
   server is willing to calculate
   or process.  For example, a
   filter such as ``(userName pr)``
   by itself would return all
   entries with a ``userName`` and
   MAY not be acceptable to the
   service provider.

.. py:data:: pydanti_scim2.UniquenessError

   One or more of the attribute
   values are already in use or
   are reserved.

.. py:data:: pydanti_scim2.MutabilityError

   The attempted modification is
   not compatible with the target
   attribute's mutability or
   current state (e.g.,
   modification of an "immutable"
   attribute with an existing
   value).

.. py:data:: pydanti_scim2.InvalidSyntaxError

   The request body message
   structure was invalid or did
   not conform to the request
   schema.

.. py:data:: pydanti_scim2.InvalidPathError

   The "path" attribute was
   invalid or malformed (see
   :rfc:`Figure 7 of RFC7644 <7644#section-3.5.2>`).

.. py:data:: pydanti_scim2.NoTargetError

   The specified "path" did not
   yield an attribute or
   attribute value that could be
   operated on.  This occurs when
   the specified "path" value
   contains a filter that yields
   no match.

.. py:data:: pydanti_scim2.InvalidValueError

   A required value was missing,
   or the value specified was not
   compatible with the operation
   or attribute type (see :rfc:`Section
   2.2 of RFC7643 <7643#section-2.2>`), or resource
   schema (see :rfc:`Section 4 of
   RFC7643 <7643#section-4>`).

.. py:data:: pydanti_scim2.InvalidVersionError

   The specified SCIM protocol
   version is not supported (see
   :rfc:`Section 3.13 of RFC7644 <7644#section-3.13>`).

.. py:data:: pydanti_scim2.SensitiveError

   The specified request cannot
   be completed, due to the
   passing of sensitive (e.g.,
   personal) information in a
   request URI.  For example,
   personal information SHALL NOT
   be transmitted over request
   URIs.  See :rfc:`Section 7.5.2 of RFC7644 <7644#section-7.5.2>`.



Custom models
=============

You can write your own model and use it the same way than the other pydantic-scim2 models. Just inherit from :class:`~pydantic_scim2.Resource`:

.. code-block:: python

    from pydantic_scim2 import Resource
    from enum import Enum

    class Pet(Resource):
        class Type(str, Enum):
            dog = "dog"
            cat = "cat"

        name : str
        """The name of the pet."""

        type: Type
        """The pet type."""
