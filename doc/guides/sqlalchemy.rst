SQLAlchemy
----------

This guide replaces the in-memory storage layer of the :doc:`index` section with a database,
using `SQLAlchemy <https://www.sqlalchemy.org/>`_ and :mod:`scim2_models`.
It is orthogonal to the framework guides: the HTTP layer stays the same, whichever of
:doc:`flask`, :doc:`django` or :doc:`fastapi` it comes from.

It is written for people who know the SQLAlchemy object-relational mapper (ORM) and can read
SQL, and it assumes you have read the :doc:`index` section and the :doc:`../filters` page. The
example runs on SQLAlchemy 2.0 and later, installed with ``pip install sqlalchemy``. It covers
:class:`~scim2_models.User` only, and stops at querying: creation, patching and deletion are
ordinary ORM work that SCIM does not weigh on.

What changes is where the filter is applied. The other guides map every stored record to a
SCIM resource and keep the ones :meth:`ScimFilter.match <scim2_models.ScimFilter.match>` accepts, which reads the
whole store on every request. Here the filter becomes a ``WHERE`` clause, and sorting and
pagination happen next to it, so a page costs a query over the matching rows and not a walk
over all of them.

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

Whether a comparison respects case depends on the engine as much as on the schema. A case-exact
attribute compares with ``LIKE``, which SQLite folds on ASCII unless ``case_sensitive_like`` is
set; PostgreSQL and MySQL settle it with the collation of the column instead.

.. literalinclude:: _examples/sqlalchemy_example.py
   :language: python
   :caption: Engine and session factory
   :start-after: # -- engine-start --
   :end-before: # -- engine-end --

Mapping application data to SCIM
================================

The conversion is the one of the :doc:`index` section, applied to ORM objects instead of
dictionaries. One detail needs a function of its own.

.. warning::

   SQLite gives back a naive :class:`~datetime.datetime`, where a SCIM ``dateTime`` carries an
   offset (:rfc:`RFC7643 §2.3.5 <7643#section-2.3.5>`). A naive instant does not compare with
   the value a filter holds, so ``meta.lastModified gt "…"`` would quietly match nothing.

.. literalinclude:: _examples/sqlalchemy_example.py
   :language: python
   :caption: Conversion between stored rows and SCIM resources
   :start-after: # -- mapping-start --
   :end-before: # -- mapping-end --

Mapping attributes to columns
=============================

A filter names SCIM attributes, such as ``userName`` or ``emails.value``.
:meth:`ScimFilter.resolve_comparison <scim2_models.ScimFilter.resolve_comparison>` looks such a
name up on the model and returns the field it designates: ``user_name`` on
:class:`~scim2_models.User`, or ``value`` on the entries of ``emails``. Which column of which
table stores that field is the one thing scim2-models cannot know. The example writes it down in
a table, keyed on the field and its sub-field. Each entry gives the relationship holding the
attribute, when it lives in a table of its own, and the column to compare:

.. literalinclude:: _examples/sqlalchemy_example.py
   :language: python
   :caption: From a resolved attribute to a column
   :start-after: # -- columns-start --
   :end-before: # -- columns-end --

A convention such as ``getattr(UserRecord, resolved.field_name)`` would spare the table, at the
cost of breaking as soon as a name diverges, and of saying nothing about which relationship an
entry lives in. An explicit table also decides what is *not* queryable: the visitor raises on an
attribute the table omits, instead of querying a column that does not exist.

Transpiling a filter
====================

Turning the filter into a ``WHERE`` clause is the job of a ``FilterVisitor``, the class
:ref:`filter-transpiling` introduces: a subclass says what to emit for each node of the parsed
filter. The ``SqlAlchemyVisitor`` below emits SQLAlchemy expressions instead of SQL text:

.. literalinclude:: _examples/sqlalchemy_example.py
   :language: python
   :caption: Filter to SQLAlchemy expression
   :start-after: # -- visitor-start --
   :end-before: # -- visitor-end --

SQLAlchemy expressions keep it short. The visitor of :ref:`filter-transpiling` refused a
multi-valued attribute, a value selection and the string operators, because each takes SQL that
is hard to write by hand. Here SQLAlchemy writes that SQL. In ``join``,
``relationship_.any(condition)`` is the subquery that looks for a matching entry in the table of
a multi-valued attribute, and ``not_()`` around it is the negation ``ne`` needs. In
``condition``, ``autoescape=True`` escapes the ``%`` and ``_`` a value may contain before a
``LIKE`` reads them as wildcards. And every value reaches the database as a query parameter,
never as text inside the query.

Two decisions remain, and neither is automated:

- **Case**, read from :attr:`~scim2_models.AttributeBinding.case_exact` and the type of the
  attribute. ``icontains`` and ``contains`` differ by one letter and by which resources they
  return.
- **The three-valued logic of SQL**, where ``NULL <> 'Manager'`` is ``NULL`` and not true. A
  missing attribute is not equal to anything, so ``ne`` needs its ``IS NULL`` guard.

The test on the case reads the SCIM type and not the Python one: ``emails.value`` is an
:class:`~pydantic.networks.EmailStr`, which is not a :class:`str` subclass.

Sorting
=======

:attr:`SearchRequest.sort_by <scim2_models.SearchRequest.sort_by>` is a :class:`~scim2_models.Path`,
already resolved against the model on a parameterised request. On a union, it resolves against
the first resource type declaring the attribute. ``sort_expression`` looks the path up in the
same table of columns as the filter does. A sub-attribute is filed under the attribute holding
it, so ``meta.lastModified`` is found at ``("meta", "last_modified")``. The remaining step turns
the column into an ``ORDER BY`` term, and :rfc:`RFC7644 §3.4.2.3 <7644#section-3.4.2.3>` decides
the order in three ways a bare ``ORDER BY column`` follows none of:

- **Case.** A case-insensitive attribute sorts on ``lower(column)``.
- **Missing values.** They come "last if ascending and first if descending".
- **Multi-valued attributes.** They sort "by the value of the primary attribute, if any, or else
  the first value in the list". The example refuses them.

.. literalinclude:: _examples/sqlalchemy_example.py
   :language: python
   :caption: From a ``sortBy`` to an ``ORDER BY`` term
   :start-after: # -- sort-start --
   :end-before: # -- sort-end --

The case is the decision the ``WHERE`` clause already makes, from the same annotation. SQLite
orders with the ``BINARY`` collation, where every uppercase letter precedes every lowercase one,
so ``RSanchez`` would sort ahead of ``bjensen`` instead of behind ``mgarcia``. ``lower()`` costs
the plain index on the column, and a functional index on ``lower(column)`` gives it back. The
``lower()`` of SQLite folds ASCII only, where :meth:`str.casefold` folds everything, so the two
disagree on ``ÉLOÏSE``. PostgreSQL folds by the collation of the column, and a case-insensitive
International Components for Unicode (ICU) collation comes closest to the rule.

PostgreSQL places missing values as the RFC asks by default, ``NULLS LAST`` ascending and
``NULLS FIRST`` descending. SQLite and MySQL take ``NULL`` for the smallest value instead, which
is right descending and wrong ascending. Naming the placement makes the query say what it means
whatever the engine does. MySQL and MariaDB have no ``NULLS`` clause and spell it
``ORDER BY column IS NULL, column``.

The sort key of a multi-valued attribute lives in another table, so it takes a correlated scalar
subquery ordered on ``primary``. And "the first value in the list" means nothing for rows a
relationship gives no order to, short of storing that order in a column of its own. The example
refuses a ``sortBy`` on such an attribute, as it refuses a filter on an attribute it does not
map.

A fourth rule belongs to pagination and costs as little. A page is a slice of an ordered result,
so ``LIMIT`` and ``OFFSET`` need a total order to slice twice the same way. Rows sharing a sort
key, and a query carrying no ``sortBy`` at all, leave the engine free to return one row on two
pages and another on none. Closing the clause with the primary key makes a page reproducible.

Querying
========

``totalResults`` counts what the filter kept, per :rfc:`RFC7644 §3.4.2 <7644#section-3.4.2>`,
so the count runs on the filtered statement before it is paginated. ``MAX_RESULTS`` is the bound
of the :doc:`index` section, the one the :class:`~scim2_models.ServiceProviderConfig` advertises.

.. literalinclude:: _examples/sqlalchemy_example.py
   :language: python
   :caption: Filtering, sorting and paginating
   :start-after: # -- query-start --
   :end-before: # -- query-end --

Two users stored through ``from_scim_user`` are enough to see it run. The filter keeps one of
them, and ``totalResults`` counts it:

.. testsetup::

   from doc.guides._examples.sqlalchemy_example import create_session_factory
   from doc.guides._examples.sqlalchemy_example import from_scim_user
   from doc.guides._examples.sqlalchemy_example import query_users

.. doctest::

    >>> from scim2_models import SearchRequest, User

    >>> Session = create_session_factory()
    >>> with Session() as session:
    ...     session.add(from_scim_user(User(id="1", user_name="bjensen", title="Manager")))
    ...     session.add(from_scim_user(User(id="2", user_name="mgarcia")))
    ...     session.commit()
    ...     request = SearchRequest[User](filter='title pr and userName eq "BJENSEN"')
    ...     total, page = query_users(session, request)
    >>> total, [record.user_name for record in page]
    (1, ['bjensen'])

Checking it against the evaluator
=================================

:meth:`ScimFilter.match <scim2_models.ScimFilter.match>` walks the same tree through the same resolution, on
Python objects instead of on a database, so it answers the question the query is meant to
answer. Running both over the same resources tells a mapping mistake from a correct query. Do it
for any mapping written by hand.

The test suite of this documentation runs its whole list of filters that way. Writing it caught
three defects in this example that had passed review: the naive :class:`~datetime.datetime`
above, the case-folding ``LIKE`` of SQLite, and a case test written on :class:`str` that
silently skipped ``emails.value``. The test is reproduced here as it stands:

.. literalinclude:: ../../tests/test_doc_examples.py
   :language: python
   :caption: Comparing the query to the evaluator
   :start-after: # -- oracle-start --
   :end-before: # -- oracle-end --

The order answers to the same treatment. ``sort_resources``, the helper of the :doc:`index`
section, applies the rules of §3.4.2.3 to Python values, and comparing the two over six
attributes in both orders says whether an ``ORDER BY`` implements them. It caught two defects
of its own. The example refused a ``sortBy`` naming a sub-attribute although its column is
mapped, and the suite asserted the ``BINARY`` order of SQLite for ``sortBy=userName`` as though
it were the one :rfc:`7644` asks for.

.. literalinclude:: ../../tests/test_doc_examples.py
   :language: python
   :caption: Comparing the order to the helper
   :start-after: # -- sort-oracle-start --
   :end-before: # -- sort-oracle-end --
