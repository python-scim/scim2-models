Django
------

This guide shows a minimal SCIM integration with `Django <https://www.djangoproject.com/>`_
and :mod:`scim2_models`.
It focuses on the integration points that matter most:

- validating incoming SCIM payloads with the right :class:`~scim2_models.Context`;
- serializing resources and collections as SCIM responses;
- exposing responses with the ``application/scim+json`` media type;
- parsing pagination parameters with :class:`~scim2_models.SearchRequest`;
- handling Django-specific concerns such as URLconfs, custom path converters, and CSRF.

The example uses :class:`~scim2_models.User` as a concrete resource type, but the same
pattern applies to any other resource such as :class:`~scim2_models.Group`.
The storage and mapping layers are defined in the :doc:`index` section and shared across
all integration examples.
The complete runnable file is available in the `Complete example`_ section.

.. code-block:: shell

   pip install django scim2-models

Application setup
=================

Start with a small response helper that sets the ``application/scim+json`` content type
on every response.

.. literalinclude:: _examples/django_example.py
   :language: python
   :start-after: # -- setup-start --
   :end-before: # -- setup-end --

Optional Django refinements
===========================

The core SCIM flow only needs the endpoints below.
Django also offers a few convenient integration patterns that can keep the views shorter
and help keep framework-level errors aligned with SCIM responses.

Django converters
^^^^^^^^^^^^^^^^^

Custom path converters let Django resolve route parameters before the view function is
called.
Define one converter per resource type: it maps a resource identifier to an application
record and lets Django turn lookup failures into a 404 during URL resolution.

.. literalinclude:: _examples/django_example.py
   :language: python
   :start-after: # -- converters-start --
   :end-before: # -- converters-end --

Validation helper
^^^^^^^^^^^^^^^^^

The validation helper keeps Pydantic validation errors aligned with SCIM responses.

.. literalinclude:: _examples/django_example.py
   :language: python
   :start-after: # -- validation-helper-start --
   :end-before: # -- validation-helper-end --

If :meth:`~scim2_models.Resource.model_validate` or
:meth:`~scim2_models.PatchOp.model_validate` fails, the views below catch the
:class:`~pydantic.ValidationError` and return a SCIM :class:`~scim2_models.Error`
response.

SCIM exception helper
^^^^^^^^^^^^^^^^^^^^^

``scim_exception_error`` converts any :class:`~scim2_models.SCIMException`
(uniqueness, mutability, …) into a SCIM error response.

.. literalinclude:: _examples/django_example.py
   :language: python
   :start-after: # -- scim-exception-helper-start --
   :end-before: # -- scim-exception-helper-end --

Error handler
^^^^^^^^^^^^^

Django does not produce SCIM-formatted 404 responses by default.
Defining ``handler404`` in the URLconf module overrides this behaviour.
Note that Django only calls ``handler404`` when ``DEBUG`` is ``False``.

.. literalinclude:: _examples/django_example.py
   :language: python
   :start-after: # -- error-handler-start --
   :end-before: # -- error-handler-end --

Endpoints
=========

Django's CSRF middleware is enabled by default.
The views below use ``@csrf_exempt`` to accept JSON API requests directly.

The views serve ``/Users``, but the same structure applies to any resource type:
replace the mapping helpers, the model class, and the URL prefix to expose ``/Groups`` or
any other collection.

Single resource
^^^^^^^^^^^^^^^

``UserView`` handles ``GET``, ``PUT``, ``PATCH`` and ``DELETE`` on ``/Users/<id>``.
For ``GET``, parse query parameters with :class:`~scim2_models.ResponseParameters` to honour the
``attributes`` and ``excludedAttributes`` query parameters, convert the native record to a
SCIM resource, and serialize with :attr:`~scim2_models.Context.RESOURCE_QUERY_RESPONSE`.
For ``DELETE``, remove the record and return an empty 204 response.
For ``PUT``, validate the full replacement payload with
:attr:`~scim2_models.Context.RESOURCE_REPLACEMENT_REQUEST`, then call
:meth:`~scim2_models.Resource.replace` to verify that immutable attributes
have not been modified.
Convert back to native and persist, then serialize with
:attr:`~scim2_models.Context.RESOURCE_REPLACEMENT_RESPONSE`.
For ``PATCH``, validate the payload with :attr:`~scim2_models.Context.RESOURCE_PATCH_REQUEST`,
apply it with :meth:`~scim2_models.PatchOp.patch` (generic, works with any resource type),
convert back to native and persist, then serialize with
:attr:`~scim2_models.Context.RESOURCE_PATCH_RESPONSE`.

.. literalinclude:: _examples/django_example.py
   :language: python
   :start-after: # -- single-resource-start --
   :end-before: # -- single-resource-end --

Collection
^^^^^^^^^^

``UsersView`` handles ``GET /Users`` and ``POST /Users``.
For ``GET``, parse pagination and filtering parameters with
:class:`~scim2_models.SearchRequest`, slice the store, then wrap the page in a
:class:`~scim2_models.ListResponse` serialized with
:attr:`~scim2_models.Context.RESOURCE_QUERY_RESPONSE`.
``req.attributes`` and ``req.excluded_attributes`` are passed to
:meth:`~scim2_models.ListResponse.model_dump_json` to apply the ``attributes`` and
``excludedAttributes`` query parameters to each embedded resource.
For ``POST``, validate the creation payload with
:attr:`~scim2_models.Context.RESOURCE_CREATION_REQUEST`, persist the record, then serialize
with :attr:`~scim2_models.Context.RESOURCE_CREATION_RESPONSE`.
The ``urlpatterns`` list wires both views to their routes.

.. literalinclude:: _examples/django_example.py
   :language: python
   :start-after: # -- collection-start --
   :end-before: # -- collection-end --

Resource versioning (ETags)
===========================

SCIM supports resource versioning through HTTP ETags
(:rfc:`RFC 7644 §3.14 <7644#section-3.14>`).
``check_etag`` compares the record's ETag against the ``If-Match`` header and
returns a 412 SCIM error response on mismatch, or :data:`None` if the check passes.
``make_etag`` computes a weak ETag from each record and populates
:attr:`~scim2_models.Meta.version`.

.. literalinclude:: _examples/django_example.py
   :language: python
   :start-after: # -- etag-start --
   :end-before: # -- etag-end --

On ``GET`` single-resource responses, the ``ETag`` header is set and the ``If-None-Match``
request header is checked manually to return a ``304 Not Modified`` when the client already
has the current version.

On write operations (``PUT``, ``PATCH``, ``DELETE``), the ``If-Match`` header is checked
before processing.
If the client's ETag does not match, a ``412 Precondition Failed`` SCIM error is returned.
``POST`` and ``PUT``/``PATCH`` responses include the ``ETag`` header for the newly created or
updated resource.

.. tip::

   With Django ORM, a :class:`~uuid.UUIDField` regenerated on every
   :meth:`~django.db.models.Model.save` provides a collision-free ETag value
   without relying on clock precision::

      import uuid

      from django.db import models

      class UserModel(models.Model):
          version = models.UUIDField(default=uuid.uuid4)

          def save(self, **kwargs):
              self.version = uuid.uuid4()
              super().save(**kwargs)

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

.. literalinclude:: _examples/django_example.py
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

.. literalinclude:: _examples/django_example.py
   :language: python
   :start-after: # -- resource-types-start --
   :end-before: # -- resource-types-end --

GET /ServiceProviderConfig
^^^^^^^^^^^^^^^^^^^^^^^^^^

Return the :class:`~scim2_models.ServiceProviderConfig` singleton that describes the
features the server supports (patch, bulk, filtering, etc.).

.. literalinclude:: _examples/django_example.py
   :language: python
   :start-after: # -- service-provider-config-start --
   :end-before: # -- service-provider-config-end --

The ``discovery_urlpatterns`` list wires the discovery views to their routes.
Merge it with the resource ``urlpatterns`` in your root URLconf.

Complete example
================

.. literalinclude:: _examples/django_example.py
   :language: python
