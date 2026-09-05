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

.. _guides-sorting:

Ordering and paging collections
-------------------------------

A collection endpoint answers the ``sortBy``, ``sortOrder``, ``startIndex`` and ``count``
parameters of :rfc:`RFC7644 §3.4.2 <7644#section-3.4.2>`. Naming the resource type the endpoint
serves, with :class:`~scim2_models.SearchRequest`\ [:class:`~scim2_models.User`], resolves
:attr:`~scim2_models.SearchRequest.sort_by` against that model, so the helper below reads
:attr:`Path.field_name <scim2_models.Path.field_name>` instead of the attribute name a client
spelled.

:rfc:`RFC7644 §3.4.2.3 <7644#section-3.4.2.3>` decides the order in three ways the helper
follows: a string attribute is compared without its case unless it is annotated
:attr:`CaseExact.true <scim2_models.CaseExact.true>`; a multi-valued attribute is compared on
the value of its ``primary`` entry, or the first one; and a resource with no value for the
attribute comes last when ascending, first when descending.

.. literalinclude:: _examples/integrations.py
   :language: python
   :caption: Ordering a collection
   :start-after: # -- sorting-start --
   :end-before: # -- sorting-end --

Sorting comes before paging, so a page holds the same resources whatever the order asked for,
and a page never exceeds the ``maxResults`` the
:class:`~scim2_models.ServiceProviderConfig` advertises. Both are what ``page_of`` applies,
and every collection endpoint of the guides goes through it.

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

Web frameworks
--------------

Those sections show how to process incoming SCIM HTTP requests, and which response to produce.

.. toctree::
   :maxdepth: 1

   flask
   django
   fastapi
