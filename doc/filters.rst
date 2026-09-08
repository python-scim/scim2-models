Advanced filters
----------------

This page picks up where the :ref:`Filters <tutorial-filters>` section of the tutorial leaves
off, and assumes you have read it. It covers three things: how to build a filter from values you
do not trust, how to turn a filter into a database query, and where the implemented grammar
departs from the published RFC. The second part is written for people implementing a SCIM
server, and assumes you can read SQL. The page does not describe the filter syntax itself, which
:rfc:`RFC7644 §3.4.2.2 <7644#section-3.4.2.2>` does.

The examples below carry on from that section:

.. doctest::

    >>> from scim2_models import ScimFilter, User

    >>> user = User(
    ...     user_name="bjensen",
    ...     emails=[{"type": "work", "value": "bjensen@example.com"}],
    ... )

Building a filter
=================

The values a filter compares often come from outside: a name typed by a user, an identifier
read from another system. Pasted into the filter string as they are, they can change what the
filter means:

.. doctest::

    >>> untrusted = 'x" or userName pr or userName eq "y'
    >>> forged = ScimFilter[User]('userName eq "%s"' % untrusted)
    >>> forged.match(user)
    True

In this example, the caller wrote one comparison and got three. The filter now matches every
user that has a ``userName``. :meth:`ScimFilter.quote <scim2_models.ScimFilter.quote>` prevents
this: it turns a value into one literal, quotes included. Put that literal in a slot with no
quotes around it, and the value stays a value whatever it contains:

.. doctest::

    >>> quoted = ScimFilter[User](f"userName eq {ScimFilter.quote(untrusted)}")
    >>> print(quoted)
    userName eq "x\" or userName pr or userName eq \"y"
    >>> quoted.match(user)
    False

``quote`` also takes a number, a boolean, :data:`None` or a :class:`~datetime.datetime`; its
documentation lists them. The literal works in a :class:`~scim2_models.Path` as well, since the
selection between its brackets is a filter.

On Python 3.14, write the filter as a t-string and the constructor quotes every interpolated
value for you, in a filter as in a path:

.. code-block:: python

    ScimFilter[User](t"userName eq {untrusted} and meta.lastModified gt {since}")
    Path[Group](t"members[value eq {member_id}]")

Quoting protects values only. You cannot escape an attribute name, because the grammar has no
quoted form for a name. Check a name that comes from outside instead. Build a
:class:`~scim2_models.Path` from it: the constructor refuses anything that is not a path, so it
rejects ``userName eq "admin" or userName`` before the name reaches the filter. A t-string
inserts a path as it stands, without quoting it:

.. code-block:: python

    ScimFilter[User](t"{Path[User](attribute)} eq {value}")

Binding the filter to a model does not replace that check. Binding refuses a name the model
does not declare, but a forged fragment can name declared attributes only. Binding also refuses
the name late: when a :class:`~scim2_models.SearchRequest` validates the filter, or when you
resolve a node. Creating the bound filter accepts the unknown name, because an endpoint that
serves several resource types must evaluate it to false rather than fail
(:rfc:`RFC7644 §3.4.2.1 <7644#section-3.4.2.1>`).

You can also build a filter without writing any SCIM syntax. Expression nodes combine with the
Python boolean operators and render back to valid syntax, parentheses included. A
:class:`~scim2_models.path.Comparison` quotes its value the same way, and an
:class:`~scim2_models.path.AttrPath` refuses a name the grammar would not read as one:

.. doctest::

    >>> from scim2_models.path import AttrPath, Comparison, CompareOperator, Present

    >>> work = Comparison(AttrPath("userName"), CompareOperator.eq, "bjensen")
    >>> titled = Present(AttrPath("title"))
    >>> print(work & titled)
    userName eq "bjensen" and title pr
    >>> print(~work | titled)
    not (userName eq "bjensen") or title pr

    >>> ScimFilter[User](work & titled).match(user)
    False

.. _filter-transpiling:

Writing a query
===============

Over a large collection, a filter has to become a query the database runs: a ``WHERE`` clause,
or its equivalent in another store. A server receives filters from its clients, in the query
parameter of a ``GET /Users?filter=…`` or in the
:attr:`SearchRequest.filter <scim2_models.SearchRequest.filter>` of a ``POST /Users/.search``.
The :doc:`guides/index` guides answer such a request with
:meth:`ScimFilter.match <scim2_models.ScimFilter.match>`: they load every resource and keep the
ones that match. That works while the store is small. Over a million users, every request reads
the whole table.

scim2-models ships no SQL, but it gives you the parts you need to write that query yourself.
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

:class:`~scim2_models.path.FilterVisitor` is a class that walks such a tree. You subclass it and
write what to do for each type of node. For a ``LogicalExpr``, write ``AND`` or ``OR`` between
its terms; for a ``Comparison``, ``column = ?``; for a ``Present``, ``column IS NOT NULL``.
:meth:`~scim2_models.path.FilterVisitor.visit` dispatches a node to the method of its type and
returns what that method returns. A subclass that turns a filter into a query for another
system is called a transpiler below.

Check the filter before you translate it. The constructor checks its syntax. Binding the filter
to a model checks the attributes it names, which
:class:`~scim2_models.SearchRequest`\ [:class:`~scim2_models.User`] does for a query parameter.
The visitor below assumes a filter that passed both checks, so it can resolve a path without
handling an unknown attribute at every node.

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
    >>> from scim2_models.path import FilterVisitor, LogicalOperator, coerce_value

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

The example refuses five things a complete transpiler has to handle:

- **A multi-valued attribute**, stored in a table of its own. A comparison reaches it through a
  correlated subquery, such as
  ``EXISTS (SELECT 1 FROM emails WHERE emails.parent_id = resource.id AND …)``.
- **A value selection.** Its whole filter goes inside that one subquery, with each of its paths
  scoped to the entry.
- **``ne``**, which holds when *no* value matches, as :ref:`filter-deviations` explains. On a
  multi-valued attribute it negates the whole subquery. On any attribute it needs an ``IS NULL``
  guard, because SQL discards a row where the column is ``NULL``, while a missing attribute is
  not equal to anything.
- **The string operators**, which ``LIKE`` implements once the ``%`` and ``_`` in the value are
  escaped. Otherwise ``title co "100%"`` also selects ``"1000 Files"``.
- **The case**, which ``LOWER()`` folds over ASCII only, where :rfc:`7643` asks for Unicode
  folding. :ref:`filter-deviations` describes the difference.

Each of these mistakes produces valid SQL that answers a different question than the filter
asked. :meth:`ScimFilter.match <scim2_models.ScimFilter.match>` walks the same tree through the
same resolution, on Python objects instead of on a database. Run both over the same resources
and compare the results. That check is the test suite of a transpiler. Here it is over an
in-memory SQLite table:

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

The :doc:`guides/sqlalchemy` guide handles each of these cases on SQLAlchemy expressions, and
runs every filter of its test list through both.

A search request also carries a ``sortBy`` parameter.
:attr:`SearchRequest.sort_by <scim2_models.SearchRequest.sort_by>` is a
:class:`~scim2_models.Path`, and it resolves the same way. The attribute it resolves to names
the column an ``ORDER BY`` sorts on. The column alone does not settle the order: the case, the
missing values and the multi-valued attributes each have a rule of their own in
:rfc:`RFC7644 §3.4.2.3 <7644#section-3.4.2.3>`. The :doc:`guides/sqlalchemy` guide implements
them.

.. _filter-deviations:

Deviations from the published RFC
=================================

:rfc:`7644` publishes its grammar in Augmented Backus–Naur Form (ABNF), and that grammar has
several defects. The grammar implemented here applies the errata that correct them. The table
gives the status each erratum had when it was applied. An erratum is *reported* when someone
submits it, *verified* once the RFC editors confirm the error, and *held for document update*
when they find it worth considering in a future revision without settling it now. None of the
errata correcting the grammar is verified yet, and a reported one may still be rejected.

.. list-table:: Errata applied to the grammar
   :header-rows: 1
   :widths: 10 20 70

   * - Errata
     - Status
     - Correction
   * - `4670 <https://www.rfc-editor.org/errata/eid4670>`_
     - Held for document update
     - The published order of precedence is reversed. Attribute operators take precedence over
       logical ones, ``not`` over ``and``, and ``and`` over ``or``.
   * - `4690 <https://www.rfc-editor.org/errata/eid4690>`_,
       `7322 <https://www.rfc-editor.org/errata/eid7322>`_
     - Held for document update, reported
     - The published rule lets a value selection nest another one, as in
       ``emails[type eq "work" and emails[type eq "home"]]``. 4690 closes the recursion but also
       forbids the parentheses and the three-term expressions implementations write, and 7322,
       which the grammar follows, restores them.
   * - `7319 <https://www.rfc-editor.org/errata/eid7319>`_
     - Reported
     - The grammar forbids a space between ``not`` and its parenthesis, which the examples of
       the RFC itself use. The parser accepts both ``not (x pr)`` and ``not(x pr)``.
   * - `7122 <https://www.rfc-editor.org/errata/eid7122>`_
     - Held for document update
     - The ``PATH`` rule of a PATCH operation lacks ``attrExp``. It is the only way to target a
       value of a multi-valued attribute that is not complex, such as ``schemas eq "urn:…"``.
   * - `8924 <https://www.rfc-editor.org/errata/eid8924>`_
     - Reported
     - ``ATTRNAME`` excludes ``$ref`` although RFC 7643 uses it. The parser accepts a leading
       ``$``.
   * - `6001 <https://www.rfc-editor.org/errata/eid6001>`_,
       `8472 <https://www.rfc-editor.org/errata/eid8472>`_
     - Held for document update, verified
     - Reference attributes are declared ``caseExact: false`` while §2.3.7 requires them to be
       case-exact. scim2-models annotates ``profileUrl``, ``groups.value``, ``groups.$ref``,
       ``members.value``, ``members.$ref`` and ``manager.$ref`` with
       :attr:`CaseExact.true <scim2_models.CaseExact.true>`, and
       :meth:`~scim2_models.Resource.to_schema` reflects it.

The grammar is also stricter than the published ABNF on five points. No deployment we know of
needs any of them:

Schema URIs
    §3.4.2.2 defines ``URI`` per :rfc:`Appendix A of RFC3986 <3986#appendix-A>`, which any
    scheme satisfies. The grammar accepts Uniform Resource Names (URNs) only, since every schema
    URI the SCIM specifications define is one.

A sub-attribute before a value selection
    ``valuePath = attrPath "[" valFilter "]"`` lets the ``attrPath`` carry a sub-attribute, so
    ``emails.type[type eq "work"]`` is legal ABNF. The filter between the brackets addresses
    the sub-attributes of the attribute in front of them, and
    :rfc:`RFC7643 §2.3.8 <7643#section-2.3.8>` gives a sub-attribute none of its own. The form
    has no possible meaning. The parser answers ``invalidFilter``, and ``invalidPath`` in a
    PATCH path.

A schema URN inside a value selection
    ``valFilter`` reaches ``attrPath``, which carries an optional ``URI``, so
    ``emails[urn:ietf:params:scim:schemas:core:2.0:User:type eq "work"]`` is legal ABNF. The
    brackets address the sub-attributes of the attribute in front of them, and §3.10 qualifies
    a sub-attribute through the attribute holding it: ``urn:…:User:emails.type``, never
    ``urn:…:User:type``. A URN designates nothing there, and the parser answers
    ``invalidFilter``.

``$`` in an attribute name
    :rfc:`RFC7643 §2.1 <7643#section-2.1>` puts ``$`` in ``nameChar``, so ``foo$bar`` is a
    legal name. The parser accepts a leading ``$`` only. Errata 8924 asks for that, and
    ``$ref`` needs it.

Numbers out of range
    A literal such as ``1e400`` would read as an infinity, which the ABNF has no syntax for, so
    it could not be rendered back into a filter. The parser rejects it.

The RFC leaves seven further choices open:

``ne`` on a multi-valued attribute
    §3.4.2.2 states that a filter matches "if any of the values" matches, without saying what
    that means for a negation. :meth:`~scim2_models.ScimFilter.match` uses the universal
    reading: ``emails.type ne "work"`` holds when *no* email is of type work. That agrees with
    ``not (emails.type eq "work")``.

Substring operators
    ``co``, ``sw`` and ``ew`` match a fragment rather than a whole value, so
    :func:`~scim2_models.path.coerce_value` leaves their operand as it is instead of converting
    it to the type of the attribute. The bound filter accepts ``emails[value co "example"]``
    even though ``"example"`` is not a valid email address on its own.

Filtering on ``schemas``
    §3.4.2.2 lets a client query by schema extension with ``schemas eq "urn:…"``. A filter reads
    the attribute as it stands, and :attr:`schemas <scim2_models.ScimObject.schemas>` holds what
    a peer asserted, not what the model declares. A resource parsed from a payload listing its
    extensions matches. One built in Python does not, since its extension URNs only appear on
    serialization. Filter the serialized form when you expect clients to query that way.

Comparing against ``null``
    ``null`` is a ``compValue`` the ABNF allows, but §3.4.2.2 does not say what comparing an
    attribute to it means. ``attr eq null`` holds when the attribute is unassigned, and
    ``attr ne null`` when it is assigned, so each is the negation of the other. An ordering
    operator against ``null`` never matches.

Comparing values of different types
    ``meta.lastModified co "2024"`` compares a string with an instant. Raising would make a
    filter over a heterogeneous collection unusable, so the comparison does not match instead.
    A naive :class:`~datetime.datetime`, read from a store that drops offsets, is incomparable
    with the aware one a filter carries in the same way: an ordering filter on it quietly
    matches nothing. Make attributes typed ``dateTime`` timezone-aware before filtering them.
    The :doc:`guides/sqlalchemy` guide shows where.

Case-insensitive comparison
    §3.4.2.2 defers to ``caseExact`` without saying how case is folded.
    :meth:`~scim2_models.ScimFilter.match` applies Unicode case folding, on strings normalised
    to Normalization Form C (NFC), so ``title eq "STRASSE"`` matches ``"Straße"``. A transpiler
    emitting SQL ``LOWER()`` folds ASCII only, and departs from ``match`` on such a value.

Coercion of comparison values
    :func:`~scim2_models.path.coerce_value` reads a comparison value as JSON, then converts it
    to the type of the attribute. The conversion is the tolerant one of pydantic, so it reads
    ``active eq "yes"`` and ``active eq 1`` as ``active eq true`` instead of rejecting them as
    ``invalidFilter``. This tolerance makes the ``roles[primary eq "True"]`` that Microsoft
    Entra ID emits usable.

Beyond the errata, three tolerances make filters from real deployments usable. The parser
accepts irregular spacing around operators. It reads keywords in any case, as in ``AND`` or
``Eq``. And it accepts ``attrName[value eq "…"]``, the notation implementations use to address
the values of a multi-valued attribute that is not complex.
