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

.. _guides-filtering:

Filtering
---------

Clients narrow a collection with the ``filter`` query parameter
(:rfc:`RFC7644 §3.4.2.2 <7644#section-3.4.2.2>`), which
:attr:`SearchRequest.filter <scim2_models.SearchRequest.filter>` parses and checks the syntax of.
Checking it against the resource model is a second step: binding it with ``ScimFilter[User]``
and calling :meth:`~scim2_models.ScimFilter.validate_semantics` rejects unknown attributes and
comparisons an attribute does not accept, which is what turns a malformed filter into a ``400``
rather than into an empty page.

That is the right behaviour for an endpoint serving one resource type.
:rfc:`RFC7644 §3.4.2.1 <7644#section-3.4.2.1>` requires the opposite of an endpoint covering
several, such as the server root or ``/.search``: there, "a presence or equality filter for an
undefined attribute evaluates to false". Skip :meth:`~scim2_models.ScimFilter.validate_semantics`
on those, and let :meth:`~scim2_models.ScimFilter.match` be tolerant, which it is by default.

A filter applies to the SCIM representation rather than to the stored records, so the endpoints
map the store first, keep the resources :meth:`~scim2_models.ScimFilter.match` accepts, and
paginate last. ``totalResults`` therefore counts what the filter kept, as
:rfc:`RFC7644 §3.4.2 <7644#section-3.4.2>` requires, and a page never exceeds the bound
:attr:`Filter.max_results <scim2_models.Filter.max_results>` advertises.

That order reads the whole store on every request, which an in-memory example can afford and a
database cannot. A server backed by one translates the filter into a query instead, and lets the
database do the filtering and the pagination; see :ref:`filter-transpiling`.

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

Storing resources in a database
-------------------------------

The storage layer above keeps everything in a dictionary, which is what lets the examples stay
short. :doc:`sqlalchemy` replaces it with a database, where the filter becomes a ``WHERE``
clause instead of a predicate applied to every mapped resource, and where sorting and
pagination happen next to it.

.. toctree::
   :maxdepth: 1

   sqlalchemy

Web frameworks
--------------

Those sections show how to process incoming SCIM HTTP requests, and which response to produce.

.. toctree::
   :maxdepth: 1

   flask
   django
   fastapi
