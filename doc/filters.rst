Advanced filters
----------------

This page picks up where the :ref:`Filters <tutorial-filters>` section of the tutorial leaves
off: building filter expressions without writing SCIM syntax, turning one into a backend query,
and the errata the implemented grammar follows.

The examples below carry on from that section:

.. doctest::

    >>> from scim2_models import ScimFilter, User

    >>> user = User(
    ...     user_name="bjensen",
    ...     emails=[{"type": "work", "value": "bjensen@example.com"}],
    ... )

Building a filter
=================

Expressions compose with the Python boolean operators, and render back to valid SCIM syntax,
parentheses included:

.. doctest::

    >>> from scim2_models.filters import AttrPath, Comparison, CompareOperator, Present

    >>> work = Comparison(AttrPath("userName"), CompareOperator.eq, "bjensen")
    >>> titled = Present(AttrPath("title"))
    >>> print(work & titled)
    userName eq "bjensen" and title pr
    >>> print(~work | titled)
    not (userName eq "bjensen") or title pr

    >>> ScimFilter[User](work & titled).match(user)
    False

Composing is also what keeps a value from being read as syntax. A filter assembled by string
formatting takes whatever the value contains, quotes included:

.. doctest::

    >>> untrusted = 'x" or userName pr or userName eq "y'
    >>> forged = ScimFilter[User]('userName eq "%s"' % untrusted)
    >>> forged.match(user)
    True

The one comparison the caller wrote became three, and the filter now matches every user that
has a ``userName`` at all. A :class:`~scim2_models.filters.Comparison` renders its value as a
single JSON string, so it stays a value:

.. doctest::

    >>> escaped = Comparison(AttrPath("userName"), CompareOperator.eq, untrusted)
    >>> print(escaped)
    userName eq "x\" or userName pr or userName eq \"y"
    >>> ScimFilter[User](escaped).match(user)
    False

The same nodes make up a PATCH path, which :rfc:`RFC7644 §3.5.2 <7644#section-3.5.2>` builds on
the filter grammar with a sub-attribute allowed past the selection.
:attr:`Path.ast <scim2_models.Path.ast>` exposes the parsed path and
:attr:`~scim2_models.Path.value_filter` the filter between its brackets; see
:ref:`patch-value-selection`.

.. _filter-transpiling:

Writing a query
===============

scim2-models ships no SQL, but it gives you what is needed to emit a query yourself.
:attr:`ScimFilter.ast <scim2_models.ScimFilter.ast>` is the parsed tree, and
:class:`~scim2_models.filters.FilterVisitor` walks it with one method per node type.

A filter reaching a server comes from the network, so it is checked before it is turned into a
query: its syntax when it is created, and the attributes it names as soon as it is bound to a
model, which :class:`~scim2_models.SearchRequest`\ [:class:`~scim2_models.User`] does for a
query parameter. What follows assumes a filter that passed both, which is what lets a
transpiler resolve a path without handling an unknown attribute at every node.

A node only carries attribute *names*, so a transpiler resolves each one against the model
before emitting anything: :meth:`ScimFilter.resolve_comparison <scim2_models.ScimFilter.resolve_comparison>` for a
comparison, :meth:`ScimFilter.resolve <scim2_models.ScimFilter.resolve>` for a presence test or a value
selection. What comes back says which column to read, whether a join is needed, and whether
the comparison ignores case.

The transpiler below targets SQLite, so that this page can run it rather than claim it works.
It assumes the storage most SCIM servers end up with: one column per simple attribute, prefixed
columns for a complex one such as ``meta_last_modified``, and one table per multi-valued
attribute, keyed on the resource holding it.

.. doctest::

    >>> import sqlite3
    >>> from datetime import datetime
    >>> from enum import Enum

    >>> from scim2_models import Attribute
    >>> from scim2_models.filters import FilterVisitor, LogicalOperator, coerce_value
    >>> from scim2_models.filters import STRING_OPERATORS

    >>> SQL_OPERATORS = {
    ...     CompareOperator.eq: "=",
    ...     CompareOperator.ne: "<>",
    ...     CompareOperator.gt: ">",
    ...     CompareOperator.ge: ">=",
    ...     CompareOperator.lt: "<",
    ...     CompareOperator.le: "<=",
    ...     CompareOperator.co: "LIKE",
    ...     CompareOperator.sw: "LIKE",
    ...     CompareOperator.ew: "LIKE",
    ... }

    >>> LIKE_PATTERNS = {
    ...     CompareOperator.co: "%{}%",
    ...     CompareOperator.sw: "{}%",
    ...     CompareOperator.ew: "%{}",
    ... }

    >>> class SqlVisitor(FilterVisitor[str]):
    ...     def __init__(self, scim_filter, params=None, scope=None):
    ...         self.filter = scim_filter
    ...         self.params = [] if params is None else params
    ...         self.scope = scope
    ...
    ...     def path(self, attr_path):
    ...         """Qualify a path with the attribute a value selection scopes it to."""
    ...         if self.scope is None:
    ...             return attr_path
    ...         return AttrPath(self.scope, attr_path.attr)
    ...
    ...     def column(self, resolved):
    ...         """A multi-valued attribute has its own table, a complex one its own columns."""
    ...         if not resolved.sub_field_name:
    ...             return resolved.field_name
    ...         if resolved.is_multivalued:
    ...             return f"{resolved.field_name}.{resolved.sub_field_name}"
    ...         return f"{resolved.field_name}_{resolved.sub_field_name}"
    ...
    ...     def casefolded(self, resolved):
    ...         """Only a string has a case, and only some strings ignore it."""
    ...         scim_type = Attribute.Type.from_python(resolved.target_type)
    ...         return scim_type == Attribute.Type.string and not resolved.case_exact
    ...
    ...     def bind(self, resolved, node):
    ...         """Collect a comparison value, and return the placeholder standing for it."""
    ...         value = coerce_value(resolved, node.value, node.op)
    ...         if isinstance(value, Enum):
    ...             value = str(value)
    ...         elif isinstance(value, datetime):
    ...             value = value.isoformat()
    ...         if node.op in STRING_OPERATORS:
    ...             for char in ("\\", "%", "_"):
    ...                 value = value.replace(char, "\\" + char)
    ...             value = LIKE_PATTERNS[node.op].format(value)
    ...         self.params.append(value)
    ...         return "?"
    ...
    ...     def join(self, resolved, condition=None, negated=False):
    ...         """Correlate a condition with the table the entries live in."""
    ...         if self.scope is not None or not resolved.is_multivalued:
    ...             return condition
    ...         table = resolved.field_name
    ...         where = f"{table}.parent_id = resource.id"
    ...         if condition:
    ...             where += f" AND {condition}"
    ...         exists = "NOT EXISTS" if negated else "EXISTS"
    ...         return f"{exists} (SELECT 1 FROM {table} WHERE {where})"
    ...
    ...     def visit_comparison(self, node):
    ...         resolved = self.filter.resolve_comparison(self.path(node.attr_path))
    ...         negated = (
    ...             node.op == CompareOperator.ne
    ...             and resolved.is_multivalued
    ...             and self.scope is None
    ...         )
    ...         op = CompareOperator.eq if negated else node.op
    ...         column, value = self.column(resolved), self.bind(resolved, node)
    ...         if self.casefolded(resolved):
    ...             column, value = f"LOWER({column})", f"LOWER({value})"
    ...         condition = f"{column} {SQL_OPERATORS[op]} {value}"
    ...         if op in STRING_OPERATORS:
    ...             condition += " ESCAPE '\\'"
    ...         if op == CompareOperator.ne:
    ...             condition = f"({self.column(resolved)} IS NULL OR {condition})"
    ...         return self.join(resolved, condition, negated=negated)
    ...
    ...     def visit_present(self, node):
    ...         resolved = self.filter.resolve(self.path(node.attr_path))
    ...         if resolved.is_multivalued and not resolved.sub_field_name:
    ...             return self.join(resolved)
    ...         return self.join(resolved, f"{self.column(resolved)} IS NOT NULL")
    ...
    ...     def visit_not(self, node):
    ...         return f"NOT ({self.visit(node.expr)})"
    ...
    ...     def visit_logical_expr(self, node):
    ...         joiner = " AND " if node.op == LogicalOperator.and_ else " OR "
    ...         return "(" + joiner.join(self.visit(term) for term in node.terms) + ")"
    ...
    ...     def visit_value_path(self, node):
    ...         resolved = self.filter.resolve(node.attr_path)
    ...         scoped = SqlVisitor(self.filter, self.params, scope=node.attr_path.attr)
    ...         return self.join(resolved, scoped.visit(node.val_filter))

Running it
^^^^^^^^^^

One SQLite trait matters here: ``LIKE`` ignores case on ASCII unless
``PRAGMA case_sensitive_like`` is on. Left alone, it would make every substring comparison
case-insensitive, including the ones :rfc:`7643` requires to be exact.

.. doctest::

    >>> SCHEMA = """PRAGMA case_sensitive_like = ON;
    ...     CREATE TABLE resource (id TEXT, user_name TEXT, title TEXT, active INTEGER,
    ...                            meta_last_modified TEXT);
    ...     CREATE TABLE emails (parent_id TEXT, type TEXT, value TEXT);
    ...     CREATE TABLE groups (parent_id TEXT, value TEXT);
    ... """

    >>> users = [
    ...     User(id="1", user_name="bjensen", title="Manager", active=True,
    ...          emails=[{"type": "work", "value": "bjensen@example.com"}],
    ...          groups=[{"value": "2819c223-7f76"}],
    ...          meta={"resource_type": "User", "last_modified": "2024-06-01T10:00:00Z"}),
    ...     User(id="2", user_name="RSanchez", active=False,
    ...          emails=[{"type": "home", "value": "rick@example.org"}],
    ...          groups=[{"value": "2819C223-7F76"}],
    ...          meta={"resource_type": "User", "last_modified": "2023-01-15T08:30:00Z"}),
    ...     User(id="3", user_name="jsmith", title="Engineer", active=True,
    ...          emails=[{"type": "work", "value": "j.smith@example.com"}],
    ...          meta={"resource_type": "User", "last_modified": "2025-03-20T12:00:00Z"}),
    ...     User(id="4", user_name="dpotter", title="100% remote", active=True,
    ...          meta={"resource_type": "User", "last_modified": "2025-01-01T00:00:00Z"}),
    ...     User(id="5", user_name="mgarcia", title="1000 Files", active=True,
    ...          meta={"resource_type": "User", "last_modified": "2025-02-01T00:00:00Z"}),
    ... ]

    >>> def store(users):
    ...     """Spread SCIM resources over the tables the transpiler expects."""
    ...     db = sqlite3.connect(":memory:")
    ...     db.executescript(SCHEMA)
    ...     for user in users:
    ...         db.execute("INSERT INTO resource VALUES (?, ?, ?, ?, ?)",
    ...                    (user.id, user.user_name, user.title, user.active,
    ...                     user.meta.last_modified.isoformat()))
    ...         for email in user.emails or []:
    ...             db.execute("INSERT INTO emails VALUES (?, ?, ?)",
    ...                        (user.id, str(email.type), email.value))
    ...         for group in user.groups or []:
    ...             db.execute("INSERT INTO groups VALUES (?, ?)", (user.id, group.value))
    ...     return db

    >>> def to_sql(scim_filter):
    ...     """Return the ``WHERE`` clause of a filter, and the values it binds."""
    ...     visitor = SqlVisitor(scim_filter)
    ...     return visitor.visit(scim_filter.ast), visitor.params

    >>> def matching_ids(db, scim_filter):
    ...     where, params = to_sql(scim_filter)
    ...     rows = db.execute(f"SELECT id FROM resource WHERE {where}", params)
    ...     return sorted(row[0] for row in rows)

    >>> db = store(users)

A comparison on a simple attribute reads a column, a presence test tests it for ``NULL``:

.. doctest::

    >>> scim_filter = ScimFilter[User]('userName eq "bjensen" and title pr')
    >>> where, params = to_sql(scim_filter)
    >>> print(where)
    (LOWER(user_name) = LOWER(?) AND title IS NOT NULL)
    >>> params
    ['bjensen']
    >>> matching_ids(db, scim_filter)
    ['1']

A multi-valued attribute is reached through a correlated subquery, and a value selection puts
its whole filter inside that one subquery:

.. doctest::

    >>> scim_filter = ScimFilter[User]('emails[type eq "work" and value ew "@example.com"]')
    >>> where, params = to_sql(scim_filter)
    >>> print(where)  # doctest: +NORMALIZE_WHITESPACE
    EXISTS (SELECT 1 FROM emails WHERE emails.parent_id = resource.id
            AND (LOWER(emails.type) = LOWER(?) AND LOWER(emails.value) LIKE LOWER(?) ESCAPE '\'))
    >>> params
    ['work', '%@example.com']
    >>> matching_ids(db, scim_filter)
    ['1', '3']

``groups`` is a multi-valued complex attribute compared without a sub-attribute, so the
comparison lands on ``groups.value``, which is case-exact where ``groups`` itself is not:
it holds a resource ``id``, and :rfc:`RFC7643 §3.1 <7643#section-3.1>` makes those case-exact,
which is the reading `erratum 8472 <https://www.rfc-editor.org/errata/eid8472>`_ applies to
``manager.value``. The two casings select different resources:

.. doctest::

    >>> scim_filter = ScimFilter[User]('groups co "2819c223"')
    >>> where, params = to_sql(scim_filter)
    >>> print(where)  # doctest: +NORMALIZE_WHITESPACE
    EXISTS (SELECT 1 FROM groups WHERE groups.parent_id = resource.id
            AND groups.value LIKE ? ESCAPE '\')
    >>> matching_ids(db, scim_filter)
    ['1']
    >>> matching_ids(db, ScimFilter[User]('groups co "2819C223"'))
    ['2']

``ne`` is the one operator that does not read as its SQL counterpart. It holds when *no* value
matches, a reading :ref:`filter-deviations` comes back to, so a multi-valued attribute negates
the whole subquery rather than comparing inside it:

.. doctest::

    >>> print(to_sql(ScimFilter[User]('emails.type ne "work"'))[0])  # doctest: +NORMALIZE_WHITESPACE
    NOT EXISTS (SELECT 1 FROM emails WHERE emails.parent_id = resource.id
                AND LOWER(emails.type) = LOWER(?))
    >>> matching_ids(db, ScimFilter[User]('emails.type ne "work"'))
    ['2', '4', '5']

A selection scopes it back to a single entry, where the existential reading is the right one:

.. doctest::

    >>> matching_ids(db, ScimFilter[User]('emails[type ne "work"]'))
    ['2']

Checking it against the evaluator
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

:meth:`ScimFilter.match <scim2_models.ScimFilter.match>` walks the same tree through the same resolution, on
Python objects instead of on a database. It answers the question the query is meant to answer,
which makes it the reference a transpiler is tested against. The two agree over ASCII; past it,
the Unicode case folding of the evaluator and the ``LOWER()`` of the database part ways, as
:ref:`filter-deviations` describes:

.. doctest::

    >>> EXPRESSIONS = [
    ...     'userName eq "bjensen"',
    ...     'userName eq "BJENSEN"',
    ...     'userName sw "b" and title pr',
    ...     'emails[type eq "work" and value ew "@example.com"]',
    ...     'emails.value co "example"',
    ...     'groups co "2819c223"',
    ...     'groups co "2819C223"',
    ...     "active eq true",
    ...     'meta.lastModified gt "2024-01-01T00:00:00Z"',
    ...     "not (title pr)",
    ...     "emails pr",
    ...     "not (emails pr)",
    ...     'userName eq "bjensen" or title eq "Engineer"',
    ...     'emails[type eq "home"] and active eq false',
    ...     'title co "100%"',
    ...     'title ne "Manager"',
    ...     'emails.type ne "work"',
    ...     'emails[type ne "work"]',
    ... ]

    >>> for expression in EXPRESSIONS:
    ...     scim_filter = ScimFilter[User](expression)
    ...     evaluated = sorted(user.id for user in users if scim_filter.match(user))
    ...     assert matching_ids(db, scim_filter) == evaluated, expression

    >>> db.close()

This is not a formality. Without the ``ESCAPE`` clause, ``title co "100%"`` also selects
``"1000 Files"``, since ``%`` is a wildcard of ``LIKE`` and not a character to look for. Without
the ``IS NULL`` guard, ``title ne "Manager"`` drops every resource that has no title at all,
since SQL discards a ``NULL`` where a missing attribute is simply not equal. Both read as
correct SQL, and both answer a different question than the filter asked.

The example stops at the ``WHERE`` clause. Sorting is the other half of a query, and
:attr:`SearchRequest.sort_by <scim2_models.SearchRequest.sort_by>` needs the same resolution:
it is a :class:`~scim2_models.Path`, and the attribute it resolves to names the column an
``ORDER BY`` sorts on. Naming that column is not the whole of it, since the case, the missing
values and the multi-valued attributes each have a rule of their own in
:rfc:`RFC7644 §3.4.2.3 <7644#section-3.4.2.3>`, which the :doc:`guides/sqlalchemy` guide takes
from there.

.. _filter-deviations:

Deviations from the published RFC
=================================

The ABNF published in :rfc:`7644` is defective on several points, and the grammar
implemented here is the one it becomes once the relevant errata are applied.
The table gives the status each erratum had when it was applied, since none of those
correcting the grammar is verified yet: an erratum still *reported* may be rejected
rather than folded into a future revision.

.. list-table::
   :header-rows: 1
   :widths: 10 20 70

   * - Errata
     - Status
     - Correction
   * - `4670 <https://www.rfc-editor.org/errata/eid4670>`_
     - Held for document update
     - The published order of precedence is reversed. Attribute operators bind tighter than
       logical ones, which rank ``not`` over ``and`` over ``or``.
   * - `4690 <https://www.rfc-editor.org/errata/eid4690>`_,
       `7322 <https://www.rfc-editor.org/errata/eid7322>`_
     - Held for document update, reported
     - ``valFilter`` reaches ``valuePath`` through ``logExp``, which would make
       ``emails[type eq "work" and emails[type eq "home"]]`` legal. 4690 closes the recursion
       by reducing the brackets to a single ``attrExp`` pair, which also rejects the
       parentheses and the three-term expressions implementations use; 7322 restores them.
       The grammar follows 7322: brackets accept a full boolean expression but never a nested
       value selection.
   * - `7319 <https://www.rfc-editor.org/errata/eid7319>`_
     - Reported
     - The grammar forbids a space between ``not`` and its parenthesis, which the examples of
       the RFC itself use. Both ``not (x pr)`` and ``not(x pr)`` are accepted.
   * - `7122 <https://www.rfc-editor.org/errata/eid7122>`_
     - Held for document update
     - The ``PATH`` rule of a PATCH operation lacks ``attrExp``, the only way to target a value
       of a multi-valued attribute that is not complex, such as ``schemas eq "urn:…"``.
   * - `8924 <https://www.rfc-editor.org/errata/eid8924>`_
     - Reported
     - ``ATTRNAME`` excludes ``$ref`` although RFC 7643 uses it. A leading ``$`` is accepted.
   * - `6001 <https://www.rfc-editor.org/errata/eid6001>`_,
       `8472 <https://www.rfc-editor.org/errata/eid8472>`_
     - Held for document update, verified
     - Reference attributes are declared ``caseExact: false`` while §2.3.7 requires them to be
       case-exact. ``profileUrl``, ``groups.value``, ``groups.$ref``, ``members.value``,
       ``members.$ref`` and ``manager.$ref`` are annotated
       :attr:`CaseExact.true <scim2_models.CaseExact.true>`, which :meth:`~scim2_models.Resource.to_schema`
       reflects.

The grammar is also stricter than the published ABNF on three points, none of which a
real deployment has been observed to need:

Schema URIs
    §3.4.2.2 defines ``URI`` per :rfc:`Appendix A of RFC3986 <3986#appendix-A>`, which any
    scheme satisfies. Only URNs are accepted, since every schema URI the SCIM specifications
    define is one.

``$`` in an attribute name
    :rfc:`RFC7643 §2.1 <7643#section-2.1>` puts ``$`` in ``nameChar``, so ``foo$bar`` is a
    legal name. Only a leading ``$`` is accepted, which is what errata 8924 asks for and what
    ``$ref`` needs.

Numbers out of range
    A literal such as ``1e400`` reads as an infinity, for which the ABNF has no syntax, so it
    could not be rendered back into a filter. It is rejected rather than parsed.

Six further choices are not settled by the RFC:

``ne`` on a multi-valued attribute
    §3.4.2.2 states that a filter matches "if any of the values" matches, without saying what
    that means for a negation. The universal reading is used, so ``emails.type ne "work"``
    holds when *no* email is of type work, which agrees with ``not (emails.type eq "work")``.

Substring operators
    ``co``, ``sw`` and ``ew`` match a fragment rather than a whole value, so their operand is
    not coerced to the type of the attribute. ``emails[value co "example"]`` is accepted even
    though ``"example"`` is not a valid email address on its own.

Filtering on ``schemas``
    §3.4.2.2 lets a client query by schema extension with ``schemas eq "urn:…"``. A filter reads
    the attribute as it stands, and :attr:`schemas <scim2_models.ScimObject.schemas>` holds what
    a peer asserted rather than what the model declares: a resource parsed from a payload
    listing its extensions matches, one built in Python does not, since its extension URNs only
    appear on serialization. Filter the serialized form when a client is expected to query that
    way.

Comparing against ``null``
    ``null`` is a ``compValue`` the ABNF allows, but §3.4.2.2 does not say what comparing an
    attribute to it means. ``attr eq null`` holds when the attribute is unassigned and
    ``attr ne null`` when it is assigned, which makes them the negation of each other. An
    ordering operator against ``null`` never matches.

Comparing values of different types
    ``meta.lastModified co "2024"`` compares a string with an instant. Rather than raising,
    which would make a filter over a heterogeneous collection unusable, the comparison does not
    match. A naive :class:`~datetime.datetime` read from a store that drops offsets is
    incomparable with the aware one a filter carries in the same way, so an ordering filter on
    it quietly matches nothing. Attributes typed ``dateTime`` should be made timezone-aware
    before they are filtered, as :doc:`guides/sqlalchemy` does.

Case-insensitive comparison
    §3.4.2.2 defers to ``caseExact`` without saying how case is folded. Unicode case folding is
    applied, on strings normalised to NFC, so ``title eq "STRASSE"`` matches ``"Straße"``.
    A transpiler emitting SQL ``LOWER()`` will not reproduce that, which is why the equivalence
    checked below holds over ASCII rather than in general.

Coercion of comparison values
    A comparison value is read as JSON, then coerced to the type of the attribute. The coercion
    is the tolerant one of pydantic, so ``active eq "yes"`` and ``active eq 1`` are read as
    ``active eq true`` instead of being rejected as ``invalidFilter``. This is what makes the
    ``roles[primary eq "True"]`` that Microsoft Entra ID emits usable.

Beyond the errata, a few tolerances make filters received from real deployments usable:
irregular spacing around operators, keywords in any case (``AND``, ``Eq``), and the
``attrName[value eq "…"]`` notation that implementations conventionally use to address values
of a multi-valued attribute that is not complex.
