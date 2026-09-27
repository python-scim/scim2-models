Validation policies
===================

Vendors implement SCIM from the same specifications and still send payloads those specifications
do not describe. scim2-models refuses such a payload by default. A
:class:`~scim2_models.ScimPolicy` states, for one application, how much of it to accept anyway.

Why a policy sits beside the context
------------------------------------

A :class:`~scim2_models.Context` and a policy answer two different questions. The difference
tells which settings belong in a policy.

The context says what a payload is: a creation request, a query response. Both ends of an exchange
read it the same way, because :rfc:`RFC7644 <7644>` defines what each one contains. It travels
with the message.

The policy says how the payloads are treated here. Nothing on the wire carries it, and the peer
never learns of it. Two applications talking to each other may hold opposite policies and still
agree on every message they exchange.

A setting belongs in a policy when it changes how a payload is read or written, and when the
specification leaves the choice open. Page sizes, base URLs and authentication schemes are
configuration too, and they belong to the application that serves the requests.

Why every default is strict
---------------------------

§5.3 of the SCIM interoperability profile asks a service provider to reject the attributes and the
schema URNs it does not define. The library applies this strict reading when it is given no
policy.

A service built on scim2-models keeps refusing the payloads of a client that sends unknown
attributes until its author picks :attr:`~scim2_models.ScimPolicy.Unknown.ignore` or
:attr:`~scim2_models.ScimPolicy.Unknown.keep`. The library documents how to accept such payloads,
but the author has to choose to.

The strict default also applies to a client reading a response. This goes further than the
profile, since §5.3 only addresses service providers. But a model has no notion of role. A
client validates the request it writes, and the server validates the same request when it
receives it. So the context cannot tell a client from a server.

Tolerances that need no setting
-------------------------------

A setting is worth its cost when a tolerance could confuse one payload with another. Some cases
the specification does not cover carry no such risk, and scim2-models accepts them without a
setting.

A key of a PATCH value that is an attribute path, such as ``name.givenName``, is read as that
path. Microsoft Entra ID and its SCIM Validator send such keys. A strict reading would reject them
as unknown attributes. But :rfc:`RFC7643 §2.1 <7643#section-2.1>` forbids dots and colons in
attribute names, so the key cannot mean anything else. A setting that rejects it by default would
only break that client. :doc:`patch` describes how such a key is read.

What a policy leaves alone
--------------------------

**PATCH filters stay strict.** Under :attr:`~scim2_models.ScimPolicy.Unknown.ignore` or
:attr:`~scim2_models.ScimPolicy.Unknown.keep`, a PATCH operation on an attribute no model
declares changes nothing, like an undeclared attribute in its value. A filter that
compares such an attribute is still rejected with ``invalidFilter``, and a malformed path with
``invalidPath``. In both cases, there is no attribute the policy could drop. Dropping an
operation has a cost: the server returns 200 for a change it never applied, where
:rfc:`RFC7644 §3.5.2 <7644#section-3.5.2>` asks for an error. A tolerant policy already accepts
that cost for the body of a resource, and the strict default keeps the error.

**Building a model in Python stays strict.** ``User(bogus=1)`` and ``user.bogus = 1`` raise under
every policy. Pydantic only offers a hook for extra keys during validation, so a keyword argument
has nowhere to go. A policy governs payloads, and a payload comes from a peer.

Where a policy is read
----------------------

A call runs under the first policy it finds among:

1. the ``scim_policy`` argument of the call;
2. the policy of the innermost open block, from ``with policy:`` or ``with provider:``;
3. the strict reading.

The policy is looked up for each validation and each dump. So a model validated inside a block
and serialized outside it is serialized under the strict reading. Under
:attr:`~scim2_models.ScimPolicy.Unknown.keep`, the unknown attributes stay on the instance, in
:attr:`~scim2_models.BaseModel.unknown_attributes`, and a dump inside a block writes them back.
The other settings leave nothing on the instance.

Blocks nest, and each one restores what it interrupted. Each thread and each asyncio task carries
its own, so a server may open one per request.

What a kept attribute costs
---------------------------

An attribute no model declares has no :class:`~scim2_models.Returned` and no
:class:`~scim2_models.Mutability` annotation, since those come from a schema. Nothing can filter
it by context, and it is written back in all of them. A client reading from one service under
:attr:`~scim2_models.ScimPolicy.Unknown.keep` and creating on another pushes the first service's
attributes to the second. A proxy needs this, and ``keep`` only applies when an author picks it.
