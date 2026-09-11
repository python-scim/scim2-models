"""The policy that says how a peer's deviations from the specification are treated."""

import asyncio
import threading
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
from scim2_models import Group
from scim2_models import InvalidValueException
from scim2_models import PatchOp
from scim2_models import PatchOperation
from scim2_models import Resource
from scim2_models import ScimPolicy
from scim2_models import ScimProvider
from scim2_models import User
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


def test_replacing_a_complex_attribute_drops_the_unknowns_it_carried():
    """The whole attribute is replaced, so what was unknown in it goes with the rest."""
    with KEEP:
        user = User.model_validate(
            unknown_payload(name={"familyName": "Jensen", "bogusSub": 1})
        )
        operation = PatchOperation(
            op=PatchOperation.Op.replace_, path="name", value={"givenName": "Barbara"}
        )
        PatchOp[User](operations=[operation]).patch(user)

    assert user.name.family_name is None
    assert user.name.unknown_attributes == {}


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
