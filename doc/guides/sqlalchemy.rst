SQLAlchemy
----------

This guide replaces the in-memory storage layer of the :doc:`index` section with a database,
using `SQLAlchemy <https://www.sqlalchemy.org/>`_ and :mod:`scim2_models`.
It is orthogonal to the framework guides: the HTTP layer stays the same, whichever of
:doc:`flask`, :doc:`django` or :doc:`fastapi` it comes from.

What changes is where the filter is applied. The other guides map every stored record to a
SCIM resource and keep the ones :meth:`ScimFilter.match <scim2_models.ScimFilter.match>` accepts, which reads the
whole store on every request. Here the filter becomes a ``WHERE`` clause, and sorting and
pagination happen next to it, so a page costs a query over the matching rows rather than a
walk over all of them.

The example covers :class:`~scim2_models.User` only, and stops at querying: creation, patching
and deletion are ordinary ORM work that SCIM does not weigh on.

Models
======

A multi-valued attribute becomes a table of its own, keyed on the resource holding it.
Everything else is a column.

.. literalinclude:: _examples/sqlalchemy_example.py
   :language: python
   :caption: Stored models
   :start-after: # -- models-start --
   :end-before: # -- models-end --

Engine
======

Case sensitivity is a property of the engine as much as of the schema. A case-exact attribute
compares with ``LIKE``, which SQLite folds on ASCII unless ``case_sensitive_like`` is set;
PostgreSQL and MySQL settle it with the collation of the column instead.

.. literalinclude:: _examples/sqlalchemy_example.py
   :language: python
   :caption: Engine and session factory
   :start-after: # -- engine-start --
   :end-before: # -- engine-end --

Mapping application data to SCIM
================================

The conversion is the one of the :doc:`index` section, applied to ORM objects instead of
dictionaries. One detail is worth its own function: SQLite gives back a naive
:class:`~datetime.datetime`, where a SCIM ``dateTime`` carries an offset
(:rfc:`RFC7643 §2.3.5 <7643#section-2.3.5>`). A naive instant does not compare with the value a
filter holds, so ``meta.lastModified gt "…"`` would quietly match nothing.

.. literalinclude:: _examples/sqlalchemy_example.py
   :language: python
   :caption: Conversion between stored rows and SCIM resources
   :start-after: # -- mapping-start --
   :end-before: # -- mapping-end --

Mapping attributes to columns
=============================

A filter node carries SCIM attribute names, and
:meth:`ScimFilter.resolve_comparison <scim2_models.ScimFilter.resolve_comparison>` turns one into the field it designates on
the model. Going from there to a column is the one thing scim2-models cannot know, so the
mapping is written out:

.. literalinclude:: _examples/sqlalchemy_example.py
   :language: python
   :caption: From a resolved attribute to a column
   :start-after: # -- columns-start --
   :end-before: # -- columns-end --

A convention such as ``getattr(UserRecord, resolved.field_name)`` would spare the table, at the
cost of breaking as soon as a name diverges, and of saying nothing about which relationship an
entry lives in. An explicit table also decides what is *not* queryable: an attribute it omits
raises rather than producing a query on a column that does not exist.

Transpiling a filter
====================

The visitor produces SQLAlchemy expressions rather than SQL text, which is what makes it short.
Compared to the raw transpiler of :ref:`filter-transpiling`, four pitfalls disappear: the
correlated subquery is ``relationship.any()``, its negation is ``not_(…any())``, ``LIKE``
metacharacters are escaped by ``autoescape=True``, and values are bound rather than
interpolated.

.. literalinclude:: _examples/sqlalchemy_example.py
   :language: python
   :caption: Filter to SQLAlchemy expression
   :start-after: # -- visitor-start --
   :end-before: # -- visitor-end --

Two decisions remain, and neither is automated:

- **case sensitivity**, read from
  :attr:`~scim2_models.ResolvedAttribute.case_exact` and the type of the attribute.
  ``icontains`` and ``contains`` differ by one letter and by which resources they return.
  Note that the test is on the SCIM type rather than on the Python one: ``emails.value`` is an
  :class:`~pydantic.networks.EmailStr`, which is not a :class:`str` subclass;
- **the three-valued logic of SQL**, where ``NULL <> 'Manager'`` is ``NULL`` and not true. A
  missing attribute is not equal to anything, so ``ne`` needs its ``IS NULL`` guard.

Querying
========

``totalResults`` counts what the filter kept, per :rfc:`RFC7644 §3.4.2 <7644#section-3.4.2>`,
so the count runs on the filtered statement before it is paginated.
:attr:`~scim2_models.SearchRequest.sort_by` is a :class:`~scim2_models.Path`, already resolved
against the model on a parameterised request, and looked up in the same table of columns, which
is also what rejects sorting on an attribute stored in another table. A request parameterised
with a union resolves it too, against the first resource type declaring the attribute.

.. literalinclude:: _examples/sqlalchemy_example.py
   :language: python
   :caption: Filtering, sorting and paginating
   :start-after: # -- query-start --
   :end-before: # -- query-end --

Checking it against the evaluator
=================================

:meth:`ScimFilter.match <scim2_models.ScimFilter.match>` walks the same tree through the same resolution, on
Python objects instead of on a database, so it answers the question the query is meant to
answer. Running both over the same resources is what tells a mapping mistake from a correct
query, and it is worth doing for a mapping written by hand.

The test suite of this documentation runs twenty-three filters that way. Writing it caught
three defects in this very example, none of which a reading had caught: the naive
:class:`~datetime.datetime` above, the case-folding ``LIKE`` of SQLite, and a case test written
on :class:`str` that silently skipped ``emails.value``.

.. literalinclude:: ../../tests/test_doc_examples.py
   :language: python
   :caption: Comparing the query to the evaluator
   :start-after: # -- oracle-start --
   :end-before: # -- oracle-end --
