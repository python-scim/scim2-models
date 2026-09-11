Tolerate a non-conformant peer
==============================

Use this guide when a real SCIM implementation sends payloads scim2-models refuses. A
:class:`~scim2_models.ScimPolicy` says how much of a payload to accept beyond what
:rfc:`RFC7643 <7643>` and :rfc:`RFC7644 <7644>` describe. See :doc:`../explanation/policies` for
what belongs in one and what does not.

Accept the attributes a peer adds
---------------------------------

A payload carrying an attribute no model declares is refused by default. Set
:attr:`~scim2_models.ScimPolicy.Unknown.ignore` to read the rest of it:

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

An unmodelled extension takes the same route, since a payload names one with a root key whose name
is a URN.

Write unknown attributes back
-----------------------------

:attr:`~scim2_models.ScimPolicy.Unknown.keep` also writes them to the dump, which is what a proxy
reading from one service and creating on another needs:

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
Set :attr:`~scim2_models.ScimPolicy.RemoveValue.apply` to read the ``value`` as the selection it
means:

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

Each entry becomes a filter on the sub-attributes it names, so a member carrying more than the
entry describes still matches. A selection matching nothing changes nothing and reports success,
which :rfc:`RFC7644 §3.5.2.2 <7644#section-3.5.2.2>` asks for a membership that was not there.

Entra documents this form as non-conformant, and its ``aadOptscim062020`` tenant flag makes it
send a filter path instead. Setting that flag is the other way out.

State a policy once per request
-------------------------------

A server naming the policy at every call repeats itself. Opening a block sets it for everything
inside:

.. doctest::

   >>> with tolerant:
   ...     user = User.model_validate(payload)
   >>> user.user_name
   'bjensen'

An argument named at the call site wins over the block:

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
