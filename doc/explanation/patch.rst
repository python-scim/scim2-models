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
the message alone settles: a missing operation value, a ``remove`` without a path or carrying a
value, a path to a read-only attribute, and an operation that removes a required
attribute or sets it to an empty value.

:meth:`~scim2_models.PatchOp.patch` then applies the message to the stored resource. Operations
run in their listed order. This is where an immutable value can be compared with the value it
replaces, and where the method reports whether any operation changed the resource. It also
rejects an operation that unassigns a required attribute in another way, such as removing its
last entry through a filter. Read-only attributes in the value are checked there too. A client
that sends back the ``id`` or ``meta`` it read is accepted, since
:rfc:`RFC7643 §3.1 <7643#section-3.1>` says to ignore them. A client that changes them gets a
``mutability`` error. Splitting the two keeps a parsed :class:`~scim2_models.PatchOp` useful
before the resource is loaded.

Operation outcomes
------------------

``add`` appends a value to a multi-valued attribute rather than replacing its list. ``replace``
replaces the value of a simple or multi-valued target. ``remove`` removes a selected list entry
or unassigns the targeted attribute.

A path to a sub-attribute of an absent complex attribute, such as ``name.givenName`` on a user
without a name, creates that attribute.

A complex attribute is merged rather than replaced. ``add`` and ``replace`` set the
sub-attributes in their value and keep the others, as
:rfc:`RFC7644 §3.5.2.3 <7644#section-3.5.2.3>` requires:

.. doctest::

    >>> from scim2_models import PatchOp, PatchOperation, User

    >>> user = User(user_name="bjensen", name={"family_name": "Jensen", "given_name": "Barbara"})
    >>> patch = PatchOp[User](
    ...     operations=[
    ...         PatchOperation(
    ...             op=PatchOperation.Op.replace_, path="name", value={"givenName": "Babs"}
    ...         )
    ...     ]
    ... )
    >>> patch.patch(user)
    True
    >>> user.name.given_name, user.name.family_name
    ('Babs', 'Jensen')

Operations without a path
-------------------------

The value of an ``add`` or ``replace`` without a path holds the attributes to write. Each
attribute is handled like an operation with that attribute as its path. A key can also be an
attribute path, such as ``name.givenName`` or the full URN of an extension attribute. Microsoft
Entra ID and its SCIM Validator send such keys. :rfc:`RFC7643 §2.1 <7643#section-2.1>` forbids
dots and colons in attribute names, so such a key cannot be confused with a name:

.. doctest::

    >>> from scim2_models import EnterpriseUser, PatchOp, PatchOperation, User

    >>> user = User[EnterpriseUser](user_name="bjensen", name={"family_name": "Jensen"})
    >>> patch = PatchOp[User[EnterpriseUser]](
    ...     operations=[
    ...         PatchOperation(
    ...             op=PatchOperation.Op.replace_,
    ...             value={
    ...                 "name.givenName": "Barbara",
    ...                 "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:employeeNumber": "42",
    ...             },
    ...         )
    ...     ]
    ... )
    >>> patch.patch(user)
    True
    >>> user.name.given_name, user.name.family_name, user[EnterpriseUser].employee_number
    ('Barbara', 'Jensen', '42')

A key with a filter is not read as a path, and neither is a key that matches no declared
attribute. Both follow :attr:`ScimPolicy.unknown <scim2_models.ScimPolicy.unknown>`.

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

When a filter selects whole entries, ``add`` and ``replace`` merge their value into each selected
entry, as they do for a complex attribute. :rfc:`RFC7644 §3.5.2.3 <7644#section-3.5.2.3>` says
"all matching record values" are replaced, and keeps the sub-attributes the value does not
specify:

.. doctest::

    >>> patch = PatchOp[User](
    ...     operations=[
    ...         PatchOperation(
    ...             op=PatchOperation.Op.replace_,
    ...             path='emails[type eq "home"]',
    ...             value={"display": "Home"},
    ...         )
    ...     ]
    ... )
    >>> patch.patch(user)
    True
    >>> user.emails[1].type.value, user.emails[1].value, user.emails[1].display
    ('home', 'home@example.com', 'Home')

Each selected entry is updated in place, not replaced by a new one. So a client can change the
``display`` of a group member without repeating its immutable ``value``. A different ``value`` is
rejected with ``mutability``. To unassign a sub-attribute, give it a null value, or remove it with
a path such as ``emails[type eq "home"].display``.

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

``add`` fails like ``replace``. :rfc:`RFC7644 §3.5.2.1 <7644#section-3.5.2.1>` does not say what
a selection matching nothing means for it, and Table 9 of :rfc:`RFC7644 §3.12 <7644#section-3.12>`
defines ``noTarget`` for a filter that "yields no match". The filter selects the entries to
write. It does not describe an entry to create. So the operation fails instead of silently doing
nothing.

Implementations differ here. UnboundID's SCIM 2 SDK, Apache SCIMple and scim-patch create the
entry on ``add``. SCIM-SDK returns ``noTarget``, and so does WSO2 Charon unless the attribute is
unassigned. `Errata 8097 <https://errata.rfc-editor.org/eid8097/>`_ describes the creation
Microsoft Entra ID expects. It is held, with no corrected text. The editor of :rfc:`7644`
`replied <https://mailarchive.ietf.org/arch/msg/scim/kQ8B5YiYjDdGj8rX441FcsbOH4Q>`_ that
such an implementation is "going outside the spec at the cost of their interoperability".

Entra sends such operations to fill an attribute it has not set yet. It sends ``add`` by
default, and ``replace`` when its ``aadOptscim062020`` flag is set. For example, it targets
``emails[type eq "work"].value`` on a user without a work email, and expects a new entry
``{"type": "work", "value": ...}``.
:attr:`ScimPolicy.UnmatchedPathFilter.create <scim2_models.ScimPolicy.UnmatchedPathFilter.create>`
creates that entry for both operations. It only works with ``eq`` comparisons joined by ``and``.
The new entry must still match the filter after the value is written, so that later operations
with the same filter find it. See :doc:`../how-to/tolerate-a-nonconformant-peer`.

What a remove selects
---------------------

:rfc:`RFC7644 §3.5.2.2 <7644#section-3.5.2.2>` defines a ``remove`` by its ``path`` alone: the
four target locations it lists all read off ``path``, and a selection is spelled as a filter
there. No member of the operation carries the entries to remove. An operation whose ``value`` is
set is therefore incompatible with the schema of the attribute it targets, which
:rfc:`RFC7644 §3.5.2 <7644#section-3.5.2>` answers with an error:

.. doctest::

    >>> patch = PatchOp[User](
    ...     operations=[
    ...         PatchOperation(
    ...             op=PatchOperation.Op.remove,
    ...             path="emails",
    ...             value=[{"value": "work@example.com"}],
    ...         )
    ...     ]
    ... )
    >>> patch.patch(user)
    Traceback (most recent call last):
        ...
    scim2_models.exceptions.InvalidValueException: a remove operation carries no value, a filter in the path selects what to remove

Write the selection in the path instead, as ``emails[value eq "work@example.com"]``.

.. note::

   Microsoft Entra ID removes a group member with ``{"op": "Remove", "path": "members",
   "value": [{"value": "..."}]}``, which this rejects. Microsoft `documents that form as
   non-conformant
   <https://learn.microsoft.com/en-us/entra/identity/app-provisioning/application-provisioning-config-problem-scim-compatibility>`_
   and the ``aadOptscim062020`` flag, added to the tenant URL of the application, has Entra send
   a filter path. An application serving that client without the flag reads the ``value`` as a
   selection with
   :attr:`ScimPolicy.RemoveValue.apply <scim2_models.ScimPolicy.RemoveValue.apply>`; see
   :doc:`../how-to/tolerate-a-nonconformant-peer`.

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
model does not declare, unless :attr:`ScimPolicy.unknown <scim2_models.ScimPolicy.unknown>` drops
it. With ``ignore`` or ``keep``, an operation on an undeclared attribute changes
nothing. Table 9 lists ``invalidFilter`` as applying to a "PATCH (Path Filter)",
so it answers what goes wrong between the brackets. That covers an unknown sub-attribute, a
comparison the attribute cannot take, and a selection over an attribute holding a single value,
under any policy.

Building a patch rather than applying one
-----------------------------------------

An application holding both the state a peer has and the state it should have does not have to
spell the operations out. :meth:`~scim2_models.PatchOp.build_from` compares the two states and
builds them, restricted to the attributes the wanted state names, so what the peer maintains and
the application does not model is left alone.

What that builder can express follows from this page. A multi-valued attribute is replaced as a
whole, since :rfc:`RFC7643 §2.4 <7643#section-2.4>` gives its entries no identity to match one
state against the other. See :doc:`../how-to/build-a-patch`.

To inspect or change a resource directly with the same path syntax, outside a PATCH request, use
:doc:`../how-to/access-resource-values`.
