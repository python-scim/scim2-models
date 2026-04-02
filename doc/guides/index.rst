Integrations
============

This section shows how to integrate scim2-models with your web framework to build a SCIM server.

Storage layer
-------------

For the sake of simplicity, all integration example will use the following simplistic storage layer.
It wraps an in-memory dictionary and enforces business constraints such as ``userName``
uniqueness.
In real applications, you will replace these functions with ORM calls (Django ORM, SQLAlchemy etc.), and adapt the code accordingly.

.. literalinclude:: _examples/integrations.py
   :language: python
   :caption: Minimalist storage layer
   :start-after: # -- storage-start --
   :end-before: # -- storage-end --

Mapping application data to SCIM
---------------------------------

scim2-models suppose that your application storage layer has its own internal model and does not use SCIM models
internally.
You need mapping helpers that convert between your application representation and the SCIM
resource exposed over HTTP — here :class:`~scim2_models.User`, but the same approach works
for :class:`~scim2_models.Group` or any other resource type.

.. literalinclude:: _examples/integrations.py
   :language: python
   :caption: Example of serialization and deserialization between scim2 and custom model representation
   :start-after: # -- mapping-start --
   :end-before: # -- mapping-end --

This separation keeps the HTTP layer simple.
The views work with SCIM resources, while the rest of the application can keep its own
representation.

.. _discovery-helpers:

Server discovery
----------------

SCIM clients discover the server capabilities by querying three read-only endpoints:
``/Schemas``, ``/ResourceTypes`` and ``/ServiceProviderConfig``
(:rfc:`RFC 7644 §4 <7644#section-4>`).
The helpers below build :class:`~scim2_models.Schema` and
:class:`~scim2_models.ResourceType` objects from the resource models your server exposes,
and define a :class:`~scim2_models.ServiceProviderConfig` describing the server's
capabilities.

.. literalinclude:: _examples/integrations.py
   :language: python
   :caption: Server discovery helpers
   :start-after: # -- discovery-start --
   :end-before: # -- discovery-end --

.. _etag-helpers:

Resource versioning (ETags)
---------------------------

SCIM supports resource versioning through HTTP ETags
(:rfc:`RFC 7644 §3.14 <7644#section-3.14>`).
The helpers below compute a weak ETag from each record's content and verify
``If-Match`` headers on write requests.
The mapping helper ``to_scim_user`` stores the ETag in
:attr:`~scim2_models.Meta.version` so that clients see the current version in
every response.

.. literalinclude:: _examples/integrations.py
   :language: python
   :caption: ETag helpers
   :start-after: # -- etag-start --
   :end-before: # -- etag-end --

.. note::

   In a real application you may not need to compute the hash yourself.
   For example, **SQLAlchemy** exposes a built-in
   :doc:`version counter <sqlalchemy:orm/versioning>` that auto-increments
   a column on every update and raises :exc:`~sqlalchemy.orm.exc.StaleDataError` on conflicts.
   A custom ``version_id_generator`` can produce UUIDs or hashes instead of integers.

Web frameworks
--------------

Those sections show how to process incoming SCIM HTTP requests, and which response to produce.

.. toctree::
   :maxdepth: 1

   flask
   django
