Flask
-----

This guide shows a minimal SCIM server built with `Flask <https://flask.palletsprojects.com/>`_
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

   pip install flask scim2-models

Blueprint setup
===============

Start with a Flask blueprint.
The SCIM specifications indicates that the responses content type must be ``application/scim+json``,
so lets enforce this on all the blueprint views with :meth:`~flask.Blueprint.after_request`.

.. literalinclude:: _examples/flask_example.py
   :language: python
   :start-after: # -- setup-start --
   :end-before: # -- setup-end --

Optional Flask refinements
==========================

The core SCIM flow only needs the blueprint and the endpoints below.
Flask also offers a few convenient integration patterns that can keep the views shorter and
help keep framework-level errors aligned with SCIM responses.

Flask converters
^^^^^^^^^^^^^^^^

Converters let Flask resolve route parameters before the view function is called.
Define one converter per resource type: it maps a resource identifier to an application
record and lets Flask handle the not-found case before entering the view.
``bp.record_once`` registers the converter on the app when the blueprint is attached.

.. literalinclude:: _examples/flask_example.py
   :language: python
   :start-after: # -- converters-start --
   :end-before: # -- converters-end --

Error handlers
^^^^^^^^^^^^^^

The error handlers keep Pydantic validation errors and Flask 404s aligned with SCIM
responses.

.. literalinclude:: _examples/flask_example.py
   :language: python
   :start-after: # -- error-handlers-start --
   :end-before: # -- error-handlers-end --

If :meth:`~scim2_models.Resource.model_validate`, Flask routes the
:class:`~pydantic.ValidationError` to ``handle_validation_error`` and the client receives a
SCIM :class:`~scim2_models.Error` response.
``handle_value_error`` catches the ``ValueError`` raised by ``save_record`` and returns a 409
with ``scimType: uniqueness`` using :class:`~scim2_models.UniquenessException`.

Endpoints
=========

The routes below serve ``/Users``, but the same structure applies to any resource type:
replace the mapping helpers, the model class, and the URL prefix to expose ``/Groups`` or
any other collection.

GET /Users/<id>
^^^^^^^^^^^^^^^

Parse query parameters with :class:`~scim2_models.ResponseParameters`, convert the native
record to a SCIM resource with your mapping helper, then serialize with
:attr:`~scim2_models.Context.RESOURCE_QUERY_RESPONSE`, forwarding
``req.attributes`` and ``req.excluded_attributes`` so the response only includes the
requested fields.

.. literalinclude:: _examples/flask_example.py
   :language: python
   :start-after: # -- get-user-start --
   :end-before: # -- get-user-end --

DELETE /Users/<id>
^^^^^^^^^^^^^^^^^^

Remove the record from the store and return an empty 204 response.
No SCIM serialization is needed.

.. literalinclude:: _examples/flask_example.py
   :language: python
   :start-after: # -- delete-user-start --
   :end-before: # -- delete-user-end --

PATCH /Users/<id>
^^^^^^^^^^^^^^^^^

Validate the patch payload with :attr:`~scim2_models.Context.RESOURCE_PATCH_REQUEST`,
apply it to a SCIM conversion of the native record with :meth:`~scim2_models.PatchOp.patch`,
convert back to native and persist, then serialize the result with
:attr:`~scim2_models.Context.RESOURCE_PATCH_RESPONSE`.
:class:`~scim2_models.PatchOp` is generic and works with any resource type.

.. literalinclude:: _examples/flask_example.py
   :language: python
   :start-after: # -- patch-user-start --
   :end-before: # -- patch-user-end --

PUT /Users/<id>
^^^^^^^^^^^^^^^

Validate the full replacement payload with
:attr:`~scim2_models.Context.RESOURCE_REPLACEMENT_REQUEST`, passing the ``original`` resource
so that immutable attributes are checked for unintended modifications.
Convert back to native and persist, then serialize the result with
:attr:`~scim2_models.Context.RESOURCE_REPLACEMENT_RESPONSE`.

.. literalinclude:: _examples/flask_example.py
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

.. literalinclude:: _examples/flask_example.py
   :language: python
   :start-after: # -- list-users-start --
   :end-before: # -- list-users-end --

POST /Users
^^^^^^^^^^^

Validate the creation payload with :attr:`~scim2_models.Context.RESOURCE_CREATION_REQUEST`,
convert to native and persist, then serialize the created resource with
:attr:`~scim2_models.Context.RESOURCE_CREATION_RESPONSE`.

.. literalinclude:: _examples/flask_example.py
   :language: python
   :start-after: # -- create-user-start --
   :end-before: # -- create-user-end --

Complete example
================

.. literalinclude:: _examples/flask_example.py
   :language: python
