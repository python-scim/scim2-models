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
Per :rfc:`RFC7644 §3.5.2.3 <7644#section-3.5.2.3>`, a ``replace`` on ``name`` keeps the
sub-attributes it does not carry. But some peers replace the whole attribute and drop them. One
path per sub-attribute gives the same result on every peer.

Leave alone what the wanted state does not set
----------------------------------------------

Only the attributes set in the wanted state take part in the comparison. Unlike a
:meth:`~scim2_models.Resource.replace`, the patch keeps an attribute the peer maintains and the
application does not model.

.. doctest::

   >>> distant = User(user_name="bjensen", nick_name="Barb", title="CEO")
   >>> wanted = User(user_name="bjensen", nick_name="Babs")
   >>> patch = PatchOp.build_from(distant, wanted)
   >>> patch.model_dump()["Operations"]
   [{'op': 'replace', 'path': 'nickName', 'value': 'Babs'}]

Setting an attribute to no value says the opposite. ``title=None`` reads as "clear the title",
while a ``title`` left out reads as "leave it alone":

.. doctest::

   >>> wanted = User(user_name="bjensen", title=None)
   >>> patch = PatchOp.build_from(distant, wanted)
   >>> patch.model_dump()["Operations"]
   [{'op': 'remove', 'path': 'title'}]

The same rule applies to sub-attributes. The path to an extension attribute starts with the
schema URN:

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

A multi-valued attribute is replaced as a whole. Only the sub-attributes set in the wanted entries
decide whether it changed. The sub-attributes that only the peer maintains do not count as a
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

A ``readOnly`` attribute is always left out, even when the two states differ. Per
:rfc:`RFC7644 §3.5.2 <7644#section-3.5.2>`, a client must not modify one, so the patch would be
invalid. That covers :attr:`~scim2_models.Resource.id`,
:attr:`~scim2_models.Resource.meta` and :attr:`~scim2_models.User.groups`, along with the
``readOnly`` sub-attributes of a complex attribute.

An ``immutable`` attribute that holds no value yet is added, which
:rfc:`RFC7644 §3.5.2 <7644#section-3.5.2>` allows. One that already holds a value cannot be
modified, and :meth:`~scim2_models.PatchOp.build_from` raises a
:class:`~scim2_models.MutabilityException` rather than building a request the peer must refuse.

An attribute a server never returns, such as :attr:`~scim2_models.User.password`, looks unset on the
peer side. So every patch built from a state that sets it sends it again.
