Tutorial
--------

Attribute access
================

SCIM resources support two ways to access and modify attributes.
The standard Python dot notation uses snake_case attribute names, while the bracket notation accepts SCIM paths as defined in :rfc:`RFC7644 §3.10 <7644#section-3.10>`.

.. doctest::

    >>> from scim2_models import User

    >>> user = User(user_name="bjensen")
    >>> user.display_name = "Barbara Jensen"
    >>> user["nickName"] = "Babs"
    >>> user["name.familyName"] = "Jensen"

Attributes can be removed with ``del`` or by assigning :data:`None` to the attribute.

.. doctest::

    >>> del user["nickName"]
    >>> user.nick_name is None
    True

Model parsing
=============

Use Pydantic's :func:`~scim2_models.BaseModel.model_validate` method to parse and validate SCIM2 payloads.


.. code-block:: python
    :emphasize-lines: 17

    >>> from scim2_models import User
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
    >>> user.meta.created  # doctest: +ELLIPSIS
    datetime.datetime(2010, 1, 23, 4, 56, 22, tzinfo=...)

Payloads that have not been decoded yet can be handled by
:func:`~scim2_models.BaseModel.model_validate_json`.
Malformed JSON raises a :class:`~pydantic_core.ValidationError`, like any other invalid payload.

.. code-block:: python

    >>> import json

    >>> user = User.model_validate_json(json.dumps(payload))
    >>> user.user_name
    'bjensen@example.com'


Model serialization
===================

Pydantic :func:`~scim2_models.BaseModel.model_dump` method has been tuned to produce valid SCIM2 payloads.

.. code-block:: python
    :emphasize-lines: 16

    >>> from scim2_models import User, Meta
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

The SCIM specifications detail some :class:`~scim2_models.Mutability` and :class:`~scim2_models.Returned` parameters for model attributes.
Depending on the context, they will indicate that attributes should be present, absent, or ignored.

For instance, attributes marked as :attr:`~scim2_models.Mutability.read_only` should not be sent by SCIM clients on resource creation requests.
By passing the right :class:`~scim2_models.Context` to the :meth:`~scim2_models.BaseModel.model_dump` method, only the expected fields will be dumped for this context:

.. code-block:: python
    :caption: Client generating a resource creation request payload

    >>> from scim2_models import User, Context
    >>> user = User(user_name="bjensen@example.com")
    >>> payload = user.model_dump(scim_ctx=Context.RESOURCE_CREATION_REQUEST)

In the same fashion, by passing the right :class:`~scim2_models.Context` to the :meth:`~scim2_models.BaseModel.model_validate` method,
fields with unexpected values will raise :class:`~pydantic_core.ValidationError`:

.. code-block:: python
    :caption: Server validating a resource creation request payload

    >>> from scim2_models import User, Context, Error
    >>> from pydantic import ValidationError
    >>> try:
    ...    obj = User.model_validate(payload, scim_ctx=Context.RESOURCE_CREATION_REQUEST)
    ... except ValidationError:
    ...    obj = Error(...)

:meth:`~scim2_models.BaseModel.model_validate_json` takes the same :paramref:`~scim2_models.BaseModel.model_validate_json.scim_ctx` parameter.

Context annotations
===================

Context type aliases
^^^^^^^^^^^^^^^^^^^^

scim2-models provides generic type aliases that wrap
:class:`~scim2_models.SCIMValidator` and :class:`~scim2_models.SCIMSerializer` for each
SCIM context.  ``*RequestContext`` aliases inject the context during **validation**,
``*ResponseContext`` aliases during **serialization**:

- :class:`~scim2_models.CreationRequestContext` / :class:`~scim2_models.CreationResponseContext` — resource creation (``POST``)
- :class:`~scim2_models.QueryRequestContext` / :class:`~scim2_models.QueryResponseContext` — resource query (``GET``)
- :class:`~scim2_models.ReplacementRequestContext` / :class:`~scim2_models.ReplacementResponseContext` — resource replacement (``PUT``)
- :class:`~scim2_models.SearchRequestContext` / :class:`~scim2_models.SearchResponseContext` — search (``POST /…/.search``)
- :class:`~scim2_models.PatchRequestContext` / :class:`~scim2_models.PatchResponseContext` — patch (``PATCH``)

.. code-block:: python

    >>> from pydantic import TypeAdapter
    >>> from scim2_models import User, CreationRequestContext, CreationResponseContext

    >>> adapter = TypeAdapter(CreationRequestContext[User])
    >>> user = adapter.validate_python({
    ...     "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
    ...     "userName": "bjensen",
    ...     "id": "should-be-stripped",
    ... })
    >>> user.id is None
    True

    >>> adapter = TypeAdapter(CreationResponseContext[User])
    >>> user.id = "123"
    >>> data = adapter.dump_python(user)
    >>> "password" not in data
    True

In FastAPI for instance, they can be used directly in endpoint signatures:

.. code-block:: python

    from scim2_models import CreationRequestContext, CreationResponseContext, User

    @router.post("/Users", status_code=201)
    async def create_user(
        user: CreationRequestContext[User],
    ) -> CreationResponseContext[User]:
        ...

See the :doc:`guides/fastapi` guide for a complete example.

.. note::

   ``*ResponseContext`` aliases do not support the ``attributes`` /
   ``excludedAttributes`` parameters defined in
   :rfc:`RFC 7644 §3.9 <7644#section-3.9>`.  When you need to forward those
   parameters, use ``model_dump_json`` explicitly instead.

Low-level markers
^^^^^^^^^^^^^^^^^

For more advanced usage, the underlying markers can be used directly with
:data:`typing.Annotated`:

- :class:`~scim2_models.SCIMValidator` — injects a context during **validation**.
- :class:`~scim2_models.SCIMSerializer` — injects a context during **serialization**.

.. code-block:: python

    >>> from typing import Annotated
    >>> from pydantic import TypeAdapter
    >>> from scim2_models import User, Context, SCIMSerializer

    >>> adapter = TypeAdapter(
    ...     Annotated[User, SCIMSerializer(Context.RESOURCE_QUERY_RESPONSE)]
    ... )
    >>> user = User(user_name="bjensen", password="secret")
    >>> user.id = "123"
    >>> data = adapter.dump_python(user)
    >>> "password" not in data
    True

Attributes inclusions and exclusions
====================================

In some situations it might be needed to exclude, or only include a given set of attributes when serializing a model.
This happens for instance when servers build response payloads for clients requesting only a subset of the model attributes.
As defined in :rfc:`RFC7644 §3.9 <7644#section-3.9>`, :code:`attributes` and :code:`excluded_attributes` parameters can
be passed to :meth:`~scim2_models.BaseModel.model_dump`.
The expected attribute notation is the one detailed on :rfc:`RFC7644 §3.10 <7644#section-3.10>`,
like :code:`urn:ietf:params:scim:schemas:core:2.0:User:userName`, or :code:`userName` for short.

.. code-block:: python
    :emphasize-lines: 5

    >>> from scim2_models import User, Context
    >>> user = User(user_name="bjensen@example.com", display_name="bjensen")
    >>> payload = user.model_dump(
    ...     scim_ctx=Context.RESOURCE_QUERY_RESPONSE,
    ...     excluded_attributes=["displayName"]
    ... )
    >>> assert payload == {
    ...     "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
    ...     "userName": "bjensen@example.com",
    ... }

Values read from :attr:`~scim2_models.ResponseParameters.attributes` and :attr:`~scim2_models.ResponseParameters.excluded_attributes` in :class:`~scim2_models.SearchRequest` objects can directly be used in :meth:`~scim2_models.BaseModel.model_dump`.

Attributes inclusions and exclusions interact with attributes :class:`~scim2_models.Returned`, in the server response :class:`Contexts <scim2_models.Context>`:

- attributes annotated with :attr:`~scim2_models.Returned.always` will always be dumped;
- attributes annotated with :attr:`~scim2_models.Returned.never` will never be dumped;
- attributes annotated with :attr:`~scim2_models.Returned.default` will be dumped unless being explicitly excluded;
- attributes annotated with :attr:`~scim2_models.Returned.request` will not be dumped unless being explicitly included.

Typed ListResponse
==================

:class:`~scim2_models.ListResponse` models take a type, or a union of types.
You must pass the type you expect in the response, e.g.
:class:`~scim2_models.ListResponse`\ [:class:`~scim2_models.User`] or
:class:`~scim2_models.ListResponse`\ [:class:`~scim2_models.User` | :class:`~scim2_models.Group`].
If a response resource type cannot be found, a ``pydantic.ValidationError`` will be raised.

.. code-block:: python
    :emphasize-lines: 48

    >>> from scim2_models import User, Group, ListResponse

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

    >>> response = ListResponse[User | Group].model_validate(payload)
    >>> user, group = response.resources
    >>> type(user)
    <class 'scim2_models.resources.user.User'>
    >>> type(group)
    <class 'scim2_models.resources.group.Group'>


Schema extensions
=================

:rfc:`RFC7643 §3.3 <7643#section-3.3>` extensions are supported.
Any class inheriting from :class:`~scim2_models.Extension` can be passed as a :class:`~scim2_models.Resource` type parameter, e.g. ``user = User[EnterpriseUser]`` or ``user = User[EnterpriseUser | SuperHero]``.
Extensions attributes are accessed with brackets, e.g. ``user[EnterpriseUser].employee_number``, where ``user[EnterpriseUser]`` is a shortcut for ``user["urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"]``.

.. code-block:: python

    >>> import datetime
    >>> from scim2_models import User, EnterpriseUser, Meta

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
    ...         "employeeNumber": "701984",
    ...         "division": "Theme Park",
    ...     }
    ... }


.. _tutorial-filters:

Filters
=======

:class:`~scim2_models.ScimFilter` parses the filters defined at :rfc:`RFC7644 §3.4.2.2 <7644#section-3.4.2.2>`,
the ones a client sends in a ``filter`` query parameter or in
:attr:`SearchRequest.filter <scim2_models.SearchRequest.filter>`.
A filter behaves as the string it was built from, and its syntax is checked as soon as it is created:

.. doctest::

    >>> from scim2_models import ScimFilter, User

    >>> ScimFilter('userName eq "bjensen"') == 'userName eq "bjensen"'
    True

    >>> ScimFilter('userName eq')
    Traceback (most recent call last):
        ...
    scim2_models.exceptions.InvalidFilterException: invalid syntax at column 10

Binding it to a model with :class:`~scim2_models.ScimFilter`\ [:class:`~scim2_models.User`]
checks it against that model too, so an operator or a value an attribute cannot take is refused
the same way:

.. doctest::

    >>> ScimFilter[User]("active gt true")
    Traceback (most recent call last):
        ...
    scim2_models.exceptions.InvalidFilterException: operator 'gt' cannot be applied to the boolean attribute 'urn:ietf:params:scim:schemas:core:2.0:User:active'

Matching resources
^^^^^^^^^^^^^^^^^^

Binding a filter to a model with :class:`~scim2_models.ScimFilter`\ [:class:`~scim2_models.User`] is what resolves attribute names against
that model, and lets you check whether a resource satisfies it:

.. doctest::

    >>> user = User(
    ...     user_name="bjensen",
    ...     emails=[{"type": "work", "value": "bjensen@example.com"}],
    ... )

    >>> ScimFilter[User]('emails[type eq "work"]').match(user)
    True
    >>> ScimFilter[User]('userName sw "bj" and title pr').match(user)
    False

An endpoint covering several resource types binds them all at once, and each resource is then
matched against its own type. This is what a server needs to answer a query against its root,
as :doc:`guides/index` shows:

.. doctest::

    >>> from scim2_models import Group

    >>> scim_filter = ScimFilter[User | Group]("userName pr")
    >>> scim_filter.match(user)
    True
    >>> scim_filter.match(Group(display_name="admins"))
    False

Comparing a multi-valued complex attribute without naming a sub-attribute compares the ``value``
of its entries, which is how :rfc:`RFC7644 §3.4.2.2 <7644#section-3.4.2.2>` uses the two forms
side by side. Presence keeps its own meaning, since ``pr`` matches a non-empty *node*:

.. doctest::

    >>> ScimFilter[User]('emails co "example.com"').match(user)
    True
    >>> ScimFilter[User]('emails.value co "example.com"').match(user)
    True

    >>> without_value = User(user_name="bjensen", emails=[{"type": "work"}])
    >>> ScimFilter[User]("emails pr").match(without_value)
    True
    >>> ScimFilter[User]("emails.value pr").match(without_value)
    False

Filters do more than match: they compose into expressions, they turn into backend queries, and
they follow a grammar the published ABNF only describes once its errata are applied.
See :doc:`filters`.

Errors and Exceptions
=====================

scim2-models provides a hierarchy of exceptions corresponding to :rfc:`RFC7644 §3.12 <7644#section-3.12>` error types.
Each exception can be converted to an :class:`~scim2_models.Error` response object or used in Pydantic validators.

Raising exceptions
^^^^^^^^^^^^^^^^^^

Exceptions are named after their ``scimType`` value:

.. code-block:: python

    >>> from scim2_models import InvalidPathException, PathNotFoundException

    >>> raise InvalidPathException(path="invalid..path")
    Traceback (most recent call last):
        ...
    scim2_models.exceptions.InvalidPathException: The path attribute was invalid or malformed

    >>> raise PathNotFoundException(path="unknownAttr")
    Traceback (most recent call last):
        ...
    scim2_models.exceptions.PathNotFoundException: The specified path references a non-existent field

Converting to Error response
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use :meth:`~scim2_models.SCIMException.to_error` to convert an exception to an :class:`~scim2_models.Error` response:

.. code-block:: python

    >>> from scim2_models import InvalidPathException

    >>> exc = InvalidPathException(path="invalid..path")
    >>> error = exc.to_error()
    >>> error.status
    400
    >>> error.scim_type
    'invalidPath'

Converting from ValidationError
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use :meth:`Error.from_validation_error <scim2_models.Error.from_validation_error>` to convert a single Pydantic error to an :class:`~scim2_models.Error`:

.. code-block:: python

    >>> from pydantic import ValidationError
    >>> from scim2_models import Error, User
    >>> from scim2_models.base import Context

    >>> try:
    ...     User.model_validate({"userName": None}, scim_ctx=Context.RESOURCE_CREATION_REQUEST)
    ... except ValidationError as exc:
    ...     error = Error.from_validation_error(exc.errors()[0])
    >>> error.scim_type
    'invalidValue'

Use :meth:`Error.from_validation_errors <scim2_models.Error.from_validation_errors>` to convert all errors at once:

.. code-block:: python

    >>> try:
    ...     User.model_validate({"userName": 123, "displayName": 456})
    ... except ValidationError as exc:
    ...     errors = Error.from_validation_errors(exc)
    >>> len(errors)
    2
    >>> [e.detail for e in errors]
    ['Input should be a valid string: username', 'Input should be a valid string: displayname']

The exhaustive list of exceptions is available in the :class:`reference <scim2_models.SCIMException>`.

Custom models
=============

You can write your own model and use it the same way as the other scim2-models models.
Just inherit from :class:`~scim2_models.Resource` for your main resource, or :class:`~scim2_models.Extension` for extensions.
Use :class:`~scim2_models.ComplexAttribute` as base class for complex attributes:

.. code-block:: python

    >>> from typing import Annotated, Optional
    >>> from scim2_models import Resource, Returned, Mutability, ComplexAttribute, URN
    >>> from enum import Enum

    >>> class PetType(ComplexAttribute):
    ...     type: Optional[str]
    ...     """The pet type like 'cat' or 'dog'."""
    ...
    ...     color: Optional[str]
    ...     """The pet color."""

    >>> class Pet(Resource):
    ...     __schema__ = URN("urn:example:schemas:Pet")
    ...
    ...     name: Annotated[Optional[str], Mutability.immutable, Returned.always]
    ...     """The name of the pet."""
    ...
    ...     pet_type: Optional[PetType]
    ...     """The pet type."""

You can annotate fields to indicate their :class:`~scim2_models.Mutability` and :class:`~scim2_models.Returned`.
If unset the default values will be :attr:`~scim2_models.Mutability.read_write` and :attr:`~scim2_models.Returned.default`.

.. warning::

    Be sure to make all the fields of your model :data:`~typing.Optional`.
    There will always be a :class:`~scim2_models.Context` in which this will be true.

There is a dedicated type for :rfc:`RFC7643 §2.3.7 <7643#section-2.3.7>` :class:`~scim2_models.Reference`
that can take type parameters to represent :rfc:`RFC7643 §7 'referenceTypes'<7643#section-7>`:

.. code-block:: python

    >>> from scim2_models import Reference
    >>> class PetOwner(Resource):
    ...    pet: Optional[Reference["Pet"]]

:class:`~scim2_models.Reference` has two special type parameters :class:`~scim2_models.External` and :class:`~scim2_models.URI` that matches :rfc:`RFC7643 §7 <7643#section-7>` external and URI reference types.

Dynamic schemas from models
===========================

With :meth:`Resource.to_schema <scim2_models.Resource.to_schema>` and :meth:`Extension.to_schema <scim2_models.Extension.to_schema>`, any model can be exported as a :class:`~scim2_models.Schema` object.
This is useful for server implementations, so custom models or models provided by scim2-models can easily be exported on the ``/Schemas`` endpoint.


.. code-block:: python

    >>> from scim2_models import Resource, URN

    >>> class MyCustomResource(Resource):
    ...     """My awesome custom schema."""
    ...
    ...     __schema__ = URN("urn:example:schemas:MyCustomResource")
    ...
    ...     foobar: Optional[str]
    ...
    >>> schema = MyCustomResource.to_schema()
    >>> dump = schema.model_dump()
    >>> assert dump == {
    ...     "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Schema"],
    ...     "id": "urn:example:schemas:MyCustomResource",
    ...     "name": "MyCustomResource",
    ...     "description": "My awesome custom schema.",
    ...     "attributes": [
    ...         {
    ...             "caseExact": False,
    ...              "multiValued": False,
    ...              "mutability": "readWrite",
    ...              "name": "foobar",
    ...              "required": False,
    ...              "returned": "default",
    ...              "type": "string",
    ...              "uniqueness": "none",
    ...         },
    ...     ],
    ... }

Dynamic models from schemas
===========================

Given a :class:`~scim2_models.Schema` object, scim2-models can dynamically generate a pythonic model to be used in your code
with the :meth:`Resource.from_schema <scim2_models.Resource.from_schema>` and :meth:`Extension.from_schema <scim2_models.Extension.from_schema>` methods.

.. code-block:: python
   :class: dropdown
   :caption: sample

    payload = {
        "id": "urn:ietf:params:scim:schemas:core:2.0:Group",
        "name": "Group",
        "description": "Group",
        "attributes": [
            {
                "name": "displayName",
                "type": "string",
                "multiValued": false,
                "description": "A human-readable name for the Group. REQUIRED.",
                "required": false,
                "caseExact": false,
                "mutability": "readWrite",
                "returned": "default",
                "uniqueness": "none"
            },
            ...
        ],
    }
    schema = Schema.model_validate(payload)
    Group = Resource.from_schema(schema)
    my_group = Group(display_name="This is my group")

Client applications can use this to dynamically discover server resources by browsing the ``/Schemas`` endpoint.

.. tip::

   Sub-Attribute models are automatically created and set as members of their parent model classes.
   For instance the RFC7643 Group members sub-attribute can be accessed with ``Group.Members``.

   .. toggle::

       .. literalinclude:: ../samples/rfc7643-8.7.1-schema-group.json
          :language: json
          :caption: schema-group.json

Replace operations
==================

When handling a ``PUT`` request, validate the incoming payload with the
:attr:`~scim2_models.Context.RESOURCE_REPLACEMENT_REQUEST` context, then call
:meth:`~scim2_models.Resource.replace` against the existing resource to
verify that :attr:`~scim2_models.Mutability.immutable` attributes have not been
modified.

.. doctest::

    >>> from scim2_models import User, Context
    >>> existing = User(user_name="bjensen")
    >>> replacement = User.model_validate(
    ...     {
    ...         "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
    ...         "userName": "bjensen",
    ...     },
    ...     scim_ctx=Context.RESOURCE_REPLACEMENT_REQUEST,
    ... )
    >>> replacement.replace(existing)

If an immutable attribute differs, a :class:`~scim2_models.MutabilityException`
is raised.

Patch operations
================

:class:`~scim2_models.PatchOp` allows you to apply patch operations to modify SCIM resources.
The :meth:`~scim2_models.PatchOp.patch` method applies operations in sequence and returns whether the resource was modified. The return code is a boolean indicating whether the object has been modified by the operations.

.. note::
   :class:`~scim2_models.PatchOp` takes a type parameter that should be the class of the resource
   that is expected to be patched.

.. code-block:: python

    >>> from scim2_models import User, PatchOp, PatchOperation
    >>> user = User(user_name="john.doe", nick_name="Johnny")

    >>> payload = {
    ...   "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
    ...   "Operations": [
    ...     {"op": "replace", "path": "nickName", "value": "John" },
    ...     {"op": "add", "path": "emails", "value": [{"value": "john@example.com"}]},
    ...   ]
    ... }
    >>> patch = PatchOp[User].model_validate(
    ...     payload, scim_ctx=Context.RESOURCE_PATCH_REQUEST
    ... )

    >>> modified = patch.patch(user)
    >>> print(modified)
    True
    >>> print(user.nick_name)
    John
    >>> print(user.emails[0].value)
    john@example.com

.. warning::

   Patch operations are validated in the :attr:`~scim2_models.Context.RESOURCE_PATCH_REQUEST`
   context. Make sure to validate patch operations with the correct context to
   ensure proper validation of mutability and required constraints.

.. _patch-value-selection:

Selecting values to patch
^^^^^^^^^^^^^^^^^^^^^^^^^

:attr:`PatchOperation.path <scim2_models.PatchOperation.path>` follows a grammar of its own,
:rfc:`RFC7644 §3.5.2 <7644#section-3.5.2>`, where a filter between brackets selects which
entries of a multi-valued attribute an operation applies to:

.. doctest::

    >>> from scim2_models import PatchOp, PatchOperation

    >>> user = User(
    ...     user_name="bjensen",
    ...     emails=[
    ...         {"type": "work", "value": "work@example.com"},
    ...         {"type": "home", "value": "home@example.com"},
    ...     ],
    ... )

    >>> patch = PatchOp[User](
    ...     operations=[
    ...         PatchOperation(
    ...             op=PatchOperation.Op.replace_,
    ...             path='emails[type eq "work"].value',
    ...             value="new@example.com",
    ...         )
    ...     ]
    ... )
    >>> patch.patch(user)
    True
    >>> [email.value for email in user.emails]
    ['new@example.com', 'home@example.com']

What a selection matching nothing means depends on the operation. For ``replace``,
:rfc:`RFC7644 §3.5.2.3 <7644#section-3.5.2.3>` requires a ``noTarget`` failure:

.. doctest::

    >>> from scim2_models import NoTargetException

    >>> patch = PatchOp[User](
    ...     operations=[
    ...         PatchOperation(
    ...             op=PatchOperation.Op.replace_,
    ...             path='emails[type eq "other"].value',
    ...             value="other@example.com",
    ...         )
    ...     ]
    ... )
    >>> try:
    ...     patch.patch(user)
    ... except NoTargetException as exc:
    ...     print(exc.scim_type)
    noTarget

For ``remove``, :rfc:`RFC7644 §3.5.2.2 <7644#section-3.5.2.2>` asks for the opposite: its
removal example states that "if the user was not a member of this group, no changes should
be made to the resource, and a success response should be returned". The operation is a
no-op, and reports that nothing changed:

.. doctest::

    >>> patch = PatchOp[User](
    ...     operations=[
    ...         PatchOperation(
    ...             op=PatchOperation.Op.remove, path='emails[type eq "other"]'
    ...         )
    ...     ]
    ... )
    >>> patch.patch(user)
    False

``add`` behaves the same way. :rfc:`RFC7644 §3.5.2.1 <7644#section-3.5.2.1>` does not say what
a selection matching nothing means for it, so the operation is a no-op rather than a failure.
`Errata 8097 <https://www.rfc-editor.org/errata/eid8097>`_ asks for value selections in ``add``
to be clarified at all, implementations differing on whether they are allowed. Note that Microsoft Entra ID emits exactly this payload expecting
the entry to be created, which scim2-models does not do.

The same selection is available on :class:`~scim2_models.Path` itself, through
:meth:`~scim2_models.Path.get`, :meth:`~scim2_models.Path.set` and
:meth:`~scim2_models.Path.delete`:

.. doctest::

    >>> from scim2_models import Path

    >>> Path[User]('emails[type eq "home"].value').get(user)
    ['home@example.com']

A multi-valued attribute that is not complex holds plain values with no sub-attribute to compare.
Those are addressed either with a bare comparison, which errata 7122 adds to the grammar, or with
the ``value`` convention that implementations use:

.. doctest::

    >>> user = User(
    ...     user_name="bjensen",
    ...     schemas=["urn:ietf:params:scim:schemas:core:2.0:User", "urn:a:b:c"],
    ... )

    >>> Path[User]('schemas eq "urn:a:b:c"').delete(user)
    True
    >>> user.schemas
    ['urn:ietf:params:scim:schemas:core:2.0:User']

    >>> Path[User]('schemas[value eq "urn:ietf:params:scim:schemas:core:2.0:User"]').get(user)
    ['urn:ietf:params:scim:schemas:core:2.0:User']

Bulk operations
===============

.. todo::

   Bulk operations are not implemented yet, but any help is welcome!
