Tutorial
--------

Model parsing
=============

Pydantic :func:`~pydantic.BaseModel.model_validate` method can be used to parse and validate SCIM2 payloads.
Python models have generally the same name than in the SCIM specifications, they are simply snake cased.


.. doctest::

    >>> from pydantic_scim2 import User
    >>> import datetime

    >>> payload = {
    ...     "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
    ...     "id": "2819c223-7f76-453a-919d-413861904646",
    ...     "userName": "bjensen@example.com",
    ...     "meta": {
    ...         "resourceType": "User",
    ...         "created": "2010-01-23T04:56:22Z",
    ...         "lastModified": "2011-05-13T04:42:34Z",
    ...         "version": 'W\\/"3694e05e9dff590"',
    ...         "location": "https://example.com/v2/Users/2819c223-7f76-453a-919d-413861904646",
    ...     },
    ... }

    >>> user = User.model_validate(payload)
    >>> user.user_name
    'bjensen@example.com'
    >>> user.meta.created
    datetime.datetime(2010, 1, 23, 4, 56, 22, tzinfo=TzInfo(UTC))


Model serialization
===================

Pydantic :func:`~pydantic.BaseModel.model_dump` method can be used to produce valid SCIM2 payloads:

.. doctest::

    >>> from pydantic_scim2 import User, Meta
    >>> import datetime

    >>> user = User(
    ...     id="2819c223-7f76-453a-919d-413861904646",
    ...     user_name="bjensen@example.com",
    ...     meta=Meta(
    ...         resource_type="User",
    ...         created=datetime.datetime(2010, 1, 23, 4, 56, 22, tzinfo=datetime.timezone.utc),
    ...         last_modified=datetime.datetime(2011, 5, 13, 4, 42, 34, tzinfo=datetime.timezone.utc),
    ...         version='W\\/"3694e05e9dff590"',
    ...         location="https://example.com/v2/Users/2819c223-7f76-453a-919d-413861904646",
    ...     ),
    ... )

    >>> dump = user.model_dump(exclude_none=True, by_alias=True, mode="json")
    >>> assert dump == {
    ...     "schemas": [
    ...         "urn:ietf:params:scim:schemas:core:2.0:User"
    ...     ],
    ...     "id": "2819c223-7f76-453a-919d-413861904646",
    ...     "meta": {
    ...         "resourceType": "User",
    ...         "created": "2010-01-23T04:56:22Z",
    ...         "lastModified": "2011-05-13T04:42:34Z",
    ...         "location": "https://example.com/v2/Users/2819c223-7f76-453a-919d-413861904646",
    ...         "version": "W\\/\"3694e05e9dff590\""
    ...     },
    ...     "userName": "bjensen@example.com"
    ... }

Typed ListResponse
==================

:class:`~pydantic_scim2.ListResponse` models take a type or a :data:`~typing.Union` of types.
You must pass the type you expect in the response, e.g. :class:`~pydantic_scim2.ListResponse[User]` or :class:`~pydantic_scim2.ListResponse[Union[User, Group]]`.
If a response resource type cannot be found, a ``pydantic.ValidationError`` will be raised.

.. doctest::

    >>> from typing import Union
    >>> from pydantic_scim2 import User, Group, ListResponse

    >>> payload = {
    ...     "totalResults": 2,
    ...     "itemsPerPage": 10,
    ...     "startIndex": 1,
    ...     "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
    ...     "Resources": [
    ...         {
    ...             "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
    ...             "id": "2819c223-7f76-453a-919d-413861904646",
    ...             "userName": "bjensen@example.com",
    ...             "meta": {
    ...                 "resourceType": "User",
    ...                 "created": "2010-01-23T04:56:22Z",
    ...                 "lastModified": "2011-05-13T04:42:34Z",
    ...                 "version": 'W\\/"3694e05e9dff590"',
    ...                 "location": "https://example.com/v2/Users/2819c223-7f76-453a-919d-413861904646",
    ...             },
    ...         },
    ...         {
    ...             "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"],
    ...             "id": "e9e30dba-f08f-4109-8486-d5c6a331660a",
    ...             "displayName": "Tour Guides",
    ...             "members": [
    ...                 {
    ...                     "value": "2819c223-7f76-453a-919d-413861904646",
    ...                     "$ref": "https://example.com/v2/Users/2819c223-7f76-453a-919d-413861904646",
    ...                     "display": "Babs Jensen",
    ...                 },
    ...                 {
    ...                     "value": "902c246b-6245-4190-8e05-00816be7344a",
    ...                     "$ref": "https://example.com/v2/Users/902c246b-6245-4190-8e05-00816be7344a",
    ...                     "display": "Mandy Pepperidge",
    ...                 },
    ...             ],
    ...             "meta": {
    ...                 "resourceType": "Group",
    ...                 "created": "2010-01-23T04:56:22Z",
    ...                 "lastModified": "2011-05-13T04:42:34Z",
    ...                 "version": 'W\\/"3694e05e9dff592"',
    ...                 "location": "https://example.com/v2/Groups/e9e30dba-f08f-4109-8486-d5c6a331660a",
    ...             },
    ...         },
    ...     ],
    ... }

    >>> response = ListResponse[Union[User, Group]].model_validate(payload)
    >>> user, group = response.resources
    >>> type(user)
    <class 'pydantic_scim2.rfc7643.user.User'>
    >>> type(group)
    <class 'pydantic_scim2.rfc7643.group.Group'>


Schema extensions
=================

:rfc:`RFC7643 §3.3 <7643#section-3.3>` extensions are supported.
Extensions must be passed as resource type parameter, e.g. ``user = User[EnterpriseUser]`` or ``user = User[EnterpriseUser, SuperHero]``.
Extensions attributes are accessed with brackets, e.g. ``user[EnterpriseUser].employee_number``.

.. doctest::

    >>> import datetime
    >>> from pydantic_scim2 import User, EnterpriseUser, Meta

    >>> user = User[EnterpriseUser](
    ...     id="2819c223-7f76-453a-919d-413861904646",
    ...     user_name="bjensen@example.com",
    ...     meta=Meta(
    ...         resource_type="User",
    ...         created=datetime.datetime(
    ...             2010, 1, 23, 4, 56, 22, tzinfo=datetime.timezone.utc
    ...         ),
    ...     ),
    ... )

    >>> user[EnterpriseUser].employee_number = "701984"
    >>> dump = user.model_dump(exclude_none=True, by_alias=True, mode="json")
    >>> assert dump == {
    ...     "schemas": [
    ...         "urn:ietf:params:scim:schemas:core:2.0:User",
    ...         "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"
    ...     ],
    ...     "id": "2819c223-7f76-453a-919d-413861904646",
    ...     "meta": {
    ...         "resourceType": "User",
    ...         "created": "2010-01-23T04:56:22Z"
    ...     },
    ...     "userName": "bjensen@example.com",
    ...     "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
    ...         "schemas": [
    ...             "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"
    ...         ],
    ...         "employeeNumber": "701984"
    ...     }
    ... }


Pre-defined Error objects
=========================

:rfc:`RFC7643 §3.12 <7643#section-3.12>` pre-defined errors are usable.

.. doctest::

    >>> from pydantic_scim2 import InvalidPathError

    >>> dump = InvalidPathError.model_dump(exclude_none=True, by_alias=True, mode="json")
    >>> assert dump == {
    ...     'detail': 'The "path" attribute was invalid or malformed (see Figure 7 of RFC7644).',
    ...     'schemas': ['urn:ietf:params:scim:api:messages:2.0:Error'],
    ...     'scimType': 'invalidPath',
    ...     'status': '400'
    ... }

The exhaustive list is availaible in the :class:`reference <pydantic_scim2.Error>`.


Custom models
=============

You can write your own model and use it the same way than the other pydantic-scim2 models. Just inherit from :class:`~pydantic_scim2.Resource`:

.. doctest::

    >>> from pydantic_scim2 import Resource
    >>> from enum import Enum

    >>> class Pet(Resource):
    ...     class Type(str, Enum):
    ...         dog = "dog"
    ...         cat = "cat"
    ...
    ...     name : str
    ...     """The name of the pet."""
    ...
    ...     type: Type
    ...     """The pet type."""
