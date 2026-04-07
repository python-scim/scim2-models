FastAPI
-------

This guide shows a minimal SCIM server built with `FastAPI <https://fastapi.tiangolo.com/>`_
and :mod:`scim2_models`.
It focuses on:

- validate incoming SCIM payloads with the right :class:`~scim2_models.Context`;
- serialize resources and collections as SCIM responses;
- expose responses with the ``application/scim+json`` media type;
- convert validation errors into SCIM :class:`~scim2_models.Error` payloads.

The example uses :class:`~scim2_models.User` as a concrete resource type, but the same
pattern applies to any other resource such as :class:`~scim2_models.Group`.
The storage and mapping layers are defined in the :doc:`index` section and shared across
all integration examples.
The complete runnable file is available in the `Complete example`_ section.

.. code-block:: shell

   pip install fastapi uvicorn scim2-models

Application setup
=================

Start with a FastAPI application and an
`APIRouter <https://fastapi.tiangolo.com/reference/apirouter/>`_ prefixed with ``/scim/v2``.
``SCIMResponse`` is a thin :class:`~fastapi.Response` subclass that sets the
``application/scim+json`` content type and automatically extracts the ``ETag`` header
from ``meta.version`` when the response body contains it.

.. literalinclude:: _examples/fastapi_example.py
   :language: python
   :start-after: # -- setup-start --
   :end-before: # -- setup-end --

Optional FastAPI refinements
============================

The core SCIM flow only needs the router and the endpoints below.
FastAPI also offers a few convenient integration patterns that can keep the views shorter and
help keep framework-level errors aligned with SCIM responses.

Dependencies
^^^^^^^^^^^^

`Dependencies <https://fastapi.tiangolo.com/tutorial/dependencies/>`_ let FastAPI resolve
route parameters before the view function is called.
Define one dependency per resource type: it maps a resource identifier to an application
record and raises an
`HTTPException <https://fastapi.tiangolo.com/reference/exceptions/>`_
when the record is not found.

.. literalinclude:: _examples/fastapi_example.py
   :language: python
   :start-after: # -- dependency-start --
   :end-before: # -- dependency-end --

Exception handlers
^^^^^^^^^^^^^^^^^^

`Exception handlers <https://fastapi.tiangolo.com/tutorial/handling-errors/>`_ keep Pydantic
validation errors, HTTP exceptions, and application errors aligned with SCIM responses.

.. literalinclude:: _examples/fastapi_example.py
   :language: python
   :start-after: # -- error-handlers-start --
   :end-before: # -- error-handlers-end --

``handle_validation_error`` catches the :class:`~pydantic.ValidationError` raised by
:meth:`~scim2_models.Resource.model_validate` and returns a SCIM :class:`~scim2_models.Error`
response.
``handle_http_exception`` catches HTTP errors such as the 404 raised by the dependency and wraps
them in a SCIM :class:`~scim2_models.Error`.
``handle_scim_error`` catches any :class:`~scim2_models.SCIMException` (uniqueness, mutability, …)
and returns the appropriate SCIM :class:`~scim2_models.Error` response.
``check_etag`` raises an :class:`~fastapi.HTTPException` with status 412 on ETag mismatch,
which is caught by ``handle_http_exception``.

Endpoints
=========

The routes below serve ``/Users``, but the same structure applies to any resource type:
replace the mapping helpers, the model class, and the URL prefix to expose ``/Groups`` or
any other collection.
Write endpoints use :class:`~scim2_models.SCIMValidator` to let FastAPI parse and validate
the request body with the correct SCIM :class:`~scim2_models.Context` automatically.
Read endpoints still build responses explicitly because they need to forward
``attributes`` / ``excludedAttributes`` query parameters.

GET /Users/<id>
^^^^^^^^^^^^^^^

Parse query parameters with :class:`~scim2_models.ResponseParameters`, convert the native
record to a SCIM resource with your mapping helper, then serialize with
:attr:`~scim2_models.Context.RESOURCE_QUERY_RESPONSE`, forwarding
``req.attributes`` and ``req.excluded_attributes`` so the response only includes the
requested fields.

.. literalinclude:: _examples/fastapi_example.py
   :language: python
   :start-after: # -- get-user-start --
   :end-before: # -- get-user-end --

DELETE /Users/<id>
^^^^^^^^^^^^^^^^^^

Remove the record from the store and return an empty 204 response.
No SCIM serialization is needed.

.. literalinclude:: _examples/fastapi_example.py
   :language: python
   :start-after: # -- delete-user-start --
   :end-before: # -- delete-user-end --

PATCH /Users/<id>
^^^^^^^^^^^^^^^^^

The patch payload is validated through :class:`~scim2_models.SCIMValidator` with
:attr:`~scim2_models.Context.RESOURCE_PATCH_REQUEST`.
Apply it to a SCIM conversion of the native record with :meth:`~scim2_models.PatchOp.patch`,
convert back to native and persist, then serialize the result with
:attr:`~scim2_models.Context.RESOURCE_PATCH_RESPONSE`.
:class:`~scim2_models.PatchOp` is generic and works with any resource type.

.. literalinclude:: _examples/fastapi_example.py
   :language: python
   :start-after: # -- patch-user-start --
   :end-before: # -- patch-user-end --

PUT /Users/<id>
^^^^^^^^^^^^^^^

The full replacement payload is validated through :class:`~scim2_models.SCIMValidator` with
:attr:`~scim2_models.Context.RESOURCE_REPLACEMENT_REQUEST`, then call
:meth:`~scim2_models.Resource.replace` to verify that immutable attributes
have not been modified.

.. literalinclude:: _examples/fastapi_example.py
   :language: python
   :start-after: # -- put-user-start --
   :end-before: # -- put-user-end --


GET /Users
^^^^^^^^^^

Parse pagination and filtering parameters with :class:`~scim2_models.SearchRequest`, slice
the store accordingly, then wrap the page in a :class:`~scim2_models.ListResponse` serialized
with :attr:`~scim2_models.Context.RESOURCE_QUERY_RESPONSE`.
Pass ``req.attributes`` and ``req.excluded_attributes`` to
:meth:`~scim2_models.ListResponse.model_dump_json` so that the ``attributes`` and
``excludedAttributes`` query parameters are applied to each embedded resource.

.. literalinclude:: _examples/fastapi_example.py
   :language: python
   :start-after: # -- list-users-start --
   :end-before: # -- list-users-end --

POST /Users
^^^^^^^^^^^

The creation payload is validated through :class:`~scim2_models.SCIMValidator` with
:attr:`~scim2_models.Context.RESOURCE_CREATION_REQUEST`.
Convert to native and persist, then serialize the created resource with
:attr:`~scim2_models.Context.RESOURCE_CREATION_RESPONSE`.

.. literalinclude:: _examples/fastapi_example.py
   :language: python
   :start-after: # -- create-user-start --
   :end-before: # -- create-user-end --

Resource versioning (ETags)
===========================

SCIM supports resource versioning through HTTP ETags
(:rfc:`RFC 7644 §3.14 <7644#section-3.14>`).
``check_etag`` reads the ``If-Match`` header from the incoming request, compares it against
the record's ETag and raises an :class:`~fastapi.HTTPException` on mismatch.
``make_etag`` computes a weak ETag from each record and populates
:attr:`~scim2_models.Meta.version`.

.. literalinclude:: _examples/fastapi_example.py
   :language: python
   :start-after: # -- etag-start --
   :end-before: # -- etag-end --

On ``GET`` single-resource responses, the ``If-None-Match``
request header is checked manually to return a ``304 Not Modified`` when the client already
has the current version.

On write operations (``PUT``, ``PATCH``, ``DELETE``), the ``If-Match`` header is checked
before processing.
If the client's ETag does not match, a ``412 Precondition Failed`` SCIM error is returned.

``SCIMResponse`` automatically extracts ``meta.version`` from the serialized body and sets
the ``ETag`` response header, so endpoints do not need to set it manually.

.. tip::

   If your application uses SQLAlchemy, the built-in
   :doc:`version counter <sqlalchemy:orm/versioning>` can serve as ETag
   value directly, removing the need for a manual hash.

Discovery endpoints
===================

SCIM defines three read-only endpoints that let clients discover the server's capabilities
and the resources it exposes (:rfc:`RFC 7644 §4 <7644#section-4>`).
The shared :ref:`discovery helpers <discovery-helpers>` that build
:class:`~scim2_models.Schema`, :class:`~scim2_models.ResourceType` and
:class:`~scim2_models.ServiceProviderConfig` objects are defined in the :doc:`index` section.

GET /Schemas and GET /Schemas/<id>
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Return all :class:`~scim2_models.Schema` objects or look one up by its URI.
Schemas are built automatically from resource models with
:meth:`~scim2_models.Resource.to_schema`.
The collection endpoint parses pagination parameters with
:class:`~scim2_models.SearchRequest`, following the same pattern as ``GET /Users``.

.. literalinclude:: _examples/fastapi_example.py
   :language: python
   :start-after: # -- schemas-start --
   :end-before: # -- schemas-end --

GET /ResourceTypes and GET /ResourceTypes/<id>
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Return all :class:`~scim2_models.ResourceType` objects or look one up by its identifier.
Resource types are built automatically from resource models with
:meth:`~scim2_models.ResourceType.from_resource`.
The collection endpoint parses pagination parameters with
:class:`~scim2_models.SearchRequest`, following the same pattern as ``GET /Users``.

.. literalinclude:: _examples/fastapi_example.py
   :language: python
   :start-after: # -- resource-types-start --
   :end-before: # -- resource-types-end --

GET /ServiceProviderConfig
^^^^^^^^^^^^^^^^^^^^^^^^^^

Return the :class:`~scim2_models.ServiceProviderConfig` singleton that describes the
features the server supports (patch, bulk, filtering, etc.).

.. literalinclude:: _examples/fastapi_example.py
   :language: python
   :start-after: # -- service-provider-config-start --
   :end-before: # -- service-provider-config-end --

Idiomatic type annotations
==========================

The write endpoints above use the context type aliases provided by :mod:`scim2_models`.
``*RequestContext`` aliases wrap :class:`~scim2_models.SCIMValidator` (input validation),
``*ResponseContext`` aliases wrap :class:`~scim2_models.SCIMSerializer` (output serialization):

.. code-block:: python

   from scim2_models import CreationRequestContext, CreationResponseContext, User

   @router.post("/Users", status_code=201)
   async def create_user(
       user: CreationRequestContext[User],
   ) -> CreationResponseContext[User]:
       app_record = from_scim_user(user)
       save_record(app_record)
       return to_scim_user(app_record, ...)

Available aliases: ``CreationRequestContext`` / ``CreationResponseContext``,
``QueryRequestContext`` / ``QueryResponseContext``,
``ReplacementRequestContext`` / ``ReplacementResponseContext``,
``SearchRequestContext`` / ``SearchResponseContext``, and
``PatchRequestContext`` / ``PatchResponseContext``.

These aliases are **pure Pydantic** and carry no dependency on FastAPI — they work with any
framework that respects :data:`typing.Annotated` metadata.

``*ResponseContext`` aliases do not support the ``attributes`` / ``excludedAttributes``
query parameters defined in :rfc:`RFC 7644 §3.9 <7644#section-3.9>`.
When you need to forward those parameters, use the explicit ``model_dump_json`` approach
shown in the previous sections instead.

Complete example
================

.. literalinclude:: _examples/fastapi_example.py
   :language: python
