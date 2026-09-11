Shared helpers for a SCIM server
================================

Every framework guide of this section serves the same resources over the same rules, and differs
only in the HTTP layer. This page holds what they share: a storage layer, the conversion between
the application model and SCIM resources, the filtering, ordering and paging of a collection, and
the three discovery endpoints. Read it before a framework guide, which assumes these helpers.

The code shown here favours brevity over completeness: it keeps resources in a dictionary and
walks them in Python. :doc:`sqlalchemy` replaces both with a database.

Storage layer
-------------

The examples share a deliberately simplistic storage layer. It wraps an in-memory dictionary and
enforces business constraints such as :attr:`userName <scim2_models.User.user_name>` uniqueness.
A real application replaces these functions with ORM calls, and adapts the code accordingly.

.. literalinclude:: _examples/integrations.py
   :language: python
   :caption: Minimalist storage layer
   :start-after: # -- storage-start --
   :end-before: # -- storage-end --

Mapping application data to SCIM
--------------------------------

scim2-models assumes the application storage layer has its own internal model, and does not use
SCIM models internally. Mapping helpers convert between the application representation and the
SCIM resource exposed over HTTP — here :class:`~scim2_models.User`, but the same approach works
for :class:`~scim2_models.Group` or any other resource type.

.. literalinclude:: _examples/integrations.py
   :language: python
   :caption: Serialization and deserialization between SCIM and a custom model
   :start-after: # -- mapping-start --
   :end-before: # -- mapping-end --

This separation keeps the HTTP layer simple. The views work with SCIM resources, while the rest
of the application keeps its own representation.

.. _helpers-filtering:

Filtering
---------

Clients narrow a collection with the ``filter`` query parameter (:rfc:`RFC7644 §3.4.2.2
<7644#section-3.4.2.2>`), which :attr:`SearchRequest.filter <scim2_models.SearchRequest.filter>`
parses. Name the resource type the endpoint serves, with :class:`~scim2_models.SearchRequest`\
[:class:`~scim2_models.User`], and the request checks the filter against that model as well. It
refuses an unknown attribute, or a comparison an attribute does not accept, while it validates
the query parameters. A malformed filter thus answers ``400`` instead of an empty page, and a
valid one comes out ready to match.

:rfc:`RFC7644 §3.4.2.1 <7644#section-3.4.2.1>` asks something else of an endpoint covering
several resource types, such as the server root: there, "a presence or equality filter for an
undefined attribute evaluates to false". Name them all, with
:class:`~scim2_models.SearchRequest`\ [:class:`~scim2_models.User` |
:class:`~scim2_models.Group`]. An attribute only some of them declare stays valid, and evaluates
to false on the resources of the others. An attribute none of them declares is still refused.

A filter applies to the SCIM representation and not to the stored records, so the endpoints map
the store first, keep the resources :meth:`ScimFilter.match <scim2_models.ScimFilter.match>`
accepts, and paginate last. ``totalResults`` therefore counts what the filter kept, as
:rfc:`RFC7644 §3.4.2 <7644#section-3.4.2>` requires, and a page never exceeds the bound
:attr:`Filter.max_results <scim2_models.Filter.max_results>` advertises.

That order reads the whole store on every request, which an in-memory example can afford and a
database cannot. :doc:`filter-transpiler` translates a filter into a query instead, and
:doc:`sqlalchemy` lets the database filter and paginate.

.. _helpers-sorting:

Ordering and paging collections
-------------------------------

A collection endpoint answers the ``sortBy``, ``sortOrder``, ``startIndex`` and ``count``
parameters of :rfc:`RFC7644 §3.4.2 <7644#section-3.4.2>`. Naming the resource type the endpoint
serves, with :class:`~scim2_models.SearchRequest`\ [:class:`~scim2_models.User`], resolves
:attr:`~scim2_models.SearchRequest.sort_by` against that model, so ``sort_value`` works from the
:class:`~scim2_models.AttributeBinding` it designates instead of from the name a client spelled.

:rfc:`RFC7644 §3.4.2.3 <7644#section-3.4.2.3>` decides the order in three ways, and
``sort_value`` follows them:

- A string attribute is compared without its case, unless it is annotated
  :attr:`CaseExact.true <scim2_models.CaseExact.true>`.
- A multi-valued attribute is compared on the value of its ``primary`` entry, or of the first
  one.
- A resource with no value for the attribute comes last when ascending, first when descending.

The second rule is why ``sort_value`` picks an entry before reading a sub-attribute from it:
``emails.value`` designates the value of *every* entry, where an order wants one value per
resource. ``sortBy=emails`` is therefore the same query as ``sortBy=emails.value``,
:rfc:`RFC7643 §2.4 <7643#section-2.4>` holding the significant value of a complex entry in its
``value`` sub-attribute.

.. literalinclude:: _examples/integrations.py
   :language: python
   :caption: Ordering a collection
   :start-after: # -- sorting-start --
   :end-before: # -- sorting-end --

Sorting comes before paging, so a page holds the same resources whatever the order asked for, and
a page never exceeds the ``maxResults`` the :class:`~scim2_models.ServiceProviderConfig`
advertises. Both are what ``page_of`` applies, and every collection endpoint of this section goes
through it.

.. _helpers-discovery:

Server discovery
----------------

SCIM clients discover the server capabilities by querying three read-only endpoints:
``/Schemas``, ``/ResourceTypes`` and ``/ServiceProviderConfig`` (:rfc:`RFC 7644 §4
<7644#section-4>`). A :class:`~scim2_models.ScimProvider` answers all three: give it the resource
models the server serves and the capabilities it announces, and it derives the
:class:`~scim2_models.Schema` and :class:`~scim2_models.ResourceType` objects the first two
endpoints return.

Deriving them is what keeps the three endpoints and the resources they describe from drifting
apart. The two helpers below only pick one object out of a collection, which is what
``/Schemas/<id>`` and ``/ResourceTypes/<id>`` serve.

.. literalinclude:: _examples/integrations.py
   :language: python
   :caption: Server discovery helpers
   :start-after: # -- discovery-start --
   :end-before: # -- discovery-end --
