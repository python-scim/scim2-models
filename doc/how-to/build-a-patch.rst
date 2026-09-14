Build a patch from two resource states
======================================

Use this guide when an application holds the state a peer is believed to have and the state it
should have, and must send the modification. :meth:`~scim2_models.PatchOp.build_from` compares the
two and returns the :class:`~scim2_models.PatchOp` that closes the gap.

Build the patch
---------------

Pass the state the peer holds first, then the state it should hold:

.. doctest::

   >>> from scim2_models import Name, PatchOp, User
   >>> distant = User(user_name="bjensen", name=Name(given_name="Barbara", family_name="Jensen"))
   >>> wanted = User(user_name="bjensen", name=Name(given_name="Babs", family_name="Jensen"))
   >>> patch = PatchOp.build_from(distant, wanted)
   >>> patch.model_dump()["Operations"]
   [{'op': 'replace', 'path': 'name.givenName', 'value': 'Babs'}]

A complex attribute is compared sub-attribute by sub-attribute, and each one gets its own path.
Targeting ``name`` as a whole would replace it entirely and drop what the operation does not
carry.

Leave alone what the wanted state does not name
-----------------------------------------------

Only the attributes the wanted state names take part in the comparison. This is what separates a
patch from the :meth:`~scim2_models.Resource.replace` it stands for: an attribute the peer
maintains and the application does not model survives the modification.

.. doctest::

   >>> distant = User(user_name="bjensen", nick_name="Barb", title="CEO")
   >>> wanted = User(user_name="bjensen", nick_name="Babs")
   >>> patch = PatchOp.build_from(distant, wanted)
   >>> patch.model_dump()["Operations"]
   [{'op': 'replace', 'path': 'nickName', 'value': 'Babs'}]

Naming an attribute with no value says the opposite. ``title=None`` reads as "clear the title",
where an unnamed ``title`` reads as "leave it alone":

.. doctest::

   >>> wanted = User(user_name="bjensen", title=None)
   >>> patch = PatchOp.build_from(distant, wanted)
   >>> patch.model_dump()["Operations"]
   [{'op': 'remove', 'path': 'title'}]

The same rule reaches sub-attributes, and an extension is named by its schema URN:

.. doctest::

   >>> from scim2_models import EnterpriseUser
   >>> distant = User[EnterpriseUser](user_name="bjensen")
   >>> distant[EnterpriseUser] = EnterpriseUser(department="Tour")
   >>> wanted = User[EnterpriseUser](user_name="bjensen")
   >>> wanted[EnterpriseUser] = EnterpriseUser(department="Chess")
   >>> patch = PatchOp.build_from(distant, wanted)
   >>> str(patch.operations[0].path)
   'urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:department'

Send nothing when nothing changed
---------------------------------

Two states that agree have no patch to describe: an ``Operations`` array must hold at least one
operation, per :rfc:`RFC7644 §3.5.2 <7644#section-3.5.2>`. :meth:`~scim2_models.PatchOp.build_from`
returns :data:`None`, so an application tests it before sending a request:

.. doctest::

   >>> PatchOp.build_from(wanted, wanted) is None
   True

Know how collections are compared
---------------------------------

A multi-valued attribute is replaced as a whole. Only the sub-attributes the wanted entries name
decide whether it changed, so the sub-attributes the peer alone maintains do not read as a
difference:

.. doctest::

   >>> from scim2_models import Email
   >>> distant = User(emails=[Email(value="barb@example.com", type="work", primary=True)])
   >>> wanted = User(emails=[Email(value="barb@example.com")])
   >>> PatchOp.build_from(distant, wanted) is None
   True

When the collection does change, the whole of it is replaced and the peer's own sub-attributes go
with it:

.. doctest::

   >>> wanted = User(emails=[Email(value="babs@example.com")])
   >>> patch = PatchOp.build_from(distant, wanted)
   >>> patch.model_dump()["Operations"]
   [{'op': 'replace', 'path': 'emails', 'value': [{'value': 'babs@example.com'}]}]

The builder cannot do better: :rfc:`RFC7643 §2.4 <7643#section-2.4>` gives the entries of a
multi-valued attribute no identity, so nothing distinguishes an entry that changed from an entry
that was removed and another that was added. An application that knows how to identify its own
entries writes those operations itself, targeting a sub-attribute through a filter such as
``emails[type eq "work"].value``.

Read what the patch never carries
---------------------------------

A ``readOnly`` attribute is left out however much the two states differ:
:rfc:`RFC7644 §3.5.2 <7644#section-3.5.2>` forbids a client to modify one, and naming it would
make the patch invalid. That covers :attr:`~scim2_models.Resource.id`,
:attr:`~scim2_models.Resource.meta` and :attr:`~scim2_models.User.groups`, along with the
``readOnly`` sub-attributes of a complex attribute.

An ``immutable`` attribute that holds no value yet is added, which
:rfc:`RFC7644 §3.5.2 <7644#section-3.5.2>` allows. One that already holds a value cannot be
modified, and :meth:`~scim2_models.PatchOp.build_from` raises a
:class:`~scim2_models.MutabilityException` rather than building a request the peer must refuse.

An attribute a server never returns, such as :attr:`~scim2_models.User.password`, reads as unset on
the side of the peer. Every patch built from a state naming it carries it again.
