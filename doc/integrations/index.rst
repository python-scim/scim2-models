Integrations
============

This section shows how to serve SCIM over HTTP with scim2-models, from the storage layer to the
discovery endpoints. It is written for people building a SCIM server, and it assumes the
:doc:`../overview`. It groups its pages by integration surface rather than by documentation
genre, since a server is built from all of them at once.

Read :doc:`helpers` first: the storage, mapping, collection and discovery helpers every other
page of the section uses.

Then choose what matches the application:

- :doc:`flask`, :doc:`django` and :doc:`fastapi` each serve the resource, collection, search and
  discovery endpoints with one framework, and each contains a complete runnable example.
- :doc:`filter-transpiler` turns a SCIM filter into an SQL query, for a store too large to walk
  in Python.
- :doc:`sqlalchemy` replaces the in-memory storage layer with a database, where filtering,
  ordering and paging happen in the query.

.. toctree::
   :maxdepth: 1

   helpers
   flask
   django
   fastapi
   filter-transpiler
   sqlalchemy
