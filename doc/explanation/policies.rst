Validation policies
===================

Vendors implement SCIM from the same specifications and still send payloads those specifications
do not describe. scim2-models refuses such a payload by default. A
:class:`~scim2_models.ScimPolicy` states, for one application, how much of it to accept anyway.

Why a policy sits beside the context
------------------------------------

A :class:`~scim2_models.Context` and a policy answer two different questions, and the difference
decides what may become a policy setting at all.

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
schema URNs it does not define, and the strict reading is what the library applies when it is
given no policy.

Two consequences follow from that choice.

A service built on scim2-models keeps refusing the payloads of a client that sends unknown
attributes until its author picks :attr:`~scim2_models.ScimPolicy.Unknown.ignore` or
:attr:`~scim2_models.ScimPolicy.Unknown.keep`. What the library ships is a documented way to
tolerate, and the tolerance itself stays a decision.

The strict default also applies to a client reading a response, which reaches further than the
profile does: §5.3 addresses service providers receiving requests and says nothing about clients.
Telling the two apart would take a notion of role, and a model has none — a request is validated
by the client that wrote it as readily as by the server that received it, so the context cannot
stand in for one.

What a policy leaves alone
--------------------------

**PATCH paths stay strict.** An operation whose ``path`` names an attribute no model declares
raises :class:`~scim2_models.PathNotFoundException`, whatever the policy says. Path resolution and
unknown attributes are two separate mechanisms, and making them uniform would take a third. The
default that would come out of it is the wrong one: a server would answer 200 to a modification it
never applied, where :rfc:`RFC7644 §3.5.2 <7644#section-3.5.2>` asks for an error. Inside the body
of a resource the trade is different, since dropping one unknown attribute still lands everything
the peer and the model both knew.

**Building a model in Python stays strict.** ``User(bogus=1)`` and ``user.bogus = 1`` raise under
every policy. Pydantic only offers a hook for extra keys during validation, so a keyword argument
has nowhere to go. A policy governs payloads, and a payload comes from a peer.

Where a policy is read
----------------------

Three layers answer, in order:

1. the ``scim_policy`` argument of the call;
2. the policy of the innermost open block, from ``with policy:`` or ``with provider:``;
3. the strict reading.

The resolution happens for each pass, which gives the layers a visible consequence. A model
validated inside a block and serialized outside it is serialized under the strict reading. Under
:attr:`~scim2_models.ScimPolicy.Unknown.keep` the attributes themselves survive on the instance
and :attr:`~scim2_models.BaseModel.unknown_attributes` still reads them, so the dump can be made
again inside a block; the other settings leave nothing behind.

Blocks nest, and each one restores what it interrupted. Each thread and each asyncio task carries
its own, so a server may open one per request.

What a kept attribute costs
---------------------------

An attribute no model declares has no :class:`~scim2_models.Returned` and no
:class:`~scim2_models.Mutability` annotation, since those come from a schema. Nothing can filter
it by context, and it is written back in all of them. A client reading from one service under
:attr:`~scim2_models.ScimPolicy.Unknown.keep` and creating on another pushes the first service's
attributes to the second. A proxy wants exactly that, and ``keep`` is a setting an author picks.
