Filter deviations from the SCIM RFC
===================================

The filter grammar scim2-models implements is not the one
:rfc:`RFC7644 §3.4.2.2 <7644#section-3.4.2.2>` publishes. This page answers why: which errata it
applies, which forms it refuses although the ABNF allows them, which questions the specification
leaves to an implementation, and which irregular filters it accepts from deployed servers. Anyone
comparing scim2-models with another SCIM implementation, or tracking down a filter one accepts
and the other refuses, finds the differences here.

A filter is parsed when it is created, and binding it to a model resolves its attribute names and
checks which comparisons each attribute supports. A bound filter may still accept a name that
only some types in a resource union declare, because
:rfc:`RFC7644 §3.4.2.1 <7644#section-3.4.2.1>` requires that comparison to evaluate to false on
the remaining types. :doc:`../how-to/build-filters` covers building a filter from untrusted
values, and :doc:`../integrations/filter-transpiler` covers turning one into a database query.

.. _filter-errata:

Errata applied to the grammar
-----------------------------

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
   * - `4670 <https://errata.rfc-editor.org/eid4670/>`_
     - Held for document update
     - The published order of precedence is reversed. Attribute operators take precedence over
       logical ones, ``not`` over ``and``, and ``and`` over ``or``.
   * - `4690 <https://errata.rfc-editor.org/eid4690/>`_,
       `7322 <https://errata.rfc-editor.org/eid7322/>`_
     - Held for document update, reported
     - The published rule lets a value selection nest another one, as in
       ``emails[type eq "work" and emails[type eq "home"]]``. 4690 closes the recursion but also
       forbids the parentheses and the three-term expressions implementations write, and 7322,
       which the grammar follows, restores them.
   * - `7319 <https://errata.rfc-editor.org/eid7319/>`_
     - Reported
     - The grammar forbids a space between ``not`` and its parenthesis, which the examples of
       the RFC itself use. The parser accepts both ``not (x pr)`` and ``not(x pr)``.
   * - `7122 <https://errata.rfc-editor.org/eid7122/>`_
     - Held for document update
     - The ``PATH`` rule of a PATCH operation lacks ``attrExp``. It is the only way to target a
       value of a multi-valued attribute that is not complex, such as ``schemas eq "urn:…"``.
   * - `8924 <https://errata.rfc-editor.org/eid8924/>`_
     - Reported
     - ``ATTRNAME`` excludes ``$ref`` although RFC 7643 uses it. The parser accepts a leading
       ``$``.
   * - `6001 <https://errata.rfc-editor.org/eid6001/>`_,
       `8472 <https://errata.rfc-editor.org/eid8472/>`_
     - Held for document update, verified
     - Reference attributes are declared ``caseExact: false`` while §2.3.7 requires them to be
       case-exact. scim2-models annotates ``profileUrl``, ``groups.value``, ``groups.$ref``,
       ``members.value``, ``members.$ref`` and ``manager.$ref`` with
       :attr:`CaseExact.true <scim2_models.CaseExact.true>`, and
       :meth:`~scim2_models.Resource.to_schema` reflects it.

.. _filter-strictness:

Stricter than the published ABNF
--------------------------------

The grammar refuses five forms the published ABNF allows. No known deployment needs any of them:

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

.. _filter-open-choices:

Choices the RFC leaves open
---------------------------

Seven questions are left open by the specification, and an implementation has to answer each of
them:

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
    serialization. Filter the serialized form when clients are expected to query that way.

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
    The :doc:`../integrations/sqlalchemy` guide shows where.

Case-insensitive comparison
    §3.4.2.2 defers to ``caseExact`` without saying how case is folded.
    :meth:`~scim2_models.ScimFilter.match` applies Unicode case folding, on strings normalised
    to Normalization Form C (NFC), so ``title eq "STRASSE"`` matches ``"Straße"``. A transpiler
    emitting SQL ``LOWER()`` folds ASCII only, and departs from
    :meth:`~scim2_models.ScimFilter.match` on such a value.

Coercion of comparison values
    :func:`~scim2_models.path.coerce_value` reads a comparison value as JSON, then converts it
    to the type of the attribute. The conversion is the tolerant one of pydantic, so it reads
    ``active eq "yes"`` and ``active eq 1`` as ``active eq true`` instead of rejecting them as
    ``invalidFilter``. This tolerance makes the ``roles[primary eq "True"]`` that Microsoft
    Entra ID emits usable.

Tolerances for real deployments
-------------------------------

Three tolerances go the other way, and make filters from deployed servers usable. The parser
accepts irregular spacing around operators. It reads keywords in any case, as in ``AND`` or
``Eq``. And it accepts ``attrName[value eq "…"]``, the notation implementations use to address
the values of a multi-valued attribute that is not complex.
