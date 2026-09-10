PATCH semantics and interoperability
====================================

A PATCH request changes a stored resource through ordered operations, and the SCIM protocol
splits the checks it needs in two: some need only the request, others need the resource as it
stands. This page answers what each operation does, what a path selects, what happens when that
selection matches nothing, and which error a rejected path answers. It is written for anyone
implementing PATCH on a server, or explaining to a client why an operation was refused.
:doc:`../how-to/validate-and-serialize` covers the request-processing sequence itself.

Validation and application
--------------------------

Validating a PATCH message in :attr:`~scim2_models.Context.RESOURCE_PATCH_REQUEST` rejects what
the message alone settles: a missing operation value, a ``remove`` without a path, a read-only
target, and an operation that would unassign a required attribute.

:meth:`~scim2_models.PatchOp.patch` then applies the message to the stored resource. Operations
run in their listed order. This is where an immutable value can be compared with the value it
replaces, and where the method reports whether any operation changed the resource. Splitting the
two keeps a parsed :class:`~scim2_models.PatchOp` useful before the resource is loaded.

Operation outcomes
------------------

``add`` appends a value to a multi-valued attribute rather than replacing its list. ``replace``
replaces its target, creating an unassigned single-valued complex parent when necessary.
``remove`` removes a selected list entry or unassigns the targeted attribute.

What a path selects
-------------------

:attr:`PatchOperation.path <scim2_models.PatchOperation.path>` follows a grammar of its own,
:rfc:`RFC7644 §3.5.2 <7644#section-3.5.2>`, where a filter between brackets selects which entries
of a multi-valued attribute an operation applies to:

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
----------------------------

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

For ``remove``, :rfc:`RFC7644 §3.5.2.2 <7644#section-3.5.2.2>` asks for the opposite. Its removal
example states that "if the user was not a member of this group, no changes should be made to the
resource, and a success response should be returned". The operation is a no-op, and reports that
nothing changed:

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

``add`` behaves the same way. :rfc:`RFC7644 §3.5.2.1 <7644#section-3.5.2.1>` does not say what a
selection matching nothing means for it, so the operation is a no-op and not a failure.
`Errata 8097 <https://errata.rfc-editor.org/eid8097/>`_ asks the RFC to say whether ``add``
accepts a value selection at all, since implementations differ on it.

.. note::

   Microsoft Entra ID sends ``add`` operations whose selection matches nothing, and expects the
   selected entry to be created. scim2-models does not create it, so an integration serving that
   client handles the case before applying the operation.

Primary values
--------------

When an operation makes one entry of a multi-valued complex attribute ``primary: true``,
scim2-models sets ``primary`` to ``false`` on the other entries. It rejects an operation that
would introduce more than one new primary entry, and a resource that already holds several
primary entries without saying which one stays primary.

Rejected paths
--------------

Which ``scimType`` a rejected path answers follows Table 9 of
:rfc:`RFC7644 §3.12 <7644#section-3.12>`. ``invalidPath`` covers "the ``path`` attribute was
invalid or malformed (see Figure 7)". It answers a path the grammar refuses, and an attribute the
model does not declare. Table 9 lists ``invalidFilter`` as applying to a "PATCH (Path Filter)",
so it answers what goes wrong between the brackets. That covers an unknown sub-attribute, a
comparison the attribute cannot take, and a selection over an attribute holding a single value.

To inspect or change a resource directly with the same path syntax, outside a PATCH request, use
:doc:`../how-to/access-resource-values`.
