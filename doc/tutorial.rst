Tutorial
--------

Model parsing
=============

Pydantic :func:`~scim2_models.BaseModel.model_validate` method can be used to parse and validate SCIM2 payloads.
Python models have generally the same name than in the SCIM specifications, they are simply snake cased.


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
    >>> user.meta.created
    datetime.datetime(2010, 1, 23, 4, 56, 22, tzinfo=TzInfo(UTC))


Model serialization
===================

Pydantic :func:`~scim2_models.BaseModel.model_dump` method have been tuned to produce valid SCIM2 payloads.

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
Depending on the context, they will indicate that attributes should be present, absent, be ignored.

For instance, attributes marked as :attr:`~scim2_models.Mutability.read_only` should not be sent by SCIM clients on resource creation requests.
By passing the right :class:`~scim2_models.Context` to the :meth:`~scim2_models.BaseModel.model_dump` method, only the expected fields will be dumped for this context:

.. code-block:: python
    :caption: Client generating a resource creation request payload

    >>> from scim2_models import User, Context
    >>> user = User(user_name="bjensen@example.com")
    >>> payload = user.model_dump(scim_ctx=Context.RESOURCE_CREATION_REQUEST)

In the same fashion, by passing the right :class:`~scim2_models.Context` to the :meth:`~scim2_models.BaseModel.model_validate` method,
fields with unexpected values will raise :class:`~pydantic.ValidationError`:

.. code-block:: python
    :caption: Server validating a resource creation request payload

    >>> from scim2_models import User, Context
    >>> from pydantic import ValidationError
    >>> try:
    ...    obj = User.model_validate(payload, scim_ctx=Context.RESOURCE_CREATION_REQUEST)
    ... except pydantic.ValidationError:
    ...    obj = Error(...)

.. note::

   With the :attr:`~scim2_models.Context.RESOURCE_REPLACEMENT_REQUEST` context,
   :meth:`~scim2_models.BaseModel.model_validate` takes an additional
   :paramref:`~scim2_models.BaseModel.model_validate.original` argument that is used to compare
   :attr:`~scim2_models.Mutability.immutable` attributes, and raise an exception when they have mutated.

Attributes inclusions and exclusions
====================================

In some situations it might be needed to exclude, or only include a given set of attributes when serializing a model.
This happens for instance when servers build response payloads for clients requesting only a sub-set the model attributes.
As defined in :rfc:`RFC7644 §3.9 <7644#section-3.9>`, :code:`attributes` and :code:`excluded_attributes` parameters can
be passed to :meth:`~scim2_models.BaseModel.model_dump`.
The expected attribute notation is the one detailed on :rfc:`RFC7644 §3.10 <7644#section-3.10>`,
like :code:`urn:ietf:params:scim:schemas:core:2.0:User:userName`, or :code:`userName` for short.

.. code-block:: python
    :emphasize-lines: 5

    >>> from scim2_models import User, Context
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

Values read from :attr:`~scim2_models.SearchRequest.attributes` and :attr:`~scim2_models.SearchRequest.excluded_attributes` in :class:`~scim2_models.SearchRequest` objects can directly be used in :meth:`~scim2_models.BaseModel.model_dump`.

Attribute inclusions and exclusions interact with attributes :class:`~scim2_models.Returned`, in the server response :class:`Contexts <scim2_models.Context>`:

- attributes annotated with :attr:`~scim2_models.Returned.always` will always be dumped;
- attributes annotated with :attr:`~scim2_models.Returned.never` will never be dumped;
- attributes annotated with :attr:`~scim2_models.Returned.default` will be dumped unless being explicitly excluded;
- attributes annotated with :attr:`~scim2_models.Returned.request` will be not dumped unless being explicitly included.

Typed ListResponse
==================

:class:`~scim2_models.ListResponse` models take a type or a :data:`~typing.Union` of types.
You must pass the type you expect in the response, e.g. :class:`~scim2_models.ListResponse[User]` or :class:`~scim2_models.ListResponse[Union[User, Group]]`.
If a response resource type cannot be found, a ``pydantic.ValidationError`` will be raised.

.. code-block:: python
    :emphasize-lines: 49

    >>> from typing import Union
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

    >>> response = ListResponse[Union[User, Group]].model_validate(payload)
    >>> user, group = response.resources
    >>> type(user)
    <class 'scim2_models.rfc7643.user.User'>
    >>> type(group)
    <class 'scim2_models.rfc7643.group.Group'>


Schema extensions
=================

:rfc:`RFC7643 §3.3 <7643#section-3.3>` extensions are supported.
Any class inheriting from :class:`~scim2_models.Extension` can be passed as a :class:`~scim2_models.Resource` type parameter, e.g. ``user = User[EnterpriseUser]`` or ``user = User[Union[EnterpriseUser, SuperHero]]``.
Extensions attributes are accessed with brackets, e.g. ``user[EnterpriseUser].employee_number``.

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


Pre-defined Error objects
=========================

:rfc:`RFC7643 §3.12 <7643#section-3.12>` pre-defined errors are usable.

.. code-block:: python

    >>> from scim2_models import Error

    >>> error = Error.make_invalid_path_error()
    >>> dump = error.model_dump()
    >>> assert dump == {
    ...     'detail': 'The "path" attribute was invalid or malformed (see Figure 7 of RFC7644).',
    ...     'schemas': ['urn:ietf:params:scim:api:messages:2.0:Error'],
    ...     'scimType': 'invalidPath',
    ...     'status': '400'
    ... }

The exhaustive list is available in the :class:`reference <scim2_models.Error>`.


Custom models
=============

You can write your own model and use it the same way than the other scim2-models models.
Just inherit from :class:`~scim2_models.Resource` for your main resource, or :class:`~scim2_models.Extension` for extensions.
Use :class:`~scim2_models.ComplexAttribute` as base class for complex attributes:

.. code-block:: python

    >>> from typing import Annotated, Optional, List
    >>> from scim2_models import Resource, Returned, Mutability, ComplexAttribute
    >>> from enum import Enum

    >>> class PetType(ComplexAttribute):
    ...     type: Optional[str]
    ...     """The pet type like 'cat' or 'dog'."""
    ...
    ...     color: Optional[str]
    ...     """The pet color."""

    >>> class Pet(Resource):
    ...     schemas: List[str] = ["example:schemas:Pet"]
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

    >>> from typing import Literal
    >>> class PetOwner(Resource):
    ...    pet: Reference[Literal["Pet"]]

:class:`~scim2_models.Reference` has two special type parameters :data:`~scim2_models.ExternalReference` and :data:`~scim2_models.URIReference` that matches :rfc:`RFC7643 §7 <7643#section-7>` external and URI reference types.

Dynamic schemas from models
===========================

With :meth:`Resource.to_schema <scim2_models.Resource.to_schema>` and :meth:`Extension.to_schema <scim2_models.Extension.to_schema>`, any model can be exported as a :class:`~scim2_models.Schema` object.
This is useful for server implementations, so custom models or models provided by scim2-models can easily be exported on the ``/Schemas`` endpoint.


.. code-block:: python

    >>> class MyCustomResource(Resource):
    ...     """My awesome custom schema."""
    ...
    ...     schemas: List[str] = ["example:schemas:MyCustomResource"]
    ...
    ...     foobar: Optional[str]
    ...
    >>> schema = MyCustomResource.to_schema()
    >>> dump = schema.model_dump()
    >>> assert dump == {
    ...     "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Schema"],
    ...     "id": "example:schemas:MyCustomResource",
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

This can be used by client applications that intends to dynamically discover server resources by browsing the `/Schemas` endpoint.

.. tip::

   Sub-Attribute models are automatically created and set as members of their parent model classes.
   For instance the RFC7643 Group members sub-attribute can be accessed with ``Group.Members``.

   .. toggle::

       .. literalinclude :: ../samples/rfc7643-8.7.1-schema-group.json
          :language: json
          :caption: schema-group.json

Bulk and Patch operations
=========================

.. todo::

   Bulk and Patch operations are not implemented yet, but any help is welcome!
