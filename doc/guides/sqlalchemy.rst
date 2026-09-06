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

Sorting
=======

:attr:`~scim2_models.SearchRequest.sort_by` is a :class:`~scim2_models.Path`, already resolved
against the model on a parameterised request, a union resolving it against the first resource
type declaring the attribute. It is looked up in the same table of columns as a filter, under
the attribute holding it rather than under its own name, since ``meta.lastModified`` is stored
in ``("meta", "last_modified")``. What is left is turning it into an ``ORDER BY`` term, and
:rfc:`RFC7644 §3.4.2.3 <7644#section-3.4.2.3>` decides the order in three ways a bare
``ORDER BY column`` follows none of.

.. literalinclude:: _examples/sqlalchemy_example.py
   :language: python
   :caption: From a ``sortBy`` to an ``ORDER BY`` term
   :start-after: # -- sort-start --
   :end-before: # -- sort-end --

- **the case**, which is the decision the ``WHERE`` clause already makes, from the same
  annotation. SQLite orders with the ``BINARY`` collation, where every uppercase letter
  precedes every lowercase one, so ``RSanchez`` sorts ahead of ``bjensen`` instead of behind
  ``mgarcia``. ``lower()`` settles it, at the price of a plain index on the column, which a
  functional index on ``lower(column)`` gives back. Its folding is not the Unicode one the RFC
  asks for: the ``lower()`` of SQLite only folds ASCII, where :meth:`str.casefold` folds
  everything, so the two part ways on ``ÉLOÏSE``. PostgreSQL folds by the collation of the
  column rather than by no locale in particular, and a case-insensitive ICU collation is the
  closest it comes to the rule;
- **the missing values**, ordered "last if ascending and first if descending". PostgreSQL
  defaults to exactly that, ``NULLS LAST`` ascending and ``NULLS FIRST`` descending; SQLite and
  MySQL take ``NULL`` for the smallest value instead, which is right descending and wrong
  ascending. Naming the placement makes the query say what it means rather than what its engine
  happens to do — bar MySQL and MariaDB, which have no ``NULLS`` clause and spell it
  ``ORDER BY column IS NULL, column``;
- **the multi-valued attributes**, sorted "by the value of the primary attribute, if any, or
  else the first value in the list". That key lives in another table, so it takes a correlated
  scalar subquery ordered on ``primary``, and "the first value in the list" means nothing for
  rows a relationship gives no order to, short of storing that order in a column of its own.
  The example refuses instead, as it refuses a filter on an attribute it does not map.

A fourth rule belongs to pagination rather than to §3.4.2.3, and costs as little. A page is a
slice of an ordered result, so ``LIMIT`` and ``OFFSET`` need a total order to slice twice the
same way. Rows sharing a sort key, and a query carrying no ``sortBy`` at all, leave the engine
free to return one row on two pages and another on none. Closing the clause with the primary
key is what makes a page reproducible.

Querying
========

``totalResults`` counts what the filter kept, per :rfc:`RFC7644 §3.4.2 <7644#section-3.4.2>`,
so the count runs on the filtered statement before it is paginated.

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

The order answers to the same treatment. ``sort_resources``, the helper of the :doc:`index`
section, applies the rules of §3.4.2.3 to Python values, and comparing the two over six
attributes in both orders is what says an ``ORDER BY`` implements them. It caught two defects
of its own: a ``sortBy`` naming a sub-attribute was refused although its column is mapped, and
the suite asserted the ``BINARY`` order of SQLite for ``sortBy=userName`` as though it were the
one :rfc:`7644` asks for.

.. literalinclude:: ../../tests/test_doc_examples.py
   :language: python
   :caption: Comparing the order to the helper
   :start-after: # -- sort-oracle-start --
   :end-before: # -- sort-oracle-end --
