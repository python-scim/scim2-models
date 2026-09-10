Patch paths
-----------

This page picks up where the :ref:`Patch operations <tutorial-patch>` section of the tutorial
leaves off, and assumes you have read it. It covers what a path can select, what happens when it
selects nothing, which error a rejected path answers, and how to use a path outside a PATCH
request. What an operation does to a whole attribute stays in the tutorial.

Selecting values
================

:attr:`PatchOperation.path <scim2_models.PatchOperation.path>` follows a grammar of its own,
:rfc:`RFC7644 §3.5.2 <7644#section-3.5.2>`, where a filter between brackets selects which
entries of a multi-valued attribute an operation applies to:

.. doctest::

    >>> from scim2_models import PatchOp, PatchOperation, User

    >>> user = User(
    ...     user_name="bjensen",
    ...     emails=[
    ...         {"type": "work", "value": "work@example.com"},
    ...         {"type": "home", "value": "home@example.com"},
    ...     ],
    ... )

    >>> patch = PatchOp[User](
    ...     operations=[
    ...         PatchOperation(
    ...             op=PatchOperation.Op.replace_,
    ...             path='emails[type eq "work"].value',
    ...             value="new@example.com",
    ...         )
    ...     ]
    ... )
    >>> patch.patch(user)
    True
    >>> [email.value for email in user.emails]
    ['new@example.com', 'home@example.com']

A selection matching nothing
============================

What a selection matching nothing means depends on the operation. For ``replace``,
:rfc:`RFC7644 §3.5.2.3 <7644#section-3.5.2.3>` requires a ``noTarget`` failure, which
:class:`~scim2_models.NoTargetException` carries:

.. doctest::

    >>> patch = PatchOp[User](
    ...     operations=[
    ...         PatchOperation(
    ...             op=PatchOperation.Op.replace_,
    ...             path='emails[type eq "other"].value',
    ...             value="other@example.com",
    ...         )
    ...     ]
    ... )
    >>> patch.patch(user)
    Traceback (most recent call last):
        ...
    scim2_models.exceptions.NoTargetException: no value of 'emails' matches the path filter

For ``remove``, :rfc:`RFC7644 §3.5.2.2 <7644#section-3.5.2.2>` asks for the opposite. Its
removal example states that "if the user was not a member of this group, no changes should be
made to the resource, and a success response should be returned". The operation is a no-op, and
reports that nothing changed:

.. doctest::

    >>> patch = PatchOp[User](
    ...     operations=[
    ...         PatchOperation(
    ...             op=PatchOperation.Op.remove, path='emails[type eq "other"]'
    ...         )
    ...     ]
    ... )
    >>> patch.patch(user)
    False

``add`` behaves the same way. :rfc:`RFC7644 §3.5.2.1 <7644#section-3.5.2.1>` does not say what
a selection matching nothing means for it, so the operation is a no-op and not a failure.
`Errata 8097 <https://www.rfc-editor.org/errata/eid8097>`_ asks the RFC to say whether ``add``
accepts a value selection at all, since implementations differ on it.

.. note::

   Microsoft Entra ID sends ``add`` operations whose selection matches nothing, and expects the
   entry to be created. scim2-models does not create it.

Rejected paths
==============

Which ``scimType`` a rejected path answers follows Table 9 of
:rfc:`RFC7644 §3.12 <7644#section-3.12>`. ``invalidPath`` covers "the ``path`` attribute was
invalid or malformed (see Figure 7)". It answers a path the grammar refuses, and an attribute the
model does not declare. Table 9 lists ``invalidFilter`` as applying to a "PATCH (Path Filter)",
so it answers what goes wrong between the brackets. That covers an unknown sub-attribute, a
comparison the attribute cannot take, and a selection over an attribute holding a single value.

Paths outside PATCH
===================

The same selection is available on :class:`~scim2_models.Path` itself, through
:meth:`~scim2_models.Path.get`, :meth:`~scim2_models.Path.set` and
:meth:`~scim2_models.Path.delete`:

.. doctest::

    >>> from scim2_models import Path

    >>> Path[User]('emails[type eq "home"].value').get(user)
    ['home@example.com']

A multi-valued attribute that is not complex holds plain values with no sub-attribute to
compare. A path addresses those either with a bare comparison, which errata 7122 adds to the
grammar as :ref:`filter-deviations` explains, or with the ``value`` convention implementations
use:

.. doctest::

    >>> user = User(
    ...     user_name="bjensen",
    ...     schemas=["urn:ietf:params:scim:schemas:core:2.0:User", "urn:a:b:c"],
    ... )

    >>> Path[User]('schemas eq "urn:a:b:c"').delete(user)
    True
    >>> user.schemas
    ['urn:ietf:params:scim:schemas:core:2.0:User']

    >>> Path[User]('schemas[value eq "urn:ietf:params:scim:schemas:core:2.0:User"]').get(user)
    ['urn:ietf:params:scim:schemas:core:2.0:User']
