"""The policy that says how a peer's deviations from the specification are treated."""

import asyncio
import contextvars
import threading
from typing import Annotated
from typing import Any

import pytest
from pydantic import SerializationInfo
from pydantic import ValidationError
from pydantic import ValidationInfo
from pydantic import ValidatorFunctionWrapHandler
from pydantic import field_serializer
from pydantic import model_validator

from scim2_models import URN
from scim2_models import ComplexAttribute
from scim2_models import Context
from scim2_models import CreationRequestContext
from scim2_models import CreationResponseContext
from scim2_models import EnterpriseUser
from scim2_models import Extension
from scim2_models import Group
from scim2_models import InvalidFilterException
from scim2_models import InvalidValueException
from scim2_models import Mutability
from scim2_models import MutabilityException
from scim2_models import NoTargetException
from scim2_models import PatchOp
from scim2_models import PatchOperation
from scim2_models import Path
from scim2_models import Resource
from scim2_models import ScimPolicy
from scim2_models import ScimProvider
from scim2_models import User
from scim2_models.policy import _ambient_policy
from scim2_models.policy import _policy

IGNORE = ScimPolicy(unknown=ScimPolicy.Unknown.ignore)

VALIDATION_POLICIES: list[ScimPolicy] = []
SERIALIZATION_POLICIES: list[ScimPolicy] = []


class Probe(ComplexAttribute):
    """Record the policy each pass over this attribute runs under."""

    label: str | None = None

    @model_validator(mode="wrap")
    @classmethod
    def _record_validation_policy(
        cls, value: Any, handler: ValidatorFunctionWrapHandler, info: ValidationInfo
    ) -> "Probe":
        VALIDATION_POLICIES.append(_policy(info))
        return handler(value)  # type: ignore[no-any-return]

    @field_serializer("label")
    def _record_serialization_policy(self, value: Any, info: SerializationInfo) -> Any:
        SERIALIZATION_POLICIES.append(_policy(info))
        return value


class Probed(Resource):
    __schema__ = URN("urn:org:example:Probed")

    probe: Probe | None = None


PAYLOAD = {"schemas": [str(Probed.__schema__)], "probe": {"label": "a"}}


@pytest.fixture(autouse=True)
def forget_recorded_policies():
    VALIDATION_POLICIES.clear()
    SERIALIZATION_POLICIES.clear()


def test_a_new_policy_forbids_every_deviation():
    """Every setting starts at the strict reading of the specification."""
    policy = ScimPolicy()
    assert policy.unknown == ScimPolicy.Unknown.forbid
    assert policy.remove_value_as_filter == ScimPolicy.RemoveValue.forbid


def test_a_policy_cannot_be_modified_once_built():
    """A settled policy cannot contradict the pass that is already running under it."""
    with pytest.raises(ValidationError):
        ScimPolicy().unknown = ScimPolicy.Unknown.ignore


def test_a_validation_given_no_policy_runs_under_the_default():
    """A caller that names no policy gets the strict reading of the specification."""
    Probed.model_validate(PAYLOAD)
    assert VALIDATION_POLICIES == [ScimPolicy()]


def test_a_policy_reaches_the_validator_of_a_nested_attribute():
    """A policy given at the root governs the whole tree, not only its top."""
    Probed.model_validate(PAYLOAD, scim_policy=IGNORE)
    assert VALIDATION_POLICIES == [IGNORE]


def test_a_policy_reaches_the_validator_of_a_nested_attribute_from_json():
    """A JSON payload takes the same route as a mapping."""
    Probed.model_validate_json(
        '{"schemas": ["urn:org:example:Probed"], "probe": {"label": "a"}}',
        scim_policy=IGNORE,
    )
    assert VALIDATION_POLICIES == [IGNORE]


def test_a_policy_reaches_the_serializer_of_a_nested_attribute():
    """A dump carries the policy down the tree the way a validation does."""
    Probed.model_validate(PAYLOAD).model_dump(scim_policy=IGNORE)
    assert SERIALIZATION_POLICIES == [IGNORE]


def test_a_policy_reaches_the_serializer_of_a_nested_attribute_for_json():
    """A JSON dump takes the same route as a mapping dump."""
    Probed.model_validate(PAYLOAD).model_dump_json(scim_policy=IGNORE)
    assert SERIALIZATION_POLICIES == [IGNORE]


def test_a_serialization_given_no_policy_runs_under_the_default():
    """A dump that names no policy gets the strict reading of the specification."""
    Probed.model_validate(PAYLOAD).model_dump()
    assert SERIALIZATION_POLICIES == [ScimPolicy()]


def test_a_policy_passed_in_the_pydantic_context_is_left_alone():
    """A caller reaching for the pydantic context directly is not overridden."""
    Probed.model_validate(PAYLOAD, context={"scim_policy": IGNORE})
    assert VALIDATION_POLICIES == [IGNORE]


def test_a_policy_crosses_a_validation_context_annotation():
    """The context annotations of :mod:`scim2_models.annotated` restart a validation."""

    class Outer(Resource):
        __schema__ = URN("urn:org:example:Outer")

        probed: CreationRequestContext[Probed] | None = None

    Outer.model_validate(
        {"schemas": [str(Outer.__schema__)], "probed": PAYLOAD},
        scim_policy=IGNORE,
    )
    assert VALIDATION_POLICIES == [IGNORE]


def test_a_policy_crosses_a_serialization_context_annotation():
    """The context annotations of :mod:`scim2_models.annotated` restart a dump."""

    class Outer(Resource):
        __schema__ = URN("urn:org:example:Outer")

        probed: CreationResponseContext[Probed] | None = None

    outer = Outer.model_validate(
        {"schemas": [str(Outer.__schema__)], "probed": PAYLOAD},
        scim_ctx=Context.DEFAULT,
    )
    VALIDATION_POLICIES.clear()
    outer.model_dump(scim_ctx=Context.RESOURCE_CREATION_RESPONSE, scim_policy=IGNORE)
    assert SERIALIZATION_POLICIES == [IGNORE]


# The ambient policy


def test_a_policy_set_around_a_block_reaches_a_validation():
    """A server wraps a request in one block instead of naming the policy everywhere."""
    with IGNORE:
        Probed.model_validate(PAYLOAD)

    assert VALIDATION_POLICIES == [IGNORE]


def test_a_policy_set_around_a_block_reaches_a_serialization():
    """A dump reads the ambient policy the way a validation does."""
    resource = Probed.model_validate(PAYLOAD)

    with IGNORE:
        resource.model_dump()

    assert SERIALIZATION_POLICIES == [IGNORE]


def test_an_explicit_policy_wins_over_the_ambient_one():
    """The call names what it wants, and the block only says what is otherwise meant."""
    with IGNORE:
        Probed.model_validate(PAYLOAD, scim_policy=ScimPolicy())

    assert VALIDATION_POLICIES == [ScimPolicy()]


def test_leaving_a_block_restores_the_strict_reading():
    """A model validated under a policy is not validated under it forever."""
    with IGNORE:
        pass
    Probed.model_validate(PAYLOAD)

    assert VALIDATION_POLICIES == [ScimPolicy()]


def test_a_nested_block_restores_the_policy_it_interrupted():
    """Blocks stack, so an inner tolerance does not outlive itself."""
    keep = ScimPolicy(unknown=ScimPolicy.Unknown.keep)

    with IGNORE:
        with keep:
            Probed.model_validate(PAYLOAD)
        Probed.model_validate(PAYLOAD)

    assert VALIDATION_POLICIES == [keep, IGNORE]


def test_a_provider_lends_its_policy_to_the_block_it_opens():
    """A service describes what it serves and what it tolerates in one object."""
    provider = ScimProvider(models=[Probed], policy=IGNORE)

    with provider:
        Probed.model_validate(PAYLOAD)

    assert VALIDATION_POLICIES == [IGNORE]


def test_a_provider_passed_at_the_call_lends_its_policy_to_a_validation():
    """The policy of a provider passed at the call applies without a block."""
    provider = ScimProvider(models=[Probed], policy=IGNORE)

    Probed.model_validate(PAYLOAD, scim_provider=provider)

    assert VALIDATION_POLICIES == [IGNORE]


def test_a_provider_passed_at_the_call_lends_its_policy_to_a_serialization():
    """A dump reads the policy of the provider the way a validation does."""
    provider = ScimProvider(models=[Probed], policy=IGNORE)
    resource = Probed.model_validate(PAYLOAD)

    resource.model_dump(scim_provider=provider)

    assert SERIALIZATION_POLICIES == [IGNORE]


def test_a_policy_passed_at_the_call_wins_over_the_one_of_the_provider():
    """One provider can read a single payload under another policy."""
    provider = ScimProvider(models=[Probed], policy=IGNORE)

    Probed.model_validate(PAYLOAD, scim_provider=provider, scim_policy=ScimPolicy())

    assert VALIDATION_POLICIES == [ScimPolicy()]


def test_a_provider_passed_at_the_call_wins_over_the_ambient_policy():
    """The call names what it wants, and the block only says what is otherwise meant."""
    provider = ScimProvider(models=[Probed], policy=IGNORE)

    with ScimPolicy():
        Probed.model_validate(PAYLOAD, scim_provider=provider)

    assert VALIDATION_POLICIES == [IGNORE]


def test_a_provider_passed_at_the_call_tolerates_an_unknown_attribute():
    """An unknown attribute is ignored when the provider passed at the call tolerates it."""
    provider = ScimProvider(models=[User], policy=IGNORE)
    payload = {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        "userName": "bjensen",
        "foo": "bar",
    }

    user = User.model_validate(payload, scim_provider=provider)

    assert user.user_name == "bjensen"


def test_a_provider_given_no_policy_declares_the_strict_reading():
    """Unlike its config, a provider always has a policy: one always applies."""
    assert ScimProvider().policy == ScimPolicy()


def test_a_discovered_provider_carries_the_policy_it_is_given():
    """How a client treats its peer is its own choice, not something it discovers."""
    served = ScimProvider(models=[Probed])

    discovered = ScimProvider.from_discovery(
        served.schemas, served.resource_types, policy=IGNORE
    )

    assert discovered.policy is IGNORE


def test_an_ambient_policy_reaches_the_round_trips_of_a_patch():
    """Applying a patch revalidates in plain Python, out of reach of a call argument."""
    resource = Probed.model_validate(PAYLOAD)
    operation = PatchOperation(
        op=PatchOperation.Op.replace_, path="probe", value={"label": "b"}
    )
    VALIDATION_POLICIES.clear()

    with IGNORE:
        PatchOp[Probed](operations=[operation]).patch(resource)

    assert IGNORE in VALIDATION_POLICIES


def test_two_threads_do_not_share_an_ambient_policy():
    """A server handling requests in a thread pool must not leak one into another."""
    seen: dict[str, ScimPolicy] = {}
    entered = threading.Barrier(2)

    def record(name: str, policy: ScimPolicy) -> None:
        with policy:
            entered.wait()
            Probed.model_validate(PAYLOAD)
            seen[name] = VALIDATION_POLICIES[-1]

    threads = [
        threading.Thread(target=record, args=("tolerant", IGNORE)),
        threading.Thread(target=record, args=("strict", ScimPolicy())),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert seen == {"tolerant": IGNORE, "strict": ScimPolicy()}


def test_two_asyncio_tasks_do_not_share_an_ambient_policy():
    """Two requests served by one event loop each keep their own policy."""

    async def record(policy: ScimPolicy) -> ScimPolicy:
        with policy:
            await asyncio.sleep(0)
            Probed.model_validate(PAYLOAD)
            return VALIDATION_POLICIES[-1]

    async def both() -> list[ScimPolicy]:
        return list(await asyncio.gather(record(IGNORE), record(ScimPolicy())))

    assert asyncio.run(both()) == [IGNORE, ScimPolicy()]


def test_a_policy_entered_twice_stays_ambient_until_its_outer_block_exits():
    """Nesting one policy in itself restores it, then nothing, as the blocks exit."""
    with IGNORE:
        with IGNORE:
            assert _ambient_policy() is IGNORE
        assert _ambient_policy() is IGNORE
    assert _ambient_policy() is None


def test_a_policy_exiting_in_a_copied_context_raises():
    """A copy of the context cannot close the block the original opened."""
    IGNORE.__enter__()
    try:
        copied = contextvars.copy_context()
        with pytest.raises(ValueError, match="different Context"):
            copied.run(IGNORE.__exit__, None, None, None)
        assert _ambient_policy() is IGNORE
    finally:
        IGNORE.__exit__(None, None, None)
    assert _ambient_policy() is None


def test_a_policy_exiting_where_it_did_not_enter_keeps_the_other_blocks():
    """A block closed in a context it did not enter raises, and leaves that context's own block open."""
    strict = ScimPolicy()

    def exit_ignore_under_strict() -> ScimPolicy | None:
        with strict:
            with pytest.raises(RuntimeError, match="did not enter"):
                IGNORE.__exit__(None, None, None)
            return _ambient_policy()

    with IGNORE:
        assert contextvars.Context().run(exit_ignore_under_strict) is strict
        assert _ambient_policy() is IGNORE


# Unknown attributes, dropped


def unknown_payload(**extra: Any) -> dict[str, Any]:
    """Build a User payload carrying whatever a peer added to it."""
    return {
        "schemas": [str(User.__schema__)],
        "userName": "bjensen",
        **extra,
    }


def test_an_unknown_attribute_is_refused_by_default():
    """§5.3 of the interoperability profile asks a provider to reject what it does not define."""
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        User.model_validate(unknown_payload(unknownAttr="x"))


def test_an_ignored_attribute_leaves_the_rest_of_the_payload_readable():
    """An Authentik payload lands in a model only once its extras stop refusing it."""
    user = User.model_validate(unknown_payload(unknownAttr="x"), scim_policy=IGNORE)

    assert user.user_name == "bjensen"


def test_an_ignored_attribute_keeps_the_spelling_the_peer_used():
    """Reporting an unknown attribute is useless once its name has been mangled."""
    user = User.model_validate(unknown_payload(unknownAttr="x"), scim_policy=IGNORE)

    assert user.unknown_attributes == {"unknownAttr": "x"}


def test_an_ignored_attribute_is_captured_where_it_was_found():
    """Each complex attribute answers for what it was sent, not the resource above it."""
    user = User.model_validate(
        unknown_payload(name={"familyName": "Jensen", "bogusSub": 1}),
        scim_policy=IGNORE,
    )

    assert user.unknown_attributes == {}
    assert user.name.unknown_attributes == {"bogusSub": 1}


def test_a_model_that_was_sent_nothing_unknown_reports_an_empty_mapping():
    """The accessor answers on every model, so a caller needs no guard."""
    assert User.model_validate(unknown_payload()).unknown_attributes == {}


def test_an_ignored_attribute_is_not_dumped_back():
    """``ignore`` reports what was dropped; it does not carry it further."""
    user = User.model_validate(unknown_payload(unknownAttr="x"), scim_policy=IGNORE)

    assert "unknownAttr" not in user.model_dump(scim_policy=IGNORE)


def test_an_unmodelled_extension_is_ignored():
    """Half of what makes a payload unreadable is an extension URN, not an attribute."""
    payload = unknown_payload(**{"urn:example:2.0:Pet": {"petName": "Mochi"}})
    payload["schemas"] = [str(User.__schema__), "urn:example:2.0:Pet"]

    user = User.model_validate(
        payload,
        scim_ctx=Context.RESOURCE_CREATION_REQUEST,
        scim_policy=IGNORE,
    )

    assert user.unknown_attributes == {"urn:example:2.0:Pet": {"petName": "Mochi"}}


def test_a_declared_extension_is_not_taken_for_an_unknown_attribute():
    """An extension is named by its URN in the payload and by its class name as a field."""
    urn = str(EnterpriseUser.__schema__)

    user = User[EnterpriseUser].model_validate(
        {
            **unknown_payload(),
            "schemas": [str(User.__schema__), urn],
            urn: {"employeeNumber": "701984"},
        },
        scim_policy=IGNORE,
    )

    assert user.unknown_attributes == {}
    assert user[EnterpriseUser].employee_number == "701984"


def test_the_keys_microsoft_entra_adds_to_a_patch_are_ignored():
    """Entra labels its operations and repeats the resource id, which no message declares."""
    payload = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "id": "2819c223",
        "Operations": [
            {"name": "addMember", "op": "add", "path": "displayName", "value": "g"}
        ],
    }

    patch_op = PatchOp[Group].model_validate(payload, scim_policy=IGNORE)

    assert patch_op.unknown_attributes == {"id": "2819c223"}
    assert patch_op.operations[0].unknown_attributes == {"name": "addMember"}


# Unknown attributes in a PATCH path


def _pathed_patch(operations, policy):
    return PatchOp[User].model_validate(
        {"Operations": operations},
        scim_ctx=Context.RESOURCE_PATCH_REQUEST,
        scim_policy=policy,
    )


def _pathed_user():
    return User(
        user_name="bjensen", emails=[{"value": "b@example.com", "type": "work"}]
    )


UNDECLARED_PATHS = [
    pytest.param("unknownAttr", id="attribute"),
    pytest.param("name.unknownAttr", id="sub-attribute"),
    pytest.param("urn:example:2.0:Unmodelled:attr", id="extension"),
    pytest.param(
        'emails[type eq "work"].unknownAttr', id="sub-attribute of a selection"
    ),
]


def test_an_undeclared_path_is_refused_by_default():
    """The interoperability profile asks a service provider to reject what it does not define."""
    with pytest.raises(ValidationError) as raised:
        _pathed_patch([{"op": "replace", "path": "unknownAttr", "value": "x"}], None)

    assert raised.value.errors()[0]["type"] == "scim_invalidPath"


@pytest.mark.parametrize(
    "policy", [IGNORE, ScimPolicy(unknown=ScimPolicy.Unknown.keep)]
)
@pytest.mark.parametrize("op", ["add", "replace", "remove"])
@pytest.mark.parametrize("path", UNDECLARED_PATHS)
def test_an_undeclared_path_is_dropped_under_a_tolerant_policy(policy, op, path):
    """An attribute the policy drops from a value is also dropped from a path, since it has no field to write to."""
    operation = {"op": op, "path": path}
    if op != "remove":
        operation["value"] = "x"
    user = _pathed_user()
    before = user.model_dump()

    assert not _pathed_patch([operation], policy).patch(user, scim_policy=policy)
    assert user.model_dump() == before


def test_the_operations_beside_an_undeclared_path_are_applied():
    """Dropping one operation leaves the others of the patch to apply."""
    user = _pathed_user()
    patch = _pathed_patch(
        [
            {"op": "replace", "path": "unknownAttr", "value": "x"},
            {"op": "replace", "path": "nickName", "value": "Babs"},
        ],
        IGNORE,
    )

    assert patch.patch(user, scim_policy=IGNORE)
    assert user.nick_name == "Babs"


def test_a_filter_comparing_an_undeclared_sub_attribute_is_invalid_under_any_policy():
    """The policy applies to attribute names, not to filter expressions."""
    patch = _pathed_patch(
        [{"op": "replace", "path": 'emails[unknownAttr eq "x"].value', "value": "x"}],
        IGNORE,
    )

    with pytest.raises(InvalidFilterException):
        patch.patch(_pathed_user(), scim_policy=IGNORE)


def test_a_malformed_path_is_invalid_under_any_policy():
    """A path the grammar rejects has no attribute the policy could drop."""
    with pytest.raises(ValidationError) as raised:
        _pathed_patch([{"op": "replace", "path": "unknown attr", "value": "x"}], IGNORE)

    assert raised.value.errors()[0]["type"] == "scim_invalidPath"


# Unknown attributes, carried back


KEEP = ScimPolicy(unknown=ScimPolicy.Unknown.keep)


def test_a_kept_attribute_is_dumped_back_as_the_peer_spelled_it():
    """A proxy reading from one service and writing to another loses nothing."""
    user = User.model_validate(unknown_payload(unknownAttr="x"), scim_policy=KEEP)

    assert user.model_dump(scim_policy=KEEP)["unknownAttr"] == "x"


def test_a_kept_attribute_is_dumped_back_from_the_level_it_was_found():
    """A sub-attribute goes back where it came from, not to the resource above."""
    payload = unknown_payload(name={"familyName": "Jensen", "bogusSub": 1})

    user = User.model_validate(payload, scim_policy=KEEP)

    assert user.model_dump(scim_policy=KEEP)["name"]["bogusSub"] == 1


def test_a_kept_attribute_is_dumped_in_every_context():
    """No attribute characteristic is declared for it, so no context can filter it out."""
    user = User.model_validate(unknown_payload(unknownAttr="x"), scim_policy=KEEP)

    for context in (
        Context.DEFAULT,
        Context.RESOURCE_CREATION_REQUEST,
        Context.RESOURCE_QUERY_RESPONSE,
    ):
        dumped = user.model_dump(scim_ctx=context, scim_policy=KEEP)
        assert dumped["unknownAttr"] == "x", context


def test_a_kept_attribute_is_dumped_outside_of_any_scim_context():
    """A plain pydantic dump takes the same route."""
    user = User.model_validate(unknown_payload(unknownAttr="x"), scim_policy=KEEP)

    assert user.model_dump(scim_ctx=None, scim_policy=KEEP)["unknownAttr"] == "x"


def test_a_kept_attribute_is_left_out_when_the_dump_forbids_it():
    """The policy governs the pass that is running, and a dump is a pass of its own."""
    user = User.model_validate(unknown_payload(unknownAttr="x"), scim_policy=KEEP)

    assert "unknownAttr" not in user.model_dump()
    assert user.unknown_attributes == {"unknownAttr": "x"}


def test_an_unmodelled_extension_survives_a_round_trip():
    """An unknown extension is a root key whose name is a URN, and its URN is in ``schemas``."""
    payload = unknown_payload(**{"urn:example:2.0:Pet": {"petName": "Mochi"}})
    payload["schemas"] = [str(User.__schema__), "urn:example:2.0:Pet"]

    with KEEP:
        dumped = User.model_validate(
            payload, scim_ctx=Context.RESOURCE_CREATION_REQUEST
        ).model_dump(scim_ctx=Context.RESOURCE_CREATION_RESPONSE)

    assert dumped["urn:example:2.0:Pet"] == {"petName": "Mochi"}
    assert "urn:example:2.0:Pet" in dumped["schemas"]


def test_a_pathless_patch_operation_keeps_the_unknown_attributes_it_merges_over():
    """A pathless operation dumps the resource and revalidates it, in plain Python."""
    with KEEP:
        user = User.model_validate(unknown_payload(unknownAttr="x"))
        operation = PatchOperation(
            op=PatchOperation.Op.replace_, value={"displayName": "Barbara"}
        )
        PatchOp[User](operations=[operation]).patch(user)

    assert user.display_name == "Barbara"
    assert user.unknown_attributes == {"unknownAttr": "x"}


def test_replacing_a_complex_attribute_keeps_the_unknowns_it_carried():
    """RFC7644 §3.5.2.3 keeps the sub-attributes a replace does not specify, unknown ones included."""
    with KEEP:
        user = User.model_validate(
            unknown_payload(name={"familyName": "Jensen", "bogusSub": 1})
        )
        operation = PatchOperation(
            op=PatchOperation.Op.replace_, path="name", value={"givenName": "Barbara"}
        )
        PatchOp[User](operations=[operation]).patch(user)

    assert user.name.given_name == "Barbara"
    assert user.name.family_name == "Jensen"
    assert user.name.unknown_attributes == {"bogusSub": 1}


# A remove operation carrying a value


APPLY = ScimPolicy(remove_value_as_filter=ScimPolicy.RemoveValue.apply)


def group_with_members() -> Group:
    """Build a group whose members carry more than the value naming them."""
    return Group.model_validate(
        {
            "schemas": [str(Group.__schema__)],
            "displayName": "Tour Guides",
            "members": [
                {"value": "s-foobar", "display": "Foo Bar"},
                {"value": "autre", "display": "Autre"},
            ],
        }
    )


def entra_remove(value: Any) -> PatchOp[Group]:
    """Build the remove operation Microsoft Entra sends to drop a member."""
    return PatchOp[Group](
        operations=[
            PatchOperation(op=PatchOperation.Op.remove, path="members", value=value)
        ]
    )


def test_a_remove_carrying_a_value_is_refused_by_default():
    """:rfc:`RFC7644 §3.5.2.2 <7644#section-3.5.2.2>` reads the target of a remove in its path alone."""
    with pytest.raises(InvalidValueException):
        entra_remove([{"value": "s-foobar"}]).patch(group_with_members())


def test_a_remove_carrying_a_value_is_refused_at_validation_by_default():
    """The refusal answers the peer at parse time, before anything is applied."""
    with pytest.raises(ValidationError, match="carries no value"):
        PatchOp[Group].model_validate(
            {
                "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
                "Operations": [
                    {"op": "remove", "path": "members", "value": [{"value": "x"}]}
                ],
            },
            scim_ctx=Context.RESOURCE_PATCH_REQUEST,
        )


def test_a_remove_carrying_a_value_passes_validation_under_apply():
    """Reading the value as a selection means accepting the payload that carries one."""
    patch_op = PatchOp[Group].model_validate(
        {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "Operations": [
                {"op": "remove", "path": "members", "value": [{"value": "x"}]}
            ],
        },
        scim_ctx=Context.RESOURCE_PATCH_REQUEST,
        scim_policy=APPLY,
    )

    assert patch_op.operations[0].value == [{"value": "x"}]


def test_the_entra_remove_form_drops_the_member_it_names():
    """Entra sends the selection as a list of objects, which is scim2-server issue 13."""
    group = group_with_members()

    assert entra_remove([{"value": "s-foobar"}]).patch(group, scim_policy=APPLY)
    assert [member.value for member in group.members] == ["autre"]


def test_a_remove_value_given_as_a_bare_object_drops_the_member_it_names():
    """The same selection written without its enclosing list means the same thing."""
    group = group_with_members()

    assert entra_remove({"value": "s-foobar"}).patch(group, scim_policy=APPLY)
    assert [member.value for member in group.members] == ["autre"]


def test_a_selection_matches_a_member_carrying_more_than_it_names():
    """Entra names a member by its value alone, where the member also carries a display."""
    group = group_with_members()

    entra_remove([{"value": "s-foobar"}]).patch(group, scim_policy=APPLY)

    assert all(member.display is not None for member in group.members)


def test_a_selection_naming_several_sub_attributes_matches_on_all_of_them():
    """Every sub-attribute the selection names must match, as a filter joined by ``and``."""
    group = group_with_members()

    entra_remove([{"value": "s-foobar", "display": "Autre"}]).patch(
        group, scim_policy=APPLY
    )

    assert [member.value for member in group.members] == ["s-foobar", "autre"]


def test_a_selection_that_matches_nothing_is_a_success():
    """:rfc:`RFC7644 §3.5.2.2 <7644#section-3.5.2.2>` answers a membership that was not there with a success."""
    group = group_with_members()

    assert entra_remove([{"value": "absent"}]).patch(group, scim_policy=APPLY) is False
    assert len(group.members) == 2


def test_a_selection_listing_no_entry_removes_nothing():
    """An empty list selects no member, so none is removed."""
    group = group_with_members()

    assert entra_remove([]).patch(group, scim_policy=APPLY) is False
    assert len(group.members) == 2


def test_a_path_that_already_selects_refuses_a_value_even_under_apply():
    """Two selections are two intentions, and nothing says which one to honour."""
    patch_op = PatchOp[Group](
        operations=[
            PatchOperation(
                op=PatchOperation.Op.remove,
                path='members[display eq "Foo Bar"]',
                value=[{"value": "s-foobar"}],
            )
        ]
    )

    with pytest.raises(InvalidValueException):
        patch_op.patch(group_with_members(), scim_policy=APPLY)


def test_a_remove_value_that_names_no_sub_attribute_is_refused():
    """A selection is built from sub-attribute names, which a bare value does not carry."""
    with pytest.raises(InvalidValueException):
        entra_remove("s-foobar").patch(group_with_members(), scim_policy=APPLY)


def test_an_ambient_policy_reaches_a_remove_carrying_a_value():
    """A server states once per request what it tolerates, patches included."""
    group = group_with_members()

    with APPLY:
        entra_remove([{"value": "s-foobar"}]).patch(group)

    assert [member.value for member in group.members] == ["autre"]


def test_selections_from_several_entries_remove_every_member_they_name():
    """Each entry of the value selects its own members, as a filter joined by ``or``."""
    group = group_with_members()

    entra_remove(
        [{"value": "s-foobar", "display": "Foo Bar"}, {"value": "autre"}]
    ).patch(group, scim_policy=APPLY)

    assert group.members is None


@pytest.mark.parametrize(
    "name",
    [
        "value pr or value",
        'value eq "s-foobar" or value',
        "value) or (value",
        "members.value",
    ],
)
def test_a_selection_whose_name_carries_filter_syntax_is_refused(name):
    """A name slipping filter syntax in would remove more than the value lists."""
    group = group_with_members()

    with pytest.raises(InvalidValueException, match="not an attribute name"):
        entra_remove([{name: "absent"}]).patch(group, scim_policy=APPLY)

    assert len(group.members) == 2


@pytest.mark.parametrize("item", [{"value": "s-foobar"}, ["s-foobar"]])
def test_a_selection_comparing_a_name_to_several_values_is_refused(item):
    """A filter compares a sub-attribute to one value, not to an object or a list."""
    with pytest.raises(InvalidValueException, match="single value"):
        entra_remove([{"value": item}]).patch(group_with_members(), scim_policy=APPLY)


def test_a_selection_comparing_a_name_to_a_value_no_filter_can_carry_is_refused():
    """JSON has no literal for NaN, which a filter therefore cannot compare to."""
    with pytest.raises(InvalidValueException):
        entra_remove([{"value": float("nan")}]).patch(
            group_with_members(), scim_policy=APPLY
        )


# A path filter matching nothing


CREATE = ScimPolicy(unmatched_path_filter=ScimPolicy.UnmatchedPathFilter.create)


class Tag(ComplexAttribute):
    kind: str | None = None
    stamp: Annotated[str | None, Mutability.read_only] = None


class Tagged(Resource):
    __schema__ = URN("urn:example:2.0:Tagged")

    tags: list[Tag] | None = None
    sealed: Annotated[list[Tag] | None, Mutability.immutable] = None
    labels: list[str] | None = None


class Tagging(Extension):
    __schema__ = URN("urn:example:2.0:Tagging")

    tags: list[Tag] | None = None


def unmatched_patch(model: Any, *operations: dict[str, Any]) -> "PatchOp[Any]":
    """Build a patch from raw operations on the given resource type."""
    return PatchOp[model].model_validate({"Operations": list(operations)})


def test_an_add_whose_filter_matches_nothing_has_no_target_by_default():
    """Table 9 of RFC7644 §3.12 defines noTarget for a filter that yields no match."""
    patch = unmatched_patch(
        User,
        {"op": "add", "path": 'emails[type eq "work"].value', "value": "w@example.com"},
    )

    with pytest.raises(NoTargetException):
        patch.patch(User(user_name="bjensen"))


@pytest.mark.parametrize("op", ["add", "replace"])
def test_the_entry_a_filter_describes_is_created_under_create(op):
    """Microsoft Entra fills an absent work email through a filter, with add or replace."""
    user = User(user_name="bjensen")
    patch = unmatched_patch(
        User,
        {"op": op, "path": 'emails[type eq "work"].value', "value": "w@example.com"},
    )

    assert patch.patch(user, scim_policy=CREATE)

    assert [(email.type, email.value) for email in user.emails] == [
        ("work", "w@example.com")
    ]


def test_the_operations_with_the_same_filter_reach_the_created_entry():
    """Entra spreads one entry over several operations that share a filter."""
    user = User(user_name="bjensen")
    patch = unmatched_patch(
        User,
        {"op": "add", "path": 'emails[type eq "work"].value', "value": "w@example.com"},
        {"op": "add", "path": 'emails[type eq "work"].display', "value": "Work"},
    )

    assert patch.patch(user, scim_policy=CREATE)

    assert len(user.emails) == 1
    assert user.emails[0].display == "Work"


def test_a_value_is_merged_into_the_created_entry():
    """The created entry also takes the sub-attributes in the value."""
    user = User(user_name="bjensen")
    patch = unmatched_patch(
        User,
        {
            "op": "add",
            "path": 'emails[type eq "work"]',
            "value": {"value": "w@example.com"},
        },
    )

    assert patch.patch(user, scim_policy=CREATE)

    assert (user.emails[0].type, user.emails[0].value) == ("work", "w@example.com")


def test_a_created_primary_entry_becomes_the_only_primary():
    """The filter literal is read as ScimFilter compares it, and primary stays unique."""
    user = User(
        user_name="bjensen",
        emails=[{"type": "home", "value": "h@example.com", "primary": True}],
    )
    patch = unmatched_patch(
        User,
        {
            "op": "replace",
            "path": 'emails[type eq "work" and primary eq "True"].value',
            "value": "w@example.com",
        },
    )

    assert patch.patch(user, scim_policy=CREATE)

    assert [(email.type, email.primary) for email in user.emails] == [
        ("home", False),
        ("work", True),
    ]


def test_a_value_contradicting_the_filter_is_refused():
    """The created entry must match its filter, for a later operation to reach it."""
    user = User(user_name="bjensen")
    patch = unmatched_patch(
        User,
        {
            "op": "add",
            "path": 'emails[type eq "work"]',
            "value": {"type": "home", "value": "h@example.com"},
        },
    )

    with pytest.raises(InvalidValueException):
        patch.patch(user, scim_policy=CREATE)
    assert user.emails is None


@pytest.mark.parametrize(
    "path",
    [
        'emails[type eq "work" or type eq "home"].value',
        'emails[type ne "work"].value',
        'emails[not (type eq "work")].value',
        'emails[display co "Work"].value',
        "emails[type pr].value",
    ],
)
def test_a_filter_describing_no_entry_still_has_no_target(path):
    """Only eq comparisons joined by and describe the entry to create."""
    patch = unmatched_patch(User, {"op": "add", "path": path, "value": "w@example.com"})

    with pytest.raises(NoTargetException):
        patch.patch(User(user_name="bjensen"), scim_policy=CREATE)


def test_a_filter_over_simple_values_still_has_no_target():
    """A multi-valued attribute without sub-attributes has no entry to describe."""
    patch = unmatched_patch(
        Tagged, {"op": "replace", "path": 'labels[value eq "red"]', "value": "green"}
    )

    with pytest.raises(NoTargetException):
        patch.patch(Tagged(labels=["blue"]), scim_policy=CREATE)


def test_a_remove_whose_filter_matches_nothing_creates_nothing():
    """Per RFC7644 §3.5.2.2, a remove that selects nothing succeeds without change."""
    user = User(user_name="bjensen")
    patch = unmatched_patch(User, {"op": "remove", "path": 'emails[type eq "work"]'})

    assert patch.patch(user, scim_policy=CREATE) is False
    assert user.emails is None


def test_a_created_entry_cannot_set_a_read_only_sub_attribute():
    """The created entry goes through the same checks as an add of that entry."""
    patch = unmatched_patch(
        Tagged, {"op": "add", "path": 'tags[stamp eq "x"].kind', "value": "k"}
    )

    with pytest.raises(MutabilityException):
        patch.patch(Tagged(), scim_policy=CREATE)


def test_no_entry_is_created_in_an_immutable_attribute_holding_values():
    """An immutable multi-valued attribute takes no new entry once assigned."""
    patch = unmatched_patch(
        Tagged, {"op": "add", "path": 'sealed[kind eq "b"].kind', "value": "b"}
    )

    with pytest.raises(MutabilityException):
        patch.patch(Tagged(sealed=[{"kind": "a"}]), scim_policy=CREATE)


def test_an_unassigned_extension_is_created_with_the_entry():
    """An extension attribute is selected into as a core one is."""
    resource = Tagged[Tagging]()
    patch = unmatched_patch(
        Tagged[Tagging],
        {"op": "add", "path": 'urn:example:2.0:Tagging:tags[kind eq "b"]', "value": {}},
    )

    assert patch.patch(resource, scim_policy=CREATE)

    assert resource[Tagging].tags == [Tag(kind="b")]


def test_an_ambient_policy_reaches_the_creation():
    """A server may state the policy once per request with a block."""
    user = User(user_name="bjensen")
    patch = unmatched_patch(
        User,
        {"op": "add", "path": 'emails[type eq "work"].value', "value": "w@example.com"},
    )

    with CREATE:
        assert patch.patch(user)


def test_path_set_creates_nothing_under_create():
    """The policy only applies to PATCH, and Path.set still reports the missing target."""
    with CREATE, pytest.raises(NoTargetException):
        Path[User]('emails[type eq "work"].value').set(
            User(user_name="bjensen"), "w@example.com"
        )
