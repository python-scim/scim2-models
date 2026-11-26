from typing import Annotated

import pytest

from scim2_models import URN
from scim2_models import ComplexAttribute
from scim2_models import Context
from scim2_models import Mutability
from scim2_models import MutabilityException
from scim2_models import PatchOp
from scim2_models import Resource
from scim2_models import Returned


class Credential(ComplexAttribute):
    value: str | None = None
    label: str | None = None
    secret: Annotated[str | None, Mutability.write_only, Returned.never] = None
    hint: Annotated[str | None, Returned.never] = None


class Device(Resource):
    __schema__ = URN("urn:example:Device")

    name: str | None = None
    serial: Annotated[str | None, Mutability.immutable] = None
    credential: Annotated[Credential | None, Mutability.immutable] = None
    credentials: Annotated[list[Credential] | None, Mutability.immutable] = None


def stored_device():
    return Device(
        id="1",
        name="printer",
        credential=Credential(value="a", label="k", secret="s", hint="h"),
        credentials=[Credential(value="a", label="k", secret="s", hint="h")],
    )


def put(stored, payload):
    replacement = Device.model_validate(
        {"schemas": ["urn:example:Device"], **payload},
        scim_ctx=Context.RESOURCE_REPLACEMENT_REQUEST,
    )
    replacement.replace(stored)
    return replacement


def patch(stored, op, path, value=None):
    operation = {"op": op, "path": path}
    if value is not None:
        operation["value"] = value
    patch_op = PatchOp[Device].model_validate(
        {"Operations": [operation]}, scim_ctx=Context.RESOURCE_PATCH_REQUEST
    )
    return patch_op.patch(stored)


def test_a_put_resending_the_retrieved_resource_keeps_the_hidden_values():
    """A client that read the resource cannot resend its hidden sub-attributes."""
    stored = stored_device()
    retrieved = stored.model_dump(scim_ctx=Context.RESOURCE_QUERY_RESPONSE)
    assert "secret" not in retrieved["credential"]

    replacement = put(stored, {**retrieved, "name": "printer-2"})

    for credential in (replacement.credential, replacement.credentials[0]):
        assert (credential.secret, credential.hint) == ("s", "h")


@pytest.mark.parametrize(
    ("secret", "expected"), [("new", "new"), (None, None)], ids=["new", "null"]
)
def test_a_put_changes_a_write_only_sub_attribute_of_an_immutable_attribute(
    secret, expected
):
    """Per RFC7643 §2.2, the write-only mutability of a sub-attribute lets it change."""
    replacement = put(
        stored_device(),
        {
            "credential": {"value": "a", "label": "k", "secret": secret},
            "credentials": [{"value": "a", "label": "k", "secret": secret}],
        },
    )
    assert replacement.credential.secret == expected
    assert replacement.credentials[0].secret == expected


@pytest.mark.parametrize(
    "credential",
    [
        {"value": "a", "label": "other"},
        {"value": "a", "label": "k", "hint": "other"},
    ],
    ids=["visible", "never returned"],
)
@pytest.mark.parametrize("multi_valued", [False, True], ids=["single", "multi"])
def test_a_put_refuses_other_sub_attributes_of_an_immutable_attribute(
    credential, multi_valued
):
    """Only a write-only sub-attribute escapes the comparison of an immutable value."""
    payload = (
        {"credentials": [credential]} if multi_valued else {"credential": credential}
    )
    with pytest.raises(MutabilityException):
        put(stored_device(), payload)


def test_a_put_refuses_a_never_returned_sub_attribute_the_immutable_value_lacks():
    """A never-returned sub-attribute is not writable once its immutable parent is set."""
    stored = Device(id="1", credential=Credential(value="a", label="k"))
    with pytest.raises(MutabilityException):
        put(stored, {"credential": {"value": "a", "label": "k", "hint": "h"}})


@pytest.mark.parametrize(
    ("attribute", "value", "empty"),
    [
        ("serial", "x", None),
        ("credential", {"label": "k"}, None),
        ("credentials", [{"label": "k"}], []),
    ],
    ids=["simple", "complex", "multi-valued"],
)
def test_a_put_sets_an_immutable_attribute_that_has_no_value(attribute, value, empty):
    """Per RFC7644 §3.5.1, input values only have to match values already set."""
    stored = Device(id="1", **{attribute: empty})
    replacement = put(stored, {attribute: value})
    assert replacement.model_dump()[attribute] == value


def test_a_put_sets_an_immutable_attribute_that_only_holds_a_write_only_value():
    """A client sees no value in such an attribute, so it can set the others."""
    stored = Device(id="1", credential=Credential(secret="s"))
    replacement = put(stored, {"credential": {"value": "a"}})
    assert (replacement.credential.value, replacement.credential.secret) == ("a", "s")


@pytest.mark.parametrize(
    "credentials",
    [
        [Credential(label="k", hint="h"), Credential(label="l", hint="i")],
        [
            Credential(value="a", label="k", hint="h"),
            Credential(value="a", label="l", hint="i"),
        ],
    ],
    ids=["without value", "with a shared value"],
)
def test_a_put_pairs_entries_by_what_the_client_sees(credentials):
    """An entry that no value designates is paired by its visible sub-attributes."""
    stored = Device(id="1", credentials=credentials)
    retrieved = stored.model_dump(scim_ctx=Context.RESOURCE_QUERY_RESPONSE)

    replacement = put(stored, {"credentials": retrieved["credentials"][::-1]})

    assert {(entry.label, entry.hint) for entry in replacement.credentials} == {
        ("k", "h"),
        ("l", "i"),
    }


def test_a_put_takes_back_the_entries_of_an_immutable_attribute_in_another_order():
    """RFC7643 §2.4 gives no significance to the order of a multi-valued attribute."""
    stored = Device(id="1", credentials=[Credential(value="a"), Credential(value="b")])
    replacement = put(stored, {"credentials": [{"value": "b"}, {"value": "a"}]})
    assert [entry.value for entry in replacement.credentials] == ["b", "a"]


@pytest.mark.parametrize(
    ("path", "credential"),
    [
        ("credential.secret", lambda device: device.credential),
        ('credentials[value eq "a"].secret', lambda device: device.credentials[0]),
    ],
    ids=["single", "multi"],
)
@pytest.mark.parametrize("op", ["add", "replace"])
def test_a_patch_changes_a_write_only_sub_attribute_of_an_immutable_attribute(
    op, path, credential
):
    """A PATCH applies the same rule as a PUT to a write-only sub-attribute."""
    stored = stored_device()
    assert patch(stored, op, path, "new")
    assert credential(stored).secret == "new"


def test_a_patch_removes_a_write_only_sub_attribute_of_an_immutable_attribute():
    """Removing a write-only value is an update the sub-attribute allows."""
    stored = stored_device()
    assert patch(stored, "remove", "credential.secret")
    assert stored.credential.secret is None


@pytest.mark.parametrize(
    "path", ["credential.label", "credential.hint", 'credentials[value eq "a"].hint']
)
def test_a_patch_refuses_other_sub_attributes_of_an_immutable_attribute(path):
    """Only a write-only sub-attribute escapes the comparison of an immutable value."""
    stored = stored_device()
    with pytest.raises(MutabilityException):
        patch(stored, "replace", path, "other")
    assert stored == stored_device()


@pytest.mark.parametrize(
    ("op", "path", "value"),
    [("add", "credential.value", "a"), ("remove", "credential", None)],
)
def test_a_patch_sets_an_immutable_attribute_that_only_holds_a_write_only_value(
    op, path, value
):
    """A PATCH applies the same rule as a PUT to an attribute the client sees empty."""
    stored = Device(id="1", credential=Credential(secret="s"))
    assert patch(stored, op, path, value)
