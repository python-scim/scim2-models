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
:attr:`SearchRequest.filter <scim2_models.SearchRequest.filter>` parses. Naming the resource
type the endpoint serves, with
:class:`~scim2_models.SearchRequest`\ [:class:`~scim2_models.User`], checks the filter against
that model as well: an unknown attribute, or a comparison an attribute does not accept, is
refused as the query parameters are validated. That is what turns a malformed filter into a
``400`` rather than into an empty page, and it leaves a filter ready to be matched.

:rfc:`RFC7644 §3.4.2.1 <7644#section-3.4.2.1>` asks something else of an endpoint covering
several resource types, such as the server root: there, "a presence or equality filter for an
undefined attribute evaluates to false". Name them all, with
:class:`~scim2_models.SearchRequest`\ [:class:`~scim2_models.User` | :class:`~scim2_models.Group`],
and an attribute only some of them declare stays valid and evaluates to false on the resources
of the others, while an attribute none of them declares is still refused.

A filter applies to the SCIM representation rather than to the stored records, so the endpoints
map the store first, keep the resources :meth:`ScimFilter.match <scim2_models.ScimFilter.match>` accepts, and
paginate last. ``totalResults`` therefore counts what the filter kept, as
:rfc:`RFC7644 §3.4.2 <7644#section-3.4.2>` requires, and a page never exceeds the bound
:attr:`Filter.max_results <scim2_models.Filter.max_results>` advertises.

That order reads the whole store on every request, which an in-memory example can afford and a
database cannot. A server backed by one translates the filter into a query instead, and lets the
database do the filtering and the pagination; see :ref:`filter-transpiling`.

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
