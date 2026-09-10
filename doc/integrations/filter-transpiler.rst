.. _filter-transpiling:

Write a filter transpiler
=========================

In this tutorial, a SCIM filter becomes the ``WHERE`` clause of an SQL query, and the query is
checked against the filter evaluator of scim2-models. The result is a working transpiler of about
forty lines, and a test that says whether it answers the question the filter asked.

The tutorial is written for people building a SCIM server who can read SQL. It assumes the
:ref:`Filter resources <overview-filters>` section of the :doc:`../overview`, and it uses SQLite
through the :mod:`sqlite3` module of the standard library, so it needs no installation.
:doc:`../explanation/filters` covers the grammar and the comparison rules the transpiler has to
honour; :doc:`sqlalchemy` covers the same work on a real ORM.

Over a large collection, a filter has to become a query the database runs: a ``WHERE`` clause, or
its equivalent in another store. A server receives filters from its clients, in the query
parameter of a ``GET /Users?filter=…`` or in the
:attr:`SearchRequest.filter <scim2_models.SearchRequest.filter>` of a ``POST /Users/.search``.
The framework guides of this section answer such a request with
:meth:`ScimFilter.match <scim2_models.ScimFilter.match>`: they load every resource and keep the
ones that match. That works while the store is small. Over a million users, every request reads
the whole table.

Read a filter as a tree
-----------------------

scim2-models ships no SQL, and provides instead the parts such a query is written from.
:class:`~scim2_models.ScimFilter` parses a filter when it is created, and keeps the result in
:attr:`ScimFilter.ast <scim2_models.ScimFilter.ast>`: an abstract syntax tree, that is, a set of
nodes referencing each other. ``userName eq "bjensen" and title pr`` is a
:class:`~scim2_models.path.LogicalExpr` node with two terms, a
:class:`~scim2_models.path.Comparison` and a :class:`~scim2_models.path.Present`, each holding
the :class:`~scim2_models.path.AttrPath` it applies to:

.. doctest::

    >>> ScimFilter('userName eq "bjensen" and title pr').ast  # doctest: +NORMALIZE_WHITESPACE
    LogicalExpr(op=<LogicalOperator.and_: 'and'>,
                terms=(Comparison(attr_path=AttrPath(attr='userName', sub_attr=None, uri=None),
                                  op=<CompareOperator.eq: 'eq'>, value='bjensen'),
                       Present(attr_path=AttrPath(attr='title', sub_attr=None, uri=None))))

:class:`~scim2_models.path.FilterVisitor` is a class that walks such a tree. A subclass says what
to do for each type of node. For a :class:`~scim2_models.path.LogicalExpr`, write ``AND`` or
``OR`` between its terms; for a :class:`~scim2_models.path.Comparison`, ``column = ?``; for a
:class:`~scim2_models.path.Present`, ``column IS NOT NULL``.
:meth:`~scim2_models.path.FilterVisitor.visit` dispatches a node to the method of its type and
returns what that method returns. A subclass that turns a filter into a query for another system
is a transpiler.

A filter is checked before it is translated. The constructor checks its syntax. Binding the
filter to a model checks the attributes it names, which :class:`~scim2_models.SearchRequest`\
[:class:`~scim2_models.User`] does for a query parameter. The visitor of this tutorial assumes a
filter that passed both checks, so it can resolve a path without handling an unknown attribute at
every node.

Write the visitor
-----------------

This first visitor writes the ``WHERE`` clause of a filter over single-valued attributes, each
stored in one column, ``meta.lastModified`` in ``meta_last_modified``. A node only carries the
*name* of an attribute. The visitor first resolves that name against the model, with
:meth:`ScimFilter.resolve_comparison <scim2_models.ScimFilter.resolve_comparison>` or
:meth:`ScimFilter.resolve <scim2_models.ScimFilter.resolve>`. The result names the field holding
the attribute, and says whether the comparison ignores case. The values do not go into the SQL.
The visitor collects them in ``params``, which the database driver sends separately from the
query. :func:`~scim2_models.path.coerce_value` converts each one beforehand, from the JSON value
the filter carries to the Python value the attribute holds. The visitor refuses whatever is
harder in SQL than in SCIM, instead of guessing:

.. doctest::

    >>> from scim2_models import Attribute
    >>> from scim2_models.path import CompareOperator, FilterVisitor, LogicalOperator, coerce_value

    >>> SQL_OPERATORS = {
    ...     CompareOperator.eq: "=",
    ...     CompareOperator.ne: "<>",
    ...     CompareOperator.gt: ">",
    ...     CompareOperator.ge: ">=",
    ...     CompareOperator.lt: "<",
    ...     CompareOperator.le: "<=",
    ... }

    >>> class SqlVisitor(FilterVisitor[str]):
    ...     def __init__(self, scim_filter):
    ...         self.filter = scim_filter
    ...         self.params = []
    ...
    ...     def column(self, resolved):
    ...         if resolved.is_multivalued:
    ...             raise NotImplementedError("a multi-valued attribute needs a subquery")
    ...         if resolved.sub_field_name:
    ...             return f"{resolved.field_name}_{resolved.sub_field_name}"
    ...         return resolved.field_name
    ...
    ...     def casefolded(self, resolved):
    ...         """Only a string has a case, and only some strings ignore it."""
    ...         scim_type = Attribute.Type.from_python(resolved.target_type)
    ...         return scim_type == Attribute.Type.string and not resolved.case_exact
    ...
    ...     def visit_comparison(self, node):
    ...         if node.op not in SQL_OPERATORS:
    ...             raise NotImplementedError("a string operator needs LIKE and its escaping")
    ...         resolved = self.filter.resolve_comparison(node.attr_path)
    ...         self.params.append(coerce_value(resolved, node.value, node.op))
    ...         column, value = self.column(resolved), "?"
    ...         if self.casefolded(resolved):
    ...             column, value = f"LOWER({column})", "LOWER(?)"
    ...         return f"{column} {SQL_OPERATORS[node.op]} {value}"
    ...
    ...     def visit_present(self, node):
    ...         resolved = self.filter.resolve(node.attr_path)
    ...         return f"{self.column(resolved)} IS NOT NULL"
    ...
    ...     def visit_not(self, node):
    ...         return f"NOT ({self.visit(node.expr)})"
    ...
    ...     def visit_logical_expr(self, node):
    ...         joiner = " AND " if node.op == LogicalOperator.and_ else " OR "
    ...         return "(" + joiner.join(self.visit(term) for term in node.terms) + ")"
    ...
    ...     def visit_value_path(self, node):
    ...         raise NotImplementedError("a value selection needs a subquery")

    >>> def to_sql(scim_filter):
    ...     """Return the ``WHERE`` clause of a filter, and the values it binds."""
    ...     visitor = SqlVisitor(scim_filter)
    ...     return visitor.visit(scim_filter.ast), visitor.params

Run the transpiler
------------------

A comparison on a string attribute reads a column and ignores case. A presence test checks the
column for ``NULL``:

.. doctest::

    >>> where, params = to_sql(ScimFilter[User]('userName eq "bjensen" and title pr'))
    >>> print(where)
    (LOWER(user_name) = LOWER(?) AND title IS NOT NULL)
    >>> params
    ['bjensen']

A dateTime is passed as the :class:`~datetime.datetime` the attribute holds, not as the string
the filter spelled. A boolean has no case, so the visitor compares it as it is:

.. doctest::

    >>> scim_filter = ScimFilter[User](
    ...     'meta.lastModified gt "2024-01-01T00:00:00Z" and active eq true'
    ... )
    >>> where, params = to_sql(scim_filter)
    >>> print(where)
    (meta_last_modified > ? AND active = ?)
    >>> [type(param).__name__ for param in params]
    ['datetime', 'bool']

Check the query against the evaluator
-------------------------------------

The example refuses five things a complete transpiler has to handle:

- **A multi-valued attribute**, stored in a table of its own. A comparison reaches it through a
  correlated subquery, such as
  ``EXISTS (SELECT 1 FROM emails WHERE emails.parent_id = resource.id AND …)``.
- **A value selection.** Its whole filter goes inside that one subquery, with each of its paths
  scoped to the entry.
- **``ne``**, which holds when *no* value matches, as :ref:`filter-open-choices` explains. On a
  multi-valued attribute it negates the whole subquery. On any attribute it needs an ``IS NULL``
  guard, because SQL discards a row where the column is ``NULL``, while a missing attribute is
  not equal to anything.
- **The string operators**, which ``LIKE`` implements once the ``%`` and ``_`` in the value are
  escaped. Otherwise ``title co "100%"`` also selects ``"1000 Files"``.
- **The case**, which ``LOWER()`` folds over ASCII only, where :rfc:`7643` asks for Unicode
  folding. :ref:`filter-open-choices` describes the difference.

Each of these mistakes produces valid SQL that answers a different question than the filter
asked. :meth:`ScimFilter.match <scim2_models.ScimFilter.match>` walks the same tree through the
same resolution, on Python objects instead of on a database. Run both over the same resources and
compare the results. That check is the test suite of a transpiler. Here it is over an in-memory
SQLite table:

.. doctest::

    >>> import sqlite3

    >>> def store(users):
    ...     """Load the resources in a table, one column per attribute."""
    ...     connection = sqlite3.connect(":memory:")
    ...     connection.execute("CREATE TABLE users (id, user_name, title)")
    ...     connection.executemany(
    ...         "INSERT INTO users VALUES (?, ?, ?)",
    ...         [(user.id, user.user_name, user.title) for user in users],
    ...     )
    ...     return connection

    >>> users = [
    ...     User(id="1", user_name="bjensen", title="Manager"),
    ...     User(id="2", user_name="mgarcia"),
    ... ]
    >>> connection = store(users)

    >>> def query(scim_filter):
    ...     where, params = to_sql(scim_filter)
    ...     rows = connection.execute(f"SELECT id FROM users WHERE {where}", params)
    ...     return [row[0] for row in rows]

    >>> def evaluate(scim_filter):
    ...     return [user.id for user in users if scim_filter.match(user)]

    >>> scim_filter = ScimFilter[User]('title pr and userName eq "BJENSEN"')
    >>> query(scim_filter)
    ['1']
    >>> evaluate(scim_filter)
    ['1']

Where to go next
----------------

The transpiler now answers five filters over three columns, and the oracle says its answers match
the evaluator. What it does not answer yet are the five cases it refuses: multi-valued
attributes, value selections, ``ne``, the string operators and Unicode case folding. The
:doc:`sqlalchemy` guide handles each of them on SQLAlchemy expressions, and runs every filter of
its test list through both the query and the evaluator.

A search request also carries a ``sortBy`` parameter.
:attr:`SearchRequest.sort_by <scim2_models.SearchRequest.sort_by>` is a
:class:`~scim2_models.Path`, and it resolves the same way. The attribute it resolves to names the
column an ``ORDER BY`` sorts on. The column alone does not settle the order: the case, the missing
values and the multi-valued attributes each have a rule of their own in
:rfc:`RFC7644 §3.4.2.3 <7644#section-3.4.2.3>`. The :doc:`sqlalchemy` guide implements them.
