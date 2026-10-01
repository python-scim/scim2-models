Tolerate a non-conformant peer
==============================

Use this guide when a real SCIM implementation sends payloads scim2-models refuses. A
:class:`~scim2_models.ScimPolicy` says how much of a payload to accept beyond what
:rfc:`RFC7643 <7643>` and :rfc:`RFC7644 <7644>` describe. See :doc:`../explanation/policies` for
what belongs in one and what does not.

Accept the attributes a peer adds
---------------------------------

A payload carrying an attribute no model declares is refused by default. Set
:attr:`~scim2_models.ScimPolicy.unknown` to
:attr:`Unknown.ignore <scim2_models.ScimPolicy.Unknown.ignore>` to read the rest of it:

.. doctest::

   >>> from scim2_models import ScimPolicy, User
   >>> payload = {
   ...     "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
   ...     "userName": "bjensen",
   ...     "unknownAttr": "some value",
   ... }
   >>> tolerant = ScimPolicy(unknown=ScimPolicy.Unknown.ignore)
   >>> user = User.model_validate(payload, scim_policy=tolerant)
   >>> user.user_name
   'bjensen'

What was dropped stays readable, spelled as the peer sent it:

.. doctest::

   >>> user.unknown_attributes
   {'unknownAttr': 'some value'}

A sub-attribute lands on the complex attribute carrying it, so a caller reads it where it came
from:

.. doctest::

   >>> payload["name"] = {"familyName": "Jensen", "bogusSub": 1}
   >>> user = User.model_validate(payload, scim_policy=tolerant)
   >>> user.name.unknown_attributes
   {'bogusSub': 1}

An extension with no model is handled the same way. In a payload, it is a root key that is a URN.

Under that policy, a PATCH operation on an undeclared attribute changes
nothing, and the other operations still apply. Pass the policy to
:meth:`PatchOp.patch <scim2_models.PatchOp.patch>` as well as to the validation of the message.

Write unknown attributes back
-----------------------------

Set :attr:`~scim2_models.ScimPolicy.unknown` to
:attr:`Unknown.keep <scim2_models.ScimPolicy.Unknown.keep>` to also write them back when dumping.
A proxy that reads from one service and creates on another needs this:

.. doctest::

   >>> keeping = ScimPolicy(unknown=ScimPolicy.Unknown.keep)
   >>> user = User.model_validate(payload, scim_policy=keeping)
   >>> user.model_dump(scim_policy=keeping)["unknownAttr"]
   'some value'

The policy of the dump decides, so a model read under ``keep`` and written under the default keeps
its unknown attributes without sending them:

.. doctest::

   >>> "unknownAttr" in user.model_dump()
   False
   >>> user.unknown_attributes["unknownAttr"]
   'some value'

Remove a group member the way Entra asks
----------------------------------------

:rfc:`RFC7644 §3.5.2.2 <7644#section-3.5.2.2>` reads the target of a ``remove`` in its ``path``
alone. Microsoft Entra ID puts it in ``value`` instead, and scim2-models refuses that operation.
Set :attr:`~scim2_models.ScimPolicy.remove_value_as_filter` to
:attr:`RemoveValue.apply <scim2_models.ScimPolicy.RemoveValue.apply>` to remove the entries that
match the ``value``:

.. doctest::

   >>> from scim2_models import Group, PatchOp, PatchOperation
   >>> group = Group.model_validate(
   ...     {
   ...         "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"],
   ...         "displayName": "Tour Guides",
   ...         "members": [
   ...             {"value": "2819c223", "display": "Babs Jensen"},
   ...             {"value": "902c246b", "display": "Mandy Pepperidge"},
   ...         ],
   ...     }
   ... )
   >>> patch = PatchOp[Group](
   ...     operations=[
   ...         PatchOperation(
   ...             op=PatchOperation.Op.remove,
   ...             path="members",
   ...             value=[{"value": "2819c223"}],
   ...         )
   ...     ]
   ... )
   >>> entra = ScimPolicy(remove_value_as_filter=ScimPolicy.RemoveValue.apply)
   >>> patch.patch(group, scim_policy=entra)
   True
   >>> [member.value for member in group.members]
   ['902c246b']

A member matches an entry when its sub-attributes have the values in the entry. Its other
sub-attributes are not compared: in the example, ``display`` is not in the entry. A ``value`` that
matches no member changes nothing and reports success. :rfc:`RFC7644 §3.5.2.2
<7644#section-3.5.2.2>` asks for this when the membership was not there.

Entra `documents this form as non-conformant
<https://learn.microsoft.com/en-us/entra/identity/app-provisioning/application-provisioning-config-problem-scim-compatibility#flags-to-alter-the-scim-behavior>`_.
Its ``aadOptscim062020`` tenant flag makes it send a filter path instead. Setting that flag is the
proper way out.

Create the entry an Entra filter describes
------------------------------------------

Microsoft Entra ID fills an attribute it has not set yet `through a filter
<https://learn.microsoft.com/en-us/entra/identity/app-provisioning/use-scim-to-provision-users-and-groups#update-user-multi-valued-properties>`_,
such as ``emails[type eq "work"].value`` on a user without a work email. The filter matches
nothing, and scim2-models returns ``noTarget``. Set
:attr:`~scim2_models.ScimPolicy.unmatched_path_filter` to
:attr:`UnmatchedPathFilter.create <scim2_models.ScimPolicy.UnmatchedPathFilter.create>` to add the
entry the filter describes instead:

.. doctest::

   >>> patch = PatchOp[User](
   ...     operations=[
   ...         PatchOperation(
   ...             op=PatchOperation.Op.add,
   ...             path='emails[type eq "work"].value',
   ...             value="bjensen@example.com",
   ...         )
   ...     ]
   ... )
   >>> creating = ScimPolicy(unmatched_path_filter=ScimPolicy.UnmatchedPathFilter.create)
   >>> user = User(user_name="bjensen")
   >>> patch.patch(user, scim_policy=creating)
   True
   >>> [(email.type.value, email.value) for email in user.emails]
   [('work', 'bjensen@example.com')]

The setting covers ``add`` and ``replace``, since Entra sends ``replace`` once its
``aadOptscim062020`` tenant flag is set. It only works with ``eq`` comparisons joined by ``and``.
Any other filter still returns ``noTarget``, and so does a filter on an attribute without
sub-attributes. :doc:`../explanation/patch` explains why this is not the default.

State a policy once per request
-------------------------------

A server can set the policy once per request instead of passing it to every call. Opening a block
sets it for everything inside:

.. doctest::

   >>> with tolerant:
   ...     user = User.model_validate(payload)
   >>> user.user_name
   'bjensen'

A policy passed to the call wins over the block:

.. doctest::

   >>> from pydantic import ValidationError
   >>> with tolerant:
   ...     try:
   ...         User.model_validate(payload, scim_policy=ScimPolicy())
   ...     except ValidationError:
   ...         print("refused")
   refused

A :class:`~scim2_models.ScimProvider` carries a policy alongside the resources it describes, and
opens the same kind of block:

.. doctest::

   >>> from scim2_models import ScimProvider
   >>> provider = ScimProvider(models=[User], policy=tolerant)
   >>> with provider:
   ...     user = User.model_validate(payload)
   >>> user.unknown_attributes["unknownAttr"]
   'some value'

Blocks nest and each restores the one it interrupted. Each thread and each asyncio task carries
its own, so a server may open one per request it serves.
