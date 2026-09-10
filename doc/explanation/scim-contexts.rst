SCIM contexts and attribute characteristics
============================================

scim2-models uses the same model for a resource held by an application and for the different
representations that SCIM exchanges over HTTP. A :class:`~scim2_models.Context` tells validation
or serialization which representation is in use. This is why a field may be optional in Python
while still being required in a creation request.

Request contexts validate what a client may send. Response contexts validate and serialize what a
server may return. :attr:`~scim2_models.Context.DEFAULT` deliberately applies neither set of SCIM
request/response rules, which is useful for internal application state.

Attribute characteristics
-------------------------

SCIM declares rules on attributes rather than on whole Python models:

``required``
   Requires a value in creation and replacement requests. A partial PATCH request does not have
   to repeat every required attribute.

``mutability``
   Controls whether a client may write an attribute. ``readOnly`` is removed from creation and
   replacement payloads, while a PATCH targeting it is rejected. ``immutable`` needs the current
   resource value, so replacement and PATCH enforce it as the change is applied.

``returned``
   Controls response projection. ``always`` cannot be excluded, ``never`` cannot be returned,
   ``default`` is returned unless excluded, and ``request`` is returned only when explicitly
   requested.

``uniqueness``
   Describes a service guarantee but is not enforced by a model: checking it requires the
   resources already held by the service.

The defaults are ``required: false``, ``mutability: readWrite``, ``returned: default`` and
``uniqueness: none``. :class:`~scim2_models.CaseExact` governs filter comparison, not storage or
serialization.

Why fields are optional
-----------------------

A resource has valid forms in which a field is absent: a client does not send a read-only value,
a response omits a ``returned: request`` value, and a partial PATCH message mentions only its
target. Declaring a field as ``T | None`` lets one model represent those forms. The context and
the field characteristics then impose the stricter rule at the protocol boundary.

This differs from relying on Pydantic required fields alone. A Pydantic-required field would
reject every representation that legitimately omits it, before SCIM can decide whether that
omission is allowed.

Where rules are enforced
------------------------

Creation and replacement validation check required values. Response serialization applies
``returned`` and attribute projection. The replacement workflow calls
:meth:`~scim2_models.Resource.replace` after parsing so it can compare immutable values with the
stored resource. PATCH first validates the operation message, then checks immutable values while
applying it.

:doc:`../how-to/validate-and-serialize` presents the validation and serialization procedure for
each resource operation.
