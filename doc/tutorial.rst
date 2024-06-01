Tutorial
--------

Model parsing
=============

Pydantic :func:`~pydantic_scim2.BaseModel.model_validate` method can be used to parse and validate SCIM2 payloads.
Python models have generally the same name than in the SCIM specifications, they are simply snake cased.


.. code-block:: python
    :emphasize-lines: 17

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

Pydantic :func:`~pydantic_scim2.BaseModel.model_dump` method have been tuned to produce valid SCIM2 payloads.

.. code-block:: python
    :emphasize-lines: 16

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

    >>> dump = user.model_dump()
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

Contexts
========

The SCIM specifications detail some :class:`~pydantic_scim2.Mutability` and :class:`~pydantic_scim2.Returned` parameters for model attributes.
Depending on the context, they will indicate that attributes should be present, absent, be ignored.

For instance, attributes marked as :attr:`~pydantic_scim2.Mutability.read_only` should not be sent by SCIM clients on resource creation requests.
By passing the right :class:`~pydantic_scim2.Context` to the :meth:`~pydantic_scim2.BaseModel.model_dump` method, only the expected fields will be dumped for this context:

.. code-block:: python
    :caption: Client generating a resource creation request payload

    >>> from pydantic_scim2 import User, Context
    >>> user = User(user_name="bjensen@example.com")
    >>> payload = user.model_dump(scim_ctx=Context.RESOURCE_CREATION_REQUEST)

In the same fashion, by passing the right :class:`~pydantic_scim2.Context` to the :meth:`~pydantic_scim2.BaseModel.model_validate` method,
fields with unexpected values will raise :class:`~pydantic.ValidationError`:

.. code-block:: python
    :caption: Server validating a resource creation request payload

    >>> from pydantic_scim2 import User, Context
    >>> from pydantic import ValidationError
    >>> try:
    ...    obj = User.model_validate(payload, scim_ctx=Context.RESOURCE_CREATION_REQUEST)
    ... except pydantic.ValidationError:
    ...    obj = Error(...)

Attributes inclusions and exclusions
====================================

In some situations it might be needed to exclude, or only include a given set of attributes when serializing a model.
This happens for instance when servers build response payloads for clients requesting only a sub-set the model attributes.
As defined in :rfc:`RFC7644 §3.9 <7644#section-3.9>`, :code:`attributes` and :code:`excluded_attributes` parameters can
be passed to :meth:`~pydantic_scim2.BaseModel.model_dump`.
The expected attribute notation is the one detailed on :rfc:`RFC7644 §3.10 <7644#section-3.10>`,
like :code:`urn:ietf:params:scim:schemas:core:2.0:User:userName`, or :code:`userName` for short.

.. code-block:: python
    :emphasize-lines: 5

    >>> from pydantic_scim2 import User, Context
    >>> user = User(user_name="bjensen@example.com", display_name="bjensen")
    >>> payload = user.model_dump(
    ...     scim_ctx=Context.RESOURCE_QUERY_REQUEST,
    ...     excluded_attributes=["displayName"]
    ... )
    >>> assert payload == {
    ...     "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
    ...     "userName": "bjensen@example.com",
    ...     "displayName": "bjensen",
    ... }

Values read from :attr:`~pydantic_scim2.SearchRequest.attributes` and :attr:`~pydantic_scim2.SearchRequest.excluded_attributes` in :class:`~pydantic_scim2.SearchRequest` objects can directly be used in :meth:`~pydantic_scim2.BaseModel.model_dump`.

Attribute inclusions and exclusions interact with attributes :class:`~pydantic_scim2.Returned`, in the server response :class:`Contexts <pydantic_scim2.Context>`:

- attributes annotated with :attr:`~pydantic_scim2.Returned.always` will always be dumped;
- attributes annotated with :attr:`~pydantic_scim2.Returned.never` will never be dumped;
- attributes annotated with :attr:`~pydantic_scim2.Returned.default` will be dumped unless being explicitly excluded;
- attributes annotated with :attr:`~pydantic_scim2.Returned.request` will be not dumped unless being explicitly included.

Typed ListResponse
==================

:class:`~pydantic_scim2.ListResponse` models take a type or a :data:`~typing.Union` of types.
You must pass the type you expect in the response, e.g. :class:`~pydantic_scim2.ListResponse.of(User)` or :class:`~pydantic_scim2.ListResponse.of(User, Group)`.
If a response resource type cannot be found, a ``pydantic.ValidationError`` will be raised.

.. code-block:: python
    :emphasize-lines: 49

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

    >>> response = ListResponse.of(User, Group).model_validate(payload)
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

.. code-block:: python

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

    >>> user[EnterpriseUser] = EnterpriseUser(employee_number = "701984")
    >>> user[EnterpriseUser].division="Theme Park"
    >>> dump = user.model_dump()
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
    ...         "employeeNumber": "701984",
    ...         "division": "Theme Park",
    ...     }
    ... }


Pre-defined Error objects
=========================

:rfc:`RFC7643 §3.12 <7643#section-3.12>` pre-defined errors are usable.

.. code-block:: python

    >>> from pydantic_scim2 import InvalidPathError

    >>> dump = InvalidPathError.model_dump()
    >>> assert dump == {
    ...     'detail': 'The "path" attribute was invalid or malformed (see Figure 7 of RFC7644).',
    ...     'schemas': ['urn:ietf:params:scim:api:messages:2.0:Error'],
    ...     'scimType': 'invalidPath',
    ...     'status': '400'
    ... }

The exhaustive list is availaible in the :class:`reference <pydantic_scim2.Error>`.


Custom models
=============

You can write your own model and use it the same way than the other pydantic-scim2 models.
Just inherit from :class:`~pydantic_scim2.Resource` for your main resource,
and from :class:`~pydantic_scim2.ComplexAttribute` for the complex attributes:

.. code-block:: python

    >>> from typing import Annotated, Optional
    >>> from pydantic_scim2 import Resource, Returned, Mutability, ComplexAttribute
    >>> from enum import Enum

    >>> class PetType(ComplexAttribute):
    ...     type: Optional[str]
    ...     """The pet type like 'cat' or 'dog'."""
    ...
    ...     color: Optional[str]
    ...     """The pet color."""

    >>> class Pet(Resource):
    ...     name : Annotated[Optional[str], Mutability.immutable, Returned.always]
    ...     """The name of the pet."""
    ...
    ...     pet_type: Optional[PetType]
    ...     """The pet type."""

You can annotate fields to indicate their :class:`~pydantic_scim2.Mutability` and :class:`~pydantic_scim2.Returned`.
If unset the default values will be :attr:`~pydantic_scim2.Mutability.read_write` and :attr:`~pydantic_scim2.Returned.default`.

.. warning::

    Be sure to make all the fields of your model :data:`~typing.Optional`.
    There will always be a :class:`~pydantic_scim2.Context` in which this will be true.
