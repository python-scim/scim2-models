Comparing values
================

A service compares attribute values when it evaluates a filter, sorts results, checks
uniqueness, or looks for a value a PATCH operation adds or removes. This page explains how
scim2-models compares strings, and why a policy decides it.

What the specifications require
-------------------------------

:rfc:`RFC7644 §3.4.2.2 <7644#section-3.4.2.2>` lets the ``caseExact`` characteristic decide
whether a comparison ignores case. :rfc:`RFC7644 §7.8 <7644#section-7.8>` asks for strings to be
"appropriately prepared" before comparison, and points to :rfc:`RFC7644 §5 <7644#section-5>`. That
section only covers ``userName`` and ``password``: a service provider must apply the PRECIS rules
of :rfc:`7613`, since replaced by :rfc:`8265`.

The specifications leave the rest open. They do not say which PRECIS profile applies to
``userName``, nor how to prepare other attributes. The SCIM working group never settled these
questions.

What scim2-models does by default
---------------------------------

:func:`~scim2_models.default_comparison_key` normalizes every string to Normalization Form C
(NFC), and maps it to lowercase unless the attribute is ``caseExact``. A composed and a decomposed
``José`` are then the same value, and so are ``BJensen`` and ``bjensen``.

This is the ``UsernameCaseMapped`` profile of :rfc:`8265`, without two of its rules:

- **Width mapping.** PRECIS reads ``ＢＪＥＮＳＥＮ`` as ``bjensen``. The default does not.
- **Refused strings.** PRECIS refuses usernames holding spaces, symbols or compatibility
  characters such as ``ﬁ``. The default refuses nothing.

As under PRECIS, ``Straße`` and ``STRASSE`` stay distinct.

Why the default is not PRECIS
-----------------------------

Every other setting of a :class:`~scim2_models.ScimPolicy` defaults to the strict reading of the
specifications. :attr:`~scim2_models.ScimPolicy.comparison_key` does not, for four reasons:

- **No other implementation applies PRECIS.** The open-source SCIM servers and the major identity
  providers map case one character at a time, or leave the comparison to their database. None of
  them normalizes strings.
- **No database applies PRECIS.** PostgreSQL, MySQL, MariaDB and SQLite have no PRECIS function,
  so a storage that compares in SQL could not reproduce it.
- **PRECIS refuses common values.** A username such as ``Barbara Jensen`` would be rejected.
- **PRECIS needs a library.** scim2-models would have to depend on one.

:doc:`../how-to/compare-values` shows how to apply PRECIS when a service needs it.

Why a policy decides it
-----------------------

The comparison is a choice of the service provider, and nothing on the wire announces it. A
schema only carries ``caseExact``, and a service that loads its schemas from JSON has no other
place to describe its choice. A policy holds such local choices, and one function covers every
attribute: it receives the attribute, with its URN and its ``caseExact`` characteristic.

The same function serves filters, sorting, uniqueness checks and PATCH operations. A service that
compares with it agrees with itself: a value a filter finds is a value a uniqueness check
refuses to duplicate.

A string the key cannot prepare
-------------------------------

A key may refuse a string, as PRECIS does, by raising :exc:`ValueError`. Such a string has no
comparison form:

- **It is equal to no other value.** ``eq``, ``co``, ``sw``, ``ew`` and the ordering operators do
  not match it, and ``ne`` does. ``not`` negates as usual.
- **It sorts as a missing value.**
- **A request cannot write it.** Creation and replacement requests are refused with
  ``invalidValue``, and so are PATCH operations that write it. A response holding it is still
  read, so that a client can read the values a service already holds.

What a storage keeps in sync
----------------------------

A :doc:`storage <scim2_server:explanation/storage>` that compares in a database, rather than in
Python, has to reproduce the key. SQL
functions such as ``lower()`` only approach the default: SQLite lowercases ASCII letters only, and
no database but PostgreSQL normalizes Unicode. A storage that saves the string returned by the key
next to each value must compute it again when the key changes. :doc:`../how-to/compare-values`
shows what such a change does to the stored values.
